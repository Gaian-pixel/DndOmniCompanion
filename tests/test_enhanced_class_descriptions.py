# tests/test_enhanced_class_descriptions.py
"""
Test completi per le descrizioni arricchite delle Classi di D&D 5e:
- Completezza e autenticità del catalogo delle 12 Classi in common/classes_data.py
- Validità dei Dadi Vita, Tiri Salvezza, Ruolo, Competenze e Privilegi di Livello 1
- Campi arricchiti: Complessità, Creazione Rapida (Quick Build), Dotazione Iniziale, Magia
- Filtri di categoria e funzione get_classes_by_category
- Formattazione e consistenza della stringa retrocompatibile 'desc'
- Funzioni get_class_info e get_class_names
- Retrocompatibilità dell'import da client.character_creation_wizard
- Funzionamento del Passo 2 (Scelta Classe) del CharacterCreationWizard con canvas scorrevole,
  filtri a pillola, tabella comparativa modale, pulsanti di navigazione rapida e aggiornamento reattivo dei dettagli.
"""

import time
import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk

from common.theme import setup_theme
from common.classes_data import (
    CLASSES,
    CLASS_CATEGORIES,
    get_class_info,
    get_class_names,
    get_classes_by_category
)
from client.character_manager import CharacterManager, Character
from client.character_creation_wizard import CharacterCreationWizard, CLASSES as WIZARD_CLASSES


