"""Smoke test UI: apre ogni finestra/dialogo dell'applicazione, verifica che non sollevi
eccezioni e salva uno screenshot di ciascuna in ./ui_screenshots per la revisione visiva.

Uso:  python test_ui_smoke.py [--no-screens]
"""
import os
import sys
import time
import traceback
import tkinter as tk
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["DND_MOCK_AUDIO"] = "1"

TAKE_SCREENS = "--no-screens" not in sys.argv
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ui_screenshots")

results = []
tk_errors = []


def pump(*roots, n=5):
    for _ in range(n):
        for r in roots:
            r.update()
        time.sleep(0.03)


def snap(win, name):
    if not TAKE_SCREENS:
        return
    try:
        from PIL import ImageGrab
        win.deiconify(); win.lift(); win.attributes("-topmost", True)
        win.update(); time.sleep(0.35); win.update()
        x, y = win.winfo_rootx(), win.winfo_rooty()
        w, h = win.winfo_width(), win.winfo_height()
        os.makedirs(OUT_DIR, exist_ok=True)
        ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True).save(os.path.join(OUT_DIR, f"{name}.png"))
        win.attributes("-topmost", False)
    except Exception as e:  # lo screenshot non deve far fallire il test
        print(f"   (screenshot {name} non riuscito: {e})")


def new_toplevels(root, before):
    return [w for w in root.winfo_children() if isinstance(w, tk.Toplevel) and w not in before]


def check(name, root, action, screenshot=True):
    """Esegue action(), cattura il Toplevel aperto, fa lo screenshot e lo chiude."""
    before = set(root.winfo_children())
    n_err = len(tk_errors)
    try:
        ret = action()
        pump(root)
        if len(tk_errors) > n_err:
            raise RuntimeError(tk_errors[-1])
        wins = new_toplevels(root, before)
        target = ret if isinstance(ret, (tk.Toplevel, tk.Tk)) else (wins[-1] if wins else None)
        if screenshot and target is not None:
            snap(target, name)
        for w in wins:
            try: w.grab_release(); w.destroy()
            except tk.TclError: pass
        results.append((name, True, ""))
        print(f"OK   {name}")
    except Exception:
        results.append((name, False, traceback.format_exc()))
        print(f"FAIL {name}\n{traceback.format_exc()}")


def main():
    # Nessun messagebox/simpledialog bloccante durante il test
    patches = [
        patch("common.messagebox.messagebox.showinfo"), patch("common.messagebox.messagebox.showerror"),
        patch("common.messagebox.messagebox.showwarning"),
        patch("common.messagebox.messagebox.askyesno", return_value=False),
        patch("common.messagebox.messagebox.askokcancel", return_value=False),
        patch("tkinter.simpledialog.askstring", return_value=None),
        patch("tkinter.simpledialog.askinteger", return_value=None),
    ]
    for p in patches: p.start()

    from server.server import DM_GUI
    from client.client import ClientGUI
    from client.character_manager import Character, CharacterManager
    from client.login_ui import LoginDialog
    from client.character_sheet_ui import CharacterSheetUI
    from common.game_state import Player

    def report_callback_exception(exc, val, tb):
        tk_errors.append("".join(traceback.format_exception(exc, val, tb)))

    # ---------------- SERVER (DM) ----------------
    root_s = tk.Tk(); root_s.report_callback_exception = report_callback_exception
    root_s.minsize(1400, 800)
    dm = DM_GUI(root_s)
    for name, hp, init in [("Goblin 1", 7, 12), ("Orco", 15, 8)]:
        npc = Player(name, None, None); npc.hp = npc.max_hp = hp; npc.initiative = init
        npc.full_sheet = {"name": name, "char_class": "Mostro", "attributes": {"FOR": 12, "DES": 14}}
        dm.server.game_state.add_player(npc)
    pump(root_s, n=10)
    dm.log_to_chat("[SISTEMA] Messaggio di prova per lo screenshot.")
    check("server_main", root_s, lambda: root_s)

    def select_first():
        dm.player_listbox.selection_clear(0, tk.END); dm.player_listbox.selection_set(0)

    check("server_travel_panel", root_s, dm.open_travel_panel)
    select_first(); check("server_conditions", root_s, dm.open_conditions_dialog)
    select_first(); check("server_action", root_s, dm.open_action_dialog)
    select_first(); check("server_view_sheet", root_s, dm.view_player_sheet)
    check("server_map_editor", root_s, dm.open_map_editor)
    check("server_map_downloader", root_s, dm.open_map_downloader)
    check("server_srd_importer", root_s, dm.open_srd_importer)
    check("server_combat_toggle", root_s, dm.toggle_combat, screenshot=False)
    check("server_next_turn", root_s, dm.next_turn_gui, screenshot=False)

    # ---------------- CLIENT ----------------
    root_c = tk.Tk(); root_c.report_callback_exception = report_callback_exception
    root_c.minsize(1200, 800)
    cl = ClientGUI(root_c)
    pump(root_c)
    check("client_main_disconnected", root_c, lambda: root_c)

    char = Character("Aragorn", "Ranger")
    char.inventory_grid[0] = {"name": "Spada Lunga", "type": "Arma", "qty": 1, "desc": "Una spada."}
    char.inventory_grid[1] = {"name": "Pozione di Cura", "type": "Pozione", "qty": 3, "desc": "2d4+2"}
    cl.active_character = char; cl.name = char.name
    cl.players_data = {
        "Aragorn": {"name": "Aragorn", "hp": 20, "max_hp": 20, "initiative": 14, "position": [0, 0]},
        "Legolas": {"name": "Legolas", "hp": 18, "max_hp": 18, "initiative": 16, "position": [1, 0]},
    }
    cl.set_controls_state(tk.NORMAL)
    cl.update_player_listbox()
    cl.status_label.config(text="Stato: Connesso a 127.0.0.1", style="Success.TLabel")
    cl.log_to_chat("[Legolas]: Messaggio di prova", "Globale", "white")
    check("client_main_connected", root_c, lambda: root_c)

    check("client_travel_dialog", root_c, cl.open_travel_dialog)
    check("client_aoe_dialog", root_c, cl.open_aoe_dialog)
    check("client_action_dialog", root_c, cl.open_action_dialog)

    mgr = CharacterManager.__new__(CharacterManager)
    mgr.characters = [char, Character("Gimli", "Guerriero")]
    mgr.update_character = lambda c: None
    mgr.save_characters = lambda: None
    check("client_login_dialog", root_c, lambda: LoginDialog(root_c, mgr))
    check("client_character_sheet", root_c,
          lambda: CharacterSheetUI(root_c, char, mgr, roll_callback=lambda *a: None,
                                   trade_callback=lambda *a: None, players_list_callback=lambda: ["Legolas"]))

    def wizard():
        from client.character_creation_wizard import CharacterCreationWizard
        return CharacterCreationWizard(root_c, mgr, on_complete_callback=lambda _: None)
    check("client_creation_wizard", root_c, wizard)

    def inventory_detail():
        sheet = CharacterSheetUI(root_c, char, mgr)
        sheet.on_inventory_click(0)
        root_c.update()
        return [w for w in sheet.winfo_children() if isinstance(w, tk.Toplevel)][-1]
    check("client_inventory_item", root_c, inventory_detail)

    # ---------------- TEARDOWN ----------------
    dm.server.stop()
    for r in (root_c, root_s):
        try: r.destroy()
        except tk.TclError: pass
    for p in patches: p.stop()

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} schermate OK")
    if TAKE_SCREENS:
        print(f"Screenshot salvati in: {OUT_DIR}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

