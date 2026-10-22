import unittest
from unittest.mock import MagicMock, patch
import json
import tkinter as tk

from common.starter_equipment import lookup_standard_weight, STANDARD_ITEM_WEIGHTS
from client.character_manager import Character, CharacterManager
from common.protocol import make_journal_approval_request, make_journal_approval_response
from client.character_sheet_ui import (
    parse_features_text,
    serialize_features_list,
    render_markdown_to_widget,
    configure_markdown_tags
)

class TestCharacterSheetEnhancements(unittest.TestCase):
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

    def test_standard_item_weight_lookup(self):
        """Verifica che gli oggetti standard abbiano pesi accurati da 5e SRD."""
        self.assertEqual(lookup_standard_weight("Spada Corta"), 2.0)
        self.assertEqual(lookup_standard_weight("Spada Lunga"), 3.0)
        self.assertEqual(lookup_standard_weight("Dardo"), 0.25)
        self.assertEqual(lookup_standard_weight("Dieci Dardi"), 1.5)
        self.assertEqual(lookup_standard_weight("Zaino da Esploratore"), 10.0)
        self.assertEqual(lookup_standard_weight("Armatura di Cuoio"), 10.0)
        self.assertEqual(lookup_standard_weight("Scudo"), 6.0)
        self.assertEqual(lookup_standard_weight("Pozione di Guarigione"), 0.5)
        self.assertEqual(lookup_standard_weight("Monete d'Oro"), 0.2)
        # Fuzzy match
        self.assertGreater(lookup_standard_weight("Cimelio: Un pugnale antico"), 0.0)

    def test_character_carried_weight_fallback(self):
        """Verifica che Character.get_carried_weight non restituisca 0 per equipaggiamento standard con weight 0.0."""
        c = Character("Test Hero")
        c.inventory_grid = [
            {"name": "Spada Corta", "qty": 1, "weight": 0.0},
            {"name": "Zaino da Esploratore", "qty": 1, "weight": 0.0},
            None,
            {"name": "Pozione di Guarigione", "qty": 2, "weight": 0.0}
        ]
        carried = c.get_carried_weight()
        # 2.0 + 10.0 + (0.5 * 2) = 13.0 lbs
        self.assertEqual(carried, 13.0)
        enc = c.get_encumbrance_status()
        self.assertEqual(enc["carried_weight"], 13.0)
        self.assertEqual(enc["tier"], "normal")

    def test_parse_and_serialize_features(self):
        """Verifica il parsing intelligente di features in lista categorizzata e viceversa."""
        raw_features = (
            "Tratti razziali:\n"
            "Scurovisione fino a 18 metri.\n"
            "Bonus: +2 Costituzione.\n\n"
            "Tratti classe:\n"
            "Difesa senz'armatura.\n\n"
            "Privilegio di Background (Grado Militare):\n"
            "Autorità riconosciuta dalle guardie.\n\n"
            "--- Privilegi di Livello 1 (API) ---\n"
            "- Arti Marziali\n"
            "- Furore"
        )
        parsed = parse_features_text(raw_features)
        self.assertTrue(len(parsed) >= 4)
        categories = [p["category"] for p in parsed]
        self.assertIn("Tratto Razziale", categories)
        self.assertIn("Privilegio di Classe", categories)
        self.assertIn("Tratto di Background", categories)

        serialized = serialize_features_list(parsed)
        self.assertIn("=== TRATTI RAZZIALI ===", serialized)
        self.assertIn("=== PRIVILEGI DI CLASSE ===", serialized)
        self.assertIn("=== TRATTI DI BACKGROUND ===", serialized)

    def test_markdown_rendering(self):
        """Verifica il rendering visuale dei tag Markdown in un widget di testo."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        txt = tk.Text(self.root)
        configure_markdown_tags(txt)
        md_sample = (
            "# Titolo Principale\n"
            "## Sottotitolo\n"
            "> Questa è una citazione di saggezza.\n"
            "- Primo punto con **grassetto** e *corsivo*\n"
            "• Secondo punto normale"
        )
        render_markdown_to_widget(txt, md_sample)
        content = txt.get("1.0", tk.END)
        self.assertIn("Titolo Principale", content)
        self.assertIn("Sottotitolo", content)
        self.assertIn("Questa è una citazione", content)
        self.assertIn("Primo punto", content)

    def test_protocol_journal_messages(self):
        """Verifica la creazione corretta dei messaggi di protocollo per l'approvazione del diario/note."""
        req = make_journal_approval_request("journal_notes", "# Il mio viaggio\nTutto procede bene.", "Aggiornamento Diario")
        self.assertEqual(req["type"], "JOURNAL_APPROVAL_REQUEST")
        self.assertEqual(req["data"]["field_name"], "journal_notes")
        self.assertIn("Il mio viaggio", req["data"]["content"])

        resp = make_journal_approval_response("Hero", "journal_notes", "Content", approved=True)
        self.assertEqual(resp["type"], "JOURNAL_APPROVAL_RESPONSE")
        self.assertTrue(resp["data"]["approved"])
        self.assertEqual(resp["data"]["player_name"], "Hero")

    def test_server_handler_routing(self):
        """Verifica che il server instradi la richiesta di approvazione del diario alla GUI del DM."""
        from server.rules.character import handle_journal_approval_request
        mock_game_state = MagicMock()
        mock_game_state.gui_queue = MagicMock()
        mock_player = MagicMock()
        mock_player.name = "TestPlayer"

        data = {"field_name": "journal_notes", "content": "Test text", "title": "Modifica Diario"}
        handle_journal_approval_request(data, mock_player, mock_game_state)
        mock_game_state.gui_queue.put.assert_called_once()
        queued = mock_game_state.gui_queue.put.call_args[0][0]
        self.assertEqual(queued["type"], "JOURNAL_APPROVAL_REQUEST")
        self.assertEqual(queued["player"], mock_player)
        self.assertEqual(queued["field_name"], "journal_notes")

    def test_server_protected_fields_on_full_sheet_update(self):
        """Verifica che handle_update_full_sheet_request non sovrascriva journal_notes o features in multiplayer."""
        from server.rules.character import handle_update_full_sheet_request
        mock_game_state = MagicMock()
        mock_player = MagicMock()
        mock_player.full_sheet = {
            "name": "Hero",
            "level": 1,
            "journal_notes": "APPROVED JOURNAL BY DM",
            "notes": "APPROVED NOTES BY DM",
            "features": "APPROVED FEATURES BY DM"
        }
        mock_player.name = "Hero"

        incoming_sheet = {
            "name": "Hero",
            "level": 1,
            "journal_notes": "HACKED OVERWRITE",
            "notes": "HACKED NOTES",
            "features": "HACKED FEATURES",
            "hp_current": 10
        }
        data = {"sheet": incoming_sheet}
        handle_update_full_sheet_request(data, mock_player, mock_game_state)

        # In multiplayer, i campi protetti non devono essere sovrascritti
        self.assertEqual(mock_player.full_sheet["journal_notes"], "APPROVED JOURNAL BY DM")
        self.assertEqual(mock_player.full_sheet["notes"], "APPROVED NOTES BY DM")
        self.assertEqual(mock_player.full_sheet["features"], "APPROVED FEATURES BY DM")

    def test_character_sheet_srd_spell_approval_routing(self):
        """Verifica che la ricerca incantesimi SRD richieda approvazione in multiplayer."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("Mage")
        cm = MagicMock()
        mock_spell_req = MagicMock(return_value=True)

        with patch("common.messagebox.messagebox.askyesno", return_value=True), \
             patch("common.messagebox.messagebox.showinfo"):
            ui = CharacterSheetUI(
                self.root, c, cm,
                is_connected=True,
                custom_spell_request_callback=mock_spell_req
            )
            ui._handle_found_spell("Palla di Fuoco", 3, "1 Azione", "150 ft", "Una sfera di fiamme...")
            mock_spell_req.assert_called_once()
            call_arg = mock_spell_req.call_args[0][0]
            self.assertEqual(call_arg["name"], "Palla di Fuoco")
            self.assertEqual(call_arg["level"], 3)
            ui.destroy()

    def test_offline_inventory_add_blocked(self):
        """Verifica che in modalità offline non sia possibile aggiungere oggetti autonomamente."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("HeroOffline")
        cm = MagicMock()

        with patch("common.messagebox.messagebox.showwarning") as mock_warn:
            ui = CharacterSheetUI(self.root, c, cm, is_connected=False)
            
            # Clic su slot vuoto
            ui.on_inventory_click(0)
            mock_warn.assert_called()
            self.assertIsNone(c.inventory_grid[0])
            
            # Apertura dialogo custom item
            mock_warn.reset_mock()
            ui.open_custom_item_dialog(0)
            mock_warn.assert_called()
            
            # Apertura compendio inventario
            mock_warn.reset_mock()
            ui.open_inventory_compendium()
            mock_warn.assert_called()
            
            ui.destroy()

    def test_offline_spell_add_blocked(self):
        """Verifica che in modalità offline non sia possibile aggiungere incantesimi al Grimorio."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("MageOffline")
        c.spellbook = []
        cm = MagicMock()

        with patch("common.messagebox.messagebox.showwarning") as mock_warn:
            ui = CharacterSheetUI(self.root, c, cm, is_connected=False)
            
            # Aggiunta manuale
            ui.add_spell()
            mock_warn.assert_called()
            
            # Aggiunta da ricerca SRD / manuale
            mock_warn.reset_mock()
            ui._handle_found_spell("Dardo Incantato", 1, "1 Azione", "36m", "Tre dardi magici...")
            mock_warn.assert_called()
            self.assertEqual(len(c.spellbook), 0)
            
            ui.destroy()

    def test_offline_weapon_and_compendium_import_blocked(self):
        """Verifica che l'importazione da compendio e l'aggiunta di armi siano bloccate offline."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("FighterOffline")
        c.weapons = []
        cm = MagicMock()

        with patch("common.messagebox.messagebox.showwarning") as mock_warn:
            ui = CharacterSheetUI(self.root, c, cm, is_connected=False)
            
            # Aggiunta arma offline
            ui.open_add_weapon_dialog()
            mock_warn.assert_called()
            self.assertEqual(len(c.weapons), 0)
            
            # Import da compendio offline
            mock_warn.reset_mock()
            ui.import_from_compendium_to_slot({"name": "Ascia da Battaglia"}, "Arma", 0)
            mock_warn.assert_called()
            self.assertIsNone(c.inventory_grid[0])
            
            ui.destroy()

    def test_inventory_coins_synced_to_currency_table(self):
        """Verifica che le monete nella griglia inventario vengano sincronizzate nella tabella valute (MR, MA, ME, MO, MP)."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("WealthyHero")
        c.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
        c.inventory_grid = [None] * 25
        c.inventory_grid[0] = {"name": "Monete d'Oro", "qty": 15, "type": "Valuta"}
        c.inventory_grid[1] = {"name": "Borsa di Monete", "qty": 1, "desc": "Contiene 50 MA e 5 MP", "type": "Oggetto"}
        c.inventory_grid[2] = {"name": "Monete di Rame", "qty": 30, "type": "Valuta"}

        cm = MagicMock()
        ui = CharacterSheetUI(self.root, c, cm, is_connected=False)
        ui.sync_inventory_coins_to_currency()

        self.assertGreaterEqual(c.currency["MO"], 15)
        self.assertGreaterEqual(c.currency["MR"], 30)
        ui.destroy()

    def test_offline_spell_removal_blocked(self):
        """Verifica che la rimozione di incantesimi sia rigorosamente bloccata in modalità offline."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("WizardOffline")
        c.spellbook = [{"name": "Dardo Incantato", "level": 1, "time": "1 Azione"}]
        cm = MagicMock()

        with patch("common.messagebox.messagebox.showwarning") as mock_warn:
            ui = CharacterSheetUI(self.root, c, cm, is_connected=False)
            children = ui.spell_tree.get_children()
            if children:
                ui.spell_tree.selection_set(children[0])
                ui.remove_spell()
                mock_warn.assert_called()
                self.assertEqual(len(c.spellbook), 1)
            ui.destroy()

    def test_offline_inventory_removal_blocked(self):
        """Verifica che la rimozione di oggetti dall'inventario e di armi sia bloccata offline."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("FighterOffline")
        c.inventory_grid = [None] * 25
        c.inventory_grid[0] = {"name": "Pozione di Guarigione", "qty": 1, "weight": 0.5, "type": "Consumabile"}
        c.weapons = [{"name": "Spada Lunga", "damage": "1d8", "prof": True}]
        cm = MagicMock()

        with patch("common.messagebox.messagebox.showwarning") as mock_warn:
            ui = CharacterSheetUI(self.root, c, cm, is_connected=False)
            
            # Tentativo rimozione arma
            ui.remove_weapon(0)
            mock_warn.assert_called()
            self.assertEqual(len(c.weapons), 1)
            self.assertIsNotNone(c.inventory_grid[0])
            ui.destroy()

    def test_online_spell_removal_approval_flow(self):
        """Verifica che la rimozione incantesimi online richieda conferma e invii action='remove' al DM."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("WizardOnline")
        c.spellbook = [{"name": "Scudo", "level": 1, "time": "1 Reazione"}]
        cm = MagicMock()
        mock_spell_req = MagicMock(return_value=True)

        with patch("common.messagebox.messagebox.askyesno", return_value=True),              patch("common.messagebox.messagebox.showinfo"):
            ui = CharacterSheetUI(
                self.root, c, cm,
                is_connected=True,
                custom_spell_request_callback=mock_spell_req
            )
            children = ui.spell_tree.get_children()
            if children:
                ui.spell_tree.selection_set(children[0])
                ui.remove_spell()
                mock_spell_req.assert_called_once()
                call_arg = mock_spell_req.call_args[0][0]
                self.assertEqual(call_arg.get("name"), "Scudo")
                self.assertEqual(call_arg.get("action"), "remove")
            ui.destroy()

    def test_client_item_and_spell_approval_handling(self):
        """Verifica che il Client aggiorni correttamente la scheda quando riceve risposte di rimozione dal Master."""
        from client.client import ClientGUI
        app = MagicMock(spec=ClientGUI)
        app.active_character = Character("HeroApp")
        app.active_character.spellbook = [{"name": "Palla di Fuoco", "level": 3}]
        app.active_character.inventory_grid = [None] * 25
        app.active_character.inventory_grid[2] = {"name": "Scudo Pesante", "type": "Armatura"}
        app.character_manager = MagicMock()
        app.network = MagicMock()
        app.show_toast = MagicMock()

        # Test rimozione incantesimo approvata
        ClientGUI.handle_custom_spell_response(app, {
            "approved": True,
            "spell": {"name": "Palla di Fuoco", "action": "remove"}
        })
        self.assertEqual(len(app.active_character.spellbook), 0)
        app.show_toast.assert_called()

        # Test rimozione oggetto inventario approvata
        ClientGUI.handle_item_approval_response(app, {
            "approved": True,
            "item": {"name": "Scudo Pesante", "action": "remove"},
            "slot_idx": 2
        })
        self.assertIsNone(app.active_character.inventory_grid[2])

    def test_starter_equipment_starting_gold_applied_to_currency(self):
        """Verifica che le monete d'oro iniziali della classe vengano accreditate in character.currency['MO']."""
        from common.starter_equipment import apply_class_and_race_starter_kit
        c = Character("RogueHero")
        c.character_class = "Ladro"
        c.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
        c.inventory_grid = [None] * 25

        apply_class_and_race_starter_kit(c)
        self.assertGreater(c.currency.get("MO", 0), 0)

    def test_container_filtering_and_quick_move(self):
        """Verifica il cambio rapido di contenitore e il filtro visivo per contenitori."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("ContainerHero")
        c.inventory_grid = [None] * 25
        c.inventory_grid[0] = {"name": "Spada Lunga", "type": "Arma", "qty": 1, "weight": 3.0, "container": "equipped"}
        c.inventory_grid[1] = {"name": "Razioni", "type": "Consumabile", "qty": 10, "weight": 2.0, "container": "backpack"}
        c.inventory_grid[2] = {"name": "Gemma Preziosa", "type": "Tesoro", "qty": 1, "weight": 0.1, "container": "bag_of_holding"}
        cm = MagicMock()

        ui = CharacterSheetUI(self.root, c, cm, is_connected=False)
        
        # Test Sposta Contenitore
        ui.move_item_to_container(1, "bag_of_holding")
        self.assertEqual(c.inventory_grid[1]["container"], "bag_of_holding")
        
        # Test Filtro Contenitore: Seleziona "bag_of_holding"
        ui.set_container_filter("bag_of_holding")
        self.assertEqual(ui.current_container_filter, "bag_of_holding")
        self.assertEqual(ui.inventory_row_frames[0].winfo_manager(), "")
        self.assertEqual(ui.inventory_row_frames[1].winfo_manager(), "pack")
        self.assertEqual(ui.inventory_row_frames[2].winfo_manager(), "pack")
        
        # Reset a "all"
        ui.set_container_filter("all")
        self.assertEqual(ui.inventory_row_frames[0].winfo_manager(), "pack")
        self.assertEqual(ui.inventory_row_frames[1].winfo_manager(), "pack")
        ui.destroy()

    def test_spend_consumable_quantity_and_weight(self):
        """Verifica che la spesa di munizioni/consumabili scali quantità e aggiorni il carico."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("ArcherHero")
        c.inventory_grid = [None] * 25
        c.inventory_grid[0] = {"name": "Frecce", "type": "Munizioni", "qty": 20, "weight": 0.05, "container": "backpack"}
        cm = MagicMock()

        with patch("common.messagebox.messagebox.showinfo"):
            ui = CharacterSheetUI(self.root, c, cm, is_connected=False)
            
            # Spendi 1 freccia
            ui.spend_consumable(0, 1)
            self.assertEqual(c.inventory_grid[0]["qty"], 19)
            
            # Spendi altre 5 frecce
            ui.spend_consumable(0, 5)
            self.assertEqual(c.inventory_grid[0]["qty"], 14)
            ui.destroy()

    def test_spend_healing_potion_heals_character(self):
        """Verifica che consumare una Pozione di Guarigione ripristini PF al personaggio."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("WoundedHero")
        c.hp_max = 20
        c.hp_current = 5
        c.inventory_grid = [None] * 25
        c.inventory_grid[0] = {"name": "Pozione di Guarigione", "type": "Consumabile", "qty": 2, "weight": 0.5, "container": "backpack"}
        cm = MagicMock()

        with patch("common.messagebox.messagebox.showinfo"):
            ui = CharacterSheetUI(self.root, c, cm, is_connected=False)
            ui.spend_consumable(0, 1)
            self.assertEqual(c.inventory_grid[0]["qty"], 1)
            # La pozione cura 2d4+2 (da 4 a 10 PF recuperati)
            self.assertGreater(c.hp_current, 5)
            self.assertLessEqual(c.hp_current, 20)
            ui.destroy()

    def test_starter_pack_unpacking(self):
        """Verifica che spacchettare uno Zaino da Esploratore estragga tutti i suoi contenuti individuali."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("ExplorerHero")
        c.inventory_grid = [None] * 25
        c.inventory_grid[0] = {"name": "Zaino da Esploratore", "type": "Equipaggiamento", "qty": 1, "weight": 10.0, "container": "backpack"}
        cm = MagicMock()

        with patch("common.messagebox.messagebox.askyesno", return_value=True),              patch("common.messagebox.messagebox.showinfo"):
            ui = CharacterSheetUI(self.root, c, cm, is_connected=False)
            ui.unpack_starter_pack(0)
            
            # Gli slot ora devono contenere Sacco a Pelo, Torce, Razioni, ecc.
            item_names = [it["name"] for it in c.inventory_grid if it]
            self.assertIn("Torce", item_names)
            self.assertIn("Razioni da Viaggio", item_names)
            self.assertIn("Sacco a Pelo", item_names)
            self.assertIn("Acciarino", item_names)
            ui.destroy()

    def test_weapon_attack_consumes_ammunition(self):
        """Verifica che attaccare con un arco consumi automaticamente 1 freccia dallo zaino."""
        if not self.root:
            self.skipTest("Tkinter non disponibile in ambiente headless")
        from client.character_sheet_ui import CharacterSheetUI
        c = Character("RangerArcher")
        c.inventory_grid = [None] * 25
        c.inventory_grid[0] = {"name": "Frecce", "type": "Munizioni", "qty": 20, "weight": 1.0, "container": "backpack"}
        c.weapons = [{"name": "Arco Lungo", "damage_dice": "1d8", "type": "A Distanza", "proficient": True, "ability": "DES"}]
        cm = MagicMock()

        with patch("common.messagebox.messagebox.showinfo"):
            ui = CharacterSheetUI(self.root, c, cm, is_connected=False)
            weapon = c.weapons[0]
            ui.execute_weapon_attack(weapon, 5)
            # Frecce passano da 20 a 19
            self.assertEqual(c.inventory_grid[0]["qty"], 19)
            ui.destroy()

if __name__ == "__main__":
    unittest.main()

