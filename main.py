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
    root.minsize(760, 540)
    root.resizable(True, True)
    
    # Centra la finestra del launcher direttamente sullo schermo senza finestre fantasma
    root.update_idletasks()
    win_w = 780
    win_h = 550
    pos_x = max(0, (root.winfo_screenwidth() // 2) - (win_w // 2))
    pos_y = max(0, (root.winfo_screenheight() // 2) - (win_h // 2))
    root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")

    content_container = tk.Frame(root, bg=BG_COLOR)
    content_container.pack(fill=tk.BOTH, expand=True)

    def launch_dm(campaign=None):
        for widget in root.winfo_children():
            widget.destroy()
        root.resizable(True, True)
        root.minsize(950, 650)
        from server.server import DM_GUI
        app = DM_GUI(root, initial_campaign=campaign)

    def launch_player(initial_character=None, auto_connect_ip=None):
        for widget in root.winfo_children():
            widget.destroy()
        root.resizable(True, True)
        root.minsize(950, 650)
        from client.client import ClientGUI
        app = ClientGUI(root, initial_character=initial_character, auto_connect_ip=auto_connect_ip)

    def prompt_join_game(initial_character=None):
        """Apre subito il dialogo di connessione per scegliere il server IP e il personaggio."""
        from client.character_manager import CharacterManager
        from client.login_ui import LoginDialog
        char_mgr = CharacterManager()
        login_dialog = LoginDialog(root, char_mgr, initial_character=initial_character)
        root.wait_window(login_dialog)
        if not login_dialog.result:
            return
        server_ip, char = login_dialog.result
        launch_player(initial_character=char, auto_connect_ip=server_ip)

    def show_campaign_selector_view():
        for w in content_container.winfo_children():
            w.destroy()
        root.resizable(True, True)
        root.minsize(820, 520)
        root.geometry("880x580")
        root.title(f"{_t('app_title')} • {_t('campaign_lib_title')}")
        
        from server.campaign_editor_ui import CampaignSelectorFrame
        selector = CampaignSelectorFrame(
            content_container,
            on_select_callback=lambda camp: launch_dm(campaign=camp),
            on_edit_callback=lambda camp: show_campaign_editor_view(campaign=camp),
            on_close_callback=show_launcher_menu
        )
        selector.pack(fill=tk.BOTH, expand=True)

    def show_campaign_editor_view(campaign=None):
        for w in content_container.winfo_children():
            w.destroy()
        root.resizable(True, True)
        root.minsize(980, 680)
        root.geometry("1150x760")
        c_title = campaign.name if campaign else ("Nuova Campagna" if get_language() == "it" else "New Campaign")
        root.title(f"{_t('app_title')} • {_t('campaign_editor_title', title=c_title)}")
        
        from server.campaign_editor_ui import CampaignEditorFrame
        editor = CampaignEditorFrame(
            content_container,
            campaign=campaign,
            on_save_callback=lambda c: None,
            on_close_callback=show_launcher_menu
        )
        editor.pack(fill=tk.BOTH, expand=True)

    def show_character_manager_view():
        for w in content_container.winfo_children():
            w.destroy()
        root.resizable(True, True)
        root.minsize(860, 560)
        root.geometry("900x620")
        root.title(f"{_t('app_title')} • {_t('char_manager_title')}")
        
        from client.character_manager import CharacterManager
        from client.character_manager_ui import CharacterManagerFrame
        mgr_view = CharacterManagerFrame(
            content_container,
            manager=CharacterManager(),
            on_select_callback=lambda char: prompt_join_game(initial_character=char),
            on_close_callback=show_launcher_menu,
            on_create_wizard_callback=show_character_wizard_view,
            is_embedded=True
        )
        mgr_view.pack(fill=tk.BOTH, expand=True)

    def show_character_wizard_view():
        for w in content_container.winfo_children():
            w.destroy()
        root.resizable(True, True)
        root.minsize(760, 700)
        root.geometry("820x760")
        root.title(f"{_t('app_title')} • {_t('wizard_window_title')}")
        
        from client.character_manager import CharacterManager
        from client.character_creation_wizard import CharacterCreationWizardFrame
        wizard_view = CharacterCreationWizardFrame(
            content_container,
            manager=CharacterManager(),
            on_complete_callback=lambda new_char: show_character_manager_view(),
            on_close_callback=show_launcher_menu,
            is_embedded=True
        )
        wizard_view.pack(fill=tk.BOTH, expand=True)

    def on_toggle_lang():
        toggle_language()
        show_launcher_menu()

    def show_launcher_menu():
        for w in content_container.winfo_children():
            w.destroy()

        root.resizable(True, True)
        root.minsize(760, 540)
        root.geometry("780x550")
        root.title(f"{_t('app_title')} • Launcher")

        # --- HEADER SECTION ---
        header_frame = tk.Frame(content_container, bg=BG_COLOR)
        header_frame.pack(fill=tk.X, padx=28, pady=(18, 8))

        top_bar = tk.Frame(header_frame, bg=BG_COLOR)
        top_bar.pack(fill=tk.X)

        tk.Label(
            top_bar, 
            text="⚔ D&D OmniCompanion ⚔", 
            font=("Georgia", 20, "bold"), 
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
            style="Dark.TButton"
        )
        btn_lang.pack(side=tk.RIGHT, pady=2)

        tk.Label(
            header_frame, 
            text=_t("launcher_tagline"), 
            font=("Segoe UI", 10, "italic"), 
            bg=BG_COLOR, 
            fg=TEXT_MUTED
        ).pack(anchor="w", pady=(3, 10))

        # Linea divisoria dorata sottile
        tk.Frame(header_frame, bg="#A37F2C", height=1).pack(fill=tk.X, pady=(0, 8))

        # --- SELECTION CARDS CONTAINER ---
        cards_frame = tk.Frame(content_container, bg=BG_COLOR)
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=28, pady=6)
        cards_frame.columnconfigure(0, weight=1, uniform="launcher_col")
        cards_frame.columnconfigure(1, weight=1, uniform="launcher_col")
        cards_frame.rowconfigure(0, weight=1)

        # CARD 1: DUNGEON MASTER
        dm_card = tk.Frame(cards_frame, bg=SURFACE_COLOR, highlightbackground="#A37F2C", highlightthickness=1, padx=20, pady=16)
        dm_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        dm_hdr = tk.Frame(dm_card, bg=SURFACE_COLOR)
        dm_hdr.pack(fill=tk.X, pady=(2, 6))
        dm_icon_cv = tk.Canvas(dm_hdr, width=56, height=46, bg=SURFACE_COLOR, highlightthickness=0, bd=0)
        dm_icon_cv.pack(anchor="center", pady=(0, 4))
        # Corona Araldica Vettoriale centrata al pixel (x=28)
        dm_icon_cv.create_polygon(
            10, 36, 6, 14, 18, 24, 28, 8, 38, 24, 50, 14, 46, 36,
            fill=ACCENT_GOLD, outline="#F59E0B", width=1.5
        )
        dm_icon_cv.create_rectangle(10, 37, 46, 42, fill="#B89628", outline=ACCENT_GOLD, width=1)
        for cx, cy in ((6, 12), (28, 6), (50, 12)):
            dm_icon_cv.create_oval(cx - 2.5, cy - 2.5, cx + 2.5, cy + 2.5, fill="#FFF3BF", outline=ACCENT_GOLD)
        tk.Label(dm_hdr, text=_t("launcher_dm_title"), font=("Georgia", 14, "bold"), bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack()
        tk.Label(dm_hdr, text=_t("launcher_dm_sub"), font=("Segoe UI", 8, "bold"), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(pady=(2, 0))

        tk.Frame(dm_card, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=8)

        tk.Label(
            dm_card, 
            text=_t("launcher_dm_desc"),
            font=FONT_MAIN, 
            bg=SURFACE_COLOR, 
            fg=TEXT_MUTED, 
            wraplength=280, 
            justify="center"
        ).pack(fill=tk.BOTH, expand=True, pady=6)

        btn_dm_box = tk.Frame(dm_card, bg=SURFACE_COLOR)
        btn_dm_box.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        ttk.Button(btn_dm_box, text=_t("launcher_dm_btn_camp"), command=show_campaign_selector_view, style="Gold.TButton").pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btn_dm_box, text=_t("launcher_dm_btn_edit"), command=lambda: show_campaign_editor_view(None), style="Info.TButton").pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btn_dm_box, text=_t("launcher_dm_btn_quick"), command=lambda: launch_dm(None), style="Dark.TButton").pack(fill=tk.X)

        # CARD 2: GIOCATORE
        player_card = tk.Frame(cards_frame, bg=SURFACE_COLOR, highlightbackground="#373A40", highlightthickness=1, padx=20, pady=16)
        player_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        pl_hdr = tk.Frame(player_card, bg=SURFACE_COLOR)
        pl_hdr.pack(fill=tk.X, pady=(2, 6))
        pl_icon_cv = tk.Canvas(pl_hdr, width=56, height=46, bg=SURFACE_COLOR, highlightthickness=0, bd=0)
        pl_icon_cv.pack(anchor="center", pady=(0, 4))
        # Scudo Araldico Vettoriale centrato al pixel (x=28)
        pl_icon_cv.create_polygon(
            12, 6, 28, 4, 44, 6, 44, 22, 39, 34, 28, 43, 17, 34, 12, 22,
            fill="#3B5BDB", outline="#748FFC", width=2
        )
        pl_icon_cv.create_polygon(
            16, 10, 28, 8, 40, 10, 40, 21, 36, 31, 28, 38, 20, 31, 16, 21,
            fill="#4C6EF5", outline="#91A7FF", width=1
        )
        pl_icon_cv.create_line(28, 8, 28, 38, fill="#DBE4FF", width=1.5)
        pl_icon_cv.create_line(16, 20, 40, 20, fill="#DBE4FF", width=1.5)
        tk.Label(pl_hdr, text=_t("launcher_player_title"), font=("Georgia", 14, "bold"), bg=SURFACE_COLOR, fg=TEXT_COLOR).pack()
        tk.Label(pl_hdr, text=_t("launcher_player_sub"), font=("Segoe UI", 8, "bold"), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(pady=(2, 0))

        tk.Frame(player_card, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=8)

        tk.Label(
            player_card, 
            text=_t("launcher_player_desc"),
            font=FONT_MAIN, 
            bg=SURFACE_COLOR, 
            fg=TEXT_MUTED, 
            wraplength=280, 
            justify="center"
        ).pack(fill=tk.BOTH, expand=True, pady=6)

        btn_pl_box = tk.Frame(player_card, bg=SURFACE_COLOR)
        btn_pl_box.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        ttk.Button(btn_pl_box, text=_t("launcher_player_btn_manage_chars"), command=show_character_manager_view, style="Gold.TButton").pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btn_pl_box, text=_t("launcher_player_btn_create_char"), command=show_character_wizard_view, style="Info.TButton").pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btn_pl_box, text=_t("launcher_player_btn_join"), command=prompt_join_game, style="Primary.TButton").pack(fill=tk.X)

        # --- FOOTER ---
        footer = tk.Frame(content_container, bg=BG_COLOR)
        footer.pack(fill=tk.X, padx=25, pady=(8, 12))
        tk.Label(footer, text=_t("launcher_footer"), font=("Segoe UI", 8), bg=BG_COLOR, fg="#5C5F66").pack()

    show_launcher_menu()
    root.mainloop()

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    start_app()
