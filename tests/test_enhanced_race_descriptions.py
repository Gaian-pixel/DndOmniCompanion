# tests/test_enhanced_race_descriptions.py
"""
Test completi per le descrizioni arricchite delle Razze di D&D 5e:
- Completezza e autenticità del catalogo delle 9 Razze in common/races_data.py
- Validità dei Bonus alle Caratteristiche, Velocità, Taglia, Sensi e Tratti Razziali
- Campi arricchiti: Sinergie di Classe, Sottorazze, Longevità e Lore Narrativa
- Formattazione e consistenza della stringa retrocompatibile 'desc'
- Funzioni get_race_info e get_race_names
- Retrocompatibilità dell'import da client.character_creation_wizard
- Funzionamento del Passo 1 (Scelta Razza) del CharacterCreationWizard con canvas scorrevole,
  pulsanti di navigazione rapida, tabella comparativa modale e aggiornamento reattivo dei dettagli.
- Applicazione corretta dei bonus razziali alla scheda finale del personaggio.
"""

import time
import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk

from common.theme import setup_theme
from common.races_data import RACES, get_race_info, get_race_names
from client.character_manager import CharacterManager, Character
from client.character_creation_wizard import CharacterCreationWizard, RACES as WIZARD_RACES


class TestEnhancedRaceDescriptions(unittest.TestCase):
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
        self.expected_races = [
            "Umano", "Elfo", "Nano", "Halfling", "Draconide", "Gnomo",
            "Mezzelfo", "Mezzorco", "Tiefling"
        ]

    def test_all_9_races_present(self):
        """Verifica la presenza di tutte le 9 razze canoniche 5e nel catalogo."""
        self.assertEqual(len(RACES), 9)
        names = get_race_names()
        self.assertEqual(len(names), 9)
        for r_name in self.expected_races:
            self.assertIn(r_name, RACES, f"Razza {r_name} mancante nel dizionario RACES")
            self.assertIn(r_name, names, f"Razza {r_name} mancante in get_race_names()")

    def test_race_data_fields_completeness(self):
        """Verifica che ogni razza contenga tutti i campi strutturati e descrizioni ricche."""
        expected_speeds = {
            "Umano": 30,
            "Elfo": 30,
            "Nano": 25,
            "Halfling": 25,
            "Draconide": 30,
            "Gnomo": 25,
            "Mezzelfo": 30,
            "Mezzorco": 30,
            "Tiefling": 30
        }

        for r_name, info in RACES.items():
            # Velocità
            self.assertEqual(info["speed"], expected_speeds[r_name], f"Velocità errata per {r_name}")
            
            # Taglia
            self.assertIn(info["size"].split()[0], ["Media", "Piccola"], f"Taglia non valida per {r_name}")
            
            # Bonus di caratteristica
            bonuses = info["bonuses"]
            self.assertIsInstance(bonuses, dict)
            self.assertTrue(len(bonuses) >= 1, f"Nessun bonus caratteristica per {r_name}")
            self.assertTrue(len(info["bonuses_display"]) > 0)
            
            # Stringhe informative
            self.assertTrue(len(info["tagline"]) > 10, f"Tagline troppo breve per {r_name}")
            self.assertTrue(len(info["languages"]) > 0, f"Linguaggi mancanti per {r_name}")
            self.assertTrue(len(info["vision"]) > 0, f"Sensi mancanti per {r_name}")
            self.assertTrue(len(info["lifespan"]) > 10, f"Longevità mancante per {r_name}")
            self.assertTrue(len(info["synergies"]) > 15, f"Sinergie mancanti per {r_name}")
            
            # Lore narrativa ricca (> 100 caratteri)
            self.assertTrue(len(info["overview"]) >= 100, f"Overview troppo breve per {r_name}")
            
            # Tratti razziali (almeno 2 tratti con nome e descrizione dettagliata)
            self.assertTrue(len(info["traits"]) >= 2, f"{r_name} deve avere almeno 2 tratti razziali")
            for t_name, t_desc in info["traits"]:
                self.assertTrue(len(t_name) > 0, f"Nome tratto vuoto in {r_name}")
                self.assertTrue(len(t_desc) > 10, f"Descrizione tratto troppo breve in {r_name}")
                
            # Sottorazze
            self.assertTrue(len(info.get("subraces_preview", [])) >= 2, f"Meno di 2 sottorazze per {r_name}")
            
            # Campo retrocompatibile 'desc'
            desc = info["desc"]
            self.assertIn(info["bonuses_display"], desc)
            self.assertIn(str(info["speed"]), desc)
            self.assertIn("Tratti Razziali", desc)
            self.assertIn("Sottorazze", desc)
            self.assertIn("Sinergie di Classe", desc)

    def test_get_race_info_and_fallback(self):
        """Verifica il comportamento di get_race_info con razze note e fallback."""
        elf_info = get_race_info("Elfo")
        self.assertEqual(elf_info["speed"], 30)
        self.assertIn("elf", elf_info["overview"].lower())
        
        fallback_info = get_race_info("RazzaInesistente")
        self.assertEqual(fallback_info["speed"], 30) # Umano fallback
        self.assertIn("uman", fallback_info["overview"].lower())

    def test_backwards_compatibility_import(self):
        """Verifica che l'import diretto di RACES dal wizard rimanga identico."""
        self.assertIs(WIZARD_RACES, RACES)

    def test_wizard_step_race_ui_interaction(self):
        """Verifica l'interfaccia interattiva del Passo 1 (Razza) nel Wizard e la tabella comparativa."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
            
        mgr = MagicMock(spec=CharacterManager)
        wiz = CharacterCreationWizard(self.root, mgr, on_complete_callback=lambda c: None)
        
        # Passo 1: Scegli la Razza (indice 0)
        wiz.current_step = 0
        wiz.show_step()
        
        # Verifica che il canvas scorrevole sia attivo per il passo razza
        self.assertIsNotNone(wiz.scroll_canvas)
        
        # Verifica valore iniziale
        self.assertIn(wiz.race_var.get(), self.expected_races)
        
        # Selezioniamo "Nano"
        wiz.race_var.set("Nano")
        self.assertEqual(wiz.char_data["race"], "Nano")
        
        # Selezioniamo "Tiefling"
        wiz.race_var.set("Tiefling")
        self.assertEqual(wiz.char_data["race"], "Tiefling")
        
        # Apertura della finestra modale di confronto razze
        wiz.open_races_comparison_dialog()
        top_windows = [w for w in wiz.winfo_children() if isinstance(w, tk.Toplevel)]
        self.assertTrue(len(top_windows) > 0)
        for tw in top_windows:
            tw.destroy()

        # Passiamo al passo successivo (Classe)
        wiz.next_step()
        self.assertEqual(wiz.current_step, 1)
        
        wiz.destroy()

    def test_character_creation_race_bonuses_application(self):
        """Verifica che i bonus di caratteristica razziali vengano applicati correttamente al personaggio finale."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")

        mgr = MagicMock(spec=CharacterManager)
        created_characters = []
        wiz = CharacterCreationWizard(self.root, mgr, on_complete_callback=lambda c: created_characters.append(c))

        # Passo 5: Dettagli & Completamento
        wiz.current_step = 4
        wiz.show_step()

        # Mezzorco: +2 Forza, +1 Costituzione
        wiz.char_data["name"] = "Grommash"
        wiz.char_data["race"] = "Mezzorco"
        wiz.char_data["char_class"] = "Guerriero"
        # Base array: FOR 15, DES 14, COS 13, INT 12, SAG 10, CAR 8
        wiz.char_data["attributes"] = {"FOR": 15, "DES": 14, "COS": 13, "INT": 12, "SAG": 10, "CAR": 8}
        
        wiz.name_var.set("Grommash")
        
        with patch("common.messagebox.messagebox.showinfo"):
            wiz.next_step()
            for _ in range(30):
                if created_characters:
                    break
                time.sleep(0.05)
                self.root.update()

        self.assertEqual(len(created_characters), 1)
        char = created_characters[0]
        self.assertEqual(char.race, "Mezzorco")
        # FOR finale = 15 base + 2 bonus Mezzorco = 17
        self.assertEqual(char.attributes["FOR"], 17)
        # COS finale = 13 base + 1 bonus Mezzorco = 14
        self.assertEqual(char.attributes["COS"], 14)
        # Velocità = 30
        self.assertEqual(char.speed, 30)
        
        wiz.destroy()


if __name__ == "__main__":
    unittest.main()
