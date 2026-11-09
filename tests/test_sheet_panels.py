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


if __name__ == "__main__":
    unittest.main()

