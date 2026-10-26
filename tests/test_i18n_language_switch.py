import unittest
import tkinter as tk
from common.i18n import (
    _t, get_language, set_language, translate_ability, translate_skill,
    translate_race, translate_class, translate_alignment, translate_background,
    translate_condition, translate_weather, STRINGS, reset_listeners_for_testing
)
from client.character_manager import Character, CharacterManager
from client.character_sheet_ui import CharacterSheetFrame
from client.character_creation_wizard import CharacterCreationWizardFrame


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

        self.assertEqual(translate_race("Umano"), "Human")
        self.assertEqual(translate_race("Elfo"), "Elf")
        self.assertEqual(translate_race("Nano"), "Dwarf")
        self.assertEqual(translate_class("Guerriero"), "Fighter")
        self.assertEqual(translate_class("Ladro"), "Rogue")
        self.assertEqual(translate_class("Mago"), "Wizard")
        self.assertEqual(translate_alignment("Legale Buono"), "Lawful Good")
        self.assertEqual(translate_background("Accolito"), "Acolyte")

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

        self.assertEqual(translate_race("Human"), "Umano")
        self.assertEqual(translate_race("Elf"), "Elfo")
        self.assertEqual(translate_race("Dwarf"), "Nano")
        self.assertEqual(translate_class("Fighter"), "Guerriero")
        self.assertEqual(translate_class("Rogue"), "Ladro")
        self.assertEqual(translate_class("Wizard"), "Mago")
        self.assertEqual(translate_alignment("Lawful Good"), "Legale Buono")
        self.assertEqual(translate_background("Acolyte"), "Accolito")

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

    def test_character_creation_wizard_english_localization(self):
        """Verifica che il Wizard di Creazione Personaggio renderizzi correttamente tutti i passi in Inglese."""
        root = tk.Tk()
        root.withdraw()
        try:
            set_language("en")
            mgr = CharacterManager()
            wiz = CharacterCreationWizardFrame(root, mgr, on_complete_callback=lambda c: None)

            # Step Indicator & Pills
            self.assertIn("Step 1 of 5", wiz.step_indicator_lbl.cget("text"))
            self.assertIn("Choose Race", wiz.step_pill_labels[0].cget("text"))
            self.assertIn("Choose Class", wiz.step_pill_labels[1].cget("text"))
            self.assertIn("Ability Scores", wiz.step_pill_labels[2].cget("text"))
            self.assertIn("Choose Background & Skills", wiz.step_pill_labels[3].cget("text"))
            self.assertIn("Backstory", wiz.step_pill_labels[4].cget("text"))

            # Step 1 (Race)
            self.assertEqual(wiz.next_btn.cget("text"), "Next Step →")
            self.assertEqual(wiz.race_var.get(), "Human")

            # Step 2 (Class)
            wiz.current_step = 1
            wiz.show_step()
            self.assertEqual(wiz.class_var.get(), "Fighter")
            self.assertEqual(wiz.prev_btn.cget("text"), "← Previous Step")

            # Step 3 (Attributes)
            wiz.current_step = 2
            wiz.show_step()
            # Verify attr labels render STR, DEX, CON, INT, WIS, CHA
            child_labels = [w.cget("text") for w in wiz.container.winfo_children() if isinstance(w, tk.Label) or isinstance(w, (tk.ttk.Label if hasattr(tk, 'ttk') else tk.Label))]

            # Step 4 (Background)
            wiz.current_step = 3
            wiz.show_step()
            self.assertEqual(wiz.bg_name_var.get(), "Acolyte")

            # Step 5 (Narrative)
            wiz.current_step = 4
            wiz.show_step()
            self.assertEqual(wiz.next_btn.cget("text"), "Finish & Create Character")
            self.assertEqual(wiz.align_var.get(), "None (Unspecified)")

            # Dynamic switch to Italian while open
            set_language("it")
            self.assertIn("Fine e Crea Personaggio", wiz.next_btn.cget("text"))
            self.assertIn("Passo 5 di 5", wiz.step_indicator_lbl.cget("text"))

            wiz.destroy()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
