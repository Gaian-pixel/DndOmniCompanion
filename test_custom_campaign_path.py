import unittest
import os
import shutil
import tempfile
import tkinter as tk
from unittest.mock import patch, MagicMock

from common.campaign import Campaign, DEFAULT_CAMPAIGNS_DIR, slugify
from server.campaign_editor_ui import CampaignEditorDialog, CampaignSelectorDialog


class TestCustomCampaignPath(unittest.TestCase):
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
        self.temp_dir = tempfile.mkdtemp(prefix="dnd_test_camp_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_campaign_save_and_load_custom_folder(self):
        custom_path = os.path.join(self.temp_dir, "CustomAdventure_123")
        camp = Campaign(name="Le Foreste Perdute", folder_path=custom_path)
        camp.description = "Un'avventura in una foresta misteriosa."
        camp.add_scene("Radura Antica", "maps/faerun.json", "Una radura sacra.")

        saved_path = camp.save()
        self.assertEqual(os.path.abspath(saved_path), os.path.abspath(custom_path))
        self.assertTrue(os.path.exists(os.path.join(custom_path, "campaign.json")))

        # Test caricamento dalla cartella
        loaded_by_dir = Campaign.load(custom_path)
        self.assertEqual(loaded_by_dir.name, "Le Foreste Perdute")
        self.assertEqual(os.path.abspath(loaded_by_dir.folder_path), os.path.abspath(custom_path))
        self.assertEqual(len(loaded_by_dir.scenes), 1)

        # Test caricamento diretto dal manifest campaign.json
        manifest_file = os.path.join(custom_path, "campaign.json")
        loaded_by_file = Campaign.load(manifest_file)
        self.assertEqual(loaded_by_file.name, "Le Foreste Perdute")
        self.assertEqual(os.path.abspath(loaded_by_file.folder_path), os.path.abspath(custom_path))

    def test_campaign_editor_custom_path_ui(self):
        if not self.root:
            self.skipTest("Tkinter display not available")

        custom_folder = os.path.join(self.temp_dir, "MyCustomCampaignFolder")
        camp = Campaign(name="Spedizione al Picco del Tuono", folder_path=custom_folder)

        saved_results = []
        def on_saved(c):
            saved_results.append(c)

        editor = CampaignEditorDialog(self.root, campaign=camp, on_save_callback=on_saved)

        # Verifichiamo che il campo ent_folder_path sia presente e contenga il percorso custom
        self.assertTrue(hasattr(editor, "ent_folder_path"))
        self.assertEqual(os.path.abspath(editor.ent_folder_path.get()), os.path.abspath(custom_folder))
        self.assertTrue(editor.is_custom_folder_path)

        # Cambiamo il percorso manualmente nel campo di testo
        another_custom_folder = os.path.join(self.temp_dir, "AnotherPath_99")
        editor.ent_folder_path.delete(0, tk.END)
        editor.ent_folder_path.insert(0, another_custom_folder)
        editor._on_folder_path_typed()

        # Eseguiamo il salvataggio
        with patch("common.messagebox.messagebox.showinfo") as mock_info:
            editor.save_campaign()
            self.assertTrue(mock_info.called)

        # Verifichiamo che sia stato salvato nella cartella decisa dal master
        self.assertTrue(os.path.exists(os.path.join(another_custom_folder, "campaign.json")))
        self.assertEqual(len(saved_results), 1)
        self.assertEqual(os.path.abspath(saved_results[0].folder_path), os.path.abspath(another_custom_folder))

        editor.destroy()

    def test_campaign_editor_save_as(self):
        if not self.root:
            self.skipTest("Tkinter display not available")

        camp = Campaign(name="Fortezza delle Ombre")
        editor = CampaignEditorDialog(self.root, campaign=camp)

        save_as_target = os.path.join(self.temp_dir, "SaveAsFolder")

        with patch("tkinter.filedialog.askdirectory", return_value=save_as_target), \
             patch("common.messagebox.messagebox.showinfo"):
            editor.save_campaign_as()

        self.assertTrue(os.path.exists(os.path.join(save_as_target, "campaign.json")))
        self.assertEqual(os.path.abspath(editor.campaign.folder_path), os.path.abspath(save_as_target))
        self.assertEqual(os.path.abspath(editor.ent_folder_path.get()), os.path.abspath(save_as_target))

        editor.destroy()

    def test_campaign_selector_custom_path_loading(self):
        if not self.root:
            self.skipTest("Tkinter display not available")

        custom_folder = os.path.join(self.temp_dir, "SelectorTestCamp")
        c = Campaign(name="Campagna Esterna", folder_path=custom_folder)
        c.description = "Descrizione esterna"
        c.save()

        selected_callback_camps = []
        selector = CampaignSelectorDialog(self.root, on_select_callback=lambda camp: selected_callback_camps.append(camp))

        # Simuliamo selezione da percorso custom
        manifest_path = os.path.join(custom_folder, "campaign.json")
        with patch("tkinter.filedialog.askopenfilename", return_value=manifest_path):
            selector.load_from_custom_path()

        # Deve essere aggiunta alla lista e selezionata
        self.assertIsNotNone(selector.selected_campaign)
        self.assertEqual(selector.selected_campaign.name, "Campagna Esterna")
        self.assertEqual(os.path.abspath(selector.selected_campaign.folder_path), os.path.abspath(custom_folder))

        selector.destroy()


if __name__ == "__main__":
    unittest.main()
