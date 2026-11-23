"""Phase 7 regression suite: TASK-053 Player/DM UX sync, Tk crash guards, i18n keys & command palette."""

import ast
import gc
import os
import queue
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("DND_MOCK_AUDIO", "1")
REPO_ROOT = Path(__file__).resolve().parent.parent


def _collect_widgets(widget, cls_tuple):
    found = []
    for child in widget.winfo_children():
        if isinstance(child, cls_tuple):
            found.append(child)
        found.extend(_collect_widgets(child, cls_tuple))
    return found


def _cleanup_toplevels(root):
    for w in list(root.winfo_children()):
        if isinstance(w, tk.Toplevel):
            try:
                w.grab_release()
            except Exception:
                pass
            try:
                if w.winfo_exists():
                    w.destroy()
            except Exception:
                pass


class TestPhase7UxSyncI18n(unittest.TestCase):
    """Test mirati TASK-053: i18n completo, Short Rest, sync scheda, Spinbox sicuri e Palette."""

    def test_zero_missing_i18n_keys_and_it_en_symmetry(self):
        from common.i18n import STRINGS, _t, get_language, set_language

        used_keys = set()
        scan_files = []
        for folder in ("common", "server", "client", "components"):
            scan_files.extend((REPO_ROOT / folder).rglob("*.py"))
        scan_files.extend([REPO_ROOT / "main.py", REPO_ROOT / "build_release.py"])

        for py_path in scan_files:
            tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "_t"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    used_keys.add(node.args[0].value)

        it_keys = set(STRINGS["it"].keys())
        en_keys = set(STRINGS["en"].keys())
        self.assertEqual(used_keys - it_keys, set())
        self.assertEqual(used_keys - en_keys, set())
        self.assertEqual(it_keys - en_keys, set())
        self.assertEqual(en_keys - it_keys, set())

        prev = get_language()
        try:
            set_language("it")
            it_vals = (_t("menu_special_abilities"), _t("menu_shops"), _t("menu_downtime"))
            set_language("en")
            en_vals = (_t("menu_special_abilities"), _t("menu_shops"), _t("menu_downtime"))
            for it_s, en_s in zip(it_vals, en_vals):
                self.assertNotEqual(it_s, en_s)
        finally:
            set_language(prev)

    def test_short_rest_in_combat_block_and_online_single_send(self):
        from client.character_manager import Character
        from client.client import ClientGUI
        from client.sheet_panels.vitals_panel import VitalsPanel

        root = tk.Tk()
        root.withdraw()
        try:
            c = Character(name="Kael", campaign="Test")
            c.char_class = "Guerriero"
            c.level = 3
            c.hp_max = 30
            c.hp_current = 15
            c.hit_dice_total = 3
            c.hit_dice_current = 3
            c.hit_dice_type = "d10"

            sent_packets = []
            host = MagicMock()
            host.master = root
            host.name = "Kael"
            host.active_character = c
            host.is_connected = True
            host.combat_active = True
            host.network = MagicMock()
            host.network.send.side_effect = lambda msg: sent_packets.append(msg)
            host.character_manager = MagicMock()

            # 1) In-combat block on ClientGUI.open_short_rest_dialog
            ClientGUI.open_short_rest_dialog(host)
            host.show_toast.assert_called_once()
            self.assertEqual(len([w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]), 0)
            self.assertEqual(sent_packets, [])

            # 2) Out-of-combat online ClientGUI.open_short_rest_dialog sends ONLY SHORT_REST_REQUEST
            host.combat_active = False
            ClientGUI.open_short_rest_dialog(host)
            tl = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
            self.assertEqual(len(tl), 1)
            btns = _collect_widgets(tl[0], (ttk.Button, tk.Button))
            go_btn = [b for b in btns if "Riposa" in str(b.cget("text"))][0]
            go_btn.invoke()
            self.assertEqual(len(sent_packets), 1)
            self.assertEqual(sent_packets[0]["type"], "SHORT_REST_REQUEST")

            # 3) In-combat block on VitalsPanel.short_rest
            sheet = tk.Frame(root)
            sheet.character = c
            sheet.combat_active = True
            with patch("client.sheet_panels.vitals_panel.messagebox.showwarning") as mock_warn:
                VitalsPanel.short_rest(sheet)
            mock_warn.assert_called_once()
            self.assertEqual(len(_collect_widgets(sheet, tk.Toplevel)), 0)

            # 4) Out-of-combat VitalsPanel.short_rest wired to ClientGUI.on_character_saved avoids double sync
            sent_packets.clear()
            c.hit_dice_current = 3
            c.hp_current = 12
            sheet.combat_active = False
            sheet.is_connected = True
            sheet.network = host.network
            sheet.manager = MagicMock()
            sheet.roll_callback = None
            sheet.hp_cur_var = tk.IntVar(value=c.hp_current)
            sheet.hp_max_var = tk.IntVar(value=c.hp_max)
            sheet.on_save_callback = lambda ch: ClientGUI.on_character_saved(host, ch)

            VitalsPanel.short_rest(sheet)
            dlg = [w for w in sheet.winfo_children() if isinstance(w, tk.Toplevel)][0]
            dlg.withdraw()
            v_btns = _collect_widgets(dlg, (ttk.Button,))
            v_btns[0].invoke()
            v_btns[-1].invoke()

            self.assertEqual(len(sent_packets), 1)
            self.assertEqual(sent_packets[0]["type"], "SHORT_REST_REQUEST")
            self.assertFalse(hasattr(c, "_skip_network_sync_once"))

            # Subsequent direct on_character_saved still sends normal stats + full_sheet
            sent_packets.clear()
            ClientGUI.on_character_saved(host, c)
            self.assertEqual([p["type"] for p in sent_packets], ["UPDATE_STATS_REQUEST", "UPDATE_FULL_SHEET_REQUEST"])
        finally:
            _cleanup_toplevels(root)
            root.destroy()
            gc.collect()

    def test_sheet_persist_sync_null_manager_and_empty_weapon_bonus(self):
        from client.character_manager import Character
        from client.character_sheet_ui import CharacterSheetUI, WeaponDialog
        from client.sheet_panels.spells_panel import SpellsPanel

        root = tk.Tk()
        root.withdraw()
        try:
            c = Character(name="Lyra", campaign="Test")
            c.char_class = "Mago"
            c.level = 3
            c.attributes["INT"] = 16
            c.hp_max = 18
            c.hp_current = 18
            c.superiority_dice_max = 4
            c.superiority_dice_current = 2
            c.spellbook = [{"name": "Dardo Incantato", "level": 1, "prepared": False}]
            c.inventory_grid = [
                {"name": "Bacchetta", "type": "Equipaggiamento", "charges_max": 3, "charges_current": 3, "container": "equipped"}
            ] + [None] * 24

            sent = []
            net = MagicMock()
            net.send.side_effect = lambda msg: sent.append(msg)
            sheet = CharacterSheetUI(root, c, manager=None, is_connected=True, network=net)
            sheet.withdraw()
            frame = sheet._sheet_frame_internal

            with patch("client.character_sheet_ui.messagebox.showinfo"), \
                 patch("client.character_sheet_ui.messagebox.askyesno", return_value=True), \
                 patch("client.character_sheet_ui.simpledialog.askstring", return_value="Arcana"), \
                 patch("client.character_sheet_ui.simpledialog.askinteger", return_value=2):
                frame._add_fetched_spell("Palla di Fuoco", 3, "1 azione", "45 m", "Boom")
                frame.add_custom_resource_dialog()
                frame.spend_superiority_die_action()
                frame.toggle_drop_backpack()
                spell_items = frame.spell_tree.get_children()
                self.assertTrue(spell_items)
                frame.spell_tree.selection_set(spell_items[0])
                SpellsPanel.toggle_spell_prepared(frame)

            self.assertTrue(c.spellbook[0]["prepared"])
            self.assertTrue(any(sp["name"] == "Palla di Fuoco" for sp in c.spellbook))
            self.assertTrue(any(r["name"] == "Arcana" for r in c.custom_resources))
            self.assertEqual(c.superiority_dice_current, 1)
            self.assertGreaterEqual(sum(1 for p in sent if p["type"] == "UPDATE_FULL_SHEET_REQUEST"), 5)

            saved_weapons = []
            wdlg = WeaponDialog(root, on_save_callback=lambda d: saved_weapons.append(d))
            wdlg.withdraw()
            wdlg.name_var.set("Spada Vuota")
            root.setvar(str(wdlg.bonus_var), "")
            wdlg.save()
            self.assertEqual(len(saved_weapons), 1)
            self.assertEqual(saved_weapons[0]["bonus"], 0)
        finally:
            _cleanup_toplevels(root)
            root.destroy()
            gc.collect()

    def test_weapon_edit_approval_in_place_server_and_client(self):
        from types import SimpleNamespace
        from common.game_state import GameState
        from server.dm_campaign_session_mixin import DMCampaignSessionMixin
        from client.character_manager import Character
        from client.network_handlers import ClientNetworkHandlersMixin

        root = tk.Tk()
        root.withdraw()
        try:
            # 1) Server side prompt_item_approval with action="edit"
            gs = GameState(queue.Queue())
            player = SimpleNamespace(
                name="Aria",
                conn=object(),
                ac=14,
                full_sheet={
                    "weapons": [
                        {"name": "Spada Lunga", "bonus": 0, "damage_dice": "1d8"},
                        {"name": "Pugnale", "bonus": 0, "damage_dice": "1d4"},
                    ],
                    "inventory_grid": [None] * 25,
                },
            )
            dm_stub = MagicMock()
            dm_stub.master = root
            dm_stub.server = SimpleNamespace(game_state=gs)
            edit_req = {
                "name": "Spada Lunga +1",
                "type": "Arma",
                "action": "edit",
                "target_collection": "weapons",
                "bonus": 1,
                "damage_dice": "1d8",
            }
            with patch("common.messagebox.messagebox.askyesno", return_value=True) as mock_ask, \
                 patch("common.network_utils.send_message"), \
                 patch("common.network_utils.broadcast"):
                DMCampaignSessionMixin.prompt_item_approval(dm_stub, player, edit_req, slot_idx=0)
            self.assertIn("Modifica", mock_ask.call_args[0][0])
            self.assertEqual(len(player.full_sheet["weapons"]), 2)
            self.assertEqual(player.full_sheet["weapons"][0]["name"], "Spada Lunga +1")
            self.assertEqual(player.full_sheet["weapons"][0]["bonus"], 1)

            # 2) Client side handle_item_approval_response with action="edit"
            char = Character(name="Aria", campaign="Test")
            char.weapons = [
                {"name": "Spada Lunga", "bonus": 0, "damage_dice": "1d8"},
                {"name": "Pugnale", "bonus": 0, "damage_dice": "1d4"},
            ]
            sent = []
            cli_stub = MagicMock()
            cli_stub.active_character = char
            cli_stub.character_manager = None
            cli_stub.stats_window = None
            cli_stub.network = MagicMock()
            cli_stub.network.send.side_effect = lambda m: sent.append(m)

            ClientNetworkHandlersMixin.handle_item_approval_response(
                cli_stub,
                {"approved": True, "item": edit_req, "slot_idx": 0},
            )
            self.assertEqual(len(char.weapons), 2)
            self.assertEqual(char.weapons[0]["name"], "Spada Lunga +1")
            self.assertEqual(char.weapons[0]["bonus"], 1)
            self.assertEqual(len(sent), 1)
            self.assertEqual(sent[0]["type"], "UPDATE_FULL_SHEET_REQUEST")
        finally:
            root.destroy()
            gc.collect()

    def test_quest_sync_and_levelup_spell_double_click_refresh(self):
        from client.client import ClientGUI
        from client.network_handlers import ClientNetworkHandlersMixin
        from client.progression_ui import LevelUpDialog

        root = tk.Tk()
        root.withdraw()
        try:
            # Quest sync in handle_game_state + fallback in open_quest_log_dialog
            host = MagicMock()
            host.master = root
            host.name = "Hero"
            host.active_character = None
            host.players_data = {}
            host.quests = []
            host.combat_active = False
            host.is_connected = True
            host._sync_open_sheet_combat_state = lambda: ClientGUI._sync_open_sheet_combat_state(host)
            host._resolve_cached_map_assets = lambda m: m
            host._maybe_request_asset_resync = lambda: None

            payload = {"players": [], "quests": [{"title": "Salva Waterdeep", "status": "active"}]}
            ClientGUI.handle_game_state(host, payload)
            self.assertEqual(len(host.quests), 1)
            self.assertEqual(host.quests[0]["title"], "Salva Waterdeep")

            host.quests = []
            with patch("components.quest_ui.QuestLogDialog") as mock_qlog:
                ClientNetworkHandlersMixin.open_quest_log_dialog(host)
            mock_qlog.assert_called_once()
            passed_data = mock_qlog.call_args[0][1]
            self.assertEqual(passed_data["quests"][0]["title"], "Salva Waterdeep")

            # LevelUpDialog._on_remove_selected_spell_double_click calls _refresh_selected_spells_ui
            lb = tk.Listbox(root)
            lb.insert(tk.END, "Dardo Incantato")
            lb.selection_set(0)
            lu_stub = MagicMock()
            lu_stub.lst_selected_spells = lb
            lu_stub.selected_spells = [{"name": "Dardo Incantato"}]
            lu_stub.btn_toggle_spell = ttk.Button(root, text="X")
            LevelUpDialog._on_remove_selected_spell_double_click(lu_stub)
            self.assertEqual(lu_stub.selected_spells, [])
            lu_stub._refresh_selected_spells_ui.assert_called_once()
        finally:
            root.destroy()
            gc.collect()

    def test_dm_tools_empty_spinboxes_single_artifact_and_speed_factor_guard(self):
        from common.game_state import GameState, Player
        from server.dm_optional_tools_ui import open_optional_rules_tools_dialog
        from client.client import ClientGUI

        root = tk.Tk()
        root.withdraw()
        try:
            gs = GameState(queue.Queue())
            p = Player("Thorin", conn=None)
            p.max_hp = 30
            p.hp = 30
            gs.add_player(p)
            dm_stub = MagicMock()
            dm_stub.master = root
            dm_stub.server = MagicMock()
            dm_stub.server.game_state = gs

            dlg = open_optional_rules_tools_dialog(dm_stub, initial_tab=0)
            dlg.withdraw()

            # Clear all tk.Spinbox/ttk.Spinbox widgets to simulate user emptying fields -> TclError without guard
            for sb in _collect_widgets(dlg, (ttk.Spinbox, tk.Spinbox)):
                sb.delete(0, tk.END)

            all_btns = _collect_widgets(dlg, (ttk.Button,))
            fear_btn = [b for b in all_btns if "Tiro Paura" in str(b.cget("text"))][0]
            cr_btn = [b for b in all_btns if str(b.cget("text")) == "Calcola CR"][0]
            mob_btn = [b for b in all_btns if "Risolvi Mob" in str(b.cget("text"))][0]
            art_btn = [b for b in all_btns if "Artefatto" in str(b.cget("text"))][0]

            fake_props = {
                "minor_beneficial": ["+1 CA"],
                "major_beneficial": ["Rigenerazione 1 PF/min"],
                "minor_detrimental": ["Occhi dorati"],
                "major_detrimental": ["Svantaggio Persuasione"],
            }
            with patch("server.dm_optional_tools.roll_artifact_properties", return_value=fake_props) as mock_roll:
                fear_btn.invoke()
                cr_btn.invoke()
                mob_btn.invoke()
                art_btn.invoke()

            mock_roll.assert_called_once()

            # ClientGUI.open_speed_factor_dialog empty Spinbox guard
            sent = []
            cli_stub = MagicMock()
            cli_stub.master = root
            cli_stub.is_connected = True
            cli_stub.network = MagicMock()
            cli_stub.network.send.side_effect = lambda m: sent.append(m)
            ClientGUI.open_speed_factor_dialog(cli_stub)
            sf_tl = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel) and w is not dlg][0]
            sf_tl.withdraw()
            for sb in _collect_widgets(sf_tl, (ttk.Spinbox, tk.Spinbox)):
                sb.delete(0, tk.END)
            decl_btn = [b for b in _collect_widgets(sf_tl, (ttk.Button,)) if "Dichiara Azione" in str(b.cget("text"))][0]
            decl_btn.invoke()
            self.assertEqual(len(sent), 1)
            self.assertEqual(sent[0]["data"]["spell_level"], 1)
        finally:
            _cleanup_toplevels(root)
            root.destroy()
            gc.collect()

    def test_handout_cancel_abort_and_command_palette_actions(self):
        from PIL import Image
        from components.command_palette import CommandPaletteDialog
        from server.dm_gui import DM_GUI

        root = tk.Tk()
        root.withdraw()
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
                tmp_png = tf.name
            try:
                Image.new("RGB", (8, 8), color=(120, 40, 40)).save(tmp_png)
                dm_stub = MagicMock()
                dm_stub.master = root
                with patch("server.dm_gui.filedialog.askopenfilename", return_value=tmp_png), \
                     patch("server.dm_gui.simpledialog.askstring", return_value=None), \
                     patch("server.dm_gui.messagebox.showinfo") as mock_info, \
                     patch("common.network_utils.broadcast") as mock_bc:
                    DM_GUI.share_image_handout(dm_stub)
                mock_bc.assert_not_called()
                mock_info.assert_not_called()
            finally:
                try:
                    os.unlink(tmp_png)
                except Exception:
                    pass

            # CommandPaletteDialog delegates toggle_ruler / toggle_fullscreen cleanly via on_action
            events = []
            canvas_mock = MagicMock()
            canvas_mock.ruler_mode = False
            pal = CommandPaletteDialog(
                root,
                map_canvas=canvas_mock,
                on_action=lambda k, p: events.append((k, p)),
            )
            pal.withdraw()
            for act_id in ("toggle_ruler", "toggle_fullscreen"):
                pal._results = [{"type": "ACTION", "icon": "🎯", "title": act_id, "summary": act_id, "payload": act_id}]
                pal.results_listbox.delete(0, tk.END)
                pal.results_listbox.insert(tk.END, act_id)
                pal.results_listbox.selection_clear(0, tk.END)
                pal.results_listbox.selection_set(0)
                pal._execute_selected()
                if not pal.winfo_exists():
                    pal = CommandPaletteDialog(
                        root,
                        map_canvas=canvas_mock,
                        on_action=lambda k, p: events.append((k, p)),
                    )
                    pal.withdraw()
            self.assertEqual(events, [("action", "toggle_ruler"), ("action", "toggle_fullscreen")])
            self.assertFalse(canvas_mock.ruler_mode)

            # DM_GUI._handle_command_palette_action supports open_sheet
            DM_GUI._handle_command_palette_action(dm_stub, "action", "open_sheet")
            dm_stub.view_player_sheet.assert_called_once()
        finally:
            _cleanup_toplevels(root)
            root.destroy()
            gc.collect()


if __name__ == "__main__":
    unittest.main()
