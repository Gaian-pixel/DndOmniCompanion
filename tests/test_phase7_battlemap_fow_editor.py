"""Phase 7 TASK-050 regression tests: Battlemap Player Display, FoW Secrecy, Square 5-10-5 / 3D Parity & MapEditor."""

import queue
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from common.game_state import GameState, Player
from common.hex_utils import Hex
from components.ui_components import HexMapCanvas
from server.dm_gui import DM_GUI
from server.map_editor import MapEditorWindow
from server.rules.chat import handle_chat
from server.rules.combat import handle_attack_request
from server.rules.inventory import handle_take_loot_request
from server.rules.map_interaction import handle_toggle_door_request
from server.rules.movement import handle_move_request


class TestPhase7BattlemapFoWEditor(unittest.TestCase):
    def test_player_display_window_sync_uses_real_game_state_keys(self):
        gs = GameState(queue.Queue())
        gs.current_map = {
            "grid_type": "square",
            "hexes": [[q, r] for q in range(4) for r in range(4)],
            "fow_enabled": False,
        }
        gs.active_aoes = [{"type": "sfera", "origin": [1, 1], "size": 2, "name": "Sfera Infuocata"}]
        gs.combat_active = True
        gs.automation_settings["auto_day_night_cycle"] = False
        hero = Player("Eroe")
        hero.is_party_member = True
        hero.initiative = 18
        hero.in_combat = True
        gs.players = [hero]

        captured = {}
        fake_canvas = SimpleNamespace(
            is_dm=True,
            update_data=lambda *args, **kwargs: captured.update({"args": args, "kwargs": kwargs}),
        )
        fake_win = SimpleNamespace(winfo_exists=lambda: True)
        fake_dm = SimpleNamespace(
            player_display_window=fake_win,
            player_display_canvas=fake_canvas,
            server=SimpleNamespace(game_state=gs),
        )
        DM_GUI._sync_player_display_window(fake_dm)
        self.assertIsNotNone(captured["args"][0])
        self.assertEqual(len(captured["args"][0]["hexes"]), 16)
        self.assertEqual(captured["kwargs"]["aoes_data"], gs.active_aoes)
        self.assertEqual(captured["kwargs"]["combat_order"], ["Eroe"])
        self.assertFalse(captured["kwargs"]["auto_day_night"])

    def test_dm_move_selected_token_emits_fow_ghost_transitions_without_mutating_draft(self):
        gs = GameState(queue.Queue())
        gs.current_map = {
            "grid_type": "square",
            "fow_enabled": True,
            "fow_revealed": [[0, 0]],
            "fow_draft": [[0, 0]],
            "hexes": [[q, r] for q in range(6) for r in range(6)],
        }
        goblin = Player("Goblin")
        goblin.is_npc = True
        goblin.position = [4, 4]
        gs.players = [goblin]

        sent_msgs = []
        fake_dm = SimpleNamespace(
            server=SimpleNamespace(game_state=gs),
            redraw_map_and_players=MagicMock(),
            log_to_chat=MagicMock(),
        )
        with patch("server.network.broadcast", side_effect=lambda _g, m: sent_msgs.append(m)):
            DM_GUI.move_selected_token_to_hex(fake_dm, "Goblin", Hex(0, 0))
            DM_GUI.move_selected_token_to_hex(fake_dm, "Goblin", Hex(5, 5))
        types = [m.get("type") for m in sent_msgs]
        self.assertIn("PLAYER_JOINED", types)
        self.assertIn("PLAYER_LEFT", types)
        self.assertEqual(gs.current_map["fow_draft"], [[0, 0]])

    def test_doors_gm_fow_isolation_undiscovered_secret_door_and_torch_walls(self):
        gs = GameState(queue.Queue())
        gs.current_map = {
            "grid_type": "square",
            "fow_enabled": True,
            "fow_revealed": [[0, 0]],
            "fow_draft": [[0, 0]],
            "walls": [[2, 0]],
            "doors": [
                {"q": 1, "r": 0, "state": "closed", "name": "Porta Est"},
                {"q": 0, "r": 1, "state": "secret", "is_secret": True, "discovered": False, "name": "Passaggio Tesoro"},
            ],
            "hexes": [[q, r] for q in range(16) for r in range(16)],
        }
        pc = Player("Eroe")
        pc.is_party_member = True
        pc.position = [0, 0]
        pc.vision_radius = 2
        pc.conn = MagicMock()

        gm_dragon = Player("DragoOcculto")
        gm_dragon.is_npc = True
        gm_dragon.layer = "gm"
        gm_dragon.position = [12, 12]
        gm_dragon.vision_radius = 6
        gs.players = [pc, gm_dragon]

        with patch("server.rules.map_interaction.broadcast"), patch("server.rules.map_interaction.send_message"):
            handle_toggle_door_request({"q": 1, "r": 0}, pc, gs)
        self.assertNotIn([12, 12], gs.current_map["fow_revealed"])
        self.assertIn([2, 0], gs.current_map["fow_revealed"])  # only party member explored adjacent wall step

        # Bumping an undiscovered secret door reports generic wall error without leaking door name
        errs = []
        with patch("server.rules.movement.send_message", side_effect=lambda _c, m: errs.append(m)):
            handle_move_request({"to": [0, 1]}, pc, gs)
        self.assertEqual(pc.position, [0, 0])
        self.assertTrue(errs)
        self.assertNotIn("Passaggio Tesoro", errs[0]["data"]["text"])

        # /torch stops at closed door / walls and updates fow_draft
        gs.current_map["doors"][0]["state"] = "closed"
        gs.current_map["fow_revealed"] = [[0, 0]]
        gs.current_map["fow_draft"] = [[0, 0]]
        with patch("server.rules.chat.broadcast"):
            handle_chat({"text": "/torch"}, pc, gs)
        self.assertNotIn([3, 0], gs.current_map["fow_revealed"])
        self.assertIn([0, 0], gs.current_map["fow_draft"])

    def test_canvas_targeting_night_light_redaction_and_static_light_no_camera(self):
        root = tk.Tk()
        root.withdraw()
        try:
            canvas = HexMapCanvas(root, width=500, height=400)
            canvas.is_dm = False
            map_data = {
                "grid_type": "square",
                "fow_enabled": True,
                "fow_revealed": [[0, 0], [5, 0]],
                "walls": [[2, 0]],
                "lights": [{"q": 5, "r": 0, "bright": 3, "dim": 2}],
                "hexes": [[q, r] for q in range(8) for r in range(8)],
            }
            players_data = {
                "Eroe": {"name": "Eroe", "position": [0, 0], "vision_radius": 2, "is_party_member": True, "ac": 16},
                "Orco": {"name": "Orco", "position": [1, 0], "ac": 19, "hp": 20, "max_hp": 20, "light_radius": 0},
                "Ombra": {"name": "Ombra", "position": [6, 0], "is_hidden": True, "hp": 30, "max_hp": 30, "light_radius": 3},
            }
            canvas.update_data(map_data, players_data, player_name="Eroe", time_hour=23)
            canvas.current_target_name = "Orco"
            canvas.redraw()

            texts = [canvas.itemcget(i, "text") for i in canvas.find_all() if canvas.type(i) == "text"]
            self.assertFalse(any("CA 19" in t for t in texts))
            self.assertFalse(any("🔥" in t for t in texts))
            # Stale fow_revealed light behind wall at (5,0) does not reveal (7,0)
            self.assertNotIn((7, 0), canvas.visible_hexes)
            # Tooltip cleanup hook exists via Destroy handler without AttributeError
            tip = tk.Toplevel(root)
            canvas.hover_tooltip = tip
        finally:
            root.destroy()

    def test_square_5105_movement_and_combat_darkvision_autocrit_sneak(self):
        gs = GameState(queue.Queue())
        gs.automation_settings = {"square_diagonal_rule": "5-10-5", "strict_movement_limits": True}
        gs.current_map = {"grid_type": "square", "walls": [], "doors": [], "hexes": [[q, r] for q in range(12) for r in range(12)]}
        gs.combat_active = True

        hero = Player("Eroe")
        hero.is_party_member = True
        hero.position = [0, 0]
        hero.speed = 30
        hero.conn = MagicMock()
        gs.players = [hero]

        errs = []
        with patch("server.rules.movement.send_message", side_effect=lambda _c, m: errs.append(m)):
            # 6 diagonals under 5-10-5 cost 9 cells = 45ft > 30ft
            handle_move_request({"to": [6, 6]}, hero, gs)
        self.assertEqual(hero.position, [0, 0])
        self.assertTrue(errs)

        # Diagonal square sneak attack + auto-crit on paralyzed target within 1 diagonal (grid_distance == 1)
        rogue = Player("Ladro")
        rogue.is_party_member = True
        rogue.position = [0, 0]
        rogue.full_sheet = {"level": 3, "char_class": "Ladro"}
        ally = Player("Guerriero")
        ally.is_party_member = True
        ally.position = [2, 2]
        ally.hp = 30
        orc = Player("Orco")
        orc.is_npc = True
        orc.position = [1, 1]
        orc.hp = 100
        orc.max_hp = 100
        orc.conditions = ["Paralizzato"]
        orc.full_sheet = {"ac": 10}
        gs.players = [rogue, ally, orc]
        gs.combat_active = False

        chats = []
        with patch("server.rules.combat.broadcast", side_effect=lambda _g, m: chats.append(m)), \
             patch("server.rules.combat.roll_dice", return_value={"total": 10, "rolls": [10]}):
            handle_attack_request(
                {"target_name": "Orco", "weapon_name": "Stocco", "hit_bonus": 10, "damage_formula": "1d8+3", "damage_type": "Perforante"},
                rogue,
                gs,
            )
        combined = " ".join(m["data"]["text"] for m in chats if m.get("type") == "CHAT_BROADCAST")
        self.assertIn("CRITICO AUTOMATICO", combined)
        self.assertIn("Attacco Furtivo", combined)

    def test_map_editor_loot_chest_no_keyerror_and_flat_top_resize(self):
        root = tk.Tk()
        root.withdraw()
        ed = None
        try:
            ed = MapEditorWindow(root)
            ed.grid_type_var.set("hex")
            ed.current_grid_type = "hex"
            ed.resize_grid(4, 3, push_undo=False)
            xs = [ed.hex_layout.hex_to_pixel(h)[0] for h in ed.grid_hexes]
            self.assertGreaterEqual(min(xs), -1e-6)

            ed.current_hex_size = 30
            ed.map_scale_var.set(list(ed.MAP_SCALES.keys())[-1])
            with patch("server.map_editor.messagebox.askyesno", return_value=False), \
                 patch("server.map_editor.messagebox.showinfo"):
                ed.on_map_scale_selected()
            self.assertEqual(ed.current_hex_size, 30)

            h0 = next(iter(ed.grid_hexes))
            px, py = ed.hex_layout.hex_to_pixel(h0)
            ed._toggle_loot_at(px, py, silent=True, item_name="Spada +1", gold=75)
            loot_dict = ed.loots[h0]
            self.assertIn("qty", loot_dict)
            self.assertIn("contents", loot_dict)

            gs = GameState(queue.Queue())
            gs.current_map = {"grid_type": "hex", "loots": [loot_dict], "walls": [], "doors": []}
            pc = Player("Eroe")
            pc.position = [h0.q, h0.r]
            pc.full_sheet = {"inventory_grid": [None] * 25, "currency": {"MO": 0}}
            with patch("server.rules.inventory.broadcast"), patch("server.rules.inventory.send_message"):
                handle_take_loot_request({"q": h0.q, "r": h0.r}, pc, gs)
            self.assertEqual(gs.current_map["loots"], [])
            self.assertEqual(pc.full_sheet["currency"]["MO"], 75)
            self.assertEqual(pc.full_sheet["inventory_grid"][0]["name"], "Spada +1")
        finally:
            if ed is not None:
                try:
                    ed.destroy()
                except Exception:
                    pass
            root.destroy()


if __name__ == "__main__":
    unittest.main()
