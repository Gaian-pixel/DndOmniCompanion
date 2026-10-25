import unittest
import tkinter as tk
from client.character_manager import Character
from client.progression_ui import LevelUpDialog, CLASS_MAP, HIT_DICE_MAP


class TestLevelUpProgression(unittest.TestCase):

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

    def test_fighter_subclass_and_features_progression(self):
        """Verifica che un Guerriero che sale al livello 3 possa scegliere l'Archetipo e riceva i privilegi corretti."""
        fgt = Character(name="Gildor")
        fgt.char_class = "Guerriero"
        fgt.level = 2
        fgt.hp_max = 20
        fgt.hp_current = 20
        fgt.attributes["COS"] = 14 # Mod +2

        applied = []
        dlg = LevelUpDialog(self.root, fgt, lambda: applied.append(True))
        dlg.withdraw()

        # Verifica dado vita e opzioni
        self.assertEqual(dlg.hit_die, 10)
        self.assertEqual(dlg.avg_hp, 6)

        # Seleziona sottoclasse Campione
        champ = [s for s in dlg.matching_subclasses if "Campione" in s["name"]][0]
        dlg.subclass_choice_var.set(champ["name"])
        dlg._on_subclass_selected()

        # Applica
        dlg.apply()

        self.assertEqual(len(applied), 1)
        self.assertEqual(fgt.level, 3)
        self.assertEqual(fgt.hp_max, 28) # 20 + 6 (media) + 2 (COS) = 28
        self.assertIn("Campione", fgt.subclass)
        self.assertIn("Critico Migliorato", fgt.features)

    def test_wizard_spell_selection_on_level_up(self):
        """Verifica che un Mago al livello 3 sblocchi gli incantesimi di 2° cerchio e possa selezionarli nel Grimorio."""
        wiz = Character(name="Elminster")
        wiz.char_class = "Mago"
        wiz.level = 2
        wiz.hp_max = 14
        wiz.hp_current = 14
        wiz.attributes = {"FOR": 8, "DES": 14, "COS": 12, "INT": 16, "SAG": 12, "CAR": 10}
        wiz.spellbook = [{"name": "Dardo Incantato", "level": 1}]

        applied = []
        dlg = LevelUpDialog(self.root, wiz, lambda: applied.append(True))
        dlg.withdraw()

        # Verifica che gli incantesimi idonei fino al 2° cerchio siano stati caricati
        self.assertGreater(len(dlg.all_eligible_spells), 100)
        acid_arrow = [s for s in dlg.all_eligible_spells if "Acid Arrow" in s["name"] or "Freccia Acida" in s.get("name_it", "")][0]
        dlg.selected_spells.append(acid_arrow)

        dlg.apply()

        self.assertEqual(len(applied), 1)
        self.assertEqual(wiz.level, 3)
        self.assertEqual(wiz.spell_slots["1"]["max"], 4)
        self.assertEqual(wiz.spell_slots["2"]["max"], 2)
        # Verifica aggiunta incantesimo al Grimorio
        self.assertTrue(any("Freccia Acida" in s["name"] or "Acid Arrow" in s["name"] for s in wiz.spellbook))

    def test_asi_ability_score_improvement_at_level_4(self):
        """Verifica che al livello 4 l'ASI aumenti correttamente la statistica scelta."""
        rogue = Character(name="Shadow")
        rogue.char_class = "Ladro"
        rogue.level = 3
        rogue.hp_max = 24
        rogue.hp_current = 24
        rogue.attributes = {"FOR": 10, "DES": 16, "COS": 14, "INT": 12, "SAG": 12, "CAR": 10}

        applied = []
        dlg = LevelUpDialog(self.root, rogue, lambda: applied.append(True))
        dlg.withdraw()

        self.assertTrue(dlg.has_asi)
        dlg.asi_choice_var.set("single")
        dlg.asi_single_stat.set("DES")
        dlg.apply()

        self.assertEqual(len(applied), 1)
        self.assertEqual(rogue.level, 4)
        self.assertEqual(rogue.attributes["DES"], 18)


if __name__ == "__main__":
    unittest.main()

