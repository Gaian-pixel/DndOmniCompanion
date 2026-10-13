# test_campaign_system.py
"""
Test di unità e integrazione per il sistema di preparazione e gestione Campagne.
Verifica:
1. Modello dati Campaign (save, load, to_dict, from_dict)
2. Campagna starter predefinita 'La Cripta dei Sussurri'
3. Integrazione con GameState (apply_to_game_state, ripristino da sessione salvata)
4. Schieramento degli incontri preparati della campagna
5. Smoke test UI delle finestre CampaignEditorDialog e CampaignSelectorDialog
"""

import os
import sys
import shutil
import tempfile
import queue
import unittest
import tkinter as tk

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from common.campaign import Campaign, slugify, get_available_campaigns, create_sample_starter_campaign
from common.game_state import GameState, Player


class TestCampaignDataModel(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_campaign_create_save_load(self):
        camp = Campaign(name="Le Miniere della Perdizione", folder_path=os.path.join(self.test_dir, "miniere"))
        camp.level_range = "3-5"
        camp.description = "Esplorazione nelle viscere del monte."
        camp.dm_notes = "Il drago dorme nella stanza 12."
        camp.start_weather = "Tempesta"
        camp.start_date = {"year": 1493, "month": 5, "day": 10, "hour": 14}
        
        camp.add_scene("Ingresso Miniera", "maps/faerun.json", "Grata di ferro")
        camp.add_encounter(
            name="Pattuglia Coboldi",
            monsters=[{"name": "Coboldo", "count": 4, "hp": 5, "initiative": 2, "xp": 25}],
            act="Atto 1"
        )
        camp.add_quest(
            title="Trova la Gemma",
            description="Recupera la gemma rossa dal capo coboldo.",
            chapter="Atto 1",
            rewards={"xp": 200, "gp": 50}
        )
        camp.add_npc(
            name="Thrum",
            role="Minatore superstite",
            hp=12,
            ac=11,
            notes="Fornirà la mappa se curato."
        )
        camp.add_handout(
            title="Mappa del Vecchio Pozzo",
            content="Disegno su pelle di capra."
        )
        
        saved_path = camp.save()
        self.assertTrue(os.path.exists(os.path.join(saved_path, "campaign.json")))
        
        loaded = Campaign.load(saved_path)
        self.assertEqual(loaded.name, "Le Miniere della Perdizione")
        self.assertEqual(loaded.level_range, "3-5")
        self.assertEqual(loaded.start_weather, "Tempesta")
        self.assertEqual(loaded.start_date["year"], 1493)
        self.assertEqual(len(loaded.scenes), 1)
        self.assertEqual(len(loaded.encounters), 1)
        self.assertEqual(len(loaded.quests), 1)
        self.assertEqual(len(loaded.npcs), 1)
        self.assertEqual(len(loaded.handouts), 1)
        self.assertEqual(loaded.encounters[0]["name"], "Pattuglia Coboldi")

    def test_sample_starter_campaign_generation(self):
        sample = create_sample_starter_campaign(os.path.join(self.test_dir, "sample_camp"))
        self.assertEqual(sample.name, "La Cripta dei Sussurri")
        self.assertTrue(len(sample.scenes) >= 2)
        self.assertTrue(len(sample.encounters) >= 2)
        self.assertTrue(len(sample.quests) >= 2)
        self.assertTrue(len(sample.npcs) >= 2)
        self.assertTrue(len(sample.starter_kit) >= 3)
        
        camps = get_available_campaigns(self.test_dir)
        self.assertTrue(any(c["name"] == "La Cripta dei Sussurri" for c in camps))


class TestCampaignGameStateIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.q = queue.Queue()
        self.game_state = GameState(self.q)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_apply_campaign_to_game_state(self):
        camp = Campaign("Campagna Test", folder_path=self.test_dir)
        camp.start_weather = "Neve"
        camp.start_date = {"year": 1495, "month": 12, "day": 25, "hour": 22}
        camp.starter_kit = [{"name": "Pugnale Magico", "type": "Arma", "qty": 1, "weight": 1.0, "desc": "+1 al tiro"}]
        camp.add_quest("Salva Babbo Natale", "Libera l'elfo prigioniero")
        
        camp.apply_to_game_state(self.game_state)
        
        self.assertEqual(self.game_state.weather, "Neve")
        self.assertEqual(self.game_state.time_year, 1495)
        self.assertEqual(self.game_state.time_month, 12)
        self.assertEqual(self.game_state.time_day, 25)
        self.assertEqual(self.game_state.time_hour, 22)
        self.assertEqual(len(self.game_state.campaign_starter_kit), 1)
        self.assertEqual(self.game_state.campaign_starter_kit[0]["name"], "Pugnale Magico")
        self.assertEqual(len(self.game_state.quests), 1)
        self.assertEqual(self.game_state.active_campaign, camp)

    def test_session_save_and_restore_campaign(self):
        camp = Campaign("Campagna Persistente", folder_path=os.path.join(self.test_dir, "pers_camp"))
        camp.save()
        camp.apply_to_game_state(self.game_state)
        
        session_file = os.path.join(self.test_dir, "session_test.json")
        self.game_state.save_session(session_file)
        
        # Nuovo game state da ricaricare
        new_gs = GameState(self.q)
        new_gs.load_session(session_file)
        
        self.assertIsNotNone(new_gs.active_campaign)
        self.assertEqual(new_gs.active_campaign.name, "Campagna Persistente")


class TestCampaignUISmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_campaign_editor_and_selector_dialogs(self):
        from server.campaign_editor_ui import CampaignEditorDialog, CampaignSelectorDialog
        
        # Test Editor Dialog
        q = queue.Queue()
        gs = GameState(q)
        camp = Campaign(name="Campagna UI Test")
        
        editor = CampaignEditorDialog(self.root, campaign=camp, game_state=gs)
        self.root.update()
        self.assertEqual(editor.campaign.name, "Campagna UI Test")
        editor.destroy()
        self.root.update()
        
        # Test Selector Dialog
        selected = []
        selector = CampaignSelectorDialog(self.root, on_select_callback=lambda c: selected.append(c))
        self.root.update()
        self.assertTrue(hasattr(selector, "tree_camps"))
        selector.destroy()
        self.root.update()

    def test_launch_dm_with_campaign(self):
        """Verifica che DM_GUI si avvii con una campagna senza deadlock o schermata bianca."""
        from server.dm_gui import DM_GUI
        camp = Campaign.load("campaigns/la_cripta_dei_sussurri")
        
        top = tk.Toplevel(self.root)
        try:
            dm = DM_GUI(top, initial_campaign=camp)
            self.root.update()
            self.assertEqual(dm.server.game_state.active_campaign.name, "La Cripta dei Sussurri")
            self.assertIn("La Cripta dei Sussurri", dm.lbl_campaign_name.cget("text"))
            dm.server.stop()
            if getattr(dm, 'voice_client', None):
                dm.voice_client.stop()
        finally:
            top.destroy()
            self.root.update()


if __name__ == "__main__":
    unittest.main()
