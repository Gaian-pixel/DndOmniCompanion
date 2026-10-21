import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch

from common.campaign import Campaign
from common.game_state import GameState
from server.dm_dialogs import CustomNPCDialog
from server.campaign_editor_ui import CampaignEditorDialog


class TestNPCSheetCreation(unittest.TestCase):
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

    def test_custom_npc_dialog_tabbed_structure(self):
        saved_sheet = {}
        def on_saved(sheet):
            saved_sheet.update(sheet)

        dialog = CustomNPCDialog(master=self.root, on_save_callback=on_saved)

        # 1. Verifica presenza dell'header profilo
        self.assertTrue(hasattr(dialog, "name_entry"))
        self.assertTrue(hasattr(dialog, "role_entry"))
        self.assertTrue(hasattr(dialog, "faction_combo"))
        self.assertTrue(hasattr(dialog, "race_entry"))
        self.assertTrue(hasattr(dialog, "align_entry"))

        # 2. Verifica presenza del notebook a schede
        self.assertTrue(hasattr(dialog, "notebook"))
        tabs = dialog.notebook.tabs()
        self.assertEqual(len(tabs), 4)

        # 3. Compilazione campi
        dialog.name_entry.insert(0, "Thorin Manodipietra")
        dialog.role_entry.delete(0, tk.END)
        dialog.role_entry.insert(0, "Fabbro Guerriero")
        dialog.faction_combo.set("Alleato")
        dialog.race_entry.delete(0, tk.END)
        dialog.race_entry.insert(0, "Nano delle Montagne")
        dialog.align_entry.delete(0, tk.END)
        dialog.align_entry.insert(0, "Legale Buono")

        dialog.hp_entry.delete(0, tk.END)
        dialog.hp_entry.insert(0, "42")
        dialog.ac_entry.delete(0, tk.END)
        dialog.ac_entry.insert(0, "16")

        # Modifica caratteristiche: FOR=18 (+4), DES=12 (+1)
        dialog.stat_entries["FOR"][1].set("18")
        dialog.stat_entries["DES"][1].set("12")
        dialog.stat_entries["COS"][1].set("16")

        self.assertEqual(dialog.stat_mod_labels["FOR"].cget("text"), "(+4)")
        self.assertEqual(dialog.stat_mod_labels["DES"].cget("text"), "(+1)")
        self.assertEqual(dialog.init_entry.get(), "1")

        # Inserimento azioni, equipaggiamento, note
        dialog.actions_text.delete("1.0", tk.END)
        dialog.actions_text.insert("1.0", "Martello da Guerra: +6 TpC, Danno 1d8+4 contundente.")

        dialog.equipment_text.delete("1.0", tk.END)
        dialog.equipment_text.insert("1.0", "Cotta di maglia, Incudine portatile, 25 MO.")

        dialog.notes_text.delete("1.0", tk.END)
        dialog.notes_text.insert("1.0", "Custodisce un lingotto di Mithral rubato dai goblin.")

        dialog.on_save()

        # Verifiche salvataggio
        self.assertEqual(saved_sheet.get("name"), "Thorin Manodipietra")
        self.assertEqual(saved_sheet.get("role"), "Fabbro Guerriero")
        self.assertEqual(saved_sheet.get("faction"), "Alleato")
        self.assertEqual(saved_sheet.get("race"), "Nano delle Montagne")
        self.assertEqual(saved_sheet.get("alignment"), "Legale Buono")
        self.assertEqual(saved_sheet.get("hp"), 42)
        self.assertEqual(saved_sheet.get("ac"), 16)
        self.assertEqual(saved_sheet.get("initiative"), 1)
        self.assertEqual(saved_sheet.get("strength"), 18)
        self.assertEqual(saved_sheet.get("dexterity"), 12)
        self.assertEqual(saved_sheet.get("constitution"), 16)
        self.assertIn("Martello da Guerra", saved_sheet.get("actions", ""))
        self.assertIn("Incudine portatile", saved_sheet.get("equipment", ""))
        self.assertIn("Mithral", saved_sheet.get("notes", ""))

    def test_custom_npc_dialog_initial_data_editing(self):
        existing_npc = {
            "name": "Eldrin il Grigio",
            "role": "Arcimago Eremita",
            "faction": "Neutrale",
            "race": "Elfo Alto",
            "alignment": "Caotico Neutrale",
            "hp": 38,
            "ac": 15,
            "initiative": 2,
            "speed": 30,
            "attributes": {"FOR": 8, "DES": 14, "COS": 12, "INT": 18, "SAG": 14, "CAR": 12},
            "actions": "Dardo Incantato: 3 dardi, 1d4+1 forza ciascuno.",
            "equipment": "Bastone del Fuoco, Tomo Antico.",
            "notes": "Conosce la parola di comando per aprire il portale."
        }

        saved_sheet = {}
        dialog = CustomNPCDialog(master=self.root, initial_data=existing_npc, on_save_callback=lambda s: saved_sheet.update(s))

        # Verifica caricamento dati iniziali
        self.assertEqual(dialog.name_entry.get(), "Eldrin il Grigio")
        self.assertEqual(dialog.role_entry.get(), "Arcimago Eremita")
        self.assertEqual(dialog.faction_combo.get(), "Neutrale")
        self.assertEqual(dialog.stat_entries["INT"][1].get(), "18")
        self.assertEqual(dialog.stat_mod_labels["INT"].cget("text"), "(+4)")

        # Modifica un valore e salva
        dialog.role_entry.delete(0, tk.END)
        dialog.role_entry.insert(0, "Maestro delle Illusioni")
        dialog.on_save()

        self.assertEqual(saved_sheet.get("role"), "Maestro delle Illusioni")
        self.assertEqual(saved_sheet.get("name"), "Eldrin il Grigio")
        self.assertEqual(saved_sheet.get("intelligence"), 18)

    def test_campaign_editor_npc_sheet_flow(self):
        import queue
        camp = Campaign(name="Test Campagna PNG")
        game_state = GameState(queue.Queue())
        editor = CampaignEditorDialog(self.root, campaign=camp, game_state=game_state)

        # 1. Aggiungi PNG tramite CustomNPCDialog callback
        custom_sheet = {
            "name": "Ser Gareth",
            "role": "Cavaliere Errante",
            "faction": "Alleato",
            "hp": 45,
            "ac": 18,
            "initiative": 0,
            "speed": 30,
            "attributes": {"FOR": 16, "DES": 10, "COS": 14, "INT": 10, "SAG": 12, "CAR": 14},
            "actions": "Spada a due mani: TpC +5, 2d6+3 tagliente.",
            "notes": "Cerca redenzione per aver tradito il suo ordine."
        }

        editor.campaign.add_npc(
            name=custom_sheet["name"],
            role=custom_sheet["role"],
            hp=custom_sheet["hp"],
            ac=custom_sheet["ac"],
            notes=custom_sheet["notes"],
            faction=custom_sheet["faction"],
            attributes=custom_sheet["attributes"],
            strength=16,
            dexterity=10,
            constitution=14,
            intelligence=10,
            wisdom=12,
            charisma=14,
            initiative=0,
            speed=30,
            actions=custom_sheet["actions"]
        )
        editor.refresh_npcs()

        self.assertGreaterEqual(len(editor.campaign.npcs), 1)
        npc = editor.campaign.npcs[-1]
        self.assertEqual(npc["name"], "Ser Gareth")
        self.assertEqual(npc["role"], "Cavaliere Errante")
        self.assertEqual(npc["attributes"]["FOR"], 16)

        # 2. Test spawning su GameState
        editor.tree_npcs.selection_set(str(len(editor.campaign.npcs) - 1))
        with patch("common.messagebox.messagebox.showinfo"):
            editor.spawn_selected_npc()

        p = game_state.find_player("Ser Gareth")
        self.assertIsNotNone(p)
        self.assertEqual(p.hp, 45)
        self.assertTrue(p.is_party_member)  # Poiché faction == "Alleato"
        self.assertEqual(p.full_sheet["attributes"]["FOR"], 16)

        editor.destroy()


if __name__ == "__main__":
    unittest.main()
