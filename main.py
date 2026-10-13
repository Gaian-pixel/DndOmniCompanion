import tkinter as tk
from tkinter import ttk
import sys
import os

# Assicuriamoci che i moduli interni siano importabili dal path principale
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from common.theme import (
    setup_theme, apply_modern_window_style, 
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, BORDER_COLOR,
    ACCENT_GOLD, ACCENT_RED, TEXT_COLOR, TEXT_MUTED,
    FONT_TITLE, FONT_HEADER, FONT_MAIN, FONT_BOLD, FONT_SMALL
)

def start_app():
    root = tk.Tk()
    root.withdraw()
    setup_theme(root)

    dialog = tk.Toplevel(root)
    dialog.transient(root)
    dialog.grab_set()
    dialog.title("D&D OmniCompanion • Launcher")
    dialog.minsize(640, 490)
    dialog.resizable(False, False)
    apply_modern_window_style(dialog)
    dialog.configure(bg=BG_COLOR)
    
    dialog.protocol("WM_DELETE_WINDOW", lambda: root.destroy())

    # --- HEADER SECTION ---
    header_frame = tk.Frame(dialog, bg=BG_COLOR)
    header_frame.pack(fill=tk.X, padx=25, pady=(20, 10))

    tk.Label(
        header_frame, 
        text="⚔ D&D OmniCompanion ⚔", 
        font=("Georgia", 18, "bold"), 
        bg=BG_COLOR, 
        fg=ACCENT_GOLD
    ).pack()

    tk.Label(
        header_frame, 
        text="Virtual Tabletop & Campaign Manager • 5e", 
        font=("Segoe UI", 10, "italic"), 
        bg=BG_COLOR, 
        fg=TEXT_MUTED
    ).pack(pady=(2, 10))

    # Linea divisoria dorata sottile
    tk.Frame(header_frame, bg="#A37F2C", height=1).pack(fill=tk.X, pady=(0, 10))

    def launch_dm(campaign=None):
        dialog.destroy()
        from server.server import DM_GUI
        root.deiconify()
        app = DM_GUI(root, initial_campaign=campaign)

    def launch_dm_campaign_picker():
        from server.campaign_editor_ui import CampaignSelectorDialog
        def on_selected(camp):
            launch_dm(campaign=camp)
        dlg = CampaignSelectorDialog(dialog, on_select_callback=on_selected)

    def open_campaign_builder():
        from server.campaign_editor_ui import CampaignEditorDialog
        dlg = CampaignEditorDialog(dialog)

    def launch_player():
        dialog.destroy()
        from client.client import ClientGUI
        root.deiconify()
        app = ClientGUI(root)

    # --- SELECTION CARDS CONTAINER ---
    cards_frame = tk.Frame(dialog, bg=BG_COLOR)
    cards_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=5)
    cards_frame.columnconfigure(0, weight=1)
    cards_frame.columnconfigure(1, weight=1)

    # CARD 1: DUNGEON MASTER
    dm_card = tk.Frame(cards_frame, bg=SURFACE_COLOR, highlightbackground="#373A40", highlightthickness=1, padx=15, pady=15)
    dm_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

    tk.Label(dm_card, text="👑", font=("Segoe UI", 26), bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(pady=(5, 5))
    tk.Label(dm_card, text="Dungeon Master", font=FONT_HEADER, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack()
    tk.Label(
        dm_card, 
        text="Ospita la sessione con campagne preparate, mappe, incontri SRD, nebbia di guerra, audio e musica.",
        font=FONT_SMALL, 
        bg=SURFACE_COLOR, 
        fg=TEXT_MUTED, 
        wraplength=220, 
        justify="center"
    ).pack(fill=tk.BOTH, expand=True, pady=8)

    btn_dm_box = tk.Frame(dm_card, bg=SURFACE_COLOR)
    btn_dm_box.pack(fill=tk.X, side=tk.BOTTOM)
    ttk.Button(btn_dm_box, text="⚔️ Avvia con Campagna", command=launch_dm_campaign_picker, style="Gold.TButton").pack(fill=tk.X, pady=(0, 4))
    ttk.Button(btn_dm_box, text="📜 Prepara / Modifica Campagna", command=open_campaign_builder).pack(fill=tk.X, pady=(0, 4))
    ttk.Button(btn_dm_box, text="⚡ Sessione Rapida (Vuota)", command=lambda: launch_dm(None)).pack(fill=tk.X)

    # CARD 2: GIOCATORE
    player_card = tk.Frame(cards_frame, bg=SURFACE_COLOR, highlightbackground="#373A40", highlightthickness=1, padx=15, pady=15)
    player_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

    tk.Label(player_card, text="🛡️", font=("Segoe UI", 26), bg=SURFACE_COLOR, fg="#5C7CFA").pack(pady=(5, 5))
    tk.Label(player_card, text="Giocatore", font=FONT_HEADER, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack()
    tk.Label(
        player_card, 
        text="Unisciti al gruppo, controlla il tuo eroe, lancia incantesimi AoE, tira dadi e parla in voce.",
        font=FONT_SMALL, 
        bg=SURFACE_COLOR, 
        fg=TEXT_MUTED, 
        wraplength=220, 
        justify="center"
    ).pack(fill=tk.BOTH, expand=True, pady=8)

    btn_pl_box = tk.Frame(player_card, bg=SURFACE_COLOR)
    btn_pl_box.pack(fill=tk.X, side=tk.BOTTOM)
    ttk.Button(btn_pl_box, text="Unisciti a Partita", command=launch_player, style="Primary.TButton").pack(fill=tk.X)

    # --- FOOTER ---
    footer = tk.Frame(dialog, bg=BG_COLOR)
    footer.pack(fill=tk.X, padx=25, pady=(10, 15))
    tk.Label(footer, text="DndOmniCompanion • Audio Streaming, Voice UDP & Hex Grid Engine", font=("Segoe UI", 8), bg=BG_COLOR, fg="#5C5F66").pack()

    root.eval('tk::PlaceWindow . center')
    root.mainloop()

if __name__ == "__main__":
    start_app()
