import json
import os
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import MagicMock, patch

import client.character_manager as cm_mod
from client.character_creation_wizard import CharacterCreationWizardFrame
from client.character_manager import Character, CharacterManager
from client.character_manager_ui import CharacterManagerFrame
from client.character_sheet_ui import CharacterSheetFrame, CharacterSheetUI
from client.client import ClientGUI
from client.login_ui import LoginDialog
from common.i18n import _t, get_language, set_language


def _walk_widgets(root_widget):
    """Restituisce ricorsivamente tutti i widget discendenti."""
    result = []
    try:
        children = root_widget.winfo_children()
    except Exception:
        return result
    for child in children:
        result.append(child)
        result.extend(_walk_widgets(child))
    return result


def _collect_button_texts(root_widget):
    """Restituisce i testi di tutti i Button / ttk.Button discendenti."""
    texts = []
    for w in _walk_widgets(root_widget):
        if isinstance(w, (tk.Button, ttk.Button)):
            try:
                texts.append(str(w.cget("text")))
            except Exception:
                pass
    return texts


def _collect_label_texts(root_widget):
    """Restituisce i testi di tutte le Label / ttk.Label discendenti."""
    texts = []
    for w in _walk_widgets(root_widget):
        if isinstance(w, (tk.Label, ttk.Label)):
            try:
                texts.append(str(w.cget("text")))
            except Exception:
                pass
    return texts


class TestPlayerGuiFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception as e:
            raise unittest.SkipTest(f"Tkinter display not available: {e}")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "root", None):
            try:
                cls.root.destroy()
            except Exception:
                pass

    def setUp(self):
        self._orig_lang = get_language()
        set_language("it")
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._char_file = os.path.join(self._tmp_dir.name, "characters.json")
        self._patch_char_file = patch.object(cm_mod, "CHARACTER_FILE", self._char_file)
        self._patch_char_file.start()

        self.manager = CharacterManager()
        self.hero1 = Character(name="Aragorn", race="Umano", char_class="Guerriero", level=3)
        self.hero2 = Character(name="Elara", race="Elfo", char_class="Mago", level=4)
        self.hero3 = Character(name="Grog", race="Mezzorco", char_class="Barbaro", level=5)
        self.manager.add_character(self.hero1)
        self.manager.add_character(self.hero2)
        self.manager.add_character(self.hero3)

    def tearDown(self):
        set_language(self._orig_lang)
        self._patch_char_file.stop()
        self._tmp_dir.cleanup()

    def test_character_manager_hub_no_manual_and_import_json(self):
        """Verifica rimozione pulsante Manuale, presenza Importa JSON e importazione funzionante."""
        top = tk.Toplevel(self.root)
        top.withdraw()
        try:
            frame = CharacterManagerFrame(top, manager=self.manager, is_embedded=True)
            btn_texts = _collect_button_texts(frame)
            self.assertIn(_t("char_manager_btn_import"), btn_texts)
            self.assertNotIn(_t("char_manager_btn_manual"), btn_texts)
            for t in btn_texts:
                self.assertNotIn("Manuale", t)

            import_path = os.path.join(self._tmp_dir.name, "exported_hero.json")
            exported = Character(name="Valeros", race="Umano", char_class="Paladino", level=6).to_dict()
            exported["id"] = "fixed-source-id"
            with open(import_path, "w", encoding="utf-8") as f:
                json.dump(exported, f)

            with patch("client.character_manager_ui.filedialog.askopenfilename", return_value=import_path), \
                 patch("client.character_manager_ui.messagebox.showinfo"):
                frame.import_character_json()

            names = [c.name for c in self.manager.characters]
            self.assertIn("Valeros", names)
            self.assertIsNotNone(frame.selected_character)
            self.assertEqual(frame.selected_character.name, "Valeros")
            self.assertNotEqual(frame.selected_character.id, "fixed-source-id")
            self.assertIn(frame.selected_character.id, frame.tree.selection())
        finally:
            top.destroy()

    def test_character_manager_preselection_read_only_and_embedded_confirm(self):
        """Verifica preselezione da ID, modalità sola-selezione online e callback embedded."""
        top = tk.Toplevel(self.root)
        top.withdraw()
        try:
            callback_alive = []

            def on_select(char):
                callback_alive.append((char.id, bool(frame.winfo_exists())))

            frame = CharacterManagerFrame(
                top,
                manager=self.manager,
                on_select_callback=on_select,
                is_embedded=True,
                selected_char_id=self.hero2.id,
                select_btn_text=_t("char_manager_btn_play"),
                read_only_select=False,
            )
            self.assertIsNotNone(frame.selected_character)
            self.assertEqual(frame.selected_character.id, self.hero2.id)
            self.assertIn(_t("char_manager_btn_play"), _collect_button_texts(frame.right_col))

            frame.confirm_selection()
            self.assertEqual(callback_alive, [(self.hero2.id, True)])
        finally:
            top.destroy()

        top2 = tk.Toplevel(self.root)
        top2.withdraw()
        try:
            blocked_calls = []
            ro_frame = CharacterManagerFrame(
                top2,
                manager=self.manager,
                on_select_callback=lambda c: blocked_calls.append(c),
                is_embedded=False,
                selected_char_id=self.hero1.id,
                read_only_select=True,
            )
            right_btns = _collect_button_texts(ro_frame.right_col)
            right_lbls = _collect_label_texts(ro_frame.right_col)
            self.assertNotIn(_t("char_manager_btn_select"), right_btns)
            self.assertIn(_t("char_manager_online_notice"), right_lbls)
            ro_frame.confirm_selection()
            self.assertEqual(blocked_calls, [])
        finally:
            top2.destroy()

    def test_login_dialog_locked_vs_standard_hub_flow(self):
        """Verifica modalità lock_character=True (solo IP + scheda bloccata) e rimozione mini-CRUD."""
        locked_dlg = LoginDialog(
            self.root,
            self.manager,
            initial_character=self.hero1,
            initial_ip="10.1.2.3",
            lock_character=True,
        )
        try:
            self.assertTrue(locked_dlg.lock_character)
            self.assertIsNone(locked_dlg.char_listbox)
            lbl_texts = _collect_label_texts(locked_dlg)
            self.assertTrue(any(self.hero1.name in txt for txt in lbl_texts))
            self.assertIn(_t("login_btn_change_char"), _collect_button_texts(locked_dlg))
            locked_dlg.connect()
            self.assertEqual(locked_dlg.result, ("10.1.2.3", self.hero1))
        finally:
            if locked_dlg.winfo_exists():
                locked_dlg.destroy()

        std_dlg = LoginDialog(self.root, self.manager, lock_character=False)
        try:
            self.assertFalse(std_dlg.lock_character)
            self.assertIsNotNone(std_dlg.char_listbox)
            btn_texts = _collect_button_texts(std_dlg)
            self.assertIn(_t("login_btn_manage_hub"), btn_texts)
            for forbidden in ("Modifica", "Elimina", "Crea Nuovo", "Edit", "Delete"):
                self.assertFalse(any(forbidden in b for b in btn_texts), f"Pulsante duplicato trovato in LoginDialog: {b if False else forbidden}")
        finally:
            if std_dlg.winfo_exists():
                std_dlg.destroy()

    def test_wizard_custom_back_button_label_for_manager_return(self):
        """Verifica che CharacterCreationWizardFrame accetti back_btn_key='wizard_btn_back_to_manager'."""
        top = tk.Toplevel(self.root)
        top.withdraw()
        try:
            closed_flag = []
            wiz = CharacterCreationWizardFrame(
                top,
                self.manager,
                on_complete_callback=lambda _c: None,
                on_close_callback=lambda: closed_flag.append(True),
                back_btn_key="wizard_btn_back_to_manager",
            )
            self.assertIn(_t("wizard_btn_back_to_manager"), _collect_button_texts(wiz))
            wiz.cancel_btn.invoke()
            self.assertEqual(closed_flag, [True])
        finally:
            top.destroy()

    def test_character_sheet_single_action_bar_and_dirty_close(self):
        """Verifica barra azioni unica nella scheda e controllo unificato modifiche non salvate."""
        top = tk.Toplevel(self.root)
        top.withdraw()
        try:
            saved_chars = []
            closed = []
            sheet = CharacterSheetFrame(
                top,
                self.hero2,
                self.manager,
                on_save_callback=lambda c: saved_chars.append(c),
                on_close_callback=lambda: closed.append(True),
                is_overlay=True,
            )
            self.assertTrue(hasattr(sheet, "action_bar"))
            self.assertFalse(hasattr(sheet, "save_button"))

            all_btn_texts = _collect_button_texts(sheet)
            self.assertEqual(all_btn_texts.count(_t("sheet_btn_quick_save")), 1)
            self.assertEqual(all_btn_texts.count(_t("sheet_btn_close_esc")), 1)

            # Nessuna modifica: request_close chiude subito senza prompt
            self.assertFalse(sheet._has_unsaved_changes())
            with patch("client.character_sheet_ui.messagebox.askyesnocancel") as mock_ask:
                self.assertTrue(sheet.request_close())
                mock_ask.assert_not_called()
            self.assertEqual(len(closed), 1)

            # Modifica effettuata -> Annulla chiusura (None)
            sheet2 = CharacterSheetFrame(
                top,
                self.hero2,
                self.manager,
                on_save_callback=lambda c: saved_chars.append(c),
                on_close_callback=lambda: closed.append(True),
                is_overlay=True,
            )
            sheet2.alignment_var.set("Caotico Buono")
            self.assertTrue(sheet2._has_unsaved_changes())
            with patch("client.character_sheet_ui.messagebox.askyesnocancel", return_value=None):
                self.assertFalse(sheet2.request_close())
            self.assertEqual(len(closed), 1)

            # Conferma salvataggio (True) -> salva e chiude
            with patch("client.character_sheet_ui.messagebox.askyesnocancel", return_value=True):
                self.assertTrue(sheet2.request_close())
            self.assertEqual(self.hero2.alignment, "Caotico Buono")
            self.assertGreaterEqual(len(saved_chars), 1)
            self.assertEqual(len(closed), 2)

            # Scarta modifiche (False) -> ripristina stato iniziale e chiude
            sheet3 = CharacterSheetFrame(
                top,
                self.hero2,
                self.manager,
                on_save_callback=lambda c: saved_chars.append(c),
                on_close_callback=lambda: closed.append(True),
                is_overlay=True,
            )
            sheet3.alignment_var.set("Malvagio")
            self.assertTrue(sheet3._has_unsaved_changes())
            with patch("client.character_sheet_ui.messagebox.askyesnocancel", return_value=False):
                self.assertTrue(sheet3.request_close())
            self.assertEqual(self.hero2.alignment, "Caotico Buono")
            self.assertEqual(len(closed), 3)
        finally:
            top.destroy()

        # Anche CharacterSheetUI (staccata) deve esporre la stessa action_bar unica e route _on_window_close -> request_close()
        detached = CharacterSheetUI(
            self.root,
            self.hero1,
            self.manager,
            on_dock_callback=lambda: None,
        )
        try:
            self.assertTrue(hasattr(detached, "action_bar"))
            self.assertFalse(hasattr(detached, "save_button"))
            self.assertEqual(_collect_button_texts(detached).count(_t("sheet_btn_quick_save")), 1)
            detached._sheet_frame_internal.request_close = MagicMock(
                wraps=detached._sheet_frame_internal.request_close
            )
            detached._on_window_close()
            detached._sheet_frame_internal.request_close.assert_called_once()
        finally:
            if detached.winfo_exists():
                detached.destroy()

        # Verifica mapping di common.messagebox.askyesnocancel ("Yes"/"Sì"/"No"/"Cancel"/None)
        from common.messagebox import askyesnocancel
        with patch("common.messagebox.Messagebox.yesnocancel", return_value="Yes"):
            self.assertIs(askyesnocancel("t", "m"), True)
        with patch("common.messagebox.Messagebox.yesnocancel", return_value="Sì"):
            self.assertIs(askyesnocancel("t", "m"), True)
        with patch("common.messagebox.Messagebox.yesnocancel", return_value="No"):
            self.assertIs(askyesnocancel("t", "m"), False)
        with patch("common.messagebox.Messagebox.yesnocancel", return_value="Cancel"):
            self.assertIsNone(askyesnocancel("t", "m"))
        with patch("common.messagebox.Messagebox.yesnocancel", return_value=None):
            self.assertIsNone(askyesnocancel("t", "m"))

    def test_client_gui_player_streamlining_and_contextual_features(self):
        """Verifica UI Client snellita: rest simmetrico, no duplicati toolbar/menu, privilegi contestuali e Esc/C."""
        top = tk.Toplevel(self.root)
        top.withdraw()
        try:
            client = ClientGUI(top, initial_character=self.hero2)  # Mago (Wizard)

            # Griglia azioni: Riposo Lungo invece del pulsante duplicato Manuali
            self.assertTrue(hasattr(client, "btn_short_rest"))
            self.assertTrue(hasattr(client, "btn_long_rest"))
            self.assertFalse(hasattr(client, "manuals_button"))

            # Toolbar sinistra: rimossi i doppioni di Righello e Centra Mappa (già nell'HUD mappa)
            self.assertFalse(hasattr(client, "measure_btn"))
            self.assertFalse(hasattr(client, "center_map_btn"))

            # Selettore eroe sidebar: nessun mini-tasto "✨" accanto al combobox
            combo_parent_btns = _collect_button_texts(client.active_character_combo.master)
            self.assertNotIn("✨", combo_parent_btns)
            self.assertIn("👤", combo_parent_btns)

            # Menu Personaggio: niente voce manuale fittizia né Alzati duplicato
            menubar_name = top.cget("menu")
            menubar = top.nametowidget(menubar_name)
            char_menu_idx = None
            for idx in range(menubar.index("end") + 1):
                if menubar.type(idx) == "cascade" and menubar.entrycget(idx, "label") == _t("menu_character"):
                    char_menu_idx = idx
                    break
            self.assertIsNotNone(char_menu_idx)
            char_menu = menubar.nametowidget(menubar.entrycget(char_menu_idx, "menu"))
            char_labels = [
                char_menu.entrycget(i, "label")
                for i in range(char_menu.index("end") + 1)
                if char_menu.type(i) == "command"
            ]
            self.assertNotIn(_t("menu_create_manual_character"), char_labels)
            self.assertFalse(any("Alzati da Prono" in lbl for lbl in char_labels))

            # Privilegi di classe contestuali:
            # 1) Mago -> riquadro nascosto
            self.assertEqual(client.class_features_frame.winfo_manager(), "")

            # 2) Guerriero -> Second Wind + Action Surge visibili, Rage nascosto
            client.set_active_character_from_manager(self.hero1)
            self.assertEqual(client.class_features_frame.winfo_manager(), "pack")
            self.assertEqual(client.btn_second_wind.winfo_manager(), "pack")
            self.assertEqual(client.btn_action_surge.winfo_manager(), "pack")
            self.assertEqual(client.btn_rage.winfo_manager(), "")

            # 3) Barbaro -> solo Rage visibile
            client.set_active_character_from_manager(self.hero3)
            self.assertEqual(client.class_features_frame.winfo_manager(), "pack")
            self.assertEqual(client.btn_rage.winfo_manager(), "pack")
            self.assertEqual(client.btn_second_wind.winfo_manager(), "")
            self.assertEqual(client.btn_action_surge.winfo_manager(), "")

            # 4) Multiclasse Guerriero/Barbaro -> tutti e 3 visibili
            mc = Character(name="Krag", char_class="Guerriero / Barbaro", level=4)
            mc.classes = {"Guerriero": 2, "Barbaro": 2}
            client.set_active_character_from_manager(mc)
            self.assertEqual(client.class_features_frame.winfo_manager(), "pack")
            self.assertEqual(client.btn_second_wind.winfo_manager(), "pack")
            self.assertEqual(client.btn_action_surge.winfo_manager(), "pack")
            self.assertEqual(client.btn_rage.winfo_manager(), "pack")

            # Esc e toggle C (open_stats_dialog) passano da stats_sheet_frame.request_close()
            client.open_stats_dialog()
            self.assertTrue(client.stats_overlay_visible)
            client.stats_sheet_frame.request_close = MagicMock(wraps=client.stats_sheet_frame.request_close)
            client._on_key_escape(None)
            client.stats_sheet_frame.request_close.assert_called_once()
            self.assertFalse(client.stats_overlay_visible)

            client.open_stats_dialog()
            self.assertTrue(client.stats_overlay_visible)
            client.stats_sheet_frame.request_close = MagicMock(wraps=client.stats_sheet_frame.request_close)
            client.open_stats_dialog()
            client.stats_sheet_frame.request_close.assert_called_once()
            self.assertFalse(client.stats_overlay_visible)

            # Manager personaggi durante sessione online passa read_only_select=True
            client.is_connected = True
            with patch("client.character_manager_ui.CharacterManagerDialog") as mock_mgr_dlg, \
                 patch.object(top, "wait_window"):
                client.open_character_manager_dialog()
                self.assertTrue(mock_mgr_dlg.called)
                _, kwargs = mock_mgr_dlg.call_args
                self.assertTrue(kwargs.get("read_only_select"))
                self.assertEqual(kwargs.get("selected_char_id"), mc.id)
        finally:
            try:
                client.destroy_cleanup()
            except Exception:
                pass
            top.destroy()


if __name__ == "__main__":
    unittest.main()
