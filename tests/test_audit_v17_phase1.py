import json
import os
import queue
import tempfile
import tkinter as tk
import unittest
from unittest.mock import MagicMock, patch

from client.character_manager import Character
from client.character_sheet_ui import CharacterSheetFrame
from client.progression_ui import LevelUpDialog
from common.campaign import Campaign
from common.campaign_journal import CampaignJournal
from common.game_state import GameState, Player
from common.protocol import make_update_stats_request
from components.calendar_ui import CalendarDialog
from components.ui_components import ToastNotification
from server.map_editor import MapEditorWindow
from server.rules.character import handle_update_stats_request
from server.rules.combat import (
    advance_combat_turn,
    drop_concentration,
    handle_submit_initiative,
)
from server.rules.inventory import (
    handle_buy_item_request,
    handle_give_gold_request,
    handle_take_loot_request,
)


def _make_char(name: str, char_class: str = "Guerriero", race: str = "Umano", level: int = 1) -> Character:
    c = Character(name=name)
    c.char_class = char_class
    c.race = race
    c.level = level
    return c


class TestAuditV17Phase1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.gui_queue = queue.Queue()
        self.game_state = GameState(self.gui_queue)
        self._p_info = patch("common.messagebox.messagebox.showinfo")
        self._p_warn = patch("common.messagebox.messagebox.showwarning")
        self._p_err = patch("common.messagebox.messagebox.showerror")
        self._p_tk_info = patch("tkinter.messagebox.showinfo")
        self._p_tk_warn = patch("tkinter.messagebox.showwarning")
        self._p_tk_err = patch("tkinter.messagebox.showerror")
        self.mock_showinfo = self._p_info.start()
        self.mock_showwarning = self._p_warn.start()
        self.mock_showerror = self._p_err.start()
        self.mock_tk_info = self._p_tk_info.start()
        self.mock_tk_warn = self._p_tk_warn.start()
        self.mock_tk_err = self._p_tk_err.start()
        self.addCleanup(self._p_info.stop)
        self.addCleanup(self._p_warn.stop)
        self.addCleanup(self._p_err.stop)
        self.addCleanup(self._p_tk_info.stop)
        self.addCleanup(self._p_tk_warn.stop)
        self.addCleanup(self._p_tk_err.stop)

    def test_1_1_features_migration_prevents_trait_wipe(self):
        char = _make_char("Aria", char_class="Guerriero", race="Elfo", level=1)
        char.features = "- Scurovisione (18m)\n- Recuperare Energie (1/Riposo Breve)"
        char.features_list = []

        sheet = CharacterSheetFrame(self.root, char, manager=None, is_connected=False)
        try:
            self.root.update_idletasks()
            self.assertGreaterEqual(len(char.features_list), 2)
            sheet.save_character(close_after=False)
            self.assertIn("Scurovisione", char.features)
            self.assertIn("Recuperare Energie", char.features)
        finally:
            sheet.destroy()

    def test_1_2_initiative_bonus_isolated_from_rolled_combat_initiative(self):
        p = Player("Legolas", None, None)
        p.initiative = 4
        p.initiative_bonus = 4
        p.full_sheet = {"initiative": 4, "attributes": {"Destrezza": 18}}
        self.game_state.add_player(p)
        self.game_state.start_combat()

        with patch("server.rules.combat.broadcast"):
            handle_submit_initiative({"initiative": 19}, p, self.game_state)
        self.assertEqual(p.initiative, 19)
        self.assertEqual(p.get_initiative_bonus(), 4)
        self.assertEqual(p.full_sheet["initiative"], 4)

    def test_1_3_campaign_apply_restores_journal_and_handouts(self):
        camp = Campaign(name="Cronache Perdute")
        camp.handouts = [{"id": "h1", "title": "Mappa Antica", "type": "text", "content": "Segreto"}]
        camp.journal = CampaignJournal(campaign_name="Cronache Perdute")
        camp.journal.record_event("story", "Prologo", "Inizio avventura", actor="Party")

        camp.apply_to_game_state(self.game_state)
        self.assertEqual(len(self.game_state.handouts), 1)
        self.assertEqual(self.game_state.handouts[0]["title"], "Mappa Antica")
        self.assertIs(self.game_state.campaign_journal, camp.journal)
        self.assertEqual(len(self.game_state.campaign_journal.sessions[0].events), 1)

    def test_1_4_map_editor_preserves_metadata_across_load_and_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, "dungeon.json")
            out_path = os.path.join(tmpdir, "dungeon_saved.json")
            map_payload = {
                "name": "Cripta Reale",
                "grid_type": "hex",
                "hex_size": 36,
                "outdoor": False,
                "spawn_point": [3, 4],
                "fow_enabled": True,
                "fow_revealed": [[3, 4]],
                "hexes": [[0, 0]],
                "walls": [["0,0", "1,0"]],
                "doors": [{"edge": ["1,0", "2,0"], "state": "locked", "dc": 15}],
                "traps": [{"q": 2, "r": 2, "name": "Dardi", "dc": 14}],
                "loots": [{"q": 1, "r": 1, "item": "Spada", "qty": 1}],
                "lights": [{"q": 0, "r": 0, "bright": 4, "dim": 4}],
                "teleports": [{"q": 5, "r": 5, "target_map": "exit.json"}],
                "room_pins": [{"q": 0, "r": 0, "title": "Sala 1", "dm_notes": "Segreto"}],
            }
            with open(src_path, "w", encoding="utf-8") as f:
                json.dump(map_payload, f)

            editor = MapEditorWindow(self.root)
            try:
                with patch("tkinter.filedialog.askopenfilename", return_value=src_path):
                    editor.load_map_file()
                with patch("tkinter.filedialog.asksaveasfilename", return_value=out_path):
                    editor.save_map()

                with open(out_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)

                self.assertEqual(saved["name"], "Cripta Reale")
                self.assertFalse(saved["outdoor"])
                self.assertEqual(saved["spawn_point"], [3, 4])
                self.assertTrue(saved["fow_enabled"])
                self.assertEqual(saved["walls"], [["0,0", "1,0"]])
                self.assertEqual(saved["doors"][0]["state"], "locked")
                self.assertEqual(saved["traps"][0]["name"], "Dardi")
                self.assertEqual(saved["loots"][0]["item"], "Spada")
                self.assertEqual(saved["lights"][0]["bright"], 4)
                self.assertEqual(saved["teleports"][0]["target_map"], "exit.json")
                self.assertEqual(saved["room_pins"][0]["title"], "Sala 1")
            finally:
                editor.destroy()

    def test_1_5_and_1_9_item_details_containers_and_dynamic_slots_above_25(self):
        char = _make_char("PackMule", char_class="Guerriero", race="Umano", level=1)
        char.inventory_grid = [
            {"name": f"Oggetto {i}", "qty": 1, "weight": 1.0, "type": "Equipaggiamento"}
            for i in range(30)
        ]
        reloaded = Character.from_dict(char.to_dict())
        self.assertEqual(len(reloaded.inventory_grid), 30)

        sheet = CharacterSheetFrame(self.root, reloaded, manager=None, is_connected=False)
        try:
            self.root.update_idletasks()
            self.assertGreaterEqual(len(sheet.inventory_buttons), 30)
            self.assertAlmostEqual(reloaded.get_carried_weight(), 30.0)
            sheet.open_item_details_dialog(0, reloaded.inventory_grid[0])
            for child in list(sheet.winfo_children()) + list(self.root.winfo_children()):
                if isinstance(child, tk.Toplevel):
                    child.destroy()
        finally:
            sheet.destroy()

    def test_1_6_and_1_15_drop_concentration_reason_and_temp_hp_preserved(self):
        p = Player("Gale", None, None)
        p.hp = 15
        p.max_hp = 20
        p.temp_hp = 8
        p.concentrating_on = "Benedizione"
        p.conditions = ["Concentrazione"]
        p.full_sheet = {
            "hp_current": 15,
            "hp_max": 20,
            "temp_hp": 8,
            "concentrating_on": "Benedizione",
            "conditions": ["Concentrazione"],
        }
        self.game_state.add_player(p)

        msg = make_update_stats_request("Gale", 15, 20, 14, 2)
        self.assertNotIn("temp_hp", msg)
        with patch("server.rules.character.broadcast"):
            handle_update_stats_request(msg, p, self.game_state)
        self.assertEqual(p.temp_hp, 8)

        with patch("server.rules.combat.broadcast"):
            drop_concentration(p, self.game_state, reason="0 PF")
        self.assertIsNone(p.concentrating_on)
        self.assertNotIn("Concentrazione", p.conditions)

    def test_1_8_calendar_month_bounds_and_toast_secondary(self):
        cal = CalendarDialog(self.root, self.game_state, is_dm=False)
        try:
            cal.view_month = 12
            cal.next_month()
            self.assertEqual(cal.view_month, 1)
            cal.prev_month()
            self.assertEqual(cal.view_month, 12)
        finally:
            cal.destroy()

        toast = ToastNotification(self.root, "Test Toast", toast_type="secondary", duration=200)
        toast.destroy()

    def test_1_10_and_2_5_saving_throws_loaded_and_offline_anti_cheat_enforced(self):
        char = _make_char("Paladino", char_class="Paladino", race="Umano", level=3)
        char.hp_current = 28
        char.hp_max = 28
        char.ac = 18
        char.saving_throw_proficiencies = ["Saggezza", "Carisma"]
        char.attributes["FOR"] = 16
        char.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 50, "MP": 0}

        sheet = CharacterSheetFrame(self.root, char, manager=None, is_connected=False)
        try:
            self.root.update_idletasks()
            self.assertEqual(sheet.save_prof_vars["SAG"].get(), 1)
            self.assertEqual(sheet.save_prof_vars["CAR"].get(), 1)
            self.assertEqual(sheet.save_prof_vars["FOR"].get(), 0)

            sheet.level_var.set("20")
            sheet.hp_max_var.set("999")
            sheet.hp_cur_var.set("999")
            sheet.ac_var.set("30")
            sheet.attr_vars["FOR"].set("30")
            sheet.currency_vars["MO"].set("99999")

            sheet.save_character(close_after=False)

            self.assertEqual(char.level, 3)
            self.assertEqual(char.hp_max, 28)
            self.assertEqual(char.hp_current, 28)
            self.assertEqual(char.ac, 18)
            self.assertEqual(char.attributes["FOR"], 16)
            self.assertEqual(char.currency["MO"], 50)
            self.assertNotIn("FOR", char.saving_throw_proficiencies)
        finally:
            sheet.destroy()

    def test_1_12_loot_overflow_preserved_give_gold_single_deduction_and_dndscript_shop(self):
        p1 = Player("Ladro", None, None)
        p1.full_sheet = {
            "currency": {"MR": 0, "MA": 0, "ME": 0, "MO": 100, "MP": 0},
            "gp": "100",
            "inventory_grid": [{"name": f"Slot{i}", "qty": 1} for i in range(24)] + [None],
        }
        p2 = Player("Mago", None, MagicMock())
        p2.full_sheet = {
            "currency": {"MR": 0, "MA": 0, "ME": 0, "MO": 10, "MP": 0},
            "gp": "10",
            "inventory_grid": [None] * 30,
        }
        self.game_state.add_player(p1)
        self.game_state.add_player(p2)

        self.game_state.current_map = {
            "hexes": {},
            "loots": [
                {
                    "q": 0,
                    "r": 0,
                    "item": "Spoglie",
                    "qty": 1,
                    "contents": {
                        "wallet": {"MO": 25},
                        "items": [
                            {"name": "Gemma Rossa", "qty": 1, "weight": 0.1},
                            {"name": "Scudo Pesante", "qty": 1, "weight": 6.0},
                        ],
                    },
                }
            ],
        }
        with patch("server.rules.inventory.send_message"), patch("server.rules.inventory.broadcast"):
            handle_take_loot_request({"q": 0, "r": 0}, p1, self.game_state)

        self.assertEqual(p1.full_sheet["currency"]["MO"], 125)
        self.assertEqual(int(p1.full_sheet["gp"]), 125)
        self.assertEqual(len(self.game_state.current_map["loots"]), 1)
        rem_items = self.game_state.current_map["loots"][0]["contents"]["items"]
        self.assertEqual(len(rem_items), 1)
        self.assertEqual(rem_items[0]["name"], "Scudo Pesante")

        with patch("server.rules.inventory.send_message"), patch("server.rules.inventory.broadcast"):
            handle_give_gold_request({"target_name": "Mago", "amount": 30}, p1, self.game_state)
        self.assertEqual(p1.full_sheet["currency"]["MO"], 95)
        self.assertEqual(int(p1.full_sheet["gp"]), 95)
        self.assertEqual(p2.full_sheet["currency"]["MO"], 40)
        self.assertEqual(int(p2.full_sheet["gp"]), 40)

        self.game_state.shops["Emporio"] = {
            "inventory": [{"name": "Pozione di Guarigione", "cost": "25 gp", "qty": 2}]
        }
        with patch("server.rules.inventory.send_message"), patch("server.rules.inventory.broadcast"):
            handle_buy_item_request(
                {"shop_name": "Emporio", "item_name": "Pozione di Guarigione"}, p2, self.game_state
            )
        self.assertEqual(p2.full_sheet["currency"]["MO"], 15)
        self.assertEqual(len(p2.full_sheet["inventory_grid"]), 30)
        self.assertTrue(
            any(s and s.get("name") == "Pozione di Guarigione" for s in p2.full_sheet["inventory_grid"])
        )

    def test_1_13_level_up_asi_validation_and_level_20_cap(self):
        char = _make_char("Eroe", char_class="Guerriero", race="Umano", level=3)
        char.hp_max = 28
        char.hp_current = 28
        char.attributes["FOR"] = 16

        dlg = LevelUpDialog(self.root, char, update_callback=lambda: None)
        try:
            dlg.asi_choice_var.set("dual")
            dlg.asi_dual_stat1.set("FOR")
            dlg.asi_dual_stat2.set("FOR")
            dlg.apply()
            self.assertEqual(char.level, 3)
            self.assertEqual(char.hp_max, 28)
        finally:
            if dlg.winfo_exists():
                dlg.destroy()

        char20 = _make_char("Semidio", char_class="Guerriero", race="Umano", level=20)
        self.mock_tk_info.reset_mock()
        self.mock_showinfo.reset_mock()
        dlg20 = LevelUpDialog(self.root, char20, update_callback=lambda: None)
        self.assertTrue(self.mock_tk_info.called or self.mock_showinfo.called)
        self.assertEqual(char20.level, 20)
        if dlg20.winfo_exists():
            dlg20.destroy()

    def test_1_16_end_of_turn_effect_decrements_only_once(self):
        p1 = Player("Chierico", None, None)
        p1.initiative = 18
        p1.add_effect({"id": "guida", "name": "Guida", "duration_rounds": 2, "decrement_timing": "end_of_turn"})
        p2 = Player("Goblin", None, None)
        p2.initiative = 10
        self.game_state.add_player(p1)
        self.game_state.add_player(p2)
        self.game_state.start_combat()

        with patch("server.rules.combat.broadcast"):
            advance_combat_turn(self.game_state)

        self.assertEqual(len(p1.active_effects), 1)
        self.assertEqual(p1.active_effects[0]["duration_rounds"], 1)


if __name__ == "__main__":
    unittest.main()
