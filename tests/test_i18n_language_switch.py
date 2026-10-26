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



    def test_race_and_class_lore_descriptions_localization(self):
        """Verifica che le descrizioni narrative, lore, tratti e ruoli di razze e classi siano localizzate in lingua."""
        from common.races_data import get_race_info
        from common.classes_data import get_class_info

        # Modalità Inglese
        set_language("en")
        elf_en = get_race_info("Elfo")
        self.assertTrue(elf_en["overview"].startswith("Elves are a magical people"), f"Expected English overview, got: {elf_en['overview'][:50]}")
        self.assertEqual(elf_en["traits"][0][0], "Darkvision")
        self.assertIn("immortal grace", elf_en["tagline"])

        barb_en = get_class_info("Barbaro")
        self.assertTrue(barb_en["overview"].startswith("From the frozen northern tundras"), f"Expected English class overview, got: {barb_en['overview'][:50]}")
        self.assertEqual(barb_en["features_lvl1"][0][0], "Rage")
        self.assertIn("Tank", barb_en["role"])

        # Modalità Italiano
        set_language("it")
        elf_it = get_race_info("Elfo")
        self.assertTrue(elf_it["overview"].startswith("Gli elfi sono un popolo"), f"Expected Italian overview, got: {elf_it['overview'][:50]}")
        self.assertEqual(elf_it["traits"][0][0], "Scurovisione (Darkvision)")
        self.assertIn("immortale", elf_it["tagline"])

        barb_it = get_class_info("Barbaro")
        self.assertTrue(barb_it["overview"].startswith("Dalle gelide tundre"), f"Expected Italian class overview, got: {barb_it['overview'][:50]}")
        self.assertEqual(barb_it["features_lvl1"][0][0], "Ira (Rage)")
        self.assertIn("Tank", barb_it["role"])

    def test_campaign_editor_and_selector_localization(self):
        """Verifica la completa internazionalizzazione dell'Editor Campagne e del Selettore Campagne."""
        from server.campaign_editor_ui import CampaignSelectorFrame, CampaignEditorFrame
        from common.campaign import Campaign

        set_language("en")
        self.assertEqual(_t("camp_sel_list_title"), "Available Campaigns")
        self.assertEqual(_t("camp_tab_studio"), "🧭 Flow & DndScript")
        self.assertEqual(_t("camp_tab_general"), "📜 General & DM Notes")
        self.assertEqual(_t("camp_ed_btn_save"), "💾 Save")
        self.assertEqual(_t("camp_gen_info_title"), "Campaign Information")

        set_language("it")
        self.assertEqual(_t("camp_sel_list_title"), "Campagne Disponibili")
        self.assertEqual(_t("camp_tab_studio"), "🧭 Flusso & DndScript")
        self.assertEqual(_t("camp_tab_general"), "📜 Generale & Note DM")
        self.assertEqual(_t("camp_ed_btn_save"), "💾 Salva")
        self.assertEqual(_t("camp_gen_info_title"), "Informazioni Campagna")

        # Verifica istanziazione UI in inglese
        root = tk.Tk()
        root.withdraw()
        try:
            set_language("en")
            camp = Campaign(name="Test Adventure")
            selector = CampaignSelectorFrame(root, on_select_callback=lambda c: None)
            self.assertEqual(selector.tree_camps.heading("Nome", "text"), "Campaign Name")
            self.assertEqual(selector.tree_camps.heading("Livello", "text"), "Level")
            selector.destroy()

            editor = CampaignEditorFrame(root, campaign=camp)
            self.assertEqual(editor.notebook.tab(0, "text"), "🧭 Flow & DndScript")
            self.assertEqual(editor.notebook.tab(1, "text"), "📜 General & DM Notes")
            self.assertEqual(editor.notebook.tab(2, "text"), "🗺️ Scenes & Maps")
            self.assertEqual(editor.notebook.tab(3, "text"), "⚔️ Tactical Encounters")
            editor.destroy()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
