# test_dm_gui_flow.py
"""
Test di integrazione per la coerenza dei flussi GUI lato Dungeon Master (DM):
1. Card DM nel Launcher ridotta a 2 bottoni (Campagne vs Sessione Rapida) e navigazione Hub <-> Editor <-> Avvio.
2. CampaignEditorFrame standalone: dirty check su chiusura, lancio diretto e fix NameError in CampaignEncounterDialog.
3. DMBestiaryPanel: assenza del pulsante '+ Crea Mostro' duplicato e fix UnboundLocalError su spawn online SRD.
4. DM_GUI: VTT HUD sulla mappa, sidebar collassabile (Ctrl+B), toolbar sinistra snellita, Bestiario tab di 1° livello,
   tab Mondo/Combattimento senza doppioni, Menu File/Strumenti/Vista puliti, salvataggio in-place e pill Meteo cliccabile.
"""

import os
import sys
import tempfile
import shutil
import threading
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["DND_MOCK_AUDIO"] = "1"

import ttkbootstrap as tb
from common.campaign import Campaign
from common.hex_utils import Hex
from common.i18n import _t, get_language, set_language
from common.theme import setup_theme
from server.campaign_editor_ui import (
    CampaignEditorFrame,
    CampaignEncounterDialog,
    CampaignSelectorFrame,
)
from server.dm_bestiary_panel import DMBestiaryPanel
from server.dm_gui import DM_GUI


def _walk_widgets(widget):
    result = [widget]
    for child in widget.winfo_children():
        result.extend(_walk_widgets(child))
    return result


def _collect_button_texts(root_widget):
    texts = []
    for w in _walk_widgets(root_widget):
        if isinstance(w, (tk.Button, ttk.Button, tk.Checkbutton, ttk.Checkbutton)):
            try:
                texts.append(w.cget("text"))
            except Exception:
                pass
    return texts


def _find_button_by_text(root_widget, target_text):
    for w in _walk_widgets(root_widget):
        if isinstance(w, (tk.Button, ttk.Button)):
            try:
                if w.cget("text") == target_text:
                    return w
            except Exception:
                pass
    return None


def _get_menu_command_labels(menubar, menu_title):
    end_idx = menubar.index("end")
    if end_idx is None:
        return []
    for idx in range(end_idx + 1):
        if menubar.type(idx) == "cascade" and menubar.entrycget(idx, "label") == menu_title:
            sub = menubar.nametowidget(menubar.entrycget(idx, "menu"))
            sub_end = sub.index("end")
            if sub_end is None:
                return []
            return [
                sub.entrycget(i, "label")
                for i in range(sub_end + 1)
                if sub.type(i) == "command"
            ]
    return []


class TestDMGuiFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()
        setup_theme(cls.root)

    @classmethod
    def tearDownClass(cls):
        set_language("it")
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self._orig_lang = get_language()
        set_language("it")
        self._tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        set_language(self._orig_lang or "it")
        if os.path.exists(self._tmp_dir):
            shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_launcher_dm_card_two_buttons_and_selector_editor_navigation(self):
        """La card DM del Launcher ha esattamente 2 bottoni e collega Hub <-> Editor con ritorno coerente."""
        import main

        launcher_win = tk.Toplevel(self.root)
        launcher_win.withdraw()

        def fake_mainloop(win_self, n=0):
            win_self.withdraw()
            win_self.update_idletasks()

        with patch.object(tk, "Tk", return_value=launcher_win), \
             patch.object(tk.Misc, "mainloop", fake_mainloop):
            main.start_app()

        launcher_root = launcher_win
        try:
            btn_camp = _find_button_by_text(launcher_root, _t("launcher_dm_btn_camp"))
            btn_quick = _find_button_by_text(launcher_root, _t("launcher_dm_btn_quick"))
            self.assertIsNotNone(btn_camp)
            self.assertIsNotNone(btn_quick)
            self.assertIs(btn_camp.master, btn_quick.master)

            dm_box_buttons = [
                w for w in btn_camp.master.winfo_children()
                if isinstance(w, (tk.Button, ttk.Button))
            ]
            self.assertEqual(len(dm_box_buttons), 2)
            self.assertNotIn("Crea / Modifica", " ".join(_collect_button_texts(launcher_root)))

            # 1) Clicca "Campagne (Prepara & Avvia)" -> entra nell'Hub selettore
            btn_camp.invoke()
            launcher_root.update_idletasks()
            selectors = [w for w in _walk_widgets(launcher_root) if isinstance(w, CampaignSelectorFrame)]
            self.assertEqual(len(selectors), 1)
            selector = selectors[0]

            # 2) Dal selettore crea una nuova campagna -> apre Editor con bottone '← Campagne' e Avvia Sessione
            selector.create_new_campaign()
            launcher_root.update_idletasks()
            editors = [w for w in _walk_widgets(launcher_root) if isinstance(w, CampaignEditorFrame)]
            self.assertEqual(len(editors), 1)
            editor = editors[0]
            self.assertIsNotNone(editor.on_launch_callback)
            self.assertIn(_t("btn_back_to_campaigns"), _collect_button_texts(editor))
            self.assertIn(_t("camp_ed_btn_launch"), _collect_button_texts(editor))

            # 3) Chiude Editor senza modifiche -> torna al Selettore senza dialoghi di conferma
            with patch("server.campaign_editor_ui.messagebox.askyesnocancel") as mock_ask:
                editor.close_editor()
                mock_ask.assert_not_called()
            launcher_root.update_idletasks()
            selectors_after = [w for w in _walk_widgets(launcher_root) if isinstance(w, CampaignSelectorFrame)]
            self.assertEqual(len(selectors_after), 1)
        finally:
            try:
                launcher_root.destroy()
            except Exception:
                pass

    def test_campaign_editor_dirty_close_launch_and_encounter_manual_monster_fix(self):
        """Dirty check chiusura editor, azione Avvia Sessione standalone e fix NameError in CampaignEncounterDialog."""
        camp_dir = os.path.join(self._tmp_dir, "cronache_test")
        camp = Campaign(name="Cronache Test", folder_path=camp_dir)
        camp.save(camp_dir)

        top = tk.Toplevel(self.root)
        top.withdraw()
        try:
            closed_count = [0]
            launched = []

            # A) Editor pulito: chiude senza prompt
            ed_clean = CampaignEditorFrame(
                top,
                campaign=camp,
                game_state=None,
                on_close_callback=lambda: closed_count.__setitem__(0, closed_count[0] + 1),
                on_launch_callback=lambda c: launched.append(c),
                back_button_text=_t("btn_back_to_campaigns"),
            )
            self.assertFalse(ed_clean._has_unsaved_changes())
            with patch("server.campaign_editor_ui.messagebox.askyesnocancel") as mock_ask:
                ed_clean.close_editor()
                mock_ask.assert_not_called()
            self.assertEqual(closed_count[0], 1)

            # B) Editor sporco: Cancel (None), Scarta (False), Salva e Chiudi (True)
            ed_dirty = CampaignEditorFrame(
                top,
                campaign=camp,
                game_state=None,
                on_close_callback=lambda: closed_count.__setitem__(0, closed_count[0] + 1),
                on_launch_callback=lambda c: launched.append(c),
                back_button_text=_t("btn_back_to_campaigns"),
            )
            ed_dirty.ent_title.delete(0, tk.END)
            ed_dirty.ent_title.insert(0, "Cronache Temporanee")
            self.assertTrue(ed_dirty._has_unsaved_changes())

            with patch("server.campaign_editor_ui.messagebox.askyesnocancel", return_value=None):
                ed_dirty.close_editor()
            self.assertEqual(closed_count[0], 1)

            with patch("server.campaign_editor_ui.messagebox.askyesnocancel", return_value=False):
                ed_dirty.close_editor()
            self.assertEqual(closed_count[0], 2)

            ed_save = CampaignEditorFrame(
                top,
                campaign=camp,
                game_state=None,
                on_close_callback=lambda: closed_count.__setitem__(0, closed_count[0] + 1),
                on_launch_callback=lambda c: launched.append(c),
            )
            ed_save.ent_title.delete(0, tk.END)
            ed_save.ent_title.insert(0, "Cronache Salvate")
            self.assertTrue(ed_save._has_unsaved_changes())
            with patch("server.campaign_editor_ui.messagebox.askyesnocancel", return_value=True), \
                 patch("server.campaign_editor_ui.messagebox.showinfo"):
                ed_save.close_editor()
            self.assertEqual(closed_count[0], 3)
            reloaded = Campaign.load(camp_dir)
            self.assertEqual(reloaded.name, "Cronache Salvate")

            # C) Launch standalone salva ed invoca on_launch_callback
            ed_launch = CampaignEditorFrame(
                top,
                campaign=reloaded,
                game_state=None,
                on_launch_callback=lambda c: launched.append(c),
            )
            with patch("server.campaign_editor_ui.messagebox.showinfo"):
                ed_launch.launch_campaign_session()
            self.assertEqual(len(launched), 1)
            self.assertEqual(launched[0].name, "Cronache Salvate")

            # D) Fix NameError in CampaignEncounterDialog.add_monster_manual (usa monster_sheet, non item_data)
            enc_dlg = CampaignEncounterDialog(top)
            try:
                fake_sheet = {
                    "name": "Ragno Gigante",
                    "hp": 26,
                    "ac": 14,
                    "initiative": 3,
                    "xp": 200,
                    "import_quantity": 2,
                    "strength": 14,
                    "dexterity": 16,
                    "constitution": 12,
                    "intelligence": 2,
                    "wisdom": 11,
                    "charisma": 4,
                    "attributes": {"darkvision": 60},
                }

                def fake_custom_npc_dialog(master=None, on_save_callback=None, **kwargs):
                    if on_save_callback:
                        on_save_callback(fake_sheet)
                    return MagicMock()

                with patch("server.dm_dialogs.CustomNPCDialog", side_effect=fake_custom_npc_dialog):
                    enc_dlg.add_monster_manual()

                self.assertEqual(len(enc_dlg.monsters), 1)
                self.assertEqual(enc_dlg.monsters[0]["name"], "Ragno Gigante")
                self.assertEqual(enc_dlg.monsters[0]["count"], 2)
                self.assertEqual(enc_dlg.monsters[0]["ac"], 14)
                self.assertEqual(enc_dlg.monsters[0]["sheet"], fake_sheet)
            finally:
                if enc_dlg.winfo_exists():
                    enc_dlg.destroy()
        finally:
            top.destroy()

    def test_bestiary_panel_no_duplicate_create_and_online_spawn_pos_fix(self):
        """DMBestiaryPanel non duplica '+ Crea Mostro' e non solleva UnboundLocalError sul ramo online."""
        top = tk.Toplevel(self.root)
        top.withdraw()
        try:
            mock_dm = MagicMock()
            mock_dm.master = top
            mock_dm.map_canvas._last_clicked_hex = None
            panel = DMBestiaryPanel(top, mock_dm)

            self.assertFalse(hasattr(panel, "btn_bestiary_create"))
            self.assertFalse(any("Crea Mostro" in t for t in _collect_button_texts(panel)))

            # Popola un risultato online SRD privo di "monster_data" (con chiave "index")
            self.assertTrue(hasattr(panel, "bestiario_results"))
            panel.bestiario_results = [{"source": "SRD", "index": "goblin", "name": "Goblin"}]
            panel.bestiario_listbox.delete(0, tk.END)
            panel.bestiario_listbox.insert(0, "Goblin (Open5e)")
            panel.bestiario_listbox.selection_set(0)

            started_calls = []

            class DummyThread:
                def __init__(self, target=None, args=(), daemon=None):
                    started_calls.append((target, args, daemon))

                def start(self):
                    pass

            with patch.object(threading, "Thread", DummyThread):
                panel.spawn_bestiario()
                mock_dm.map_canvas._last_clicked_hex = Hex(3, -1)
                panel.spawn_bestiario()

            self.assertEqual(len(started_calls), 2)
            self.assertEqual(started_calls[0][1][1], [0, 0])
            self.assertEqual(started_calls[1][1][1], [3, -1])
        finally:
            top.destroy()

    def test_dm_gui_vtt_hud_sidebar_bestiary_tab_menubar_and_weather(self):
        """Verifica end-to-end della DM_GUI: HUD mappa, sidebar Ctrl+B, Bestiario top-level, menu e pill meteo."""
        camp_dir = os.path.join(self._tmp_dir, "campagna_dm_gui")
        camp = Campaign(name="La Rocca d'Ambra", folder_path=camp_dir)
        camp.save(camp_dir)

        top = tk.Toplevel(self.root)
        top.withdraw()
        dm = None
        try:
            dm = DM_GUI(top, initial_campaign=camp)
            self.root.update_idletasks()

            # 1) HUD VTT sulla viewport mappa + toolbar sinistra esclusivamente con tool DM
            self.assertTrue(hasattr(dm, "vtt_hud_bar"))
            for attr in ("zoom_in_btn", "zoom_out_btn", "btn_hud_center", "btn_hud_ruler", "btn_hud_pan", "btn_hud_toggle_sidebar"):
                self.assertTrue(hasattr(dm, attr), f"Widget HUD mancante: {attr}")

            self.assertFalse(hasattr(dm, "btn_fow_tool"))
            self.assertFalse(hasattr(dm, "btn_darkness"))
            left_toolbar = dm.btn_aoe.master
            left_btns = _collect_button_texts(left_toolbar)
            for dup in ("✋", "📏", "🎯"):
                self.assertNotIn(dup, left_btns)

            # 2) Toggle sidebar (Ctrl+B): nasconde/mostra right_panel e aggiorna minsize colonna 2
            self.assertFalse(dm.sidebar_collapsed)
            self.assertEqual(dm.right_panel.winfo_manager(), "grid")
            dm.toggle_sidebar()
            self.assertTrue(dm.sidebar_collapsed)
            self.assertEqual(dm.right_panel.winfo_manager(), "")
            self.assertEqual(dm.main_frame.columnconfigure(2)["minsize"], 0)
            self.assertEqual(dm.btn_hud_toggle_sidebar.cget("text"), "◀")

            dm.toggle_sidebar()
            self.assertFalse(dm.sidebar_collapsed)
            self.assertEqual(dm.right_panel.winfo_manager(), "grid")
            self.assertEqual(dm.main_frame.columnconfigure(2)["minsize"], 360)
            self.assertEqual(dm.btn_hud_toggle_sidebar.cget("text"), "▶")

            # 3) Bestiario scheda top-level #3 in right_notebook + traduzione dinamica IT/EN
            tabs = list(dm.right_notebook.tabs())
            self.assertEqual(len(tabs), 5)
            self.assertEqual(tabs[2], str(dm.tab_bestiario))
            self.assertIsInstance(dm.bestiary_panel, DMBestiaryPanel)
            self.assertIs(dm.bestiary_panel.master, dm.tab_bestiario)

            self.assertFalse(hasattr(dm, "btn_spawn_png"))
            self.assertTrue(hasattr(dm, "btn_campaign_encounter"))
            self.assertTrue(hasattr(dm, "btn_encounter_builder"))
            self.assertTrue(hasattr(dm, "btn_add_npc"))

            self.assertFalse(hasattr(dm, "btn_world_manuals"))
            world_btns = _collect_button_texts(dm.tab_world)
            self.assertIn(_t("btn_live_flow"), world_btns)
            self.assertIn(_t("btn_session_chronicle"), world_btns)
            self.assertIn(_t("btn_campaign_journal"), world_btns)

            set_language("en")
            dm.refresh_ui_language()
            self.assertEqual(dm.right_notebook.tab(dm.tab_bestiario, "text"), _t("tab_bestiary"))
            set_language("it")
            dm.refresh_ui_language()
            self.assertEqual(dm.right_notebook.tab(dm.tab_bestiario, "text"), _t("tab_bestiary"))

            # 4) Menu File / Strumenti / Vista deduplicati + Salva Campagna Attiva in-place
            menubar = top.nametowidget(top.cget("menu"))
            file_labels = _get_menu_command_labels(menubar, _t("menu_file"))
            tools_labels = _get_menu_command_labels(menubar, _t("menu_tools"))
            view_labels = _get_menu_command_labels(menubar, _t("menu_view"))

            self.assertIn(_t("menu_save_campaign"), file_labels)
            self.assertIn(_t("menu_save_campaign_as"), file_labels)
            self.assertFalse(any("da File / Cartella" in l for l in file_labels))

            self.assertIn(_t("menu_optional_rules_workbench"), tools_labels)
            self.assertIn(_t("menu_calendar"), tools_labels)
            self.assertIn(_t("menu_shops"), tools_labels)
            self.assertFalse(any("Generatori Dungeon" in l for l in tools_labels))

            self.assertIn(_t("menu_toggle_sidebar_dm"), view_labels)

            camp.name = "La Rocca d'Ambra Modificata"
            dm.save_active_campaign()
            reloaded = Campaign.load(camp_dir)
            self.assertEqual(reloaded.name, "La Rocca d'Ambra Modificata")

            # 5) Pill Meteo/Oscurità cliccabile e helper _apply_weather_change
            self.assertTrue(bool(dm.top_status_weather_lbl.bind("<Button-1>")))
            dm.toggle_darkness_filter()
            self.assertEqual(dm.server.game_state.weather, "Oscurità")
            self.assertIn("🌑", dm.top_status_weather_lbl.cget("text"))
            dm.toggle_darkness_filter()
            self.assertEqual(dm.server.game_state.weather, "Sereno")
            dm._apply_weather_change("Tempesta")
            self.assertEqual(dm.server.game_state.weather, "Tempesta")
            self.assertIn("⛈️", dm.top_status_weather_lbl.cget("text"))
        finally:
            if dm is not None:
                try:
                    dm.server.stop()
                except Exception:
                    pass
                try:
                    if getattr(dm, "voice_client", None):
                        dm.voice_client.stop()
                except Exception:
                    pass
            if top.winfo_exists():
                top.destroy()
            self.root.update_idletasks()


if __name__ == "__main__":
    unittest.main()
