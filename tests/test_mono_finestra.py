import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock, patch

from client.character_manager import Character, CharacterManager
from client.character_sheet_ui import CharacterSheetFrame, CharacterSheetUI
from client.character_manager_ui import CharacterManagerFrame, CharacterManagerDialog
from client.character_creation_wizard import CharacterCreationWizardFrame, CharacterCreationWizard
from server.campaign_editor_ui import CampaignSelectorFrame, CampaignSelectorDialog, CampaignEditorFrame, CampaignEditorDialog
from common.campaign import Campaign


class TestMonoFinestraArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception:
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            cls.root.destroy()

    def setUp(self):
        if not self.root:
            self.skipTest("Tkinter display not available")
        self.char = Character(name="Gimli")
        self.char.char_class = "Guerriero"
        self.char.level = 3
        self.char.race = "Nano"
        self.mgr = CharacterManager()

    def test_character_sheet_frame_and_ui_wrapper(self):
        """Verifica che CharacterSheetFrame possa essere incastonato in un Frame e che CharacterSheetUI sia un Toplevel retrocompatibile."""
        container = tk.Frame(self.root)
        container.pack()

        dock_called = []
        close_called = []
        detach_called = []

        frame = CharacterSheetFrame(
            container,
            character=self.char,
            manager=self.mgr,
            on_close_callback=lambda: close_called.append(True),
            on_detach_callback=lambda: detach_called.append(True),
            on_dock_callback=lambda: dock_called.append(True),
            is_overlay=True
        )
        frame.pack(fill=tk.BOTH, expand=True)

        self.assertIsInstance(frame, ttk.Frame)
        self.assertTrue(hasattr(frame, "name_var"))
        self.assertEqual(frame.name_var.get(), "Gimli")

        # Test delegazione e chiusura
        frame.close_sheet()
        self.assertEqual(len(close_called), 1)

        # Test CharacterSheetUI (Toplevel wrapper)
        ui = CharacterSheetUI(self.root, self.char, self.mgr)
        self.assertIsInstance(ui, tk.Toplevel)
        self.assertTrue(hasattr(ui, "name_var"))
        self.assertEqual(ui.name_var.get(), "Gimli")
        self.assertTrue(hasattr(ui, "load_data"))
        self.assertTrue(hasattr(ui, "currency_vars"))
        ui.destroy()
        container.destroy()

    def test_character_manager_frame_and_dialog(self):
        """Verifica CharacterManagerFrame in modalità incorporata e CharacterManagerDialog modale."""
        container = tk.Frame(self.root)
        container.pack()

        close_called = []
        wizard_called = []
        selected_called = []

        frame = CharacterManagerFrame(
            container,
            manager=self.mgr,
            on_select_callback=lambda c: selected_called.append(c),
            on_close_callback=lambda: close_called.append(True),
            on_create_wizard_callback=lambda: wizard_called.append(True),
            is_embedded=True
        )
        frame.pack(fill=tk.BOTH, expand=True)

        self.assertIsInstance(frame, tk.Frame)
        self.assertTrue(hasattr(frame, "tree"))

        frame.create_wizard_character()
        self.assertEqual(len(wizard_called), 1)

        frame.close_view()
        self.assertEqual(len(close_called), 1)

        # Test Dialog modale
        dlg = CharacterManagerDialog(self.root, manager=self.mgr)
        self.assertIsInstance(dlg, tk.Toplevel)
        self.assertTrue(hasattr(dlg, "tree"))
        dlg.destroy()
        container.destroy()

    def test_character_creation_wizard_frame_and_dialog(self):
        """Verifica CharacterCreationWizardFrame incorporato e CharacterCreationWizard modale."""
        container = tk.Frame(self.root)
        container.pack()

        close_called = []
        done_called = []

        frame = CharacterCreationWizardFrame(
            container,
            manager=self.mgr,
            on_complete_callback=lambda c: done_called.append(c),
            on_close_callback=lambda: close_called.append(True),
            is_embedded=True
        )
        frame.pack(fill=tk.BOTH, expand=True)

        self.assertIsInstance(frame, ttk.Frame)
        self.assertTrue(hasattr(frame, "char_data"))
        self.assertEqual(frame.current_step, 0)

        frame.close_wizard()
        self.assertEqual(len(close_called), 1)

        # Test Dialog modale
        wiz = CharacterCreationWizard(self.root, self.mgr, on_complete_callback=lambda c: None)
        self.assertIsInstance(wiz, tk.Toplevel)
        self.assertTrue(hasattr(wiz, "char_data"))
        wiz.destroy()
        container.destroy()

    def test_campaign_selector_and_editor_frames(self):
        """Verifica CampaignSelectorFrame e CampaignEditorFrame incorporabili e relativi Toplevel wrapper."""
        container = tk.Frame(self.root)
        container.pack()

        close_called = []
        edit_called = []
        select_called = []

        selector_frame = CampaignSelectorFrame(
            container,
            on_select_callback=lambda c: select_called.append(c),
            on_edit_callback=lambda c: edit_called.append(c),
            on_close_callback=lambda: close_called.append(True)
        )
        selector_frame.pack(fill=tk.BOTH, expand=True)

        self.assertIsInstance(selector_frame, tk.Frame)
        self.assertTrue(hasattr(selector_frame, "tree_camps"))

        selector_frame.close_selector()
        self.assertEqual(len(close_called), 1)

        # Test CampaignSelectorDialog
        s_dlg = CampaignSelectorDialog(self.root, on_select_callback=lambda c: None)
        self.assertIsInstance(s_dlg, tk.Toplevel)
        self.assertTrue(hasattr(s_dlg, "tree_camps"))
        s_dlg.destroy()

        # Test CampaignEditorFrame
        camp = Campaign(name="Campagna Mono-Finestra")
        editor_frame = CampaignEditorFrame(
            container,
            campaign=camp,
            on_close_callback=lambda: close_called.append("editor")
        )
        editor_frame.pack(fill=tk.BOTH, expand=True)
        self.assertIsInstance(editor_frame, tk.Frame)
        self.assertTrue(hasattr(editor_frame, "notebook"))
        editor_frame.close_editor()
        self.assertIn("editor", close_called)

        # Test CampaignEditorDialog
        e_dlg = CampaignEditorDialog(self.root, campaign=camp)
        self.assertIsInstance(e_dlg, tk.Toplevel)
        self.assertTrue(hasattr(e_dlg, "toggle_fullscreen"))
        self.assertTrue(hasattr(e_dlg, "exit_fullscreen"))
        e_dlg.destroy()

        container.destroy()

    def test_client_center_overlay_and_docking(self):
        """Verifica il comportamento dell'overlay centro-schermo e del docking/detaching nel Client."""
        from client.client import ClientGUI
        client = ClientGUI(self.root, initial_character=self.char)

        self.assertTrue(hasattr(client, "center_overlay_frame"))
        self.assertFalse(client.stats_overlay_visible)

        # Apertura overlay centro-schermo
        client.open_stats_dialog()
        self.assertTrue(client.stats_overlay_visible)
        self.assertIsNotNone(client.stats_sheet_frame)
        self.assertEqual(client.stats_window, client.stats_sheet_frame)

        # Toggle rapido: ri-chiamata chiude l'overlay
        client.open_stats_dialog()
        self.assertFalse(client.stats_overlay_visible)

        # Riapriamo e testiamo stacco finestra (detach)
        client.open_stats_dialog()
        self.assertTrue(client.stats_overlay_visible)
        client.detach_character_sheet()
        self.assertFalse(client.stats_overlay_visible)
        self.assertIsNotNone(client.stats_detached_window)
        self.assertIsInstance(client.stats_detached_window, tk.Toplevel)

        # Riaggancio alla mappa (dock)
        client.dock_character_sheet()
        self.assertTrue(client.stats_overlay_visible)
        self.assertIsNone(client.stats_detached_window)

        # Chiusura con Esc
        mock_event = MagicMock()
        client._on_key_escape(mock_event)
        self.assertFalse(client.stats_overlay_visible)

        for w in self.root.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
