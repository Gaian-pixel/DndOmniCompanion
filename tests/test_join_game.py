# tests/test_join_game.py
"""
Test per il flusso di connessione e unione a una partita:
- LoginDialog con selezione rapida del server e del personaggio
- Cronologia server recenti (settings.json)
- Preset IP locale (127.0.0.1)
- Auto-connessione di ClientGUI all'avvio da launcher
- Parsing host e porta personalizzata
"""

import os
import tempfile
import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch
import client.character_manager as cm_mod
import client.login_ui as login_ui_mod
import common.i18n as i18n_mod
from client.character_manager import Character, CharacterManager
from client.login_ui import LoginDialog, load_server_history, save_server_history


class TestJoinGameFlow(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._settings_path = os.path.join(self._tmp_dir.name, "settings.json")
        self._char_file = os.path.join(self._tmp_dir.name, "characters.json")
        self._patch_login_settings = patch.object(login_ui_mod, "SETTINGS_PATH", self._settings_path)
        self._patch_i18n_settings = patch.object(i18n_mod, "SETTINGS_PATH", self._settings_path)
        self._patch_char_file = patch.object(cm_mod, "CHARACTER_FILE", self._char_file)
        self._patch_login_settings.start()
        self._patch_i18n_settings.start()
        self._patch_char_file.start()

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
        self._patch_char_file.stop()
        self._patch_i18n_settings.stop()
        self._patch_login_settings.stop()
        self._tmp_dir.cleanup()

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

    def test_login_dialog_locked_long_name_wrapping_and_resizing(self):
        """Regressione LoginDialog: testo lungo wrappa senza schiacciare 'Cambia Eroe' e segue il resize."""
        long_hero = Character("Ser Kaelen di Castelalto", "Paladino 6 / Stregone 6")
        long_hero.level = 12
        long_hero.race = "Mezzelfo"
        long_hero.campaign = "La Cripta dei Sussurri Eterna delle Terre Perdute"
        self.mgr.characters = [long_hero, self.char1]

        prev_lang = i18n_mod.get_language()
        host = tk.Toplevel(self.root)
        host.geometry("1280x800+-3000+-3000")
        host.update()
        try:
            for lang in ("it", "en"):
                i18n_mod.set_language(lang)
                dlg = LoginDialog(host, self.mgr, initial_character=long_hero, lock_character=True)
                try:
                    dlg.update()
                    win_w, win_h = dlg.winfo_width(), dlg.winfo_height()
                    req_w, req_h = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
                    self.assertGreaterEqual(win_w, req_w, f"[{lang}] req_w={req_w} > win_w={win_w}")
                    self.assertGreaterEqual(win_h, req_h, f"[{lang}] req_h={req_h} > win_h={win_h}")

                    # Locked hero label wraps instead of inflating width or crushing btn_change_char
                    wrap_initial = int(float(dlg.locked_hero_lbl.cget("wraplength")))
                    self.assertGreaterEqual(wrap_initial, 120)
                    self.assertLess(wrap_initial, win_w)
                    btn_w = dlg.btn_change_char.winfo_width()
                    btn_h = dlg.btn_change_char.winfo_height()
                    self.assertGreaterEqual(btn_w, dlg.btn_change_char.winfo_reqwidth() - 2)
                    self.assertGreaterEqual(btn_h, dlg.btn_change_char.winfo_reqheight() - 2)

                    min_w, min_h = dlg.minsize()
                    self.assertLessEqual(min_w, win_w)
                    self.assertGreaterEqual(min_h, req_h)

                    # Manual dialog resizing updates wraplength and preserves minimum bounds after shrink-back
                    dlg.geometry("720x500")
                    dlg.update()
                    wrap_wide = int(float(dlg.locked_hero_lbl.cget("wraplength")))
                    self.assertGreater(wrap_wide, wrap_initial + 120)

                    dlg.geometry(f"{min_w}x{min_h}")
                    dlg.update()
                    wrap_narrow = int(float(dlg.locked_hero_lbl.cget("wraplength")))
                    self.assertLess(wrap_narrow, wrap_wide)
                    self.assertLessEqual(dlg.winfo_reqwidth(), dlg.winfo_width())
                    self.assertLessEqual(dlg.winfo_reqheight(), dlg.winfo_height())
                    self.assertGreaterEqual(dlg.btn_change_char.winfo_width(), dlg.btn_change_char.winfo_reqwidth() - 2)
                    self.assertGreaterEqual(dlg.btn_connect.winfo_width(), dlg.btn_connect.winfo_reqwidth() - 2)
                finally:
                    if dlg.winfo_exists():
                        dlg.destroy()
        finally:
            if host.winfo_exists():
                host.destroy()
            i18n_mod.set_language(prev_lang)

    def test_login_dialog_unlocked_and_small_display_resolutions(self):
        """Regressione LoginDialog: modalità unlocked e schermi compatti / desktop realistici senza clipping dei CTA."""
        long_hero = Character("Aria Tempesta d'Acciaio", "Mago 5 / Artefice 4")
        long_hero.level = 9
        long_hero.race = "Elfo Alto"
        long_hero.campaign = "Cronache dell'Abisso"
        self.mgr.characters = [long_hero, self.char1, self.char2]

        host = tk.Toplevel(self.root)
        host.geometry("1280x800+-3000+-3000")
        host.update()
        try:
            for sw, sh in [(640, 480), (800, 600), (1024, 720), (1366, 768), (1920, 1080)]:
                with patch.object(LoginDialog, "_available_screen_bounds", return_value=(sw, sh)):
                    for locked in (True, False):
                        dlg = LoginDialog(host, self.mgr, initial_character=long_hero, lock_character=locked)
                        try:
                            dlg.update()
                            dw, dh = dlg.winfo_width(), dlg.winfo_height()
                            self.assertLessEqual(dw, sw - 40)
                            self.assertLessEqual(dh, sh - 60)

                            # Key primary controls stay inside dialog bounds and retain clickable geometry
                            key_widgets = [dlg.ip_combo, dlg.btn_local, dlg.pin_entry, dlg.pin_toggle_btn, dlg.btn_connect, dlg.btn_cancel]
                            if locked:
                                key_widgets.append(dlg.btn_change_char)
                            else:
                                key_widgets.extend([dlg.char_listbox, dlg.btn_manage_hub])

                            for wdg in key_widgets:
                                self.assertTrue(wdg.winfo_ismapped(), f"{wdg} unmapped at {sw}x{sh} lock={locked}")
                                rx = wdg.winfo_rootx() - dlg.winfo_rootx()
                                ry = wdg.winfo_rooty() - dlg.winfo_rooty()
                                ww, wh = wdg.winfo_width(), wdg.winfo_height()
                                self.assertGreaterEqual(rx, 0)
                                self.assertGreaterEqual(ry, 0)
                                self.assertLessEqual(rx + ww, dw + 2)
                                self.assertLessEqual(ry + wh, dh + 2)
                                self.assertGreaterEqual(wh, max(16, wdg.winfo_reqheight() - 2) if wdg is not dlg.char_listbox else 30)
                        finally:
                            if dlg.winfo_exists():
                                dlg.destroy()

            # Verify transition from locked -> unlocked expands safely & keeps buttons visible
            dlg_t = LoginDialog(host, self.mgr, initial_character=long_hero, lock_character=True)
            try:
                dlg_t.update()
                dlg_t.unlock_character_selection()
                dlg_t.update()
                self.assertFalse(dlg_t.lock_character)
                self.assertIsNotNone(dlg_t.char_listbox)
                self.assertTrue(dlg_t.btn_manage_hub.winfo_ismapped())
                self.assertTrue(dlg_t.btn_connect.winfo_ismapped())
            finally:
                if dlg_t.winfo_exists():
                    dlg_t.destroy()
        finally:
            if host.winfo_exists():
                host.destroy()

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
