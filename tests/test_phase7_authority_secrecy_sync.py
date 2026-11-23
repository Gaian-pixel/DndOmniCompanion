"""Phase 7 TASK-049 regression tests: Server Authority, Non-DM Secrecy, Concurrency, Protocol & UDP Voice Keepalive."""

import base64
import os
import queue
import socket
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from common.game_state import GameState, Player
from common.network_utils import (
    broadcast,
    prepare_per_player_state_payload,
)
from common.protocol import (
    make_handout_share_broadcast,
    make_player_joined,
    make_quest_list_update,
)
from server.network import sanitize_client_payload


def _remote_player(name="Hero", role="PLAYER", cls="Ladro", level=5, hp=30):
    p = Player(name)
    p.role = role
    p.is_party_member = True
    p.hp = hp
    p.max_hp = hp
    p.position = [0, 0]
    p.conn = MagicMock(spec=socket.socket)
    p.full_sheet = {
        "name": name,
        "char_class": cls,
        "level": level,
        "ac": 15,
        "inventory_grid": [],
        "inventory": [],
    }
    return p


class TestPhase7AuthoritySecrecyAndSync(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.gs.current_map = {
            "width": 15,
            "height": 15,
            "grid_type": "hex",
            "hexes": [],
            "walls": [[5, 0]],
            "doors": [],
            "fow_enabled": False,
            "fow_revealed": [],
            "fow_draft": [],
        }

    def test_sanitize_client_payload_strips_privileged_keys_and_nested_aoe_flags(self):
        pc = _remote_player("Alice")
        dm = Player("DM")
        dm.role = "DM"
        raw = {
            "to": [3, 0],
            "is_dm_force": True,
            "is_teleport": True,
            "is_forced": True,
            "manual_roll": 20,
            "ignore_los": True,
            "_already_consumed_reaction": True,
            "_internal_bypass": 1,
            "forced_hit": True,
            "free_test": True,
            "extra_action": True,
            "aoe_data": {"origin": [1, 1], "size": 3, "ignore_los": True, "_secret": 1},
        }
        clean = sanitize_client_payload(raw, pc)
        self.assertEqual(clean["to"], [3, 0])
        for bad in (
            "is_dm_force", "is_teleport", "is_forced", "manual_roll",
            "ignore_los", "_already_consumed_reaction", "_internal_bypass",
            "forced_hit", "free_test", "extra_action",
        ):
            self.assertNotIn(bad, clean)
        self.assertEqual(clean["aoe_data"], {"origin": [1, 1], "size": 3})
        # DM preserves fields
        self.assertIn("is_dm_force", sanitize_client_payload(raw, dm))

    def test_companion_move_no_dm_escalation_and_error_routed_to_owner(self):
        from server.rules.movement import handle_move_request

        pc = _remote_player("Ranger")
        wolf = Player("Lupo")
        wolf.owner = "Ranger"
        wolf.is_companion = True
        wolf.conn = None
        wolf.position = [0, 0]
        self.gs.players = [pc, wolf]

        sent = []
        with patch("server.rules.movement.send_message", side_effect=lambda c, m: sent.append((c, m))):
            # Try jumping over wall at [5, 0] to [6, 0] with forged is_dm_force on companion
            handle_move_request({"entity_name": "Lupo", "to": [6, 0], "is_dm_force": True}, pc, self.gs)

        self.assertEqual(wolf.position, [0, 0])
        self.assertTrue(any(c is pc.conn and m.get("type") == "ERROR_REPLY" for c, m in sent))

    def test_fall_death_save_aoe_reaction_and_door_key_authority(self):
        from server.rules.chat import handle_chat
        from server.rules.combat import handle_death_save_request, handle_reaction_response
        from server.rules.map_interaction import handle_resolve_aoe_request, handle_toggle_door_request

        alice = _remote_player("Alice", cls="Guerriero", level=5, hp=0)
        bob = _remote_player("Bob", cls="Ladro", level=5, hp=40)
        boss = Player("Drago")
        boss.is_npc = True
        boss.hp = 100
        boss.max_hp = 100
        boss.position = [1, 0]
        self.gs.players = [alice, bob, boss]

        errs = []
        with patch("server.rules.chat.send_message", side_effect=lambda c, m: errs.append(m)), \
             patch("server.rules.combat.send_message", side_effect=lambda c, m: errs.append(m)), \
             patch("server.rules.map_interaction.send_message", side_effect=lambda c, m: errs.append(m)):
            # Non-DM cannot /fall another entity
            handle_chat({"text": "/fall 200 Drago"}, bob, self.gs)
            self.assertEqual(boss.hp, 100)

            # Non-DM cannot death save for another PC or supply manual_roll
            handle_death_save_request({"actor_name": "Alice", "manual_roll": 20}, bob, self.gs)
            self.assertEqual(alice.hp, 0)
            handle_death_save_request({"actor_name": "Alice", "manual_roll": 20}, alice, self.gs)
            self.assertEqual(alice.hp, 0)

            # Unauthorized RESOLVE_AOE_REQUEST by non-caster remote client rejected
            self.gs.active_aoes = [{"origin": [1, 0], "size": 2, "type": "sfera", "caster": "Mago", "dc": 15, "dmg": "8d6"}]
            handle_resolve_aoe_request({"aoe_index": 0, "dc": 99, "damage_formula": "20d10"}, bob, self.gs)
            self.assertEqual(boss.hp, 100)

            # Forged UNCANNY_DODGE self-heal without server _last_hit_for_reaction rejected
            bob.hp = 10
            bob.max_hp = 40
            handle_reaction_response(
                {"reaction_type": "UNCANNY_DODGE", "accepted": True, "target_name": "Drago", "details": {"dmg_to_hp": 60}},
                bob,
                self.gs,
            )
            self.assertEqual(bob.hp, 10)
            self.assertFalse(bob.has_reacted_this_turn)

            # Fake door key_item not in inventory rejected without leaking door_key
            self.gs.current_map["doors"] = [{"q": 0, "r": 1, "state": "locked", "key_name": "Chiave d'Ebano", "name": "Porta Segreta"}]
            handle_toggle_door_request({"q": 0, "r": 1, "method": "key", "key_item": "Chiave d'Ebano"}, bob, self.gs)
            self.assertEqual(self.gs.current_map["doors"][0]["state"], "locked")
            self.assertFalse(any("Chiave d'Ebano" in str(m) for m in errs))

    def test_secrecy_redaction_player_joined_quests_traps_combat_turn_and_listbox(self):
        from server.rules.combat import advance_combat_turn
        from server.rules.map_interaction import handle_quest_action_request
        from client.client import ClientGUI

        pc = _remote_player("Eroe")
        hidden_orc = Player("Orco Ombra")
        hidden_orc.is_npc = True
        hidden_orc.hp = 15
        hidden_orc.max_hp = 30
        hidden_orc.ac = 17
        hidden_orc.layer = "tokens"
        hidden_orc.is_hidden = False
        hidden_orc.position = [1, 0]
        hidden_orc.full_sheet = {
            "ac": 17,
            "hit_dice": "4d8",
            "hit_dice_pools": {"d8": {"total": 4, "current": 4}},
            "dm_note": "Trap ambush",
            "dm_notes": "Secret boss",
            "special_abilities": [{"name": "Secret"}],
        }

        stealth_npc = Player("Assassino")
        stealth_npc.is_npc = True
        stealth_npc.is_hidden = True
        stealth_npc.hp = 20
        stealth_npc.max_hp = 20
        stealth_npc.initiative = 5
        pc.initiative = 20
        pc.in_combat = True
        stealth_npc.in_combat = True
        self.gs.players = [pc, hidden_orc, stealth_npc]
        self.gs.active_complex_traps = [{"name": "Lame Rotanti", "dc": 16}]

        safe_state = self.gs.get_state_dict(is_dm=False)
        self.assertEqual(safe_state["active_complex_traps"], [])
        san_orc = next(pl for pl in safe_state["players"] if pl["name"] == "Orco Ombra")
        self.assertNotIn("ac", san_orc)
        self.assertNotIn("dm_note", san_orc["full_sheet"])
        self.assertNotIn("hit_dice", san_orc["full_sheet"])
        self.assertNotIn("hit_dice_pools", san_orc["full_sheet"])

        sent = []
        with patch("common.network_utils.send_message", side_effect=lambda c, m: sent.append(m)):
            broadcast(self.gs, make_player_joined(hidden_orc.to_dict()))
        joined = [m for m in sent if m.get("type") == "PLAYER_JOINED"]
        self.assertEqual(len(joined), 1)
        self.assertNotIn("ac", joined[0]["data"])
        self.assertNotIn("dm_note", joined[0]["data"]["full_sheet"])

        # Secret quest sanitized in QUEST_LIST_UPDATE and not announced to chat
        sent.clear()
        with patch("common.network_utils.send_message", side_effect=lambda c, m: sent.append(m)):
            handle_quest_action_request(
                {"action": "add", "quest": {"id": "q_sec", "title": "Culto Occulto", "secret": True, "description": "Test"}},
                None,
                self.gs,
            )
        q_updates = [m for m in sent if m.get("type") == "QUEST_LIST_UPDATE"]
        chats = [m for m in sent if m.get("type") == "CHAT_BROADCAST"]
        self.assertEqual(q_updates[0]["data"]["quests"], [])
        self.assertEqual(chats, [])

        # Hidden combatant turn name masked in chat broadcast
        hidden_orc.in_combat = False
        self.gs.combat_active = True
        self.gs.turn_index = 0
        sent.clear()
        with patch("common.network_utils.send_message", side_effect=lambda c, m: sent.append(m)):
            advance_combat_turn(self.gs)
        chat_texts = [m["data"]["text"] for m in sent if m.get("type") == "CHAT_BROADCAST"]
        self.assertTrue(any("Sconosciuto" in t and "Assassino" not in t for t in chat_texts))

        # ClientGUI.update_player_listbox hides exact HP of hostile NPCs
        inserted = []
        fake_lb = SimpleNamespace(
            cget=lambda _k: "normal",
            config=lambda **kw: None,
            delete=lambda *a: None,
            insert=lambda _idx, txt: inserted.append(txt),
            itemconfig=lambda *a, **kw: None,
        )
        fake_client = SimpleNamespace(
            name="Eroe",
            player_listbox=fake_lb,
            players_data={
                "Eroe": {"name": "Eroe", "hp": 30, "max_hp": 30, "is_party_member": True, "initiative": 12, "conditions": []},
                "Goblin": {"name": "Goblin", "hp": 5, "max_hp": 20, "is_npc": True, "initiative": 8, "conditions": []},
            },
            local_map_data={"fow_enabled": False},
            combat_active=False,
            turn_player_name="",
        )
        ClientGUI.update_player_listbox(fake_client)
        goblin_row = [r for r in inserted if "Goblin" in r][0]
        self.assertIn("Gravemente Ferito", goblin_row)
        self.assertNotIn("5/20", goblin_row)

    def test_handout_b64_no_path_leak_fow_avatar_resync_and_asset_rollback(self):
        from server.rules.map_interaction import handle_handout_share_request
        from client.network_handlers import ClientNetworkHandlersMixin

        pc = _remote_player("Eroe")
        self.gs.players = [pc]

        with tempfile.TemporaryDirectory() as td:
            img_path = os.path.join(td, "secret_map.png")
            raw_bytes = b"\x89PNG\r\n\x1a\nFAKEIMG"
            with open(img_path, "wb") as fh:
                fh.write(raw_bytes)

            sent = []
            with patch("common.network_utils.send_message", side_effect=lambda c, m: sent.append(m)):
                handle_handout_share_request({"title": "Mappa", "content": "Indizio", "image_path": img_path}, None, self.gs)

            ho_msgs = [m for m in sent if m.get("type") == "HANDOUT_SHARE_BROADCAST"]
            self.assertEqual(len(ho_msgs), 1)
            self.assertEqual(ho_msgs[0]["data"].get("image_path"), "")
            self.assertEqual(base64.b64decode(ho_msgs[0]["data"].get("image_b64", "")), raw_bytes)

            # Asset hash deduplication rollback on failed send
            pc2 = _remote_player("Mago")
            msg_ho = make_handout_share_broadcast("Mappa", "Indizio", image_path="", image_b64=base64.b64encode(raw_bytes).decode("ascii"))
            self.gs.players = [pc2]
            with patch("common.network_utils.send_message", return_value=False):
                broadcast(self.gs, msg_ho)
            # Hash must have been rolled back so next send still includes image_b64
            payload2 = prepare_per_player_state_payload(msg_ho, pc2)
            self.assertTrue(payload2["data"].get("image_b64"))

        # FOW_UPDATE_BROADCAST avatar rehydration + resync
        fake_client = SimpleNamespace(
            local_map_data={},
            players_data={},
            _asset_cache={"av_1": "BASE64AV"},
            _asset_cache_order=["av_1"],
            _missing_asset_hashes_pending=set(),
            is_connected=False,
            network=None,
            redraw_map_and_players=MagicMock(),
        )
        # Seed cache by storing via helper for real hash
        from common.network_utils import compute_asset_hash
        real_av = base64.b64encode(b"AVATARBYTES").decode("ascii")
        real_h = compute_asset_hash(real_av)
        ClientNetworkHandlersMixin._store_asset_in_cache(fake_client, real_h, real_av)
        ClientNetworkHandlersMixin.handle_fow_update_broadcast(
            fake_client,
            {"fow_revealed": [[1, 0]], "players": [{"name": "Orco", "avatar_hash": real_h, "avatar_cached": True}]},
        )
        self.assertEqual(fake_client.players_data["Orco"].get("avatar_b64"), real_av)

    def test_voice_server_keepalive_and_sio_udp_guard(self):
        from server.voice_server import VoiceServer
        from client.voice_client import VoiceClient

        srv = VoiceServer("127.0.0.1", 0)
        srv.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        srv.sock.bind(("127.0.0.1", 0))
        port = srv.sock.getsockname()[1]
        srv.running = True
        t = threading.Thread(target=srv._listen, daemon=True)
        t.start()

        vc = VoiceClient("127.0.0.1", port)
        try:
            vc.sock.sendto(b"JOIN", ("127.0.0.1", port))
            time.sleep(0.05)
            self.assertIn(vc.sock.getsockname()[1], {c[1] for c in srv.clients})

            # KEEPALIVE refreshes timestamp and does NOT relay PCM
            listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                listener.bind(("127.0.0.1", 0))
                listener.settimeout(0.15)
                listener.sendto(b"JOIN", ("127.0.0.1", port))
                time.sleep(0.05)
                vc.sock.sendto(b"KEEPALIVE", ("127.0.0.1", port))
                time.sleep(0.05)
                with self.assertRaises(socket.timeout):
                    listener.recvfrom(1024)
            finally:
                listener.close()
        finally:
            srv.stop()
            try:
                vc.sock.close()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
