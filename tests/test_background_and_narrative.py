# test_background_and_narrative.py
"""
Test completi per il sistema di Background e Sviluppo Narrativo:
- Catalogo Backgrounds D&D 5e e competenze abilità
- Privilegi di Background (Features)
- 4 Colonne Ruolistiche (Tratti, Ideali, Legami, Difetti)
- Ganci d'avventura (Personal Quests), Segreti (per il DM), Legami di gruppo, Cimeli (Trinkets)
- Generatore narrativo "Componi la mia Storia"
- Integrazione completa nel CharacterCreationWizard
- Visualizzazione e persistenza in CharacterSheetUI
"""

import os
import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk

from common.theme import setup_theme
from common.backgrounds_data import (
    BACKGROUNDS,
    PERSONAL_QUESTS,
    CHARACTER_SECRETS,
    PARTY_TIES,
    TRINKETS,
    generate_backstory
)
from client.character_manager import CharacterManager, Character
from client.character_creation_wizard import CharacterCreationWizard
from client.character_sheet_ui import CharacterSheetUI


class TestBackgroundAndNarrative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
            setup_theme(cls.root)
        except (tk.TclError, Exception):
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def setUp(self):
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        self.mgr = MagicMock(spec=CharacterManager)
        self.mgr.add_character = MagicMock()

    def test_backgrounds_data_structure(self):
        """Verifica la completezza dei dati dei background ufficiali 5e."""
        expected_bgs = [
            "Accolito", "Criminale / Spia", "Eroe Popolare", "Nobile",
            "Saggio", "Soldato", "Marinaio", "Forestiero (Outlander)",
            "Monello (Urchin)", "Artigiano della Gilda", "Intrattenitore",
            "Eremita", "Ciarlatano", "Personalizzato"
        ]
        for bg in expected_bgs:
            self.assertIn(bg, BACKGROUNDS, f"Background {bg} mancante nel catalogo")
            data = BACKGROUNDS[bg]
            self.assertTrue(len(data["skills"]) >= 2, f"{bg} deve avere almeno 2 abilità")
            self.assertTrue(len(data["feature_name"]) > 0, f"{bg} deve avere un nome di privilegio")
            self.assertTrue(len(data["feature_desc"]) > 0, f"{bg} deve avere una descrizione di privilegio")
            self.assertTrue(len(data["traits"]) > 0, f"{bg} deve avere tratti ruolistici")
            self.assertTrue(len(data["ideals"]) > 0, f"{bg} deve avere ideali")
            self.assertTrue(len(data["bonds"]) > 0, f"{bg} deve avere legami")
            self.assertTrue(len(data["flaws"]) > 0, f"{bg} deve avere difetti")

    def test_narrative_tables_presence(self):
        """Verifica le tabelle dei ganci narrativi, segreti, legami e cimeli."""
        self.assertTrue(len(PERSONAL_QUESTS) >= 8)
        self.assertTrue(len(CHARACTER_SECRETS) >= 8)
        self.assertTrue(len(PARTY_TIES) >= 6)
        self.assertTrue(len(TRINKETS) >= 10)

    def test_generate_backstory_function(self):
        """Verifica che la funzione di composizione automatica generi una biografia ricca."""
        story = generate_backstory(
            name="Valeros",
            race="Umano",
            char_class="Guerriero",
            background="Soldato",
            origin_place="Forte delle Colline",
            trait="Ho storie di guerra per ogni occasione.",
            ideal="Cameratismo: proteggo i miei compagni.",
            bond="Combatto per onorare il mio vecchio reggimento.",
            flaw="Disprezzo chi non ha mai provato il fango del fronte.",
            quest="Vendetta contro il nemico giurato.",
            secret="Erede nascosto di un casato nobile.",
            trinket="Una medaglia d'argento spezzata."
        )
        self.assertIn("Valeros", story)
        self.assertIn("Guerriero", story)
        self.assertIn("Soldato", story)
        self.assertIn("Forte delle Colline", story)
        self.assertIn("Cameratismo", story)
        self.assertIn("Erede nascosto", story)
        self.assertTrue(len(story.split("\n\n")) >= 2, "La backstory deve essere articolata in più paragrafi")

    def test_wizard_background_step_ui_and_assignment(self):
        """Verifica che il Passo 4 del Wizard carichi il background e assegni competenze e privilegi."""
        wiz = CharacterCreationWizard(self.root, self.mgr, on_complete_callback=lambda c: None)
        
        # Passo 4: Background & Competenze (indice 3)
        wiz.current_step = 3
        wiz.show_step()
        
        # Selezioniamo il background Soldato
        wiz.bg_name_var.set("Soldato")
        self.assertEqual(wiz.char_data["background"], "Soldato")
        self.assertIn("Atletica", wiz.char_data["background_skills"])
        self.assertIn("Intimidire", wiz.char_data["background_skills"])
        self.assertEqual(wiz.char_data["background_feature_name"], "Grado Militare")
        
        # Test tiro casuale di tutti i tratti
        wiz._roll_all_roleplay_traits()
        self.assertTrue(len(wiz.trait_var.get()) > 0)
        self.assertTrue(len(wiz.ideal_var.get()) > 0)
        self.assertTrue(len(wiz.bond_var.get()) > 0)
        self.assertTrue(len(wiz.flaw_var.get()) > 0)
        
        # Procediamo al passo successivo
        wiz.next_step()
        self.assertEqual(wiz.current_step, 4)
        wiz.destroy()

    def test_full_character_creation_with_narrative(self):
        """Verifica la creazione completa del personaggio con tutti i dettagli narrativi memorizzati."""
        created = []
        wiz = CharacterCreationWizard(self.root, self.mgr, on_complete_callback=lambda c: created.append(c))
        
        # Passo 4: Background
        wiz.current_step = 3
        wiz.show_step()
        wiz.bg_name_var.set("Nobile")
        wiz.trait_var.set("Mantengo sempre una postura regale.")
        wiz.ideal_var.set("Noblesse Oblige: proteggere i deboli.")
        wiz.bond_var.set("Restaurare l'onore del mio casato.")
        wiz.flaw_var.set("Fatico a comprendere la povertà altrui.")
        wiz.next_step()
        
        # Passo 5: Dettagli & Narrativa
        self.assertEqual(wiz.current_step, 4)
        wiz.name_var.set("Lord Brandon")
        wiz.camp_var.set("La Notte Eterna")
        wiz.origin_var.set("Città Alta di Neverwinter")
        wiz.quest_var.set("Riconquista del Retaggio Ereditario")
        wiz.secret_var.set("Marchio dell'Occulto")
        wiz.party_tie_var.set("Salvezza Reciproca")
        wiz.trinket_var.set("Un anello con sigillo nobiliare spezzato.")
        wiz.backstory_text.delete("1.0", tk.END)
        wiz.backstory_text.insert(tk.END, "Questa è la nobile e tragica storia di Lord Brandon.")
        
        with patch("common.messagebox.messagebox.showinfo"):
            wiz.next_step()
            import time
            for _ in range(30):
                if created:
                    break
                time.sleep(0.05)
                self.root.update()

        self.assertEqual(len(created), 1)
        char = created[0]
        self.assertEqual(char.name, "Lord Brandon")
        self.assertEqual(char.background, "Nobile")
        self.assertEqual(char.background_feature_name, "Privilegio di Posizione")
        self.assertIn("Storia", char.skills)
        self.assertEqual(char.skills["Storia"], 1)
        self.assertEqual(char.skills["Persuasione"], 1)
        self.assertIn("Privilegio di Background (Privilegio di Posizione)", char.features)
        self.assertEqual(char.personality_trait, "Mantengo sempre una postura regale.")
        self.assertEqual(char.ideal, "Noblesse Oblige: proteggere i deboli.")
        self.assertEqual(char.personal_quest, "Riconquista del Retaggio Ereditario")
        self.assertEqual(char.secret, "Marchio dell'Occulto")
        self.assertEqual(char.party_tie, "Salvezza Reciproca")
        self.assertEqual(char.trinket, "Un anello con sigillo nobiliare spezzato.")
        self.assertEqual(char.backstory, "Questa è la nobile e tragica storia di Lord Brandon.")
        self.assertIn("Biografia & Origini di Lord Brandon", char.journal_notes)
        self.assertIn("Privilegio di Posizione", char.features)
        
        # Oro iniziale: 25 mo del Nobile
        self.assertTrue(char.currency["MO"] >= 25)
        try:
            wiz.destroy()
        except Exception:
            pass

    def test_character_sheet_ui_header_background(self):
        """Verifica che la scheda PG visualizzi e persista Background e Allineamento nell'header."""
        char = Character(name="Eroe Prova", campaign="Campagna Test")
        char.background = "Marinaio"
        char.alignment = "CB"
        sheet = CharacterSheetUI(self.root, char, self.mgr)
        
        self.assertEqual(sheet.background_var.get(), "Marinaio")
        self.assertEqual(sheet.alignment_var.get(), "CB")
        
        # Modifica e salvataggio
        sheet.background_var.set("Eroe Popolare")
        sheet.alignment_var.set("LB")
        sheet.save_character()
        
        self.assertEqual(char.background, "Eroe Popolare")
        self.assertEqual(char.alignment, "LB")
        sheet.destroy()


    def test_advanced_backstory_multi_styles_and_coherence(self):
        """Verifica la coerenza avanzata dei capitoli narrativi, degli stili e della pulizia etichette."""
        from common.backgrounds_data import generate_backstory, NARRATIVE_STYLES
        
        # Stile Dark Fantasy con Tiefling Warlock
        story_dark = generate_backstory(
            name="Morvath",
            race="Tiefling",
            char_class="Warlock",
            background="Criminale / Spia",
            origin_place="Bassifondi di Baldur's Gate",
            trait="Controllo sempre ogni via di fuga.",
            ideal="Libertà: le catene vanno spezzate. (Caotico)",
            bond="Qualcuno è stato incastrato per un mio colpo.",
            flaw="Non riesco a fidarmi di nessuno.",
            quest="Maledizione da Spezzare",
            secret="Patto dell'Ombra",
            party_tie="Salvezza Reciproca",
            trinket="Una lettera con ceralacca nera mai aperta.",
            narrative_style="dark",
            include_headers=True
        )
        self.assertIn("Morvath", story_dark)
        self.assertIn("Tiefling", story_dark)
        self.assertIn("Warlock", story_dark)
        self.assertIn("Bassifondi di Baldur's Gate", story_dark)
        self.assertIn("Libertà", story_dark)
        # Verifica che (Caotico) sia stato ripulito per eleganza
        self.assertNotIn("(Caotico)", story_dark)
        self.assertIn("I. Origini e Retaggio", story_dark)
        self.assertIn("V. L'Anima dell'Eroe", story_dark)
        self.assertTrue(len(story_dark.split("\n\n")) >= 5)

        # Stile Picaresco con Halfling Ladro
        story_pic = generate_backstory(
            name="Regis",
            race="Halfling",
            char_class="Ladro",
            background="Monello (Urchin)",
            origin_place="Luskan",
            narrative_style="picaresque",
            include_headers=False
        )
        self.assertIn("Regis", story_pic)
        self.assertIn("Halfling", story_pic)
        self.assertIn("Ladro", story_pic)
        self.assertTrue(len(story_pic.split("\n\n")) >= 4)

    def test_character_sheet_generate_backstory_button(self):
        """Verifica che la scheda PG possa generare la biografia guidata direttamente nel diario."""
        char = Character(name="Bruenor", campaign="Faerun")
        char.race = "Nano"
        char.char_class = "Guerriero"
        char.background = "Nobile"
        char.personality_trait = "Orgoglioso della mia casata."
        char.ideal = "Rispetto: per gli antenati. (Legale)"
        
        sheet = CharacterSheetUI(self.root, char, self.mgr)
        self.assertTrue(hasattr(sheet, "_generate_character_backstory"))
        with patch("common.messagebox.messagebox.showinfo"), patch("common.messagebox.messagebox.askyesno", return_value=True):
            sheet._generate_character_backstory()
        
        journal_text = sheet.text_widgets["journal_notes"].get("1.0", tk.END)
        self.assertIn("Bruenor", journal_text)
        self.assertIn("Nano", journal_text)
        self.assertIn("Guerriero", journal_text)
        sheet.destroy()

if __name__ == "__main__":
    unittest.main()

