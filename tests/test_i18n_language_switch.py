import unittest
import tkinter as tk
from common.i18n import (
    _t, get_language, set_language, translate_ability, translate_skill,
    translate_condition, translate_weather, STRINGS, reset_listeners_for_testing
)
from client.character_manager import Character, CharacterManager
from client.character_sheet_ui import CharacterSheetFrame


class TestI18nLanguageSwitch(unittest.TestCase):
    def setUp(self):
        reset_listeners_for_testing()
        self.original_lang = get_language()

    def tearDown(self):
        set_language(self.original_lang)
        reset_listeners_for_testing()

    def test_translation_dictionaries_symmetry(self):
        """Verifica che tutte le chiavi in Italiano abbiano la controparte in Inglese e viceversa."""
        it_keys = set(STRINGS["it"].keys())
        en_keys = set(STRINGS["en"].keys())
        diff = it_keys ^ en_keys
        self.assertEqual(len(diff), 0, f"Mancata simmetria tra chiavi IT ed EN: {diff}")

    def test_bilingual_ability_and_skills_translation(self):
        """Verifica la corretta traduzione bidirezionale di abilità e caratteristiche."""
        set_language("en")
        self.assertEqual(translate_ability("FOR"), "STR")
        self.assertEqual(translate_ability("DES"), "DEX")
        self.assertEqual(translate_ability("COS"), "CON")
        self.assertEqual(translate_ability("SAG"), "WIS")
        self.assertEqual(translate_ability("CAR"), "CHA")
        self.assertEqual(translate_ability("INT"), "INT")

        self.assertEqual(translate_skill("Acrobazia"), "Acrobatics")
        self.assertEqual(translate_skill("Furtività"), "Stealth")
        self.assertEqual(translate_skill("Percezione"), "Perception")
        self.assertEqual(translate_skill("Atletica"), "Athletics")
        self.assertEqual(translate_skill("Inganno"), "Deception")

        self.assertEqual(_t("cantrip"), "Cantrip")
        self.assertEqual(_t("wizard_step1_title"), "Step 1: Choose Race")
        self.assertEqual(_t("prog_title"), "Level Up Progression")
        self.assertEqual(_t("sheet_saves_header"), "Saving Throws")

        set_language("it")
        self.assertEqual(translate_ability("STR"), "FOR")
        self.assertEqual(translate_ability("DEX"), "DES")
        self.assertEqual(translate_ability("CON"), "COS")
        self.assertEqual(translate_ability("WIS"), "SAG")
        self.assertEqual(translate_ability("CHA"), "CAR")
        self.assertEqual(translate_ability("INT"), "INT")

        self.assertEqual(translate_skill("Acrobatics"), "Acrobazia")
        self.assertEqual(translate_skill("Stealth"), "Furtività")
        self.assertEqual(translate_skill("Perception"), "Percezione")
        self.assertEqual(translate_skill("Athletics"), "Atletica")
        self.assertEqual(translate_skill("Deception"), "Inganno")

        self.assertEqual(_t("cantrip"), "Trucchetto")
        self.assertEqual(_t("wizard_step1_title"), "Passo 1: Scegli la Razza")
        self.assertEqual(_t("prog_title"), "Avanzamento di Livello (Level Up)")
        self.assertEqual(_t("sheet_saves_header"), "Tiri Salvezza")

    def test_character_sheet_dynamic_language_refresh(self):
        """Verifica che la Scheda Personaggio risponda al cambio lingua aggiornando tab, tiri salvezza e abilità."""
        root = tk.Tk()
        root.withdraw()
        try:
            char = Character(name="TestHero", campaign="TestCampaign")
            char.char_class = "Guerriero"
            char.level = 3
            char.weapons = [{"name": "Spada Lunga", "ability": "FOR", "damage": "1d8", "type": "Tagliente"}]
            char.spellbook = [{"name": "Dardo Incantato", "level": 1, "casting_time": "1 Azione", "range": "36m"}]
            mgr = CharacterManager()

            set_language("it")
            sheet = CharacterSheetFrame(root, char, mgr)
            self.assertIn("Armi", sheet.notebook.tab(0, "text"))
            self.assertEqual(sheet.lbl_saves_header.cget("text"), "Tiri Salvezza")
            self.assertEqual(sheet.save_name_labels["FOR"].cget("text"), "FOR")
            self.assertIn("Furtività", sheet.skill_name_labels["Furtività"].cget("text"))

            # Switch a Inglese
            set_language("en")
            sheet.refresh_ui_language()

            self.assertIn("Weapons", sheet.notebook.tab(0, "text"))
            self.assertIn("Inventory", sheet.notebook.tab(1, "text"))
            self.assertIn("Features", sheet.notebook.tab(2, "text"))
            self.assertIn("Spellbook", sheet.notebook.tab(3, "text"))
            self.assertEqual(sheet.lbl_saves_header.cget("text"), "Saving Throws")
            self.assertEqual(sheet.save_name_labels["FOR"].cget("text"), "STR")
            self.assertIn("Stealth", sheet.skill_name_labels["Furtività"].cget("text"))
            self.assertIn("DEX", sheet.skill_name_labels["Furtività"].cget("text"))

            # Switch back a Italiano
            set_language("it")
            sheet.refresh_ui_language()

            self.assertIn("Armi", sheet.notebook.tab(0, "text"))
            self.assertEqual(sheet.lbl_saves_header.cget("text"), "Tiri Salvezza")
            self.assertEqual(sheet.save_name_labels["FOR"].cget("text"), "FOR")
            self.assertIn("Furtività", sheet.skill_name_labels["Furtività"].cget("text"))
            self.assertIn("DES", sheet.skill_name_labels["Furtività"].cget("text"))

            sheet.destroy()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
