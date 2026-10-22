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


    def test_listbox_curselection_and_import_flow(self):
        """Verifica che la selezione e importazione da Listbox non sollevi AttributeError e invochi il callback."""
        imported = []
        def on_import(data, cat):
            imported.append((data, cat))

        with patch.object(CompendiumDialog, "fetch_list"):
            dlg = CompendiumDialog(
                self.root,
                on_import_callback=on_import,
                monsters_only=True,
                action_label="➕ Aggiungi all'Incontro"
            )

        # Inseriamo mostro fittizio nei current_items
        test_monster = {
            "name": "Goblin Esploratore",
            "hit_points": 7,
            "armor_class": 15,
            "challenge_rating": "1/4",
            "actions": [{"name": "Scimitarra", "desc": "+4 a colpire, 1d6+2 taglienti"}]
        }
        dlg.compendium_manager.get_items = MagicMock(return_value=[])
        dlg.current_items = [test_monster]
        dlg.update_listbox()

        # 1. Test nessun elemento selezionato
        dlg.listbox.selection_clear(0, tk.END)
        with patch("common.messagebox.messagebox.showinfo") as mock_info:
            dlg.import_selected()
            self.assertEqual(len(imported), 0)
            mock_info.assert_called_once()

        # 2. Seleziona elemento nella listbox (indice 0)
        dlg.listbox.selection_set(0)
        sel_item = dlg.get_selected_item()
        self.assertIsNotNone(sel_item)
        self.assertEqual(sel_item["name"], "Goblin Esploratore")

        # 3. Invoca _on_item_selected (simula click utente)
        dlg._on_item_selected()

        # 4. Invoca import_selected (simula click pulsante 'Aggiungi all'Incontro')
        with patch("common.messagebox.messagebox.showinfo"):
            dlg.import_selected()

        self.assertEqual(len(imported), 1)
        imported_data, imported_cat = imported[0]
        self.assertEqual(imported_data["name"], "Goblin Esploratore")
        self.assertEqual(imported_cat, "Mostri")
        dlg.destroy()

    def test_encounter_builder_import_integration(self):
        """Verifica che EncounterBuilderDialog riceva il mostro importato e lo registri correttamente."""
        eb = EncounterBuilderDialog(self.root, MagicMock())
        monster_data = {
            "name": "Orco Berserker",
            "hit_points": 30,
            "armor_class": 13,
            "challenge_rating": "2",
            "xp": 450,
            "dexterity": 12,
            "speed": 30
        }
        eb.on_monster_imported(monster_data, "Mostri")
        
        # Verifica presenza nell'elenco mostri dell'incontro
        names = [m["name"] for m in eb.monsters]
        self.assertIn("Orco Berserker", names)
        orco = next(m for m in eb.monsters if m["name"] == "Orco Berserker")
        self.assertEqual(orco["count"], 1)
        self.assertEqual(orco["hp"], 30)
        self.assertEqual(orco["ac"], 13)
        self.assertEqual(orco["xp"], 450)

        # Se importato nuovamente, incrementa il conteggio invece di duplicare
        eb.on_monster_imported(monster_data, "Mostri")
        self.assertEqual(orco["count"], 2)
        eb.destroy()

if __name__ == "__main__":
    unittest.main()

