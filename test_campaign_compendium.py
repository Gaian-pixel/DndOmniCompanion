# test_campaign_compendium.py
"""
Test di integrazione per l'aggiunta di elementi dal compendio 5e in 'Crea Campagna':
- Importazione equipaggiamento nello Starter Kit
- Importazione mostri/PNG dal compendio nei PNG chiave della campagna
- Importazione magie/oggetti/lore negli Handouts della campagna
- Consultazione globale dal compendio con routing intelligente dei tab
"""

import unittest
from unittest.mock import patch, MagicMock
import tkinter as tk
import queue

from common.theme import setup_theme
from common.campaign import Campaign
from common.game_state import GameState
from server.campaign_editor_ui import CampaignEditorDialog
from server.compendium_ui import CompendiumDialog

class TestCampaignCompendiumIntegration(unittest.TestCase):
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
        self.camp = Campaign(name="Campagna Compendium Test")
        self.q = queue.Queue()
        self.gs = GameState(self.q)
        self.editor = CampaignEditorDialog(self.root, campaign=self.camp, game_state=self.gs)

    def tearDown(self):
        if hasattr(self, "editor") and self.editor:
            try:
                self.editor.destroy()
            except Exception:
                pass

    def test_compendium_dialog_params(self):
        """Verifica che CompendiumDialog accetti initial_category e action_label."""
        with patch.object(CompendiumDialog, "fetch_list"):
            dlg = CompendiumDialog(
                self.root,
                on_import_callback=lambda d, c: None,
                is_dm=True,
                initial_category="Equipaggiamento",
                action_label="➕ Aggiungi al Kit"
            )
            self.assertEqual(dlg.initial_category, "Equipaggiamento")
            self.assertEqual(dlg.action_label, "➕ Aggiungi al Kit")
            self.assertEqual(dlg.category_var.get(), "Equipaggiamento")
            dlg.destroy()

    def test_import_starter_kit_from_compendium_data(self):
        """Verifica parsing e inserimento di un'arma nello starter kit della campagna."""
        initial_count = len(self.camp.starter_kit)
        weapon_data = {
            "name": "Arco Lungo",
            "equipment_category": {"name": "Weapon"},
            "damage": {"damage_dice": "1d8", "damage_type": {"name": "Piercing"}},
            "properties": [{"name": "Due mani"}, {"name": "Pesante"}],
            "weight": 2.0,
            "desc": "Arco lungo in legno di tasso."
        }
        self.editor._import_starter_kit_data(weapon_data, "Equipaggiamento")
        self.assertEqual(len(self.camp.starter_kit), initial_count + 1)
        added = self.camp.starter_kit[-1]
        self.assertEqual(added["name"], "Arco Lungo")
        self.assertEqual(added["type"], "Arma")
        self.assertEqual(added["weight"], 2.0)
        self.assertIn("1d8", added["desc"])
        self.assertIn("Due mani", added["desc"])

    def test_import_npc_from_compendium_data(self):
        """Verifica parsing e inserimento di una creatura/PNG dal compendio."""
        initial_count = len(self.camp.npcs)
        monster_data = {
            "name": "Cultista Fanatico",
            "type": "humanoid",
            "subtype": "human",
            "hit_points": 33,
            "armor_class": 13,
            "alignment": "medium humanoid, lawful evil",
            "challenge_rating": 2,
            "senses": "Percezione passiva 11",
            "languages": "Comune",
            "actions": [{"name": "Pugnale Sacrificale"}, {"name": "Lancio Incantesimi"}]
        }
        self.editor._import_npc_data(monster_data, "Mostri")
        self.assertEqual(len(self.camp.npcs), initial_count + 1)
        added = self.camp.npcs[-1]
        self.assertEqual(added["name"], "Cultista Fanatico")
        self.assertEqual(added["hp"], 33)
        self.assertEqual(added["ac"], 13)
        self.assertIn("humanoid", added["role"])
        self.assertIn("lawful evil", added["notes"])
        self.assertIn("Pugnale Sacrificale", added["notes"])

    def test_import_handout_from_compendium_data(self):
        """Verifica parsing e inserimento di un oggetto magico/documento negli handouts."""
        initial_count = len(self.camp.handouts)
        magic_item_data = {
            "name": "Tomo dei Pensieri Limpidi",
            "rarity": "Molto Raro",
            "type": "Libro Magico",
            "desc": "Questo libro contiene esercizi per la memoria e la logica. Leggerlo aumenta l'Intelligenza di 2."
        }
        self.editor._import_handout_data(magic_item_data, "Oggetti Magici")
        self.assertEqual(len(self.camp.handouts), initial_count + 1)
        added = self.camp.handouts[-1]
        self.assertEqual(added["title"], "Tomo dei Pensieri Limpidi")
        self.assertIn("Molto Raro", added["content"])
        self.assertIn("Intelligenza di 2", added["content"])

    @patch("server.compendium_ui.CompendiumDialog")
    def test_open_global_compendium_modal(self, mock_comp_dialog):
        """Verifica apertura del compendio globale dalla toolbar della campagna."""
        captured_cb = None
        def mock_init(master, on_import_callback=None, is_dm=True, initial_category=None, action_label=None):
            nonlocal captured_cb
            captured_cb = on_import_callback
            return MagicMock()

        mock_comp_dialog.side_effect = mock_init
        self.editor.open_global_compendium()
        self.assertIsNotNone(captured_cb)

        # Selezioniamo il tab PNG
        tab_idx = None
        for i in range(self.editor.notebook.index("end")):
            if "png" in self.editor.notebook.tab(i, "text").lower():
                tab_idx = i
                break
        if tab_idx is not None:
            self.editor.notebook.select(tab_idx)

        npc_data = {
            "name": "Guardia Cittadina",
            "type": "humanoid",
            "hit_points": 11,
            "armor_class": 16
        }
        captured_cb(npc_data, "Mostri")
        self.assertTrue(any(n["name"] == "Guardia Cittadina" for n in self.camp.npcs))

if __name__ == '__main__':
    unittest.main()
