"""tests/test_phase5b_scenarios_e2e.py - TASK-037 Realistic Gameplay Acceptance Suite (Scenarios A-E)."""

import base64
import gc
import json
import os
import queue
import socket
import sys
import tempfile
import threading
import time
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["DND_MOCK_AUDIO"] = "1"

from common.character_schema import format_hit_dice_summary, sync_hit_dice_pools
from common.feats_and_classes import apply_half_feat_bonus, check_feat_prerequisites
from common.game_state import GameState, Player
from common.hex_utils import Hex
from common.network_utils import broadcast, compute_asset_hash, compute_hexes_hash, receive_message, sanitize_map_for_players
from common.protocol import (
    make_attack_request,
    make_death_save_request,
    make_game_state,
    make_join,
    make_short_rest_request,
    make_update_stats_request,
)
from common.spell_effects_engine import cast_iconic_spell, get_spell_ac_bonus


def _make_root() -> tk.Tk:
    root = tk.Tk()
    root.withdraw()
    return root


def _drain_queue(q: queue.Queue):
    items = []
    while True:
        try:
            items.append(q.get_nowait())
        except queue.Empty:
            break
    return items


def _wait_until(predicate, timeout: float = 3.0, interval: float = 0.02):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        res = predicate()
        if res:
            return res
        time.sleep(interval)
    return predicate()


def _make_actor(name: str, hp: int = 30, max_hp: int = 30, ac: int = 15, pos=(0, 0), is_party: bool = True, sheet=None) -> Player:
    p = Player(name)
    p.is_party_member = is_party
    p.is_npc = not is_party
    p.role = "player" if is_party else "npc"
    p.hp = hp
    p.max_hp = max_hp
    p.ac = ac
    p.position = list(pos)
    p.conditions = []
    p.active_effects = []
    p.death_saves = {"successes": 0, "failures": 0}
    p.full_sheet = sheet if sheet is not None else {}
    return p


