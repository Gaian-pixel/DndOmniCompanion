"""
test_character_schema.py - Test unitari per il modulo common/character_schema.py.
Verifica la normalizzazione, la sincronizzazione bidirezionale delle chiavi
e la compatibilità con Character e Player.full_sheet.
"""

import unittest
from common.character_schema import (
    normalize_character_dict,
    calculate_modifier,
    canonical_stat_name,
    STAT_IT_TO_EN,
    STAT_EN_TO_IT
)
from client.character_manager import Character

class TestCharacterSchema(unittest.TestCase):
    def test_calculate_modifier(self):
        self.assertEqual(calculate_modifier(10), 0)
        self.assertEqual(calculate_modifier(11), 0)
        self.assertEqual(calculate_modifier(12), 1)
        self.assertEqual(calculate_modifier(18), 4)
        self.assertEqual(calculate_modifier(20), 5)
        self.assertEqual(calculate_modifier(8), -1)
        self.assertEqual(calculate_modifier(3), -4)
        self.assertEqual(calculate_modifier("14"), 2)
        self.assertEqual(calculate_modifier(None), 0)

    def test_canonical_stat_name(self):
        self.assertEqual(canonical_stat_name("FOR", "en"), "STR")
        self.assertEqual(canonical_stat_name("str", "it"), "FOR")
        self.assertEqual(canonical_stat_name("DES", "en"), "DEX")
        self.assertEqual(canonical_stat_name("dex", "it"), "DES")

    def test_normalize_empty_dict(self):
        norm = normalize_character_dict({})
        self.assertEqual(norm["name"], "Nuovo Personaggio")
        self.assertEqual(norm["level"], 1)
        self.assertEqual(norm["hp_current"], 10)
        self.assertEqual(norm["hp"], 10)
        self.assertEqual(norm["hp_max"], 10)
        self.assertEqual(norm["max_hp"], 10)
        self.assertEqual(norm["ac"], 10)
        self.assertEqual(norm["armor_class"], 10)
        self.assertEqual(len(norm["inventory_grid"]), 25)
        self.assertEqual(len(norm["spell_slots"]), 9)
        self.assertIn("FOR", norm["attributes"])
        self.assertIn("STR", norm["stats"])
        self.assertEqual(norm["currency"]["MO"], 0)
        self.assertEqual(norm["gp"], 0)

    def test_normalize_synonyms_sync(self):
        # Input con chiavi miste (class_name invece di char_class, stats invece di attributes, gp invece di MO)
        raw = {
            "name": "Conan",
            "class_name": "Barbaro",
            "level": 5,
            "stats": {"STR": 18, "DEX": 14, "CON": 16, "INT": 8, "WIS": 12, "CHA": 10},
            "hp": 55,
            "max_hp": 55,
            "armor_class": 15,
            "gp": 150
        }
        norm = normalize_character_dict(raw)
        self.assertEqual(norm["char_class"], "Barbaro")
        self.assertEqual(norm["class_name"], "Barbaro")
        self.assertEqual(norm["attributes"]["FOR"], 18)
        self.assertEqual(norm["stats"]["STR"], 18)
        self.assertEqual(norm["attributes"]["DES"], 14)
        self.assertEqual(norm["attributes"]["COS"], 16)
        self.assertEqual(norm["hp_current"], 55)
        self.assertEqual(norm["hp_max"], 55)
        self.assertEqual(norm["ac"], 15)
        self.assertEqual(norm["currency"]["MO"], 150)
        self.assertEqual(norm["gp"], 150)

    def test_character_class_integration(self):
        c = Character("Legolas")
        c.char_class = "Ranger"
        c.attributes["DES"] = 18
        c.currency["MO"] = 75
        c.hp_current = 24
        c.hp_max = 24
        c.starting_kit_applied = True

        d = c.to_dict()
        self.assertEqual(d["class_name"], "Ranger")
        self.assertEqual(d["stats"]["DEX"], 18)
        self.assertEqual(d["attributes"]["DES"], 18)
        self.assertEqual(d["gp"], 75)
        self.assertEqual(d["currency"]["MO"], 75)
        self.assertEqual(d["hp"], 24)
        self.assertEqual(d["hp_current"], 24)

        # Test from_dict con dati normalizzati
        c2 = Character.from_dict(d)
        self.assertEqual(c2.name, "Legolas")
        self.assertEqual(c2.char_class, "Ranger")
        self.assertEqual(c2.attributes["DES"], 18)
        self.assertEqual(c2.currency["MO"], 75)

if __name__ == "__main__":
    unittest.main()
