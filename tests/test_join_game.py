# tests/test_join_game.py
"""
Test per il flusso di connessione e unione a una partita:
- LoginDialog con selezione rapida del server e del personaggio
- Cronologia server recenti (settings.json)
- Preset IP locale (127.0.0.1)
- Auto-connessione di ClientGUI all'avvio da launcher
- Parsing host e porta personalizzata
"""

import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch
from client.character_manager import Character, CharacterManager
from client.login_ui import LoginDialog, load_server_history, save_server_history


class TestJoinGameFlow(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.char1 = Character("Aragorn", "Ranger")
        self.char1.level = 5
        self.char2 = Character("Gimli", "Guerriero")
        self.char2.level = 4
        self.mgr = CharacterManager.__new__(CharacterManager)
        self.mgr.characters = [self.char1, self.char2]
        self.mgr.update_character = lambda c: None
        self.mgr.save_characters = lambda: None
        self.mgr.delete_character = lambda c: None

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_server_history_save_and_load(self):
        """Verifica che la cronologia degli IP server venga salvata e ricaricata correttamente."""
        save_server_history("192.168.1.42")
        last_ip, recents = load_server_history()
        self.assertEqual(last_ip, "192.168.1.42")
        self.assertIn("192.168.1.42", recents)
        self.assertIn("127.0.0.1", recents)

    def test_login_dialog_initialization_and_preselection(self):
        """Verifica che LoginDialog carichi i personaggi e pre-selezioni il personaggio iniziale."""
        dialog = LoginDialog(self.root, self.mgr, initial_character=self.char2)
        
        # IP var deve essere valorizzata
        self.assertTrue(dialog.ip_var.get())
        
        # Il secondo personaggio deve essere selezionato
        cur_sel = dialog.char_listbox.curselection()
        self.assertEqual(cur_sel[0], 1)
        dialog.destroy()

    def test_login_dialog_set_local_ip(self):
        """Verifica che il pulsante 'Locale (127.0.0.1)' imposti l'IP a 127.0.0.1."""
        dialog = LoginDialog(self.root, self.mgr)
        dialog.ip_var.set("10.0.0.99")
        dialog.set_local_ip()
        self.assertEqual(dialog.ip_var.get(), "127.0.0.1")
        dialog.destroy()

    def test_login_dialog_connect_sets_result(self):
        """Verifica che confermando la connessione, result sia una tupla (ip, char)."""
        dialog = LoginDialog(self.root, self.mgr)
        dialog.ip_var.set("192.168.1.50:5555")
        dialog.char_listbox.selection_clear(0, tk.END)
        dialog.char_listbox.selection_set(0)
        
        dialog.connect()
        self.assertIsNotNone(dialog.result)
        self.assertEqual(dialog.result[0], "192.168.1.50:5555")
        self.assertEqual(dialog.result[1].name, "Aragorn")

    def test_login_dialog_cancel_sets_none(self):
        """Verifica che annullando il dialogo, result rimanga None."""
        dialog = LoginDialog(self.root, self.mgr)
        dialog.on_close()
        self.assertIsNone(dialog.result)

    def test_client_gui_auto_connect(self):
        """Verifica che passare auto_connect_ip a ClientGUI chiami perform_connect con host e porta corretti."""
        from client.client import ClientGUI
        with patch("client.client.ClientNetwork") as MockNet, \
             patch("client.client.AudioManager"), \
             patch("client.client.VoiceClient"):
            
            app = ClientGUI(self.root, initial_character=self.char1, auto_connect_ip="192.168.1.10:5005")
            self.assertEqual(app.auto_connect_ip, "192.168.1.10:5005")
            
            # Esegui perform_connect direttamente per testare il parsing e il join
            app.perform_connect("192.168.1.10:5005", self.char1)
            
            # Deve aver chiamato connect con host '192.168.1.10' e port 5005
            app.network.connect.assert_called_with("192.168.1.10", 5005)
            self.assertTrue(app.is_connected)
            self.assertEqual(app.last_server_ip, "192.168.1.10:5005")
            self.assertIn("192.168.1.10:5005", app.status_label.cget("text"))


if __name__ == "__main__":
    unittest.main()
