"""
tests/test_audit_fixes.py - Test di regressione mirati per i fix dell'audit completo.
"""

import os
import sys
import queue
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["DND_MOCK_AUDIO"] = "1"

from common.game_state import GameState, Player
from common.network_utils import is_dm_actor
from common.srd_offline import normalize_npc_actions
from common.theme import setup_theme
from common.campaign import Campaign
from common.campaign_script import FlowNode


class _MockConn:
    def __init__(self):
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)


class TestSecurityAndAuthorizationFixes(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.attacker = Player("Attaccante", conn=_MockConn())
        self.attacker.is_party_member = True
        self.target = Player("Goblin", conn=None)
        self.target.hp = 30
        self.target.max_hp = 30
        self.gs.players = [self.attacker, self.target]

    def test_is_dm_actor_does_not_treat_plain_offline_player_as_dm(self):
        plain_pc = Player("OfflineHero")
        dm_actor = SimpleNamespace(role="DM")
        self.assertFalse(is_dm_actor(plain_pc))
        self.assertFalse(is_dm_actor(self.attacker))
        self.assertTrue(is_dm_actor(None))
        self.assertTrue(is_dm_actor(dm_actor))

    def test_sanitize_client_payload_strips_forced_keys_for_non_dm(self):
        from server.network import sanitize_client_payload

        raw = {"forced_roll": 1, "forced_wild_d20": 1, "free_test": True, "dc": 15}
        sanitized_pc = sanitize_client_payload(raw, self.attacker)
        self.assertEqual(sanitized_pc, {"dc": 15})
        sanitized_dm = sanitize_client_payload(raw, None)
        self.assertEqual(sanitized_dm, raw)

    def test_non_dm_rejected_from_admin_map_combat_monster_and_optional_tools(self):
        from server.rules.map_interaction import (
            handle_clear_drawings_request,
            handle_quest_action_request,
            handle_handout_share_request,
            handle_toggle_wall_request,
            handle_toggle_cover_request,
        )
        from server.rules.combat import (
            handle_apply_pending_damage_request,
            handle_set_automation_mode_request,
        )
        from server.dm_monster_engine import handle_resolve_legendary_resistance_request
        from server.dm_optional_tools import handle_optional_rule_action_request

        self.gs.drawn_lines = [{"points": [(0, 0), (1, 1)]}]
        handle_clear_drawings_request({}, self.attacker, self.gs)
        self.assertEqual(len(self.gs.drawn_lines), 1)

        self.gs.current_map = {"walls": [], "half_cover": [], "doors": [], "fow_revealed": [], "fow_draft": []}
        handle_toggle_wall_request({"q": 2, "r": 2}, self.attacker, self.gs)
        handle_toggle_cover_request({"q": 2, "r": 3, "cover_type": "half_cover"}, self.attacker, self.gs)
        self.assertEqual(self.gs.current_map["walls"], [])
        self.assertEqual(self.gs.current_map["half_cover"], [])

        before_quests = list(self.gs.quests)
        handle_quest_action_request({"action": "add", "title": "Hack"}, self.attacker, self.gs)
        self.assertEqual(self.gs.quests, before_quests)

        before_mode = self.gs.automation_mode
        handle_set_automation_mode_request({"mode": "manual"}, self.attacker, self.gs)
        self.assertEqual(self.gs.automation_mode, before_mode)

        self.gs.pending_damages["d1"] = {"target": "Goblin", "damage": 10, "damage_type": "Fuoco", "source": "Attaccante"}
        handle_apply_pending_damage_request({"pending_id": "d1", "action": "apply"}, self.attacker, self.gs)
        self.assertIn("d1", self.gs.pending_damages)
        self.assertEqual(self.target.hp, 30)

        self.gs.pending_legendary_resistances["lr1"] = {"target": "Goblin", "stat": "DES", "dc": 15}
        handle_resolve_legendary_resistance_request({"pending_id": "lr1", "decision": "use"}, self.attacker, self.gs)
        self.assertIn("lr1", self.gs.pending_legendary_resistances)

        with patch("server.dm_optional_tools.broadcast") as mock_bc:
            handle_handout_share_request({"title": "Spam", "content": "x"}, self.attacker, self.gs)
            handle_optional_rule_action_request({"action": "morale_check"}, self.attacker, self.gs)
            mock_bc.assert_not_called()


class TestCombatAndRulesFixes(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())

    def test_deferred_legendary_resistance_avoids_double_damage_and_preserves_concentration(self):
        from server.rules.combat import _process_save_result
        from server.dm_monster_engine import handle_resolve_legendary_resistance_request

        self.gs.automation_settings["opt_legendary_res_prompt"] = True
        self.gs.automation_settings["auto_apply_aoe_damage"] = True
        dragon = Player("Drago")
        dragon.hp = 100
        dragon.max_hp = 100
        dragon.legendary_resistances_max = 3
        dragon.legendary_resistances_current = 3
        dragon.conditions = ["Concentrazione"]
        dragon.active_effects = [{"name": "Veleno", "save_ends": {"stat": "COS", "dc": 15}}]
        wizard = Player("Mago")
        self.gs.players = [dragon, wizard]

        # Failed save against 20 fire damage (half on success): must defer cleanly
        _process_save_result("Drago", "DES", 5, False, False, 18, "20", True, "Mago", self.gs, "Fuoco")
        self.assertEqual(dragon.hp, 100)
        self.assertIn("Concentrazione", dragon.conditions)
        self.assertEqual(len(self.gs.pending_legendary_resistances), 1)
        lr_id = next(iter(self.gs.pending_legendary_resistances))

        # DM decides to use Legendary Resistance -> save succeeds (takes half: 10), LR becomes 2
        with patch("threading.Timer") as mock_timer:
            handle_resolve_legendary_resistance_request({"pending_id": lr_id, "decision": "use"}, None, self.gs)
            self.assertEqual(dragon.legendary_resistances_current, 2)
            self.assertEqual(dragon.hp, 90)
            self.assertEqual(len(self.gs.pending_legendary_resistances), 0)
            self.assertTrue(mock_timer.called or "Concentrazione" in dragon.conditions)

        # Second failed save where DM chooses NOT to spend LR -> takes full 20
        _process_save_result("Drago", "DES", 5, False, False, 18, "20", True, "Mago", self.gs, "Fuoco")
        lr_id_2 = next(iter(self.gs.pending_legendary_resistances))
        handle_resolve_legendary_resistance_request({"pending_id": lr_id_2, "decision": "fail"}, None, self.gs)
        self.assertEqual(dragon.legendary_resistances_current, 2)
        self.assertEqual(dragon.hp, 70)

    def test_bonus_action_attack_rollback_on_validation_failure(self):
        from server.rules.combat import handle_attack_request

        hero = Player("Guerriero", conn=_MockConn())
        hero.position = [0, 0]
        orc = Player("Orco")
        orc.position = [10, 10]
        orc.hp = 30
        orc.max_hp = 30
        self.gs.players = [hero, orc]
        self.gs.combat_active = True
        self.gs.automation_settings["strict_turn_lock"] = True

        # Out-of-reach bonus attack must fail cleanly and NOT burn bonus_action_used_this_turn
        handle_attack_request(
            {"target_name": "Orco", "weapon_name": "Pugnale", "hit_bonus": 15, "damage_formula": "1d4", "is_bonus_action": True},
            hero,
            self.gs,
        )
        self.assertFalse(hero.bonus_action_used_this_turn)
        self.assertTrue(len(hero.conn.sent) >= 1)

        # In-reach bonus attack must mark bonus_action_used_this_turn
        orc.position = [1, 0]
        handle_attack_request(
            {"target_name": "Orco", "weapon_name": "Pugnale", "hit_bonus": 15, "damage_formula": "1d4", "is_bonus_action": True},
            hero,
            self.gs,
        )
        self.assertTrue(hero.bonus_action_used_this_turn)

        # Second bonus attack in the same turn must be rejected
        prev_msgs = len(hero.conn.sent)
        handle_attack_request(
            {"target_name": "Orco", "weapon_name": "Pugnale", "hit_bonus": 15, "damage_formula": "1d4", "is_bonus_action": True},
            hero,
            self.gs,
        )
        self.assertGreater(len(hero.conn.sent), prev_msgs)

    def test_give_item_rejects_excess_quantity_and_transfers_valid_quantity(self):
        from server.rules.inventory import handle_give_item_request

        sender = Player("Bardo", conn=_MockConn())
        receiver = Player("Chierico", conn=_MockConn())
        potion = {"name": "Pozione di Guarigione", "type": "Consumabile", "qty": 2, "weight": 0.5}
        sender.full_sheet = {"inventory_grid": [dict(potion)] + [None] * 24}
        receiver.full_sheet = {"inventory_grid": [None] * 25}
        self.gs.players = [sender, receiver]

        # Attempt to give 5 when owning 2 -> rejected
        handle_give_item_request({"target_name": "Chierico", "item": {"name": "Pozione di Guarigione", "qty": 5}}, sender, self.gs)
        self.assertEqual(sender.full_sheet["inventory_grid"][0]["qty"], 2)
        self.assertIsNone(receiver.full_sheet["inventory_grid"][0])

        # Valid give of 1
        handle_give_item_request({"target_name": "Chierico", "item": {"name": "Pozione di Guarigione", "qty": 1}}, sender, self.gs)
        self.assertEqual(sender.full_sheet["inventory_grid"][0]["qty"], 1)
        self.assertEqual(receiver.full_sheet["inventory_grid"][0]["qty"], 1)

    def test_knock_and_dispel_magic_enforce_spell_slots(self):
        from server.rules.map_interaction import handle_toggle_door_request
        from server.rules.reaction_magic import handle_dispel_magic_request

        caster = Player("Mago", conn=_MockConn())
        caster.position = [0, 0]
        caster.full_sheet = {
            "spell_slots": {"1": {"max": 2, "current": 2}, "2": {"max": 1, "current": 0}, "3": {"max": 1, "current": 0}}
        }
        victim = Player("Alleato")
        victim.active_effects = [{"name": "Blocca Persone", "target": "Alleato", "caster": "Cultista"}]
        self.gs.current_map = {"doors": [{"q": 1, "r": 0, "state": "locked", "name": "Porta"}], "walls": [], "fow_revealed": [], "fow_draft": []}
        self.gs.players = [caster, victim]

        # No 2nd-level slot -> knock fails
        handle_toggle_door_request({"q": 1, "r": 0, "method": "knock"}, caster, self.gs)
        self.assertEqual(self.gs.current_map["doors"][0]["state"], "locked")

        # No 3rd-level slot -> dispel fails
        handle_dispel_magic_request({"target_name": "Alleato", "slot_level": 3}, caster, self.gs)
        self.assertEqual(len(victim.active_effects), 1)

        # Grant slots -> both succeed and consume slots
        caster.full_sheet["spell_slots"]["2"]["current"] = 1
        caster.full_sheet["spell_slots"]["3"]["current"] = 1
        handle_toggle_door_request({"q": 1, "r": 0, "method": "knock"}, caster, self.gs)
        self.assertEqual(self.gs.current_map["doors"][0]["state"], "open")
        self.assertEqual(caster.full_sheet["spell_slots"]["2"]["current"], 0)

        handle_dispel_magic_request({"target_name": "Alleato", "slot_level": 3}, caster, self.gs)
        self.assertEqual(len(victim.active_effects), 0)
        self.assertEqual(caster.full_sheet["spell_slots"]["3"]["current"], 0)


class TestDataCampaignAndUIFixes(unittest.TestCase):
    def test_normalize_npc_actions(self):
        self.assertEqual(normalize_npc_actions(None), [])
        str_res = normalize_npc_actions("Morso. +4 a colpire, 1d6+2 perforanti.\nArtiglio. 1d4 taglienti.")
        self.assertEqual(len(str_res), 2)
        self.assertEqual(str_res[0]["name"], "Morso")
        self.assertEqual(normalize_npc_actions(["Schianto: 1d8"])[0]["name"], "Schianto")
        self.assertEqual(normalize_npc_actions([{"name": "Soffio", "desc": "Fuoco"}])[0]["name"], "Soffio")

    def test_activate_encounter_on_vtt_count_qty_ac_and_victory_reset(self):
        from server.dm_live_flow import DMLiveFlowDialog

        gs = GameState(queue.Queue())
        camp = Campaign(name="CampTest")

        dlg = DMLiveFlowDialog.__new__(DMLiveFlowDialog)
        dlg.master_gui = MagicMock()
        dlg._get_game_state = lambda: gs
        dlg.campaign = camp
        dlg.session_ledger = MagicMock()
        dlg._record_to_campaign_journal = MagicMock()
        dlg.winfo_exists = lambda: True

        node = FlowNode(
            id="n1",
            node_type="encounter",
            title="Agguato",
            data={"monsters": [{"name": "Goblin", "count": 3, "hp": 7, "ac": 15, "cr": "1/4"}]},
        )
        with patch("server.network.broadcast"), patch("server.dm_live_flow.messagebox.showinfo"):
            DMLiveFlowDialog.activate_encounter_on_vtt(dlg, node)

        spawned = [p for p in gs.players if p.name.startswith("Goblin")]
        self.assertEqual(len(spawned), 3)
        self.assertTrue(all(p.ac == 15 for p in spawned))
        dlg.session_ledger.record_combat.assert_called_once()
        self.assertFalse(dlg.session_ledger.record_combat.call_args.kwargs["victory"])

    def test_theme_defines_all_referenced_ttk_styles(self):
        root = tk.Tk()
        root.withdraw()
        try:
            setup_theme(root)
            style = ttk.Style(root)
            for s_name in ("Gold.TLabel", "Primary.TLabel", "Small.TButton", "Warning.TButton"):
                cfg = style.configure(s_name)
                self.assertTrue(cfg, f"Style {s_name} should be configured")
        finally:
            root.destroy()

    def test_dm_automation_panel_badge_includes_pending_legendary_resistances(self):
        from server.dm_automation_panel import update_pending_actions_ui

        root = tk.Tk()
        root.withdraw()
        try:
            gs = GameState(queue.Queue())
            gs.pending_legendary_resistances["lr1"] = {"target": "Drago", "stat": "DES", "dc": 15}
            dm_mock = MagicMock()
            dm_mock.server.game_state = gs
            dm_mock.pending_actions_container = tk.Frame(root)
            del dm_mock.dm_quick_dice_strip

            update_pending_actions_ui(dm_mock)
            texts = [
                w.cget("text")
                for parent in dm_mock.pending_actions_container.winfo_children()
                for w in [parent] + parent.winfo_children()
                if isinstance(w, tk.Label)
            ]
            self.assertIn("(1)", texts)
        finally:
            root.destroy()

    def test_open_conditions_dialog_preserves_custom_conditions(self):
        from server.dm_entity_dialogs import open_conditions_dialog

        root = tk.Tk()
        root.withdraw()
        try:
            gs = GameState(queue.Queue())
            hero = Player("Eroe")
            hero.conditions = ["Benedetto", "Prono", "Concentrazione"]
            gs.players = [hero]

            dm_mock = MagicMock()
            dm_mock.master = root
            dm_mock.server.game_state = gs
            dm_mock.get_player_name_from_listbox.return_value = "Eroe"

            open_conditions_dialog(dm_mock)
            top = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))

            def all_widgets(w):
                res = [w]
                for c in w.winfo_children():
                    res.extend(all_widgets(c))
                return res

            apply_btn = next(w for w in all_widgets(top) if isinstance(w, (ttk.Button, tk.Button)))
            with patch("server.dm_entity_dialogs.broadcast"):
                apply_btn.invoke()
            self.assertIn("Benedetto", hero.conditions)
            self.assertIn("Concentrazione", hero.conditions)
        finally:
            root.destroy()

    def test_client_companion_filtered_out_and_sheet_dirty_preserved(self):
        from client.client import ClientGUI
        from client.character_manager import Character
        from client.character_sheet_ui import CharacterSheetFrame

        root = tk.Tk()
        root.withdraw()
        try:
            # Verify companion filtering from owned_chars
            c_mock = MagicMock()
            c_mock.name = "Aragorn"
            c_mock.players_data = {}
            c_mock.active_character = None
            c_mock.character_manager = None
            c_mock.map_canvas = None
            c_mock.combat_active = False
            c_mock._is_my_turn = False
            c_mock.lbl_time = None
            c_mock.active_character_var = tk.StringVar(value="Aragorn")
            c_mock.active_character_combo = {"values": []}
            data = {
                "players": [
                    {"name": "Aragorn", "is_companion": False},
                    {"name": "Lupo Fedele", "owner": "Aragorn", "is_companion": True},
                ]
            }
            ClientGUI.handle_game_state(c_mock, data)
            self.assertEqual(c_mock.active_character_combo["values"], ["Aragorn"])

            # Verify recalculate_and_refresh_derived_stats keeps dirty state intact
            char = Character("Eroe", "Guerriero")
            sheet = CharacterSheetFrame(root, char, manager=None, is_connected=False)
            sheet._initial_state_snapshot = {"marker": "orig"}
            sheet.recalculate_and_refresh_derived_stats()
            self.assertEqual(sheet._initial_state_snapshot, {"marker": "orig"})
            sheet.destroy()
        finally:
            root.destroy()

    def test_non_dm_blocked_from_travel_camp_and_journal_handlers(self):
        from server.rules.character import (
            handle_set_travel_params_request,
            handle_set_watch_shifts_request,
            handle_resolve_night_camp_request,
            handle_generate_encounter_request,
        )
        from server.rules.journal import handle_journal_update_request

        gs = GameState(queue.Queue())
        gs.travel_biome = "foresta"
        gs.camp_watch_shifts = {}
        gs.time_hour = 8
        gs.campaign_journal.get_active_session().title = "Originale"

        non_dm = Player("Giocatore", conn=_MockConn())
        non_dm.role = "PLAYER"

        handle_set_travel_params_request({"biome": "vulcano"}, non_dm, gs)
        self.assertEqual(gs.travel_biome, "foresta")

        handle_set_watch_shifts_request({"shifts": {"1": "Giocatore"}, "has_campfire": False}, non_dm, gs)
        self.assertEqual(gs.camp_watch_shifts, {})

        handle_resolve_night_camp_request({}, non_dm, gs)
        self.assertEqual(gs.time_hour, 8)

        with patch("common.travel_data.generate_biome_encounter") as mock_gen:
            handle_generate_encounter_request({"biome": "palude"}, non_dm, gs)
            mock_gen.assert_not_called()

        handle_journal_update_request({"session_index": 0, "title": "Manomesso"}, non_dm, gs)
        self.assertEqual(gs.campaign_journal.get_active_session().title, "Originale")
        self.assertGreaterEqual(len(non_dm.conn.sent), 5)

        dm = Player("DM")
        dm.role = "DM"
        handle_set_travel_params_request({"biome": "montagna"}, dm, gs)
        self.assertEqual(gs.travel_biome, "montagna")
        handle_journal_update_request({"session_index": 0, "title": "Capitolo 1"}, dm, gs)
        self.assertEqual(gs.campaign_journal.get_active_session().title, "Capitolo 1")

    def test_client_audio_play_blocks_unsafe_url_schemes(self):
        from client.client import ClientGUI

        c_mock = MagicMock()
        with patch("webbrowser.open") as mock_open:
            ClientGUI.handle_audio_play(c_mock, {"url": "file:///C:/Windows/System32/calc.exe"})
            ClientGUI.handle_audio_play(c_mock, {"url": "javascript:alert(1)"})
            ClientGUI.handle_audio_play(c_mock, {"url": r"\\evil\share\payload.exe"})
            mock_open.assert_not_called()

            ClientGUI.handle_audio_play(c_mock, {"url": "https://example.com/music.mp3"})
            mock_open.assert_called_once_with("https://example.com/music.mp3")

    def test_client_audio_track_chunk_bounds_and_atomic_write(self):
        import base64
        import tempfile
        from client.client import ClientGUI

        with tempfile.TemporaryDirectory() as tmpdir:
            c_mock = MagicMock()
            c_mock.audio_cache_dir = tmpdir
            c_mock._audio_downloads = {}
            c_mock._pending_play = None

            # Indici invalidi o fuori intervallo devono essere ignorati
            b64_ok = base64.b64encode(b"ID3DATA").decode("ascii")
            ClientGUI.handle_audio_track_chunk(c_mock, {"track_id": "abc123", "index": -1, "total": 2, "data": b64_ok, "ext": ".mp3"})
            ClientGUI.handle_audio_track_chunk(c_mock, {"track_id": "abc123", "index": 2, "total": 2, "data": b64_ok, "ext": ".mp3"})
            ClientGUI.handle_audio_track_chunk(c_mock, {"track_id": "abc123", "index": 0, "total": 9999, "data": b64_ok, "ext": ".mp3"})
            self.assertEqual(c_mock._audio_downloads, {})

            # Ricomposizione valida in 2 chunk e scrittura atomica
            c_mock._pending_play = {"track_id": "abc123", "name": "Taverna", "channel": "music", "loop": True, "volume": 0.7, "ext": ".mp3"}
            ClientGUI.handle_audio_track_chunk(c_mock, {"track_id": "abc123", "index": 0, "total": 2, "data": base64.b64encode(b"PART1").decode("ascii"), "ext": ".mp3"})
            self.assertIn("abc123", c_mock._audio_downloads)
            ClientGUI.handle_audio_track_chunk(c_mock, {"track_id": "abc123", "index": 1, "total": 2, "data": base64.b64encode(b"PART2").decode("ascii"), "ext": ".mp3"})

            target = os.path.join(tmpdir, "abc123.mp3")
            self.assertTrue(os.path.isfile(target))
            self.assertFalse(os.path.exists(target + ".tmp"))
            with open(target, "rb") as fh:
                self.assertEqual(fh.read(), b"PART1PART2")
            c_mock.audio_manager.play.assert_called_once()

    def test_audio_downloads_ttl_eviction_and_max_concurrent_cap(self):
        import base64
        import tempfile
        from client.client import ClientGUI

        with tempfile.TemporaryDirectory() as tmpdir:
            c_mock = MagicMock()
            c_mock.audio_cache_dir = tmpdir
            c_mock._audio_downloads = {
                "stale_trk": {"total": 3, "ext": ".mp3", "chunks": {0: b"x"}, "started_at": 1.0, "updated_at": 1.0}
            }
            c_mock._audio_download_ttl = 60.0
            c_mock._max_audio_downloads = 2
            c_mock._pending_play = {"track_id": "stale_trk", "name": "Vecchia"}

            # 1. Verifica scadenza TTL esplicita + pulizia _pending_play
            ClientGUI._prune_stale_audio_downloads(c_mock, now=100.0)
            self.assertNotIn("stale_trk", c_mock._audio_downloads)
            self.assertIsNone(c_mock._pending_play)

            # 2. Verifica cap massimo download concorrenti (evict del piu vecchio)
            b64_ok = base64.b64encode(b"CHUNK").decode("ascii")
            with patch("client.client.time.monotonic", side_effect=[200.0, 200.0, 201.0, 201.0, 202.0, 202.0]):
                ClientGUI.handle_audio_track_chunk(c_mock, {"track_id": "trk1", "index": 0, "total": 2, "data": b64_ok, "ext": ".mp3"})
                ClientGUI.handle_audio_track_chunk(c_mock, {"track_id": "trk2", "index": 0, "total": 2, "data": b64_ok, "ext": ".mp3"})
                ClientGUI.handle_audio_track_chunk(c_mock, {"track_id": "trk3", "index": 0, "total": 2, "data": b64_ok, "ext": ".mp3"})

            self.assertEqual(len(c_mock._audio_downloads), 2)
            self.assertNotIn("trk1", c_mock._audio_downloads)
            self.assertIn("trk2", c_mock._audio_downloads)
            self.assertIn("trk3", c_mock._audio_downloads)

            # 3. Messaggi malformati verso ClientGUI non devono sollevare eccezioni
            ClientGUI.handle_server_message(c_mock, "non_un_dizionario")
            ClientGUI.handle_server_message(c_mock, {"type": 123, "data": []})
            ClientGUI.handle_server_message(c_mock, {"type": "UNKNOWN_EVT", "data": None})

    def test_server_malformed_packets_do_not_drop_connection(self):
        from server.network import Server

        class _FakeConn:
            def settimeout(self, _t):
                pass
            def setsockopt(self, *_a):
                pass
            def close(self):
                pass
            def sendall(self, _b):
                pass

        srv = Server("127.0.0.1", 0, queue.Queue())
        fake_conn = _FakeConn()
        sent_messages = []
        dispatched_chat = []

        incoming = iter([
            {"type": "JOIN", "data": {"name": "EroeTest", "position": "bad_pos"}},
            "not_a_dict",
            {"type": 999, "data": {}},
            {"type": "CHAT", "data": ["lista_non_valida"]},
            {"type": "CHAT", "data": {"text": "Ancora connesso!"}},
            None,
        ])

        def fake_chat_handler(payload, player, gs):
            dispatched_chat.append((player.name, payload.get("text")))

        with patch("server.network.receive_message", side_effect=lambda _c: next(incoming)), \
             patch("server.network.send_message", side_effect=lambda _c, m: sent_messages.append(m)), \
             patch("server.network.broadcast"), \
             patch.dict("server.network.command_handlers", {"CHAT": fake_chat_handler}):
            srv.handle_client(fake_conn, ("127.0.0.1", 55555))

        self.assertEqual(dispatched_chat, [("EroeTest", "Ancora connesso!")])
        err_texts = [m["data"]["text"] for m in sent_messages if isinstance(m, dict) and m.get("type") == "ERROR_REPLY"]
        self.assertGreaterEqual(len(err_texts), 3)

    def test_server_join_session_password_and_rate_limiting(self):
        from common.protocol import make_join
        from server.network import Server

        class _FakeConn:
            def settimeout(self, _t):
                pass
            def setsockopt(self, *_a):
                pass
            def close(self):
                pass
            def sendall(self, _b):
                pass

        # 1. make_join mantiene retrocompatibilità senza password e la include se valorizzata
        self.assertNotIn("password", make_join("Elara")["data"])
        self.assertEqual(make_join("Elara", password="1234")["data"]["password"], "1234")

        # 2. Password errata + rate limit dopo 5 tentativi dallo stesso IP
        srv = Server("127.0.0.1", 0, queue.Queue(), session_password="Drago5e")
        sent_msgs = []
        with patch("server.network.send_message", side_effect=lambda _c, m: sent_msgs.append(m)), \
             patch("server.network.broadcast"):
            for _ in range(Server.AUTH_MAX_ATTEMPTS):
                with patch("server.network.receive_message", return_value=make_join("Intruder", password="wrong")):
                    srv.handle_client(_FakeConn(), ("10.0.0.5", 40000))

            self.assertIsNone(srv.game_state.find_player("Intruder"))
            self.assertTrue(srv._is_ip_rate_limited("10.0.0.5"))

            # Anche con la password giusta l'IP bloccato deve restare respinto
            with patch("server.network.receive_message", return_value=make_join("Intruder", password="Drago5e")):
                srv.handle_client(_FakeConn(), ("10.0.0.5", 40001))
            self.assertIsNone(srv.game_state.find_player("Intruder"))

            # Un IP diverso con password corretta viene ammesso
            seq = iter([make_join("Elara", password="Drago5e"), None])
            with patch("server.network.receive_message", side_effect=lambda _c: next(seq)):
                srv.handle_client(_FakeConn(), ("10.0.0.99", 40002))
            self.assertIsNotNone(srv.game_state.find_player("Elara"))

            # Cambio/rimozione password sblocca e permette JOIN senza PIN
            srv.set_session_password("")
            self.assertFalse(srv._is_ip_rate_limited("10.0.0.5"))
            seq2 = iter([make_join("Ospite"), None])
            with patch("server.network.receive_message", side_effect=lambda _c: next(seq2)):
                srv.handle_client(_FakeConn(), ("10.0.0.5", 40003))
            self.assertIsNotNone(srv.game_state.find_player("Ospite"))

    def test_hash_cached_map_and_handout_transfer_deduplication(self):
        import base64
        from common.network_utils import broadcast, compute_asset_hash
        from common.protocol import make_game_state, make_handout_broadcast, make_map_data_update_broadcast
        from client.client import ClientGUI

        b64_map = base64.b64encode(b"FAKE_PNG_MAP_PAYLOAD_DATA").decode("ascii")
        b64_handout = base64.b64encode(b"FAKE_PNG_HANDOUT_DATA").decode("ascii")
        expected_map_hash = compute_asset_hash(b64_map)
        expected_handout_hash = compute_asset_hash(b64_handout)

        gs = GameState(queue.Queue())
        gs.current_map = {"name": "Cripta", "bg_image_data": b64_map, "hexes": {}}
        gs.handouts = [{"title": "Pergamena", "content": "Testo", "image_b64": b64_handout}]

        p1 = Player("P1", conn=object())
        p2 = Player("P2", conn=object())
        gs.players = [p1]

        delivered = []
        with patch("common.network_utils.send_message", side_effect=lambda conn, msg: delivered.append((conn, msg))):
            # 1. Primo broadcast: solo P1 -> riceve payload completi
            broadcast(gs, make_game_state(gs.get_state_dict(is_dm=False)))
            self.assertEqual(len(delivered), 1)
            pkt1 = delivered[0][1]
            self.assertEqual(pkt1["data"]["map"]["bg_image_data"], b64_map)
            self.assertEqual(pkt1["data"]["map"]["bg_image_hash"], expected_map_hash)
            self.assertEqual(pkt1["data"]["handouts"][0]["image_b64"], b64_handout)

            # 2. Secondo broadcast: P1 e P2 insieme -> P1 riceve riferimenti hash/cached, P2 riceve i blob completi
            gs.players = [p1, p2]
            delivered.clear()
            broadcast(gs, make_game_state(gs.get_state_dict(is_dm=False)))
            self.assertEqual(len(delivered), 2)
            pkt_p1 = delivered[0][1]
            pkt_p2 = delivered[1][1]
            self.assertIsNone(pkt_p1["data"]["map"]["bg_image_data"])
            self.assertTrue(pkt_p1["data"]["map"].get("bg_image_cached"))
            self.assertEqual(pkt_p1["data"]["map"]["bg_image_hash"], expected_map_hash)
            self.assertIsNone(pkt_p1["data"]["handouts"][0]["image_b64"])
            self.assertTrue(pkt_p1["data"]["handouts"][0].get("image_cached"))
            self.assertEqual(pkt_p1["data"]["handouts"][0]["image_hash"], expected_handout_hash)
            self.assertEqual(pkt_p2["data"]["map"]["bg_image_data"], b64_map)
            self.assertEqual(pkt_p2["data"]["handouts"][0]["image_b64"], b64_handout)

            # 3. ClientGUI ricostruisce map_data e handout dalla cache client anche su pacchetti deduplicati
            c_mock = MagicMock()
            c_mock.name = "P1"
            c_mock.active_character = None
            c_mock._asset_cache = {}
            ClientGUI.handle_game_state(c_mock, pkt1["data"])
            self.assertIn(expected_map_hash, c_mock._asset_cache)
            ClientGUI.handle_game_state(c_mock, pkt_p1["data"])
            self.assertEqual(c_mock.local_map_data["bg_image_data"], b64_map)
            self.assertEqual(pkt_p1["data"]["handouts"][0]["image_b64"], b64_handout)

            # 4. Verifica MAP_DATA_UPDATE e HANDOUT_BROADCAST deduplicati su P1
            delivered.clear()
            broadcast(gs, make_map_data_update_broadcast(gs.current_map))
            ClientGUI.handle_map_data_update(c_mock, delivered[0][1]["data"])
            self.assertEqual(c_mock.local_map_data["bg_image_data"], b64_map)

            delivered.clear()
            broadcast(gs, make_handout_broadcast("Pergamena", b64_handout))
            self.assertIsNone(delivered[0][1]["data"]["image_b64"])
            ClientGUI._resolve_cached_handout_assets(c_mock, delivered[0][1]["data"])
            self.assertEqual(delivered[0][1]["data"]["image_b64"], b64_handout)

    def test_client_and_dm_gui_mixin_extraction_preserves_public_api(self):
        """TASK-008: ClientGUI and DM_GUI inherit extracted mixins cleanly and keep mock targets."""
        import client.client as client_mod
        from client.network_handlers import ClientNetworkHandlersMixin
        import server.dm_gui as dm_mod
        from server.dm_campaign_session_mixin import DMCampaignSessionMixin

        self.assertTrue(issubclass(client_mod.ClientGUI, ClientNetworkHandlersMixin))
        self.assertTrue(issubclass(dm_mod.DM_GUI, DMCampaignSessionMixin))

        client_spec = MagicMock(spec=client_mod.ClientGUI)
        for attr in (
            "_get_asset_cache",
            "_store_asset_in_cache",
            "_resolve_cached_map_assets",
            "_resolve_cached_handout_assets",
            "_prune_stale_audio_downloads",
            "handle_handout_broadcast",
            "handle_audio_track_chunk",
            "handle_chat_broadcast",
            "handle_dice_roll",
            "export_session_log",
        ):
            self.assertTrue(hasattr(client_mod.ClientGUI, attr), f"Missing ClientGUI.{attr}")
            self.assertTrue(hasattr(client_spec, attr), f"Missing MagicMock(spec=ClientGUI).{attr}")

        dm_spec = MagicMock(spec=dm_mod.DM_GUI)
        for attr in (
            "load_map_from_file",
            "save_session",
            "load_session",
            "open_session_password_dialog",
            "open_new_campaign_dialog",
            "open_campaign_editor_dialog",
            "switch_campaign_scene_dialog",
            "prompt_currency_approval",
            "prompt_item_approval",
            "prompt_journal_approval",
            "prompt_custom_spell_approval",
        ):
            self.assertTrue(hasattr(dm_mod.DM_GUI, attr), f"Missing DM_GUI.{attr}")
            self.assertTrue(hasattr(dm_spec, attr), f"Missing MagicMock(spec=DM_GUI).{attr}")

        for client_patch_target in ("ClientNetwork", "AudioManager", "VoiceClient", "LoginDialog", "time"):
            self.assertTrue(hasattr(client_mod, client_patch_target))
        for dm_patch_target in ("Server", "AudioManager", "VoiceClient"):
            self.assertTrue(hasattr(dm_mod, dm_patch_target))


