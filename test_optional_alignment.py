# test_optional_alignment.py
"""
Test per l'allineamento opzionale e il suggerimento etico in Crea Personaggio/Giocatore:
- Verifica che l'allineamento sia opzionale (default vuoto / non specificato).
- Verifica che se non specificato, il personaggio creato abbia alignment == "".
- Verifica che se selezionato, l'allineamento venga registrato correttamente.
- Verifica la presenza del messaggio/suggerimento che specifica che l'allineamento è solo una linea guida.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk

from common.theme import setup_theme
from client.character_manager import CharacterManager, Character
from client.character_creation_wizard import (
    CharacterCreationWizard,
    ALIGNMENT_NONE,
    ALIGNMENTS
)


class TestOptionalAlignmentCreation(unittest.TestCase):
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
            self.skipTest("Tkinter not available in headless environment")
        self.mgr = MagicMock(spec=CharacterManager)
        self.mgr.add_character = MagicMock()

    def test_alignment_none_in_alignments(self):
        """Verifica che ALIGNMENT_NONE sia presente tra le opzioni e sia la prima opzione."""
        self.assertIn(ALIGNMENT_NONE, ALIGNMENTS)
        align_keys = list(ALIGNMENTS.keys())
        self.assertEqual(align_keys[0], ALIGNMENT_NONE)

    def test_wizard_default_alignment_is_optional_empty(self):
        """Verifica che il wizard inizializzi l'allineamento come opzionale (stringa vuota)."""
        created = []
        wiz = CharacterCreationWizard(self.root, self.mgr, on_complete_callback=lambda c: created.append(c))
        
        self.assertEqual(wiz.char_data["alignment"], "")
        
        # Andiamo all'ultimo passo (Dettagli & Narrativa)
        wiz.current_step = len(wiz.steps) - 1
        wiz.show_step()
        
        # Verifica che il combobox sia impostato su ALIGNMENT_NONE
        self.assertEqual(wiz.align_var.get(), ALIGNMENT_NONE)

        # Inseriamo nome valido
        wiz.name_var.set("Eroe Senza Allineamento")
        with patch("common.messagebox.messagebox.showinfo"):
            wiz.next_step()
            import time
            for _ in range(30):
                if created:
                    break
                time.sleep(0.05)
                self.root.update()
        
        # Verifica che il personaggio creato abbia allineamento vuoto
        self.assertEqual(len(created), 1)
        char = created[0]
        self.assertEqual(char.name, "Eroe Senza Allineamento")
        self.assertEqual(char.alignment, "")
        try:
            wiz.destroy()
        except Exception:
            pass

    def test_wizard_selected_alignment(self):
        """Verifica che se l'utente sceglie un allineamento specifico, questo venga registrato."""
        created = []
        wiz = CharacterCreationWizard(self.root, self.mgr, on_complete_callback=lambda c: created.append(c))
        
        wiz.current_step = len(wiz.steps) - 1
        wiz.show_step()
        
        wiz.name_var.set("Paladino di Giustizia")
        wiz.align_var.set("LB (Legale Buono)")
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
        self.assertEqual(char.name, "Paladino di Giustizia")
        self.assertEqual(char.alignment, "LB")
        try:
            wiz.destroy()
        except Exception:
            pass

    def test_wizard_guideline_hint_displayed(self):
        """Verifica che nel passo 4 sia presente il suggerimento sulla linea guida dell'allineamento."""
        wiz = CharacterCreationWizard(self.root, self.mgr, on_complete_callback=lambda c: None)
        wiz.current_step = len(wiz.steps) - 1
        wiz.show_step()

        # Ispeziona i widget generati nel container
        all_labels = []
        def find_labels(widget):
            for child in widget.winfo_children():
                if isinstance(child, tk.Label) or isinstance(child, tk.ttk.Label if hasattr(tk, "ttk") else tk.Label):
                    txt = child.cget("text")
                    if txt:
                        all_labels.append(txt)
                find_labels(child)

        find_labels(wiz.container)
        combined_text = " ".join(all_labels).lower()
        
        self.assertIn("linea guida", combined_text)
        self.assertIn("non definisce per forza", combined_text)
        self.assertIn("opzionale", combined_text)
        wiz.destroy()


if __name__ == "__main__":
    unittest.main()
