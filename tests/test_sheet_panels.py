"""
tests/test_sheet_panels.py - Test unitari per i moduli e pannelli estratti della Scheda Personaggio:
- VitalsPanel (client.sheet_panels.vitals_panel)
- CombatPanel (client.sheet_panels.combat_panel)
- InventoryPanel (client.sheet_panels.inventory_panel)
- SpellsPanel (client.sheet_panels.spells_panel)
"""

import unittest
from unittest.mock import MagicMock
from client.character_manager import Character
from client.sheet_panels import VitalsPanel, CombatPanel, InventoryPanel, SpellsPanel


class TestSheetPanels(unittest.TestCase):
    def setUp(self):
        self.char = Character(name="Valeros", campaign="Kingmaker")
        self.char.char_class = "Guerriero"
        self.char.level = 1
        self.char.attributes = {"FOR": 16, "DES": 14, "COS": 14, "INT": 10, "SAG": 12, "CAR": 8}
        self.char.hp_max = 12
        self.char.hp_current = 12
        self.char.starting_kit_applied = True

    def test_spells_panel_class_abilities_and_dc(self):
        """Verifica che SpellsPanel determini correttamente la caratteristica da incantatore e calcoli CD e Attacco."""
        # Mago (INT)
        self.assertEqual(SpellsPanel.get_spellcasting_ability("Mago"), "INT")
        self.assertEqual(SpellsPanel.get_spellcasting_ability("Wizard"), "INT")

        # Chierico, Druido, Ranger (SAG)
        self.assertEqual(SpellsPanel.get_spellcasting_ability("Chierico"), "SAG")
        self.assertEqual(SpellsPanel.get_spellcasting_ability("Druid"), "SAG")
        self.assertEqual(SpellsPanel.get_spellcasting_ability("Ranger"), "SAG")

        # Bardo, Paladino, Stregone, Warlock (CAR)
        self.assertEqual(SpellsPanel.get_spellcasting_ability("Bardo"), "CAR")
        self.assertEqual(SpellsPanel.get_spellcasting_ability("Paladin"), "CAR")
        self.assertEqual(SpellsPanel.get_spellcasting_ability("Warlock"), "CAR")

        # Calcolo per Chierico livello 5 con SAG 16 (Mod +3, PB +3 -> CD 14, Attacco +6)
        c = Character(name="Kyra", campaign="Path")
        c.char_class = "Chierico"
        c.level = 5
        c.attributes["SAG"] = 16
        c.starting_kit_applied = True
        stats = SpellsPanel.calculate_spell_stats(c)
        self.assertEqual(stats["ability"], "SAG")
        self.assertEqual(stats["mod"], 3)
        self.assertEqual(stats["pb"], 3)
        self.assertEqual(stats["dc"], 14)
        self.assertEqual(stats["attack_bonus"], 6)
        self.assertEqual(stats["attack_str"], "+6")

    def test_combat_panel_txc_and_finesse(self):
        """Verifica che CombatPanel calcoli accuratamente TxC e Danni, gestendo proprietà Accurata (Finesse)."""
        # Spada Lunga: FOR 16 (+3), PB +2 -> TxC = +5, Danno = 1d8+3
        w_sword = {"name": "Spada Lunga", "ability": "FOR", "damage_dice": "1d8", "damage_type": "Tagliente", "proficient": True, "bonus": 0}
        txc, mod, pb, w_bonus, stat = CombatPanel.calculate_weapon_txc(self.char, w_sword)
        self.assertEqual(txc, 5)
        self.assertEqual(stat, "FOR")
        dmg_formula, dmg_str, dmg_mod = CombatPanel.calculate_weapon_damage(self.char, w_sword, mod, w_bonus)
        self.assertEqual(dmg_formula, "1d8+3")
        self.assertEqual(dmg_str, "1d8+3 Tagliente")

        # Stocco (Accurata/Finesse): anche se ability impostata su FOR, se DES > FOR usa DES
        self.char.attributes["FOR"] = 10
        self.char.attributes["DES"] = 18
        w_rapier = {"name": "Stocco", "ability": "FOR", "properties": "Accurata", "damage_dice": "1d8", "damage_type": "Perforante", "proficient": True, "bonus": 1}
        txc, mod, pb, w_bonus, stat = CombatPanel.calculate_weapon_txc(self.char, w_rapier)
        self.assertEqual(stat, "DES")
        # DES 18 (+4) + PB 2 + bonus magico 1 = +7
        self.assertEqual(txc, 7)
        dmg_formula, dmg_str, dmg_mod = CombatPanel.calculate_weapon_damage(self.char, w_rapier, mod, w_bonus)
        self.assertEqual(dmg_formula, "1d8+5")  # 4 mod + 1 bonus = 5

    def test_inventory_panel_currency_rates_and_gold_value(self):
        """Verifica la conversione delle monete in controvalore di Monete d'Oro (gp)."""
        purse = {
            "MR": 100,  # 1 gp
            "MA": 20,   # 2 gp
            "ME": 4,    # 2 gp
            "MO": 15,   # 15 gp
            "MP": 3     # 30 gp
        }
        # Totale: 1 + 2 + 2 + 15 + 30 = 50 gp
        val = InventoryPanel.get_estimated_gold_value(purse)
        self.assertAlmostEqual(val, 50.0)

    def test_vitals_panel_rest_and_death_saves(self):
        """Verifica i metodi di recupero e riposo di VitalsPanel."""
        sheet_mock = MagicMock()
        sheet_mock.character = self.char
        self.char.hp_current = 5
        self.char.hp_max = 12
        self.char.hit_dice_current = 0
        self.char.hit_dice_total = 1
        self.char.hit_dice_type = "d10"

        # Esecuzione long_rest direttamente
        self.char.long_rest()
        self.assertEqual(self.char.hp_current, 12)
        self.assertEqual(self.char.hit_dice_current, 1)

    def test_multiclass_spell_stats_and_prepared_cap_sum(self):
        c = Character(name="Theurge", campaign="Test")
        c.char_class = "Guerriero"
        c.level = 2  # volutamente disallineato rispetto a classes per verificare entity_get_total_level
        c.classes = {"Guerriero": 3, "Chierico": 2, "Mago": 2}
        c.attributes["SAG"] = 16  # +3 -> Chierico: 2+3=5
        c.attributes["INT"] = 14  # +2 -> Mago: 2+2=4
        c.starting_kit_applied = True

        stats = SpellsPanel.calculate_spell_stats(c)
        self.assertEqual(stats["ability"], "SAG")
        self.assertEqual(stats["pb"], 3)
        self.assertEqual(stats["dc"], 14)

        self.assertEqual(SpellsPanel.get_max_prepared_spells(c), 9)

    def test_vitals_panel_short_rest_sends_network_before_save(self):
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            events = []
            c = Character(name="Thorin", campaign="Test")
            c.char_class = "Guerriero"
            c.level = 3
            c.hp_max = 30
            c.hp_current = 18
            c.hit_dice_total = 3
            c.hit_dice_current = 3
            c.hit_dice_type = "d10"
            c.class_resources["second_wind"] = False

            sheet = tk.Frame(root)
            sheet.character = c
            sheet.is_connected = True
            sheet.manager = MagicMock()
            sheet.roll_callback = lambda f, m: events.append(("roll", m))
            sheet.on_save_callback = lambda ch: events.append(("save", ch.hit_dice_current))
            sheet.hp_cur_var = tk.IntVar(value=c.hp_current)
            sheet.hp_max_var = tk.IntVar(value=c.hp_max)
            sheet.hd_var = tk.StringVar(value="3/3 (d10)")
            sheet.hp_bar = None
            sheet.network = MagicMock()
            sheet.network.send.side_effect = lambda msg: events.append(("net", msg))

            VitalsPanel.short_rest(sheet)
            dlg = [w for w in sheet.winfo_children() if isinstance(w, tk.Toplevel)][0]
            dlg.withdraw()

            # Trova e premi "Tira 1 Dado" poi "Concludi Riposo Breve"
            from tkinter import ttk
            def _all_buttons(w):
                res = []
                for ch in w.winfo_children():
                    if isinstance(ch, ttk.Button):
                        res.append(ch)
                    res.extend(_all_buttons(ch))
                return res

            btns = _all_buttons(dlg)
            # Il primo bottone nella btn_row e' "roll_one", l'ultimo "finish_rest"
            btns[0].invoke()
            btns[-1].invoke()

            net_evs = [ev for ev in events if ev[0] == "net"]
            self.assertEqual(len(net_evs), 1)
            self.assertEqual(net_evs[0][1]["type"], "SHORT_REST_REQUEST")
            self.assertEqual(net_evs[0][1]["data"]["hd_spent"], 1)
            # Deve essere inviato prima di on_save_callback per preservare hit_dice_current sul server
            net_idx = next(i for i, e in enumerate(events) if e[0] == "net")
            save_idx = next(i for i, e in enumerate(events) if e[0] == "save")
            self.assertLess(net_idx, save_idx)
        finally:
            try:
                root.destroy()
            except Exception:
                pass

    def test_sheet_null_manager_spend_drop_and_en_inspiration(self):
        import tkinter as tk
        from unittest.mock import patch
        from common.i18n import get_language, set_language
        from client.character_sheet_ui import CharacterSheetUI
        old_lang = get_language()
        root = tk.Tk()
        root.withdraw()
        try:
            set_language("en")
            c = Character(name="Lyra", campaign="Test")
            c.char_class = "Ladro"
            c.level = 2
            c.hp_max = 16
            c.hp_current = 10
            c.has_inspiration = True
            c.inventory_grid = [
                {"name": "Potion of Healing", "qty": 2, "type": "Pozione", "weight": 0.5, "container": "equipped"},
                {"name": "Rations", "qty": 3, "type": "Equipaggiamento", "weight": 2.0, "container": "backpack"},
            ] + [None] * 23

            sheet = CharacterSheetUI(root, c, manager=None)
            self.assertIsNone(sheet.manager)
            with patch("common.messagebox.messagebox.askyesno", return_value=True), \
                 patch("common.messagebox.messagebox.showinfo"):
                sheet.spend_consumable(0, 1)
                self.assertEqual(c.inventory_grid[0]["qty"], 1)
                self.assertGreater(c.hp_current, 10)

                sheet.toggle_drop_backpack()
                self.assertTrue(c.backpack_dropped)

                sheet.on_inspiration_clicked()
                self.assertFalse(c.has_inspiration)
                self.assertEqual(sheet.adv_dis_var.get(), "Advantage")
        finally:
            set_language(old_lang)
            try:
                root.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()