class TestPhase5BRealisticScenariosE2E(unittest.TestCase):
    """Realistic 5e acceptance workflows (Scenarios A-E) across VTT subsystems."""

    def test_scenario_a_tactical_combat_aoe_elevation_concentration_ammo_boss_and_victory(self):
        from server.commands import command_handlers
        from server.dm_monster_engine import execute_monster_multiattack
        from server.rules.character import handle_update_full_sheet_request
        from server.rules.combat import (
            apply_damage,
            handle_attack_request,
            handle_spend_legendary_action_request,
        )
        from server.rules.map_interaction import handle_clear_aoes_request, handle_create_aoe_request

        gs = GameState(queue.Queue())
        gs.combat_active = True
        gs.current_map = {
            "name": "Cripta del Drago",
            "grid_type": "square",
            "width": 12,
            "height": 12,
            "walls": [],
            "doors": [],
            "fow_enabled": False,
        }

        fighter = _make_actor(
            "Kaelen",
            hp=44,
            max_hp=44,
            ac=16,
            pos=(1, 0),
            sheet={
                "name": "Kaelen",
                "char_class": "Guerriero",
                "level": 5,
                "attributes": {"FOR": 16, "DES": 14, "COS": 14},
                "inventory_grid": [{"name": "Frecce", "qty": 20}],
                "starting_kit_applied": True,
                "campaign_starter_received": True,
            },
        )
        cleric = _make_actor(
            "Kyra",
            hp=32,
            max_hp=32,
            ac=18,
            pos=(0, 1),
            sheet={"name": "Kyra", "char_class": "Chierico", "level": 5, "attributes": {"COS": 14, "SAG": 18}},
        )
        wizard = _make_actor(
            "Elara",
            hp=28,
            max_hp=28,
            ac=12,
            pos=(0, 0),
            sheet={"name": "Elara", "char_class": "Mago", "level": 5, "attributes": {"INT": 18, "COS": 12}},
        )
        minion = _make_actor("Kobold", hp=24, max_hp=24, ac=12, pos=(5, 0), is_party=False)
        minion.elevation = 0
        boss = _make_actor(
            "Drago Giovane",
            hp=85,
            max_hp=85,
            ac=15,
            pos=(5, 0),
            is_party=False,
            sheet={
                "is_npc": True,
                "damage_resistances": [],
                "actions": [
                    {"name": "Multiattacco", "desc": "Multiattacco: 1 Morso e 1 Artiglio"},
                    {"name": "Morso", "attack_bonus": 8, "damage_dice": "1d10+4", "desc": "Colpito: (1d10+4) danni perforanti."},
                    {"name": "Artiglio", "attack_bonus": 8, "damage_dice": "1d8+4", "desc": "Colpito: (1d8+4) danni taglienti."},
                ],
            },
        )
        boss.elevation = 30
        boss.legendary_actions_max = 3
        boss.legendary_actions_current = 3

        gs.players = [fighter, cleric, wizard, minion, boss]

        # 1. Cleric casts Shield of Faith (+2 dynamic AC, concentration on Kyra)
        ok_sof = cast_iconic_spell(cleric, fighter, "Scudo della Fede", 1, gs)
        self.assertTrue(ok_sof)
        self.assertEqual(get_spell_ac_bonus(fighter), 2)
        self.assertEqual(cleric.concentrating_on, "Scudo della Fede")

        # 2. Fighter shoots Longbow arrow consuming 1 ammo (20 -> 19) without inflation
        with patch("common.dice.random.randint", return_value=14), patch("server.rules.combat.random.randint", return_value=14):
            handle_attack_request(
                make_attack_request("Drago Giovane", "Arco Lungo", 7, "1d8+3", damage_type="Perforante", is_ranged=True)["data"],
                fighter,
                gs,
            )
        self.assertEqual(fighter.full_sheet["inventory_grid"][0]["qty"], 19)
        self.assertLess(boss.hp, 85)
        handle_update_full_sheet_request(
            {
                "character": {
                    "attributes": {"FOR": 16, "DES": 14, "COS": 14},
                    "inventory_grid": [{"name": "Frecce", "qty": 20}],
                }
            },
            fighter,
            gs,
        )
        self.assertEqual(fighter.full_sheet["inventory_grid"][0]["qty"], 19)

        # 3. 3D AoE Fireball sphere at elevation 0 radius 2 (10ft) affects ground Minion (z=0) but misses flying Boss (z=30)
        elara_prompts = []
        with patch("server.rules.map_interaction.broadcast"), \
             patch("server.rules.map_interaction.send_message"), \
             patch("common.dice.random.randint", return_value=4):
            minion.conn = MagicMock()
            boss.conn = MagicMock()
            with patch("common.protocol.make_prompt_save", side_effect=lambda *a, **kw: elara_prompts.append(a) or {"type": "PROMPT_SAVE", "data": {}}) as mock_prompt:
                handle_create_aoe_request(
                    {
                        "aoe_data": {
                            "type": "sfera",
                            "origin": [5, 0],
                            "size": 2,
                            "elevation": 0,
                            "req_save": True,
                            "save_stat": "DES",
                            "dc": 15,
                            "dmg": "6d6",
                            "dmg_type": "Fuoco",
                            "concentration": True,
                        }
                    },
                    wizard,
                    gs,
                )
                self.assertEqual(mock_prompt.call_count, 1)
                self.assertEqual(minion.conn.sendall.call_count, 0)  # sent via send_message mock

        # 4. Boss spends 1 Legendary Action, executes Multiattack, then downs Cleric -> concentration breaks (-2 AC)
        dm_actor = Player("DM")
        dm_actor.role = "DM"
        handle_spend_legendary_action_request({"boss_name": "Drago Giovane", "action_name": "Colpo d'Ala", "cost": 1}, dm_actor, gs)
        self.assertEqual(boss.legendary_actions_current, 2)

        with patch("server.dm_monster_engine.roll_dice", return_value={"total": 12, "rolls": [12], "raw_total": 12}):
            ma = execute_monster_multiattack(boss, gs, target=fighter)
        self.assertEqual(len(ma["rolls"]), 2)
        self.assertLess(fighter.hp, 44)

        apply_damage(cleric, 40, "Tagliente", gs)
        self.assertEqual(cleric.hp, 0)
        self.assertIn("Incosciente", cleric.conditions)
        self.assertEqual(get_spell_ac_bonus(fighter), 0)

        # 5. Cleric rolls Natural 20 Death Save -> stands at 1 HP cleanly, then combat concludes
        command_handlers["DEATH_SAVE_REQUEST"](make_death_save_request(manual_roll=20, actor_name="Kyra")["data"], cleric, gs)
        self.assertEqual(cleric.hp, 1)
        self.assertNotIn("Incosciente", cleric.conditions)

        minion.hp = 0
        boss.hp = 0
        gs.end_combat()
        self.assertFalse(gs.combat_active)
        with patch("server.rules.map_interaction.broadcast"):
            handle_clear_aoes_request({}, wizard, gs)
        self.assertEqual(gs.active_aoes, [])

    def test_scenario_b_dungeon_exploration_editor_doors_traps_fow_and_player_display(self):
        from components.ui_components import HexMapCanvas
        from server.dm_gui import DM_GUI
        from server.map_editor import MapEditorWindow
        from server.rules.map_interaction import handle_toggle_door_request
        from server.rules.movement import handle_move_request

        with tempfile.TemporaryDirectory() as td:
            char_file = os.path.join(td, "chars.json")
            with patch.dict(os.environ, {"DND_CHARACTERS_PATH": char_file}):
                root = _make_root()
                try:
                    # 1. Author dungeon layout in MapEditorWindow with Undo/Redo & grid resize
                    editor = MapEditorWindow(root)
                    editor.grid_type_var.set("square")
                    editor.current_grid_type = "square"
                    editor.current_hex_size = 30
                    editor.hex_layout = editor._create_layout(30, "square")
                    editor.resize_grid(6, 4, push_undo=False)

                    px_trap, py_trap = editor.hex_layout.hex_to_pixel(Hex(3, 0))
                    editor._toggle_trap_at(px_trap, py_trap, silent=True, name="Fossa Segreta", dc=14, damage="2d6")
                    px_pin, py_pin = editor.hex_layout.hex_to_pixel(Hex(4, 0))
                    editor._toggle_room_pin_at(px_pin, py_pin, silent=True, title="Tesoro", read_aloud="Un antico forziere brilla.")

                    editor.resize_grid(5, 4, push_undo=True)
                    self.assertEqual(len(editor.grid_hexes), 20)
                    self.assertTrue(editor.undo())
                    self.assertEqual(len(editor.grid_hexes), 24)
                    self.assertTrue(editor.redo())
                    self.assertEqual(len(editor.grid_hexes), 20)
                    editor.destroy()

                    # 2. Load tactical map into DM_GUI server & verify FoW/secrecy filtering
                    with patch("server.network.Server.start"), patch.object(DM_GUI, "process_queue", return_value=None):
                        dm = DM_GUI(root)

                    gs = dm.server.game_state
                    gs.current_map = {
                        "name": "Catacombe",
                        "grid_type": "square",
                        "width": 6,
                        "height": 4,
                        "fow_enabled": True,
                        "fow_revealed": [[0, 0], [1, 0]],
                        "fow_draft": [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]],
                        "walls": [[2, 1], [2, 2]],
                        "doors": [
                            {"q": 2, "r": 0, "state": "closed", "name": "Porta di Ferro"},
                            {"q": 4, "r": 1, "state": "secret", "name": "Passaggio Segreto"},
                        ],
                        "traps": [
                            {"q": 3, "r": 0, "name": "Dardi", "dc": 14, "damage": "1d8", "damage_type": "Perforante", "hidden": True, "secret": True, "detected": False, "triggered": False},
                        ],
                        "room_pins": [{"id": "rp1", "q": 4, "r": 0, "title": "Altare", "read_aloud": "Silenzio tombale."}],
                    }

                    scout = _make_actor("Vex", hp=30, max_hp=30, ac=16, pos=(1, 0), sheet={"attributes": {"DES": 18}})
                    scout.vision_radius = 6
                    hidden_gargoyle = _make_actor("Gargoyle", hp=40, max_hp=40, pos=(4, 0), is_party=False)
                    hidden_gargoyle.is_hidden = True
                    hidden_gargoyle.layer = "gm"
                    gs.players = [scout, hidden_gargoyle]

                    san_map = sanitize_map_for_players(gs.current_map)
                    door_coords = {(d["q"], d["r"]) for d in san_map["doors"]}
                    self.assertIn((2, 0), door_coords)
                    self.assertNotIn((4, 1), door_coords)
                    self.assertEqual(san_map["traps"], [])

                    # 3. Adjacent explorer opens closed door (2,0), steps onto trap (3,0), and memoized canvas updates cleanly
                    with patch("server.rules.map_interaction.broadcast"), patch("server.rules.movement.broadcast"):
                        handle_toggle_door_request({"q": 2, "r": 0}, scout, gs)
                    self.assertEqual(gs.current_map["doors"][0]["state"], "open")
                    self.assertIn([3, 0], gs.current_map["fow_revealed"])

                    with (
                        patch("server.rules.movement.broadcast"),
                        patch("server.rules.combat.broadcast"),
                        patch("common.dice.random.randint", return_value=2),
                    ):
                        handle_move_request({"to": [3, 0]}, scout, gs)
                    self.assertEqual(scout.position, [3, 0])
                    self.assertTrue(gs.current_map["traps"][0]["triggered"])
                    self.assertFalse(gs.current_map["traps"][0]["secret"])

                    # Check Player Display filtering + read-only guard
                    disp_win = dm.open_player_display_window()
                    self.assertFalse(dm.player_display_canvas.is_dm)
                    self.assertIn("Vex", dm.player_display_canvas.players_data)
                    self.assertNotIn("Gargoyle", dm.player_display_canvas.players_data)
                    self.assertFalse(dm.player_display_canvas.can_move_token_callback("Vex", (3, 0), (4, 0)))

                    # Verify FoW memoization avoids recompute on unchanged draws
                    fow_canvas = HexMapCanvas(root)
                    fow_canvas.player_name = "Vex"
                    fow_canvas.players_data = {"Vex": {"name": "Vex", "position": [3, 0], "vision_radius": 6, "light_radius": 0, "conditions": []}}
                    fow_canvas.map_data = {"lights": []}
                    walls_h = {Hex(2, 1)}
                    with patch("components.ui_components.get_visible_hexes", return_value=[Hex(3, 0), Hex(4, 0)]) as m_vis:
                        fow_canvas._compute_player_visible_hexes(False, {(3, 0)}, walls_h, "square")
                        fow_canvas._compute_player_visible_hexes(False, {(3, 0), (4, 0)}, walls_h, "square")
                        self.assertEqual(m_vis.call_count, 1)
                    disp_win.destroy()

                    with patch("server.dm_gui.messagebox.askokcancel", return_value=True):
                        dm.on_closing()
                finally:
                    disp_win = None
                    fow_canvas = None
                    dm = None
                    gc.collect()
                    try:
                        if root.winfo_exists():
                            root.destroy()
                    except tk.TclError:
                        pass
                    gc.collect()

    def test_scenario_c_multiclass_lv1_to_5_prerequisites_half_feat_and_mixed_rests(self):
        from client.character_manager import Character, CharacterManager
        from server.rules.character import _apply_player_long_rest, handle_update_full_sheet_request
        from server.rules.combat import handle_short_rest_request

        with tempfile.TemporaryDirectory() as td:
            char_file = os.path.join(td, "chars.json")
            with patch.dict(os.environ, {"DND_CHARACTERS_PATH": char_file}):
                pc = Character("Alden", char_class="Guerriero", level=1, race="Umano")
                pc.classes = {"Guerriero": 1}
                pc.attributes = {"FOR": 16, "DES": 12, "COS": 13, "INT": 14, "SAG": 10, "CAR": 10}
                pc.saving_throw_proficiencies = ["FOR"]
                pc.hp_max = 11
                pc.hp_current = 11
                pc.starting_kit_applied = True
                sync_hit_dice_pools(pc)

                # 1. Prerequisite check blocks caster feat at Fighter 1
                ok_caster, _ = check_feat_prerequisites(pc.to_dict(), "Incantatore da Guerra (War Caster)")
                self.assertFalse(ok_caster)

                # 2. Level Fighter 1 -> 3 and apply Resilient (COS) Half-Feat (+1 COS & save prof)
                ok_fgt, _ = pc.add_class_level("Guerriero", 2)
                self.assertTrue(ok_fgt)
                sheet_tmp = pc.to_dict()
                apply_half_feat_bonus(sheet_tmp, "Resilient", "COS")
                pc.attributes = sheet_tmp["attributes"]
                pc.saving_throw_proficiencies = sheet_tmp["saving_throw_proficiencies"]
                self.assertEqual(pc.attributes["COS"], 14)
                self.assertIn("COS", pc.saving_throw_proficiencies)

                # 3. Multiclass into Wizard 2 -> Lv5 (d10:3, d6:2)
                ok_wiz, _ = pc.add_class_level("Mago", 2)
                self.assertTrue(ok_wiz)
                self.assertEqual(pc.level, 5)
                self.assertEqual(pc.classes, {"Guerriero": 3, "Mago": 2})
                self.assertEqual(pc.hit_dice_pools, {"d10": {"total": 3, "current": 3}, "d6": {"total": 2, "current": 2}})
                self.assertIn("3/3 d10", format_hit_dice_summary(pc))
                self.assertIn("2/2 d6", format_hit_dice_summary(pc))

                # Caster prerequisite now passes cleanly!
                ok_caster_after, _ = check_feat_prerequisites(pc.to_dict(), "Incantatore da Guerra (War Caster)")
                self.assertTrue(ok_caster_after)

                mgr = CharacterManager()
                mgr.add_character(pc)
                reloaded = mgr.get_character_by_name("Alden")
                self.assertEqual(reloaded.hit_dice_pools, {"d10": {"total": 3, "current": 3}, "d6": {"total": 2, "current": 2}})

                # 4. Sync to Server -> Short Rest spending 1d6 + 1d10 -> Long Rest recovers 5//2 = 2 dice
                gs = GameState(queue.Queue())
                srv_p = _make_actor("Alden", hp=20, max_hp=42, sheet=pc.to_dict())
                gs.players = [srv_p]
                handle_update_full_sheet_request({"character": pc.to_dict()}, srv_p, gs)
                srv_p.hp = 20
                srv_p.max_hp = 42
                srv_p.full_sheet["hp_max"] = 42
                srv_p.full_sheet["hp_current"] = 20

                with patch("server.rules.combat.broadcast"), patch("server.rules.combat.random.randint", return_value=4):
                    handle_short_rest_request(make_short_rest_request(2, 12, die_counts={"d6": 1, "d10": 1})["data"], srv_p, gs)
                self.assertEqual(srv_p.full_sheet["hit_dice_pools"], {"d10": {"total": 3, "current": 2}, "d6": {"total": 2, "current": 1}})
                self.assertEqual(srv_p.full_sheet["hit_dice_current"], 3)
                self.assertEqual(srv_p.hp, 32)  # 20 + (4+2) + (4+2)

                _apply_player_long_rest(srv_p, gs)
                self.assertEqual(srv_p.hp, 42)
                self.assertEqual(sum(v["current"] for v in srv_p.full_sheet["hit_dice_pools"].values()), 5)

    def test_scenario_d_hybrid_tabletop_mode_and_character_manager_writeback(self):
        from client.character_manager import Character, CharacterManager
        from server.dm_campaign_session_mixin import import_party_character_to_game_state
        from server.dm_dialogs import DMPlayerSheetViewer
        from server.dm_gui import DM_GUI

        with tempfile.TemporaryDirectory() as td:
            char_file = os.path.join(td, "chars.json")
            with patch.dict(os.environ, {"DND_CHARACTERS_PATH": char_file}):
                hero = Character(name="Brom", char_class="Chierico", level=4, race="Nano")
                hero.hp_max = 34
                hero.hp_current = 24
                hero.ac = 18
                hero.spell_slots["1"] = {"max": 4, "current": 2}
                hero.custom_resources = [{"name": "Incanalare Divinita", "current": 0, "max": 1, "reset_on": "short"}]
                mgr = CharacterManager()
                mgr.add_character(hero)

                root = _make_root()
                try:
                    with patch("server.network.Server.start"), patch.object(DM_GUI, "process_queue", return_value=None):
                        dm = DM_GUI(root)

                    pc = import_party_character_to_game_state(dm.server.game_state, hero.to_dict(), spawn_pos=[1, 1])
                    gob = _make_actor("Goblin Capo", hp=21, max_hp=21, pos=(3, 1), is_party=False, sheet={"is_npc": True, "initiative": 2})
                    dm.server.game_state.players.append(gob)

                    with patch("random.randint", return_value=13), patch("server.dm_gui.broadcast"):
                        dm.roll_all_npcs_initiative()
                    self.assertEqual(pc.initiative, 0)
                    self.assertGreater(gob.initiative, 0)

                    # Short Rest recharges short-rest resource; interactive DM viewer tests 0 HP + Nat20 stabilize
                    with patch("server.dm_gui.broadcast"):
                        dm.advance_time(1, is_rest=True)
                    self.assertEqual(pc.full_sheet["custom_resources"][0]["current"], 1)

                    viewer = DMPlayerSheetViewer(
                        root,
                        "Brom",
                        pc.full_sheet,
                        game_state=dm.server.game_state,
                        on_change_callback=lambda msg=None: dm._on_dm_sheet_changed("Brom", msg),
                    )
                    viewer._apply_hp_delta(-30)
                    self.assertEqual(pc.hp, 0)
                    self.assertIn("Incosciente", pc.conditions)
                    with patch("server.dm_dialogs.random.randint", return_value=20):
                        viewer.roll_death_save()
                    self.assertEqual(pc.hp, 1)
                    self.assertNotIn("Incosciente", pc.conditions)
                    viewer.destroy()

                    # Writeback saves tabletop state into persistent CharacterManager JSON
                    updated_count = dm.sync_local_party_characters_to_manager()
                    self.assertGreaterEqual(updated_count, 1)
                    mgr2 = CharacterManager()
                    saved_brom = mgr2.get_character_by_name("Brom")
                    self.assertIsNotNone(saved_brom)
                    self.assertEqual(saved_brom.hp_current, 1)
                    self.assertEqual(saved_brom.custom_resources[0]["current"], 1)

                    with patch("server.dm_gui.messagebox.askokcancel", return_value=True):
                        dm.on_closing()
                finally:
                    viewer = None
                    dm = None
                    gc.collect()
                    try:
                        if root.winfo_exists():
                            root.destroy()
                    except tk.TclError:
                        pass
                    gc.collect()

    def test_scenario_e_loopback_tcp_auth_hexes_cache_isolation_and_reconnect(self):
        from client.client import ClientGUI
        from client.network import ClientNetwork
        from server.network import Server

        big_hexes = [{"q": i % 100, "r": i // 100, "terrain": "stone"} for i in range(5000)]
        img_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"M" * 512).decode("ascii")
        exp_hx_hash = compute_hexes_hash(big_hexes)
        exp_bg_hash = compute_asset_hash(img_b64)

        slow_srv, slow_cli = socket.socketpair()
        srv = None
        clients = []
        with patch("server.network.VoiceServer", return_value=MagicMock()):
            srv_q = queue.Queue()
            srv = Server("127.0.0.1", 0, srv_q, session_password="Table5e")
            srv_thread = threading.Thread(target=srv.start, daemon=True)
            srv_thread.start()
            self.assertTrue(_wait_until(lambda: srv.running and srv.server_socket is not None, timeout=3.0))
            port = srv.server_socket.getsockname()[1]

            try:
                gs = srv.game_state
                gs.current_map = {"name": "Torre", "hexes": big_hexes, "bg_image_data": img_b64, "fow_enabled": False}

                # 1. Wrong PIN is rejected
                q_bad = queue.Queue()
                cn_bad = ClientNetwork(q_bad, on_disconnect_callback=lambda: None)
                clients.append(cn_bad)
                cn_bad.connect("127.0.0.1", port)
                cn_bad.send(make_join("Intruder", password="bad"))
                bad_err = _wait_until(lambda: next((m for m in _drain_queue(q_bad) if m.get("type") == "ERROR_REPLY"), None), timeout=3.0)
                self.assertIsNotNone(bad_err)
                cn_bad.disconnect()

                # 2. Healthy client joins with valid PIN -> receives initial GAME_STATE & caches hexes + image
                q_ok = queue.Queue()
                cn_ok = ClientNetwork(q_ok, on_disconnect_callback=lambda: None)
                clients.append(cn_ok)
                cn_ok.connect("127.0.0.1", port)
                cn_ok.send(make_join("Aria", password="Table5e"))
                srv_aria = _wait_until(
                    lambda: (p := gs.find_player("Aria"))
                    and exp_hx_hash in getattr(p, "_sent_asset_hashes", {})
                    and p,
                    timeout=3.0,
                )
                self.assertIsNotNone(srv_aria)

                msg1 = _wait_until(lambda: next((m for m in _drain_queue(q_ok) if m.get("type") == "GAME_STATE"), None), timeout=3.0)
                self.assertIsNotNone(msg1)
                self.assertEqual(len(msg1["data"]["map"]["hexes"]), 5000)

                c_stub = MagicMock()
                c_stub._asset_cache = {}
                c_stub._MAX_ASSET_CACHE_ENTRIES = 32
                c_stub.local_map_data = None
                ClientGUI._resolve_cached_map_assets(c_stub, msg1["data"]["map"])
                self.assertIn(exp_hx_hash, c_stub._asset_cache)
                self.assertIn(exp_bg_hash, c_stub._asset_cache)

                with gs.lock:
                    srv_aria.hp = 27
                    srv_aria.max_hp = 35
                    srv_aria.full_sheet = {
                        "hp_current": 27,
                        "hp_max": 35,
                        "starting_kit_applied": True,
                        "campaign_starter_received": True,
                    }

                # 3. Stalled socket inserted BEFORE Aria does not block 2nd cached broadcast to healthy TCP client
                slow_srv.setblocking(False)
                try:
                    slow_srv.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
                    slow_cli.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
                    while True:
                        slow_srv.send(b"Z" * 4096)
                except OSError:
                    pass
                slow_srv.setblocking(True)
                slow_srv.settimeout(30.0)
                slow_peer = Player("AAA_Stalled", conn=slow_srv)
                with gs.lock:
                    gs.players = [slow_peer, srv_aria]

                _drain_queue(q_ok)
                t0 = time.monotonic()
                broadcast(gs, make_game_state(gs.get_state_dict(is_dm=False)))
                self.assertLess(time.monotonic() - t0, 1.5)
                msg2 = _wait_until(lambda: next((m for m in _drain_queue(q_ok) if m.get("type") == "GAME_STATE"), None), timeout=3.0)
                self.assertIsNotNone(msg2)
                self.assertIsNone(msg2["data"]["map"]["hexes"])
                self.assertTrue(msg2["data"]["map"].get("hexes_cached"))
                self.assertIsNone(msg2["data"]["map"]["bg_image_data"])
                self.assertTrue(msg2["data"]["map"].get("bg_image_cached"))
                ClientGUI._resolve_cached_map_assets(c_stub, msg2["data"]["map"])
                self.assertEqual(len(msg2["data"]["map"]["hexes"]), 5000)

                # 4. Reconnect with known_asset_hashes preserves cache dedup and clamps stale client HP
                with gs.lock:
                    gs.players = [srv_aria]
                cn_ok.disconnect()
                time.sleep(0.1)

                q_rec = queue.Queue()
                cn_rec = ClientNetwork(q_rec, on_disconnect_callback=lambda: None)
                clients.append(cn_rec)
                cn_rec.connect("127.0.0.1", port)
                cn_rec.send(make_join("Aria", password="Table5e", known_asset_hashes=list(c_stub._asset_cache.keys())))
                init_rec = _wait_until(lambda: next((m for m in _drain_queue(q_rec) if m.get("type") == "GAME_STATE"), None), timeout=3.0)
                self.assertIsNotNone(init_rec)
                self.assertIsNone(init_rec["data"]["map"]["hexes"])
                self.assertTrue(init_rec["data"]["map"].get("hexes_cached"))
                self.assertTrue(_wait_until(lambda: srv_aria.conn is not None and exp_hx_hash in getattr(srv_aria, "_sent_asset_hashes", {}), timeout=3.0))

                cn_rec.send(make_update_stats_request(35, 35, 0))
                stats_ack = _wait_until(
                    lambda: next((m for m in _drain_queue(q_rec) if m.get("type") == "PLAYER_STATS_UPDATE"), None),
                    timeout=3.0,
                )
                self.assertIsNotNone(stats_ack)
                self.assertEqual(stats_ack["data"]["hp"], 27)
                self.assertEqual(srv_aria.hp, 27)
            finally:
                for cn in clients:
                    try:
                        cn.disconnect()
                    except Exception:
                        pass
                for s in (slow_srv, slow_cli):
                    try:
                        s.close()
                    except Exception:
                        pass
                if srv is not None:
                    srv.stop()
                srv_thread.join(timeout=2.0)


if __name__ == "__main__":
    unittest.main()
