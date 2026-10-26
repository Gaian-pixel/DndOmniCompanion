import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import queue
# client_gui.py
import tkinter as tk
from common.messagebox import messagebox
from tkinter import simpledialog, scrolledtext, ttk
import base64
from io import BytesIO
from PIL import Image, ImageTk

from common.protocol import *
from components.ui_components import HexMapCanvas, ToolTip, show_toast
from client.character_manager import CharacterManager
from client.login_ui import LoginDialog
from client.character_sheet_ui import CharacterSheetUI
from client.voice_client import VoiceClient
from common.audio_player import AudioManager
from common.i18n import (
    _t, get_language, set_language, register_language_listener, unregister_language_listener,
    get_distance_unit, set_distance_unit, register_unit_listener, unregister_unit_listener, speed_to_hexes, format_distance_hexes
)

from common.theme import (
    setup_theme, apply_modern_window_style,
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, BORDER_COLOR,
    TEXT_COLOR, TEXT_MUTED, TEXT_DARK,
    ACCENT_GOLD, ACCENT_RED, ACCENT_GREEN,
    FONT_MAIN, FONT_HEADER, FONT_BOLD, FONT_SMALL, FONT_REGULAR
)
from .network import ClientNetwork

class ClientGUI:
    def __init__(self, master, initial_character=None):
        self.master = master
        setup_theme(master)
        self.master.title("D&D Client")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.audio_manager = AudioManager()
        from common.file_utils import get_writable_dir
        self.audio_cache_dir = os.path.join(get_writable_dir(), "client_data", "audio_cache")
        os.makedirs(self.audio_cache_dir, exist_ok=True)
        self._audio_downloads = {}
        self._pending_play = None
        self._audio_muted = False
        self._saved_music_vol = 0.8
        self._saved_sfx_vol = 1.0
        self.character_manager = CharacterManager()
        self.active_character = initial_character
        self.name = initial_character.name if initial_character else None
        self.is_connected = False
        self.players_data = {}
        self.local_map_data = None
        self.game_state = None
        self.notebook = None
        self.chat_tabs = {}
        self.player_listbox = None
        self.map_canvas = None
        self.default_font = ("Georgia", 10)
        self.combat_active = False
        self.turn_index = 0
        self.round_number = 1
        self.gui_queue = queue.Queue()
        self.voice_client = None
        self.action_spent = False
        self.bonus_spent = False
        self.reaction_spent = False
        self.movement_spent_ft = 0
        def _safe_disconnect_notify():
            if hasattr(self, 'master') and self.master.winfo_exists():
                try: self.master.after(0, self.handle_disconnection)
                except Exception: pass
        self.network = ClientNetwork(self.gui_queue, _safe_disconnect_notify)
        register_language_listener(self.on_language_changed)
        register_unit_listener(self.on_unit_changed)
        self.setup_gui()
        self.refresh_offline_characters()
        if initial_character:
            self.set_active_character_from_manager(initial_character)
        self.master.after(100, self.process_queue)

    def show_toast(self, message, title=None, duration=3500, toast_type="info", icon=None):
        return show_toast(self.master, message, title=title, duration=duration, toast_type=toast_type, icon=icon)

    def switch_language(self, lang_code):
        set_language(lang_code)
        lang_name = "Italiano 🇮🇹" if lang_code == "it" else "English 🇬🇧"
        self.show_toast(_t("language_changed_toast", lang=lang_name), title=_t("language"), toast_type="success")
        self.refresh_ui_language()

    def on_language_changed(self, lang_code):
        if hasattr(self, 'master') and self.master.winfo_exists():
            self.master.after(0, self.refresh_ui_language)

    def switch_distance_unit(self, unit_code):
        set_distance_unit(unit_code)
        unit_label = _t("unit_feet") if unit_code == "ft" else _t("unit_meters")
        self.show_toast(_t("unit_changed_toast", unit=unit_label), title=_t("menu_units"), toast_type="info")
        self.on_unit_changed(unit_code)

    def on_unit_changed(self, unit_code):
        if hasattr(self, 'master') and self.master.winfo_exists():
            if hasattr(self, 'unit_var'):
                self.unit_var.set(unit_code)
            self.update_hero_summary_card()
            self.update_action_economy_ui()
            if self.map_canvas:
                self.map_canvas.redraw()

    def setup_menubar(self):
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        self.main_menubar = menubar
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=_t("menu_export_session_log"), command=self.export_session_log)
        file_menu.add_separator()
        file_menu.add_command(label=_t("menu_exit"), command=self.on_closing)
        menubar.add_cascade(label=_t("menu_file"), menu=file_menu)

        server_menu = tk.Menu(menubar, tearoff=0)
        server_menu.add_command(label=_t("menu_connect"), command=self.connect_to_server)
        server_menu.add_command(label=_t("menu_reconnect"), command=self.reconnect_to_server)
        menubar.add_cascade(label=_t("menu_server"), menu=server_menu)

        char_menu = tk.Menu(menubar, tearoff=0)
        char_menu.add_command(label=_t("menu_manage_characters"), command=self.open_character_manager_dialog)
        char_menu.add_command(label=_t("menu_create_character"), command=self.open_create_character_dialog)
        char_menu.add_command(label=_t("menu_create_manual_character"), command=self.create_manual_character)
        char_menu.add_separator()
        char_menu.add_command(label=_t("menu_active_sheet"), command=self.open_stats_dialog)
        menubar.add_cascade(label=_t("menu_character"), menu=char_menu)
        
        library_menu = tk.Menu(menubar, tearoff=0)
        library_menu.add_command(label=_t("tool_command_palette"), command=self.open_command_palette)
        library_menu.add_command(label=_t("menu_manuals"), command=self.open_manuals_dialog)
        library_menu.add_command(label=_t("menu_srd_compendium"), command=self.open_srd_compendium)
        library_menu.add_separator()
        library_menu.add_command(label=_t("menu_quest_log"), command=self.open_quest_log_dialog)
        menubar.add_cascade(label=_t("menu_library"), menu=library_menu)

        # Menu Visualizza / View
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label=_t("menu_fullscreen"), command=self.toggle_fullscreen, accelerator="F11")
        menubar.add_cascade(label=_t("menu_view"), menu=view_menu)


        # Menu Lingua / Language
        lang_menu = tk.Menu(menubar, tearoff=0)
        self.lang_var = tk.StringVar(value=get_language())
        lang_menu.add_radiobutton(label="Italiano 🇮🇹", variable=self.lang_var, value="it", command=lambda: self.switch_language("it"))
        lang_menu.add_radiobutton(label="English 🇬🇧", variable=self.lang_var, value="en", command=lambda: self.switch_language("en"))
        menubar.add_cascade(label=_t("menu_language"), menu=lang_menu)

        # Menu Unità di Misura (Piedi / Metri)
        unit_menu = tk.Menu(menubar, tearoff=0)
        self.unit_var = tk.StringVar(value=get_distance_unit())
        unit_menu.add_radiobutton(label=_t("unit_feet"), variable=self.unit_var, value="ft", command=lambda: self.switch_distance_unit("ft"))
        unit_menu.add_radiobutton(label=_t("unit_meters"), variable=self.unit_var, value="m", command=lambda: self.switch_distance_unit("m"))
        menubar.add_cascade(label=_t("menu_units"), menu=unit_menu)

    def refresh_ui_language(self):
        self.master.title(f"{_t('app_title')} • Player")
        self.setup_menubar()

        # Aggiorna tab del notebook laterale
        if hasattr(self, 'right_notebook'):
            try:
                self.right_notebook.tab(0, text=_t("tab_chat"))
                self.right_notebook.tab(1, text=_t("tab_player_controls"))
            except Exception:
                pass

        # Aggiorna tab chat
        if hasattr(self, 'lbl_party_header'):
            self.lbl_party_header.config(text=_t("party_members_header"))
        if hasattr(self, 'btn_send_chat'):
            self.btn_send_chat.config(text=_t("btn_send"))
        if hasattr(self, 'voice_status_lbl'):
            v_status = _t("voice_status_connected") if (self.voice_client and getattr(self.voice_client, "is_running", False)) else _t("voice_status_disconnected")
            self.voice_status_lbl.config(text=f"⚪ Voice: {v_status}")

        # Aggiorna controlli PG
        if hasattr(self, 'status_label'):
            self.status_label.config(text=_t("status_connected") if self.is_connected else _t("status_disconnected"))
        if hasattr(self, 'lbl_econ_hdr'):
            self.lbl_econ_hdr.config(text=_t("turn_economy"))
        if hasattr(self, 'btn_reset_econ'):
            self.btn_reset_econ.config(text=_t("turn_economy_reset"))
        if hasattr(self, 'lbl_change_char'):
            self.lbl_change_char.config(text=_t("change_active_char"))
        if hasattr(self, 'stats_button'):
            self.stats_button.config(text=_t("btn_sheet"))
        if hasattr(self, 'roll_button'):
            self.roll_button.config(text=_t("btn_roll_dice"))
        if hasattr(self, 'action_button'):
            self.action_button.config(text=_t("btn_action"))
        if hasattr(self, 'btn_short_rest'):
            self.btn_short_rest.config(text=_t("btn_short_rest"))
        if hasattr(self, 'class_features_frame'):
            self.class_features_frame.config(text=_t("lbl_class_features"))
        if hasattr(self, 'btn_second_wind'):
            self.btn_second_wind.config(text=_t("btn_second_wind"))
        if hasattr(self, 'btn_action_surge'):
            self.btn_action_surge.config(text=_t("btn_action_surge"))
        if hasattr(self, 'btn_rage'):
            self.btn_rage.config(text=_t("btn_rage"))
        if hasattr(self, 'travel_button'):
            self.travel_button.config(text=_t("btn_travel_actions"))
        if hasattr(self, 'manuals_button'):
            self.manuals_button.config(text=_t("btn_manuals"))
        if hasattr(self, 'combat_btn'):
            self.combat_btn.config(text=_t("btn_request_combat"))
        if hasattr(self, 'end_turn_btn'):
            self.end_turn_btn.config(text=_t("btn_end_turn"))
        if hasattr(self, 'btn_dash'):
            self.btn_dash.config(text=_t("btn_dash"))
        if hasattr(self, 'btn_disengage'):
            self.btn_disengage.config(text=_t("btn_disengage"))
        if hasattr(self, 'btn_dodge'):
            self.btn_dodge.config(text=_t("btn_dodge"))
        if hasattr(self, 'btn_help'):
            self.btn_help.config(text=_t("btn_help"))

        self.update_action_economy_ui()
        self.update_hero_summary_card()
        if hasattr(self, 'sheet_ui') and self.sheet_ui and getattr(self.sheet_ui, 'winfo_exists', lambda: False)():
            try:
                self.sheet_ui.refresh_ui_language()
            except Exception:
                pass

    def setup_gui(self):
        # 1. MENU BAR GLOBALE
        self.setup_menubar()
        
        # 2. LAYOUT PRINCIPALE (3 Colonne: Sinistra=Toolbar, Centro=Mappa, Destra=Notebook)
        main_frame = ttk.Frame(self.master, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=0) # Barra strumenti mappa a sinistra
        main_frame.columnconfigure(1, weight=1) # Mappa
        main_frame.columnconfigure(2, weight=0) # Pannello destro per i Tab
        main_frame.rowconfigure(0, weight=1)
        
        # --- COLONNA 0: LEFT TOOLBAR (Strumenti Mappa & Eroe Raggruppati) ---
        left_panel = tk.Frame(main_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=6)
        left_panel.grid(row=0, column=0, sticky="ns", padx=(0, 6))
        
        self.zoom_in_btn = None
        self.zoom_out_btn = None

        # Gruppo 1: Scheda Eroe & Navigazione Mappa
        self.quick_sheet_btn = ttk.Button(left_panel, text="📜", width=3, style="ToolActive.TButton", command=self.open_stats_dialog)
        self.quick_sheet_btn.pack(pady=2)
        ToolTip(self.quick_sheet_btn, "Apri / Chiudi Scheda Personaggio (Scorciatoia: C)")

        tk.Frame(left_panel, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=4)

        self.pan_btn = ttk.Button(left_panel, text="✋", width=3, style="Tool.TButton", command=self.toggle_pan_mode)
        self.pan_btn.pack(pady=2)
        ToolTip(self.pan_btn, "Sposta Mappa (Pan - Scorciatoia: Spazio / H)")

        self.measure_btn = ttk.Button(left_panel, text="📏", width=3, style="Tool.TButton", command=self.toggle_ruler_mode)
        self.measure_btn.pack(pady=2)
        ToolTip(self.measure_btn, "Righello Distanze 5e (Misura in ft/m)")

        self.center_map_btn = ttk.Button(left_panel, text="🎯", width=3, style="Tool.TButton", command=lambda: self.map_canvas and self.map_canvas.center_view())
        self.center_map_btn.pack(pady=2)
        ToolTip(self.center_map_btn, "Centra Mappa")

        tk.Frame(left_panel, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=4)

        # Gruppo 2: Area d'Effetto & Lavagna Tattica
        self.aoe_button = ttk.Button(left_panel, text="💥", width=3, style="Tool.TButton", command=self.open_aoe_dialog)
        self.aoe_button.pack(pady=2)
        ToolTip(self.aoe_button, lambda: _t("tool_aoe"))

        self.pen_btn = ttk.Button(left_panel, text="✏️", width=3, style="Tool.TButton", command=self.toggle_whiteboard_pen)
        self.pen_btn.pack(pady=2)
        ToolTip(self.pen_btn, lambda: _t("tool_pen"))

        self.clear_drawings_btn = ttk.Button(left_panel, text="🧹", width=3, style="Tool.TButton", command=self.clear_whiteboard_drawings)
        self.clear_drawings_btn.pack(pady=2)
        ToolTip(self.clear_drawings_btn, lambda: _t("tool_clear_drawings"))

        tk.Frame(left_panel, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=4)

        # Gruppo 3: Consultazione & Ricerca Rapida
        self.manuals_btn = ttk.Button(left_panel, text="📖", width=3, style="Tool.TButton", command=self.open_manuals_dialog)
        self.manuals_btn.pack(pady=2)
        ToolTip(self.manuals_btn, lambda: _t("tool_manuals"))

        self.cmd_palette_btn = ttk.Button(left_panel, text="🔍", width=3, style="Tool.TButton", command=self.open_command_palette)
        self.cmd_palette_btn.pack(pady=2)
        ToolTip(self.cmd_palette_btn, lambda: _t("tool_command_palette"))

        # Pulsante rapido Schermo Intero in fondo alla barra
        self.btn_fullscreen = ttk.Button(left_panel, text="⛶", width=3, style="Tool.TButton", command=self.toggle_fullscreen)
        self.btn_fullscreen.pack(side=tk.BOTTOM, pady=(0, 2))
        ToolTip(self.btn_fullscreen, lambda: _t("menu_fullscreen"))
        
        # --- COLONNA 1: MAPPA ---
        self.map_outer_frame = ttk.Frame(main_frame)
        self.map_outer_frame.grid(row=0, column=1, sticky="nsew", padx=4)
        map_outer_frame = self.map_outer_frame
        
        self.map_canvas = HexMapCanvas(self.map_outer_frame, bg="#121316")
        self.map_canvas.pack(fill=tk.BOTH, expand=True)

        # Overlay Centro-Schermo per la Scheda Personaggio (Mono-Finestra)
        self.center_overlay_frame = tk.Frame(self.map_outer_frame, bg=BG_COLOR, highlightbackground=ACCENT_GOLD, highlightthickness=2)
        self.stats_overlay_visible = False
        self.stats_detached_window = None
        self.stats_sheet_frame = None
        self.aoe_mode = False
        self.aoe_params = None
        self.map_canvas.set_on_click_callback(self.on_hex_click)
        self.map_canvas.on_token_drop_callback = self.on_token_drop
        self.map_canvas.set_on_ping_callback(self.on_ping_callback)
        self.map_canvas.set_on_hex_right_click_callback(self.on_hex_right_clicked)
        self.map_canvas.set_on_wall_toggle_callback(self.on_wall_toggle_callback)
        self.map_canvas.set_on_cover_toggle_callback(self.on_cover_toggle_callback)
        self.map_canvas.set_on_draw_callback(self.on_draw_request)
        
        # --- COLONNA 2: RIGHT SIDEBAR (Notebook Dark Fantasy) ---
        right_panel = ttk.Frame(main_frame, width=360)
        right_panel.grid(row=0, column=2, sticky="ns", padx=(6, 0))
        right_panel.pack_propagate(False) # Mantieni la larghezza fissa a 360
        
        self.right_notebook = ttk.Notebook(right_panel)
        self.right_notebook.pack(fill=tk.BOTH, expand=True)
        
        # --- TAB 1: CHAT ---
        chat_tab = ttk.Frame(self.right_notebook)
        self.right_notebook.add(chat_tab, text=_t("tab_chat"))
        
        self.lbl_party_header = tk.Label(chat_tab, text=_t("party_members_header"), font=FONT_BOLD, bg=BG_COLOR, fg=ACCENT_GOLD)
        self.lbl_party_header.pack(anchor="w", padx=6, pady=(6, 2))
        
        list_container = tk.Frame(chat_tab, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        list_container.pack(fill=tk.X, padx=6, pady=(0, 6))
        
        self.player_listbox = tk.Listbox(
            list_container, font=FONT_MAIN, relief="flat", bg=SURFACE_COLOR, fg=TEXT_COLOR,
            selectbackground=ACCENT_GOLD, selectforeground=TEXT_DARK, height=5, borderwidth=0
        )
        self.player_listbox.pack(fill=tk.BOTH, expand=True)
        self.player_listbox.bind("<Double-Button-1>", self.open_private_chat_from_list)
        
        self.notebook = ttk.Notebook(chat_tab)
        self.create_chat_tab("Globale")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        # Barra Tiri Rapidi 1-Click (d4, d6, d8, d10, d12, d20, d100)
        quick_dice_frame = tk.Frame(chat_tab, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=3)
        quick_dice_frame.pack(fill=tk.X, padx=6, pady=(2, 0))
        tk.Label(quick_dice_frame, text="🎲", font=FONT_SMALL, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT, padx=(2, 4))
        for die_faces in ("d4", "d6", "d8", "d10", "d12", "d20", "d100"):
            d_btn = ttk.Button(quick_dice_frame, text=die_faces, width=4, style="QuickDie.TButton")
            d_btn.pack(side=tk.LEFT, padx=1, expand=True, fill=tk.X)
            d_btn.bind("<Button-1>", lambda e, d=die_faces: self.quick_roll_die(d, e))
            if die_faces == "d20":
                ToolTip(d_btn, "Click: Tira 1d20 • Shift+Click: Vantaggio (adv) • Ctrl+Click: Svantaggio (dis)")
            else:
                ToolTip(d_btn, f"Click: Tira rapidamente 1{die_faces}")
        
        chat_cmd_frame = ttk.Frame(chat_tab)
        chat_cmd_frame.pack(fill=tk.X, padx=6, pady=(4, 6))
        self.entry = ttk.Entry(chat_cmd_frame, font=FONT_MAIN)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.entry.bind("<Return>", self.send_chat_message)
        ToolTip(self.entry, "Scrivi un messaggio, /w <nome> <testo> per sussurrare, o /roll 1d20+5")
        self.btn_send_chat = ttk.Button(chat_cmd_frame, text=_t("btn_send"), command=self.send_chat_message, style="Primary.TButton")
        self.btn_send_chat.pack(side=tk.LEFT)

        # Barra Voice Discord-like
        self.voice_controls_frame = tk.Frame(chat_tab, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, pady=4, padx=6)
        self.voice_controls_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=6, pady=(0, 4))
        self.voice_status_lbl = tk.Label(self.voice_controls_frame, text=f"⚪ Voice: {_t('voice_status_disconnected')}", bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, font=FONT_SMALL)
        self.voice_status_lbl.pack(side=tk.LEFT, padx=3)
        self.btn_audio_mute = tk.Button(self.voice_controls_frame, text=" 🔊 ", bg=SURFACE_COLOR, fg="white", activebackground=SURFACE_COLOR_ALT, relief=tk.FLAT, bd=0, command=self.toggle_audio_mute)
        self.btn_audio_mute.pack(side=tk.RIGHT, padx=2)
        ToolTip(self.btn_audio_mute, lambda: _t("tooltip_mute_audio"))
        self.btn_deafen = tk.Button(self.voice_controls_frame, text=" 🎧 ", bg=SURFACE_COLOR, fg="white", activebackground=SURFACE_COLOR_ALT, relief=tk.FLAT, bd=0, command=self.toggle_deafen)
        self.btn_deafen.pack(side=tk.RIGHT, padx=2)
        ToolTip(self.btn_deafen, lambda: _t("tooltip_deafen"))
        self.btn_mute = tk.Button(self.voice_controls_frame, text=" 🎤 ", bg=SURFACE_COLOR, fg="white", activebackground=SURFACE_COLOR_ALT, relief=tk.FLAT, bd=0, command=self.toggle_mute)
        self.btn_mute.pack(side=tk.RIGHT, padx=2)
        ToolTip(self.btn_mute, lambda: _t("tooltip_mute_mic"))
        
        # --- TAB 2: CONTROLLI PG ---
        controls_tab = ttk.Frame(self.right_notebook, padding=10)
        self.right_notebook.add(controls_tab, text=_t("tab_player_controls"))
        
        self.status_label = ttk.Label(controls_tab, text=_t("status_disconnected"), style="Danger.TLabel", font=FONT_SMALL)
        self.status_label.pack(anchor="w", pady=(0, 6))
        
        # --- HERO SUMMARY CARD ---
        hero_card = tk.Frame(controls_tab, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=8)
        hero_card.pack(fill=tk.X, pady=(0, 8))
        
        hero_top = tk.Frame(hero_card, bg=SURFACE_COLOR)
        hero_top.pack(fill=tk.X, pady=(0, 6))

        self.hero_token_canvas = tk.Canvas(hero_top, width=44, height=44, bg=SURFACE_COLOR, highlightthickness=0)
        self.hero_token_canvas.pack(side=tk.LEFT, padx=(0, 8))

        hero_text_col = tk.Frame(hero_top, bg=SURFACE_COLOR)
        hero_text_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.hero_name_lbl = tk.Label(hero_text_col, text=self.name or _t("no_character"), font=FONT_HEADER, bg=SURFACE_COLOR, fg=ACCENT_GOLD)
        self.hero_name_lbl.pack(anchor="w")
        
        self.hero_class_lbl = tk.Label(hero_text_col, text=_t("adventurer_lvl", lvl=1), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
        self.hero_class_lbl.pack(anchor="w")
        
        # Barra HP Visuale
        hp_row = tk.Frame(hero_card, bg=SURFACE_COLOR)
        hp_row.pack(fill=tk.X, pady=(2, 2))
        self.hero_hp_lbl = tk.Label(hp_row, text="HP: -- / --", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR)
        self.hero_hp_lbl.pack(anchor="w")
        
        self.hero_hp_bar_bg = tk.Frame(hero_card, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, height=12)
        self.hero_hp_bar_bg.pack(fill=tk.X, pady=(2, 6))
        self.hero_hp_bar_fill = tk.Frame(self.hero_hp_bar_bg, bg=ACCENT_GREEN, height=10)
        self.hero_hp_bar_fill.place(x=0, y=0, width=0, relwidth=0.0, relheight=1.0)
        
        # Badge Rapidi (CA, Velocità, Iniziativa)
        pill_row = tk.Frame(hero_card, bg=SURFACE_COLOR)
        pill_row.pack(fill=tk.X, pady=(4, 0))
        self.hero_ac_badge = tk.Label(pill_row, text=f"🛡️ {_t('sheet_ac_badge')}: 10", bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_SMALL, padx=5, pady=2, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.hero_ac_badge.pack(side=tk.LEFT, padx=(0, 4))
        self.hero_speed_badge = tk.Label(pill_row, text=f"👟 {_t('sheet_speed_badge')}: 30ft", bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_SMALL, padx=5, pady=2, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.hero_speed_badge.pack(side=tk.LEFT, padx=2)
        self.hero_init_badge = tk.Label(pill_row, text=f"⚡ {_t('sheet_init_badge')}: +0", bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_SMALL, padx=5, pady=2, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.hero_init_badge.pack(side=tk.LEFT, padx=2)
        
        self.hero_backpack_btn = tk.Button(
            pill_row, text="🎒", font=FONT_SMALL, relief=tk.FLAT, bd=0, padx=6, pady=2,
            bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, activebackground=BORDER_COLOR, command=self.quick_toggle_backpack
        )
        self.hero_backpack_btn.pack(side=tk.RIGHT)
        ToolTip(self.hero_backpack_btn, lambda: _t("btn_drop_backpack") if not getattr(getattr(self, "active_character", None), "backpack_dropped", False) else _t("btn_pickup_backpack"))

        self.hero_light_btn = tk.Button(
            pill_row, text="🕯️", font=FONT_SMALL, relief=tk.FLAT, bd=0, padx=6, pady=2,
            bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, activebackground=BORDER_COLOR, command=self.quick_toggle_light
        )
        self.hero_light_btn.pack(side=tk.RIGHT, padx=(0, 4))
        self.hero_light_btn.bind("<Button-3>", self.open_light_presets_menu)
        ToolTip(self.hero_light_btn, lambda: "Accendi/Spegni Torcia o Luce (Click destro per opzioni)")

        
        # --- ACTION ECONOMY TRACKER (D&D 5e) ---
        self.economy_frame = tk.Frame(controls_tab, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=6)
        self.economy_frame.pack(fill=tk.X, pady=(0, 8))
        
        econ_hdr = tk.Frame(self.economy_frame, bg=SURFACE_COLOR)
        econ_hdr.pack(fill=tk.X, pady=(0, 4))
        self.lbl_econ_hdr = tk.Label(econ_hdr, text=_t("turn_economy"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD)
        self.lbl_econ_hdr.pack(side=tk.LEFT)
        self.btn_reset_econ = tk.Label(econ_hdr, text=_t("turn_economy_reset"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED, cursor="hand2")
        self.btn_reset_econ.pack(side=tk.RIGHT)
        self.btn_reset_econ.bind("<Button-1>", lambda e: self.reset_turn_resources())
        ToolTip(self.btn_reset_econ, lambda: _t("tooltip_reset_economy"))

        # Slot Azioni (Pillole / Toggle)
        econ_badges = tk.Frame(self.economy_frame, bg=SURFACE_COLOR)
        econ_badges.pack(fill=tk.X, pady=(2, 4))

        self.btn_act_tracker = tk.Button(
            econ_badges, text=_t("btn_act"), font=FONT_SMALL, relief=tk.FLAT, bd=0, padx=4, pady=2,
            bg=ACCENT_GREEN, fg="white", activebackground=SURFACE_COLOR_ALT, command=self.toggle_action
        )
        self.btn_act_tracker.pack(side=tk.LEFT, padx=(0, 2), fill=tk.X, expand=True)
        ToolTip(self.btn_act_tracker, lambda: _t("tooltip_act"))

        self.btn_bonus_tracker = tk.Button(
            econ_badges, text=_t("btn_bonus"), font=FONT_SMALL, relief=tk.FLAT, bd=0, padx=4, pady=2,
            bg="#3B82F6", fg="white", activebackground=SURFACE_COLOR_ALT, command=self.toggle_bonus
        )
        self.btn_bonus_tracker.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ToolTip(self.btn_bonus_tracker, lambda: _t("tooltip_bonus"))

        self.btn_react_tracker = tk.Button(
            econ_badges, text=_t("btn_react"), font=FONT_SMALL, relief=tk.FLAT, bd=0, padx=4, pady=2,
            bg="#F59E0B", fg="white", activebackground=SURFACE_COLOR_ALT, command=self.toggle_reaction
        )
        self.btn_react_tracker.pack(side=tk.LEFT, padx=(2, 0), fill=tk.X, expand=True)
        ToolTip(self.btn_react_tracker, lambda: _t("tooltip_react"))

        # Tracker Movimento
        self.lbl_movement_tracker = tk.Label(
            self.economy_frame, text=_t("lbl_movement", used=0, total=30, rem=30),
            font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_COLOR
        )
        self.lbl_movement_tracker.pack(anchor="w", pady=(2, 4))

        # Bottoni Rapidi Scatto & Disimpegno
        econ_quick_actions = tk.Frame(self.economy_frame, bg=SURFACE_COLOR)
        econ_quick_actions.pack(fill=tk.X, pady=(2, 0))

        self.btn_dash = tk.Button(
            econ_quick_actions, text=_t("btn_dash"), font=FONT_SMALL, relief=tk.FLAT, bd=0,
            bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, activebackground=BORDER_COLOR, command=self.perform_dash
        )
        self.btn_dash.pack(side=tk.LEFT, padx=(0, 2), fill=tk.X, expand=True)
        ToolTip(self.btn_dash, lambda: _t("tooltip_dash"))

        self.btn_disengage = tk.Button(
            econ_quick_actions, text=_t("btn_disengage"), font=FONT_SMALL, relief=tk.FLAT, bd=0,
            bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, activebackground=BORDER_COLOR, command=self.perform_disengage
        )
        self.btn_disengage.pack(side=tk.LEFT, padx=(2, 0), fill=tk.X, expand=True)
        ToolTip(self.btn_disengage, lambda: _t("tooltip_disengage"))

        # Seconda riga: Schivata & Aiuto
        econ_quick_actions_2 = tk.Frame(self.economy_frame, bg=SURFACE_COLOR)
        econ_quick_actions_2.pack(fill=tk.X, pady=(2, 0))

        self.btn_dodge = tk.Button(
            econ_quick_actions_2, text=_t("btn_dodge"), font=FONT_SMALL, relief=tk.FLAT, bd=0,
            bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, activebackground=BORDER_COLOR, command=self.perform_dodge
        )
        self.btn_dodge.pack(side=tk.LEFT, padx=(0, 2), fill=tk.X, expand=True)
        ToolTip(self.btn_dodge, lambda: _t("tooltip_dodge"))

        self.btn_help = tk.Button(
            econ_quick_actions_2, text=_t("btn_help"), font=FONT_SMALL, relief=tk.FLAT, bd=0,
            bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, activebackground=BORDER_COLOR, command=self.perform_help
        )
        self.btn_help.pack(side=tk.LEFT, padx=(2, 0), fill=tk.X, expand=True)
        ToolTip(self.btn_help, lambda: _t("tooltip_help"))

        # Scelta Personaggio Attivo
        self.lbl_change_char = tk.Label(controls_tab, text=_t("change_active_char"), font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED)
        self.lbl_change_char.pack(anchor="w", pady=(2, 2))
        
        char_select_frame = tk.Frame(controls_tab, bg=SURFACE_COLOR)
        char_select_frame.pack(fill=tk.X, pady=(0, 6))

        self.active_character_var = tk.StringVar(value=self.name)
        self.active_character_combo = ttk.Combobox(char_select_frame, textvariable=self.active_character_var, state="readonly")
        self.active_character_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.active_character_combo.bind("<<ComboboxSelected>>", self.on_active_character_changed)

        btn_new_char = ttk.Button(char_select_frame, text="✨", width=3, style="Tool.TButton", command=self.open_create_character_dialog)
        btn_new_char.pack(side=tk.LEFT, padx=(0, 2))
        ToolTip(btn_new_char, lambda: _t("char_manager_btn_wizard"))

        btn_mgr_char = ttk.Button(char_select_frame, text="👤", width=3, style="Tool.TButton", command=self.open_character_manager_dialog)
        btn_mgr_char.pack(side=tk.LEFT)
        ToolTip(btn_mgr_char, lambda: _t("char_manager_header"))
        
        # Griglia Compatta 2x3 Azioni Eroe (Previene overflow verticale su schermi compatti)
        actions_grid = ttk.Frame(controls_tab)
        actions_grid.pack(fill=tk.X, pady=(0, 4))
        actions_grid.columnconfigure(0, weight=1)
        actions_grid.columnconfigure(1, weight=1)

        self.stats_button = ttk.Button(actions_grid, text=_t("btn_sheet"), command=self.open_stats_dialog, style='Gold.TButton')
        self.stats_button.grid(row=0, column=0, sticky="ew", padx=(0, 2), pady=2)
        
        self.roll_button = ttk.Button(actions_grid, text=_t("btn_roll_dice"), command=getattr(self, "roll_dice_dialog", lambda: None), style="Primary.TButton")
        self.roll_button.grid(row=0, column=1, sticky="ew", padx=(2, 0), pady=2)
        
        self.action_button = ttk.Button(actions_grid, text=_t("btn_action"), command=getattr(self, "open_action_dialog", lambda: None))
        self.action_button.grid(row=1, column=0, sticky="ew", padx=(0, 2), pady=2)

        self.btn_short_rest = ttk.Button(actions_grid, text=_t("btn_short_rest"), command=self.open_short_rest_dialog, style='Info.TButton')
        self.btn_short_rest.grid(row=1, column=1, sticky="ew", padx=(2, 0), pady=2)

        self.travel_button = ttk.Button(actions_grid, text=_t("btn_travel_actions"), command=getattr(self, "open_travel_dialog", lambda: None))
        self.travel_button.grid(row=2, column=0, sticky="ew", padx=(0, 2), pady=2)

        self.manuals_button = ttk.Button(actions_grid, text=_t("btn_manuals"), command=self.open_manuals_dialog)
        self.manuals_button.grid(row=2, column=1, sticky="ew", padx=(2, 0), pady=2)

        # Privilegi di Classe (Guerriero / Barbaro / ecc. - Riga Compatta 3 Colonne)
        self.class_features_frame = ttk.LabelFrame(controls_tab, text=_t("lbl_class_features"))
        self.class_features_frame.pack(fill=tk.X, pady=(2, 4))

        cf_row = tk.Frame(self.class_features_frame, bg=SURFACE_COLOR, padx=2, pady=2)
        cf_row.pack(fill=tk.X)
        self.btn_second_wind = tk.Button(
            cf_row, text=_t("btn_second_wind"), font=FONT_SMALL, relief=tk.FLAT, bd=0, pady=3,
            bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, activebackground=BORDER_COLOR, command=self.use_second_wind
        )
        self.btn_second_wind.pack(side=tk.LEFT, padx=(0, 2), fill=tk.X, expand=True)
        ToolTip(self.btn_second_wind, lambda: _t("tooltip_second_wind"))

        self.btn_action_surge = tk.Button(
            cf_row, text=_t("btn_action_surge"), font=FONT_SMALL, relief=tk.FLAT, bd=0, pady=3,
            bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, activebackground=BORDER_COLOR, command=self.use_action_surge
        )
        self.btn_action_surge.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ToolTip(self.btn_action_surge, lambda: _t("tooltip_action_surge"))

        self.btn_rage = tk.Button(
            cf_row, text=_t("btn_rage"), font=FONT_SMALL, relief=tk.FLAT, bd=0, pady=3,
            bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, activebackground=BORDER_COLOR, command=self.use_rage
        )
        self.btn_rage.pack(side=tk.LEFT, padx=(2, 0), fill=tk.X, expand=True)
        ToolTip(self.btn_rage, lambda: _t("tooltip_rage"))
        
        self.combat_btn = ttk.Button(controls_tab, text=_t("btn_request_combat"), command=lambda: getattr(self, "network", None) and self.network.send({"type": "COMBAT_TOGGLE_REQUEST", "data": {}}))
        self.combat_btn.pack(fill=tk.X, pady=2)
        
        self.end_turn_btn = ttk.Button(controls_tab, text=_t("btn_end_turn"), command=self.end_turn, style='Danger.TButton')
        
        # Hotbar al fondo del right_panel
        self.hotbar_frame = tk.Frame(self.right_notebook.master, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, pady=4, padx=4)
        self.hotbar_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=6, padx=6)
        self.hotbar_buttons = []
        for i in range(10):
            btn = ttk.Button(self.hotbar_frame, text=f"{i+1}", width=3)
            btn.grid(row=0, column=i, padx=1)
            btn.bind("<Button-1>", lambda e, idx=i: getattr(self, "on_hotbar_click")(idx))
            btn.bind("<Button-3>", lambda e, idx=i: getattr(self, "on_hotbar_right_click")(idx))
            ToolTip(btn, lambda idx=i: self._get_hotbar_tooltip(idx))
            self.hotbar_buttons.append(btn)
            key_num = str((i + 1) % 10)
            self.master.bind(f"<Alt-Key-{key_num}>", lambda e, idx=i: self.on_hotbar_click(idx))
        
        self.set_controls_state(tk.DISABLED)
        self.update_hero_summary_card()

        # Scorciatoia universale Command Palette (Ctrl+K)
        self.master.bind("<Control-k>", self.open_command_palette)
        self.master.bind("<Control-K>", self.open_command_palette)
        # Scorciatoia Schermo Intero (F11 / Esc) & Scheda PG (C)
        self.master.bind("<F11>", self.toggle_fullscreen)
        self.master.bind("<Escape>", self._on_key_escape)
        self.master.bind("<c>", self._on_key_c)
        self.master.bind("<C>", self._on_key_c)
        # Scorciatoie Navigazione Mappa (Spazio, H, P)
        self.master.bind("<KeyPress-space>", self._on_space_key_press)
        self.master.bind("<KeyRelease-space>", self._on_space_key_release)
        self.master.bind("<h>", self._on_shortcut_pan_key)
        self.master.bind("<H>", self._on_shortcut_pan_key)
        self.master.bind("<p>", self._on_shortcut_pan_key)
        self.master.bind("<P>", self._on_shortcut_pan_key)

    def open_command_palette(self, event=None):
        try:
            from components.ui_components import CommandPaletteDialog
            CommandPaletteDialog(
                self.master,
                map_canvas=self.map_canvas,
                on_action=self._handle_command_palette_action,
                is_dm=False,
                player_names=list(self.players_data.keys())
            )
        except Exception as e:
            print("Error opening CommandPaletteDialog:", e)

    def _handle_command_palette_action(self, action_type, payload):
        if action_type == "roll":
            formula = payload.strip()
            if not formula.startswith("/"):
                formula = f"/roll {formula}"
            self.send_chat_message(formula)
        elif action_type == "center_token":
            if self.map_canvas and hasattr(self.map_canvas, "center_on_token"):
                self.map_canvas.center_on_token(payload)
        elif action_type == "action":
            if payload == "open_sheet":
                self.open_stats_dialog()
            elif payload == "open_manuals":
                self.open_manuals_dialog()
            elif payload == "toggle_ruler":
                self.toggle_ruler_mode()
            elif payload == "toggle_pan":
                self.toggle_pan_mode()
            elif payload == "open_aoe":
                self.open_aoe_dialog()
            elif payload == "center_map" and self.map_canvas:
                self.map_canvas.center_view()
            elif payload == "toggle_fullscreen":
                self.toggle_fullscreen()

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not getattr(self, "is_fullscreen", False)
        self.master.attributes("-fullscreen", self.is_fullscreen)
        if hasattr(self, "btn_fullscreen"):
            self.btn_fullscreen.config(text="🗗" if self.is_fullscreen else "⛶")
        if self.is_fullscreen:
            self.show_toast(_t("toast_fullscreen_on"), title=_t("menu_fullscreen"), toast_type="info")
        else:
            self.show_toast(_t("toast_fullscreen_off"), title=_t("menu_fullscreen"), toast_type="info")

    def exit_fullscreen(self, event=None):
        if getattr(self, "is_fullscreen", False):
            self.is_fullscreen = False
            self.master.attributes("-fullscreen", False)
            if hasattr(self, "btn_fullscreen"):
                self.btn_fullscreen.config(text="⛶")
            self.show_toast(_t("toast_fullscreen_off"), title=_t("menu_fullscreen"), toast_type="info")
        elif self.map_canvas and getattr(self.map_canvas, "pan_mode", False):
            self.map_canvas.toggle_pan_mode(False)

    def toggle_pan_mode(self):
        if self.map_canvas and hasattr(self.map_canvas, "toggle_pan_mode"):
            is_active = self.map_canvas.toggle_pan_mode()
            if hasattr(self, "pan_btn") and self.pan_btn:
                self.pan_btn.configure(style="ToolActive.TButton" if is_active else "Tool.TButton")
            if hasattr(self, "show_toast"):
                if is_active:
                    self.show_toast("Modalità Navigazione Mappa attiva (Trascina con Tasto Sinistro)", title="✋ Pan Mappa", toast_type="info")
                else:
                    self.show_toast("Modalità Navigazione Mappa disattivata", title="✋ Pan Mappa", toast_type="info")
            return is_active
        return False

    def _on_space_key_press(self, event):
        focus = self.master.focus_get()
        if focus:
            try:
                cls_name = focus.winfo_class()
                if cls_name in ("Entry", "Text", "TEntry", "Combobox", "TCombobox", "Spinbox", "TSpinbox"):
                    return
            except Exception:
                pass
        if self.map_canvas and hasattr(self.map_canvas, "_on_space_press"):
            self.map_canvas._on_space_press(event)

    def _on_space_key_release(self, event):
        if self.map_canvas and hasattr(self.map_canvas, "_on_space_release"):
            self.map_canvas._on_space_release(event)

    def _on_shortcut_pan_key(self, event):
        focus = self.master.focus_get()
        if focus:
            try:
                cls_name = focus.winfo_class()
                if cls_name in ("Entry", "Text", "TEntry", "Combobox", "TCombobox", "Spinbox", "TSpinbox"):
                    return
            except Exception:
                pass
        self.toggle_pan_mode()

    def on_active_character_changed(self, event=None):
        new_active = self.active_character_var.get()
        if not new_active: return
        self.name = new_active
        if self.character_manager:
            char = self.character_manager.get_or_create(new_active)
            self.active_character = char
            self.character_manager.active_character = char
        if getattr(self, "map_canvas", None):
            self.map_canvas.player_name = new_active
            self.map_canvas.redraw()
        self.update_hero_summary_card()

    def update_hero_summary_card(self):
        if not hasattr(self, 'hero_name_lbl'): return
        char = getattr(self, 'active_character', None)
        if hasattr(self, 'hero_token_canvas'):
            from common.image_utils import render_avatar_on_canvas
            av_b64 = getattr(char, 'avatar_b64', "") if char else ""
            c_name = char.name if char else (self.name or "")
            render_avatar_on_canvas(self.hero_token_canvas, av_b64, c_name, size=44)
        pref_unit = get_distance_unit()
        default_spd_str = format_distance_hexes(6, pref_unit).replace(" ", "")
        if not char:
            self.hero_name_lbl.config(text=self.name or _t("no_character"))
            self.hero_class_lbl.config(text=_t("select_or_create_char"))
            self.hero_hp_lbl.config(text="HP: -- / --")
            self.hero_ac_badge.config(text=f"🛡️ {_t('sheet_ac_badge')}: 10")
            self.hero_speed_badge.config(text=f"👟 {_t('sheet_speed_badge')}: {default_spd_str}")
            self.hero_init_badge.config(text=f"⚡ {_t('sheet_init_badge')}: +0")
            try: self.hero_hp_bar_fill.place_forget()
            except Exception: pass
            return
        
        self.hero_name_lbl.config(text=char.name)
        cls = getattr(char, 'char_class', _t('class_adventurer')) or _t('class_adventurer')
        lvl = getattr(char, 'level', 1) or 1
        race = getattr(char, 'race', '')
        race_str = f" • {race}" if race else ""
        self.hero_class_lbl.config(text=f"{_t('char_level_prefix')} {lvl} {cls}{race_str}")
        
        hp_cur = getattr(char, 'hp_current', 0)
        hp_max = getattr(char, 'hp_max', 1) or 1
        temp_hp = getattr(char, 'temp_hp', 0)
        temp_str = f" (+{temp_hp} Temp)" if temp_hp > 0 else ""
        exh = getattr(char, 'exhaustion_level', 0)
        exh_str = f" [{_t('exhaustion_prefix')} Lv{exh}]" if exh > 0 else ""
        conds = getattr(char, 'conditions', [])
        cond_str = f"  ({', '.join(conds)})" if conds else ""
        self.hero_hp_lbl.config(text=f"HP: {hp_cur} / {hp_max}{temp_str}{exh_str}{cond_str}")
        
        ratio = max(0.0, min(1.0, hp_cur / max(1, hp_max)))
        bar_color = ACCENT_GREEN if ratio > 0.5 else ("#F59F00" if ratio > 0.25 else ACCENT_RED)
        self.hero_hp_bar_fill.config(bg=bar_color)
        self.hero_hp_bar_fill.place(x=0, y=0, width=0, relwidth=ratio, relheight=1.0)
        
        ac = getattr(char, 'ac', 10) or 10
        self.hero_ac_badge.config(text=f"🛡️ {_t('sheet_ac_badge')}: {ac}")
        speed = getattr(char, 'get_effective_speed', lambda: getattr(char, 'speed', 30))() or 30
        char_unit = getattr(char, 'speed_unit', None)
        hexes = speed_to_hexes(speed, char_unit)
        spd_display = format_distance_hexes(hexes, pref_unit).replace(" ", "")
        
        enc_status = getattr(char, 'get_encumbrance_status', lambda: {"tier": "normal", "color": "#10B981"})()
        tier = enc_status.get("tier", "normal")
        enc_tag = ""
        if tier == "encumbered":
            enc_tag = " [🟡]"
        elif tier == "heavily_encumbered":
            enc_tag = " [🔴]"
        elif tier == "overloaded":
            enc_tag = " [⛔]"

        self.hero_speed_badge.config(text=f"👟 {_t('sheet_speed_badge')}: {spd_display}{enc_tag}")
        init = getattr(char, 'initiative', 0) or 0
        init_str = f"+{init}" if init >= 0 else str(init)
        self.hero_init_badge.config(text=f"⚡ {_t('sheet_init_badge')}: {init_str}")

        if hasattr(self, 'hero_backpack_btn'):
            if getattr(char, "backpack_dropped", False):
                self.hero_backpack_btn.config(text="🎒 [A Terra]", bg="#F59E0B", fg="black")
            else:
                self.hero_backpack_btn.config(text="🎒", bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR)

        if hasattr(self, 'hero_light_btn'):
            light = getattr(char, "active_light", None)
            if light and isinstance(light, dict):
                icon = light.get("icon", "🕯️")
                rad = light.get("total_radius", 8)
                self.hero_light_btn.config(text=f"{icon} {rad}h", bg="#F59E0B", fg="black")
            else:
                self.hero_light_btn.config(text="🕯️", bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED)

        self.update_action_economy_ui()

    def quick_toggle_backpack(self):
        char = getattr(self, "active_character", None)
        if not char:
            return
        new_state = char.toggle_drop_backpack()
        if self.character_manager:
            self.character_manager.update_character(char)
            self.character_manager.save_characters()
            
        self.update_hero_summary_card()
        self.update_action_economy_ui()
        
        char_name = getattr(char, "name", self.name)
        if new_state:
            chat_msg = _t("msg_backpack_dropped", name=char_name)
            self.show_toast("🎒 Zaino sfilato a terra!\nIl carico dello zaino è escluso.", title="Zaino a Terra", toast_type="warning")
        else:
            chat_msg = _t("msg_backpack_picked_up", name=char_name)
            self.show_toast("🎒 Zaino raccolto da terra e rimesso in spalla.", title="Zaino Indossato", toast_type="success")
            
        if getattr(self, "is_connected", False):
            self.send_chat_message(chat_msg)
            from common.protocol import make_update_full_sheet_request
            try:
                self.network.send(make_update_full_sheet_request(char.to_dict()))
            except Exception:
                pass
        else:
            self.log_to_chat(chat_msg, "Globale", sender="Sistema", color="#F59E0B")

    def quick_toggle_light(self):
        char = getattr(self, "active_character", None)
        if not char:
            return
        is_active, status_text, preset = char.toggle_light()
        if self.character_manager:
            self.character_manager.update_character(char)
            self.character_manager.save_characters()
            
        self.update_hero_summary_card()
        char_name = getattr(char, "name", self.name)
        tot_r, color = char.get_light_specs()
        
        if is_active:
            name_p = preset.get("name_it", "Torcia")
            chat_msg = f"🕯️ [LUCE] {char_name} accende: {name_p} (Raggio: {tot_r} hex)!"
            self.show_toast(f"Sorgente accesa: {name_p}", title="Luce Accesa", toast_type="success")
        else:
            chat_msg = f"🕯️ [LUCE] {char_name} spegne la sorgente di luce."
            self.show_toast("Sorgente di luce spenta.", title="Luce Spenta", toast_type="info")
            
        if getattr(self, "is_connected", False):
            self.send_chat_message(chat_msg)
            from common.protocol import make_update_stats_request
            try:
                self.network.send(make_update_stats_request(
                    char.hp_current, char.hp_max, char.initiative, getattr(char, "conditions", []),
                    light_radius=tot_r, light_color=color, name=char_name
                ))
            except Exception:
                pass
        else:
            self.log_to_chat(chat_msg, "Globale", sender="Sistema", color="#FFD700")
            if hasattr(self, "map_canvas"):
                self.map_canvas.redraw()

    def open_light_presets_menu(self, event=None):
        """Menu contestuale per selezionare quale sorgente di luce usare."""
        char = getattr(self, "active_character", None)
        if not char:
            return
        menu = tk.Menu(self.master, tearoff=0)
        from client.character_manager import LIGHT_PRESETS
        is_en = (get_language() == "en")
        for key, p in LIGHT_PRESETS.items():
            name = p.get("name_en") if is_en else p.get("name_it")
            desc = p.get("desc_en") if is_en else p.get("desc_it")
            icon = p.get("icon", "🕯️")
            menu.add_command(label=f"{icon} {name} ({desc})", command=lambda k=key: self.set_light_preset(k))
        menu.add_separator()
        off_label = "🚫 Douse Light" if is_en else "🚫 Spegni Luce"
        menu.add_command(label=off_label, command=lambda: self.set_light_preset(None))
        try:
            if event:
                menu.tk_popup(event.x_root, event.y_root)
            else:
                menu.tk_popup(self.master.winfo_pointerx(), self.master.winfo_pointery())
        finally:
            menu.grab_release()

    def set_light_preset(self, preset_key):
        char = getattr(self, "active_character", None)
        if not char:
            return
        from client.character_manager import LIGHT_PRESETS
        if preset_key is None:
            char.active_light = None
        else:
            preset = LIGHT_PRESETS.get(preset_key, LIGHT_PRESETS["torch"])
            char.active_light = preset.copy()
        if self.character_manager:
            self.character_manager.update_character(char)
            self.character_manager.save_characters()
        self.update_hero_summary_card()
        char_name = getattr(char, "name", self.name)
        tot_r, color = char.get_light_specs()
        if char.active_light:
            chat_msg = f"🕯️ [LUCE] {char_name} attiva {char.active_light.get('name_it', 'Luce')} (Raggio: {tot_r} hex)!"
        else:
            chat_msg = f"🕯️ [LUCE] {char_name} spegne la sorgente di luce."
            
        if getattr(self, "is_connected", False):
            self.send_chat_message(chat_msg)
            from common.protocol import make_update_stats_request
            try:
                self.network.send(make_update_stats_request(
                    char.hp_current, char.hp_max, char.initiative, getattr(char, "conditions", []),
                    light_radius=tot_r, light_color=color, name=char_name
                ))
            except Exception:
                pass
        else:
            self.log_to_chat(chat_msg, "Globale", sender="Sistema", color="#FFD700")
            if hasattr(self, "map_canvas"):
                self.map_canvas.redraw()


    def toggle_action(self):
        self.action_spent = not self.action_spent
        self.update_action_economy_ui()

    def toggle_bonus(self):
        self.bonus_spent = not self.bonus_spent
        self.update_action_economy_ui()

    def toggle_reaction(self):
        self.reaction_spent = not self.reaction_spent
        self.update_action_economy_ui()

    def reset_turn_resources(self):
        self.action_spent = False
        self.bonus_spent = False
        self.reaction_spent = False
        self.movement_spent_ft = 0
        self.update_action_economy_ui()

    def _has_cunning_action(self) -> bool:
        """Verifica se il personaggio attivo possiede Azione Scaltra (Ladro Lv 2+), che consente Scatto/Disimpegno come Azione Bonus."""
        char = getattr(self, "active_character", None)
        if not char:
            return False
        cls_name = str(getattr(char, "char_class", "") or "").strip().lower()
        lvl = int(getattr(char, "level", 1) or 1)
        if cls_name in ("ladro", "rogue") and lvl >= 2:
            return True
        features_val = getattr(char, "features", "")
        if isinstance(features_val, list):
            features_text = " ".join(str(f) for f in features_val).lower()
        else:
            features_text = str(features_val or "").lower()
        if "azione scaltra" in features_text or "cunning action" in features_text:
            return True
        feat_list = getattr(char, "features_list", [])
        if isinstance(feat_list, list):
            for f in feat_list:
                name_f = str(f.get("name", "")).lower() if isinstance(f, dict) else str(f).lower()
                if "azione scaltra" in name_f or "cunning action" in name_f:
                    return True
        return False

    def update_action_economy_ui(self):
        if not hasattr(self, 'btn_act_tracker'):
            return

        in_combat = bool(getattr(self, "combat_active", False))
        my_turn = bool(in_combat and getattr(self, "_is_my_turn", False))
        connected = bool(getattr(self, "is_connected", False))

        # 1. Intestazione e bordo contestuale (Esplorazione vs Tuo Turno vs Turno Altrui)
        if hasattr(self, 'lbl_econ_hdr') and hasattr(self, 'economy_frame'):
            if not in_combat:
                self.lbl_econ_hdr.config(
                    text=_t("turn_economy_exploration", default="⚡ Economia Turno • 🧭 Esplorazione"),
                    fg=TEXT_MUTED
                )
                self.economy_frame.config(highlightbackground=BORDER_COLOR, highlightthickness=1)
            elif my_turn:
                self.lbl_econ_hdr.config(
                    text=_t("turn_economy_my_turn", default="⚡ Economia Turno • 🟢 TUO TURNO"),
                    fg=ACCENT_GREEN
                )
                self.economy_frame.config(highlightbackground=ACCENT_GOLD, highlightthickness=2)
            else:
                self.lbl_econ_hdr.config(
                    text=_t("turn_economy_other_turn", default="⚡ Economia Turno • ⏳ Turno Altrui"),
                    fg="#F59E0B"
                )
                self.economy_frame.config(highlightbackground=BORDER_COLOR, highlightthickness=1)

        # 2. Pillole Azione / Bonus / Reazione
        act_state = tk.NORMAL if (connected and in_combat and my_turn) else tk.DISABLED
        bonus_state = tk.NORMAL if (connected and in_combat and my_turn) else tk.DISABLED
        react_state = tk.NORMAL if (connected and in_combat) else tk.DISABLED

        if not in_combat:
            self.btn_act_tracker.config(text=f"{_t('btn_act')} (-)", bg="#2A2D32", fg="#666666", state=act_state)
            self.btn_bonus_tracker.config(text=f"{_t('btn_bonus')} (-)", bg="#2A2D32", fg="#666666", state=bonus_state)
            self.btn_react_tracker.config(text=f"{_t('btn_react')} (-)", bg="#2A2D32", fg="#666666", state=react_state)
        else:
            if self.action_spent:
                self.btn_act_tracker.config(text=f"{_t('btn_act')} (❌)", bg="#33373B", fg="#888888", state=act_state)
            else:
                self.btn_act_tracker.config(text=f"{_t('btn_act')} (✔)", bg=ACCENT_GREEN if my_turn else "#2E5A44", fg="white", state=act_state)

            if self.bonus_spent:
                self.btn_bonus_tracker.config(text=f"{_t('btn_bonus')} (❌)", bg="#33373B", fg="#888888", state=bonus_state)
            else:
                self.btn_bonus_tracker.config(text=f"{_t('btn_bonus')} (✔)", bg="#3B82F6" if my_turn else "#2B4C7E", fg="white", state=bonus_state)

            if self.reaction_spent:
                self.btn_react_tracker.config(text=f"{_t('btn_react')} (❌)", bg="#33373B", fg="#888888", state=react_state)
            else:
                self.btn_react_tracker.config(text=f"{_t('btn_react')} (✔)", bg="#F59E0B", fg="white", state=react_state)

        # 3. Velocità Base e Tracker Movimento (con calcolo effettivo Ingombro 5e)
        base_speed = 30
        char_unit = None
        if self.active_character:
            base_speed = getattr(self.active_character, 'get_effective_speed', lambda: getattr(self.active_character, 'speed', 30))() or 0
            char_unit = getattr(self.active_character, 'speed_unit', None)
        
        base_hexes = speed_to_hexes(base_speed, char_unit)
        pref_unit = get_distance_unit()

        if not in_combat:
            base_spd_str = format_distance_hexes(base_hexes, pref_unit)
            enc = getattr(self.active_character, 'get_encumbrance_status', lambda: {})() if self.active_character else {}
            enc_tag = ""
            if enc.get("tier") == "encumbered":
                enc_tag = " [🟡 Ingombrato]"
            elif enc.get("tier") == "heavily_encumbered":
                enc_tag = " [🔴 Grav. Ingombrato]"
            elif enc.get("tier") == "overloaded":
                enc_tag = " [⛔ Sovraccarico: 0]"
            if enc.get("backpack_dropped"):
                enc_tag += " (🎒 A Terra)"
                
            mov_text = _t(
                "lbl_movement_exploration",
                base=base_spd_str,
                default=f"🧭 Esplorazione: Movimento libero (Base: {base_spd_str})"
            ) + enc_tag
            if hasattr(self, 'lbl_movement_tracker'):
                self.lbl_movement_tracker.config(text=mov_text, fg=TEXT_MUTED)
        else:
            is_dashed = False
            if self.name in getattr(self, "players_data", {}):
                conds = self.players_data[self.name].get("conditions", [])
                is_dashed = "Scatto" in conds or "Dash" in conds
            elif self.active_character and hasattr(self.active_character, "conditions"):
                is_dashed = "Scatto" in getattr(self.active_character, "conditions", []) or "Dash" in getattr(self.active_character, "conditions", [])
            
            eff_hexes = base_hexes * 2 if is_dashed else base_hexes
            spent_hexes = self.movement_spent_ft // 5
            rem_hexes = max(0, eff_hexes - spent_hexes)

            if pref_unit == "m":
                def _fmt_m(h):
                    v = round(h * 1.5, 1)
                    return int(v) if v == int(v) else v
                used_val, total_val, rem_val = _fmt_m(spent_hexes), _fmt_m(eff_hexes), _fmt_m(rem_hexes)
                mov_text = _t("lbl_movement", used=used_val, total=total_val, rem=rem_val).replace(" ft", " m")
            else:
                used_val, total_val, rem_val = spent_hexes * 5, eff_hexes * 5, rem_hexes * 5
                mov_text = _t("lbl_movement", used=used_val, total=total_val, rem=rem_val)

            status_tag = f" [🏃 {_t('action_dash')}]" if is_dashed else ""
            if self.active_character:
                enc = getattr(self.active_character, 'get_encumbrance_status', lambda: {})()
                if enc.get("tier") == "encumbered":
                    status_tag += " [🟡 -10ft]"
                elif enc.get("tier") == "heavily_encumbered":
                    status_tag += " [🔴 -20ft]"
                elif enc.get("tier") == "overloaded":
                    status_tag += " [⛔ Sovraccarico: 0]"
                if enc.get("backpack_dropped"):
                    status_tag += " (🎒 A Terra)"
                    
            if hasattr(self, 'lbl_movement_tracker'):
                self.lbl_movement_tracker.config(text=mov_text + status_tag, fg=TEXT_COLOR if my_turn else TEXT_MUTED)

        # 4. Abilitazione contestuale dei pulsanti tattici e privilegi di classe
        can_std = connected and in_combat and (not self.action_spent)
        can_cunning = connected and in_combat and self._has_cunning_action() and (not self.action_spent or not self.bonus_spent)
        can_bonus = connected and in_combat and (not self.bonus_spent)

        def _cfg_tactical_btn(btn_attr, enabled):
            btn = getattr(self, btn_attr, None)
            if not btn:
                return
            if enabled:
                btn.config(state=tk.NORMAL, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR)
            else:
                btn.config(state=tk.DISABLED, bg="#25282C", fg="#666666")

        _cfg_tactical_btn("btn_dash", can_std or can_cunning)
        _cfg_tactical_btn("btn_disengage", can_std or can_cunning)
        _cfg_tactical_btn("btn_dodge", can_std)
        _cfg_tactical_btn("btn_help", can_std)

        res = getattr(self.active_character, "class_resources", {}) if self.active_character else {}
        has_sw = res.get("second_wind", True)
        has_as = res.get("action_surge", True)
        has_rage = res.get("rage_current", 2) > 0

        # Secondo Fiato può essere usato anche fuori dal combattimento per curarsi, ma in combattimento richiede l'Azione Bonus
        _cfg_tactical_btn("btn_second_wind", connected and has_sw and (not in_combat or can_bonus))
        _cfg_tactical_btn("btn_action_surge", connected and in_combat and has_as)
        _cfg_tactical_btn("btn_rage", connected and in_combat and can_bonus and has_rage)

    def prompt_death_save(self):
        char = self.active_character
        if not char: return
        self.show_toast(
            f"{char.name} è a 0 HP! È il tuo turno: esegui un Tiro Salvezza contro la Morte con /tsmorte o dalla scheda.",
            title="💀 TIRO SALVEZZA MORTE", duration=5000, toast_type="danger"
        )

    def roll_death_save(self):
        char = self.active_character
        if not char: return None
        if not hasattr(char, "death_saves") or not isinstance(char.death_saves, dict):
            char.death_saves = {"successes": 0, "failures": 0}
            
        import random
        roll = random.randint(1, 20)
        succ = char.death_saves.get("successes", 0)
        fail = char.death_saves.get("failures", 0)
        conds = getattr(char, "conditions", [])
        
        flavor = ""
        if roll == 1:
            fail += 2
            flavor = "💥 FALLIMENTO CRITICO (2 fallimenti)!"
        elif roll <= 9:
            fail += 1
            flavor = "❌ Fallimento."
        elif roll <= 19:
            succ += 1
            flavor = "✅ Successo."
        elif roll == 20:
            char.hp_current = 1
            succ = 0
            fail = 0
            if "Incosciente" in conds:
                conds.remove("Incosciente")
            flavor = "🌟 CRITICO NATURALE (20)! Ti risvegli con 1 HP!"
            
        if roll != 20:
            succ = min(3, succ)
            fail = min(3, fail)
            if fail >= 3:
                if "Morto" not in conds:
                    conds.append("Morto")
                flavor += " 💀 Sei MORTO!"
            elif succ >= 3:
                if "Stabilizzato" not in conds:
                    conds.append("Stabilizzato")
                flavor += " 🩹 Ti sei STABILIZZATO!"
                
        char.conditions = conds
        char.death_saves["successes"] = succ
        char.death_saves["failures"] = fail
        self.character_manager.save_characters()
        
        from common.protocol import make_update_stats_request
        self.network.send(make_update_stats_request(
            char.hp_current, char.hp_max, char.initiative, char.conditions
        ))
        
        ds_msg = f"🎲 [TS MORTE] {char.name} tira 1d20: {roll}. {flavor} (Successi: {succ}/3 | Fallimenti: {fail}/3)"
        self.send_chat_message(ds_msg)
        self.show_toast(f"Tiro Morte: {roll}\n{flavor}", title="Tiro Salvezza Morte", toast_type="danger" if fail > succ else "success")
        self.update_hero_summary_card()
        return roll

    def perform_dash(self):
        if not self.is_connected:
            self.show_toast("Non sei connesso al server.", toast_type="warning")
            return
        if not self.combat_active:
            self.show_toast("Puoi usare Scatto solo durante il combattimento! In esplorazione il movimento è libero.", title="🧭 Modalità Esplorazione", toast_type="warning")
            return
        used_bonus = False
        if not self.action_spent:
            self.action_spent = True
        elif self._has_cunning_action() and not self.bonus_spent:
            self.bonus_spent = True
            used_bonus = True
        else:
            self.show_toast("Hai già speso la tua Azione in questo turno!", title="⚠️ Azione Esaurita", toast_type="warning")
            return
        from common.protocol import make_dash_request
        self.network.send(make_dash_request())
        self.update_action_economy_ui()
        slot_note = " (Azione Scaltra: Azione Bonus spesa)" if used_bonus else ""
        self.show_toast(f"Azione di Scatto inviata! Velocità raddoppiata per questo turno{slot_note}.", title="🏃 Scatto", toast_type="info")

    def perform_disengage(self):
        if not self.is_connected:
            self.show_toast("Non sei connesso al server.", toast_type="warning")
            return
        if not self.combat_active:
            self.show_toast("Puoi usare Disimpegno solo durante il combattimento!", title="🧭 Modalità Esplorazione", toast_type="warning")
            return
        used_bonus = False
        if not self.action_spent:
            self.action_spent = True
        elif self._has_cunning_action() and not self.bonus_spent:
            self.bonus_spent = True
            used_bonus = True
        else:
            self.show_toast("Hai già speso la tua Azione in questo turno!", title="⚠️ Azione Esaurita", toast_type="warning")
            return
        from common.protocol import make_disengage_request
        self.network.send(make_disengage_request())
        self.update_action_economy_ui()
        slot_note = " (Azione Scaltra: Azione Bonus spesa)" if used_bonus else ""
        self.show_toast(f"Azione di Disimpegno inviata! Non provochi attacchi d'opportunità per questo turno{slot_note}.", title="💨 Disimpegno", toast_type="info")

    def perform_dodge(self):
        if not self.is_connected:
            self.show_toast("Non sei connesso al server.", toast_type="warning")
            return
        if not self.combat_active:
            self.show_toast("Puoi usare Schivata solo durante il combattimento!", title="🧭 Modalità Esplorazione", toast_type="warning")
            return
        if self.action_spent:
            self.show_toast("Hai già speso la tua Azione Standard in questo turno!", title="⚠️ Azione Esaurita", toast_type="warning")
            return
        from common.protocol import make_dodge_request
        self.network.send(make_dodge_request())
        self.action_spent = True
        self.update_action_economy_ui()
        self.show_toast("Azione di Schivata attivata! Gli attacchi contro di te avranno svantaggio e hai vantaggio ai TS su Destrezza.", title="🛡️ Schivata", toast_type="info")

    def perform_help(self):
        if not self.is_connected:
            self.show_toast("Non sei connesso al server.", toast_type="warning")
            return
        if not self.combat_active:
            self.show_toast("Puoi usare l'Azione di Aiuto tattica solo durante il combattimento!", title="🧭 Modalità Esplorazione", toast_type="warning")
            return
        if self.action_spent:
            self.show_toast("Hai già speso la tua Azione Standard in questo turno!", title="⚠️ Azione Esaurita", toast_type="warning")
            return
        self.help_targeting_mode = True
        self.show_toast("Clicca sulla mappa il token del bersaglio da distrarre per Aiutare un alleato.", title="🤝 Aiuto", toast_type="info")

    def use_second_wind(self):
        if not self.active_character:
            self.show_toast("Nessun personaggio attivo selezionato.", toast_type="warning")
            return
        if self.combat_active and self.bonus_spent:
            self.show_toast("Hai già speso la tua Azione Bonus in questo turno!", title="⚠️ Azione Bonus Esaurita", toast_type="warning")
            return
        res = getattr(self.active_character, "class_resources", {})
        if not res.get("second_wind", True):
            self.show_toast("Hai già usato Secondo Fiato! Si ricarica con un Riposo Breve o Lungo.", title="💨 Secondo Fiato", toast_type="warning")
            return
        lvl = getattr(self.active_character, "level", 1) or 1
        import random
        healed = random.randint(1, 10) + lvl
        self.active_character.hp_current = min(self.active_character.hp_max, self.active_character.hp_current + healed)
        res["second_wind"] = False
        self.active_character.class_resources = res
        if self.combat_active:
            self.bonus_spent = True
        self.character_manager.save_characters()
        self.update_hero_summary_card()
        self.update_action_economy_ui()
        if self.is_connected:
            from common.protocol import make_update_stats_request
            self.network.send(make_update_stats_request(self.active_character.hp_current, self.active_character.hp_max, self.active_character.initiative, getattr(self.active_character, "conditions", []), getattr(self.active_character, "temp_hp", 0)))
            self.send_chat_message(f"💨 {self.name} usa Secondo Fiato e recupera {healed} HP! (HP: {self.active_character.hp_current}/{self.active_character.hp_max})")
        self.show_toast(f"Secondo Fiato: recuperati {healed} HP!", title="💨 Secondo Fiato", toast_type="success")

    def use_action_surge(self):
        if not self.active_character:
            self.show_toast("Nessun personaggio attivo selezionato.", toast_type="warning")
            return
        if not self.combat_active:
            self.show_toast("Azione Furente si usa durante il proprio turno di combattimento!", title="⚡ Azione Furente", toast_type="warning")
            return
        res = getattr(self.active_character, "class_resources", {})
        if not res.get("action_surge", True):
            self.show_toast("Hai già usato Azione Furente! Si ricarica con un Riposo Breve o Lungo.", title="⚡ Azione Furente", toast_type="warning")
            return
        res["action_surge"] = False
        self.active_character.class_resources = res
        self.action_spent = False
        self.character_manager.save_characters()
        self.update_action_economy_ui()
        if self.is_connected:
            self.send_chat_message(f"⚡ {self.name} scatena Azione Furente e ottiene un'Azione Standard aggiuntiva!")
        self.show_toast("Azione Furente attivata: Azione Standard ripristinata per questo turno!", title="⚡ Azione Furente", toast_type="success")

    def use_rage(self):
        if not self.active_character:
            self.show_toast("Nessun personaggio attivo selezionato.", toast_type="warning")
            return
        if not self.combat_active:
            self.show_toast("Puoi entrare in Ira Barbarica solo durante il combattimento!", title="🩸 Ira Barbarica", toast_type="warning")
            return
        if self.bonus_spent:
            self.show_toast("Hai già speso la tua Azione Bonus in questo turno!", title="⚠️ Azione Bonus Esaurita", toast_type="warning")
            return
        res = getattr(self.active_character, "class_resources", {})
        cur_rage = res.get("rage_current", 2)
        if cur_rage <= 0:
            self.show_toast("Non hai più utilizzi di Ira disponibili per oggi! Si ricaricano con un Riposo Lungo.", title="🩸 Ira Barbarica", toast_type="warning")
            return
        res["rage_current"] = cur_rage - 1
        self.active_character.class_resources = res
        conds = getattr(self.active_character, "conditions", [])
        if "Ira" not in conds:
            conds.append("Ira")
            self.active_character.conditions = conds
        self.bonus_spent = True
        self.character_manager.save_characters()
        self.update_hero_summary_card()
        self.update_action_economy_ui()
        if self.is_connected:
            from common.protocol import make_update_stats_request
            self.network.send(make_update_stats_request(self.active_character.hp_current, self.active_character.hp_max, self.active_character.initiative, self.active_character.conditions, getattr(self.active_character, "temp_hp", 0)))
            self.send_chat_message(f"🩸 {self.name} entra in IRA! (+2 danni da mischia e resistenza a contundente, perforante e tagliente, rimaste: {cur_rage-1})")
        self.show_toast(f"Ira Barbarica attivata! (Utilizzi rimasti: {cur_rage-1})", title="🩸 Ira Barbarica", toast_type="success")

    def open_short_rest_dialog(self):
        if not self.active_character:
            self.show_toast("Nessun personaggio attivo selezionato.", toast_type="warning")
            return
        char = self.active_character
        hd_cur = getattr(char, "hit_dice_current", 0)
        hd_tot = getattr(char, "hit_dice_total", 1) or 1
        hd_type = getattr(char, "hit_dice_type", "d8")
        
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        win.title("Riposo Breve (1 Ora)")
        win.minsize(320, 240)
        from common.theme import apply_modern_window_style
        apply_modern_window_style(win)
        
        ttk.Label(win, text="☕ Riposo Breve (1 Ora)", font=("Georgia", 13, "bold"), foreground="#D4AF37").pack(pady=(12, 4))
        ttk.Label(win, text=f"HP Attuali: {char.hp_current} / {char.hp_max}").pack(pady=2)
        ttk.Label(win, text=f"Dadi Vita Disponibili: {hd_cur} / {hd_tot} ({hd_type})").pack(pady=2)
        
        con_mod = (int(char.attributes.get("COS", 10)) - 10) // 2
        sign = f"+{con_mod}" if con_mod >= 0 else str(con_mod)
        ttk.Label(win, text=f"Bonus Costituzione per dado: {sign}", font=FONT_SMALL).pack(pady=2)
        
        if hd_cur <= 0:
            ttk.Label(win, text="Non hai Dadi Vita rimasti. Effettua un Riposo Lungo per recuperarli.", foreground="#ED4245").pack(pady=10)
            ttk.Button(win, text="Chiudi", command=win.destroy).pack(pady=10)
            return
            
        spend_frame = ttk.Frame(win)
        spend_frame.pack(pady=10)
        ttk.Label(spend_frame, text="Dadi da spendere: ").pack(side=tk.LEFT)
        spend_var = tk.IntVar(value=1)
        spin = ttk.Spinbox(spend_frame, from_=1, to=hd_cur, textvariable=spend_var, width=5)
        spin.pack(side=tk.LEFT)
        
        def do_rest():
            try: n_dice = int(spend_var.get())
            except (ValueError, tk.TclError): return
            if n_dice <= 0 or n_dice > hd_cur:
                return
            recovered = char.short_rest(n_dice)
            self.character_manager.save_characters()
            self.update_hero_summary_card()
            if self.is_connected:
                from common.protocol import make_update_stats_request, make_short_rest_request
                self.network.send(make_update_stats_request(char.hp_current, char.hp_max, char.initiative, getattr(char, "conditions", []), getattr(char, "temp_hp", 0)))
                self.network.send(make_short_rest_request(n_dice, recovered))
            win.destroy()
            self.show_toast(f"Hai speso {n_dice} Dado/i Vita e recuperato {recovered} HP! Privilegi di classe ricaricati.", title="☕ Riposo Breve Completato", toast_type="success")
            
        ttk.Button(win, text="Tira Dadi & Riposa", command=do_rest, style='Primary.TButton').pack(pady=12)


    def _get_hotbar_tooltip(self, idx):
        key_num = (idx + 1) % 10
        cmd = ""
        if self.active_character and hasattr(self.active_character, "hotbar") and idx < len(self.active_character.hotbar):
            cmd = self.active_character.hotbar[idx]
        if cmd:
            return f"Slot #{idx+1} (Alt+{key_num}): {cmd}\n• Click sinistro: Esegui\n• Click destro: Modifica macro"
        return f"Slot #{idx+1} vuoto (Alt+{key_num})\n• Click destro per assegnare una formula dadi (es. 1d20+5) o comando chat"

    def quick_roll_die(self, die_faces, event=None):
        formula = f"1{die_faces}"
        reason = "Tiro Rapido"
        if die_faces == "d20" and event is not None:
            state = getattr(event, "state", 0)
            if state & 0x0001:  # Shift
                formula = "1d20 adv"
                reason = "Tiro Rapido (Vantaggio)"
            elif state & 0x0004:  # Control
                formula = "1d20 dis"
                reason = "Tiro Rapido (Svantaggio)"
        if self.is_connected:
            self.do_roll(formula, reason)
        else:
            from common.dice import roll_dice
            res = roll_dice(formula)
            self.handle_dice_roll({
                "player_name": self.name or "Giocatore (Offline)",
                "formula": formula,
                "reason": reason,
                "result": res,
            })

    def on_hotbar_right_click(self, idx):
        if not self.active_character: return
        if not hasattr(self.active_character, "hotbar") or not isinstance(self.active_character.hotbar, list):
            self.active_character.hotbar = [""] * 10
        while len(self.active_character.hotbar) < 10:
            self.active_character.hotbar.append("")
        initial_val = self.active_character.hotbar[idx] if idx < len(self.active_character.hotbar) else ""
        cmd = simpledialog.askstring("Hotbar", f"Imposta comando per lo slot {idx+1} (es: 1d20+5, oppure Ciao!)", initialvalue=initial_val)
        if cmd is not None:
            self.active_character.hotbar[idx] = cmd
            self.hotbar_buttons[idx].config(text=cmd[:10] if cmd else f"{idx+1}")
            self.character_manager.save_characters()

    def on_hotbar_click(self, idx):
        if not self.active_character or not hasattr(self.active_character, "hotbar"): return
        if not isinstance(self.active_character.hotbar, list) or idx >= len(self.active_character.hotbar): return
        cmd = str(self.active_character.hotbar[idx] or "").strip()
        if not cmd:
            self.show_toast(f"Lo slot Hotbar #{idx+1} è vuoto. Usa il click destro per configurare una macro!", title="Hotbar", toast_type="info")
            return
        import re
        clean = cmd.lower()
        if re.match(r"^(\d+)?d\d+", clean) or clean.startswith("/r ") or clean.startswith("/roll "):
            formula = re.sub(r"^/(?:roll|r)\s+", "", cmd).strip()
            self.do_roll(formula, f"Hotbar {idx+1}")
        else:
            self.send_chat_message(cmd)


    def on_ping_callback(self, clicked_hex):
        if not self.is_connected: return
        self.network.send({"type": "PING_REQUEST", "data": {"q": clicked_hex.q, "r": clicked_hex.r, "color": "red"}})

    def on_draw_request(self, points, color):
        if not self.is_connected: return
        self.network.send({"type": "DRAW_REQUEST", "data": {"points": points, "color": color}})

    def on_wall_toggle_callback(self, q, r):
        if not self.is_connected: return
        from common.protocol import make_toggle_wall_request
        self.network.send(make_toggle_wall_request(q, r))

    def on_cover_toggle_callback(self, q, r, cover_type):
        if not self.is_connected: return
        self.network.send({"type": "TOGGLE_COVER_REQUEST", "data": {"q": q, "r": r, "cover_type": cover_type}})


    def on_token_drop(self, token_name, q, r):
        if not self.is_connected:
            if self.active_character:
                self.active_character.last_position = (q, r)
                self.redraw_map_and_players()
            return
        if token_name == self.name:
            self.network.send({"type": "MOVE_REQUEST", "data": {"to": [q, r]}})

    def on_hex_right_clicked(self, event, clicked_hex, token_name):
        import tkinter as tk
        menu = tk.Menu(self.master, tearoff=0, bg="#2C2F33", fg="white")
        
        # Seleziona nella listbox per preparare l'apertura chat
        for i in range(self.player_listbox.size()):
            display_text = self.player_listbox.get(i)
            name = display_text.split(" (HP")[0].replace("? ", "").strip()
            if name == token_name:
                self.player_listbox.selection_clear(0, tk.END)
                self.player_listbox.selection_set(i)
                self.player_listbox.activate(i)
                break
                
        if self.character_manager and self.character_manager.active_character and token_name == self.character_manager.active_character.name:
            menu.add_command(label=_t("ctx_view_sheet", default="Visualizza Scheda PG"), command=self.open_stats_dialog)
            
        def _open_priv():
            self.open_private_chat_from_list(None)
            
        menu.add_command(label=_t("ctx_open_private_chat", default="Invia Messaggio Privato"), command=_open_priv)
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def on_hex_click(self, clicked_hex):
        if getattr(self, "aoe_mode", False) and getattr(self, "aoe_params", None):
            aoe_type = self.aoe_params["type"]
            size = self.aoe_params["size"]
            color = self.aoe_params["color"]
            
            player_pos = [0, 0]
            if self.name in self.players_data:
                player_pos = self.players_data[self.name].get("position", [0, 0])
            
            if aoe_type in ["cono", "linea"]:
                aoe_data = {"type": aoe_type, "origin": player_pos, "target": [clicked_hex.q, clicked_hex.r], "size": size, "color": color}
            else:
                aoe_data = {"type": aoe_type, "origin": [clicked_hex.q, clicked_hex.r], "size": size, "color": color}
                
            for k in ["req_save", "stat", "dc", "dmg", "half"]:
                if k in self.aoe_params:
                    aoe_data[k] = self.aoe_params[k]

            slot_level = str(self.aoe_params.get("slot_level", "0"))
            if slot_level and slot_level != "0" and self.active_character and hasattr(self.active_character, "spell_slots"):
                slots_info = self.active_character.spell_slots.get(slot_level)
                if slots_info and isinstance(slots_info, dict):
                    cur = slots_info.get("current", 0)
                    if cur > 0:
                        slots_info["current"] = cur - 1
                        self.character_manager.save_characters()
                        from common.protocol import make_update_full_sheet_request
                        self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
                        self.show_toast(f"Slot Incantesimo Liv. {slot_level} consumato! (Rimanenti: {cur - 1}/{slots_info.get('max', 0)})", title="✨ Slot Scalato", toast_type="info")
                    else:
                        self.show_toast(f"Attenzione: Non avevi slot di Livello {slot_level} disponibili!", title="⚠️ Slot Esauriti", toast_type="warning")
                
            from common.protocol import make_create_aoe_request
            self.network.send(make_create_aoe_request(aoe_data))
            self.aoe_mode = False
            if hasattr(self, "aoe_button"):
                self.aoe_button.configure(style="Tool.TButton")
            if getattr(self, "map_canvas", None):
                try: self.map_canvas.config(cursor="")
                except Exception: pass
            self.action_spent = True
            self.update_action_economy_ui()
            self.show_toast("L'area d'effetto è stata piazzata sulla mappa.", title="💥 AoE Piazzata", toast_type="success")
        elif getattr(self, "attack_targeting_mode", False):
            target_name = None
            for p in self.players_data.values():
                pos = p.get('position', [0,0])
                if pos == [clicked_hex.q, clicked_hex.r]:
                    target_name = p['name']
                    break
            if target_name:
                self.attack_targeting_mode = False
                params = self.attack_params
                from common.protocol import make_attack_request
                self.network.send(make_attack_request(
                    target_name, params["weapon_name"], params["hit_bonus"],
                    params["damage_formula"], params.get("damage_type", "Tagliente")
                ))
                self.action_spent = True
                self.update_action_economy_ui()
                self.show_toast(f"Attacco contro {target_name} inviato!", title="Attacco Inviato", toast_type="info")
            else:
                self.show_toast("Non c'è nessuno in questo esagono.", title="Nessun Bersaglio", toast_type="warning")
        elif getattr(self, "help_targeting_mode", False):
            target_name = None
            for p in self.players_data.values():
                pos = p.get('position', [0, 0])
                if pos == [clicked_hex.q, clicked_hex.r]:
                    target_name = p['name']
                    break
            if target_name:
                self.help_targeting_mode = False
                from common.protocol import make_help_request
                self.network.send(make_help_request(target_name))
                self.action_spent = True
                self.update_action_economy_ui()
                self.show_toast(f"Azione di Aiuto inviata contro {target_name}!", title="🤝 Aiuto", toast_type="success")
            else:
                self.show_toast("Non c'è nessuno in questo esagono.", title="Nessun Bersaglio", toast_type="warning")
        elif getattr(self, "targeting_mode", False):
            target_name = None
            for p in self.players_data.values():
                pos = p.get('position', [0,0])
                if pos == [clicked_hex.q, clicked_hex.r]:
                    target_name = p['name']
                    break
            if target_name:
                self.targeting_mode = False
                self.show_action_dialog_for_target(target_name)
            else:
                self.show_toast("Non c'è nessuno in questo esagono.", title="Nessun Bersaglio", toast_type="warning")
        else:
            doors = getattr(self, "local_map_data", {}).get("doors", []) if getattr(self, "local_map_data", None) else []
            door_found = next((d for d in doors if d.get("q") == clicked_hex.q and d.get("r") == clicked_hex.r), None)
            if door_found:
                door_st = door_found.get("state", "closed")
                if door_st == "secret":
                    self.request_move(clicked_hex)
                    return
                elif door_st == "locked":
                    self.open_locked_door_dialog(door_found, clicked_hex)
                    return
                else:
                    from common.protocol import make_toggle_door_request
                    self.network.send(make_toggle_door_request(clicked_hex.q, clicked_hex.r))
                    return

            loots = getattr(self, "local_map_data", {}).get("loots", []) if getattr(self, "local_map_data", None) else []
            loot_found = None
            for l in loots:
                if l["q"] == clicked_hex.q and l["r"] == clicked_hex.r:
                    loot_found = l
                    break
            if loot_found:
                if messagebox.askyesno("Bottino", f"C'e' un forziere qui contenente: {loot_found['qty']}x {loot_found['item']}.\nVuoi raccoglierlo?"):
                    self.network.send({"type": "TAKE_LOOT_REQUEST", "data": {"q": clicked_hex.q, "r": clicked_hex.r}})
            else:
                self.request_move(clicked_hex)

    def on_attack_action(self, weapon_name, hit_bonus, damage_formula, damage_type="Tagliente"):
        self.attack_targeting_mode = True
        self.attack_params = {
            "weapon_name": weapon_name,
            "hit_bonus": hit_bonus,
            "damage_formula": damage_formula,
            "damage_type": damage_type
        }
        self.show_toast(f"Seleziona un bersaglio sulla mappa per attaccare con {weapon_name} ({damage_type})!", title="Modalità Bersaglio", toast_type="info")



    def open_calendar_dialog(self):
        try:
            from components.calendar_ui import CalendarDialog
            win = CalendarDialog(self.master, self.game_state_obj if hasattr(self, 'game_state_obj') else type('obj', (object,), self.game_state)(), is_dm=False)
            win.grab_set()
        except ImportError as e:
            from common.messagebox import messagebox
            messagebox.showerror("Errore", f"Impossibile aprire il calendario: {e}")

    def open_quest_dialog(self):
        try:
            from components.quest_ui import QuestLogDialog
            QuestLogDialog(self.master, self.game_state, is_dm=False, network_or_server=self.network)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire il diario: {e}")

    def open_shop_dialog(self):
        try:
            from components.shop_ui import ShopDialog
            ShopDialog(self.master, self.game_state, is_dm=False, network_or_server=self.network)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire i negozi: {e}")

    def open_travel_dialog(self):
        if not self.active_character:
            self.show_toast("Nessun personaggio attivo selezionato.", toast_type="warning")
            return

        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        win.title("🧭 Diario & Modalità di Viaggio")
        win.minsize(540, 680)
        apply_modern_window_style(win)

        gs = getattr(self, "game_state", {}) or {}
        weather = gs.get("weather", "Sereno")
        pace = gs.get("travel_pace", "Normale")
        hours_today = gs.get("travel_hours_today", 0)
        terrain = gs.get("travel_terrain", "Foresta")

        # Container scrollabile per schermi a bassa risoluzione
        canvas = tk.Canvas(win, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Intestazione
        header_frame = tk.Frame(scrollable_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        header_frame.pack(fill=tk.X, padx=14, pady=(12, 8))
        tk.Label(header_frame, text="🧭 DIARIO E MODALITÀ DI VIAGGIO", font=("Georgia", 13, "bold"),
                 bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(header_frame, text="Configura l'ordine di marcia 5e, l'attività del personaggio e consuma le razioni.",
                 font=("Segoe UI", 9), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", padx=12, pady=(0, 10))

        # Card Ambiente di Viaggio
        env_frame = tk.Frame(scrollable_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1)
        env_frame.pack(fill=tk.X, padx=14, pady=6)
        tk.Label(env_frame, text="📍 STATO DELL'AMBIENTE & MARCIA", font=("Segoe UI", 10, "bold"),
                 bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(anchor="w", padx=12, pady=(8, 4))
        
        env_grid = tk.Frame(env_frame, bg=SURFACE_COLOR_ALT)
        from common.i18n import translate_weather
        weather_disp = translate_weather(weather)
        tk.Label(env_grid, text=f"⛅ Clima: {weather_disp}", font=("Segoe UI", 9), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).grid(row=0, column=0, sticky="w", padx=(0, 15), pady=2)
        tk.Label(env_grid, text=f"🌲 Terreno: {terrain}", font=("Segoe UI", 9), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).grid(row=0, column=1, sticky="w", padx=15, pady=2)
        tk.Label(env_grid, text=f"🚶 Andatura: {pace}", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).grid(row=1, column=0, sticky="w", padx=(0, 15), pady=2)
        
        hours_color = ACCENT_RED if hours_today > 8 else TEXT_COLOR
        hours_text = f"⏱️ Ore Marcia Oggi: {hours_today} / 8h"
        if hours_today > 8:
            hours_text += f" (Marcia Forzata: TS COS CD {10 + (hours_today - 8)})"
        tk.Label(env_grid, text=hours_text, font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=hours_color).grid(row=1, column=1, sticky="w", padx=15, pady=2)

        # Sezione 1: Ordine di Marcia (Marching Order)
        order_frame = tk.Frame(scrollable_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        order_frame.pack(fill=tk.X, padx=14, pady=6)
        tk.Label(order_frame, text="🛡️ ORDINE DI MARCIA (FORMAZIONE 5e)", font=("Segoe UI", 10, "bold"),
                 bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=12, pady=(8, 2))
        tk.Label(order_frame, text="Definisce chi subisce o rileva per primo imboscate e trappole lungo la marcia:",
                 font=("Segoe UI", 8), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", padx=12, pady=(0, 6))

        order_var = tk.StringVar(value=getattr(self.active_character, "marching_order", "Centro"))
        order_options = [
            ("Avanguardia", "🛡️ Avanguardia (Prima Fila)", "In testa alla formazione. Affronta per prima nemici frontali, trappole e ostacoli."),
            ("Centro", "📜 Centro (Fila Protetta)", "Al centro del gruppo. Posizione riparata ideale per cartografi, incantatori e convalescenti."),
            ("Retroguardia", "🏹 Retroguardia (Coda)", "Chiude la fila. Protegge da accerchiamenti e imboscate alle spalle.")
        ]
        
        for val, title, desc in order_options:
            rb_f = tk.Frame(order_frame, bg=SURFACE_COLOR)
            rb_f.pack(fill=tk.X, padx=12, pady=2)
            rb = ttk.Radiobutton(rb_f, text=title, variable=order_var, value=val)
            rb.pack(anchor="w")
            tk.Label(rb_f, text=f"   └ {desc}", font=("Segoe UI", 8), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w")

        # Roster Attuale della Formazione del Party
        formation_f = tk.Frame(order_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1)
        formation_f.pack(fill=tk.X, padx=12, pady=(8, 10))
        tk.Label(formation_f, text="Schieramento Attuale del Gruppo:", font=("Segoe UI", 8, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(anchor="w", padx=8, pady=(4, 2))
        
        players = gs.get("players", [])
        front_rank = [p.get("name") for p in players if p.get("marching_order") == "Avanguardia"]
        mid_rank = [p.get("name") for p in players if p.get("marching_order", "Centro") == "Centro"]
        rear_rank = [p.get("name") for p in players if p.get("marching_order") == "Retroguardia"]
        
        rank_text = f"🛡️ Avan: {', '.join(front_rank) or 'Nessuno'}  |  📜 Centro: {', '.join(mid_rank) or 'Nessuno'}  |  🏹 Retro: {', '.join(rear_rank) or 'Nessuno'}"
        tk.Label(formation_f, text=rank_text, font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).pack(anchor="w", padx=8, pady=(0, 6))

        # Sezione 2: Attività di Viaggio (Travel Role)
        role_frame = tk.Frame(scrollable_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        role_frame.pack(fill=tk.X, padx=14, pady=6)
        tk.Label(role_frame, text="⛺ ATTIVITÀ DURANTE IL VIAGGIO (5e)", font=("Segoe UI", 10, "bold"),
                 bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=12, pady=(8, 2))
        tk.Label(role_frame, text="Seleziona il compito a cui ti dedichi durante le ore di spostamento:",
                 font=("Segoe UI", 8), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", padx=12, pady=(0, 6))

        role_var = tk.StringVar(value=getattr(self.active_character, "travel_role", "Nessuna"))
        role_cards = [
            ("Navigatore", "🧭 Navigatore", "Saggezza (Sopravvivenza) vs CD Terreno per evitare che il gruppo si smarrisca. (-5 con andatura Veloce)."),
            ("Sentinella", "👁️ Sentinella / All'Erta", "Usa la Percezione Passiva per scorgere pericoli ed evitare imboscate (+5 andatura Lenta, -5 andatura Veloce)."),
            ("Cacciatore", "🏹 Cacciatore / Cercatore di Cibo", "Sopravvivenza CD 15/20 per trovare cibo e acqua lungo il tragitto (non permessa a passo Veloce)."),
            ("Cartografo", "🗺️ Cartografo", "Traccia una mappa fedele del tragitto percorso; consente di tornare indietro senza perdersi."),
            ("Furtivo", "🥷 Esploratore Furtivo", "Avanza furtivamente per sorprendere nemici o passare inosservato (richiede andatura Lenta)."),
            ("Nessuna", "☕ Nessuna Attività / Riposo", "Ti rilassi, conversi o aiuti casualmente senza assumere una responsabilità primaria.")
        ]

        for val, title, desc in role_cards:
            rf = tk.Frame(role_frame, bg=SURFACE_COLOR)
            rf.pack(fill=tk.X, padx=12, pady=2)
            rb = ttk.Radiobutton(rf, text=title, variable=role_var, value=val)
            rb.pack(anchor="w")
            tk.Label(rf, text=f"   └ {desc}", font=("Segoe UI", 8), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w")

        # Sezione 3: Sostentamento & Razioni Personali
        subsist_frame = tk.Frame(scrollable_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        subsist_frame.pack(fill=tk.X, padx=14, pady=6)
        tk.Label(subsist_frame, text="🥖 SOSTENTAMENTO & PROVVISTE NELLO ZAINO", font=("Segoe UI", 10, "bold"),
                 bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=12, pady=(8, 2))
        tk.Label(subsist_frame, text="Ogni giorno di viaggio richiede 1 Razione e 1 Otre d'Acqua per evitare lo Sfinimento.",
                 font=("Segoe UI", 8), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", padx=12, pady=(0, 6))

        def get_ration_counts():
            food, water = 0, 0
            # Grid inventory
            for it in getattr(self.active_character, "inventory_grid", []):
                if not it: continue
                n = str(it.get("name", "")).lower()
                q = int(it.get("qty", it.get("quantity", 1)) or 1)
                if "razion" in n or "cibo" in n:
                    food += q
                elif "acqua" in n or "otre" in n:
                    water += q
            # Normal inventory list
            for it in getattr(self.active_character, "inventory", []):
                if isinstance(it, dict):
                    n = str(it.get("name", "")).lower()
                    q = int(it.get("quantity", it.get("qty", 1)) or 1)
                    if "razion" in n or "cibo" in n:
                        food += q
                    elif "acqua" in n or "otre" in n:
                        water += q
            return food, water

        food_cnt, water_cnt = get_ration_counts()
        lbl_rations_status = tk.Label(subsist_frame,
            text=f"🍞 Razioni Disponibili: {food_cnt}   |   💧 Otri d'Acqua Disponibili: {water_cnt}",
            font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR, fg=ACCENT_GOLD if (food_cnt > 0 and water_cnt > 0) else ACCENT_RED)
        lbl_rations_status.pack(anchor="w", padx=12, pady=4)

        def consume_single_ration():
            char = self.active_character
            food_deducted, water_deducted = False, False

            # Check inventory_grid
            grid = getattr(char, "inventory_grid", [])
            for idx, it in enumerate(grid):
                if not it: continue
                n = str(it.get("name", "")).lower()
                q = int(it.get("qty", it.get("quantity", 1)) or 1)
                if not food_deducted and ("razion" in n or "cibo" in n) and q > 0:
                    if q - 1 <= 0:
                        grid[idx] = None
                    else:
                        if "qty" in it: it["qty"] = q - 1
                        if "quantity" in it: it["quantity"] = q - 1
                    food_deducted = True
                elif not water_deducted and ("acqua" in n or "otre" in n) and q > 0:
                    if q - 1 <= 0:
                        grid[idx] = None
                    else:
                        if "qty" in it: it["qty"] = q - 1
                        if "quantity" in it: it["quantity"] = q - 1
                    water_deducted = True

            # Check inventory
            inv = getattr(char, "inventory", [])
            if isinstance(inv, list):
                for it in inv:
                    if isinstance(it, dict):
                        n = str(it.get("name", "")).lower()
                        q = int(it.get("quantity", it.get("qty", 1)) or 1)
                        if not food_deducted and ("razion" in n or "cibo" in n) and q > 0:
                            it["quantity"] = q - 1
                            food_deducted = True
                        elif not water_deducted and ("acqua" in n or "otre" in n) and q > 0:
                            it["quantity"] = q - 1
                            water_deducted = True
                char.inventory = [i for i in inv if not isinstance(i, dict) or int(i.get("quantity", i.get("qty", 1)) or 1) > 0]

            self.character_manager.save_characters()
            if hasattr(self, "network") and self.network.connected:
                from common.protocol import make_update_full_sheet_request
                self.network.send(make_update_full_sheet_request(char.to_dict()))

            f_now, w_now = get_ration_counts()
            lbl_rations_status.config(
                text=f"🍞 Razioni Disponibili: {f_now}   |   💧 Otri d'Acqua Disponibili: {w_now}",
                fg=ACCENT_GOLD if (f_now > 0 and w_now > 0) else ACCENT_RED
            )

            if food_deducted and water_deducted:
                self.show_toast("Hai consumato 1 razione e 1 otre d'acqua per la giornata di viaggio.", title="🍞 Sostentamento", toast_type="success")
                if hasattr(self, "send_chat_message"):
                    self.send_chat_message(f"[VIAGGIO] {char.name} ha consumato la razione e l'acqua giornaliera.")
            elif food_deducted:
                self.show_toast("Hai consumato 1 razione, ma non avevi acqua nello zaino!", title="⚠️ Razioni", toast_type="warning")
            elif water_deducted:
                self.show_toast("Hai bevuto 1 otre d'acqua, ma non avevi razioni di cibo!", title="⚠️ Razioni", toast_type="warning")
            else:
                self.show_toast("Non hai né razioni di cibo né acqua nello zaino!", title="❌ Scorte Esaurite", toast_type="danger")

        btn_consume = ttk.Button(subsist_frame, text="🥖 Consuma Razione e Acqua Giornaliera", command=consume_single_ration, style="Info.TButton")
        btn_consume.pack(anchor="w", padx=12, pady=(4, 10))

        # Barra dei Bottoni Inferiore
        btn_bar = tk.Frame(scrollable_frame, bg=BG_COLOR)
        btn_bar.pack(fill=tk.X, padx=14, pady=16)

        def submit():
            chosen_role = role_var.get()
            chosen_order = order_var.get()
            self.active_character.travel_role = chosen_role
            self.active_character.marching_order = chosen_order
            self.character_manager.save_characters()
            
            if hasattr(self, "network") and self.network.connected:
                from common.protocol import make_set_travel_role_request, make_update_full_sheet_request
                self.network.send(make_set_travel_role_request(chosen_role, chosen_order))
                self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))

            self.show_toast(f"Ordine [{chosen_order}] e Ruolo '{chosen_role}' salvati!", title="🧭 Viaggio Aggiornato", toast_type="success")
            win.destroy()

        ttk.Button(btn_bar, text="💾 Salva & Notifica Master", command=submit, style="Success.TButton").pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_bar, text="Annulla", command=win.destroy).pack(side=tk.RIGHT, padx=4)

    def open_manuals_dialog(self, initial_query=""):
        try:
            from client.manuals_ui import ManualsDialog
            def on_share(text):
                if hasattr(self, "send_chat_message"):
                    self.send_chat_message(text)
            ManualsDialog(self.master, share_callback=on_share, initial_query=initial_query)
        except Exception as e:
            from common.messagebox import messagebox
            messagebox.showerror("Errore", f"Impossibile aprire i manuali: {e}")

    def toggle_ruler_mode(self):
        active = self.map_canvas.toggle_ruler_mode()
        style = "ToolActive.TButton" if active else "Tool.TButton"
        if hasattr(self, 'measure_btn') and self.measure_btn:
            self.measure_btn.configure(style=style)
        msg = "Righello attivato: clicca due punti sulla mappa per misurare la distanza." if active else "Righello disattivato."
        self.show_toast(msg, title="📏 Righello", toast_type="info" if active else "secondary")
        return active

    def open_locked_door_dialog(self, door, clicked_hex):
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        door_name = door.get("name", "Porta")
        win.title(f"Interazione: {door_name} (Serrata)")
        win.minsize(460, 520)
        from common.theme import apply_modern_window_style
        apply_modern_window_style(win)

        hdr_f = tk.Frame(win, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        hdr_f.pack(fill=tk.X, padx=12, pady=(12, 6))
        tk.Label(hdr_f, text=f"🔒 {door_name} (Coordinate: {clicked_hex.q}, {clicked_hex.r})", font=("Segoe UI", 12, "bold"), bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(hdr_f, text="La serratura è bloccata. Scegli come tentare di aprirla (Regole D&D 5e):", font=("Segoe UI", 9), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", padx=10, pady=(0, 8))

        char = getattr(self, "active_character", None)
        dex_mod = 0
        str_mod = 0
        pb = 2
        has_tools = False
        tools_prof = False
        tools_expertise = False
        ath_prof = False
        ath_expertise = False
        slot2_count = 0
        keys_in_bag = []

        if char:
            attrs = getattr(char, "attributes", {})
            dex_val = attrs.get("DES", attrs.get("DEX", 10))
            try: dex_mod = (int(dex_val) - 10) // 2
            except Exception: dex_mod = 0

            str_val = attrs.get("FOR", attrs.get("STR", 10))
            try: str_mod = (int(str_val) - 10) // 2
            except Exception: str_mod = 0

            lvl = getattr(char, "level", 1) or 1
            pb = getattr(char, "proficiency_bonus", None) or (2 + max(0, (int(lvl) - 1) // 4))

            inv_items = (getattr(char, "inventory_grid", []) or []) + (getattr(char, "inventory", []) or [])
            for it in inv_items:
                if it and isinstance(it, dict):
                    iname = str(it.get("name", "")).lower()
                    if any(k in iname for k in ["arnesi da scasso", "thieves' tools", "attrezzi da scasso", "lockpick", "arnesi"]):
                        has_tools = True
                    if any(k in iname for k in ["chiave", "key"]):
                        keys_in_bag.append(it.get("name"))

            c_cls = str(getattr(char, "char_class", "")).lower()
            if any(k in c_cls for k in ["ladro", "rogue"]):
                tools_prof = True
                has_tools = True
                if int(lvl) >= 1:
                    feats = str(getattr(char, "features", "")).lower()
                    if "maestria" in feats or "expertise" in feats or "scasso" in feats:
                        tools_expertise = True

            skills = getattr(char, "skills", {}) or {}
            sk_tools = skills.get("Arnesi da Scasso", skills.get("Thieves' Tools", 0))
            if sk_tools == 2:
                tools_expertise = True
                tools_prof = True
            elif sk_tools == 1:
                tools_prof = True

            ath = skills.get("Atletica", skills.get("Athletics", 0))
            if ath == 2:
                ath_expertise = True
            elif ath == 1:
                ath_prof = True

            slots = getattr(char, "spell_slots", {}) or {}
            if "2" in slots and isinstance(slots["2"], dict):
                slot2_count = slots["2"].get("current", 0)

        content_f = tk.Frame(win, bg=BG_COLOR)
        content_f.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        # 1. Card Scasso (Arnesi da Scasso)
        c1 = tk.Frame(content_f, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        c1.pack(fill=tk.X, pady=4)
        c1_top = tk.Frame(c1, bg=SURFACE_COLOR)
        c1_top.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(c1_top, text="🗝️ Scassina Serratura (Destrezza + Arnesi)", font=("Segoe UI", 10, "bold"), bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        
        lock_bonus = dex_mod + (2 * pb if tools_expertise else (pb if tools_prof else 0))
        bonus_str = f"+{lock_bonus}" if lock_bonus >= 0 else str(lock_bonus)
        detail_prof = "Maestria (+{})".format(2*pb) if tools_expertise else ("Competente (+{})".format(pb) if tools_prof else "Non competente")
        tk.Label(c1_top, text=f"Bonus: {bonus_str}", font=("Segoe UI", 10, "bold"), bg=SURFACE_COLOR, fg="#10B981").pack(side=tk.RIGHT)

        c1_sub = tk.Frame(c1, bg=SURFACE_COLOR)
        c1_sub.pack(fill=tk.X, padx=10, pady=(0, 6))
        tools_status = "✔️ Arnesi presenti" if has_tools else "⚠️ Nessun arnese rilevato"
        tk.Label(c1_sub, text=f"{tools_status} • DES ({'+' if dex_mod>=0 else ''}{dex_mod}) • {detail_prof}", font=("Segoe UI", 8), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT)

        def do_lockpick():
            from common.protocol import make_toggle_door_request
            self.network.send(make_toggle_door_request(clicked_hex.q, clicked_hex.r, method="lockpick"))
            win.destroy()

        ttk.Button(c1_sub, text="Tenta lo Scasso", command=do_lockpick, style='Success.TButton').pack(side=tk.RIGHT, padx=4)

        # 2. Card Sfondare (Forza / Atletica)
        c2 = tk.Frame(content_f, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        c2.pack(fill=tk.X, pady=4)
        c2_top = tk.Frame(c2, bg=SURFACE_COLOR)
        c2_top.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(c2_top, text="🔨 Sfonda la Porta (Forza / Atletica)", font=("Segoe UI", 10, "bold"), bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)

        break_bonus = str_mod + (2 * pb if ath_expertise else (pb if ath_prof else 0))
        b_bonus_str = f"+{break_bonus}" if break_bonus >= 0 else str(break_bonus)
        ath_detail = "Atletica Maestria" if ath_expertise else ("Atletica Competente" if ath_prof else "Solo Forza")
        tk.Label(c2_top, text=f"Bonus: {b_bonus_str}", font=("Segoe UI", 10, "bold"), bg=SURFACE_COLOR, fg="#F59E0B").pack(side=tk.RIGHT)

        c2_sub = tk.Frame(c2, bg=SURFACE_COLOR)
        c2_sub.pack(fill=tk.X, padx=10, pady=(0, 6))
        tk.Label(c2_sub, text=f"📢 Causa forte boato! • FOR ({'+' if str_mod>=0 else ''}{str_mod}) • {ath_detail}", font=("Segoe UI", 8), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT)

        def do_break():
            from common.protocol import make_toggle_door_request
            self.network.send(make_toggle_door_request(clicked_hex.q, clicked_hex.r, method="break"))
            win.destroy()

        ttk.Button(c2_sub, text="Sfonda Porta", command=do_break, style='Warning.TButton').pack(side=tk.RIGHT, padx=4)

        # 3. Card Incantesimo Scassinare (Knock)
        c3 = tk.Frame(content_f, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        c3.pack(fill=tk.X, pady=4)
        c3_top = tk.Frame(c3, bg=SURFACE_COLOR)
        c3_top.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(c3_top, text="🪄 Incantesimo Scassinare (Knock - Liv 2)", font=("Segoe UI", 10, "bold"), bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        slot_lbl_color = "#3B82F6" if slot2_count > 0 else TEXT_MUTED
        tk.Label(c3_top, text=f"Slot 2°: {slot2_count}", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR, fg=slot_lbl_color).pack(side=tk.RIGHT)

        c3_sub = tk.Frame(c3, bg=SURFACE_COLOR)
        c3_sub.pack(fill=tk.X, padx=10, pady=(0, 6))
        tk.Label(c3_sub, text="🔔 Apre all'istante • Echeggia fino a 90 metri (300 ft)", font=("Segoe UI", 8), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT)

        def do_knock():
            from common.protocol import make_toggle_door_request
            self.network.send(make_toggle_door_request(clicked_hex.q, clicked_hex.r, method="knock"))
            win.destroy()

        knock_btn = ttk.Button(c3_sub, text="Lancia Knock", command=do_knock, style='Primary.TButton')
        knock_btn.pack(side=tk.RIGHT, padx=4)
        if slot2_count <= 0 and not any("scassinare" in str(sp.get("name", "")).lower() or "knock" in str(sp.get("name", "")).lower() for sp in (getattr(char, "spellbook", []) or [])):
            knock_btn.config(state="disabled")

        # 4. Card Usa Chiave
        c4 = tk.Frame(content_f, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        c4.pack(fill=tk.X, pady=4)
        c4_top = tk.Frame(c4, bg=SURFACE_COLOR)
        c4_top.pack(fill=tk.X, padx=10, pady=(6, 2))
        tk.Label(c4_top, text="🔑 Usa una Chiave dall'Inventario", font=("Segoe UI", 10, "bold"), bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)

        c4_sub = tk.Frame(c4, bg=SURFACE_COLOR)
        c4_sub.pack(fill=tk.X, padx=10, pady=(0, 6))
        if keys_in_bag:
            key_var = tk.StringVar(value=keys_in_bag[0])
            key_combo = ttk.Combobox(c4_sub, textvariable=key_var, values=keys_in_bag, state="readonly", width=18)
            key_combo.pack(side=tk.LEFT, padx=(0, 6))

            def do_key():
                from common.protocol import make_toggle_door_request
                self.network.send(make_toggle_door_request(clicked_hex.q, clicked_hex.r, method="key", key_item=key_var.get()))
                win.destroy()

            ttk.Button(c4_sub, text="Inserisci Chiave", command=do_key, style='Info.TButton').pack(side=tk.RIGHT, padx=4)
        else:
            tk.Label(c4_sub, text="Nessuna chiave identificata nell'inventario.", font=("Segoe UI", 8, "italic"), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT)

        btn_close = ttk.Button(win, text="Annulla / Non Interagire", command=win.destroy, style='Secondary.TButton')
        btn_close.pack(pady=8)

    def open_aoe_dialog(self):
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        win.title(_t("aoe_client_dialog_title", default="Lancia Incantesimo / AoE"))
        win.minsize(300, 250)
        apply_modern_window_style(win)
        
        ttk.Label(win, text=_t("aoe_shape", default="Forma Area:")).pack(pady=5)
        type_var = tk.StringVar(value="sfera")
        frame_radio = ttk.Frame(win)
        frame_radio.pack()
        ttk.Radiobutton(frame_radio, text=_t("aoe_sphere_cube", default="Sfera/Cubo"), variable=type_var, value="sfera").pack(side=tk.LEFT)
        ttk.Radiobutton(frame_radio, text=_t("aoe_cone", default="Cono"), variable=type_var, value="cono").pack(side=tk.LEFT)
        ttk.Radiobutton(frame_radio, text=_t("aoe_line", default="Linea"), variable=type_var, value="linea").pack(side=tk.LEFT)
        
        ttk.Label(win, text=_t("aoe_size_hexes", default="Raggio / Lunghezza (esagoni):")).pack(pady=5)
        size_entry = ttk.Entry(win, width=10)
        size_entry.insert(0, "3")
        size_entry.pack()
        
        ttk.Label(win, text=_t("aoe_color", default="Colore:")).pack(pady=5)
        color_var = tk.StringVar(value="red")
        color_frame = ttk.Frame(win)
        color_frame.pack()
        colors = [
            (_t("color_red", default="Rosso"), "red"),
            (_t("color_blue", default="Blu"), "blue"),
            (_t("color_green", default="Verde"), "green"),
            (_t("color_yellow", default="Giallo"), "yellow"),
            (_t("color_purple", default="Viola"), "purple")
        ]
        for cname, cval in colors:
            ttk.Radiobutton(color_frame, text=cname, variable=color_var, value=cval).pack(side=tk.LEFT)
            
        ttk.Separator(win, orient="horizontal").pack(fill="x", pady=10)
        
        req_save_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(win, text=_t("aoe_save_auto_damage", default="Richiede Tiro Salvezza (Danni Automatici)"), variable=req_save_var).pack(pady=2)
        
        save_frame = ttk.Frame(win)
        save_frame.pack(pady=5)
        
        ttk.Label(save_frame, text="Stat:").grid(row=0, column=0, padx=2)
        stat_var = tk.StringVar(value="DES")
        ttk.Combobox(save_frame, textvariable=stat_var, values=["FOR", "DES", "COS", "INT", "SAG", "CAR"], width=5).grid(row=0, column=1, padx=2)
        
        ttk.Label(save_frame, text=_t("aoe_dc", default="CD:")).grid(row=0, column=2, padx=2)
        dc_entry = ttk.Entry(save_frame, width=5)
        dc_entry.insert(0, "15")
        dc_entry.grid(row=0, column=3, padx=2)
        
        ttk.Label(save_frame, text=_t("aoe_damage", default="Danni:")).grid(row=1, column=0, padx=2, pady=5)
        dmg_entry = ttk.Entry(save_frame, width=8)
        dmg_entry.insert(0, "8d6")
        dmg_entry.grid(row=1, column=1, padx=2, pady=5)
        
        half_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(save_frame, text=_t("aoe_half_damage", default="Dimezza Danni"), variable=half_var).grid(row=1, column=2, columnspan=2, padx=2)

        ttk.Label(win, text=_t("aoe_consume_slot", default="Consuma Slot Incantesimo:")).pack(pady=(6, 2))
        slot_frame = ttk.Frame(win)
        slot_frame.pack(pady=(0, 5))
        
        slot_combo_values = [_t("aoe_no_slot", default="0 - Nessuno / Trucchetto")]
        char_slots = getattr(self.active_character, "spell_slots", {}) if self.active_character else {}
        for lvl_str in sorted([str(i) for i in range(1, 10)], key=int):
            if isinstance(char_slots, dict) and lvl_str in char_slots:
                info = char_slots[lvl_str]
                cur = info.get("current", 0)
                mx = info.get("max", 0)
                slot_combo_values.append(_t("aoe_slot_lvl", lvl=lvl_str, cur=cur, mx=mx, default=f"{lvl_str} - Slot Livello {lvl_str} ({cur}/{mx} disp)"))
            else:
                slot_combo_values.append(f"{lvl_str} - Slot Livello {lvl_str}")
        
        slot_combo = ttk.Combobox(slot_frame, values=slot_combo_values, state="readonly", width=25)
        slot_combo.current(0)
        slot_combo.pack()
            
        def submit():
            try:
                sz = int(size_entry.get())
            except (ValueError, TypeError):
                sz = 3
            self.aoe_mode = True
            if hasattr(self, "aoe_button"):
                self.aoe_button.configure(style="ToolActive.TButton")
            if getattr(self, "map_canvas", None):
                try: self.map_canvas.config(cursor="tcross")
                except Exception: pass
            dc = 10
            if req_save_var.get():
                try: dc = int(dc_entry.get())
                except (ValueError, TypeError): dc = 10
                
            sel_slot = slot_combo.get().split(" - ")[0].strip()
            self.aoe_params = {
                "type": type_var.get(), "size": sz, "color": color_var.get(),
                "req_save": req_save_var.get(), "stat": stat_var.get(), "dc": dc,
                "dmg": dmg_entry.get(), "half": half_var.get(),
                "slot_level": sel_slot
            }
            self.show_toast(_t("aoe_click_map_prompt", default="Clicca sulla mappa per confermare il bersaglio / centro dell'area d'effetto."), title="💥 AoE", toast_type="info")
            win.destroy()
            
        def resolve_existing_aoe():
            stat = stat_var.get()
            try: dc = int(dc_entry.get())
            except (ValueError, TypeError): dc = 13
            dmg = dmg_entry.get().strip() or "8d6"
            half = half_var.get()
            from common.protocol import make_resolve_aoe_request
            self.network.send(make_resolve_aoe_request(0, stat, dc, dmg, half))
            self.show_toast("Risoluzione TS e danni inviata al server!", title="⚡ Risolvi AoE", toast_type="info")
            win.destroy()

        btn_box = ttk.Frame(win)
        btn_box.pack(pady=10)
        ttk.Button(btn_box, text=_t("btn_prepare_cast", default="Prepara Lancio"), command=submit, style="Primary.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_box, text="⚡ Risolvi TS/Danni su Bersagli", command=resolve_existing_aoe, style="Gold.TButton").pack(side=tk.LEFT, padx=4)

    def request_long_rest(self):
        if not self.is_connected: return
        self.network.send({"type": "LONG_REST_REQUEST", "data": {}})

    def request_move(self, clicked_hex):
        """Invia una richiesta di movimento al server quando il giocatore clicca su un esagono."""
        if not self.is_connected: return
        self.network.send(make_move_request(clicked_hex.q, clicked_hex.r))

    def connect_to_server(self):
        if self.is_connected: return
        
        login_dialog = LoginDialog(self.master, self.character_manager)
        self.master.wait_window(login_dialog)
        
        if not login_dialog.result: return
        
        server_ip, char = login_dialog.result
        self.name = char.name
        self.active_character = char
        
        try:
            self.network.connect(server_ip, 5000)
            self.is_connected = True
            self.last_server_ip = server_ip
            
            # Start Voice Client
            self.voice_client = VoiceClient(server_ip, 53912)
            self.voice_client.start()
            
            self.network.send(make_join(self.name, getattr(self.active_character, "last_position", None)))
            self.network.send(make_update_stats_request(self.active_character.hp_current, self.active_character.hp_max, self.active_character.initiative, getattr(self.active_character, "conditions", [])))
            self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
            self.log_to_chat(f"Connesso a {server_ip} come {self.name} (Lv.{char.level} {char.char_class}).", "Globale")
            self.master.title(f"D&D Client - {self.name}")
            self.status_label.config(text=f"Stato: Connesso a {server_ip}", style="Success.TLabel")
            if hasattr(self, 'voice_status_lbl'):
                self.voice_status_lbl.config(text="🟢 Voice: Connesso", fg=ACCENT_GREEN)
            self.set_controls_state(tk.NORMAL)
            self.active_character_var.set(self.name)
            self.update_hero_summary_card()
            for i in range(10):
                cmd = self.active_character.hotbar[i]
                self.hotbar_buttons[i].config(text=cmd[:10] if cmd else f"{i+1}")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile connettersi a {server_ip}: {e}"); self.is_connected = False

    def reconnect_to_server(self):
        if self.is_connected:
            messagebox.showinfo("Connesso", "Sei già connesso al server.")
            return
        last_ip = getattr(self, "last_server_ip", None)
        if not last_ip or not self.active_character:
            self.connect_to_server()
            return
        try:
            self.network.connect(last_ip, 5000)
            self.is_connected = True
            if self.voice_client:
                try: self.voice_client.stop()
                except Exception: pass
            self.voice_client = VoiceClient(last_ip, 53912)
            self.voice_client.start()
            self.network.send(make_join(self.name, getattr(self.active_character, "last_position", None)))
            self.network.send(make_update_stats_request(self.active_character.hp_current, self.active_character.hp_max, self.active_character.initiative, getattr(self.active_character, "conditions", [])))
            self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
            self.log_to_chat(f"Riconnesso con successo a {last_ip} come {self.name}!", "Globale", sender="Sistema", color="#2ECC71")
            self.master.title(f"D&D Client - {self.name}")
            self.status_label.config(text=f"Stato: Connesso a {last_ip}", style="Success.TLabel")
            if hasattr(self, 'voice_status_lbl'):
                self.voice_status_lbl.config(text="🟢 Voice: Connesso", fg=ACCENT_GREEN)
            self.set_controls_state(tk.NORMAL)
            self.update_hero_summary_card()
        except Exception as e:
            messagebox.showerror("Errore Riconnessione", f"Impossibile riconnettersi a {last_ip}: {e}")
            self.is_connected = False

    def process_queue(self):
        try:
            while True:
                try:
                    msg = self.gui_queue.get_nowait()
                except queue.Empty:
                    break
                try:
                    self.handle_server_message(msg)
                except Exception as e:
                    print(f"[CLIENT] Errore elaborazione messaggio: {e}")
        finally:
            if hasattr(self, "master") and self.master.winfo_exists():
                self.master.after(100, self.process_queue)

    def redraw_map_and_players(self):
        # Pass the full players_data so UI components can access position, conditions, etc.
        players_info = {}
        for name, data in self.players_data.items():
            if data.get("is_hidden", False) and name != self.name:
                continue
            players_info[name] = data
            
        turn_name = ""
        if getattr(self, "combat_active", False):
            turn_name = self.game_state.get("turn_player_name", "") if self.game_state else ""
            if not turn_name:
                combatants = [p for p in self.players_data.values() if p.get('in_combat', True)]
                if 0 <= getattr(self, "turn_index", 0) < len(combatants):
                    turn_name = combatants[self.turn_index].get('name', '')
        
        time_hour = self.game_state.get("time_hour", 12) if self.game_state else 12
        time_minute = self.game_state.get("time_minute", 0) if self.game_state else 0
        weather = self.game_state.get("weather", "Sereno") if self.game_state else "Sereno"
        combat_active = self.combat_active
        combat_order = [p["name"] for p in self.players_data.values() if p.get("in_combat", True)] if combat_active else []
        
        round_number = getattr(self, "round_number", 1)
        auto_day_night = True
        if self.game_state and isinstance(self.game_state.get("automation_settings"), dict):
            auto_day_night = self.game_state["automation_settings"].get("auto_day_night_cycle", True)
        elif hasattr(self, "automation_settings") and isinstance(self.automation_settings, dict):
            auto_day_night = self.automation_settings.get("auto_day_night_cycle", True)

        self.map_canvas.update_data(
            self.local_map_data, 
            players_info, 
            self.name, 
            turn_player_name=turn_name, 
            aoes_data=getattr(self, "aoes_data", []),
            time_hour=time_hour,
            weather=weather,
            combat_active=combat_active,
            combat_order=combat_order,
            round_number=round_number,
            time_minute=time_minute,
            auto_day_night=auto_day_night
        )

    def handle_map_data_update(self, data):
        self.local_map_data = data.get("map")
        self.redraw_map_and_players()
        
    def handle_combat_state_update(self, data):
        was_combat = getattr(self, "combat_active", False)
        self.combat_active = data.get("combat_active", False)
        self.turn_index = data.get("turn_index", 0)
        self.round_number = data.get("round_number", 1)
        self.aoes_data = data.get("active_aoes", [])
        turn_player_name = data.get("turn_player_name")
        
        was_my_turn = getattr(self, "_is_my_turn", False)
        is_my_turn = False
        if self.combat_active:
            if turn_player_name:
                is_my_turn = (turn_player_name == self.name)
            else:
                combatants = [p for p in self.players_data.values() if p.get('in_combat', True)]
                combatants.sort(key=lambda x: x.get('initiative', 0), reverse=True)
                if 0 <= self.turn_index < len(combatants):
                    is_my_turn = (combatants[self.turn_index].get('name') == self.name)
        
        self._is_my_turn = is_my_turn
        if not self.combat_active and was_combat:
            self.help_targeting_mode = False
            self.reset_turn_resources()

        if is_my_turn:
            if hasattr(self, 'end_turn_btn'):
                self.end_turn_btn.pack(fill=tk.X, pady=2, before=self.combat_btn)
            if not was_my_turn:
                self.reset_turn_resources()
                self.show_turn_banner()
                if self.active_character and getattr(self.active_character, "hp_current", 1) == 0:
                    conds = getattr(self.active_character, "conditions", [])
                    if "Morto" not in conds and "Stabilizzato" not in conds:
                        self.prompt_death_save()
        else:
            if hasattr(self, 'end_turn_btn'):
                self.end_turn_btn.pack_forget()

        self.update_action_economy_ui()
        self.update_player_listbox()
        self.redraw_map_and_players()

    def handle_game_state(self, data):
        was_combat = getattr(self, "combat_active", False)
        self.game_state = data
        self.players_data = {p['name']: p for p in data.get('players', [])}
        self.local_map_data = data.get("map")
        
        if self.active_character and self.name in self.players_data:
            p_dict = self.players_data[self.name]
            pos = p_dict.get("position")
            if pos:
                self.active_character.last_position = pos
            if "conditions" in p_dict:
                self.active_character.conditions = list(p_dict.get("conditions", []))
            if "hp" in p_dict and p_dict["hp"] is not None:
                self.active_character.hp_current = p_dict["hp"]
            if "max_hp" in p_dict and p_dict["max_hp"] is not None:
                self.active_character.hp_max = p_dict["max_hp"]
            if "temp_hp" in p_dict and p_dict["temp_hp"] is not None:
                self.active_character.temp_hp = p_dict["temp_hp"]
            if "initiative" in p_dict and p_dict["initiative"] is not None:
                self.active_character.initiative = p_dict["initiative"]
            self.character_manager.save_characters()
            self.update_hero_summary_card()
        
        owned_chars = [p['name'] for p in data.get('players', []) if p['name'] == self.name or p.get('owner') == self.name]
        if not owned_chars: owned_chars = [self.name]
        if hasattr(self, 'active_character_combo'):
            self.active_character_combo['values'] = owned_chars
            if self.active_character_var.get() not in owned_chars:
                self.active_character_var.set(owned_chars[0])
                self.on_active_character_changed()
        was_my_turn = getattr(self, "_is_my_turn", False)
        
        self.combat_active = data.get("combat_active", False)
        self.turn_index = data.get("turn_index", 0)
        self.round_number = data.get("round_number", 1)
        self.aoes_data = data.get("active_aoes", [])
        
        day = data.get("time_day", 1)
        month = data.get("time_month", 1)
        year = data.get("time_year", 1492)
        hour = data.get("time_hour", 8)
        months = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
        month_name = months[month] if 1 <= month <= 12 else "Mese Sconosciuto"
        time_str = f"{hour:02d}:00"
        
        if getattr(self, 'lbl_time', None):
            self.lbl_time.config(text=f"Data: {day} {month_name} {year} - {time_str}")
        
        is_my_turn = False
        if self.combat_active:
            all_players_list = data.get('players', [])
            combatants_list = [p for p in all_players_list if p.get('in_combat', True)]
            if 0 <= self.turn_index < len(combatants_list):
                if combatants_list[self.turn_index]['name'] == self.name:
                    is_my_turn = True
        
        self._is_my_turn = is_my_turn
        if not self.combat_active and was_combat:
            self.help_targeting_mode = False
            self.reset_turn_resources()
        
        if is_my_turn:
            self.end_turn_btn.pack(fill=tk.X, pady=2, before=self.combat_btn)
            if not was_my_turn:
                self.reset_turn_resources()
                self.show_turn_banner()
        else:
            self.end_turn_btn.pack_forget()

        self.update_hero_summary_card()
        self.update_action_economy_ui()
        self.update_player_listbox()
        self.redraw_map_and_players()

    def show_turn_banner(self):
        banner = tk.Toplevel(self.master)
        banner.overrideredirect(True)
        banner.attributes('-topmost', True)
        banner.configure(bg="#D4AF37")
        
        lbl = tk.Label(banner, text="È IL TUO TURNO!", font=("Georgia", 24, "bold"), bg="#D4AF37", fg="black", padx=20, pady=10)
        lbl.pack()
        
        self.master.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (lbl.winfo_reqwidth() // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (lbl.winfo_reqheight() // 2)
        banner.geometry(f"+{x}+{y}")
        
        self.master.after(2000, lambda: banner.destroy() if hasattr(banner, "winfo_exists") and banner.winfo_exists() else None)

    def handle_player_joined(self, data):
        self.players_data[data.get('name')] = data
        self.update_player_listbox()
        self.redraw_map_and_players()

    def handle_player_left(self, data):
        name = data.get('name')
        if name in self.players_data: del self.players_data[name]
        self.update_player_listbox()
        self.redraw_map_and_players()

    def handle_player_move(self, data):
        name = data.get('name')
        old_pos = None
        if name in self.players_data:
            old_pos = self.players_data[name].get('position')
            self.players_data[name]['position'] = data.get('position')
        new_pos = data.get('position')
        if name == self.name and self.active_character:
            self.active_character.last_position = new_pos
            self.character_manager.save_characters()
            if self.combat_active and getattr(self, "_is_my_turn", False) and old_pos and new_pos and old_pos != new_pos:
                dist = max(abs(old_pos[0] - new_pos[0]), abs(old_pos[0] + old_pos[1] - new_pos[0] - new_pos[1]), abs(old_pos[1] - new_pos[1]))
                self.movement_spent_ft += dist * 5
                self.update_action_economy_ui()
        self.redraw_map_and_players()

    def handle_player_stats_update(self, data):
        name = data.get('name')
        if name in self.players_data:
            self.players_data[name]['hp'] = data.get('hp')
            self.players_data[name]['max_hp'] = data.get('max_hp')
            self.players_data[name]['initiative'] = data.get('initiative')
            self.players_data[name]['temp_hp'] = data.get('temp_hp', 0)
            if 'conditions' in data:
                self.players_data[name]['conditions'] = data.get('conditions')
            if 'active_effects' in data:
                self.players_data[name]['active_effects'] = data.get('active_effects')
            if 'condition_durations' in data:
                self.players_data[name]['condition_durations'] = data.get('condition_durations')
            
        if name == self.name and self.active_character:
            if data.get('hp') is not None:
                self.active_character.hp_current = data.get('hp')
            if data.get('max_hp') is not None:
                self.active_character.hp_max = data.get('max_hp')
            if data.get('initiative') is not None:
                self.active_character.initiative = data.get('initiative')
            if 'temp_hp' in data and data.get('temp_hp') is not None:
                self.active_character.temp_hp = data.get('temp_hp', 0)
            if 'conditions' in data and data.get('conditions') is not None:
                self.active_character.conditions = data.get('conditions')
            if 'active_effects' in data and data.get('active_effects') is not None:
                self.active_character.active_effects = data.get('active_effects')
            self.character_manager.save_characters()
            self.update_hero_summary_card()
            self.update_action_economy_ui()
            
            if hasattr(self, 'stats_window') and self.stats_window.winfo_exists():
                self.stats_window.update_dynamic_stats()
            
        self.update_player_listbox()

    def set_controls_state(self, state):
        for btn in ['entry', 'roll_button', 'player_listbox', 'action_button', 'aoe_button', 'travel_button', 'calendar_button', 'combat_btn', 'end_turn_btn', 'btn_act_tracker', 'btn_bonus_tracker', 'btn_react_tracker', 'btn_dash', 'btn_disengage', 'btn_dodge', 'btn_help', 'btn_short_rest', 'btn_second_wind', 'btn_action_surge', 'btn_rage']:
            widget = getattr(self, btn, None)
            if widget:
                try: widget.config(state=state)
                except Exception: pass
        if hasattr(self, 'stats_button') and self.stats_button:
            try: self.stats_button.config(state=tk.NORMAL)
            except Exception: pass
        self.update_action_economy_ui()


    def request_combat(self):
        from common.protocol import make_start_combat_request
        self.network.send(make_start_combat_request(self.name))
        self.log_to_chat("Hai richiesto l'inizio del combattimento al DM.", "Globale", "grey")

    def end_turn(self):
        from common.protocol import make_end_turn_request
        self.network.send(make_end_turn_request())
        self.end_turn_btn.pack_forget()
        self.reset_turn_resources()

    def open_action_dialog(self):
        self.targeting_mode = True
        self.show_toast("Clicca sul token del bersaglio direttamente sulla mappa.", title="Seleziona Bersaglio", toast_type="info")
        
    def show_action_dialog_for_target(self, target_name):
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        win.title(f"Azione su {target_name}")
        win.minsize(320, 360)
        from common.theme import apply_modern_window_style
        apply_modern_window_style(win)

        ttk.Label(win, text=f"Bersaglio: {target_name}", font=("Georgia", 12, "bold"), foreground="#D4AF37").pack(pady=(10, 0))

        ttk.Label(win, text="Tipo di Azione:").pack(pady=(10, 0))
        action_var = tk.StringVar(value="damage")
        frame_radio = ttk.Frame(win)
        frame_radio.pack(pady=5)
        ttk.Radiobutton(frame_radio, text="Danno", variable=action_var, value="damage").pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(frame_radio, text="Cura", variable=action_var, value="heal").pack(side=tk.LEFT, padx=6)
        ttk.Radiobutton(frame_radio, text="Temp HP", variable=action_var, value="temp_hp").pack(side=tk.LEFT, padx=6)

        dt_frame = ttk.Frame(win)
        dt_frame.pack(fill=tk.X, padx=20, pady=(6, 2))
        ttk.Label(dt_frame, text="Tipo di Danno (se Danno):").pack(anchor="w")
        damage_types = ["Tagliente", "Perforante", "Contundente", "Fuoco", "Freddo", "Fulmine", "Veleno", "Acido", "Psichico", "Necrotico", "Radioso", "Forza", "Tuono"]
        dt_combo = ttk.Combobox(dt_frame, values=damage_types, state="readonly")
        dt_combo.set("Tagliente")
        dt_combo.pack(fill=tk.X, pady=2)

        cover_frame = ttk.Frame(win)
        cover_frame.pack(fill=tk.X, padx=20, pady=(4, 2))
        ttk.Label(cover_frame, text="🛡️ Copertura Bersaglio (D&D 5e RAW):").pack(anchor="w")
        cover_combo = ttk.Combobox(cover_frame, values=["Nessuna (0 CA)", "Mezza (+2 CA, +2 TS DES)", "Tre Quarti (+5 CA, +5 TS DES)", "Totale (Bloccato)"], state="readonly")
        cover_combo.set("Nessuna (0 CA)")
        cover_combo.pack(fill=tk.X, pady=2)

        ttk.Label(win, text="Formula / Valore (es. 1d8+3 oppure 5):").pack(pady=(6, 0))
        formula_entry = ttk.Entry(win, font=self.default_font)
        formula_entry.pack(pady=4, padx=20, fill=tk.X)

        ttk.Label(win, text="Arma / Motivo (Opzionale):").pack(pady=(6, 0))
        reason_entry = ttk.Entry(win, font=self.default_font)
        reason_entry.pack(pady=4, padx=20, fill=tk.X)

        def submit():
            action_type = action_var.get()
            formula = formula_entry.get().strip()
            reason = reason_entry.get().strip()
            damage_type = dt_combo.get().strip()
            
            if not formula:
                self.show_toast("Devi inserire una formula o un valore numerico.", title="Errore", toast_type="danger")
                return
                
            cov_sel = cover_combo.get()
            if "Mezza" in cov_sel:
                reason = f"{reason} [Mezza Copertura]".strip()
            elif "Tre Quarti" in cov_sel:
                reason = f"{reason} [Tre Quarti Copertura]".strip()
            elif "Totale" in cov_sel:
                reason = f"{reason} [Copertura Totale]".strip()

            self.network.send(make_targeted_action_request(target_name, action_type, formula, reason, damage_type=damage_type))
            self.action_spent = True
            self.update_action_economy_ui()
            win.destroy()
            self.show_toast(f"Azione '{action_type}' eseguita su {target_name}!", title="⚔️ Azione Eseguita", toast_type="success")


        ttk.Button(win, text="Esegui Azione", command=submit, style='Primary.TButton').pack(pady=16)

    def toggle_mute(self):
        if self.voice_client:
            self.voice_client.is_muted = not self.voice_client.is_muted
            return self.voice_client.is_muted
        return False

    def toggle_deafen(self):
        if self.voice_client:
            self.voice_client.is_deafened = not self.voice_client.is_deafened
            return self.voice_client.is_deafened
        return False

    def toggle_audio_mute(self):
        if getattr(self, "_audio_muted", False):
            self._audio_muted = False
            self.audio_manager.set_volume("music", getattr(self, '_saved_music_vol', 0.8))
            self.audio_manager.set_volume("sfx", getattr(self, '_saved_sfx_vol', 1.0))
            self.btn_audio_mute.config(text=" 🔊 ", fg="white")
        else:
            self._audio_muted = True
            self._saved_music_vol = self.audio_manager.get_volume("music")
            self._saved_sfx_vol = self.audio_manager.get_volume("sfx")
            self.audio_manager.set_volume("music", 0.0)
            self.audio_manager.set_volume("sfx", 0.0)
            self.btn_audio_mute.config(text=" 🔇 ", fg="#ED4245")

    def disconnect(self):
        if getattr(self, "audio_manager", None):
            try: self.audio_manager.stop("all")
            except Exception: pass
        if getattr(self, "voice_client", None):
            try: self.voice_client.stop()
            except Exception: pass
        if self.is_connected:
            self.network.disconnect()
        self.is_connected = False

    def on_closing(self):
        msg = _t("confirm_exit_connected") if self.is_connected else _t("confirm_exit_client")
        if messagebox.askokcancel(_t("menu_exit"), msg):
            try:
                unregister_language_listener(self.on_language_changed)
            except Exception:
                pass
            try:
                unregister_unit_listener(self.on_unit_changed)
            except Exception:
                pass
            self.disconnect()
            self.master.destroy()

    def handle_disconnection(self):
        self.is_connected = False
        if getattr(self, "audio_manager", None):
            try: self.audio_manager.stop("all")
            except Exception: pass
        if self.voice_client:
            try: self.voice_client.stop()
            except Exception: pass
        self.show_toast("La connessione con il server è stata persa.\nPuoi usare 'Riconnetti Ultimo Server' dal menu Server.", title="Disconnesso", toast_type="danger")
        self.master.title("D&D Client - Disconnesso")
        self.status_label.config(text="Stato: Disconnesso", style="Danger.TLabel")
        self.set_controls_state(tk.DISABLED)
        self.local_map_data=None; self.players_data={}; self.update_player_listbox(); self.redraw_map_and_players()

    def handle_server_message(self, msg):
        msg_type=msg.get("type"); data=msg.get("data", {})
        handler_map={
            "ERROR_REPLY": lambda d: messagebox.showerror("Errore dal Server", d.get("text")), 
            "SIMPLE_REPLY": lambda d: self.log_to_chat(f"[SERVER]: {d.get('text')}", "Globale", "lightblue"), 
            "CHAT_BROADCAST": self.handle_chat_broadcast, 
            "GAME_STATE": self.handle_game_state, 
            "MAP_DATA_UPDATE": self.handle_map_data_update,
            "COMBAT_STATE_UPDATE": self.handle_combat_state_update,
            "PLAYER_JOINED": self.handle_player_joined, 
            "PLAYER_LEFT": self.handle_player_left, 
            "PLAYER_MOVE": self.handle_player_move, 
            "DICE_ROLL_RESULT": self.handle_dice_roll, 
            "PLAYER_STATS_UPDATE": self.handle_player_stats_update,
            "RECEIVE_ITEM": self.handle_receive_item,
            "RECEIVE_GOLD": self.handle_receive_gold,
            "REQUEST_INITIATIVE": self.handle_request_initiative,
            "PING_BROADCAST": self.handle_ping_broadcast,
            "DRAW_BROADCAST": self.handle_draw_broadcast,
            "CLEAR_DRAWINGS_BROADCAST": self.handle_clear_drawings_broadcast,
            "PROMPT_LONG_REST_VOTE": self.handle_prompt_long_rest_vote,
            "DO_LONG_REST": self.handle_do_long_rest,
            "FOW_UPDATE_BROADCAST": self.handle_fow_update_broadcast,
            "AUDIO_PLAY_BROADCAST": self.handle_audio_play,
            "AUDIO_TRACK_PLAY": self.handle_audio_track_play,
            "AUDIO_STOP": self.handle_audio_stop,
            "AUDIO_TRACK_CHUNK": self.handle_audio_track_chunk,
            "CUSTOM_SPELL_RESPONSE": self.handle_custom_spell_response,
            "CURRENCY_RESPONSE": self.handle_currency_response,
            "ITEM_APPROVAL_RESPONSE": self.handle_item_approval_response,
            "JOURNAL_APPROVAL_RESPONSE": self.handle_journal_approval_response,
            "CAMPAIGN_STARTER_GRANTED": self.handle_campaign_starter_granted,
            "UPDATE_INSPIRATION": self.handle_update_inspiration,
            "PROMPT_SAVE": self.handle_prompt_save,
            "PROMPT_REACTION": self.handle_prompt_reaction,
            "OPPORTUNITY_ALERT": self.handle_opportunity_alert,
            "HANDOUT_BROADCAST": self.handle_handout_broadcast,
            "HANDOUT_SHARE_BROADCAST": self.handle_handout_broadcast,
            "QUEST_LIST_UPDATE": self.handle_quest_list_update,
            "AUTOMATION_SETTINGS_BROADCAST": self.handle_automation_settings_broadcast
        }

        handler=handler_map.get(msg_type)
        if handler: handler(data)

    def handle_automation_settings_broadcast(self, data):
        mode = data.get("mode", "hybrid")
        settings = data.get("settings", {})
        self.automation_settings = settings
        if self.game_state:
            self.game_state["automation_settings"] = settings
            self.game_state["automation_mode"] = mode
        mode_names = {
            "manual": "🎲 Tavolo Tradizionale (Controllo DM)",
            "hybrid": "⚖️ Ibrido Assistito",
            "full": "⚡ Full Automation (Tattico Rapido)"
        }
        name = mode_names.get(mode, mode)
        self.log_to_chat(f"⚙️ Stile di gestione campagna impostato dal DM su: {name}", "Sistema", ACCENT_GOLD)
        self.redraw_map_and_players()

    def handle_prompt_reaction(self, data):
        reaction_type = data.get("reaction_type")
        source_name = data.get("source_name", "Un'entità")
        details = data.get("details", {})
        
        if reaction_type == "OPPORTUNITY_ATTACK":
            win = tk.Toplevel(self.master)
            win.transient(self.master)
            win.grab_set()
            apply_modern_window_style(win)
            win.title("⚔️ Attacco d'Opportunità (Reazione)")
            win.minsize(420, 200)
            
            tk.Label(win, text="⚔️ REAZIONE: ATTACCO D'OPPORTUNITÀ", font=("Georgia", 13, "bold"), fg="#F59E0B", bg="#1E2024").pack(fill=tk.X, pady=8)
            msg = f"{source_name} sta uscendo dalla tua portata di mischia senza disimpegnarsi!\n\nVuoi spendere la tua REAZIONE per sferrare un Attacco d'Opportunità?"
            tk.Label(win, text=msg, font=FONT_REGULAR, fg=TEXT_COLOR, bg=BG_COLOR, justify="center").pack(padx=16, pady=10)
            
            btn_frame = tk.Frame(win, bg=BG_COLOR)
            btn_frame.pack(pady=12)
            
            def accept():
                from common.protocol import make_reaction_response
                self.network.send(make_reaction_response("OPPORTUNITY_ATTACK", True, self.name, source_name, details))
                self.show_toast(f"Attacco d'Opportunità sferrato contro {source_name}!", title="⚔️ Reazione Usata", toast_type="success")
                win.destroy()
                
            def decline():
                from common.protocol import make_reaction_response
                self.network.send(make_reaction_response("OPPORTUNITY_ATTACK", False, self.name, source_name, details))
                win.destroy()

            win.protocol("WM_DELETE_WINDOW", decline)
            ttk.Button(btn_frame, text="⚔️ Sferra Attacco (Spendi Reazione)", command=accept, style="Gold.TButton").pack(side=tk.LEFT, padx=6)
            ttk.Button(btn_frame, text="Ignora", command=decline).pack(side=tk.LEFT, padx=6)
            
        elif reaction_type == "SHIELD_SPELL":
            win = tk.Toplevel(self.master)
            win.transient(self.master)
            win.grab_set()
            apply_modern_window_style(win)
            win.title("🛡️ Reazione: Incantesimo Scudo")
            win.minsize(440, 220)
            
            hit_roll = details.get("hit_roll", 15)
            atk_weapon = details.get("weapon_name", "un attacco")
            current_ac = details.get("current_ac", 12)
            
            tk.Label(win, text="🛡️ REAZIONE: INCANTESIMO SCUDO", font=("Georgia", 13, "bold"), fg="#60A5FA", bg="#1E2024").pack(fill=tk.X, pady=8)
            msg = f"{source_name} ti sta colpendo con {atk_weapon}!\n(Tiro per Colpire: {hit_roll} vs la tua CA {current_ac})\n\nVuoi spendere uno slot di 1° livello per lanciare SCUDO?\nOttieni +5 CA (totale {current_ac + 5}), che farà fallire l'attacco!"
            tk.Label(win, text=msg, font=FONT_REGULAR, fg=TEXT_COLOR, bg=BG_COLOR, justify="center").pack(padx=16, pady=8)
            
            btn_frame = tk.Frame(win, bg=BG_COLOR)
            btn_frame.pack(pady=12)
            
            available_slot_lvl = None
            if self.active_character and hasattr(self.active_character, "spell_slots"):
                for s_lvl in range(1, 10):
                    sl = self.active_character.spell_slots.get(str(s_lvl), {})
                    cur_val = sl.get("current", 0) if isinstance(sl, dict) else (sl[0] if isinstance(sl, list) and sl else 0)
                    if cur_val > 0:
                        available_slot_lvl = str(s_lvl)
                        break

            def accept():
                if available_slot_lvl and self.active_character and hasattr(self.active_character, "spell_slots"):
                    sl = self.active_character.spell_slots.get(available_slot_lvl)
                    if isinstance(sl, dict):
                        sl["current"] = max(0, sl.get("current", 1) - 1)
                    elif isinstance(sl, list) and sl:
                        sl[0] = max(0, sl[0] - 1)
                    self.character_manager.save_characters()
                    from common.protocol import make_update_full_sheet_request
                    self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
                from common.protocol import make_reaction_response
                self.network.send(make_reaction_response("SHIELD_SPELL", True, self.name, source_name, details))
                self.show_toast("Incantesimo Scudo attivato! (+5 CA)", title="🛡️ Scudo", toast_type="success")
                win.destroy()

            def decline():
                from common.protocol import make_reaction_response
                self.network.send(make_reaction_response("SHIELD_SPELL", False, self.name, source_name, details))
                win.destroy()

            win.protocol("WM_DELETE_WINDOW", decline)
            shield_btn_state = "normal" if available_slot_lvl else "disabled"
            ttk.Button(btn_frame, text="🛡️ Lancia Scudo (+5 CA)", command=accept, style="Primary.TButton", state=shield_btn_state).pack(side=tk.LEFT, padx=6)
            ttk.Button(btn_frame, text="Subisci Attacco", command=decline).pack(side=tk.LEFT, padx=6)

    def handle_handout_broadcast(self, data):
        title = data.get("title", "Documento Condiviso")
        content = data.get("content", "")
        img_b64 = data.get("image_b64")

        self.show_toast(f"Il Dungeon Master ha condiviso: '{title}'", title="📜 Nuovo Documento", toast_type="gold")
        self.log_to_chat(f"📜 [DOCUMENTO DM] '{title}' condiviso con il party.", "Globale", color="#E5A50A")

        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.title(f"📜 {title}")
        win.minsize(480, 420)
        apply_modern_window_style(win)

        header_frame = tk.Frame(win, bg="#1A1B1E", padx=12, pady=10)
        header_frame.pack(fill=tk.X)
        tk.Label(header_frame, text=f"📜 {title}", font=("Georgia", 14, "bold"), bg="#1A1B1E", fg="#D4AF37").pack(anchor="w")

        content_frame = tk.Frame(win, bg="#212529", padx=14, pady=12)
        content_frame.pack(fill=tk.BOTH, expand=True)

        if img_b64:
            try:
                img_data = base64.b64decode(img_b64)
                img = Image.open(BytesIO(img_data))
                img.thumbnail((420, 320))
                tk_img = ImageTk.PhotoImage(img)
                lbl_img = tk.Label(content_frame, image=tk_img, bg="#212529")
                lbl_img.image = tk_img
                lbl_img.pack(pady=6)
            except Exception as e:
                print("Errore rendering immagine handout:", e)

        if content:
            txt = tk.Text(content_frame, wrap="word", font=("Georgia", 11), bg="#2B2D31", fg="#F8F9FA", padx=10, pady=10, relief="flat", height=10)
            txt.pack(fill=tk.BOTH, expand=True, pady=6)
            txt.insert("1.0", content)
            txt.configure(state="disabled")

        btn_box = tk.Frame(win, bg="#1A1B1E", padx=10, pady=8)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text="Chiudi", command=win.destroy).pack(side=tk.RIGHT)

    def handle_quest_list_update(self, data):
        self.quests = data.get("quests", [])
        self.show_toast("Registro Missioni aggiornato dal Dungeon Master!", title="📜 Missioni Aggiornate", toast_type="gold")

    def open_quest_log_dialog(self):
        """Apre il registro interattivo delle missioni ed obiettivi della campagna."""
        from components.quest_ui import QuestLogDialog
        quests = getattr(self, "quests", []) or []
        if not quests and hasattr(self, "server") and getattr(self.server, "game_state", None):
            quests = getattr(self.server.game_state, "quests", [])
        QuestLogDialog(self.master, {"quests": quests}, is_dm=False, network_or_server=getattr(self, "network", None))

    def handle_opportunity_alert(self, data):
        enemy_name = data.get("enemy_name", "Un nemico")
        self.show_toast(f"{enemy_name} si allontana da te!\nPuoi effettuare un Attacco d'Opportunità spendendo la tua Reazione.", title="⚠️ Attacco d'Opportunità!", duration=6000, toast_type="warning", icon="⚔️")

    def handle_custom_spell_response(self, data):
        approved = data.get("approved", False)
        spell = data.get("spell", {})
        spell_name = spell.get("name", "Incantesimo")
        is_remove = spell.get("action") == "remove"
        if approved:
            if self.active_character:
                if is_remove:
                    self.active_character.spellbook = [s for s in getattr(self.active_character, "spellbook", []) if s.get("name") != spell_name]
                    self.character_manager.save_characters()
                    if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                        self.stats_window.refresh_spell_list()
                    from common.protocol import make_update_full_sheet_request
                    self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
                    self.show_toast(f"Il Dungeon Master ha APPROVATO la rimozione di '{spell_name}' dal Grimorio.", title="Rimozione Approvata", toast_type="info")
                    return
                if not hasattr(self.active_character, "spellbook") or not isinstance(self.active_character.spellbook, list):
                    self.active_character.spellbook = []
                if not any(s.get("name") == spell_name for s in self.active_character.spellbook):
                    self.active_character.spellbook.append(spell)
                    self.character_manager.save_characters()
                    if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                        self.stats_window.refresh_spell_list()
                    from common.protocol import make_update_full_sheet_request
                    self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
            self.show_toast(f"Il Dungeon Master ha APPROVATO l'incantesimo '{spell_name}'!\nÈ stato aggiunto al tuo Grimorio.", title="Incantesimo Approvato!", toast_type="success")
        else:
            reason = data.get("reason", "Il Master ha respinto la richiesta.")
            act_disp = "la rimozione di" if is_remove else "la richiesta per"
            self.show_toast(f"Il Dungeon Master ha RESPINTO {act_disp} '{spell_name}'.\nMotivo: {reason}", title="Richiesta Rifiutata", toast_type="warning")

    def handle_currency_response(self, data):
        approved = data.get("approved", False)
        coin = data.get("coin", "MO")
        amount = data.get("amount", 0)
        reason = data.get("reason", "")
        if approved:
            if self.active_character:
                if not hasattr(self.active_character, "currency") or not isinstance(self.active_character.currency, dict):
                    self.active_character.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
                self.active_character.currency[coin] = self.active_character.currency.get(coin, 0) + amount
                self.character_manager.save_characters()
                if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                    if hasattr(self.stats_window, "currency_vars") and coin in self.stats_window.currency_vars:
                        self.stats_window.currency_vars[coin].set(self.active_character.currency[coin])
                    if hasattr(self.stats_window, "initial_currency"):
                        self.stats_window.initial_currency[coin] = self.active_character.currency[coin]
            self.show_toast(f"Il Dungeon Master ha APPROVATO la richiesta!\nHai ricevuto +{amount} {coin}.", title="Valuta Accreditata!", toast_type="gold")
        else:
            msg = reason or "La tua richiesta di valuta è stata respinta dal Master."
            self.show_toast(msg, title="Richiesta Respinta", toast_type="warning")

    def handle_journal_approval_response(self, data):
        approved = data.get("approved", False)
        field_name = data.get("field_name")
        content = data.get("content")
        reason = data.get("reason", "")
        field_disp = "Biografia & Diario" if "journal" in str(field_name) else ("Tratti & Privilegi" if "features" in str(field_name) else "Appunti di Sessione")
        if approved:
            if self.active_character:
                if hasattr(self.active_character, field_name):
                    setattr(self.active_character, field_name, content)
                self.character_manager.save_characters()
                if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                    self.stats_window.load_data()
            self.show_toast(f"Il Dungeon Master ha APPROVATO le tue modifiche a '{field_disp}'!", title="Modifica Approvata!", toast_type="success")
            self.log_to_chat(f"📜 Il Master ha approvato le modifiche a '{field_disp}'.", "Sistema", ACCENT_GOLD)
        else:
            msg = reason or f"La richiesta di modifica per '{field_disp}' è stata respinta dal Master."
            self.show_toast(msg, title="Modifica Respinta", toast_type="warning")
            self.log_to_chat(f"❌ {msg}", "Sistema", "#FF6B6B")

    def request_journal_approval(self, field_name, content, title=""):
        if self.is_connected:
            from common.protocol import make_journal_approval_request
            self.network.send(make_journal_approval_request(field_name, content, title))
            return True
        else:
            messagebox.showwarning("Non Connesso", "Devi essere connesso per richiedere l'approvazione al Master.")
            return False

    def handle_item_approval_response(self, data):
        approved = data.get("approved", False)
        item = data.get("item", {})
        slot_idx = data.get("slot_idx")
        reason = data.get("reason", "")
        it_name = item.get("name", "Oggetto")
        is_remove = item.get("action") == "remove"
        if approved:
            if self.active_character:
                if is_remove:
                    if not hasattr(self.active_character, "inventory_grid") or not isinstance(self.active_character.inventory_grid, list):
                        self.active_character.inventory_grid = [None] * 25
                    if slot_idx is not None and 0 <= slot_idx < len(self.active_character.inventory_grid):
                        self.active_character.inventory_grid[slot_idx] = None
                    else:
                        for i in range(len(self.active_character.inventory_grid)):
                            if self.active_character.inventory_grid[i] and self.active_character.inventory_grid[i].get("name") == it_name:
                                self.active_character.inventory_grid[i] = None
                                break
                    self.character_manager.save_characters()
                    if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                        self.stats_window.refresh_inventory_grid()
                    from common.protocol import make_update_full_sheet_request
                    self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
                    self.show_toast(f"Il Dungeon Master ha APPROVATO la rimozione di '{it_name}' dallo zaino.", title="Rimozione Approvata", toast_type="info")
                    return
                if not hasattr(self.active_character, "inventory_grid") or not isinstance(self.active_character.inventory_grid, list):
                    self.active_character.inventory_grid = [None] * 25
                if slot_idx is not None and 0 <= slot_idx < len(self.active_character.inventory_grid):
                    self.active_character.inventory_grid[slot_idx] = item
                else:
                    for i in range(len(self.active_character.inventory_grid)):
                        if self.active_character.inventory_grid[i] is None:
                            self.active_character.inventory_grid[i] = item
                            break
                self.character_manager.save_characters()
                if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                    self.stats_window.refresh_inventory_grid()
            self.show_toast(f"Il Dungeon Master ha APPROVATO '{it_name}'!\nL'oggetto è stato aggiunto al tuo inventario.", title="Oggetto Approvato!", toast_type="success")
        else:
            act_disp = "la rimozione di" if is_remove else "la richiesta per"
            msg = reason or f"La richiesta per {act_disp} '{it_name}' è stata respinta dal Master."
            self.show_toast(msg, title="Richiesta Respinta", toast_type="warning")

    def handle_campaign_starter_granted(self, data):
        full_sheet = data.get("full_sheet")
        if full_sheet and self.active_character:
            for k in ["inventory_grid", "spellbook", "spell_slots", "ac", "starting_kit_applied", "campaign_starter_received"]:
                if k in full_sheet:
                    setattr(self.active_character, k, full_sheet[k])
            self.character_manager.save_characters()
            if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                self.stats_window.load_data()
        elif self.active_character:
            items = data.get("items", [])
            if items:
                self.active_character.inventory_grid = items
                self.active_character.campaign_starter_received = True
                self.character_manager.save_characters()
                if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                    self.stats_window.load_data()
        self.log_to_chat("Hai ricevuto l'equipaggiamento iniziale della campagna dal Master!", "Globale", sender="Sistema", color="#2ECC71")

    def request_custom_spell(self, spell_dict):
        if self.is_connected:
            from common.protocol import make_custom_spell_request
            self.network.send(make_custom_spell_request(spell_dict))
            return True
        else:
            messagebox.showwarning("Non Connesso", "Devi essere connesso al server per richiedere l'approvazione di un incantesimo al Master!")
            return False

    def request_currency(self, coin, amount, reason=""):
        if self.is_connected:
            from common.protocol import make_currency_request
            self.network.send(make_currency_request(coin, amount, reason))
            return True
        else:
            messagebox.showwarning("Non Connesso", "Devi essere connesso per richiedere valuta al Master.")
            return False

    def request_item_approval(self, item, slot_idx=None):
        if self.is_connected:
            from common.protocol import make_item_approval_request
            self.network.send(make_item_approval_request(item, slot_idx))
            return True
        else:
            messagebox.showwarning("Non Connesso", "Devi essere connesso per richiedere l'approvazione di oggetti al Master.")
            return False

    def handle_audio_play(self, data):
        import webbrowser
        url = data.get("url")
        if url:
            webbrowser.open(url)
            self.log_to_chat("Stai ascoltando un audio avviato dal DM", "Globale", sender="Sistema", color="#99AAB5")

    def handle_audio_track_play(self, data):
        track_id = data.get("track_id")
        name = data.get("name", "Audio")
        ext = data.get("ext", ".mp3")
        channel = data.get("channel", "music")
        loop = data.get("loop", False)
        volume = float(data.get("volume", 0.8))
        if not track_id:
            return

        target_path = os.path.join(self.audio_cache_dir, f"{track_id}{ext}")
        if os.path.isfile(target_path):
            self.audio_manager.play(target_path, channel=channel, loop=loop, volume=volume, name=name)
            icon = "🎵" if channel == "music" else "💥"
            self.log_to_chat(f"In riproduzione: {icon} {name}", "Globale", sender="Audio", color="#1ABC9C")
        else:
            self._pending_play = {
                "track_id": track_id,
                "name": name,
                "channel": channel,
                "loop": loop,
                "volume": volume,
                "ext": ext
            }
            from common.protocol import make_audio_track_request
            self.network.send(make_audio_track_request(track_id))
            self.log_to_chat(f"Scaricamento traccia '{name}' dal server in corso...", "Globale", sender="Audio", color="#7289DA")

    def handle_audio_track_chunk(self, data):
        track_id = data.get("track_id")
        index = data.get("index", 0)
        total = data.get("total", 1)
        b64_data = data.get("data", "")
        ext = data.get("ext") or (self._pending_play.get("ext") if self._pending_play and self._pending_play.get("track_id") == track_id else ".mp3")

        if not track_id:
            return

        if track_id not in self._audio_downloads:
            self._audio_downloads[track_id] = {
                "total": total,
                "ext": ext,
                "chunks": {}
            }

        rec = self._audio_downloads[track_id]
        if ext and not rec.get("ext"):
            rec["ext"] = ext
        try:
            rec["chunks"][index] = base64.b64decode(b64_data)
        except Exception as e:
            print(f"[AUDIO] Errore decodifica chunk {index}: {e}")
            return

        if len(rec["chunks"]) == rec["total"]:
            target_path = os.path.join(self.audio_cache_dir, f"{track_id}{rec['ext']}")
            try:
                with open(target_path, "wb") as f:
                    for i in range(rec["total"]):
                        f.write(rec["chunks"][i])
            except Exception as e:
                print(f"[AUDIO] Errore salvataggio file in cache {target_path}: {e}")
            finally:
                if track_id in self._audio_downloads:
                    del self._audio_downloads[track_id]

            if self._pending_play and self._pending_play.get("track_id") == track_id:
                req = self._pending_play
                self._pending_play = None
                self.audio_manager.play(target_path, channel=req.get("channel", "music"), loop=req.get("loop", False), volume=req.get("volume", 0.8), name=req.get("name", "Audio"))
                icon = "🎵" if req.get("channel") == "music" else "💥"
                self.log_to_chat(f"In riproduzione: {icon} {req.get('name')}", "Globale", sender="Audio", color="#1ABC9C")

    def handle_audio_stop(self, data):
        channel = data.get("channel", "all")
        self.audio_manager.stop(channel)
        if self._pending_play:
            if channel == "all" or channel == self._pending_play.get("channel"):
                self._pending_play = None

    def handle_prompt_long_rest_vote(self, data):
        initiator = data.get("initiator", "Qualcuno")
        if messagebox.askyesno("Voto Riposo Lungo", f"{initiator} propone un Riposo Lungo. Questo resettera' slot, salute e dadi vita.\n\nSei d'accordo?"):
            self.network.send({"type": "LONG_REST_VOTE", "data": {"vote": True}})
        else:
            self.network.send({"type": "LONG_REST_VOTE", "data": {"vote": False}})

    def handle_do_long_rest(self, data):
        if self.active_character:
            self.active_character.long_rest()
            self.character_manager.update_character(self.active_character)
            from common.protocol import make_update_full_sheet_request
            self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
            self.show_toast("Il gruppo ha completato un Riposo Lungo. Hai recuperato le tue statistiche.", title="Riposo Lungo Completato", toast_type="success")
            if hasattr(self, "stats_window") and self.stats_window and self.stats_window.winfo_exists():
                self.stats_window.load_data()

    def handle_draw_broadcast(self, data):
        points = data.get("points", [])
        color = data.get("color", "red")
        if hasattr(self, "map_canvas"):
            self.map_canvas.draw_remote_line(points, color)

    def handle_clear_drawings_broadcast(self, data):
        if hasattr(self, "map_canvas") and self.map_canvas:
            self.map_canvas.clear_drawings()

    def toggle_whiteboard_pen(self):
        if not hasattr(self, "map_canvas") or not self.map_canvas: return
        is_active = self.map_canvas.toggle_pen_mode()
        if hasattr(self, "pen_btn"):
            self.pen_btn.config(style="Accent.TButton" if is_active else "Tool.TButton")
        self.show_toast("Modalità Penna Disegno: " + ("Attiva" if is_active else "Disattivata"), title="Lavagna", toast_type="info")

    def clear_whiteboard_drawings(self):
        from common.messagebox import messagebox
        if not messagebox.askyesno(_t("tool_clear_drawings"), "Cancellare tutti i disegni a mano libera dalla mappa?"):
            return
        if self.map_canvas:
            self.map_canvas.clear_drawings()
        if hasattr(self, "network") and self.network:
            from common.protocol import make_clear_drawings_request
            self.network.send(make_clear_drawings_request())
        self.show_toast("Disegni mappa cancellati", title="Lavagna", toast_type="info")

    def export_session_log(self):
        if not hasattr(self, "chat_display"):
            return
        log_text = self.chat_display.get("1.0", tk.END).strip()
        from common.messagebox import messagebox
        if not log_text:
            messagebox.showinfo(_t("export_log_title"), _t("export_log_empty"))
            return

        from tkinter import filedialog
        from datetime import datetime
        default_filename = f"Player_Session_Log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = filedialog.asksaveasfilename(
            title=_t("menu_export_session_log"),
            initialfile=default_filename,
            filetypes=[("Markdown (*.md)", "*.md"), ("HTML (*.html)", "*.html"), ("Text (*.txt)", "*.txt")]
        )
        if not filepath:
            return

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        char_name = self.character_manager.active_character.name if self.character_manager and self.character_manager.active_character else self.username

        if filepath.endswith(".html"):
            html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>{_t('export_log_title')} - {char_name}</title>
<style>
body {{ background-color: #121316; color: #E5E7EB; font-family: 'Segoe UI', Tahoma, sans-serif; padding: 24px; line-height: 1.6; }}
h1 {{ color: #F59E0B; border-bottom: 2px solid #D97706; padding-bottom: 8px; }}
.meta {{ color: #9CA3AF; font-size: 0.9em; margin-bottom: 20px; }}
.log-box {{ background-color: #1A1B1E; border: 1px solid #374151; border-radius: 8px; padding: 18px; white-space: pre-wrap; font-family: 'Consolas', monospace; }}
</style>
</head>
<body>
<h1>📜 {_t('export_log_title')} - {char_name}</h1>
<div class="meta">Esportato il: {now_str} • D&D OmniCompanion</div>
<div class="log-box">{log_text}</div>
</body>
</html>"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
        else:
            md_content = f"""# 📜 {_t('export_log_title')} - {char_name}
**Data Esportazione:** {now_str}
**Giocatore / Personaggio:** {char_name}
**Piattaforma:** D&D OmniCompanion

---

```
{log_text}
```
"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)

        messagebox.showinfo(_t("export_log_title"), _t("export_log_saved").format(path=filepath))

    def handle_ping_broadcast(self, data):
        if self.map_canvas:
            self.map_canvas.draw_ping(data.get("q"), data.get("r"), data.get("color", "red"))

    def handle_fow_update_broadcast(self, data):
        if not hasattr(self, 'local_map_data') or self.local_map_data is None:
            self.local_map_data = {}
        self.local_map_data["fow_revealed"] = data.get("fow_revealed", [])
        self.local_map_data["fow_draft"] = data.get("fow_draft", [])
        if "fow_enabled" in data:
            self.local_map_data["fow_enabled"] = bool(data.get("fow_enabled"))
        self.redraw_map_and_players()

    def handle_request_initiative(self, data):
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        win.title("Iniziativa")
        win.minsize(300, 200)
        from common.theme import apply_modern_window_style
        apply_modern_window_style(win)
        
        ttk.Label(win, text="Combattimento Iniziato!", font=("Georgia", 14, "bold"), foreground="#D4AF37").pack(pady=10)
        ttk.Label(win, text="Tira l'Iniziativa:").pack(pady=5)
        
        mod = getattr(self.active_character, 'initiative', 0) if self.active_character else 0
        ttk.Label(win, text=f"Il tuo modificatore è: {mod}").pack(pady=5)
        
        def roll():
            import random
            from common.protocol import make_submit_initiative
            roll_val = random.randint(1, 20)
            total = roll_val + mod
            self.network.send(make_submit_initiative(total))
            self.log_to_chat(f"Hai tirato iniziativa: {roll_val} + {mod} = {total}", "Globale", "orange")
            win.destroy()
            
        ttk.Button(win, text="Tira 1d20 + Iniziativa", command=roll, style='Primary.TButton').pack(pady=15)

    def handle_update_inspiration(self, data):
        has_insp = data.get("has_inspiration", True)
        if self.active_character:
            self.active_character.has_inspiration = has_insp
            self.character_manager.save_characters()
            if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                self.stats_window.set_inspiration(has_insp)
        if has_insp:
            self.log_to_chat("🌟 Hai ricevuto l'Ispirazione dal Dungeon Master!", "Globale", sender="Sistema", color="#FEE75C")
            self.show_toast("🌟 Hai ricevuto l'Ispirazione dal Dungeon Master!\nPuoi usarla per ottenere Vantaggio in un attacco o prova.", title="Ispirazione Assegnata", toast_type="gold")
        else:
            self.log_to_chat("☆ L'Ispirazione è stata consumata o rimossa.", "Globale", sender="Sistema", color="#99AAB5")

    def give_gold(self, target_name, amount):
        if not self.is_connected:
            self.show_toast("Devi essere connesso per donare oro.", title="Non Connesso", toast_type="warning")
            return
        if not self.active_character: return
        
        cur_gold = self.active_character.currency.get("MO", 0) if hasattr(self.active_character, "currency") else 0
        if amount > cur_gold:
            self.show_toast(f"Possiedi solo {cur_gold} MO.", title="Oro Insufficiente", toast_type="warning")
            return
            
        self.active_character.currency["MO"] -= amount
        self.character_manager.save_characters()
        from common.protocol import make_give_gold_request, make_update_full_sheet_request
        self.network.send(make_give_gold_request(target_name, amount))
        self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
        self.log_to_chat(f"Hai consegnato {amount} MO a {target_name}.", "Globale", sender="Sistema", color="#00B0F4")
        self.show_toast(f"Hai consegnato {amount} MO a {target_name}.", title="Oro Donato", toast_type="success")

    def handle_receive_gold(self, data):
        amount = data.get("amount", 0)
        sender = data.get("sender", "Il DM")
        if not self.active_character: return
        
        if not hasattr(self.active_character, "currency") or not isinstance(self.active_character.currency, dict):
            self.active_character.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
            
        self.active_character.currency["MO"] = self.active_character.currency.get("MO", 0) + amount
        
        self.character_manager.save_characters()
        from common.protocol import make_update_full_sheet_request
        self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
        
        if hasattr(self, "sheet_ui") and self.sheet_ui.winfo_exists():
            self.sheet_ui.load_data()
        elif hasattr(self, "stats_window") and self.stats_window and self.stats_window.winfo_exists():
            self.stats_window.load_data()
            
        self.show_toast(f"{sender} ti ha inviato {amount} MO!", title="Loot Ricevuto", toast_type="gold")
        self.log_to_chat(f"Hai ricevuto {amount} MO da {sender}.", "Globale", sender="Sistema", color="#2ECC71")

    def handle_receive_item(self, data):
        item = data.get("item")
        if not self.active_character or not item: return
        
        sender = item.pop("_sender", "Il DM")
        
        # Trova il primo slot libero nella griglia
        for i in range(len(self.active_character.inventory_grid)):
            if self.active_character.inventory_grid[i] is None:
                self.active_character.inventory_grid[i] = item
                self.character_manager.save_characters()
                self.show_toast(f"{sender} ti ha assegnato/inviato: {item['name']}", title="Oggetto Ricevuto", toast_type="gold")
                # Invia l'aggiornamento della scheda al server
                self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
                if hasattr(self, "stats_window") and self.stats_window and self.stats_window.winfo_exists():
                    self.stats_window.load_data()
                return
        
        self.show_toast(f"{sender} ha provato ad inviarti '{item['name']}' ma non hai spazio nello zaino!", title="Inventario Pieno", toast_type="warning")
        if sender and sender != self.name:
            # Rimbalza l'oggetto al mittente per evitarne la distruzione
            from common.protocol import make_give_item_request
            self.network.send(make_give_item_request(sender, item))

    def handle_chat_broadcast(self, data):
        sender, text, is_whisper=data.get('sender'), data.get('text'), data.get('is_whisper')
        if not is_whisper:
            self.log_to_chat(text, "Globale", sender=sender, color="#5865F2")
        else:
            tab_name=sender.replace("Tu -> ", "") if sender.startswith("Tu -> ") else sender
            prefix="Tu" if sender.startswith("Tu -> ") else sender
            self.create_chat_tab(tab_name)
            self.log_to_chat(text, tab_name, sender=prefix, color="#EB459E")
            self.log_to_chat(f"🔒 [Sussurro] {text}", "Globale", sender=sender, color="#EB459E")

    def handle_dice_roll(self, data):
        res = data.get('result', {})
        reason = data.get('reason')
        reason_text = f" ({reason})" if reason else ""
        player_name = data.get('player_name', 'Qualcuno')
        formula = data.get('formula', '')
        rolls = res.get('rolls', [])
        other_rolls = res.get('other_rolls', [])
        mod = res.get('modifier', 0)
        total = res.get('total', 0)

        is_crit = res.get('is_crit', False)
        is_fumble = res.get('is_fumble', False) or res.get('is_crit_fail', False)

        rolls_display = f"{rolls}"
        if other_rolls:
            rolls_display = f"{rolls} (scartato: {other_rolls})"

        mod_str = f" + {mod}" if mod >= 0 else f" - {abs(mod)}"
        crit_badge = ""
        chat_color = "#FEE75C"
        if is_crit:
            crit_badge = " 🌟 SUCCESSO CRITICO! (20 Naturale)"
            chat_color = "#2ECC71"
            self.show_toast(
                f"{player_name} ha ottenuto un 20 NATURALE su {reason or formula} (Totale: {total})!",
                title="🌟 Successo Critico!",
                toast_type="gold",
            )
        elif is_fumble:
            crit_badge = " 💀 FALLIMENTO CRITICO! (1 Naturale)"
            chat_color = "#ED4245"
            self.show_toast(
                f"{player_name} ha ottenuto un 1 NATURALE su {reason or formula} (Totale: {total})!",
                title="💀 Fallimento Critico!",
                toast_type="danger",
            )

        log_text = f"tira {formula}{reason_text}: {rolls_display}{mod_str} = {total}{crit_badge}"
        self.log_to_chat(log_text, "Globale", sender=player_name, color=chat_color)
    
    def open_private_chat_from_list(self, event):
        selected_indices=self.player_listbox.curselection()
        if not selected_indices: return
        display_text=self.player_listbox.get(selected_indices[0])
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip() if " (HP" in display_text else display_text.strip()
        if player_name == "DM": pass
        elif player_name == self.name: return # Non aprire chat con se stessi
        self.create_chat_tab(player_name)
        for i, tab_text in enumerate(self.notebook.tabs()):
            if self.notebook.tab(i, "text") == player_name: self.notebook.select(i); break
        self.entry.focus_set(); self.log_to_chat(f"Hai aperto una chat con {player_name}.", player_name, sender="Sistema", color="#99AAB5")

    def create_chat_tab(self, name):
        if name in self.chat_tabs: return
        tab_frame = ttk.Frame(self.notebook)
        text_widget = scrolledtext.ScrolledText(
            tab_frame, state='disabled', wrap=tk.WORD, height=8, 
            bg=SURFACE_COLOR, fg=TEXT_COLOR, borderwidth=0, highlightthickness=0, font=FONT_MAIN
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(tab_frame, text=name)
        self.chat_tabs[name] = text_widget
        
        # Configure tags for Dark Fantasy / Discord-like format
        text_widget.tag_config("timestamp", foreground=TEXT_MUTED, font=("Segoe UI", 8))
        text_widget.tag_config("sender", font=FONT_BOLD, foreground=ACCENT_GOLD)
        text_widget.tag_config("text", foreground=TEXT_COLOR, font=FONT_MAIN)

    def update_player_listbox(self):
        import tkinter as tk
        state = self.player_listbox.cget('state')
        if state == tk.DISABLED:
            self.player_listbox.config(state=tk.NORMAL)
            
        self.player_listbox.delete(0, tk.END)
        self.player_listbox.insert(tk.END, "DM")
        try:
            self.player_listbox.itemconfig(0, {'fg': '#DDA0DD'})
        except tk.TclError:
            pass
        
        # Includi tutti i giocatori per vedere l'ordine di iniziativa
        all_players = list(self.players_data.values())
        if not getattr(self, "combat_active", False):
            all_players = sorted(all_players, key=lambda x: x.get('initiative', 0), reverse=True)
            
        for i, p in enumerate(all_players):
            is_turn = getattr(self, "combat_active", False) and i == getattr(self, "turn_index", 0)
            prefix = "▶ " if is_turn else "  "
            display_text = f"{prefix}{p['name']} (HP: {p.get('hp', 10)}/{p.get('max_hp', 10)}) [Iniz: {p.get('initiative', 0)}]"
            conditions = p.get('conditions', [])
            if conditions:
                display_text += f" {{{', '.join(conditions)}}}"
            self.player_listbox.insert(tk.END, display_text)
            
            idx = i + 1
            if is_turn:
                self.player_listbox.itemconfig(idx, {'bg': '#FBC02D', 'fg': 'black'})
            elif p['name'] == self.name:
                self.player_listbox.itemconfig(idx, {'bg': '#1565C0', 'fg': 'white'})
            else:
                self.player_listbox.itemconfig(idx, {'bg': '#1E1E1E', 'fg': '#E0E0E0'})

    def log_to_chat(self, message, tab_name="Globale", sender="Sistema", color="white"):
        text_widget=self.chat_tabs.get(tab_name)
        if not text_widget: return
        text_widget.config(state='normal')
        
        import datetime
        timestamp = datetime.datetime.now().strftime("[%H:%M]")
        
        text_widget.insert(tk.END, f"{timestamp} ", "timestamp")
        
        sender_color = color if sender != "Sistema" else "#72767D"
        if sender_color not in text_widget.tag_names(): text_widget.tag_config(sender_color, foreground=sender_color, font=("Arial", 10, "bold"))
        
        text_widget.insert(tk.END, f"{sender}: ", sender_color)
        
        if "\n" in message:
            text_widget.insert(tk.END, message + "\n", "text")
        else:
            text_widget.insert(tk.END, message + "\n", color)
            
        text_widget.config(state='disabled')
        text_widget.see(tk.END)
        
    def send_chat_message(self, message_or_event=None):
        if isinstance(message_or_event, str):
            text = message_or_event.strip()
        else:
            text = self.entry.get().strip()
        if not text: return

        # Se offline e comando /manuale o /rule, rispondi localmente
        if any(text.lower().startswith(cmd) for cmd in ["/manuale", "/manual", "/regola", "/rule"]):
            if not getattr(self, "is_connected", False):
                parts = text.split(" ", 1)
                query = parts[1].strip() if len(parts) > 1 else ""
                from common.manuals_manager import ManualsManager
                mgr = ManualsManager()
                if not query:
                    reply = "📖 [MANUALI 5e] Sintassi: `/manuale <argomento>` (es. `/manuale concentrazione`, `/manuale sfinimento`)"
                else:
                    m = mgr.quick_lookup(query)
                    if m:
                        reply = f"📖 [{m.get('page_ref', '5e')}] {m.get('title')}:\n{m.get('summary')}"
                    else:
                        reply = f"📖 [MANUALI] Nessuna regola trovata per '{query}'."
                self.log_to_chat(reply, "Globale", sender="Manuali 5e", color="#00B0F4")
                if not isinstance(message_or_event, str):
                    self.entry.delete(0, tk.END)
                return

        if not getattr(self, "is_connected", False):
            self.show_toast("Non sei connesso al server.", toast_type="warning")
            return

        if text.lower().startswith("/roll ") or text.lower().startswith("/r "):
            formula = text.split(" ", 1)[1].strip()
            self.do_roll(formula, "Tiro Personalizzato")
            if not isinstance(message_or_event, str):
                self.entry.delete(0, tk.END)
            return

        if text.lower() in ["/tsmorte", "/deathsave", "/morte", "/ds"]:
            self.roll_death_save()
            if not isinstance(message_or_event, str):
                self.entry.delete(0, tk.END)
            return

        try: active_tab_name=self.notebook.tab(self.notebook.select(), "text")
        except tk.TclError: return
        if active_tab_name == "Globale": self.network.send(make_chat(text))
        else: self.network.send(make_whisper(active_tab_name, text))
        if not isinstance(message_or_event, str):
            self.entry.delete(0, tk.END)

    def roll_dice_dialog(self):
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        apply_modern_window_style(win)
        win.title("🎲 Tira Dadi")
        win.minsize(360, 270)

        header = tk.Frame(win, bg=SURFACE_COLOR, padx=12, pady=8)
        header.pack(fill=tk.X)
        tk.Label(header, text="🎲 TIRA I DADI (D&D 5e)", font=FONT_BOLD, fg=ACCENT_GOLD, bg=SURFACE_COLOR).pack(anchor="w")

        body = tk.Frame(win, bg=BG_COLOR, padx=14, pady=10)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(body, text="Formula Dado (es: 1d20+5, 2d6+3, 1d8):", font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_COLOR).pack(anchor="w", pady=(0, 2))
        formula_entry = ttk.Entry(body, font=("Georgia", 11))
        formula_entry.insert(0, "1d20")
        formula_entry.pack(fill=tk.X, pady=(0, 6))

        # Quick dice buttons
        dice_bar = tk.Frame(body, bg=BG_COLOR)
        dice_bar.pack(fill=tk.X, pady=(0, 8))
        def append_die(d):
            cur = formula_entry.get().strip()
            if not cur or cur == "1d20":
                formula_entry.delete(0, tk.END)
                formula_entry.insert(0, f"1{d}")
            else:
                formula_entry.insert(tk.END, f"+1{d}")

        for die in ["d4", "d6", "d8", "d10", "d12", "d20", "d100"]:
            ttk.Button(dice_bar, text=die, width=4, command=lambda d=die: append_die(d)).pack(side=tk.LEFT, padx=1)

        tk.Label(body, text="Motivo o Descrizione (facoltativo):", font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_COLOR).pack(anchor="w", pady=(0, 2))
        reason_entry = ttk.Entry(body)
        reason_entry.pack(fill=tk.X, pady=(0, 8))

        blind_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="🙈 Tiro Segreto al DM (Blind Roll)", variable=blind_var).pack(anchor="w", pady=(0, 10))

        btns_row = tk.Frame(win, bg=SURFACE_COLOR, padx=12, pady=10)
        btns_row.pack(fill=tk.X)

        def execute_roll():
            form = formula_entry.get().strip()
            if not form:
                return
            reas = reason_entry.get().strip()
            if blind_var.get():
                if self.is_connected:
                    from common.protocol import make_blind_roll_request
                    self.network.send(make_blind_roll_request(form, reas))
                    self.log_to_chat(f"🙈 [Tiro Segreto inviato al DM] Formula: {form} ({reas})", "Globale", sender="Tu", color="#A855F7")
                    self.show_toast(f"Tiro segreto ({form}) inviato al DM!", title="🙈 Tiro Segreto", toast_type="info")
                else:
                    self.do_roll(form, f"[Segreto Offline] {reas}")
            else:
                self.do_roll(form, reas)
            win.destroy()

        ttk.Button(btns_row, text="🎲 Lancia Dado", command=execute_roll, style="Gold.TButton").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btns_row, text="Annulla", command=win.destroy).pack(side=tk.RIGHT)
        formula_entry.focus_set()
        win.bind("<Return>", lambda e: execute_roll())

    def do_roll(self, formula, reason=""):
        if self.is_connected:
            self.network.send(make_roll_request(formula, reason))
        else:
            from common.dice import roll_dice
            if formula and formula != "0d0":
                try:
                    res = roll_dice(formula)
                    rolls_str = "+".join(map(str, res.get("rolls", [])))
                    total = res.get("total", 0)
                    msg = f"🎲 [Offline] {reason}: [{rolls_str}] -> Totale: {total} ({formula})"
                except Exception:
                    msg = f"🎲 [Offline] {reason}: {formula}"
            else:
                msg = f"🎲 [Offline] {reason}"
            self.log_to_chat(msg, "Globale", sender="Offline", color="#5C7CFA")

    def _on_key_c(self, event):
        if event.widget and isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox, scrolledtext.ScrolledText)):
            return
        self.open_stats_dialog()

    def _on_key_escape(self, event):
        if getattr(self, "stats_overlay_visible", False):
            self.hide_stats_overlay()
            return "break"
        return self.exit_fullscreen(event)

    def open_stats_dialog(self):
        # Se c'è già una finestra staccata aperta, portala in primo piano
        if getattr(self, "stats_detached_window", None) and self.stats_detached_window.winfo_exists():
            self.stats_detached_window.lift()
            self.stats_detached_window.focus_force()
            return

        # Se l'overlay centro-schermo è già visibile, agisce da toggle e lo chiude
        if getattr(self, "stats_overlay_visible", False):
            self.hide_stats_overlay()
            return

        self.show_stats_overlay()

    def show_stats_overlay(self):
        if not self.active_character:
            self.refresh_offline_characters()
            if not self.active_character:
                if messagebox.askyesno("Nessun Personaggio", "Non hai ancora nessun personaggio salvato. Vuoi crearne uno adesso con la procedura guidata?"):
                    self.open_create_character_dialog()
                return

        for child in self.center_overlay_frame.winfo_children():
            child.destroy()

        from client.character_sheet_ui import CharacterSheetFrame
        self.stats_sheet_frame = CharacterSheetFrame(
            self.center_overlay_frame,
            character=self.active_character,
            manager=self.character_manager,
            on_save_callback=self.on_character_saved,
            roll_callback=self.do_roll,
            trade_callback=self.do_trade,
            give_gold_callback=self.give_gold,
            attack_callback=self.on_attack_action,
            players_list_callback=self.get_player_names,
            custom_spell_request_callback=self.request_custom_spell,
            request_currency_callback=self.request_currency,
            request_item_callback=self.request_item_approval,
            is_connected=self.is_connected,
            request_journal_approval_callback=self.request_journal_approval,
            on_close_callback=self.hide_stats_overlay,
            on_detach_callback=self.detach_character_sheet,
            is_overlay=True,
            long_rest_callback=self.request_long_rest,
            network=getattr(self, "network", None)
        )
        self.stats_sheet_frame.pack(fill=tk.BOTH, expand=True)
        self.stats_window = self.stats_sheet_frame

        self.center_overlay_frame.place(relx=0.01, rely=0.01, relwidth=0.98, relheight=0.98)
        self.center_overlay_frame.lift()
        self.stats_overlay_visible = True

    def hide_stats_overlay(self, save=False):
        if getattr(self, "_hiding_stats_overlay", False):
            return
        self._hiding_stats_overlay = True
        try:
            if save and hasattr(self, 'stats_sheet_frame') and self.stats_sheet_frame:
                try:
                    if self.stats_sheet_frame.winfo_exists():
                        self.stats_sheet_frame.save_character(close_after=False)
                except Exception:
                    pass
            self.center_overlay_frame.place_forget()
            self.stats_overlay_visible = False
        finally:
            self._hiding_stats_overlay = False

    def detach_character_sheet(self):
        self.hide_stats_overlay(save=True)
        from client.character_sheet_ui import CharacterSheetUI
        self.stats_detached_window = CharacterSheetUI(
            self.master,
            character=self.active_character,
            manager=self.character_manager,
            on_save_callback=self.on_character_saved,
            roll_callback=self.do_roll,
            trade_callback=self.do_trade,
            give_gold_callback=self.give_gold,
            attack_callback=self.on_attack_action,
            players_list_callback=self.get_player_names,
            custom_spell_request_callback=self.request_custom_spell,
            request_currency_callback=self.request_currency,
            request_item_callback=self.request_item_approval,
            is_connected=self.is_connected,
            request_journal_approval_callback=self.request_journal_approval,
            on_dock_callback=self.dock_character_sheet,
            long_rest_callback=self.request_long_rest,
            network=getattr(self, "network", None)
        )
        self.stats_window = self.stats_detached_window

    def dock_character_sheet(self):
        if getattr(self, "stats_detached_window", None):
            try:
                if self.stats_detached_window.winfo_exists():
                    self.stats_detached_window.destroy()
            except Exception:
                pass
            self.stats_detached_window = None
        self.show_stats_overlay()

    def do_trade(self, item, target_name):
        if self.is_connected:
            self.network.send(make_give_item_request(target_name, item))
            if self.active_character:
                from common.protocol import make_update_full_sheet_request
                self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
            self.log_to_chat(f"Hai inviato l'oggetto '{item.get('name')}' a {target_name}.", "Globale", sender="Sistema", color="#00B0F4")

    def get_player_names(self):
        return [p for p in self.players_data.keys() if p != self.name]

    def handle_prompt_save(self, data):
        stat = data.get("stat")
        dc = data.get("dc")
        damage_formula = data.get("damage_formula")
        half_on_success = data.get("half_on_success")
        source_name = data.get("source_name")
        damage_type = data.get("damage_type", "Fuoco")
        
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        win.title("Tiro Salvezza Richiesto!")
        win.minsize(350, 250)
        apply_modern_window_style(win)
        
        ttk.Label(win, text=f"{source_name} richiede un TS!", font=("Georgia", 12, "bold"), foreground="#D4AF37").pack(pady=(10, 5))
        ttk.Label(win, text=f"Statistica: {stat} | CD: {dc}").pack(pady=5)
        
        if damage_formula:
            ttk.Label(win, text=f"Danno potenziale: {damage_formula}").pack()
            
        def do_roll():
            from common.dice import roll_dice
            mod = 0
            if self.active_character:
                if hasattr(self.active_character, "get_effective_save_bonus"):
                    mod = self.active_character.get_effective_save_bonus(stat)
                else:
                    attr = self.active_character.attributes
                    if stat in attr:
                        mod = (int(attr[stat]) - 10) // 2
                    
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            res = roll_dice(f"1d20{mod_str}")
            
            is_crit = res.get("is_crit", res["rolls"][0] == 20)
            is_fail = res.get("is_fumble", res["rolls"][0] == 1)
            
            if is_crit:
                self.show_toast(
                    f"20 NATURALE sul Tiro Salvezza su {stat} (Totale: {res['total']})! Successo Automatico!",
                    title="🌟 TS Critico!",
                    toast_type="gold",
                )
            elif is_fail:
                self.show_toast(
                    f"1 NATURALE sul Tiro Salvezza su {stat} (Totale: {res['total']})! Fallimento Critico!",
                    title="💀 TS Fallimento Critico!",
                    toast_type="danger",
                )
            
            from common.protocol import make_save_result
            self.network.send(make_save_result(stat, res["total"], is_crit, is_fail, dc, damage_formula, half_on_success, source_name, damage_type=damage_type))
            win.destroy()
            
        ttk.Button(win, text=f"Tira Salvezza ({stat})", command=do_roll, style="Danger.TButton").pack(pady=20)

    def on_character_saved(self, char):
        self.active_character = char
        self.name = char.name
        if hasattr(self, 'active_character_var'):
            self.active_character_var.set(char.name)
        self.update_hero_summary_card()
        if self.is_connected:
            self.network.send(make_update_stats_request(char.hp_current, char.hp_max, char.initiative, getattr(char, "conditions", [])))
            self.network.send(make_update_full_sheet_request(char.to_dict()))

    def refresh_offline_characters(self):
        """Carica e aggiorna la lista dei personaggi locali nell'interfaccia client (anche offline)."""
        if not hasattr(self, 'character_manager') or not self.character_manager:
            self.character_manager = CharacterManager()
        self.character_manager.load_characters()
        char_names = [c.name for c in self.character_manager.characters]
        
        if hasattr(self, 'active_character_combo'):
            self.active_character_combo['values'] = char_names
            current_val = self.active_character_var.get()
            if char_names:
                if not current_val or current_val not in char_names:
                    target_char = self.active_character or self.character_manager.characters[0]
                    self.active_character = target_char
                    self.name = target_char.name
                    self.active_character_var.set(target_char.name)
            else:
                self.active_character_var.set("")
                self.active_character = None
                self.name = None
        self.update_hero_summary_card()

    def open_character_manager_dialog(self):
        """Apre il pannello completo di Gestione Personaggi (Offline)."""
        from client.character_manager_ui import CharacterManagerDialog
        def on_selected(char):
            self.set_active_character_from_manager(char)
        dlg = CharacterManagerDialog(self.master, manager=self.character_manager, on_select_callback=on_selected)
        self.master.wait_window(dlg)
        self.refresh_offline_characters()

    def open_create_character_dialog(self):
        """Apre il wizard guidato di creazione del personaggio (Offline)."""
        from client.character_creation_wizard import CharacterCreationWizard
        def on_complete(new_char):
            self.refresh_offline_characters()
            if new_char:
                self.set_active_character_from_manager(new_char)
        dlg = CharacterCreationWizard(self.master, self.character_manager, on_complete_callback=on_complete)
        self.master.wait_window(dlg)

    def create_manual_character(self):
        """Crea un personaggio vuoto ed apre direttamente la scheda PG offline."""
        from client.character_manager import Character
        new_char = Character(name="Nuovo Eroe")
        self.character_manager.add_character(new_char)
        self.refresh_offline_characters()
        self.set_active_character_from_manager(new_char)
        self.open_stats_dialog()

    def set_active_character_from_manager(self, char):
        """Imposta il personaggio attivo selezionato dal manager e aggiorna la UI."""
        if not char: return
        self.active_character = char
        self.name = char.name
        if hasattr(self, 'active_character_var'):
            self.active_character_var.set(char.name)
        if getattr(self, "map_canvas", None):
            self.map_canvas.player_name = char.name
            self.map_canvas.redraw()
        self.update_hero_summary_card()
        if self.is_connected:
            self.network.send(make_update_stats_request(char.hp_current, char.hp_max, char.initiative, getattr(char, "conditions", [])))
            self.network.send(make_update_full_sheet_request(char.to_dict()))

    def open_srd_compendium(self):
        try:
            from server.srd_importer import SRDImportDialog
            win = SRDImportDialog(self.master, on_import_callback=None, is_dm=False)
            win.grab_set()
        except ImportError as e:
            messagebox.showerror("Errore", f"Impossibile aprire il Compendio: {e}")

if __name__ == "__main__":
    root=tk.Tk()
    ClientGUI(root)
    root.mainloop()
