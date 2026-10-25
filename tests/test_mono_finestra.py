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

    def test_hide_stats_overlay_save_no_recursion_and_cancel_reverts(self):
        """Verifica che hide_stats_overlay(save=True) non vada in RecursionError e che Annulla ripristini i campi."""
        from client.client import ClientGUI
        client = ClientGUI(self.root, initial_character=self.char)
        client.open_stats_dialog()
        self.assertTrue(client.stats_overlay_visible)

        # Modifica il nome nell'overlay e salva tramite hide_stats_overlay(save=True)
        client.stats_sheet_frame.name_var.set("Eroe Salvato")
        client.hide_stats_overlay(save=True)
        self.assertFalse(client.stats_overlay_visible)
        self.assertEqual(self.char.name, "Eroe Salvato")

        # Riapri, modifica senza salvare e premi Annulla (cancel_sheet)
        client.open_stats_dialog()
        client.stats_sheet_frame.name_var.set("Modifica Non Salvata")
        client.stats_sheet_frame.cancel_sheet()
        self.assertFalse(client.stats_overlay_visible)
        self.assertEqual(self.char.name, "Eroe Salvato")

        for w in self.root.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

    def test_server_update_full_sheet_anticheat_and_character_key(self):
        """Verifica che handle_update_full_sheet_request accetti la chiave 'character', validi tutte le valute e blocchi l'exploit dei pacchetti."""
        from server.rules.character import handle_update_full_sheet_request
        from common.starter_equipment import get_pack_contents

        player = MagicMock()
        player.name = "Aragorn"
        player.hp = 10
        player.max_hp = 10
        player.full_sheet = {
            "name": "Aragorn",
            "level": 1,
            "hp_current": 10,
            "hp_max": 10,
            "exp": 0,
            "currency": {"MR": 0, "MA": 5, "ME": 0, "MO": 10, "MP": 0},
            "inventory_grid": [
                {"name": "Zaino da Esploratore", "type": "Equipaggiamento", "qty": 1, "weight": 10.0}
            ] + [None] * 24,
            "weapons": [],
            "spellbook": [{"name": "Luce", "level": 0}],
            "journal_notes": "Diario Iniziale",
            "notes": "Appunti Iniziali",
            "features": "Tratti Iniziali",
        }
        game_state = MagicMock()

        # Tentativo di barare aumentando MP/MA e aggiungendo Torce senza aver rimosso lo Zaino da Esploratore
        pack_sub = get_pack_contents("Zaino da Esploratore")
        torches = [dict(it) for it in pack_sub if it["name"] == "Torce"][0]
        client_sheet = {
            "name": "Aragorn",
            "level": 1,
            "hp_current": 99,
            "hp_max": 99,
            "exp": 5000,
            "currency": {"MR": 0, "MA": 500, "ME": 0, "MO": 10, "MP": 99},
            "inventory_grid": [
                {"name": "Zaino da Esploratore", "type": "Equipaggiamento", "qty": 1, "weight": 10.0},
                torches,
            ] + [None] * 23,
            "weapons": [{"name": "Spada Vorpal", "damage_dice": "2d6"}],
            "spellbook": [{"name": "Luce", "level": 0}, {"name": "Desiderio", "level": 9}],
            "journal_notes": "Diario Modificato Senza Approvazione",
        }
        handle_update_full_sheet_request({"character": client_sheet}, player, game_state)
        updated = player.full_sheet
        self.assertEqual(updated["hp_current"], 10)
        self.assertEqual(updated["currency"]["MP"], 0)
        self.assertEqual(updated["currency"]["MA"], 5)
        # Lo Zaino da Esploratore non è stato consumato, quindi le Torce extra vengono bloccate
        inv_names = [it["name"] for it in updated["inventory_grid"] if it]
        self.assertEqual(inv_names, ["Zaino da Esploratore"])
        # Armi e incantesimi non autorizzati bloccati
        self.assertEqual(len(updated["weapons"]), 0)
        self.assertEqual(len(updated["spellbook"]), 1)
        self.assertEqual(updated["journal_notes"], "Diario Iniziale")

    def test_dndscript_loot_linked_to_compendium(self):
        """Verifica che il loot scritto in DndScript venga risolto contro il Compendio SRD e l'equipaggiamento 5e."""
        from common.campaign_script import DndScriptParser, sync_flow_graph_to_campaign
        from common.campaign import Campaign

        script = '''
# INCONTRO: Imboscata Goblin
mostri: 2x "Goblin"
loot: "50 mo, 20 ma, 2x Pozione di Guarigione, Spada Lunga +1"

# TESORO: Scrigno Reale
monete: "150 mo, 5 mp"
oggetti: "Borsa Conservante", "Corda di Seta"

# QUEST: Liberare la Miniera
obiettivi: "Sconfiggi il capo"
loot: "100 mo, Anello di Protezione"
'''
        parser = DndScriptParser()
        graph = parser.parse(script)
        camp = Campaign(name="Test Compendio Loot")
        sync_flow_graph_to_campaign(graph, camp)

        # 1. Verifica Incontro
        self.assertEqual(len(camp.encounters), 1)
        enc = camp.encounters[0]
        self.assertEqual(enc["loot_currency"]["MO"], 50)
        self.assertEqual(enc["loot_currency"]["MA"], 20)
        self.assertEqual(len(enc["loot_items"]), 2)
        potion = enc["loot_items"][0]
        sword = enc["loot_items"][1]
        self.assertEqual(potion["name"], "Pozione di Guarigione")
        self.assertEqual(potion["qty"], 2)
        self.assertTrue(potion["from_compendium"])
        self.assertEqual(potion["type"], "Pozione")
        self.assertEqual(sword["name"], "Spada Lunga +1")
        self.assertTrue(sword["from_compendium"])
        self.assertEqual(sword["type"], "Arma")

        # 2. Verifica Nodo Tesoro
        self.assertEqual(len(camp.treasures), 1)
        tr = camp.treasures[0]
        self.assertEqual(tr["currency"]["MO"], 150)
        self.assertEqual(tr["currency"]["MP"], 5)
        self.assertEqual(len(tr["resolved_items"]), 2)
        bag = tr["resolved_items"][0]
        self.assertEqual(bag["name"], "Borsa Conservante")
        self.assertTrue(bag["from_compendium"])
        self.assertIn("Bag of Holding", bag.get("srd_name", ""))

        # 3. Verifica Quest
        self.assertEqual(len(camp.quests), 1)
        q = camp.quests[0]
        self.assertEqual(q["reward_currency"]["MO"], 100)
        self.assertEqual(len(q["reward_items"]), 1)
        ring = q["reward_items"][0]
        self.assertEqual(ring["name"], "Anello di Protezione")
        self.assertTrue(ring["from_compendium"])

    def test_load_campaign_into_editor(self):
        """Verifica che il pulsante/metodo di caricamento campagna in CampaignEditorFrame aggiorni tutte le viste."""
        container = tk.Frame(self.root)
        container.pack()

        editor_frame = CampaignEditorFrame(container, campaign=None)
        editor_frame.pack(fill=tk.BOTH, expand=True)
        self.assertEqual(editor_frame.ent_title.get(), "Nuova Campagna Avventura")

        loaded = Campaign(name="Le Miniere Perdute di Phandelver")
        loaded.description = "Un'avventura epica sulla Costa della Spada."
        loaded.dm_notes = "Il Ragno Nero trama nell'ombra."
        loaded.level_range = "1-5"
        loaded.start_date = {"year": 1495, "month": 6, "day": 15, "hour": 10}
        loaded.start_weather = "Pioggia"
        loaded.flow_script = '# SCENA: Sentiero di Triboar\nmappa: "maps/faerun.json"\nnarra: "Due cavalli morti bloccano la via."\n\n# INCONTRO: Imboscata dei Cragmaw\nmostri: 4x "Goblin"\nloot: "50 mo, Pozione di Guarigione"'
        loaded.add_handout("Mappa di Gundren", content="Indicazioni per la Caverna dell'Eco.")

        editor_frame.load_campaign_into_editor(loaded)

        self.assertIs(editor_frame.campaign, loaded)
        self.assertEqual(editor_frame.ent_title.get(), "Le Miniere Perdute di Phandelver")
        self.assertEqual(editor_frame.ent_level.get(), "1-5")
        self.assertEqual(editor_frame.combo_weather.get(), "Pioggia")
        self.assertIn("Costa della Spada", editor_frame.txt_synopsis.get("1.0", tk.END))
        self.assertIn("Ragno Nero", editor_frame.txt_dm_notes.get("1.0", tk.END))
        self.assertIn("Sentiero di Triboar", editor_frame.studio_frame.txt_script.get("1.0", tk.END))
        self.assertEqual(len(editor_frame.tree_scenes.get_children()), 1)
        self.assertEqual(len(editor_frame.tree_enc.get_children()), 1)
        self.assertEqual(len(editor_frame.tree_handouts.get_children()), 1)

        container.destroy()


if __name__ == "__main__":
    unittest.main()
