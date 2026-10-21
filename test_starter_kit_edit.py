# test_starter_kit_edit.py
import unittest
from unittest.mock import patch, MagicMock
import tkinter as tk
from common.campaign import Campaign
from common.starter_equipment import DEFAULT_CAMPAIGN_STARTER_KIT
from common.theme import setup_theme
from server.dm_dialogs import CampaignStarterKitDialog, StarterKitItemEditorDialog

class TestStarterKitEdit(unittest.TestCase):
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

    def test_campaign_default_starter_kit_initialization(self):
        camp = Campaign(name="Nuova Campagna Test")
        # Simula creazione in CampaignEditorDialog
        if not camp.starter_kit:
            camp.starter_kit = [item.copy() for item in DEFAULT_CAMPAIGN_STARTER_KIT]
        self.assertGreaterEqual(len(camp.starter_kit), 1)
        item_names = [it["name"] for it in camp.starter_kit]
        self.assertIn("Pozione di Cura", item_names)

    @patch("server.dm_dialogs.messagebox.showwarning")
    def test_starter_kit_item_editor_dialog_save(self, mock_warning):
        saved_data = {}
        def on_save_handler(data):
            nonlocal saved_data
            saved_data = data

        initial_item = {
            "name": "Pozione di Cura",
            "type": "Consumabile",
            "qty": 2,
            "weight": 0.5,
            "desc": "Cura 2d4+2 PF"
        }

        dlg = StarterKitItemEditorDialog(self.root, item_data=initial_item, on_save=on_save_handler)
        self.assertEqual(dlg.ent_name.get(), "Pozione di Cura")
        self.assertEqual(dlg.cb_type.get(), "Consumabile")
        self.assertEqual(int(dlg.sp_qty.get()), 2)
        self.assertEqual(float(dlg.sp_weight.get()), 0.5)

        # Modifica i valori
        dlg.ent_name.delete(0, tk.END)
        dlg.ent_name.insert(0, "Pozione di Cura Maggiore")
        dlg.sp_qty.delete(0, tk.END)
        dlg.sp_qty.insert(0, "4")
        dlg.sp_weight.delete(0, tk.END)
        dlg.sp_weight.insert(0, "1.5")
        dlg.txt_desc.delete("1.0", tk.END)
        dlg.txt_desc.insert("1.0", "Cura 4d4+4 PF")

        dlg._save_and_close()

        self.assertEqual(saved_data.get("name"), "Pozione di Cura Maggiore")
        self.assertEqual(saved_data.get("qty"), 4)
        self.assertEqual(saved_data.get("weight"), 1.5)
        self.assertEqual(saved_data.get("desc"), "Cura 4d4+4 PF")

    @patch("server.dm_dialogs.messagebox.showinfo")
    def test_campaign_starter_kit_dialog_edit_and_save(self, mock_info):
        initial_items = [
            {"name": "Spada Corta", "type": "Arma", "qty": 1, "weight": 2.0, "desc": "1d6 perforante"},
            {"name": "Torcia", "type": "Equipaggiamento", "qty": 3, "weight": 1.0, "desc": "Luce 20ft"}
        ]
        saved_items = []
        def on_saved(items):
            nonlocal saved_items
            saved_items = items

        dlg = CampaignStarterKitDialog(self.root, initial_items=initial_items, on_save_callback=on_saved)
        self.assertEqual(len(dlg.items), 2)

        # Modifica il primo oggetto
        dlg.items[0]["qty"] = 2
        dlg.items[0]["name"] = "Due Spade Corte"
        dlg.refresh_list()

        # Aggiungi un nuovo oggetto
        dlg.items.append({
            "name": "Corda", "type": "Equipaggiamento", "qty": 1, "weight": 10.0, "desc": "15 metri"
        })
        dlg.refresh_list()
        self.assertEqual(len(dlg.items), 3)

        # Salva
        dlg.on_save()
        self.assertEqual(len(saved_items), 3)
        self.assertEqual(saved_items[0]["name"], "Due Spade Corte")
        self.assertEqual(saved_items[0]["qty"], 2)
        self.assertEqual(saved_items[2]["name"], "Corda")

    @patch("server.compendium_ui.CompendiumDialog")
    def test_campaign_starter_kit_add_from_compendium(self, mock_comp_dialog):
        initial_items = [
            {"name": "Torcia", "type": "Equipaggiamento", "qty": 1, "weight": 1.0, "desc": "Luce"}
        ]
        dlg = CampaignStarterKitDialog(self.root, initial_items=initial_items)
        self.assertEqual(len(dlg.items), 1)

        captured_callback = None
        def mock_init(master, on_import_callback=None, is_dm=True, initial_category=None, action_label=None):
            nonlocal captured_callback
            captured_callback = on_import_callback
            mock_inst = MagicMock()
            return mock_inst

        mock_comp_dialog.side_effect = mock_init

        dlg.on_add_from_compendium()
        self.assertIsNotNone(captured_callback)

        # Simula importazione dal compendio
        sample_srd_item = {
            "name": "Longsword",
            "equipment_category": {"name": "Weapon"},
            "weight": 3.0,
            "damage": {"damage_dice": "1d8", "damage_type": {"name": "Slashing"}},
            "properties": [{"name": "Versatile"}],
            "desc": "Spada a una mano versatile."
        }
        captured_callback(sample_srd_item, "Equipaggiamento")

        self.assertEqual(len(dlg.items), 2)
        added = dlg.items[1]
        self.assertEqual(added["name"], "Longsword")
        self.assertEqual(added["type"], "Arma")
        self.assertEqual(added["weight"], 3.0)
        self.assertIn("1d8", added["desc"])
        self.assertIn("Versatile", added["desc"])

if __name__ == '__main__':
    unittest.main()