class TestPhase2ProductMaturityAndE2E(unittest.TestCase):
    """TASK-009 .. TASK-012: Post-review hardening, combat/spell integration, and session/tabletop E2E."""

    def test_task009_join_password_redacted_in_server_logs(self):
        import contextlib
        import io
        import socket
        from server.network import Server
        from common.network_utils import send_message, receive_message
        from common.protocol import make_join

        srv = Server(host="127.0.0.1", port=0, gui_queue=queue.Queue())
        srv.set_session_password("SuperSegreto99")
        try:
            s_client, s_srv = socket.socketpair()
            s_client.settimeout(2.0)
            s_srv.settimeout(2.0)
            out_buf = io.StringIO()
            t_buf = [None]

            def _run_srv():
                with contextlib.redirect_stdout(out_buf):
                    srv.handle_client(s_srv, ("127.0.0.1", 55555))

            import threading
            t = threading.Thread(target=_run_srv, daemon=True)
            t.start()
            send_message(s_client, make_join("RedactedHero", password="SuperSegreto99"))
            resp = receive_message(s_client)
            self.assertEqual(resp.get("type"), "GAME_STATE")
            s_client.close()
            t.join(timeout=2.0)
            logs = out_buf.getvalue()
            self.assertNotIn("SuperSegreto99", logs)
            self.assertIn("***", logs)
            _ = t_buf
        finally:
            srv.stop()

    def test_task009_inplace_asset_mutation_and_bounded_lru_sync(self):
        import base64
        from common.network_utils import MAX_TRACKED_SENT_ASSET_HASHES, broadcast, compute_asset_hash, sanitize_map_for_players
        from common.protocol import make_game_state, make_handout_broadcast
        from client.client import ClientGUI

        b64_a = base64.b64encode(b"MAP_IMAGE_V1").decode("ascii")
        b64_b = base64.b64encode(b"MAP_IMAGE_V2_MUTATED").decode("ascii")
        hash_a = compute_asset_hash(b64_a)
        hash_b = compute_asset_hash(b64_b)

        gs = GameState(queue.Queue())
        p1 = Player("P1", conn=object())
        gs.players = [p1]
        gs.current_map = {"name": "Arena", "bg_image_data": b64_a, "bg_image_hash": hash_a, "hexes": {}}

        delivered = []
        with patch("common.network_utils.send_message", side_effect=lambda c, m: delivered.append(m)):
            # Mutazione in-place del blob senza azzerare il vecchio bg_image_hash
            gs.current_map["bg_image_data"] = b64_b
            san = sanitize_map_for_players(gs.current_map)
            self.assertEqual(san["bg_image_hash"], hash_b)

            p1._sent_asset_hashes = {hash_a: True}
            broadcast(gs, make_game_state(gs.get_state_dict(is_dm=False)))
            pkt = delivered[-1]
            self.assertEqual(pkt["data"]["map"]["bg_image_data"], b64_b)
            self.assertEqual(pkt["data"]["map"]["bg_image_hash"], hash_b)

            # Saturazione oltre 32 asset: il server mantiene <= 24 hash e ritrasmette asset #0 una volta evicted
            c_mock = MagicMock()
            c_mock.name = "P1"
            c_mock.active_character = None
            c_mock._asset_cache = {}
            c_mock._MAX_ASSET_CACHE_ENTRIES = 32
            c_mock.local_map_data = None
            first_blob = base64.b64encode(b"ASSET_0").decode("ascii")
            for idx in range(36):
                blob = base64.b64encode(f"ASSET_{idx}".encode("ascii")).decode("ascii")
                gs.current_map = {"name": f"M{idx}", "bg_image_data": blob, "hexes": {}}
                broadcast(gs, make_game_state(gs.get_state_dict(is_dm=False)))
                ClientGUI._resolve_cached_map_assets(c_mock, delivered[-1]["data"]["map"])

            self.assertLessEqual(len(p1._sent_asset_hashes), MAX_TRACKED_SENT_ASSET_HASHES)
            self.assertLessEqual(len(c_mock._asset_cache), 32)
            # Asset #0 e' stato evitto sia lato server sia lato client -> server lo reinvia completo
            gs.current_map = {"name": "M0", "bg_image_data": first_blob, "hexes": {}}
            broadcast(gs, make_game_state(gs.get_state_dict(is_dm=False)))
            self.assertEqual(delivered[-1]["data"]["map"]["bg_image_data"], first_blob)

            # Mutazione in-place su handout
            h_mut = make_handout_broadcast("Foglio", b64_a)["data"]
            h_mut["image_hash"] = hash_a
            h_mut["image_b64"] = b64_b
            broadcast(gs, {"type": "HANDOUT_BROADCAST", "data": h_mut})
            self.assertEqual(delivered[-1]["data"]["image_b64"], b64_b)
            self.assertEqual(delivered[-1]["data"]["image_hash"], hash_b)

    def test_task010_combat_extra_attack_lock_cunning_and_action_surge_sync(self):
        from server.rules.combat import handle_attack_request, handle_dash_request
        from server.rules.class_abilities import handle_class_feature_request
        from client.client import ClientGUI

        gs = GameState(queue.Queue())
        gs.combat_active = True
        gs.automation_settings["strict_turn_lock"] = True

        fighter = Player("Garrick", conn=_MockConn())
        fighter.is_party_member = True
        fighter.position = [0, 0]
        fighter.combat_initiative = 20
        fighter.full_sheet = {
            "name": "Garrick",
            "char_class": "Guerriero",
            "level": 5,
            "classes": {"Guerriero": 5},
            "class_resources": {"action_surge": True, "second_wind": True},
        }
        goblin = Player("Goblin", conn=None)
        goblin.hp = 100
        goblin.max_hp = 100
        goblin.ac = 5
        goblin.position = [1, 0]
        goblin.combat_initiative = 5
        gs.players = [fighter, goblin]
        gs.turn_index = 0

        # 1. Attacco 1 e Attacco 2 consentiti (Extra Attack = 2); Attacco 3 bloccato
        handle_attack_request({"target_name": "Goblin", "weapon_name": "Spada", "hit_bonus": 15, "damage_formula": "1d4"}, fighter, gs)
        self.assertEqual(fighter.attacks_made_this_turn, 1)
        self.assertFalse(fighter.has_acted_this_turn)

        handle_attack_request({"target_name": "Goblin", "weapon_name": "Spada", "hit_bonus": 15, "damage_formula": "1d4"}, fighter, gs)
        self.assertEqual(fighter.attacks_made_this_turn, 2)
        self.assertTrue(fighter.has_acted_this_turn)

        fighter.conn.sent.clear()
        handle_attack_request({"target_name": "Goblin", "weapon_name": "Spada", "hit_bonus": 15, "damage_formula": "1d4"}, fighter, gs)
        self.assertTrue(fighter.conn.sent, "Expected third attack after max_attacks to be rejected")

        # 2. Azione tattica standard (Scatto) bloccata una volta consumata l'Azione principale
        fighter.conn.sent.clear()
        handle_dash_request({}, fighter, gs)
        self.assertTrue(fighter.conn.sent, "Expected standard Dash to be rejected after Action spent")

        # 3. Action Surge ripristina Azione e contatore attacchi
        handle_class_feature_request({"feature": "action_surge"}, fighter, gs)
        self.assertFalse(fighter.has_acted_this_turn)
        self.assertEqual(fighter.attacks_made_this_turn, 0)
        handle_attack_request({"target_name": "Goblin", "weapon_name": "Spada", "hit_bonus": 15, "damage_formula": "1d4"}, fighter, gs)
        self.assertEqual(fighter.attacks_made_this_turn, 1)

        # 4. Second Wind cura HP e consuma Azione Bonus
        fighter.hp = 10
        fighter.max_hp = 40
        handle_class_feature_request({"feature": "second_wind", "heal_amount": 12}, fighter, gs)
        self.assertEqual(fighter.hp, 22)
        self.assertTrue(fighter.bonus_action_used_this_turn)

        # 5. Serializzazione Player.to_dict / from_dict dei campi economia turno
        rt = Player.from_dict(fighter.to_dict())
        self.assertEqual(rt.attacks_made_this_turn, 1)
        self.assertTrue(rt.bonus_action_used_this_turn)

        # 6. ClientGUI Extra Attack, Cunning Action bonus packet, e handle_game_state sync
        c = MagicMock()
        c.name = "Garrick"
        c.is_connected = True
        c.combat_active = True
        c._is_my_turn = True
        c.action_spent = False
        c.bonus_spent = False
        c.reaction_spent = False
        c._attacks_made_this_turn = 0
        c.movement_spent_ft = 0
        c.active_character = SimpleNamespace(char_class="Guerriero", level=5, classes={"Guerriero": 5}, features="", features_list=[])
        c.players_data = {"Goblin": {"name": "Goblin", "position": [1, 0]}}
        c.map_canvas = SimpleNamespace(current_target_name="Goblin")
        c.network = MagicMock()

        ClientGUI.on_attack_action(c, "Spada", 5, "1d8+3")
        self.assertFalse(c.action_spent)
        self.assertEqual(c._attacks_made_this_turn, 1)
        ClientGUI.on_attack_action(c, "Spada", 5, "1d8+3")
        self.assertTrue(c.action_spent)
        self.assertEqual(c._attacks_made_this_turn, 2)

        # Cunning Action su Ladro Lv 2 invia CUNNING_ACTION_REQUEST
        c.active_character = SimpleNamespace(char_class="Ladro", level=2, classes={"Ladro": 2}, features="", features_list=[])
        c.action_spent = True
        c.bonus_spent = False
        c.network.send.reset_mock()
        ClientGUI.perform_dash(c)
        sent_pkt = c.network.send.call_args[0][0]
        self.assertEqual(sent_pkt["type"], "CUNNING_ACTION_REQUEST")
        self.assertEqual(sent_pkt["data"]["sub_action"], "dash")

    def test_task011_sheet_spellcasting_charges_attack_slots_and_syncs_server(self):
        from client.character_manager import Character
        from client.character_sheet_ui import CharacterSheetFrame
        from client.client import ClientGUI
        from server.rules.class_abilities import handle_cast_special_spell_request

        root = tk.Tk()
        root.withdraw()
        try:
            wizard_char = Character(name="Elara", char_class="Mago", level=3)
            wizard_char.spell_slots["1"] = {"max": 4, "current": 2}
            wizard_char.spellbook = [
                {
                    "name": "Dardo Incantato",
                    "level": 1,
                    "time": "1 azione",
                    "range": "120 ft",
                    "school": "Invocazione",
                    "duration": "Istantanea",
                    "components": "V, S",
                    "damage_formula": "1d4+1",
                    "prepared": True,
                    "desc": "Tre dardi di forza colpiscono automaticamente.",
                },
                {
                    "name": "Dardo Tracciante",
                    "level": 1,
                    "time": "1 azione",
                    "range": "120 ft",
                    "school": "Invocazione",
                    "duration": "1 round",
                    "components": "V, S",
                    "damage_formula": "4d6",
                    "prepared": True,
                    "desc": "Un lampo di luce infligge 4d6 danni radiosi.",
                },
            ]

            c_mock = MagicMock()
            c_mock.name = "Elara"
            c_mock.is_connected = True
            c_mock.combat_active = True
            c_mock.action_spent = False
            c_mock.bonus_spent = False
            c_mock.reaction_spent = False
            c_mock.active_character = wizard_char
            c_mock.map_canvas = SimpleNamespace(current_target_name="Goblin")
            c_mock.network = MagicMock()

            sent_packets = []
            c_mock.network.send.side_effect = lambda p: sent_packets.append(p)

            attacks_received = []
            frame = CharacterSheetFrame(
                root,
                wizard_char,
                manager=None,
                roll_callback=lambda *a: None,
                attack_callback=lambda *a, **kw: attacks_received.append((a, kw)),
                cast_spell_callback=lambda *a, **kw: ClientGUI.on_sheet_cast_spell(c_mock, *a, **kw),
                is_connected=True,
            )

            # 1. Attacca Bersaglio con incantesimo di 1° livello ('Dardo Tracciante') DEVE consumare lo slot (2 -> 1)
            item_ids = frame.spell_tree.get_children()
            frame.spell_tree.selection_set(item_ids[1])
            with patch("tkinter.Toplevel.grab_set"), patch("tkinter.simpledialog.askstring", side_effect=["+5", "4d6"]):
                frame.cast_spell()
                dlg = [w for w in frame.winfo_children() if isinstance(w, tk.Toplevel)][-1]
                atk_btn = next(
                    b for child in dlg.winfo_children()
                    if isinstance(child, ttk.Frame)
                    for b in child.winfo_children()
                    if isinstance(b, ttk.Button) and "Attacca" in str(b.cget("text"))
                )
                atk_btn.invoke()

            self.assertEqual(wizard_char.spell_slots["1"]["current"], 1)
            self.assertEqual(len(attacks_received), 1)
            self.assertTrue(attacks_received[0][1].get("is_spell"))

            # 2. Lancia in Chat su 'Dardo Incantato' consuma slot (1 -> 0) e invia CAST_SPECIAL_SPELL_REQUEST al server
            sent_packets.clear()
            c_mock.action_spent = False
            frame.spell_tree.selection_set(item_ids[0])
            with patch("tkinter.Toplevel.grab_set"):
                frame.cast_spell()
                dlg = [w for w in frame.winfo_children() if isinstance(w, tk.Toplevel)][-1]
                cast_btn = next(
                    b for child in dlg.winfo_children()
                    if isinstance(child, ttk.Frame)
                    for b in child.winfo_children()
                    if isinstance(b, ttk.Button) and "Lancia" in str(b.cget("text"))
                )
                cast_btn.invoke()

            self.assertEqual(wizard_char.spell_slots["1"]["current"], 0)
            self.assertTrue(c_mock.action_spent)
            spell_pkts = [p for p in sent_packets if p.get("type") == "CAST_SPECIAL_SPELL_REQUEST"]
            self.assertEqual(len(spell_pkts), 1)
            self.assertTrue(spell_pkts[0]["data"].get("already_consumed_slot"))

            # 3. Il server risolve il pacchetto senza doppio consumo di slot e colpisce il Goblin
            gs = GameState(queue.Queue())
            srv_wiz = Player("Elara", conn=_MockConn())
            srv_wiz.is_party_member = True
            srv_wiz.full_sheet = wizard_char.to_dict()
            srv_gob = Player("Goblin", conn=None)
            srv_gob.hp = 30
            srv_gob.max_hp = 30
            gs.players = [srv_wiz, srv_gob]
            handle_cast_special_spell_request(spell_pkts[0]["data"], srv_wiz, gs)
            self.assertLess(srv_gob.hp, 30)
            self.assertEqual(srv_wiz.full_sheet["spell_slots"]["1"]["current"], 0)
        finally:
            root.destroy()

    def test_task012_lossless_session_persistence_and_tabletop_local_pc_import(self):
        import tempfile
        from client.character_manager import Character
        from server.dm_campaign_session_mixin import import_party_character_to_game_state

        gs = GameState(queue.Queue())
        gs.maps = {
            "Taverna": {"name": "Taverna", "hexes": {}},
            "Cripta": {"name": "Cripta", "hexes": {"1,1": {"difficult": True}}},
        }
        gs.active_map_id = "Cripta"
        gs.current_map = gs.maps["Cripta"]
        gs.pending_legendary_resistances = {"req-1": {"monster": "Drago", "save": "DES"}}
        gs.campaign_starter_kit = {"gold": 50}

        hero = Character(name="Thorin", char_class="Warlock", level=5, race="Nano")
        hero.hp_max = 42
        hero.hp_current = 37
        hero.attributes["DES"] = 14
        hero.pact_slots = {"current": 2, "max": 2, "level": 3}

        p = import_party_character_to_game_state(gs, hero)
        self.assertTrue(p.is_party_member)
        self.assertEqual(p.hp, 37)
        self.assertEqual(p.max_hp, 42)
        self.assertEqual(p.initiative_bonus, 2)
        self.assertEqual(p.pact_slots_max, 2)
        self.assertEqual(p.pact_slots_current, 2)
        self.assertEqual(p.pact_slot_level, 3)
        self.assertTrue(p.has_darkvision)

        p.attacks_made_this_turn = 1
        p.movement_spent_this_turn = 3
        p.pact_slots_current = 1
        p.honor = 15
        p.sanity = 8

        with tempfile.TemporaryDirectory() as tmpdir:
            sess_file = os.path.join(tmpdir, "session_test.json")
            gs.save_session(sess_file)

            gs2 = GameState(queue.Queue())
            live_sock = _MockConn()
            live_thorin = Player("Thorin", addr=("127.0.0.1", 12345), conn=live_sock)
            live_thorin._sent_asset_hashes = {"keep_hash": True}
            gs2.players = [live_thorin]

            gs2.load_session(sess_file)
            self.assertEqual(set(gs2.maps.keys()), {"Taverna", "Cripta"})
            self.assertEqual(gs2.active_map_id, "Cripta")
            self.assertEqual(gs2.pending_legendary_resistances, {"req-1": {"monster": "Drago", "save": "DES"}})
            self.assertEqual(gs2.campaign_starter_kit, {"gold": 50})

            reloaded = gs2.find_player("Thorin")
            self.assertIs(reloaded.conn, live_sock)
            self.assertEqual(reloaded._sent_asset_hashes, {"keep_hash": True})
            self.assertEqual(reloaded.attacks_made_this_turn, 1)
            self.assertEqual(reloaded.movement_spent_this_turn, 3)
            self.assertEqual(reloaded.pact_slots_current, 1)
            self.assertEqual(reloaded.honor, 15)
            self.assertEqual(reloaded.sanity, 8)


