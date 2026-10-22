import unittest
import os
import io
import time
import base64
import tkinter as tk
from unittest.mock import MagicMock, patch
from PIL import Image

from common.image_utils import (
    process_avatar_image,
    avatar_b64_to_tk_image,
    render_avatar_on_canvas
)
from client.character_manager import Character, CharacterManager
from client.character_creation_wizard import CharacterCreationWizard
from server.dm_dialogs import CustomNPCDialog
from common.game_state import Player, GameState
from components.ui_components import HexMapCanvas


class TestCharacterTokenImage(unittest.TestCase):
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
            try:
                cls.root.destroy()
            except Exception:
                pass

    def setUp(self):
        # Genera una piccola immagine PIL in memoria per i test
        self.sample_img = Image.new("RGBA", (100, 80), color=(255, 0, 0, 255))
        buf = io.BytesIO()
        self.sample_img.save(buf, format="PNG")
        self.sample_png_bytes = buf.getvalue()

    def test_process_avatar_image_square_crop_and_b64(self):
        """Verifica che l'immagine venga ritagliata al quadrato e convertita in base64 PNG valido."""
        b64 = process_avatar_image(self.sample_png_bytes, max_size=(64, 64))
        self.assertTrue(len(b64) > 0)

        # Decodifica e verifica dimensioni quadrate
        decoded_bytes = base64.b64decode(b64)
        img_out = Image.open(io.BytesIO(decoded_bytes))
        self.assertEqual(img_out.size, (64, 64))
        self.assertEqual(img_out.format, "PNG")

    def test_character_model_avatar_fields_and_serialization(self):
        """Verifica che la classe Character persista avatar_b64 e avatar_path in to_dict e from_dict."""
        c = Character(name="Elrond")
        self.assertTrue(hasattr(c, "avatar_b64"))
        self.assertTrue(hasattr(c, "avatar_path"))
        self.assertEqual(c.avatar_b64, "")

        dummy_b64 = process_avatar_image(self.sample_png_bytes)
        c.avatar_b64 = dummy_b64
        c.avatar_path = "C:/fake/path/elrond.png"

        data = c.to_dict()
        self.assertEqual(data["avatar_b64"], dummy_b64)
        self.assertEqual(data["avatar_path"], "C:/fake/path/elrond.png")

        restored = Character.from_dict(data)
        self.assertEqual(restored.avatar_b64, dummy_b64)
        self.assertEqual(restored.avatar_path, "C:/fake/path/elrond.png")

    def test_player_game_state_avatar_propagation(self):
        """Verifica che l'entità Player e il GameState propaghino avatar_b64 per la mappa."""
        p = Player(name="Aragorn")
        p.avatar_b64 = "base64_sample_test"
        
        p_dict = p.to_dict()
        self.assertEqual(p_dict.get("avatar_b64"), "base64_sample_test")

        # Deserializzazione
        p_restored = Player.from_dict(p_dict)
        self.assertEqual(p_restored.avatar_b64, "base64_sample_test")

    def test_creation_wizard_avatar_integration(self):
        """Verifica che CharacterCreationWizard assegni l'avatar al personaggio creato."""
        if not self.root:
            self.skipTest("Tkinter display not available")

        mgr = MagicMock()
        mgr.characters = []
        created_characters = []

        wizard = CharacterCreationWizard(self.root, mgr, on_complete_callback=lambda c: created_characters.append(c))
        
        # Simula selezione immagine nel wizard al Passo 5
        wizard.current_step = 4
        wizard.show_step()

        dummy_b64 = process_avatar_image(self.sample_png_bytes)
        wizard.name_var.set("Gimli")
        wizard.char_data["avatar_b64"] = dummy_b64
        wizard.char_data["avatar_path"] = "C:/portraits/gimli.png"

        # Conclude creazione
        with patch("common.messagebox.messagebox.showinfo"):
            wizard.next_step()
            for _ in range(30):
                if created_characters:
                    break
                time.sleep(0.05)
                self.root.update()

        self.assertEqual(len(created_characters), 1)
        gimli = created_characters[0]
        self.assertEqual(gimli.name, "Gimli")
        self.assertEqual(gimli.avatar_b64, dummy_b64)
        self.assertEqual(gimli.avatar_path, "C:/portraits/gimli.png")

    def test_custom_npc_dialog_avatar_integration(self):
        """Verifica che CustomNPCDialog salvi avatar_b64 per PNG e mostri custom."""
        if not self.root:
            self.skipTest("Tkinter display not available")

        saved_sheets = []
        dummy_b64 = process_avatar_image(self.sample_png_bytes)

        dialog = CustomNPCDialog(
            master=self.root,
            on_save_callback=lambda sheet: saved_sheets.append(sheet),
            initial_data={"avatar_b64": dummy_b64, "avatar_path": "npc_art.png"}
        )

        self.assertEqual(dialog.avatar_b64, dummy_b64)
        self.assertTrue(hasattr(dialog, "token_canvas"))

        dialog.name_entry.delete(0, tk.END)
        dialog.name_entry.insert(0, "Drago Rosso")
        dialog.hp_entry.delete(0, tk.END)
        dialog.hp_entry.insert(0, "150")

        dialog.on_save()

        self.assertEqual(len(saved_sheets), 1)
        sheet = saved_sheets[0]
        self.assertEqual(sheet["name"], "Drago Rosso")
        self.assertEqual(sheet["avatar_b64"], dummy_b64)
        self.assertEqual(sheet["avatar_path"], "npc_art.png")

    def test_hex_map_canvas_avatar_rendering(self):
        """Verifica che HexMapCanvas legga avatar_b64 e lo renderizzi sul token della mappa."""
        if not self.root:
            self.skipTest("Tkinter display not available")

        canvas = HexMapCanvas(self.root)
        dummy_b64 = process_avatar_image(self.sample_png_bytes, max_size=(32, 32))

        # Configura mappa minima corretta
        map_data = {
            "grid_type": "flat",
            "hex_size": 30,
            "hexes": [[0, 0], [1, 0]]
        }
        players_data = {
            "Gandalf": {
                "position": [0, 0],
                "hp": 20,
                "hp_max": 20,
                "avatar_b64": dummy_b64,
                "conditions": []
            }
        }

        canvas.update_data(map_data, players_data, player_name="Gandalf")
        canvas.redraw()

        # Verifica presenza della chiave nella cache avatar
        matched_keys = [k for k in canvas._avatar_cache.keys() if "Gandalf" in k]
        self.assertTrue(len(matched_keys) > 0, "L'avatar di Gandalf dovrebbe essere memorizzato nella cache di HexMapCanvas")

    def test_character_sheet_avatar_ui_interaction(self):
        """Verifica che CharacterSheetUI carichi, modifichi e rimuova l'avatar del token."""
        if not self.root:
            self.skipTest("Tkinter display not available")

        from client.character_sheet_ui import CharacterSheetUI
        dummy_b64 = process_avatar_image(self.sample_png_bytes)

        char = Character(name="Legolas")
        char.avatar_b64 = dummy_b64
        char.avatar_path = "legolas.png"

        mgr = MagicMock()
        mgr.update_character = MagicMock()

        sheet = CharacterSheetUI(self.root, char, mgr)

        self.assertTrue(hasattr(sheet, "avatar_canvas"))
        self.assertEqual(sheet.character.avatar_b64, dummy_b64)

        # Test rimozione avatar
        sheet._remove_avatar()
        self.assertEqual(sheet.character.avatar_b64, "")
        self.assertEqual(sheet.character.avatar_path, "")
        mgr.update_character.assert_called_with(char)

        # Test assegnazione nuovo avatar
        new_b64 = process_avatar_image(self.sample_png_bytes, max_size=(32, 32))
        with patch("common.image_utils.open_avatar_file_dialog", return_value=(new_b64, "new_legolas.png")):
            sheet._on_avatar_clicked()

        self.assertEqual(sheet.character.avatar_b64, new_b64)
        self.assertEqual(sheet.character.avatar_path, "new_legolas.png")
        sheet.destroy()


if __name__ == "__main__":
    unittest.main()