class TestEnhancedClassDescriptions(unittest.TestCase):
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
        self.expected_classes = [
            "Barbaro", "Bardo", "Chierico", "Druido", "Guerriero", "Ladro",
            "Mago", "Monaco", "Paladino", "Ranger", "Stregone", "Warlock"
        ]

    def test_all_12_classes_present(self):
        """Verifica la presenza di tutte le 12 classi canoniche 5e nel catalogo."""
        self.assertEqual(len(CLASSES), 12)
        names = get_class_names()
        self.assertEqual(len(names), 12)
        for cls_name in self.expected_classes:
            self.assertIn(cls_name, CLASSES, f"Classe {cls_name} mancante nel dizionario CLASSES")
            self.assertIn(cls_name, names, f"Classe {cls_name} mancante in get_class_names()")

    def test_class_categories_and_filtering(self):
        """Verifica i filtri di categoria per raggruppare le classi per archetipo di gioco."""
        self.assertIn("Tutte", CLASS_CATEGORIES)
        self.assertIn("⚔️ Marziali", CLASS_CATEGORIES)
        self.assertIn("🔮 Incantatori", CLASS_CATEGORIES)
        self.assertIn("🛡️ Ibridi", CLASS_CATEGORIES)
        self.assertIn("🗡️ Esperti", CLASS_CATEGORIES)

        marziali = get_classes_by_category("⚔️ Marziali")
        self.assertIn("Guerriero", marziali)
        self.assertIn("Barbaro", marziali)
        self.assertIn("Monaco", marziali)

        incantatori = get_classes_by_category("🔮 Incantatori")
        self.assertIn("Mago", incantatori)
        self.assertIn("Chierico", incantatori)
        self.assertIn("Bardo", incantatori)
        self.assertIn("Stregone", incantatori)
        self.assertIn("Warlock", incantatori)
        self.assertIn("Druido", incantatori)

        ibridi = get_classes_by_category("🛡️ Ibridi")
        self.assertIn("Paladino", ibridi)
        self.assertIn("Ranger", ibridi)

        esperti = get_classes_by_category("🗡️ Esperti")
        self.assertIn("Ladro", esperti)

        tutte = get_classes_by_category("Tutte")
        self.assertEqual(len(tutte), 12)

    def test_class_data_fields_completeness(self):
        """Verifica che ogni classe contenga tutti i campi strutturati e descrizioni ricche."""
        expected_hit_dice = {
            "Barbaro": 12,
            "Bardo": 8,
            "Chierico": 8,
            "Druido": 8,
            "Guerriero": 10,
            "Ladro": 8,
            "Mago": 6,
            "Monaco": 8,
            "Paladino": 10,
            "Ranger": 10,
            "Stregone": 6,
            "Warlock": 8
        }

        for cls_name, info in CLASSES.items():
            # Dado Vita
            self.assertEqual(info["hd"], expected_hit_dice[cls_name], f"Dado Vita errato per {cls_name}")
            
            # Stringhe informative non vuote
            self.assertTrue(len(info["role"]) > 5, f"Ruolo non valido per {cls_name}")
            self.assertTrue(len(info["tagline"]) > 10, f"Tagline non valida per {cls_name}")
            self.assertTrue(len(info["primary_stat"]) > 2, f"Stat primaria non valida per {cls_name}")
            self.assertTrue(len(info["saving_throws"]) > 2, f"Tiri salvezza non validi per {cls_name}")
            self.assertTrue(len(info["armor_prof"]) > 0, f"Competenze armature mancanti per {cls_name}")
            self.assertTrue(len(info["weapon_prof"]) > 0, f"Competenze armi mancanti per {cls_name}")
            self.assertTrue(len(info["skills_info"]) > 5, f"Info abilità mancanti per {cls_name}")
            
            # Nuovi campi arricchiti: Complessità, Quick Build, Dotazione Iniziale
            self.assertTrue(len(info.get("complexity", "")) > 5, f"Complessità mancante per {cls_name}")
            self.assertTrue(len(info.get("quick_build", "")) > 20, f"Quick build mancante per {cls_name}")
            self.assertTrue(len(info.get("starter_gear", "")) > 15, f"Dotazione iniziale mancante per {cls_name}")
            self.assertIn(info.get("category"), ["Marziale", "Incantatore", "Ibrido", "Esperto"])

            # Panoramica narrativa ricca (> 100 caratteri)
            self.assertTrue(len(info["overview"]) >= 100, f"Panoramica troppo breve per {cls_name}")
            
            # Privilegi di livello 1 (almeno 2 privilegi con nome e testo)
            self.assertTrue(len(info["features_lvl1"]) >= 2, f"{cls_name} deve avere almeno 2 privilegi di 1° livello")
            for feat_name, feat_desc in info["features_lvl1"]:
                self.assertTrue(len(feat_name) > 0, f"Nome privilegio vuoto in {cls_name}")
                self.assertTrue(len(feat_desc) > 10, f"Descrizione privilegio troppo breve in {cls_name}")
                
            # Stile di gioco (> 100 caratteri)
            self.assertTrue(len(info["playstyle"]) >= 100, f"Stile di gioco troppo breve per {cls_name}")
            
            # Sottoclassi future (almeno 3 anteprime)
            self.assertTrue(len(info["subclasses_preview"]) >= 3, f"Meno di 3 sottoclassi per {cls_name}")
            
            # Campo retrocompatibile 'desc'
            desc = info["desc"]
            self.assertIn(f"d{info['hd']}", desc)
            self.assertIn("Tiri Salvezza", desc)
            self.assertIn("Privilegi di Livello 1", desc)
            self.assertIn("Stile di Gioco", desc)
            self.assertIn("Archetipi Futuri", desc)
            self.assertIn("Dotazione Iniziale", desc)
            self.assertIn("Creazione Rapida", desc)

    def test_get_class_info_and_fallback(self):
        """Verifica il comportamento di get_class_info con classi note e fallback."""
        pal_info = get_class_info("Paladino")
        self.assertEqual(pal_info["hd"], 10)
        self.assertIn("paladino", pal_info["overview"].lower())
        
        fallback_info = get_class_info("ClasseInesistente")
        self.assertEqual(fallback_info["hd"], 10) # Guerriero fallback
        self.assertIn("guerriero", fallback_info["overview"].lower())

    def test_backwards_compatibility_import(self):
        """Verifica che l'import diretto di CLASSES dal wizard rimanga identico."""
        self.assertIs(WIZARD_CLASSES, CLASSES)

    def test_wizard_step_class_ui_interaction_and_filter(self):
        """Verifica l'interfaccia interattiva del Passo 2 (Classe) nel Wizard e i filtri di categoria."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
            
        mgr = MagicMock(spec=CharacterManager)
        wiz = CharacterCreationWizard(self.root, mgr, on_complete_callback=lambda c: None)
        
        # Passo 2: Scegli la Classe (indice 1)
        wiz.current_step = 1
        wiz.show_step()
        
        # Verifica che il canvas scorrevole sia attivo per il passo classe
        self.assertIsNotNone(wiz.scroll_canvas)
        
        # Verifica valore iniziale
        self.assertIn(wiz.class_var.get(), self.expected_classes)
        
        # Selezioniamo "Mago"
        wiz.class_var.set("Mago")
        self.assertEqual(wiz.char_data["char_class"], "Mago")
        
        # Selezioniamo "Barbaro"
        wiz.class_var.set("Barbaro")
        self.assertEqual(wiz.char_data["char_class"], "Barbaro")
        
        # Apertura della finestra modale di confronto rapido
        wiz.open_classes_comparison_dialog()
        # Verifichiamo che la finestra modale sia stata aperta e poi la chiudiamo
        top_windows = [w for w in wiz.winfo_children() if isinstance(w, tk.Toplevel)]
        self.assertTrue(len(top_windows) > 0)
        for tw in top_windows:
            tw.destroy()

        # Passiamo al passo successivo
        wiz.next_step()
        self.assertEqual(wiz.current_step, 2)
        
        wiz.destroy()

    def test_character_creation_hp_with_enhanced_classes(self):
        """Verifica che la creazione del personaggio assegni correttamente PF massimi per ogni dado vita."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")

        mgr = MagicMock(spec=CharacterManager)
        created_characters = []
        wiz = CharacterCreationWizard(self.root, mgr, on_complete_callback=lambda c: created_characters.append(c))

        # Passo 5: Dettagli & Completamento
        wiz.current_step = 4
        wiz.show_step()

        wiz.char_data["name"] = "Thorgar"
        wiz.char_data["char_class"] = "Barbaro"
        # Con COS 14 (+2 mod) e d12 del Barbaro -> HP Max = 12 + 2 = 14
        wiz.char_data["attributes"] = {"FOR": 15, "DES": 14, "COS": 14, "INT": 10, "SAG": 12, "CAR": 8}
        
        wiz.name_var.set("Thorgar")
        
        with patch("common.messagebox.messagebox.showinfo"):
            wiz.next_step()
            for _ in range(30):
                if created_characters:
                    break
                time.sleep(0.05)
                self.root.update()

        self.assertEqual(len(created_characters), 1)
        char = created_characters[0]
        self.assertEqual(char.char_class, "Barbaro")
        # HP Barbaro = 12 (Dado Vita d12) + 2 (mod Costituzione) = 14
        self.assertEqual(char.hp_max, 14)
        self.assertEqual(char.hp_current, 14)
        
        wiz.destroy()


if __name__ == "__main__":
    unittest.main()
