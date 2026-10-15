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
from common.i18n import _t, get_language, set_language, toggle_language

def start_app():
    root = tk.Tk()
    setup_theme(root)
    apply_modern_window_style(root)
    root.configure(bg=BG_COLOR)
    root.minsize(640, 500)
    root.resizable(False, False)
    
    # Centra la finestra del launcher direttamente sullo schermo senza finestre fantasma
    root.update_idletasks()
    win_w = 640
    win_h = 500
    pos_x = max(0, (root.winfo_screenwidth() // 2) - (win_w // 2))
    pos_y = max(0, (root.winfo_screenheight() // 2) - (win_h // 2))
    root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")

    def launch_dm(campaign=None):
        for widget in root.winfo_children():
            widget.destroy()
        root.resizable(True, True)
        root.minsize(950, 650)
        from server.server import DM_GUI
        app = DM_GUI(root, initial_campaign=campaign)

    def launch_dm_campaign_picker():
        from server.campaign_editor_ui import CampaignSelectorDialog
        def on_selected(camp):
            launch_dm(campaign=camp)
        dlg = CampaignSelectorDialog(root, on_select_callback=on_selected)

    def open_campaign_builder():
        from server.campaign_editor_ui import CampaignEditorDialog
        dlg = CampaignEditorDialog(root)

    def launch_player():
        for widget in root.winfo_children():
            widget.destroy()
        root.resizable(True, True)
        root.minsize(950, 650)
        from client.client import ClientGUI
        app = ClientGUI(root)

    def on_toggle_lang():
        toggle_language()
        render_ui()

    content_container = tk.Frame(root, bg=BG_COLOR)
    content_container.pack(fill=tk.BOTH, expand=True)

    def render_ui():
        for w in content_container.winfo_children():
            w.destroy()

        root.title(f"{_t('app_title')} • Launcher")

        # --- HEADER SECTION ---
        header_frame = tk.Frame(content_container, bg=BG_COLOR)
        header_frame.pack(fill=tk.X, padx=25, pady=(15, 8))

        top_bar = tk.Frame(header_frame, bg=BG_COLOR)
        top_bar.pack(fill=tk.X)

        tk.Label(
            top_bar, 
            text="⚔ D&D OmniCompanion ⚔", 
            font=("Georgia", 18, "bold"), 
            bg=BG_COLOR, 
            fg=ACCENT_GOLD
        ).pack(side=tk.LEFT)

        # Pulsante Switch Lingua
        current_lang = get_language()
        lang_btn_text = "🌐 Italiano 🇮🇹" if current_lang == "it" else "🌐 English 🇬🇧"
        btn_lang = ttk.Button(
            top_bar, 
            text=lang_btn_text, 
            command=on_toggle_lang, 
            style="Tool.TButton"
        )
        btn_lang.pack(side=tk.RIGHT, pady=2)

        tk.Label(
            header_frame, 
            text=_t("launcher_tagline"), 
            font=("Segoe UI", 10, "italic"), 
            bg=BG_COLOR, 
            fg=TEXT_MUTED
        ).pack(anchor="w", pady=(2, 8))

        # Linea divisoria dorata sottile
        tk.Frame(header_frame, bg="#A37F2C", height=1).pack(fill=tk.X, pady=(0, 6))

        # --- SELECTION CARDS CONTAINER ---
        cards_frame = tk.Frame(content_container, bg=BG_COLOR)
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=4)
        cards_frame.columnconfigure(0, weight=1)
        cards_frame.columnconfigure(1, weight=1)

        # CARD 1: DUNGEON MASTER
        dm_card = tk.Frame(cards_frame, bg=SURFACE_COLOR, highlightbackground="#373A40", highlightthickness=1, padx=15, pady=12)
        dm_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(dm_card, text="👑", font=("Segoe UI", 26), bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(pady=(2, 4))
        tk.Label(dm_card, text=_t("launcher_dm_title"), font=FONT_HEADER, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack()
        tk.Label(
            dm_card, 
            text=_t("launcher_dm_desc"),
            font=FONT_SMALL, 
            bg=SURFACE_COLOR, 
            fg=TEXT_MUTED, 
            wraplength=220, 
            justify="center"
        ).pack(fill=tk.BOTH, expand=True, pady=6)

        btn_dm_box = tk.Frame(dm_card, bg=SURFACE_COLOR)
        btn_dm_box.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(btn_dm_box, text=_t("launcher_dm_btn_camp"), command=launch_dm_campaign_picker, style="Gold.TButton").pack(fill=tk.X, pady=(0, 4))
        ttk.Button(btn_dm_box, text=_t("launcher_dm_btn_edit"), command=open_campaign_builder).pack(fill=tk.X, pady=(0, 4))
        ttk.Button(btn_dm_box, text=_t("launcher_dm_btn_quick"), command=lambda: launch_dm(None)).pack(fill=tk.X)

        # CARD 2: GIOCATORE
        player_card = tk.Frame(cards_frame, bg=SURFACE_COLOR, highlightbackground="#373A40", highlightthickness=1, padx=15, pady=12)
        player_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        tk.Label(player_card, text="🛡️", font=("Segoe UI", 26), bg=SURFACE_COLOR, fg="#5C7CFA").pack(pady=(2, 4))
        tk.Label(player_card, text=_t("launcher_player_title"), font=FONT_HEADER, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack()
        tk.Label(
            player_card, 
            text=_t("launcher_player_desc"),
            font=FONT_SMALL, 
            bg=SURFACE_COLOR, 
            fg=TEXT_MUTED, 
            wraplength=220, 
            justify="center"
        ).pack(fill=tk.BOTH, expand=True, pady=6)

        btn_pl_box = tk.Frame(player_card, bg=SURFACE_COLOR)
        btn_pl_box.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(btn_pl_box, text=_t("launcher_player_btn_join"), command=launch_player, style="Primary.TButton").pack(fill=tk.X)

        # --- FOOTER ---
        footer = tk.Frame(content_container, bg=BG_COLOR)
        footer.pack(fill=tk.X, padx=25, pady=(8, 12))
        tk.Label(footer, text=_t("launcher_footer"), font=("Segoe UI", 8), bg=BG_COLOR, fg="#5C5F66").pack()

    render_ui()
    root.mainloop()

if __name__ == "__main__":
    start_app()
