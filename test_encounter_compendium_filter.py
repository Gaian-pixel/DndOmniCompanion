# test_encounter_compendium_filter.py
"""
Test per la limitazione delle categorie nel Compendio durante la creazione incontri:
- Solo Mostri e PNG ammessi (niente pozioni, armi, incantesimi, equipaggiamento)
- Verifica che EncounterBuilderDialog e CampaignEncounterDialog passino monsters_only=True
- Verifica che spawn_png_dialog passi monsters_only=True
- Verifica che la categoria PNG carichi sia custom PNG che umanoidi SRD
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import tkinter as tk
import queue

from common.theme import setup_theme
from common.campaign import Campaign
from common.game_state import GameState
from server.compendium_ui import CompendiumDialog
from server.encounter_builder_ui import EncounterBuilderDialog
from server.campaign_editor_ui import CampaignEncounterDialog


class TestEncounterCompendiumFilter(unittest.TestCase):
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

    def test_compendium_monsters_only_categories(self):
        """Verifica che con monsters_only=True ci siano solo Mostri e PNG, niente pozioni o armi."""
        with patch.object(CompendiumDialog, "fetch_list"):
            dlg = CompendiumDialog(
                self.root,
                monsters_only=True
            )
            cats = dlg._build_category_list()
            
            # Devono esserci Mostri e PNG
            self.assertIn("Mostri", cats)
            self.assertIn("PNG", cats)

            # NON devono esserci pozioni, armi, equipaggiamento, incantesimi, regole, classi, tratti, oggetti magici
            forbidden = [
                "Pozioni", "Armi", "Equipaggiamento", "Incantesimi",
                "Regole", "Classi", "Tratti", "Oggetti Magici",
                "📖 [PDF] Player's Handbook (PHB 2024)",
                "📖 [PDF] Dungeon Master's Guide (DMG 2024)",
                "📖 [PDF] Incantesimi dai Manuali",
                "📖 [PDF] Equipaggiamento & Tesori"
            ]
            for f in forbidden:
                self.assertNotIn(f, cats, f"La categoria '{f}' non dovrebbe apparire quando monsters_only=True")

            # I PDF consentiti devono essere solo bestiari / monster manual
            for cat in cats:
                if cat.startswith("📖 [PDF]"):
                    low = cat.lower()
                    self.assertTrue(
                        any(k in low for k in ["mostr", "monster", "creatur", "bestiar", "npc", "png"]),
                        f"Categoria PDF non pertinente a mostri trovata: {cat}"
                    )

            # Titolo finestra coerente
            self.assertIn("Avversari", dlg.title())
            dlg.destroy()

    def test_compendium_default_full_categories(self):
        """Verifica che il compendio normale (monsters_only=False) contenga tutte le categorie comprese le pozioni."""
        with patch.object(CompendiumDialog, "fetch_list"):
            dlg = CompendiumDialog(
                self.root,
                is_dm=True,
                monsters_only=False
            )
            cats = dlg._build_category_list()
            self.assertIn("Mostri", cats)
            self.assertIn("PNG", cats)
            self.assertIn("Pozioni", cats)
            self.assertIn("Armi", cats)
            self.assertIn("Incantesimi", cats)
            self.assertIn("Equipaggiamento", cats)
            dlg.destroy()

    @patch("server.compendium_ui.CompendiumDialog")
    def test_encounter_builder_opens_monsters_only(self, mock_compendium_dialog):
        """Verifica che EncounterBuilderDialog apra il Compendio con monsters_only=True."""
        eb = EncounterBuilderDialog(self.root, MagicMock())
        eb.open_compendium()
        
        mock_compendium_dialog.assert_called_once()
        _, kwargs = mock_compendium_dialog.call_args
        self.assertTrue(kwargs.get("monsters_only"), "EncounterBuilderDialog deve passare monsters_only=True")
        self.assertEqual(kwargs.get("initial_category"), "Mostri")
        eb.destroy()

    @patch("server.compendium_ui.CompendiumDialog")
    def test_campaign_encounter_dialog_opens_monsters_only(self, mock_compendium_dialog):
        """Verifica che CampaignEncounterDialog apra il Compendio con monsters_only=True."""
        encounter_data = {"name": "Agguato Goblin", "monsters": []}
        ced = CampaignEncounterDialog(self.root, encounter_data=encounter_data)
        ced.add_from_compendium()

        mock_compendium_dialog.assert_called_once()
        _, kwargs = mock_compendium_dialog.call_args
        self.assertTrue(kwargs.get("monsters_only"), "CampaignEncounterDialog deve passare monsters_only=True")
        self.assertEqual(kwargs.get("initial_category"), "Mostri")
        ced.destroy()

    def test_compendium_png_category_loading(self):
        """Verifica che la categoria PNG aggreghi PNG custom e umanoidi SRD."""
        with patch.object(CompendiumDialog, "fetch_list"):
            dlg = CompendiumDialog(self.root, monsters_only=True)
        
        dlg.category_var.set("PNG")
        dlg.compendium_manager.get_items = MagicMock(return_value=[
            {"name": "Oste Toblen", "type": "humanoid", "is_npc": True}
        ])
        
        # Invochiamo il vero fetch_list per la categoria PNG
        CompendiumDialog.fetch_list(dlg)
        
        import time
        for _ in range(30):
            if hasattr(dlg, "current_items") and dlg.current_items:
                break
            time.sleep(0.05)
            dlg.update()

        self.assertTrue(len(dlg.current_items) > 0)
        names = [item.get("name") for item in dlg.current_items]
        self.assertIn("Oste Toblen", names)
        dlg.destroy()

    @patch("server.compendium_ui.CompendiumDialog")
    def test_dm_gui_spawn_png_opens_monsters_only(self, mock_compendium_dialog):
        """Verifica che lo spawn PNG sulla mappa apra il compendio con monsters_only=True."""
        # Creiamo un mock DM_GUI essenziale
        from server.dm_gui import DM_GUI
        mock_gui = MagicMock()
        mock_gui.master = self.root
        
        # Invochiamo il metodo non-bound spawn_png_dialog su mock_gui
        DM_GUI.spawn_png_dialog(mock_gui)
        mock_compendium_dialog.assert_called_once()
        _, kwargs = mock_compendium_dialog.call_args
        self.assertTrue(kwargs.get("monsters_only"), "spawn_png_dialog deve passare monsters_only=True")
        self.assertEqual(kwargs.get("initial_category"), "Mostri")


if __name__ == "__main__":
    unittest.main()