class TestTask036UxSecurityAndManualsTests(unittest.TestCase):
    @staticmethod
    def _contrast_ratio(hex1: str, hex2: str) -> float:
        def _lum(hx: str) -> float:
            hx = hx.lstrip("#")
            vals = []
            for idx in (0, 2, 4):
                c = int(hx[idx:idx + 2], 16) / 255.0
                vals.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
            return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]

        l1, l2 = _lum(hex1), _lum(hex2)
        hi, lo = max(l1, l2), min(l1, l2)
        return (hi + 0.05) / (lo + 0.05)

    def test_theme_disabled_button_contrast_and_dice_banner_i18n_en_it(self):
        import tkinter as tk
        import ttkbootstrap as tb
        from common.theme import setup_theme
        from common.i18n import get_language, set_language
        from components.dice_3d_canvas import Dice3DOverlay

        prev_lang = get_language()
        root = tk.Tk()
        root.withdraw()
        try:
            setup_theme(root)
            style = tb.Style.instance
            self.assertIsNotNone(style)
            for sname in ("TButton", "Gold.TButton", "Accent.TButton", "Secondary.TButton", "Primary.TButton", "Hud.TButton", "SlotFilled.TButton"):
                bg_map = dict(style.map(sname, "background"))
                fg_map = dict(style.map(sname, "foreground"))
                self.assertIn("disabled", bg_map, sname)
                self.assertIn("disabled", fg_map, sname)
                self.assertGreaterEqual(self._contrast_ratio(bg_map["disabled"], fg_map["disabled"]), 4.5, sname)

            canvas = tk.Canvas(root, width=640, height=480)
            ov = Dice3DOverlay(canvas, sound_enabled=False)

            def _canvas_texts():
                return [canvas.itemcget(item, "text") for item in canvas.find_all() if canvas.type(item) == "text"]

            set_language("it")
            ov.banner_info = {"player": "", "reason": "Tiro", "formula": "1d20", "total": 20, "rolls": [20], "other_rolls": [4], "modifier": 0, "is_crit": True, "is_fumble": False}
            ov._render_result_banner(640, 480)
            txt_it = " ".join(_canvas_texts())
            self.assertIn("Giocatore", txt_it)
            self.assertIn("scartato", txt_it)
            self.assertIn("20 NATURALE - SUCCESSO CRITICO!", txt_it)

            canvas.delete("all")
            set_language("en")
            ov.banner_info = {"player": "", "reason": "Check", "formula": "1d100", "total": 100, "rolls": [100], "other_rolls": [12], "modifier": 0, "is_crit": True, "is_fumble": False}
            ov._render_result_banner(640, 480)
            txt_en = " ".join(_canvas_texts())
            self.assertIn("Player", txt_en)
            self.assertIn("discarded", txt_en)
            self.assertIn("NATURAL 100 - CRITICAL SUCCESS!", txt_en)

            canvas.delete("all")
            ov.banner_info = {"player": "Aria", "reason": "Save", "formula": "1d20", "total": 1, "rolls": [1], "other_rolls": [], "modifier": 0, "is_crit": False, "is_fumble": True}
            ov._render_result_banner(640, 480)
            self.assertIn("NATURAL 1 - CRITICAL FAILURE!", " ".join(_canvas_texts()))

            canvas.delete("all")
            ov.banner_info = {"player": "Aria", "reason": "Skill", "formula": "1d20", "total": 11, "rolls": [11], "other_rolls": [], "modifier": 0, "is_crit": False, "is_fumble": False}
            ov._render_result_banner(640, 480)
            self.assertIn("Click to close immediately", " ".join(_canvas_texts()))
        finally:
            set_language(prev_lang)
            try:
                root.destroy()
            except Exception:
                pass

    def test_journal_and_character_dm_privilege_rejection_and_spoof_guards(self):
        from server.rules.journal import handle_new_journal_session_request, handle_conclude_journal_session_request
        from server.rules.character import handle_set_elevation_request, handle_update_stats_request

        gs = GameState(queue.Queue())
        s0 = gs.campaign_journal.get_active_session()
        initial_count = len(gs.campaign_journal.sessions)

        rogue = Player("Rogue", conn=_MockConn())
        rogue.role = "PLAYER"
        rogue.hp = 12
        rogue.max_hp = 30
        rogue.conditions = ["Avvelenato"]
        rogue._preserve_server_state_on_join = True
        rogue._preserve_stats_on_join = True

        ally = Player("Paladin", conn=_MockConn())
        ally.elevation = 0
        gs.players = [rogue, ally]

        # 1. journal.py: non-DM cannot open or conclude sessions
        handle_new_journal_session_request({"title": "Illegale"}, rogue, gs)
        self.assertEqual(len(gs.campaign_journal.sessions), initial_count)
        handle_conclude_journal_session_request({}, rogue, gs)
        self.assertFalse(getattr(s0, "concluded", False) or bool(getattr(s0, "ended_at", "")))
        self.assertGreaterEqual(len(rogue.conn.sent), 2)

        # 2. character.py: non-DM cannot alter another actor's elevation, nor bypass server-protected HP
        handle_set_elevation_request({"target_name": "Paladin", "elevation": 40}, rogue, gs)
        self.assertEqual(ally.elevation, 0)
        handle_set_elevation_request({"target_name": "Rogue", "elevation": 15}, rogue, gs)
        self.assertEqual(rogue.elevation, 15)

        handle_update_stats_request({"hp": 30, "max_hp": 30, "temp_hp": 10, "conditions": []}, rogue, gs)
        self.assertEqual(rogue.hp, 12)
        self.assertIn("Avvelenato", rogue.conditions)

    def test_audio_library_security_bounds_traversal_extension_size_and_chunks(self):
        import tempfile
        import server.audio_library as al_mod
        from client.client import ClientGUI

        with tempfile.TemporaryDirectory() as tmpdir:
            lib_dir = os.path.join(tmpdir, "lib")
            idx_file = os.path.join(lib_dir, "library.json")
            with patch.object(al_mod, "LIB_DIR", lib_dir), \
                 patch.object(al_mod, "INDEX_FILE", idx_file), \
                 patch.object(al_mod, "CHUNK_SIZE", 10):
                lib = al_mod.AudioLibrary()

                # Path traversal rejection
                bad_path = lib._file_for({"id": "../../etc/passwd", "ext": ".mp3"})
                self.assertEqual(os.path.basename(bad_path), "__invalid__")
                self.assertIsNone(lib.get("../secret"))
                self.assertIsNone(lib.get_path("..\\secret"))
                self.assertEqual(list(lib.iter_chunks("bad/id")), [])

                # Bad extension rejection
                exe_path = os.path.join(tmpdir, "bad.exe")
                with open(exe_path, "wb") as f:
                    f.write(b"MZ90")
                with self.assertRaises(ValueError):
                    lib.import_file(exe_path)

                # Oversized file rejection
                wav_path = os.path.join(tmpdir, "huge.wav")
                with open(wav_path, "wb") as f:
                    f.write(b"RIFF" + b"A" * 21)
                with patch.object(al_mod.os.path, "getsize", return_value=al_mod.MAX_FILE_SIZE + 1):
                    with self.assertRaises(ValueError):
                        lib.import_file(wav_path)

                # Valid import + chunk iteration bounds (25 bytes -> 10, 10, 5)
                with patch.object(al_mod, "get_audio_info", return_value=(12.0, 44100, 1)):
                    trk = lib.import_file(wav_path)
                chunks = list(lib.iter_chunks(trk["id"]))
                self.assertEqual([(i, t, len(b)) for i, t, b in chunks], [(0, 3, 10), (1, 3, 10), (2, 3, 5)])
                self.assertEqual(b"".join(b for _, _, b in chunks), b"RIFF" + b"A" * 21)

            # Client URL schemes + traversal track_id bounds
            c_mock = MagicMock()
            c_mock.audio_cache_dir = tmpdir
            c_mock._audio_downloads = {}
            with patch("webbrowser.open") as mock_open:
                for bad_url in ("data:text/html,<script>", "vbscript:msgbox(1)", "ftp://evil/x.mp3"):
                    ClientGUI.handle_audio_play(c_mock, {"url": bad_url})
                mock_open.assert_not_called()
            ClientGUI.handle_audio_track_chunk(c_mock, {"track_id": "../evil", "index": 0, "total": 1, "data": "QUJD", "ext": ".mp3"})
            self.assertEqual(c_mock._audio_downloads, {})

    def test_manuals_ui_open_pdf_and_manuals_folder_actions(self):
        import tempfile
        import subprocess
        from client.manuals_ui import ManualsDialog
        import common.pdf_manuals_indexer as pdf_idx

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_dir = os.path.join(tmpdir, "pdfs")
            stub = MagicMock()
            with patch.object(pdf_idx, "PDF_DIR", pdf_dir):
                with patch("os.name", "nt"), patch("os.startfile", create=True) as mock_start:
                    ManualsDialog.open_pdf_folder(stub)
                    self.assertTrue(os.path.isdir(pdf_dir))
                    mock_start.assert_called_once_with(pdf_dir)

                with patch("os.name", "posix"), patch.object(subprocess, "Popen") as mock_popen:
                    ManualsDialog.open_pdf_folder(stub)
                    mock_popen.assert_called_once_with(["xdg-open", pdf_dir])

                with patch("os.name", "nt"), \
                     patch("os.startfile", side_effect=OSError("no shell"), create=True), \
                     patch("client.manuals_ui.messagebox.showinfo") as mock_info:
                    ManualsDialog.open_pdf_folder(stub)
                    mock_info.assert_called_once()
                    self.assertIn(pdf_dir, mock_info.call_args[0][1])

                man_dir = os.path.join(tmpdir, "manuals")
                with patch("client.manuals_ui.MANUALS_DIR", man_dir), \
                     patch("os.name", "posix"), \
                     patch.object(subprocess, "Popen") as mock_popen:
                    ManualsDialog.open_manuals_folder(stub)
                    self.assertTrue(os.path.isdir(man_dir))
                    mock_popen.assert_called_once_with(["xdg-open", man_dir])


if __name__ == "__main__":
    unittest.main()
