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

if __name__ == "__main__":
    unittest.main()
