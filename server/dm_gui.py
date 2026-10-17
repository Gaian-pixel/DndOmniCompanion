# dm_server.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import socket
import threading
import queue
import tkinter as tk
import json
import base64
import os
from common.messagebox import messagebox
from tkinter import filedialog, ttk, scrolledtext, simpledialog
from PIL import Image, ImageTk

from common.protocol import *
from common.theme import (
    setup_theme, apply_modern_window_style, 
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, BORDER_COLOR,
    TEXT_COLOR, TEXT_MUTED, TEXT_DARK,
    ACCENT_GOLD, ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE,
    FONT_MAIN, FONT_TITLE, FONT_HEADER, FONT_BOLD, FONT_SMALL
)
from server.commands import command_handlers
from common.game_state import GameState, Player
from server.map_editor import MapEditorWindow
from server.map_downloader import MapDownloaderDialog
from .network import Server
from common.hex_utils import Hex
from common.network_utils import send_message, receive_message, broadcast
from components.ui_components import HexMapCanvas, ToolTip, show_toast
from client.voice_client import VoiceClient
from common.i18n import (
    _t, get_language, set_language, register_language_listener, unregister_language_listener,
    translate_weather, translate_period,
    get_distance_unit, set_distance_unit, register_unit_listener, unregister_unit_listener
)
from server.dm_dialogs import (
    TextHandoutDialog,
    CustomNPCDialog,
    DMPlayerSheetViewer,
    CampaignStarterKitDialog
)
from common.audio_player import AudioManager
from server.dm_bestiary_panel import DMBestiaryPanel
from server.dm_soundboard_panel import DMSoundboardPanel

class DM_GUI:
    def __init__(self, master, initial_campaign=None):
        self.master = master; self.master.title("Dungeon Master - Server")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.initial_campaign = initial_campaign
        self.audio_manager = AudioManager()
        self.gui_queue=queue.Queue()
        self.server=Server('', 5000, self.gui_queue)
        self.map_canvas = None # Il nostro nuovo componente
        self.notebook = None
        self.chat_tabs = {}
        self.default_font = ("Georgia", 10)
        setup_theme(self.master)
        self.setup_gui()
        
        # Se avviato con una campagna preparata, applicala immediatamente
        if self.initial_campaign:
            self.initial_campaign.apply_to_game_state(self.server.game_state)
            if hasattr(self, "lbl_campaign_name"):
                self.lbl_campaign_name.config(text=f"🏰 Campagna: {self.initial_campaign.name}")
            if self.server.game_state.current_map:
                self.fow_enabled_var.set(self.server.game_state.current_map.get("fow_enabled", False))
                self.redraw_map_and_players()
            self.log_to_chat(f"[SISTEMA] Campagna '{self.initial_campaign.name}' applicata con successo.")

            
        self.server_thread=threading.Thread(target=self.server.start, daemon=True); self.server_thread.start()
        self.voice_client = VoiceClient("127.0.0.1", 53912)
        self.voice_client.start()
        register_language_listener(self.on_language_changed)
        register_unit_listener(self.on_unit_changed)
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
            self._update_map_scale_pill()
            if self.map_canvas:
                self.map_canvas.redraw()

    def setup_menubar(self):
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        self.main_menubar = menubar
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=_t("menu_new_campaign"), command=self.open_new_campaign_dialog)
        file_menu.add_command(label=_t("menu_load_campaign"), command=self.open_load_campaign_dialog)
        file_menu.add_command(label=_t("menu_edit_active_campaign"), command=self.open_campaign_editor_dialog)
        file_menu.add_separator()
        file_menu.add_command(label=_t("menu_load_map"), command=self.load_map_from_file)
        file_menu.add_separator()
        file_menu.add_command(label=_t("menu_save_session"), command=self.save_session)
        file_menu.add_command(label=_t("menu_load_session"), command=self.load_session)
        file_menu.add_separator()
        file_menu.add_command(label=_t("menu_export_session_log"), command=self.export_session_log)
        file_menu.add_separator()
        file_menu.add_command(label=_t("menu_exit"), command=self.on_closing)
        menubar.add_cascade(label=_t("menu_file"), menu=file_menu)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label=_t("menu_new_campaign"), command=self.open_campaign_editor_dialog)
        tools_menu.add_command(label=_t("menu_loot_gen"), command=self.open_loot_generator_dialog)
        tools_menu.add_command(label=_t("menu_npc_gen"), command=self.open_random_npc_dialog)
        tools_menu.add_command(label=_t("menu_map_editor"), command=self.open_map_editor)
        tools_menu.add_command(label=_t("menu_share_image"), command=self.share_image_handout)
        tools_menu.add_command(label=_t("menu_share_text"), command=self.share_text_handout)
        tools_menu.add_command(label=_t("menu_download_maps"), command=self.open_map_downloader)
        tools_menu.add_command(label=_t("menu_srd_compendium"), command=self.open_srd_importer)
        tools_menu.add_command(label=_t("tool_command_palette"), command=self.open_command_palette)
        tools_menu.add_command(label=_t("menu_manuals"), command=self.open_manuals_dialog)
        tools_menu.add_command(label=_t("menu_travel_panel"), command=self.open_travel_panel)
        tools_menu.add_command(label=_t("menu_starter_pack"), command=self.open_campaign_starter_kit_dialog)
        menubar.add_cascade(label=_t("menu_tools"), menu=tools_menu)

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
        self.master.title(f"{_t('app_title')} • Dungeon Master")
        self.setup_menubar()

        # Aggiorna tab del notebook destro
        if hasattr(self, 'right_notebook'):
            try:
                self.right_notebook.tab(0, text=_t("tab_chat_log"))
                self.right_notebook.tab(1, text=_t("tab_party_initiative"))
                self.right_notebook.tab(2, text=_t("tab_world"))
                self.right_notebook.tab(3, text=_t("tab_audio_sfx"))
            except Exception:
                pass
        
        if hasattr(self, 'notebook') and hasattr(self, 'tab_bestiario'):
            try:
                self.notebook.tab(self.tab_bestiario, text=_t("tab_bestiary"))
            except Exception:
                pass

        # Aggiorna Bestiario
        if hasattr(self, 'lbl_bestiary_header'):
            self.lbl_bestiary_header.config(text=_t("lbl_bestiary_header"))
        if hasattr(self, 'btn_bestiary_search'):
            self.btn_bestiary_search.config(text=_t("search"))
        if hasattr(self, 'btn_bestiary_spawn'):
            self.btn_bestiary_spawn.config(text=_t("btn_spawn_on_map"))
        if hasattr(self, 'btn_bestiary_full'):
            self.btn_bestiary_full.config(text=_t("btn_full_sheet"))

        # Aggiorna Chat e Voice
        if hasattr(self, 'btn_dm_chat_send'):
            self.btn_dm_chat_send.config(text=_t("btn_send"))
        if hasattr(self, 'btn_dm_chat_dice'):
            self.btn_dm_chat_dice.config(text=_t("btn_dice"))
        if hasattr(self, 'voice_status_lbl'):
            self.voice_status_lbl.config(text=_t("voice_server_active"))

        # Aggiorna Controlli Combattimento
        if hasattr(self, 'lbl_combatants_hdr'):
            self.lbl_combatants_hdr.config(text=_t("dm_combatants_header"))
        if hasattr(self, 'lbl_round'):
            curr_rnd = getattr(self.server.game_state, 'round_number', 1) if hasattr(self, 'server') and hasattr(self.server, 'game_state') else 1
            self.lbl_round.config(text=_t("lbl_round_num", round=curr_rnd))
        if hasattr(self, 'btn_prev_turn'):
            self.btn_prev_turn.config(text=_t("btn_prev_turn"))
        if hasattr(self, 'btn_next_turn'):
            self.btn_next_turn.config(text=_t("btn_next_turn"))
        if hasattr(self, 'btn_hide_reveal'):
            self.btn_hide_reveal.config(text=_t("btn_hide_reveal"))
        if hasattr(self, 'npc_actions_frame'):
            self.npc_actions_frame.config(text=_t("npc_actions_header"))
        if hasattr(self, 'btn_combat'):
            is_combat = getattr(self.server.game_state, 'combat_active', False) if hasattr(self, 'server') and hasattr(self.server, 'game_state') else False
            self.btn_combat.config(text=_t("btn_start_combat") if not is_combat else _t("btn_end_combat"))
        if hasattr(self, 'btn_campaign_encounter'):
            self.btn_campaign_encounter.config(text=_t("btn_deploy_prepared"))
        if hasattr(self, 'btn_mass_npc_initiative'):
            self.btn_mass_npc_initiative.config(text=_t("btn_roll_all_npcs"))
        if hasattr(self, 'btn_spawn_png'):
            self.btn_spawn_png.config(text=_t("btn_spawn_png"))
        if hasattr(self, 'btn_add_npc'):
            self.btn_add_npc.config(text=_t("btn_add_manual_npc"))
        if hasattr(self, 'btn_split_loot'):
            self.btn_split_loot.config(text=_t("btn_split_loot"))

        # Aggiorna Barra Mappa e Controlli FoW
        if hasattr(self, 'lbl_map_title'):
            self.lbl_map_title.config(text=_t("dm_tactical_map"))
        if hasattr(self, 'lbl_fow_tool'):
            self.lbl_fow_tool.config(text=_t("fow_tool_label"))
        if hasattr(self, 'map_tool_combo'):
            self.map_tool_combo['values'] = (_t("fow_mode_move"), _t("fow_mode_erase"), _t("fow_mode_draw"))
            curr_mode = self.fow_mode_var.get()
            if curr_mode in ("Cancella Nebbia", "Erase Fog", _t("fow_mode_erase")):
                self.fow_mode_var.set(_t("fow_mode_erase"))
            elif curr_mode in ("Disegna Nebbia", "Draw Fog", _t("fow_mode_draw")):
                self.fow_mode_var.set(_t("fow_mode_draw"))
            else:
                self.fow_mode_var.set(_t("fow_mode_move"))
        if hasattr(self, 'chk_player_view'):
            self.chk_player_view.config(text=_t("fow_player_view"))
        if hasattr(self, 'btn_send_fow'):
            self.btn_send_fow.config(text=_t("fow_send_btn"))
        if hasattr(self, 'fow_options_btn'):
            self.fow_options_btn.config(text=_t("fow_options_btn"))
            self.setup_fow_options_menu()

        # Aggiorna Tab Mondo
        if hasattr(self, 'btn_encounter_builder'):
            self.btn_encounter_builder.config(text="Encounter Builder")
        if hasattr(self, 'btn_switch_scene'):
            self.btn_switch_scene.config(text=_t("btn_switch_scene"))
        if hasattr(self, 'lbl_time_mgmt'):
            self.lbl_time_mgmt.config(text=_t("time_mgmt_header"))
        if hasattr(self, 'btn_add_1h'):
            self.btn_add_1h.config(text=_t("time_add_1h"))
        if hasattr(self, 'btn_add_8h'):
            self.btn_add_8h.config(text=_t("time_add_8h"))
        if hasattr(self, 'btn_add_1d'):
            self.btn_add_1d.config(text=_t("time_add_1d"))
        if hasattr(self, 'btn_calendar'):
            self.btn_calendar.config(text=_t("btn_open_calendar"))
        if hasattr(self, 'btn_quests'):
            self.btn_quests.config(text=_t("btn_open_quests"))
        if hasattr(self, 'btn_shops'):
            self.btn_shops.config(text=_t("btn_open_shops"))
        if hasattr(self, 'btn_travel'):
            self.btn_travel.config(text=_t("btn_travel_panel"))
        if hasattr(self, 'btn_world_manuals'):
            self.btn_world_manuals.config(text=_t("btn_manuals"))
        if hasattr(self, 'lbl_weather_hdr'):
            self.lbl_weather_hdr.config(text=_t("weather_header"))
        if hasattr(self, 'weather_combo'):
            self.weather_combo['values'] = [_t("weather_clear"), _t("weather_rain"), _t("weather_storm"), _t("weather_snow"), _t("weather_fog")]

        # Aggiorna Tab Audio
        if hasattr(self, 'lbl_audio_lib'):
            self.lbl_audio_lib.config(text=_t("audio_library_header"))
        if hasattr(self, 'lbl_audio_desc'):
            self.lbl_audio_desc.config(text=_t("audio_library_desc"))
        if hasattr(self, 'btn_import_audio'):
            self.btn_import_audio.config(text=_t("audio_upload_btn"))
        if hasattr(self, 'audio_tree'):
            try:
                self.audio_tree.heading("Nome", text=_t("audio_col_name"))
                self.audio_tree.heading("Tipo", text=_t("audio_col_type"))
                self.audio_tree.heading("Durata", text=_t("audio_col_duration"))
            except Exception:
                pass

        # Aggiorna Menu Contestuale
        if hasattr(self, 'setup_player_context_menu'):
            self.setup_player_context_menu()

        self.update_state()

    def setup_fow_options_menu(self):
        if not hasattr(self, 'fow_options_btn'):
            return
        self.fow_options_menu = tk.Menu(self.fow_options_btn, tearoff=0)
        self.fow_options_btn["menu"] = self.fow_options_menu
        self.fow_options_menu.add_checkbutton(label=_t("fow_menu_enable"), variable=self.fow_enabled_var, command=self.toggle_fow)
        self.fow_options_menu.add_separator()
        self.fow_options_menu.add_command(label=_t("fow_menu_hide_all"), command=self.hide_all_fow)
        self.fow_options_menu.add_command(label=_t("fow_menu_reveal_all"), command=self.reveal_all_fow)

    def setup_player_context_menu(self):
        self.player_menu = tk.Menu(
            self.master, tearoff=0,
            bg=SURFACE_COLOR, fg=TEXT_COLOR,
            activebackground=ACCENT_GOLD, activeforeground=TEXT_DARK,
            font=self.default_font
        )
        self.player_menu.add_command(label=_t("ctx_view_sheet"), command=self.view_player_sheet)
        self.player_menu.add_command(label=_t("ctx_assign_item"), command=self.open_assign_item_dialog)
        self.player_menu.add_command(label=_t("ctx_modify_hp"), command=self.open_modify_hp_dialog)
        self.player_menu.add_command(label=_t("ctx_modify_conditions"), command=self.open_conditions_dialog)
        self.player_menu.add_command(label=_t("ctx_execute_action"), command=self.open_action_dialog)
        self.player_menu.add_command(label=_t("ctx_set_aura"), command=self.open_aura_dialog)
        self.player_menu.add_command(label=_t("ctx_light_source"), command=self.open_light_source_dialog)
        self.player_menu.add_command(label=_t("ctx_config_boss"), command=self.open_boss_config_dialog)
        self.player_menu.add_command(label=_t("ctx_spend_legendary"), command=self.open_spend_legendary_action_dialog)
        self.player_menu.add_command(label=_t("ctx_set_owner"), command=self.open_set_owner_dialog)
        self.player_menu.add_command(label=_t("ctx_open_private_chat"), command=self.open_private_chat_from_context)
        self.player_menu.add_separator()
        size_menu = tk.Menu(
            self.player_menu, tearoff=0,
            bg=SURFACE_COLOR, fg=TEXT_COLOR,
            activebackground=ACCENT_GOLD, activeforeground=TEXT_DARK,
            font=self.default_font
        )
        size_menu.add_command(label=_t("size_tiny"), command=lambda: self.set_selected_player_size("tiny"))
        size_menu.add_command(label=_t("size_small"), command=lambda: self.set_selected_player_size("small"))
        size_menu.add_command(label=_t("size_medium"), command=lambda: self.set_selected_player_size("medium"))
        size_menu.add_command(label=_t("size_large"), command=lambda: self.set_selected_player_size("large"))
        size_menu.add_command(label=_t("size_huge"), command=lambda: self.set_selected_player_size("huge"))
        size_menu.add_command(label=_t("size_gargantuan"), command=lambda: self.set_selected_player_size("gargantuan"))
        self.player_menu.add_cascade(label=_t("token_size_menu"), menu=size_menu)
        self.player_menu.add_command(label=_t("ctx_toggle_gm_layer"), command=self.toggle_selected_player_gm_layer)
        self.player_menu.add_separator()
        self.player_menu.add_command(label=_t("ctx_toggle_combat"), command=self.toggle_player_combat_status)
        self.player_menu.add_command(label=_t("ctx_toggle_party"), command=self.toggle_party_status)
        self.player_menu.add_command(label=_t("ctx_toggle_inspiration"), command=self.toggle_inspiration)
        self.player_menu.add_separator()
        self.player_menu.add_command(label=_t("ctx_remove_entity"), command=self.remove_entity)

    def setup_gui(self):
        # 1. MENU BAR GLOBALE
        self.setup_menubar()
        
        # 2. LAYOUT PRINCIPALE (3 Colonne: Sinistra=Toolbar, Centro=Mappa, Destra=Notebook)
        main_frame = ttk.Frame(self.master, padding="10 10 10 10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=0, minsize=360)
        main_frame.rowconfigure(0, weight=1)
        
        # --- COLONNA 0: LEFT TOOLBAR (Strumenti Mappa Eleganti) ---
        left_toolbar = tk.Frame(main_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=6)
        left_toolbar.grid(row=0, column=0, sticky="ns", padx=(0, 6))
        
        btn1 = ttk.Button(left_toolbar, text="👆", width=3, style="Tool.TButton", command=lambda: self.map_canvas.center_view() if self.map_canvas else None)
        btn1.pack(pady=3)
        ToolTip(btn1, lambda: _t("tool_center_map"))

        btn_zin = ttk.Button(left_toolbar, text="➕", width=3, style="Tool.TButton", command=lambda: self.map_canvas.zoom_in() if self.map_canvas else None)
        btn_zin.pack(pady=3)
        ToolTip(btn_zin, lambda: _t("tool_zoom_in"))

        btn_zout = ttk.Button(left_toolbar, text="➖", width=3, style="Tool.TButton", command=lambda: self.map_canvas.zoom_out() if self.map_canvas else None)
        btn_zout.pack(pady=3)
        ToolTip(btn_zout, lambda: _t("tool_zoom_out"))
        
        self.btn_fow_tool = ttk.Button(left_toolbar, text="☁️", width=3, style="Tool.TButton", command=self.toggle_fow_quick_tool)
        self.btn_fow_tool.pack(pady=3)
        ToolTip(self.btn_fow_tool, lambda: _t("tool_fog_of_war"))
        
        self.btn_ruler = ttk.Button(left_toolbar, text="📏", width=3, style="Tool.TButton", command=self.toggle_ruler_mode)
        self.btn_ruler.pack(pady=3)
        ToolTip(self.btn_ruler, lambda: _t("tool_measure"))
        
        self.btn_aoe = ttk.Button(left_toolbar, text="💥", width=3, style="Tool.TButton", command=self.open_aoe_dialog)
        self.btn_aoe.pack(pady=3)
        ToolTip(self.btn_aoe, lambda: _t("tool_aoe"))
        
        self.btn_clear_aoe = ttk.Button(left_toolbar, text="🧹", width=3, style="Tool.TButton", command=self.clear_aoes)
        self.btn_clear_aoe.pack(pady=3)
        ToolTip(self.btn_clear_aoe, lambda: _t("tool_clear_aoe"))

        self.btn_pen = ttk.Button(left_toolbar, text="✏️", width=3, style="Tool.TButton", command=self.toggle_whiteboard_pen)
        self.btn_pen.pack(pady=3)
        ToolTip(self.btn_pen, lambda: _t("tool_pen"))

        self.btn_clear_drawings = ttk.Button(left_toolbar, text="🗑️", width=3, style="Tool.TButton", command=self.clear_whiteboard_drawings)
        self.btn_clear_drawings.pack(pady=3)
        ToolTip(self.btn_clear_drawings, lambda: _t("tool_clear_drawings"))
        
        # Separatore sottile
        tk.Frame(left_toolbar, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=6)
        
        self.teleport_mode_var = tk.BooleanVar(value=False)
        btn_teleport = ttk.Checkbutton(left_toolbar, text="🚪", width=3, style="Toolbutton", variable=self.teleport_mode_var)
        btn_teleport.pack(pady=3)
        ToolTip(btn_teleport, lambda: _t("tool_teleport"))

        btn_manuals = ttk.Button(left_toolbar, text="📖", width=3, style="Tool.TButton", command=self.open_manuals_dialog)
        btn_manuals.pack(pady=3)
        ToolTip(btn_manuals, lambda: _t("tool_manuals"))

        btn_palette = ttk.Button(left_toolbar, text="🔍", width=3, style="Tool.TButton", command=self.open_command_palette)
        btn_palette.pack(pady=3)
        ToolTip(btn_palette, lambda: _t("tool_command_palette"))
        
        # --- COLONNA 1: MAPPA (Viewport & Status Header) ---
        map_outer_frame = ttk.Frame(main_frame)
        map_outer_frame.grid(row=0, column=1, sticky="nsew", padx=4)
        
        # Header Mappa con Pillole di Stato & Controlli Nebbia
        map_top_bar = tk.Frame(map_outer_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=5)
        map_top_bar.pack(fill=tk.X, pady=(0, 6))
        
        # Titolo mappa / VTT
        self.lbl_map_title = tk.Label(map_top_bar, text=_t("dm_tactical_map"), font=FONT_HEADER, bg=SURFACE_COLOR, fg=ACCENT_GOLD)
        self.lbl_map_title.pack(side=tk.LEFT, padx=(2, 10))
        
        # Status Pills (Orario, Meteo, Combattimento)
        pills_frame = tk.Frame(map_top_bar, bg=SURFACE_COLOR)
        pills_frame.pack(side=tk.LEFT, padx=5)
        
        self.top_status_time_lbl = tk.Label(
            pills_frame, text=f"☀️ 08:00 ({_t('period_morning')})", font=FONT_SMALL, 
            bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, padx=6, pady=2,
            highlightbackground=BORDER_COLOR, highlightthickness=1
        )
        self.top_status_time_lbl.pack(side=tk.LEFT, padx=3)
        
        self.top_status_weather_lbl = tk.Label(
            pills_frame, text=f"🌤️ {_t('weather_clear')}", font=FONT_SMALL, 
            bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, padx=6, pady=2,
            highlightbackground=BORDER_COLOR, highlightthickness=1
        )
        self.top_status_weather_lbl.pack(side=tk.LEFT, padx=3)
        
        self.top_status_combat_lbl = tk.Label(
            pills_frame, text=_t("status_exploration"), font=FONT_SMALL, 
            bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, padx=6, pady=2,
            highlightbackground=BORDER_COLOR, highlightthickness=1
        )
        self.top_status_combat_lbl.pack(side=tk.LEFT, padx=3)

        self.top_status_scale_lbl = tk.Label(
            pills_frame, text="🗺️ 1 hex = 5 ft", font=FONT_SMALL,
            bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD, padx=6, pady=2,
            highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2"
        )
        self.top_status_scale_lbl.pack(side=tk.LEFT, padx=3)
        self.top_status_scale_lbl.bind("<Button-1>", self._show_map_scale_menu)
        ToolTip(self.top_status_scale_lbl, "Scala Mappa Attiva (Clicca per cambiare scala del righello)")

        self.top_status_grid_lbl = tk.Label(
            pills_frame, text="🌐 Griglia: Esagonale", font=FONT_SMALL,
            bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD, padx=6, pady=2,
            highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2"
        )
        self.top_status_grid_lbl.pack(side=tk.LEFT, padx=3)
        self.top_status_grid_lbl.bind("<Button-1>", self._show_grid_type_menu)
        ToolTip(self.top_status_grid_lbl, lambda: _t("grid_type_menu"))
        
        # Toolbar Fog of War a destra
        fow_toolbar = tk.Frame(map_top_bar, bg=SURFACE_COLOR)
        fow_toolbar.pack(side=tk.RIGHT, padx=2)
        
        self.fow_enabled_var = tk.BooleanVar(value=False)
        self.fow_mode_var = tk.StringVar(value=_t("fow_mode_move"))
        
        self.lbl_fow_tool = tk.Label(fow_toolbar, text=_t("fow_tool_label"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
        self.lbl_fow_tool.pack(side=tk.LEFT, padx=(0, 4))
        
        self.map_tool_combo = ttk.Combobox(fow_toolbar, textvariable=self.fow_mode_var, state="readonly", width=15)
        self.map_tool_combo['values'] = (_t("fow_mode_move"), _t("fow_mode_erase"), _t("fow_mode_draw"))
        self.map_tool_combo.pack(side=tk.LEFT, padx=3)

        self.fow_brush_radius_var = tk.IntVar(value=0)
        self.lbl_fow_brush = tk.Label(fow_toolbar, text=_t("fow_brush_radius"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
        self.lbl_fow_brush.pack(side=tk.LEFT, padx=(4, 2))
        self.fow_brush_combo = ttk.Combobox(fow_toolbar, textvariable=self.fow_brush_radius_var, values=[0, 1, 2, 3], state="readonly", width=3)
        self.fow_brush_combo.pack(side=tk.LEFT, padx=(0, 4))
        ToolTip(self.fow_brush_combo, "Raggio del Pennello Nebbia (0 = singolo esagono, 1-3 = area)")
        
        self.dm_player_view_var = tk.BooleanVar(value=False)
        self.chk_player_view = ttk.Checkbutton(fow_toolbar, text=_t("fow_player_view"), variable=self.dm_player_view_var, command=self.redraw_map_and_players)
        self.chk_player_view.pack(side=tk.LEFT, padx=4)

        self.btn_send_fow = ttk.Button(fow_toolbar, text=_t("fow_send_btn"), command=self._broadcast_fow_update, style="Success.TButton")
        self.btn_send_fow.pack(side=tk.LEFT, padx=4)
        
        self.fow_options_btn = ttk.Menubutton(fow_toolbar, text=_t("fow_options_btn"))
        self.setup_fow_options_menu()
        self.fow_options_btn.pack(side=tk.LEFT, padx=3)
        
        self.map_canvas = HexMapCanvas(map_outer_frame, bg="#121316")
        self.map_canvas.pack(fill=tk.BOTH, expand=True)
        self.map_canvas.set_on_click_callback(self.on_hex_clicked)
        self.map_canvas.on_token_drop_callback = self.on_token_drop
        self.map_canvas.set_on_ping_callback(self.on_ping_callback)
        self.map_canvas.set_on_hex_right_click_callback(self.on_hex_right_clicked)
        
        # --- COLONNA 2: RIGHT SIDEBAR (Notebook Dark Fantasy) ---
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        
        self.right_notebook = ttk.Notebook(right_panel)
        self.right_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1 ("Chat & Log")
        tab_chat = ttk.Frame(self.right_notebook)
        self.right_notebook.add(tab_chat, text=_t("tab_chat_log"))
        
        self.notebook = ttk.Notebook(tab_chat)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=0)
        self.create_chat_tab("Sistema")
        
        # Tab Bestiario (Componente Modulare DMBestiaryPanel)
        self.tab_bestiario = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_bestiario, text=_t("tab_bestiary"))
        
        self.bestiary_panel = DMBestiaryPanel(self.tab_bestiario, self)
        self.bestiary_panel.pack(fill=tk.BOTH, expand=True)

        # Alias per compatibilità retroattiva con metodi esistenti e test
        self.lbl_bestiary_header = self.bestiary_panel.lbl_bestiary_header
        self.bestiario_search_var = self.bestiary_panel.bestiario_search_var
        self.btn_bestiary_search = self.bestiary_panel.btn_bestiary_search
        self.bestiario_listbox = self.bestiary_panel.bestiario_listbox
        self.bestiario_preview = self.bestiary_panel.bestiario_preview
        self.btn_bestiary_spawn = self.bestiary_panel.btn_bestiary_spawn
        self.btn_bestiary_full = self.bestiary_panel.btn_bestiary_full
        self.bestiario_results = self.bestiary_panel.bestiario_results

        # 1-Click Quick Dice Strip (DM)
        dm_quick_dice_strip = tk.Frame(tab_chat, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=3)
        dm_quick_dice_strip.pack(fill=tk.X, pady=(4, 0))
        tk.Label(dm_quick_dice_strip, text="🎲", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(side=tk.LEFT, padx=(2, 4))
        for die_sides in (4, 6, 8, 10, 12, 20, 100):
            d_btn = ttk.Button(dm_quick_dice_strip, text=f"d{die_sides}", width=4 if die_sides == 100 else 3, style="QuickDie.TButton")
            d_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
            d_btn.bind("<ButtonRelease-1>", lambda e, s=die_sides: self.quick_roll_dm_die(s, e))
            if die_sides == 20:
                ToolTip(d_btn, "Click: Tira 1d20 | Shift+Click: Vantaggio | Ctrl+Click: Svantaggio")
            else:
                ToolTip(d_btn, f"Tiro rapido 1d{die_sides}")

        # Chat Input Frame
        chat_input_frame = ttk.Frame(tab_chat)
        chat_input_frame.pack(fill=tk.X, pady=(4, 3))
        self.chat_entry = ttk.Entry(chat_input_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.chat_entry.bind("<Return>", lambda e: self.send_dm_chat())
        self.btn_dm_chat_send = ttk.Button(chat_input_frame, text=_t("btn_send"), command=self.send_dm_chat, style="Primary.TButton")
        self.btn_dm_chat_send.pack(side=tk.LEFT)
        self.btn_dm_chat_dice = ttk.Button(chat_input_frame, text=_t("btn_dice"), command=self.roll_dice_dialog, style="Gold.TButton")
        self.btn_dm_chat_dice.pack(side=tk.LEFT, padx=(4, 0))

        # Barra Voice Discord-like
        self.voice_controls_frame = tk.Frame(tab_chat, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, pady=4, padx=6)
        self.voice_controls_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(4, 0))
        self.voice_status_lbl = tk.Label(self.voice_controls_frame, text=_t("voice_server_active"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GREEN, font=FONT_SMALL)
        self.voice_status_lbl.pack(side=tk.LEFT, padx=3)
        self.btn_deafen = tk.Button(self.voice_controls_frame, text=" 🎧 ", bg=SURFACE_COLOR, fg="white", activebackground=SURFACE_COLOR_ALT, relief=tk.FLAT, bd=0, command=self.toggle_deafen)
        self.btn_deafen.pack(side=tk.RIGHT, padx=2)
        ToolTip(self.btn_deafen, _t("tooltip_deafen"))
        self.btn_mute = tk.Button(self.voice_controls_frame, text=" 🎤 ", bg=SURFACE_COLOR, fg="white", activebackground=SURFACE_COLOR_ALT, relief=tk.FLAT, bd=0, command=self.toggle_mute)
        self.btn_mute.pack(side=tk.RIGHT, padx=2)
        ToolTip(self.btn_mute, _t("tooltip_mute_mic"))
        
        # Tab 2 ("Iniziativa & PG")
        tab_combat = ttk.Frame(self.right_notebook)
        self.right_notebook.add(tab_combat, text=_t("tab_party_initiative"))
        
        self.lbl_combatants_hdr = tk.Label(tab_combat, text=_t("dm_combatants_header"), font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD)
        self.lbl_combatants_hdr.pack(anchor="w", pady=(0, 6))
        
        # Combat Banner Card (Iniziativa)
        self.combat_controls_frame = tk.Frame(tab_combat, bg=SURFACE_COLOR, highlightbackground=ACCENT_GOLD, highlightthickness=1, padx=8, pady=6)
        
        combat_top_row = tk.Frame(self.combat_controls_frame, bg=SURFACE_COLOR)
        combat_top_row.pack(fill=tk.X, pady=(0, 4))
        curr_rnd = getattr(self.server.game_state, 'round_number', 1) if hasattr(self, 'server') and hasattr(self.server, 'game_state') else 1
        self.lbl_round = tk.Label(combat_top_row, text=_t("lbl_round_num", round=curr_rnd), font=("Georgia", 11, "bold"), bg=SURFACE_COLOR, fg=ACCENT_GOLD)
        self.lbl_round.pack(side=tk.LEFT)
        
        turn_nav_frame = tk.Frame(self.combat_controls_frame, bg=SURFACE_COLOR)
        turn_nav_frame.pack(fill=tk.X)
        self.btn_prev_turn = ttk.Button(turn_nav_frame, text=_t("btn_prev_turn"), command=self.prev_turn_gui, state=tk.DISABLED)
        self.btn_prev_turn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        self.btn_next_turn = ttk.Button(turn_nav_frame, text=_t("btn_next_turn"), command=self.next_turn_gui, state=tk.DISABLED, style="Primary.TButton")
        self.btn_next_turn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        # Container Player Listbox
        list_frame = tk.Frame(tab_combat, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        list_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=(0, 6))

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.player_listbox = tk.Listbox(
            list_frame, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=FONT_MAIN,
            selectbackground=ACCENT_GOLD, selectforeground=TEXT_DARK,
            borderwidth=0, relief="flat", highlightthickness=0, yscrollcommand=scrollbar.set
        )
        self.player_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.player_listbox.yview)
        self.player_listbox.bind("<Double-Button-1>", self.open_private_chat_from_list)
        self.player_listbox.bind("<Button-3>", self.show_player_context_menu)
        self.player_listbox.bind("<<ListboxSelect>>", self.on_player_selected)

        self.btn_hide_reveal = ttk.Button(tab_combat, text=_t("btn_hide_reveal"), command=self.toggle_hide_reveal)
        self.btn_hide_reveal.pack(fill=tk.X, side=tk.TOP, pady=(0, 4))

        self.npc_actions_frame = ttk.LabelFrame(tab_combat, text=_t("npc_actions_header"))
        self.npc_actions_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 4))
        
        self.btn_combat = ttk.Button(tab_combat, text=_t("btn_start_combat"), command=self.toggle_combat, style='Gold.TButton')
        self.btn_combat.pack(fill=tk.X, side=tk.TOP, pady=(0, 4))
        
        self.btn_campaign_encounter = ttk.Button(tab_combat, text=_t("btn_deploy_prepared"), command=self.deploy_campaign_encounter_dialog, style='Gold.TButton')
        self.btn_campaign_encounter.pack(fill=tk.X, side=tk.TOP, pady=(0, 4))
        
        self.btn_mass_npc_initiative = ttk.Button(tab_combat, text=_t("btn_roll_all_npcs"), command=self.roll_all_npcs_initiative, style='Primary.TButton')
        self.btn_mass_npc_initiative.pack(fill=tk.X, side=tk.TOP, pady=(0, 4))
        
        self.lbl_encounter_diff = tk.Label(tab_combat, text=_t("lbl_balance_waiting"), font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, padx=6, pady=4, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.lbl_encounter_diff.pack(fill=tk.X, side=tk.TOP, pady=(0, 6))
        
        # Pulsanti Bottom Tab 2
        btn_frame_bottom = ttk.Frame(tab_combat)
        btn_frame_bottom.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))
        self.btn_spawn_png = ttk.Button(btn_frame_bottom, text=_t("btn_spawn_png"), command=self.spawn_png_dialog, style="Primary.TButton")
        self.btn_spawn_png.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        self.btn_encounter_builder = ttk.Button(btn_frame_bottom, text="Encounter Builder", command=self.open_encounter_builder, style="Primary.TButton")
        self.btn_encounter_builder.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        self.btn_add_npc = ttk.Button(tab_combat, text=_t("btn_add_manual_npc"), command=self.add_npc)
        self.btn_add_npc.pack(fill=tk.X, side=tk.BOTTOM, pady=(4, 0))
        self.btn_split_loot = ttk.Button(tab_combat, text=_t("btn_split_loot"), command=self.split_loot_dialog, style="Gold.TButton")
        self.btn_split_loot.pack(fill=tk.X, side=tk.BOTTOM, pady=(4, 0))

        # Tab 3 ("Mondo")
        tab_world = ttk.Frame(self.right_notebook)
        self.right_notebook.add(tab_world, text=_t("tab_world"))
        
        self.lbl_campaign_name = tk.Label(tab_world, text=_t("campaign_none"), font=FONT_BOLD, 
                                          bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD, padx=8, pady=4, 
                                          highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.lbl_campaign_name.pack(fill=tk.X, pady=(4, 6))
        
        self.btn_switch_scene = ttk.Button(tab_world, text=_t("btn_switch_scene"), command=self.switch_campaign_scene_dialog, style='Info.TButton')
        self.btn_switch_scene.pack(fill=tk.X, pady=(0, 8))
        
        self.lbl_time_mgmt = tk.Label(tab_world, text=_t("time_mgmt_header"), font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD)
        self.lbl_time_mgmt.pack(anchor="w", pady=(4, 4))
        self.lbl_time = ttk.Label(tab_world, text="")
        self.lbl_time.pack(anchor="w", pady=(0, 8))
        
        time_btn_frame = ttk.Frame(tab_world)
        time_btn_frame.pack(fill=tk.X, pady=4)
        self.btn_add_1h = ttk.Button(time_btn_frame, text=_t("time_add_1h"), command=lambda: self.advance_time(1))
        self.btn_add_1h.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        self.btn_add_8h = ttk.Button(time_btn_frame, text=_t("time_add_8h"), command=lambda: self.advance_time(8, is_rest=True))
        self.btn_add_8h.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 2))
        self.btn_add_1d = ttk.Button(time_btn_frame, text=_t("time_add_1d"), command=lambda: self.advance_time(24, is_rest=True))
        self.btn_add_1d.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        self.btn_calendar = ttk.Button(tab_world, text=_t("btn_open_calendar"), command=self.open_calendar_dialog, style='Info.TButton')
        self.btn_calendar.pack(fill=tk.X, pady=(8, 4))
        
        self.btn_quests = ttk.Button(tab_world, text=_t("btn_open_quests"), command=self.open_quest_dialog, style='Info.TButton')
        self.btn_quests.pack(fill=tk.X, pady=4)
        
        self.btn_shops = ttk.Button(tab_world, text=_t("btn_open_shops"), command=self.open_shop_dialog, style='Info.TButton')
        self.btn_shops.pack(fill=tk.X, pady=4)
        
        self.btn_travel = ttk.Button(tab_world, text=_t("btn_travel_panel"), command=self.open_travel_panel, style='Primary.TButton')
        self.btn_travel.pack(fill=tk.X, pady=(8, 4))
        self.btn_world_manuals = ttk.Button(tab_world, text=_t("btn_manuals"), command=self.open_manuals_dialog, style='Info.TButton')
        self.btn_world_manuals.pack(fill=tk.X, pady=(0, 4))
        
        self.lbl_weather_hdr = tk.Label(tab_world, text=_t("weather_header"), font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD)
        self.lbl_weather_hdr.pack(anchor="w", pady=(12, 4))
        self.weather_var = tk.StringVar(value=_t("weather_clear"))
        self.weather_combo = ttk.Combobox(tab_world, textvariable=self.weather_var, values=[_t("weather_clear"), _t("weather_rain"), _t("weather_storm"), _t("weather_snow"), _t("weather_fog")], state="readonly")
        self.weather_combo.pack(fill=tk.X)
        self.weather_combo.bind("<<ComboboxSelected>>", self.on_weather_changed)
        
        # Tab 4 ("Audio/Sfx")
        tab_audio = ttk.Frame(self.right_notebook, padding=5)
        self.right_notebook.add(tab_audio, text=_t("tab_audio_sfx"))
        self.build_audio_tab(tab_audio)
        self.setup_player_context_menu()

        # Scorciatoia universale Command Palette (Ctrl+K)
        self.master.bind("<Control-k>", self.open_command_palette)
        self.master.bind("<Control-K>", self.open_command_palette)

    def open_command_palette(self, event=None):
        try:
            from components.ui_components import CommandPaletteDialog
            p_names = [p.name for p in self.server.game_state.get_all_players()]
            CommandPaletteDialog(
                self.master,
                map_canvas=self.map_canvas,
                on_action=self._handle_command_palette_action,
                is_dm=True,
                player_names=p_names
            )
        except Exception as e:
            print("Error opening CommandPaletteDialog in DM_GUI:", e)

    def _handle_command_palette_action(self, action_type, payload):
        if action_type == "roll":
            formula = payload.strip()
            if formula.startswith("/roll"):
                formula = formula[5:].strip()
            elif formula.startswith("/r"):
                formula = formula[2:].strip()
            formula = formula or "1d20"
            from common.dice import roll_dice
            res = roll_dice(formula)
            from common.protocol import make_chat_broadcast
            from server.network import broadcast
            crit_badge = ""
            if res.get("is_crit"):
                crit_badge = " 🌟 SUCCESSO CRITICO! (20 Naturale)"
                if hasattr(self, "show_toast"):
                    self.show_toast(f"20 NATURALE su {formula} (Totale: {res['total']})!", title="🌟 Successo Critico!", toast_type="gold")
            elif res.get("is_fumble"):
                crit_badge = " 💀 FALLIMENTO CRITICO! (1 Naturale)"
                if hasattr(self, "show_toast"):
                    self.show_toast(f"1 NATURALE su {formula} (Totale: {res['total']})!", title="💀 Fallimento Critico!", toast_type="danger")
            msg = f"🎲 [DM Tiro Rapido] {formula} -> Risultato: {res['total']} ({res['rolls']}){crit_badge}"
            broadcast(self.server.game_state, make_chat_broadcast("DM", msg))
            self.log_to_chat(f"[DM]: {msg}")
        elif action_type == "center_token":
            if self.map_canvas and hasattr(self.map_canvas, "center_on_token"):
                self.map_canvas.center_on_token(payload)
        elif action_type == "action":
            if payload == "open_manuals":
                self.open_manuals_dialog()
            elif payload == "toggle_ruler":
                self.toggle_ruler_mode()
            elif payload == "open_aoe":
                self.open_aoe_dialog()
            elif payload == "center_map" and self.map_canvas:
                self.map_canvas.center_view()

    # ------------------------------------------------------------------
    # AUDIO: libreria di tracce caricate dal DM
    # ------------------------------------------------------------------
    def build_audio_tab(self, parent):
        self.soundboard_panel = DMSoundboardPanel(parent, self)
        self.soundboard_panel.pack(fill=tk.BOTH, expand=True)

        # Alias per compatibilità retroattiva con attributi di test e controller
        self.lbl_audio_lib = self.soundboard_panel.lbl_audio_lib
        self.lbl_audio_desc = self.soundboard_panel.lbl_audio_desc
        self.btn_import_audio = self.soundboard_panel.btn_import_audio
        self.audio_tree = self.soundboard_panel.audio_tree
        self.audio_loop_var = self.soundboard_panel.audio_loop_var
        self.audio_dm_listen_var = self.soundboard_panel.audio_dm_listen_var
        self.audio_volume_var = self.soundboard_panel.audio_volume_var
        self.audio_now_playing = self.soundboard_panel.audio_now_playing

    @staticmethod
    def _format_duration(seconds):
        return DMSoundboardPanel._format_duration(seconds)

    def refresh_audio_list(self):
        if hasattr(self, 'soundboard_panel'):
            self.soundboard_panel.refresh_audio_list()

    def _selected_track(self):
        if hasattr(self, 'soundboard_panel'):
            return self.soundboard_panel._selected_track()
        return None

    def import_audio_tracks(self):
        if hasattr(self, 'soundboard_panel'):
            self.soundboard_panel.import_audio_tracks()

    def rename_audio_track(self):
        if hasattr(self, 'soundboard_panel'):
            self.soundboard_panel.rename_audio_track()

    def toggle_audio_category(self):
        if hasattr(self, 'soundboard_panel'):
            self.soundboard_panel.toggle_audio_category()

    def remove_audio_track(self):
        if hasattr(self, 'soundboard_panel'):
            self.soundboard_panel.remove_audio_track()

    def play_selected_audio(self):
        if hasattr(self, 'soundboard_panel'):
            self.soundboard_panel.play_selected_audio()

    def stop_audio(self, channel="all"):
        if hasattr(self, 'soundboard_panel'):
            self.soundboard_panel.stop_audio(channel)

    def share_audio_link(self):
        if hasattr(self, 'soundboard_panel'):
            self.soundboard_panel.share_audio_link()

    def play_audio(self, url):
        if hasattr(self, 'soundboard_panel'):
            self.soundboard_panel.play_audio(url)

    def on_ping_callback(self, clicked_hex):
        broadcast(self.server.game_state, make_ping_broadcast(clicked_hex.q, clicked_hex.r, "red"))
        self.map_canvas.draw_ping(clicked_hex.q, clicked_hex.r, "red")

    def open_map_downloader(self):
        win = MapDownloaderDialog(self.master)
        win.grab_set()

    def open_srd_importer(self):
        try:
            from server.compendium_ui import CompendiumDialog
            win = CompendiumDialog(self.master, on_import_callback=self.handle_srd_import, is_dm=True)
            win.grab_set()
        except ImportError as e:
            messagebox.showerror("Errore", f"Impossibile aprire il compendio: {e}")

    def open_encounter_builder(self):
        try:
            from server.encounter_builder_ui import EncounterBuilderDialog
            win = EncounterBuilderDialog(self.master, self.server.game_state, on_start_encounter_callback=self.handle_encounter_start)
            win.grab_set()
        except ImportError as e:
            from common.messagebox import messagebox
            messagebox.showerror("Errore", f"Impossibile aprire il builder: {e}")
            
    def handle_encounter_start(self, monsters):
        added_names = []
        for m in monsters:
            for i in range(m["count"]):
                name = m["name"]
                if m["count"] > 1:
                    name = f"{name} {i+1}"
                npc = Player(name, None, None)
                npc.hp = m["hp"]
                npc.max_hp = m["hp"]
                npc.initiative = m["initiative"]
                
                npc.full_sheet = {
                    "name": npc.name,
                    "char_class": "Mostro/NPC",
                    "level": 1,
                    "hp_current": npc.hp,
                    "hp_max": npc.max_hp,
                }
                self.server.game_state.add_player(npc)
                broadcast(self.server.game_state, make_player_joined(npc.to_dict()))
                added_names.append(name)
                
        self.log_to_chat(f"[SISTEMA] Incontro caricato. Aggiunti {len(added_names)} NPC: {', '.join(added_names)}")

    def spawn_png_dialog(self):
        try:
            from server.compendium_ui import CompendiumDialog
            win = CompendiumDialog(self.master, on_import_callback=self.on_monster_spawned, is_dm=True)
            win.grab_set()
        except ImportError as e:
            from common.messagebox import messagebox
            messagebox.showerror("Errore", f"Impossibile aprire il compendio: {e}")

    def on_monster_spawned(self, item_data, category):
        base_name = item_data.get("name", "Mostro")
        idx = 1
        new_name = f"{base_name} {idx}"
        while self.server.game_state.find_player(new_name):
            idx += 1
            new_name = f"{base_name} {idx}"

        # SRD stats extraction
        hp = item_data.get("hit_points", item_data.get("hp", 10))
        
        ac_data = item_data.get("armor_class", item_data.get("ac", 10))
        ac = 10
        if isinstance(ac_data, list) and len(ac_data) > 0:
            first_ac = ac_data[0]
            if isinstance(first_ac, dict):
                ac = first_ac.get("value", 10)
            else:
                ac = first_ac
        elif isinstance(ac_data, int):
            ac = ac_data
            
        npc = Player(new_name, None, None)
        npc.hp = hp
        npc.max_hp = hp
        npc.initiative = item_data.get("initiative", 0)
        
        npc.full_sheet = {
            "name": npc.name,
            "char_class": "Mostro/NPC",
            "level": 1,
            "hp_current": npc.hp,
            "hp_max": npc.max_hp,
            "ac": ac,
            "speed": item_data.get("speed", 30),
            "attributes": item_data.get("attributes", {}),
            "features": item_data.get("features", ""),
        }
        
        self.server.game_state.add_player(npc)
        
        from common.protocol import make_player_joined, make_game_state
        broadcast(self.server.game_state, make_player_joined(npc.to_dict()))
        broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
        
        self.log_to_chat(f"[SISTEMA] Mostro '{npc.name}' spawnato sulla mappa.")
        self.server.game_state._trigger_gui_update()

    def handle_srd_import(self, entity_data, category=None):
        npc = Player(entity_data["name"], None, None)
        npc.hp = entity_data.get("hp", 10)
        npc.max_hp = npc.hp
        npc.initiative = entity_data.get("initiative", 0)
        
        # Add basic full sheet data from SRD
        npc.full_sheet = {
            "name": npc.name,
            "char_class": "Mostro/NPC",
            "level": 1,
            "hp_current": npc.hp,
            "hp_max": npc.max_hp,
            "ac": entity_data.get("ac", 10),
            "speed": entity_data.get("speed", 30),
            "attributes": entity_data.get("attributes", {}),
            "features": entity_data.get("features", ""),
        }
        
        self.server.game_state.add_player(npc)
        broadcast(self.server.game_state, make_player_joined(npc.to_dict()))
        self.log_to_chat(f"[SISTEMA] NPC '{npc.name}' importato dal SRD e aggiunto.")

    def remove_entity(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
        player = self.server.game_state.find_player(player_name)
        if not player: return
        
        if messagebox.askyesno("Conferma Rimuovi", f"Rimuovere {player_name} dal gioco?"):
            self.server.game_state.remove_player(player_name)
            broadcast(self.server.game_state, make_player_left(player_name))
            self.log_to_chat(f"[SISTEMA] {player_name} è stato rimosso dal DM.")
            self.server.game_state._trigger_gui_update()

    def toggle_player_combat_status(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return
        if display_text.startswith("---"): return
        player_name = display_text.split(" (HP")[0].replace("▶", "").replace("➡️", "").strip()
        if player_name.startswith("[N] "):
            player_name = player_name[4:]
        player = self.server.game_state.find_player(player_name)
        if not player: return

        if not self.server.game_state.combat_active:
            messagebox.showinfo("Combattimento", "Nessun combattimento in corso.")
            return

        current_status = getattr(player, 'in_combat', False)
        player.in_combat = not current_status
        
        current_turn_p = self.server.game_state.get_current_turn_player()

        if player.in_combat:
            # Entering combat mid-fight
            import random
            from common.protocol import make_request_initiative, make_player_stats_update
            if player.conn is None:
                player.initiative = random.randint(1, 20) + player.initiative
                self.log_to_chat(f"[COMBAT] {player.name} (NPC) entra in combattimento con iniziativa: {player.initiative}")
                broadcast(self.server.game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions))
            else:
                send_message(player.conn, make_request_initiative())
                self.log_to_chat(f"[COMBAT] Richiesta iniziativa a {player.name} entrato mid-combat.")
        else:
            self.log_to_chat(f"[COMBAT] {player.name} rimosso dal combattimento.")
            
        # Re-sort and adjust turn index
        with self.server.game_state.lock:
            self.server.game_state.players.sort(key=lambda p: (getattr(p, 'in_combat', True), p.initiative), reverse=True)
            if current_turn_p:
                combatants = [p for p in self.server.game_state.players if getattr(p, 'in_combat', True)]
                try:
                    self.server.game_state.turn_index = combatants.index(current_turn_p)
                except ValueError:
                    self.server.game_state.turn_index = 0

        self.server.game_state._trigger_gui_update()
        from common.protocol import make_game_state
        broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))

    def toggle_party_status(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return
        if display_text.startswith("---"): return
        player_name = display_text.split(" (HP")[0].replace("▶", "").replace("➡️", "").strip()
        if player_name.startswith("[N] "):
            player_name = player_name[4:]
        player = self.server.game_state.find_player(player_name)
        if not player: return

        current_status = getattr(player, 'is_party_member', False)
        player.is_party_member = not current_status
        self.server.game_state._trigger_gui_update()

    def clear_aoes(self):
        self.server.game_state.clear_aoes()
        from common.protocol import make_game_state
        broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))

    def toggle_combat(self):
        if not self.server.game_state.combat_active:
            self.open_combat_config()
        else:
            if messagebox.askyesno(_t("msg_combat_end_title", default="Fine Combattimento"), _t("msg_combat_end_confirm", default="Vuoi terminare il combattimento?")):
                ended_round = getattr(self.server.game_state, "round_number", 1)
                self.server.game_state.end_combat()
                self._auto_restore_scene_music()
                self.server.game_state.add_calendar_event(f"Combattimento Terminato al Round {ended_round}")
                self.log_to_chat("[SISTEMA] Fine Combattimento.")
                from common.protocol import make_chat_broadcast, make_game_state
                broadcast(self.server.game_state, make_chat_broadcast("Sistema", "Fine Combattimento."))
                broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))

    def open_combat_config(self, initiator_name=None):
        if self.server.game_state.combat_active:
            messagebox.showinfo(_t("combat", default="Combattimento"), _t("msg_combat_already_running", default="Un combattimento è già in corso."))
            return

        all_players = self.server.game_state.get_all_players()
        if not all_players:
            messagebox.showinfo(_t("combat", default="Combattimento"), _t("msg_no_players_combat", default="Nessun personaggio/NPC per iniziare il combattimento."))
            return

        dialog = tk.Toplevel(self.master)
        dialog.title(_t("combat_config_title", default="Configurazione Combattimento"))
        dialog.minsize(400, 550)
        dialog.transient(self.master)
        dialog.grab_set()

        from common.theme import apply_modern_window_style
        apply_modern_window_style(dialog)

        if initiator_name:
            ttk.Label(dialog, text=f"{initiator_name} ha richiesto l'inizio del combattimento!", font=self.default_font, foreground="#D4AF37").pack(pady=(10, 5))

        # Filtro per distanza
        filter_frame = ttk.LabelFrame(dialog, text=_t("combat_filter_distance", default="Filtro per Distanza (Auto-selezione)"))
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text=_t("combat_origin", default="Origine:")).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        origin_var = tk.StringVar(value=initiator_name if initiator_name else all_players[0].name)
        origin_combo = ttk.Combobox(filter_frame, textvariable=origin_var, values=[p.name for p in all_players], state="readonly")
        origin_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(filter_frame, text=_t("combat_radius_hex", default="Raggio (esagoni):")).grid(row=1, column=0, padx=5, pady=5, sticky="e")
        radius_var = tk.StringVar(value="6")
        ttk.Entry(filter_frame, textvariable=radius_var, width=5).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        checkbox_vars = {}
        def apply_filter():
            origin_name = origin_var.get()
            try:
                rad = int(radius_var.get())
            except:
                rad = 0
            
            origin_p = self.server.game_state.find_player(origin_name)
            if not origin_p: return
            o_hex = Hex(origin_p.position[0], origin_p.position[1])
            
            for p in all_players:
                p_hex = Hex(p.position[0], p.position[1])
                dist = o_hex.distance(p_hex)
                checkbox_vars[p.name].set(dist <= rad)

        ttk.Button(filter_frame, text=_t("btn_select_nearby", default="Seleziona Vicini"), command=apply_filter).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(dialog, text=_t("combat_participants", default="Partecipanti:"), font=self.default_font).pack(pady=(10,0))

        listbox_frame = ttk.Frame(dialog)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas = tk.Canvas(listbox_frame, bg=SURFACE_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Create checkboxes
        for p in all_players:
            var = tk.BooleanVar(value=True)
            checkbox_vars[p.name] = var
            ttk.Checkbutton(scrollable_frame, text=f"{p.name} (HP: {p.hp}/{p.max_hp})", variable=var).pack(anchor="w", pady=2)

        def finalize_combat(selected_names, npc_initiatives):
            self.server.game_state.start_combat(participant_names=selected_names)
            self._auto_play_battle_music()
            self.server.game_state.add_calendar_event(f"Combattimento Iniziato (Partecipanti: {len(selected_names)})")
            
            from common.protocol import make_request_initiative, make_player_stats_update
            for p in self.server.game_state.get_all_players():
                if p.name in selected_names:
                    if p.conn is None: # NPC
                        p.initiative = npc_initiatives.get(p.name, p.initiative)
                        self.log_to_chat(f"[COMBAT] {p.name} (NPC) iniziativa: {p.initiative}")
                        broadcast(self.server.game_state, make_player_stats_update(p.name, p.hp, p.max_hp, p.initiative, p.conditions))
                    else: # Player
                        send_message(p.conn, make_request_initiative())
            
            self.log_to_chat("[SISTEMA] Inizio Combattimento!")
            from common.protocol import make_chat_broadcast, make_game_state
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", "Inizio Combattimento! Ai giocatori è stata richiesta l'iniziativa."))
            
            # Re-sort state and update
            self.server.game_state.players.sort(key=lambda p: (getattr(p, 'in_combat', True), p.initiative), reverse=True)
            self.server.game_state._trigger_gui_update()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            dialog.destroy()

        def confirm():
            selected_names = [name for name, var in checkbox_vars.items() if var.get()]
            if not selected_names:
                messagebox.showwarning(_t("warning", default="Attenzione"), _t("msg_select_at_least_one_participant", default="Seleziona almeno un partecipante."))
                return
            
            import random
            npcs_in_combat = [p for p in self.server.game_state.get_all_players() if p.name in selected_names and p.conn is None]
            
            if not npcs_in_combat:
                finalize_combat(selected_names, {})
                return
                
            # Mostra dialog per l'iniziativa degli NPC
            init_dialog = tk.Toplevel(dialog)
            init_dialog.title(_t("npc_init_dialog_title", default="Iniziativa NPC"))
            init_dialog.minsize(300, 400)
            init_dialog.transient(dialog)
            init_dialog.grab_set()
            apply_modern_window_style(init_dialog)
            
            ttk.Label(init_dialog, text=_t("npc_init_dialog_prompt", default="Inserisci l'iniziativa per gli NPC:"), font=self.default_font).pack(pady=10)
            
            entries = {}
            frame = ttk.Frame(init_dialog)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Canvas per scrollare se ci sono troppi NPC
            c = tk.Canvas(frame, bg=SURFACE_COLOR, highlightthickness=0)
            s = ttk.Scrollbar(frame, orient="vertical", command=c.yview)
            sf = ttk.Frame(c)
            sf.bind("<Configure>", lambda e: c.configure(scrollregion=c.bbox("all")))
            c.create_window((0, 0), window=sf, anchor="nw")
            c.configure(yscrollcommand=s.set)
            c.pack(side="left", fill="both", expand=True)
            s.pack(side="right", fill="y")
            
            for npc in npcs_in_combat:
                row = ttk.Frame(sf)
                row.pack(fill=tk.X, pady=2)
                ttk.Label(row, text=npc.name, width=15).pack(side=tk.LEFT)
                auto_roll = random.randint(1, 20) + npc.initiative
                var = tk.StringVar(value=str(auto_roll))
                entries[npc.name] = var
                ttk.Entry(row, textvariable=var, width=5).pack(side=tk.RIGHT)
                
            def submit_init():
                npc_initiatives = {}
                for name, var in entries.items():
                    try:
                        npc_initiatives[name] = int(var.get())
                    except ValueError:
                        npc_initiatives[name] = 0
                init_dialog.destroy()
                finalize_combat(selected_names, npc_initiatives)
                
            ttk.Button(init_dialog, text=_t("btn_confirm_initiatives", default="Conferma Iniziative"), command=submit_init, style="Primary.TButton").pack(pady=10)

        ttk.Button(dialog, text=_t("btn_next", default="Avanti"), command=confirm, style='Primary.TButton').pack(pady=15)

    def roll_all_npcs_initiative(self):
        """Tira automaticamente l'iniziativa (1d20 + mod DES) per tutti i mostri/PNG."""
        from common.protocol import make_player_stats_update, make_chat_broadcast, make_game_state
        import random
        rolled_count = 0
        with self.server.game_state.lock:
            for p in self.server.game_state.players:
                # Mostri/PNG non hanno una connessione client attiva
                if not getattr(p, "conn", None):
                    dex_mod = 0
                    if getattr(p, "full_sheet", None):
                        attr = p.full_sheet.get("attributes", {})
                        if "DES" in attr:
                            try:
                                dex_mod = (int(attr["DES"]) - 10) // 2
                            except (ValueError, TypeError):
                                pass
                    d20 = random.randint(1, 20)
                    p.initiative = d20 + dex_mod
                    rolled_count += 1
                    broadcast(self.server.game_state, make_player_stats_update(p.name, p.hp, p.max_hp, p.initiative, getattr(p, "conditions", []), getattr(p, "temp_hp", 0)))
            if self.server.game_state.combat_active:
                self.server.game_state.players.sort(key=lambda p: (getattr(p, 'in_combat', True), p.initiative), reverse=True)
                
        if rolled_count > 0:
            self.server.game_state._trigger_gui_update()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            msg = f"🎲 Iniziativa tirata automaticamente per tutti i {rolled_count} Mostri/PNG!"
            self.log_to_chat(f"[COMBAT] {msg}")
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", msg))
        else:
            self.log_to_chat("[COMBAT] Nessun Mostro/PNG presente per tirare l'iniziativa.")

    def next_turn_gui(self):
        self.server.game_state.next_turn()
        self._announce_turn()

    def prev_turn_gui(self):
        self.server.game_state.prev_turn()
        self._announce_turn()

    def _announce_turn(self):
        player = self.server.game_state.get_current_turn_player()
        if player:
            msg = f"Round {self.server.game_state.round_number} - Turno di {player.name}!"
            self.log_to_chat(f"[COMBAT] {msg}")
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", msg))
        broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))

    def roll_dice_dialog(self):
        formula = simpledialog.askstring("Tira Dadi", "Inserisci formula (es: 2d6+1):")
        if formula:
            reason = simpledialog.askstring("Motivo", "Motivo del tiro (facoltativo):") or ""
            from common.dice import roll_dice
            try:
                result = roll_dice(formula)
                crit_badge = ""
                if result.get("is_crit"):
                    crit_badge = " 🌟 SUCCESSO CRITICO! (20 Naturale)"
                    if hasattr(self, "show_toast"):
                        self.show_toast(f"20 NATURALE su {reason or formula} (Totale: {result['total']})!", title="🌟 Successo Critico!", toast_type="gold")
                elif result.get("is_fumble"):
                    crit_badge = " 💀 FALLIMENTO CRITICO! (1 Naturale)"
                    if hasattr(self, "show_toast"):
                        self.show_toast(f"1 NATURALE su {reason or formula} (Totale: {result['total']})!", title="💀 Fallimento Critico!", toast_type="danger")
                log_msg = f"DM tira {formula} {'(' + reason + ')' if reason else ''}: {result['rolls']} + {result['modifier']} = {result['total']}{crit_badge}"
                self.log_to_chat(f"[ROLL] {log_msg}")
                broadcast(self.server.game_state, make_dice_roll_result("DM", formula, reason, result))
            except Exception as e:
                messagebox.showerror("Errore Dadi", str(e))

    def toggle_fow(self):
        if not self.server.game_state.current_map: return
        self.server.game_state.current_map["fow_enabled"] = self.fow_enabled_var.get()
        self.redraw_map_and_players()
        self._broadcast_fow_update()
        from common.protocol import make_map_data_update_broadcast
        broadcast(self.server.game_state, make_map_data_update_broadcast(self.server.game_state.current_map))
        
    def reveal_all_fow(self):
        if not self.server.game_state.current_map: return
        self.server.game_state.current_map["fow_draft"] = self.server.game_state.current_map.get("hexes", [])[:]
        self.redraw_map_and_players()
        self.show_toast("Tutta la mappa rivelata nella bozza. Clicca 'Invia ai Giocatori' per applicare.", title="☁️ Nebbia di Guerra", toast_type="info")

    def hide_all_fow(self):
        if not self.server.game_state.current_map: return
        self.server.game_state.current_map["fow_draft"] = []
        self.redraw_map_and_players()
        self.show_toast("Tutta la mappa coperta nella bozza. Clicca 'Invia ai Giocatori' per applicare.", title="☁️ Nebbia di Guerra", toast_type="info")

    def advance_time(self, hours, is_rest=False):
        gs = self.server.game_state
        gs.time_hour += hours
        while gs.time_hour >= 24:
            gs.time_hour -= 24
            gs.time_day += 1
            gs.travel_hours_today = 0  # Nuovo giorno, reset ore marcia
            while gs.time_day > 30:
                gs.time_day -= 30
                gs.time_month += 1
                while gs.time_month > 12:
                    gs.time_month -= 12
                    gs.time_year += 1
            
        if is_rest and hours >= 8:
            gs.travel_hours_today = 0
            self.log_to_chat(f"Il party ha completato un Riposo Lungo! (Giorno {gs.time_day})")
            gs.add_calendar_event("Il party ha completato un Riposo Lungo")
            for p in gs.players:
                p.hp = p.max_hp
                p.exhaustion_level = max(0, getattr(p, "exhaustion_level", 0) - 1)
                conds = [c for c in getattr(p, "conditions", []) if not c.startswith("Sfinimento")]
                if p.exhaustion_level > 0:
                    conds.append(f"Sfinimento (Liv. {p.exhaustion_level})")
                p.conditions = conds
                if p.full_sheet:
                    p.full_sheet["hp_current"] = p.max_hp
                    p.full_sheet["exhaustion_level"] = p.exhaustion_level
                    p.full_sheet["conditions"] = conds
        else:
            self.log_to_chat(f"Il tempo avanza di {hours} ore.")
        
        gs._trigger_gui_update()
        broadcast(gs, make_game_state(gs.get_state_dict()))

    def on_weather_changed(self, event):
        gs = self.server.game_state
        gs.weather = self.weather_var.get()
        self.log_to_chat(f"Il clima cambia in: {gs.weather}")
        gs._trigger_gui_update()
        broadcast(gs, make_game_state(gs.get_state_dict()))

    def _broadcast_fow_update(self):
        if self.server.game_state.current_map:
            cur_map = self.server.game_state.current_map
            if "fow_draft" not in cur_map:
                cur_map["fow_draft"] = cur_map.get("fow_revealed", []).copy()
            cur_map["fow_revealed"] = cur_map["fow_draft"].copy()
            from common.protocol import make_fow_update_broadcast
            fow_rev = cur_map["fow_revealed"]
            fow_draft = cur_map["fow_draft"]
            fow_enabled = cur_map.get("fow_enabled", False)
            broadcast(self.server.game_state, make_fow_update_broadcast(fow_rev, fow_draft, fow_enabled=fow_enabled))
            self.log_to_chat("[SISTEMA] Nebbia di Guerra sincronizzata con i giocatori.")

    def on_token_drop(self, token_name, q, r):
        player = self.server.game_state.find_player(token_name)
        if player:
            from server.commands import command_handlers
            command_handlers["MOVE_REQUEST"]({"to": [q, r], "is_dm_force": True}, player, self.server.game_state)

    def on_hex_right_clicked(self, event, clicked_hex, token_name):
        if token_name:
            # Seleziona il token nella listbox in base al nome
            for i in range(self.player_listbox.size()):
                display_text = self.player_listbox.get(i)
                if display_text.startswith('---'): continue
                name = display_text.split(" (HP")[0].replace("? ", "").strip()
                if name == token_name:
                    self.player_listbox.selection_clear(0, "end")
                    self.player_listbox.selection_set(i)
                    self.player_listbox.activate(i)
                    self.on_player_selected(None)
                    break
                    
            # Apri il menu contestuale gia' esistente per i player
            try:
                self.player_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.player_menu.grab_release()
        else:
            # Menu contestuale della mappa (hex vuoto)
            map_menu = tk.Menu(self.master, tearoff=0)
            map_menu.add_command(label="Imposta Punto di Spawn", command=lambda: self.set_spawn_point(clicked_hex))
            
            cur_map = getattr(self.server.game_state, "current_map", None)
            traps = cur_map.get("traps", []) if cur_map else []
            trap_here = next((t for t in traps if t.get("q") == clicked_hex.q and t.get("r") == clicked_hex.r), None)
            
            if trap_here:
                map_menu.add_command(label=f"🗑️ Rimuovi Trappola ({trap_here.get('name', 'Trappola')})", 
                                    command=lambda: self.remove_trap_at(clicked_hex))
                if trap_here.get("triggered", False):
                    map_menu.add_command(label="🔄 Resetta Trappola (Riattiva)", 
                                        command=lambda: self.reset_trap_at(clicked_hex))
            else:
                map_menu.add_command(label="⚠️ Piazza Trappola 5e...", command=lambda: self.open_place_trap_dialog(clicked_hex))

            try:
                map_menu.tk_popup(event.x_root, event.y_root)
            finally:
                map_menu.grab_release()

    def set_spawn_point(self, clicked_hex):
        if not self.server.game_state.current_map: return
        self.server.game_state.current_map["spawn_point"] = [clicked_hex.q, clicked_hex.r]
        self.log_to_chat(f"[SISTEMA] Punto di spawn impostato a [{clicked_hex.q}, {clicked_hex.r}].")
        from common.protocol import make_map_data_update_broadcast
        from server.network import broadcast
        broadcast(self.server.game_state, make_map_data_update_broadcast(self.server.game_state.current_map))
            
    def on_hex_clicked(self, clicked_hex):
        if not self.server.game_state.current_map: return
        
        if getattr(self, "teleport_mode_var", None) and self.teleport_mode_var.get():
            pos_key = f"{clicked_hex.q},{clicked_hex.r}"
            teleports = self.server.game_state.current_map.setdefault("teleports", {})
            if pos_key in teleports:
                if messagebox.askyesno("Teletrasporto", "Rimuovere questo teletrasporto?"):
                    del teleports[pos_key]
                    self.redraw_map_and_players()
            else:
                target_map = simpledialog.askstring("Teletrasporto", "Inserisci il nome del file mappa (es. taverna.json):")
                if target_map:
                    teleports[pos_key] = target_map
                    self.redraw_map_and_players()
            return
            
        mode_str = self.fow_mode_var.get()
        mode = "move"
        if mode_str in ("Cancella Nebbia", "Erase Fog", _t("fow_mode_erase")): mode = "reveal"
        elif mode_str in ("Disegna Nebbia", "Draw Fog", _t("fow_mode_draw")): mode = "hide"
        
        map_hexes = {Hex(q, r) for q, r in self.server.game_state.current_map.get("hexes", [])}
        if clicked_hex not in map_hexes: return
        
        if mode in ("reveal", "hide"):
            drafted = {Hex(h[0], h[1]) for h in self.server.game_state.current_map.get("fow_draft", self.server.game_state.current_map.get("fow_revealed", []))}
            changed = False
            brush_rad = self.fow_brush_radius_var.get() if hasattr(self, 'fow_brush_radius_var') else 0
            if brush_rad > 0:
                target_hexes = get_sphere_hexes(clicked_hex, brush_rad)
            else:
                target_hexes = [clicked_hex]
                
            for h in target_hexes:
                if h in map_hexes:
                    if mode == "reveal" and h not in drafted:
                        drafted.add(h)
                        changed = True
                    elif mode == "hide" and h in drafted:
                        drafted.remove(h)
                        changed = True
                
            if changed:
                self.server.game_state.current_map["fow_draft"] = [[h.q, h.r] for h in drafted]
                self.redraw_map_and_players()
            return

        sel_indices = self.player_listbox.curselection()
        if not sel_indices: return
        
        display_text = self.player_listbox.get(sel_indices[0])
        if display_text.startswith('---'): return
        selected_name = display_text.split(" (HP")[0].replace("▶", "").strip()

        if self.server.game_state.move_player(selected_name, [clicked_hex.q, clicked_hex.r]):
            broadcast(self.server.game_state, make_player_move(selected_name, [clicked_hex.q, clicked_hex.r]))
            self.redraw_map_and_players()
    
    def redraw_map_and_players(self):
        map_data = self.server.game_state.current_map
        players_data = {}
        for p in self.server.game_state.get_all_players():
            players_data[p.name] = {
                "position": p.position,
                "hp": p.hp,
                "hp_max": p.max_hp,
                "is_party_member": getattr(p, "is_party_member", False),
                "conditions": list(getattr(p, "conditions", [])),
                "size_mult": getattr(p, "size_mult", 1),
                "aura_radius": getattr(p, "aura_radius", 0),
                "aura_color": getattr(p, "aura_color", "yellow"),
                "light_radius": getattr(p, "light_radius", 0),
                "light_color": getattr(p, "light_color", "#FFD700"),
                "avatar_b64": getattr(p, "avatar_b64", None),
                "is_hidden": getattr(p, "is_hidden", False),
                "legendary_resistances_max": getattr(p, "legendary_resistances_max", 0),
                "legendary_actions_max": getattr(p, "legendary_actions_max", 0),
            }
        turn_player = self.server.game_state.get_current_turn_player()
        turn_name = turn_player.name if turn_player else ""
        view_name = ""
        if getattr(self, "dm_player_view_var", None) and self.dm_player_view_var.get():
            view_name = "DM_TEST"
            if hasattr(self, 'player_listbox') and self.player_listbox.curselection():
                display_text = self.player_listbox.get(self.player_listbox.curselection()[0])
                if not display_text.startswith('---'):
                    sel_pname = display_text.split(" (HP")[0].replace("▶", "").strip()
                    if sel_pname in players_data:
                        view_name = sel_pname
        
        time_hour = getattr(self.server.game_state, "time_hour", 12)
        weather = getattr(self.server.game_state, "weather", "Sereno")
        combat_active = getattr(self.server.game_state, "combat_active", False)
        combat_order = [p.name for p in self.server.game_state.players] if combat_active else []
        round_number = getattr(self.server.game_state, "round_number", 1)
        
        self._update_map_scale_pill()
        self.map_canvas.update_data(
            map_data, 
            players_data, 
            player_name=view_name, 
            turn_player_name=turn_name, 
            aoes_data=getattr(self.server.game_state, "active_aoes", []),
            time_hour=time_hour,
            weather=weather,
            combat_active=combat_active,
            combat_order=combat_order,
            round_number=round_number
        )

    def _update_map_scale_pill(self):
        if not hasattr(self, "top_status_scale_lbl"):
            return
        from common.i18n import get_map_scale_info
        cur_map = getattr(self.server.game_state, "current_map", None) if hasattr(self, "server") and hasattr(self.server, "game_state") else None
        info = get_map_scale_info(cur_map)
        per_hex = info["per_hex"]
        per_hex_str = str(int(per_hex)) if per_hex == int(per_hex) else f"{per_hex:g}"
        self.top_status_scale_lbl.config(
            text=f"🗺️ {info['scale_name']}: 1 hex = {per_hex_str} {info['unit_label']}"
        )

    def _show_map_scale_menu(self, event=None):
        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(
            label="⚔️ Combattimento (1 hex = 5 ft / 1.5 m)",
            command=lambda: self._set_active_map_scale("combat")
        )
        menu.add_command(
            label="🧭 Esplorazione / POI (1 hex = 1 mi / 1.5 km)",
            command=lambda: self._set_active_map_scale("exploration")
        )
        menu.add_command(
            label="🌍 Mondo / Regione (1 hex = 6 mi / 9 km)",
            command=lambda: self._set_active_map_scale("world")
        )
        menu.add_separator()
        menu.add_command(
            label="📏 Scala Personalizzata...",
            command=lambda: self._set_active_map_scale("custom")
        )
        try:
            x = event.x_root if event else self.top_status_scale_lbl.winfo_rootx()
            y = event.y_root if event else (self.top_status_scale_lbl.winfo_rooty() + self.top_status_scale_lbl.winfo_height())
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _set_active_map_scale(self, scale_type: str):
        if not hasattr(self, "server") or not getattr(self.server.game_state, "current_map", None):
            return
        cur_map = self.server.game_state.current_map
        if scale_type == "custom":
            from common.i18n import get_distance_unit
            u_default = "m" if get_distance_unit() == "m" else "ft"
            val_str = simpledialog.askstring(
                "Scala Mappa Personalizzata",
                f"Inserisci la distanza per 1 esagono (es. '10 ft', '3 m', '24 mi', '36 km'):",
                initialvalue=f"10 {u_default}",
                parent=self.master
            )
            if not val_str:
                return
            parts = val_str.strip().replace(",", ".").split()
            try:
                val_num = float(parts[0])
            except (ValueError, IndexError):
                messagebox.showerror("Errore", "Valore numerico non valido per la scala.")
                return
            u_custom = parts[1].lower() if len(parts) > 1 and parts[1].lower() in ("ft", "m", "mi", "km") else u_default
            cur_map["map_scale_type"] = "custom"
            cur_map["hex_scale_value"] = val_num
            cur_map["hex_scale_unit"] = u_custom
        else:
            cur_map["map_scale_type"] = scale_type
            cur_map.pop("hex_scale_value", None)
            cur_map.pop("hex_scale_unit", None)

        self._update_map_scale_pill()
        self.redraw_map_and_players()
        from common.protocol import make_map_data_update_broadcast
        from server.network import broadcast
        broadcast(self.server.game_state, make_map_data_update_broadcast(cur_map))
        from common.i18n import get_map_scale_info
        info = get_map_scale_info(cur_map)
        per_hex = info["per_hex"]
        per_hex_str = str(int(per_hex)) if per_hex == int(per_hex) else f"{per_hex:g}"
        self.show_toast(
            f"Scala mappa aggiornata: {info['scale_name']} (1 hex = {per_hex_str} {info['unit_label']})",
            title="Scala Mappa",
            toast_type="info"
        )

    def _show_grid_type_menu(self, event=None):
        menu = tk.Menu(self.master, tearoff=0, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=self.default_font)
        menu.add_command(label=_t("grid_hex"), command=lambda: self.set_map_grid_type("hex"))
        menu.add_command(label=_t("grid_square"), command=lambda: self.set_map_grid_type("square"))
        menu.add_command(label=_t("grid_none"), command=lambda: self.set_map_grid_type("none"))
        try:
            x = event.x_root if event else self.top_status_grid_lbl.winfo_rootx()
            y = event.y_root if event else (self.top_status_grid_lbl.winfo_rooty() + self.top_status_grid_lbl.winfo_height())
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def set_map_grid_type(self, grid_type):
        if not hasattr(self, "server") or not getattr(self.server, "game_state", None):
            return
        if not getattr(self.server.game_state, "current_map", None):
            return
        cur_map = self.server.game_state.current_map
        cur_map["grid_type"] = grid_type
        grid_names = {"hex": _t("grid_hex"), "square": _t("grid_square"), "none": _t("grid_none")}
        name_str = grid_names.get(grid_type, grid_type)
        if hasattr(self, "top_status_grid_lbl"):
            self.top_status_grid_lbl.config(text=f"🌐 {_t('grid_type_menu')}: {name_str}")
        self.redraw_map_and_players()
        from common.protocol import make_map_data_update_broadcast
        from server.network import broadcast
        broadcast(self.server.game_state, make_map_data_update_broadcast(cur_map))
        self.show_toast(f"Tipo griglia impostato a: {name_str}", title=_t("grid_type_menu"), toast_type="info")

    def set_selected_player_size(self, size_name):
        player_name = self.get_selected_player_name()
        if not player_name:
            return
        player = self.server.game_state.find_player(player_name)
        if player:
            player.size = size_name
            self.server.game_state._trigger_gui_update()
            from common.protocol import make_game_state
            from server.network import broadcast
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            self.redraw_map_and_players()
            self.show_toast(f"Dimensioni di {player_name}: {size_name.title()}", title="Token Size", toast_type="info")

    def toggle_selected_player_gm_layer(self):
        player_name = self.get_selected_player_name()
        if not player_name:
            return
        player = self.server.game_state.find_player(player_name)
        if player:
            cur_layer = getattr(player, "layer", "token")
            new_layer = "gm" if cur_layer != "gm" else "token"
            player.layer = new_layer
            self.server.game_state._trigger_gui_update()
            from common.protocol import make_game_state
            from server.network import broadcast
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            self.redraw_map_and_players()
            status_text = "spostato nel LIVELLO GM (invisibile ai giocatori)" if new_layer == "gm" else "spostato nel LIVELLO TOKEN (visibile)"
            self.show_toast(f"{player_name} {status_text}", title="GM Layer", toast_type="info")

    def toggle_whiteboard_pen(self):
        if not self.map_canvas: return
        is_active = self.map_canvas.toggle_pen_mode()
        if hasattr(self, "btn_pen"):
            self.btn_pen.config(style="Accent.TButton" if is_active else "Tool.TButton")
        self.show_toast("Modalità Penna Disegno: " + ("Attiva" if is_active else "Disattivata"), title="Lavagna", toast_type="info")

    def clear_whiteboard_drawings(self):
        if not messagebox.askyesno(_t("tool_clear_drawings"), "Cancellare tutti i disegni a mano libera dalla mappa?"):
            return
        if self.map_canvas:
            self.map_canvas.clear_drawings()
        if hasattr(self, "server") and hasattr(self.server, "game_state"):
            self.server.game_state.drawn_lines = []
            from common.protocol import make_clear_drawings_broadcast
            from server.network import broadcast
            broadcast(self.server.game_state, make_clear_drawings_broadcast())
            self.server.game_state._trigger_gui_update()
        self.show_toast("Disegni mappa cancellati", title="Lavagna", toast_type="info")

    def export_session_log(self):
        log_text = ""
        if hasattr(self, "chat_tabs"):
            for tname, txt_widget in self.chat_tabs.items():
                content = txt_widget.get("1.0", tk.END).strip()
                if content:
                    log_text += f"\n\n--- [TAB: {tname}] ---\n\n" + content
        elif hasattr(self, "chat_display"):
            log_text = self.chat_display.get("1.0", tk.END).strip()

        if not log_text.strip():
            messagebox.showinfo(_t("export_log_title"), _t("export_log_empty"))
            return

        from tkinter import filedialog
        from datetime import datetime
        default_filename = f"Session_Log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = filedialog.asksaveasfilename(
            title=_t("menu_export_session_log"),
            initialfile=default_filename,
            filetypes=[("Markdown (*.md)", "*.md"), ("HTML (*.html)", "*.html"), ("Text (*.txt)", "*.txt")]
        )
        if not filepath:
            return

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        campaign_name = getattr(self.server.game_state, 'active_campaign', None)
        campaign_str = campaign_name.name if campaign_name else "D&D Session"

        if filepath.endswith(".html"):
            html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>{_t('export_log_title')} - {campaign_str}</title>
<style>
body {{ background-color: #121316; color: #E5E7EB; font-family: 'Segoe UI', Tahoma, sans-serif; padding: 24px; line-height: 1.6; }}
h1 {{ color: #F59E0B; border-bottom: 2px solid #D97706; padding-bottom: 8px; }}
.meta {{ color: #9CA3AF; font-size: 0.9em; margin-bottom: 20px; }}
.log-box {{ background-color: #1A1B1E; border: 1px solid #374151; border-radius: 8px; padding: 18px; white-space: pre-wrap; font-family: 'Consolas', monospace; }}
</style>
</head>
<body>
<h1>📜 {_t('export_log_title')} - {campaign_str}</h1>
<div class="meta">Esportato il: {now_str} • D&D OmniCompanion</div>
<div class="log-box">{log_text}</div>
</body>
</html>"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
        else:
            md_content = f"""# 📜 {_t('export_log_title')} - {campaign_str}
**Data Esportazione:** {now_str}
**Piattaforma:** D&D OmniCompanion

---

```
{log_text}
```
"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)

        messagebox.showinfo(_t("export_log_title"), _t("export_log_saved").format(path=filepath))

    def open_calendar_dialog(self):
        try:
            from components.calendar_ui import CalendarDialog
            win = CalendarDialog(self.master, self.server.game_state, is_dm=True, network_or_server=self.server)
            win.grab_set()
        except ImportError as e:
            from common.messagebox import messagebox
            messagebox.showerror("Errore", f"Impossibile aprire il calendario: {e}")

    def open_quest_dialog(self):
        try:
            from components.quest_ui import QuestLogDialog
            win = QuestLogDialog(self.master, self.server.game_state, is_dm=True, network_or_server=self.server)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire il diario: {e}")

    def open_shop_dialog(self):
        try:
            from components.shop_ui import ShopDialog
            win = ShopDialog(self.master, self.server.game_state, is_dm=True, network_or_server=self.server)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire i negozi: {e}")

    def open_travel_panel(self):
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        from common.theme import (
            apply_modern_window_style, BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT,
            BORDER_COLOR, ACCENT_GOLD, ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE,
            TEXT_COLOR, TEXT_MUTED
        )
        apply_modern_window_style(win)
        win.title("🧭 Gestione Viaggio & Hex Crawl (5e)")
        win.minsize(620, 720)
        
        gs = self.server.game_state
        months = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
        month_name = months[gs.time_month] if hasattr(gs, 'time_month') and 1 <= gs.time_month <= 12 else "Mese Sconosciuto"

        # Container scrollabile
        canvas = tk.Canvas(win, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Intestazione
        header_f = tk.Frame(scrollable_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        header_f.pack(fill=tk.X, padx=14, pady=(12, 8))
        tk.Label(header_f, text="🧭 PANNELLO GESTIONE VIAGGIO & HEX CRAWL", font=("Georgia", 13, "bold"),
                 bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(header_f, text="Controlla andatura, tiri di navigazione, imboscate nemiche, caccia e sostentamento del party.",
                 font=("Segoe UI", 9), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", padx=12, pady=(0, 10))

        # Parametri e Ambiente
        env_f = tk.Frame(scrollable_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1)
        env_f.pack(fill=tk.X, padx=14, pady=6)
        tk.Label(env_f, text="📍 STATO DELL'AMBIENTE & MARCIA", font=("Segoe UI", 10, "bold"),
                 bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(anchor="w", padx=12, pady=(8, 4))
        
        lbl_current_time = tk.Label(env_f, text=f"📅 Data & Ora: {gs.time_day} {month_name} {getattr(gs, 'time_year', 1492)} - {gs.time_hour:02d}:00  |  ⛅ Clima: {getattr(gs, 'weather', 'Sereno')}",
                                    font=("Segoe UI", 9), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR)
        lbl_current_time.pack(anchor="w", padx=12, pady=2)
        
        hours_today = getattr(gs, "travel_hours_today", 0)
        h_color = ACCENT_RED if hours_today > 8 else TEXT_COLOR
        h_text = f"⏱️ Ore Viaggiate Oggi: {hours_today} / 8h"
        if hours_today > 8:
            h_text += f" ⚠️ Marcia Forzata Attiva (CD {10 + (hours_today - 8)})"
        lbl_hours = tk.Label(env_f, text=h_text, font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=h_color)
        lbl_hours.pack(anchor="w", padx=12, pady=2)

        # Selezione Andatura e Terreno
        param_grid = tk.Frame(env_f, bg=SURFACE_COLOR_ALT)
        param_grid.pack(fill=tk.X, padx=12, pady=(6, 10))
        
        tk.Label(param_grid, text="Andatura di Viaggio (5e):", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).grid(row=0, column=0, sticky="w", pady=2)
        pace_var = tk.StringVar(value=getattr(gs, "travel_pace", "Normale"))
        pace_frame = tk.Frame(param_grid, bg=SURFACE_COLOR_ALT)
        pace_frame.grid(row=0, column=1, sticky="w", padx=10, pady=2)
        
        def on_pace_change():
            gs.travel_pace = pace_var.get()
            self._update_roster_labels()
            
        for p_opt, p_desc in [("Lenta", "Lenta (2 mi/h, +5 PP, Furtivo)"), ("Normale", "Normale (3 mi/h)"), ("Veloce", "Veloce (4 mi/h, -5 PP, no caccia)")]:
            ttk.Radiobutton(pace_frame, text=p_opt, variable=pace_var, value=p_opt, command=on_pace_change).pack(side=tk.LEFT, padx=5)

        tk.Label(param_grid, text="Terreno Attuale:", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).grid(row=1, column=0, sticky="w", pady=6)
        terrain_var = tk.StringVar(value=getattr(gs, "travel_terrain", "Foresta"))
        terrain_combo = ttk.Combobox(param_grid, textvariable=terrain_var, state="readonly", width=30,
                                     values=["Pianura / Strada (CD 10)", "Foresta / Collina (CD 15)", "Palude / Montagna (CD 18)", "Deserto / Landa (CD 20)"])
        terrain_combo.grid(row=1, column=1, sticky="w", padx=10, pady=6)
        
        def on_terrain_select(event=None):
            val = terrain_var.get().split()[0]
            gs.travel_terrain = val
        terrain_combo.bind("<<ComboboxSelected>>", on_terrain_select)

        # Sezione Formazione e Roster Party
        party_f = tk.Frame(scrollable_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        party_f.pack(fill=tk.X, padx=14, pady=6)
        tk.Label(party_f, text="👥 FORMAZIONE E RUOLI DEL GRUPPO (LIVE)", font=("Segoe UI", 10, "bold"),
                 bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=12, pady=(8, 2))
        
        roster_container = tk.Frame(party_f, bg=SURFACE_COLOR)
        roster_container.pack(fill=tk.X, padx=12, pady=(4, 10))

        # Helper per calcolare bonus statistici 5e
        def get_stat_mod(char_sheet, stat_name):
            if not char_sheet: return 0
            val = char_sheet.get("attributes", {}).get(stat_name, 10)
            try: return (int(val) - 10) // 2
            except: return 0

        def get_skill_mod(char_sheet, skill_name, stat_name):
            if not char_sheet: return 0
            mod = get_stat_mod(char_sheet, stat_name)
            sk = char_sheet.get("skills", {}).get(skill_name, 0)
            try: sk_val = int(sk)
            except: sk_val = 0
            return mod + sk_val

        def get_passive_perception(p, pace):
            sheet = getattr(p, "full_sheet", {}) or {}
            base_bonus = get_skill_mod(sheet, "Percezione", "SAG")
            pp = 10 + base_bonus
            if pace == "Lenta": pp += 5
            elif pace == "Veloce": pp -= 5
            return pp

        party_labels = []
        def refresh_roster():
            for widget in roster_container.winfo_children():
                widget.destroy()
            party_members = [p for p in gs.get_all_players() if getattr(p, "is_party_member", False) or not gs.combat_active]
            if not party_members: party_members = gs.get_all_players()
            
            cur_pace = pace_var.get()
            for p in party_members:
                row_f = tk.Frame(roster_container, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1)
                row_f.pack(fill=tk.X, pady=2)
                
                name_lbl = tk.Label(row_f, text=f"👤 {p.name}", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD, width=14, anchor="w")
                name_lbl.pack(side=tk.LEFT, padx=8, pady=4)
                
                order_val = getattr(p, "marching_order", "Centro")
                order_lbl = tk.Label(row_f, text=f"Pos: [{order_val}]", font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, width=16, anchor="w")
                order_lbl.pack(side=tk.LEFT, padx=4)
                
                role_val = getattr(p, "travel_role", "Nessuna")
                sheet = getattr(p, "full_sheet", {}) or {}
                
                stat_desc = ""
                if role_val == "Navigatore":
                    surv_mod = get_skill_mod(sheet, "Sopravvivenza", "SAG")
                    if cur_pace == "Veloce": surv_mod -= 5
                    stat_desc = f"(Sopravvivenza {surv_mod:+d})"
                elif role_val == "Sentinella":
                    pp = get_passive_perception(p, cur_pace)
                    stat_desc = f"(PP: {pp})"
                elif role_val == "Cacciatore":
                    surv_mod = get_skill_mod(sheet, "Sopravvivenza", "SAG")
                    stat_desc = f"(Sopravvivenza {surv_mod:+d})"
                elif role_val == "Furtivo":
                    stealth_mod = get_skill_mod(sheet, "Furtività", "DES")
                    stat_desc = f"(Furtività {stealth_mod:+d})"
                
                role_lbl = tk.Label(row_f, text=f"Ruolo: {role_val} {stat_desc}", font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, width=28, anchor="w")
                role_lbl.pack(side=tk.LEFT, padx=4)
                
                exh = getattr(p, "exhaustion_level", 0)
                exh_color = ACCENT_RED if exh > 0 else TEXT_MUTED
                exh_text = f"Sfinimento: {exh}/6" if exh > 0 else "Sfinimento: 0"
                tk.Label(row_f, text=exh_text, font=("Segoe UI", 8, "bold"), bg=SURFACE_COLOR_ALT, fg=exh_color, width=14, anchor="e").pack(side=tk.RIGHT, padx=8)

        self._update_roster_labels = refresh_roster
        refresh_roster()

        # Funzione Consumo Razioni Party
        def consume_rations():
            from common.protocol import make_chat_broadcast, make_game_state
            from server.network import broadcast
            
            party_members = [p for p in gs.get_all_players() if getattr(p, "is_party_member", False) or not gs.combat_active]
            if not party_members: party_members = gs.get_all_players()

            msg = "🥖 [SISTEMA] CONSUMO RAZIONI & SOSTENTAMENTO GIORNALIERO:\n"
            for p in party_members:
                sheet = getattr(p, "full_sheet", None)
                if not sheet:
                    continue
                
                has_ration = False
                has_water = False

                # 1. Controlla e scala da inventory_grid
                grid = sheet.get("inventory_grid", [])
                if isinstance(grid, list):
                    for idx, it in enumerate(grid):
                        if not it or not isinstance(it, dict): continue
                        name_lower = str(it.get("name", "")).lower()
                        qty = int(it.get("qty", it.get("quantity", 1)) or 1)
                        if not has_ration and ("razion" in name_lower or "cibo" in name_lower) and qty > 0:
                            if qty - 1 <= 0:
                                grid[idx] = None
                            else:
                                if "qty" in it: it["qty"] = qty - 1
                                if "quantity" in it: it["quantity"] = qty - 1
                            has_ration = True
                        elif not has_water and ("acqua" in name_lower or "otre" in name_lower) and qty > 0:
                            if qty - 1 <= 0:
                                grid[idx] = None
                            else:
                                if "qty" in it: it["qty"] = qty - 1
                                if "quantity" in it: it["quantity"] = qty - 1
                            has_water = True

                # 2. Controlla e scala da inventory classico se non ancora dedotto
                inv = sheet.get("inventory", [])
                if isinstance(inv, list):
                    for it in inv:
                        if not isinstance(it, dict): continue
                        name_lower = str(it.get("name", "")).lower()
                        qty = int(it.get("quantity", it.get("qty", 1)) or 1)
                        if not has_ration and ("razion" in name_lower or "cibo" in name_lower) and qty > 0:
                            it["quantity"] = qty - 1
                            has_ration = True
                        elif not has_water and ("acqua" in name_lower or "otre" in name_lower) and qty > 0:
                            it["quantity"] = qty - 1
                            has_water = True
                    sheet["inventory"] = [i for i in inv if not isinstance(i, dict) or int(i.get("quantity", i.get("qty", 1)) or 1) > 0]

                if not has_ration or not has_water:
                    p.exhaustion_level = min(6, getattr(p, "exhaustion_level", 0) + 1)
                    conds = [c for c in getattr(p, "conditions", []) if not c.startswith("Sfinimento")]
                    conds.append(f"Sfinimento (Liv. {p.exhaustion_level})")
                    p.conditions = conds
                    sheet["exhaustion_level"] = p.exhaustion_level
                    sheet["conditions"] = conds
                    msg += f"❌ {p.name}: Provviste insufficienti! Subisce Sfinimento (Livello {p.exhaustion_level})\n"
                else:
                    msg += f"✅ {p.name}: Ha consumato 1 Razione e 1 Otre d'Acqua.\n"

            gs._trigger_gui_update()
            broadcast(gs, make_game_state(gs.get_state_dict()))
            broadcast(gs, make_chat_broadcast("Sistema", msg))
            self.log_to_chat(msg)
            refresh_roster()
            messagebox.showinfo("Razioni Consumate", "Razioni e acqua giornaliere elaborate per tutti i membri del gruppo.")

        # Motore di Avanzamento Viaggio (5e Automated Engine)
        def do_travel(hours=4):
            from common.dice import roll_dice
            from common.protocol import make_chat_broadcast, make_game_state
            from server.network import broadcast

            cur_pace = pace_var.get()
            cur_terrain = terrain_var.get().split()[0]
            gs.travel_pace = cur_pace
            gs.travel_terrain = cur_terrain

            # Calcolo CD Terreno per Navigazione
            terrain_dc = 15
            if "Pianura" in terrain_var.get(): terrain_dc = 10
            elif "Foresta" in terrain_var.get(): terrain_dc = 15
            elif "Palude" in terrain_var.get() or "Montagna" in terrain_var.get(): terrain_dc = 18
            elif "Deserto" in terrain_var.get(): terrain_dc = 20

            party_members = [p for p in gs.get_all_players() if getattr(p, "is_party_member", False) or not gs.combat_active]
            if not party_members: party_members = gs.get_all_players()

            # 1. TIRO NAVIGATORE (Sopravvivenza)
            navigators = [p for p in party_members if getattr(p, "travel_role", "") == "Navigatore"]
            nav_msg = ""
            if navigators:
                nav = navigators[0]
                sheet = getattr(nav, "full_sheet", {}) or {}
                bonus = get_skill_mod(sheet, "Sopravvivenza", "SAG")
                if cur_pace == "Veloce": bonus -= 5
                d20 = roll_dice("1d20")["total"]
                nav_tot = d20 + bonus
                if nav_tot >= terrain_dc:
                    nav_msg = f"🧭 ROTTA MANTENUTA: Il Navigatore {nav.name} orienta la marcia! (Tiro: {d20}{bonus:+d}={nav_tot} vs CD {terrain_dc})"
                else:
                    nav_msg = f"⚠️ SMARRITI: Il Navigatore {nav.name} ha perso l'orientamento! (Tiro: {d20}{bonus:+d}={nav_tot} vs CD {terrain_dc})"
            else:
                d20 = roll_dice("1d20")["total"]
                if d20 >= terrain_dc:
                    nav_msg = f"🧭 ROTTA MANTENUTA: Il gruppo avanza a vista senza navigatore (Tiro: {d20} vs CD {terrain_dc})"
                else:
                    nav_msg = f"⚠️ SMARRITI: Senza navigatore il gruppo perde la rotta! (Tiro: {d20} vs CD {terrain_dc})"

            # 2. INCONTRO CASUALE & SENTINELLE
            enc_roll = roll_dice("1d20")["total"]
            has_encounter = (enc_roll >= 16)
            enc_msg = ""
            if has_encounter:
                ambush_dc = roll_dice("1d20+2")["total"]
                sentinels = [p for p in party_members if getattr(p, "travel_role", "") == "Sentinella"]
                if sentinels:
                    best_sentinel = max(sentinels, key=lambda s: get_passive_perception(s, cur_pace))
                    best_pp = get_passive_perception(best_sentinel, cur_pace)
                    if best_pp >= ambush_dc:
                        enc_msg = f"⚔️ INCONTRO CASUALE! La Sentinella {best_sentinel.name} ha avvistato il pericolo in anticipo! (Percezione Passiva {best_pp} vs Insidia CD {ambush_dc}) - Nessuna sorpresa!"
                    else:
                        enc_msg = f"⚠️ IMBOSCATA OSTILE! I nemici colgono il gruppo di sorpresa! (Insidia CD {ambush_dc} superata vs Percezione Passiva {best_pp} di {best_sentinel.name})"
                else:
                    enc_msg = f"⚔️ INCONTRO CASUALE RILEVATO! (Tiro Incontro: {enc_roll}/20 - Nessuna sentinella di guardia)"
            else:
                enc_msg = f"🌿 Marcia tranquilla: nessun pericolo ostile lungo la via (Tiro: {enc_roll}/20)."

            # 3. CACCIA & FORAGING
            hunt_msg = ""
            if cur_pace == "Veloce":
                hunt_msg = "🏹 Andatura Veloce: impossibile dedicarsi alla caccia o raccolta."
            else:
                hunters = [p for p in party_members if getattr(p, "travel_role", "") == "Cacciatore"]
                if hunters:
                    h = hunters[0]
                    sheet = getattr(h, "full_sheet", {}) or {}
                    surv_bonus = get_skill_mod(sheet, "Sopravvivenza", "SAG")
                    h_roll = roll_dice("1d20")["total"] + surv_bonus
                    if h_roll >= 15:
                        food_found = roll_dice("1d6")["total"] + max(0, get_stat_mod(sheet, "SAG"))
                        hunt_msg = f"🏹 CACCIA: {h.name} raccoglie con successo {food_found} razioni di cibo e acqua fresca! (Tiro: {h_roll} vs CD 15)"
                    else:
                        hunt_msg = f"🏹 CACCIA: {h.name} non trova provviste sufficienti in quest'area (Tiro: {h_roll} vs CD 15)."

            # 4. MARCIA FORZATA (Ore > 8)
            gs.travel_hours_today = getattr(gs, "travel_hours_today", 0) + hours
            exhaustion_logs = []
            if gs.travel_hours_today > 8:
                extra_hours = gs.travel_hours_today - 8
                con_dc = 10 + extra_hours
                for p in party_members:
                    sheet = getattr(p, "full_sheet", {}) or {}
                    cos_mod = get_stat_mod(sheet, "COS")
                    d20_con = roll_dice("1d20")["total"]
                    con_tot = d20_con + cos_mod
                    if con_tot < con_dc:
                        p.exhaustion_level = min(6, getattr(p, "exhaustion_level", 0) + 1)
                        conds = [c for c in getattr(p, "conditions", []) if not c.startswith("Sfinimento")]
                        conds.append(f"Sfinimento (Liv. {p.exhaustion_level})")
                        p.conditions = conds
                        if sheet:
                            sheet["exhaustion_level"] = p.exhaustion_level
                            sheet["conditions"] = conds
                        exhaustion_logs.append(f"😫 {p.name}: Fallisce TS COS (Tiro {d20_con}{cos_mod:+d}={con_tot} vs CD {con_dc}) -> Guadagna Sfinimento (Livello {p.exhaustion_level})")
                    else:
                        exhaustion_logs.append(f"💪 {p.name}: Supera TS COS (Tiro {con_tot} vs CD {con_dc}) e resiste alla fatica.")

            # Avanzamento del tempo sul server
            self.advance_time(hours, is_rest=False)

            months_list = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
            cur_month = months_list[gs.time_month] if hasattr(gs, 'time_month') and 1 <= gs.time_month <= 12 else "Mese"

            msg = f"========================================\n"
            msg += f"🧭 RESOCONTO MARCIA ({hours} ORE) - {gs.time_day} {cur_month} {getattr(gs, 'time_year', 1492)} - {gs.time_hour:02d}:00\n"
            msg += f"========================================\n"
            msg += f"• Andatura: {cur_pace} | Terreno: {cur_terrain} | Ore oggi: {gs.travel_hours_today}/8h\n"
            msg += f"• {nav_msg}\n"
            msg += f"• {enc_msg}\n"
            if hunt_msg: msg += f"• {hunt_msg}\n"
            if exhaustion_logs:
                msg += f"⚠️ MARCIA FORZATA (CD {10 + (gs.travel_hours_today - 8)}):\n"
                for el in exhaustion_logs:
                    msg += f"  - {el}\n"
            msg += "========================================"

            gs.add_calendar_event(f"Avanzamento Viaggio {hours}h ({cur_pace}, {cur_terrain}). Incontro: {enc_msg}")
            self.log_to_chat(msg, tab_name="Sistema")
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", msg))
            broadcast(self.server.game_state, make_game_state(gs.get_state_dict()))
            win.destroy()

        # Pulsantiere Azioni
        action_f = tk.Frame(scrollable_frame, bg=BG_COLOR)
        action_f.pack(fill=tk.X, padx=14, pady=16)

        btn_advance4 = ttk.Button(action_f, text="🚶 Avanza 4 Ore (Mezza Giornata)", command=lambda: do_travel(4), style="Primary.TButton")
        btn_advance4.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        btn_advance8 = ttk.Button(action_f, text="🏃 Avanza 8 Ore (Giornata Intera)", command=lambda: do_travel(8), style="Primary.TButton")
        btn_advance8.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        btn_consume = ttk.Button(action_f, text="🥖 Consuma Razioni Party", command=consume_rations, style="Info.TButton")
        btn_consume.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

        ttk.Button(action_f, text="Chiudi", command=win.destroy).pack(side=tk.RIGHT, padx=4)

    def load_map_from_file(self):
        maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
        file_path=filedialog.askopenfilename(initialdir=maps_dir, filetypes=[("Mappe D&D", "*.json")])
        if not file_path: return
        try:
            with open(file_path, 'r') as f: map_data=json.load(f)
            if 'base_image_path' in map_data and map_data['base_image_path']:
                with open(map_data['base_image_path'], "rb") as image_file:
                    encoded_string=base64.b64encode(image_file.read()).decode('utf-8')
                    map_data['bg_image_data']=encoded_string
            
            self.server.game_state.load_map(map_data)
            self.fow_enabled_var.set(self.server.game_state.current_map.get("fow_enabled", False))
            self.redraw_map_and_players()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            self.log_to_chat(f"[SISTEMA] Mappa '{os.path.basename(file_path)}' caricata.")
        except Exception as e:
            messagebox.showerror("Errore Caricamento", f"Impossibile caricare la mappa: {e}")

    def save_session(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Sessione D&D", "*.json")])
        if not file_path: return
        try:
            self.server.game_state.save_session(file_path)
            messagebox.showinfo("Successo", "Sessione salvata correttamente.")
        except Exception as e:
            messagebox.showerror("Errore Salvataggio", f"Impossibile salvare la sessione: {e}")

    def load_session(self):
        file_path = filedialog.askopenfilename(filetypes=[("Sessione D&D", "*.json")])
        if not file_path: return
        try:
            self.server.game_state.load_session(file_path)
            if self.server.game_state.current_map:
                self.fow_enabled_var.set(self.server.game_state.current_map.get("fow_enabled", False))
            self.redraw_map_and_players()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            messagebox.showinfo("Successo", "Sessione caricata correttamente.")
        except Exception as e:
            messagebox.showerror("Errore Caricamento", f"Impossibile caricare la sessione: {e}")

    def open_new_campaign_dialog(self):
        from server.campaign_editor_ui import CampaignEditorDialog
        from common.campaign import Campaign
        new_camp = Campaign(name="Nuova Campagna")
        def on_saved(camp):
            camp.apply_to_game_state(self.server.game_state)
            if self.server.game_state.current_map:
                self.fow_enabled_var.set(self.server.game_state.current_map.get("fow_enabled", False))
                self.redraw_map_and_players()
            self.log_to_chat(f"[SISTEMA] Nuova campagna '{camp.name}' creata e applicata.")
        dlg = CampaignEditorDialog(self.master, campaign=new_camp, game_state=self.server.game_state, on_save_callback=on_saved)

    def open_load_campaign_dialog(self):
        from server.campaign_editor_ui import CampaignSelectorDialog
        def on_selected(camp):
            camp.apply_to_game_state(self.server.game_state)
            if self.server.game_state.current_map:
                self.fow_enabled_var.set(self.server.game_state.current_map.get("fow_enabled", False))
                self.redraw_map_and_players()
            self.log_to_chat(f"[SISTEMA] Campagna '{camp.name}' caricata e attiva.")
            messagebox.showinfo("Campagna Caricata", f"Campagna '{camp.name}' caricata con successo!", parent=self.master)
        dlg = CampaignSelectorDialog(self.master, on_select_callback=on_selected)

    def open_campaign_editor_dialog(self):
        from server.campaign_editor_ui import CampaignEditorDialog
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        if active_camp:
            def on_saved(camp):
                camp.apply_to_game_state(self.server.game_state)
                self.log_to_chat(f"[SISTEMA] Campagna '{camp.name}' aggiornata.")
            dlg = CampaignEditorDialog(self.master, campaign=active_camp, game_state=self.server.game_state, on_save_callback=on_saved)
        else:
            self.open_load_campaign_dialog()

    def deploy_campaign_encounter_dialog(self):
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        if not active_camp or not active_camp.encounters:
            if messagebox.askyesno(_t("msg_no_encounter_title", default="Nessun Incontro"), _t("msg_no_encounter_desc", default="Nessuna campagna attiva con incontri preparati. Vuoi aprire l'Editor Campagna?"), parent=self.master):
                self.open_campaign_editor_dialog()
            return
            
        dlg = tk.Toplevel(self.master)
        dlg.title(_t("deploy_encounter_title", default="Schiera Incontro della Campagna"))
        dlg.minsize(520, 360)
        dlg.transient(self.master)
        dlg.grab_set()
        apply_modern_window_style(dlg)
        dlg.configure(bg=BG_COLOR)
        
        container = tk.Frame(dlg, bg=BG_COLOR, padx=15, pady=12)
        container.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(container, text=_t("deploy_encounter_header", default="⚔️ Incontri Preparati della Campagna"), font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 4))
        tk.Label(container, text=_t("deploy_encounter_subtitle", default="Seleziona l'incontro da schierare sulla mappa corrente:"), font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 8))
        
        tree_frame = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        cols = ("Nome", "Atto", "Mostri", "Descrizione")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=6)
        tree.heading("Nome", text=_t("col_encounter_name", default="Nome Incontro"))
        tree.heading("Atto", text=_t("col_act", default="Atto"))
        tree.heading("Mostri", text=_t("col_monsters", default="Mostri"))
        tree.heading("Descrizione", text=_t("col_notes", default="Note"))
        tree.column("Nome", width=160)
        tree.column("Atto", width=90)
        tree.column("Mostri", width=60, anchor="center")
        tree.column("Descrizione", width=180)
        
        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        for idx, enc in enumerate(active_camp.encounters):
            m_cnt = sum(m.get("count", 1) for m in enc.get("monsters", []))
            tree.insert("", tk.END, iid=str(idx), values=(
                enc.get("name", "Incontro"),
                enc.get("act", "Atto 1"),
                str(m_cnt),
                enc.get("description", "")
            ))
        if active_camp.encounters:
            tree.selection_set("0")
            
        def do_deploy():
            sel = tree.selection()
            if not sel: return
            idx = int(sel[0])
            enc = active_camp.encounters[idx]
            monsters = enc.get("monsters", [])
            self.handle_encounter_start(monsters)
            self.log_to_chat(f"[SISTEMA] Incontro '{enc.get('name')}' schierato dal piano di campagna.")
            dlg.destroy()
            
        btn_box = tk.Frame(container, bg=BG_COLOR)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text=_t("btn_deploy_on_map", default="⚡ Schiera sulla Mappa"), command=do_deploy, style="Gold.TButton").pack(side=tk.RIGHT)
        ttk.Button(btn_box, text=_t("cancel", default="Annulla"), command=dlg.destroy).pack(side=tk.RIGHT, padx=6)

    def switch_campaign_scene_dialog(self):
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        if not active_camp or not active_camp.scenes:
            messagebox.showinfo(_t("msg_no_scene_title", default="Nessuna Scena"), _t("msg_no_scene_desc", default="Nessuna campagna attiva con scene collegate."), parent=self.master)
            return
            
        dlg = tk.Toplevel(self.master)
        dlg.title(_t("switch_scene_title", default="Passa a Scena della Campagna"))
        dlg.minsize(480, 320)
        dlg.transient(self.master)
        dlg.grab_set()
        apply_modern_window_style(dlg)
        dlg.configure(bg=BG_COLOR)
        
        container = tk.Frame(dlg, bg=BG_COLOR, padx=15, pady=12)
        container.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(container, text=_t("switch_scene_header", default="🗺️ Scene della Campagna"), font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 6))
        
        lb_scenes = tk.Listbox(container, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=FONT_MAIN,
                               selectbackground=ACCENT_GOLD, selectforeground=TEXT_DARK,
                               highlightthickness=1, highlightbackground=BORDER_COLOR)
        lb_scenes.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        for sc in active_camp.scenes:
            lb_scenes.insert(tk.END, f"{sc.get('name', 'Scena')}  [{sc.get('map_file', '')}]")
        if active_camp.scenes:
            lb_scenes.selection_set(0)
            
        def do_switch():
            sel = lb_scenes.curselection()
            if not sel: return
            sc = active_camp.scenes[sel[0]]
            map_file = sc.get("map_file")
            map_path = map_file
            if not os.path.isabs(map_path) and active_camp.folder_path:
                cand = os.path.join(active_camp.folder_path, map_path)
                if os.path.exists(cand): map_path = cand
            if not os.path.exists(map_path):
                cand_global = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), map_file)
                if os.path.exists(cand_global): map_path = cand_global
            if os.path.exists(map_path):
                try:
                    with open(map_path, 'r', encoding="utf-8") as f:
                        map_data = json.load(f)
                    if 'base_image_path' in map_data and map_data['base_image_path']:
                        img_path = map_data['base_image_path']
                        if not os.path.isabs(img_path):
                            img_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), img_path)
                        if os.path.exists(img_path):
                            with open(img_path, "rb") as image_file:
                                map_data['bg_image_data'] = base64.b64encode(image_file.read()).decode('utf-8')
                    self.server.game_state.load_map(map_data)
                    self.fow_enabled_var.set(self.server.game_state.current_map.get("fow_enabled", False))
                    self.redraw_map_and_players()
                    broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
                    broadcast(self.server.game_state, make_chat_broadcast("DM", f"Il DM ha spostato il gruppo nella scena: {sc.get('name')}"))
                    self.log_to_chat(f"[SISTEMA] Scena cambiata in: '{sc.get('name')}'.")
                except Exception as e:
                    messagebox.showerror(_t("error", default="Errore"), f"Impossibile caricare la mappa: {e}", parent=dlg)
            dlg.destroy()
            
        btn_box = tk.Frame(container, bg=BG_COLOR)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text=_t("btn_switch_scene", default="Passa a Questa Scena"), command=do_switch, style="Gold.TButton").pack(side=tk.RIGHT)
        ttk.Button(btn_box, text=_t("cancel", default="Annulla"), command=dlg.destroy).pack(side=tk.RIGHT, padx=6)

    def update_state(self):
        self.update_player_list()

    def update_player_list(self):
        current_selection=self.player_listbox.curselection()
        self.player_listbox.delete(0, tk.END)
        
        gs = self.server.game_state
        time_str = f"{gs.time_hour:02d}:00"
        if 6 <= gs.time_hour < 12: period = _t("period_morning")
        elif 12 <= gs.time_hour < 18: period = _t("period_afternoon")
        elif 18 <= gs.time_hour < 22: period = _t("period_evening")
        else: period = _t("period_night")
        
        months = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
        month_name = months[gs.time_month] if hasattr(gs, 'time_month') and 1 <= gs.time_month <= 12 else "Mese Sconosciuto"
        
        self.lbl_time.config(text=f"{gs.time_day} {month_name} {getattr(gs, 'time_year', 1492)} - {time_str} ({period})")
        if hasattr(self, "weather_var") and self.weather_var.get() != translate_weather(gs.weather):
            self.weather_var.set(translate_weather(gs.weather))
            
        if hasattr(self, "lbl_campaign_name"):
            active_c = getattr(gs, "active_campaign", None)
            c_text = _t("campaign_active", name=active_c.name) if active_c else _t("campaign_none")
            self.lbl_campaign_name.config(text=c_text)
            
        # Aggiorna pillole status in alto
        if hasattr(self, "top_status_time_lbl"):
            time_icon = "☀️" if 6 <= gs.time_hour < 18 else "🌙"
            self.top_status_time_lbl.config(text=f"{time_icon} {time_str} ({period})")
        if hasattr(self, "top_status_weather_lbl"):
            weather_icons = {"Sereno": "🌤️", "Pioggia": "🌧️", "Tempesta": "⛈️", "Neve": "❄️", "Nebbia": "🌫️",
                             "Clear": "🌤️", "Rain": "🌧️", "Storm": "⛈️", "Snow": "❄️", "Fog": "🌫️"}
            w_icon = weather_icons.get(gs.weather, "🌤️")
            self.top_status_weather_lbl.config(text=f"{w_icon} {translate_weather(gs.weather)}")
            
        if self.server.game_state.combat_active:
            # Mostra banner combattimento
            self.combat_controls_frame.pack(fill=tk.X, side=tk.TOP, pady=5, before=self.btn_hide_reveal)
            self.btn_combat.config(text=_t("btn_end_combat"), style='Danger.TButton')
            self.lbl_round.config(text=_t("lbl_round_num", round=self.server.game_state.round_number))
            self.btn_prev_turn.config(state=tk.NORMAL)
            self.btn_next_turn.config(state=tk.NORMAL)
            if hasattr(self, "top_status_combat_lbl"):
                self.top_status_combat_lbl.config(text=_t("status_in_combat", round=self.server.game_state.round_number), fg=ACCENT_RED)
        else:
            self.combat_controls_frame.pack_forget()
            self.btn_combat.config(text=_t("btn_start_combat"), style='Gold.TButton')
            self.lbl_round.config(text="Round: -")
            self.btn_prev_turn.config(state=tk.DISABLED)
            self.btn_next_turn.config(state=tk.DISABLED)
            if hasattr(self, "top_status_combat_lbl"):
                self.top_status_combat_lbl.config(text=_t("status_exploration"), fg=TEXT_MUTED)

        # Calcolo Difficoltà Incontro (D&D 5e DMG p.82)
        if hasattr(self, "lbl_encounter_diff") and self.server.game_state:
            from common.encounter_calc import calculate_encounter_difficulty
            party_members = [p for p in self.server.game_state.players if getattr(p, "is_party_member", False)]
            party_levels = []
            for p in party_members:
                lvl = 1
                if getattr(p, "full_sheet", None):
                    lvl = p.full_sheet.get("level", 1) or 1
                party_levels.append(int(lvl))
            
            monsters = [p for p in self.server.game_state.players if not getattr(p, "is_party_member", False) and getattr(p, "in_combat", True)]
            monster_crs = []
            for m in monsters:
                cr = 1
                if getattr(m, "full_sheet", None):
                    cr = m.full_sheet.get("cr", 1) or 1
                monster_crs.append(cr)
                
            if party_levels and monster_crs:
                calc_res = calculate_encounter_difficulty(party_levels, monster_crs)
                diff = calc_res["difficulty"]
                eff_xp = calc_res["adjusted_xp"]
                diff_colors = {
                    "Facile": "#51CF66",
                    "Medio": "#339AF0",
                    "Difficile": "#FF922B",
                    "Mortale": "#FF6B6B"
                }
                c = diff_colors.get(diff, ACCENT_GOLD)
                self.lbl_encounter_diff.config(text=f"⚔️ Bilanciamento: {diff} ({eff_xp} XP eff.)", fg=c)
            else:
                self.lbl_encounter_diff.config(text="⚔️ Bilanciamento 5e: Nessun nemico", fg=TEXT_MUTED)

        if self.server.game_state:
            players = self.server.game_state.get_all_players()
            if not self.server.game_state.combat_active:
                party = sorted([p for p in players if getattr(p, "is_party_member", False)], key=lambda p: p.initiative, reverse=True)
                npcs = sorted([p for p in players if not getattr(p, "is_party_member", False)], key=lambda p: p.initiative, reverse=True)
                
                ordered_list = []
                ordered_list.append(("--- PARTY ---", None))
                for p in party: ordered_list.append((p, "party"))
                ordered_list.append(("--- NPC ---", None))
                for p in npcs: ordered_list.append((p, "npc"))

                for i, item in enumerate(ordered_list):
                    if isinstance(item[0], str):
                        self.player_listbox.insert(tk.END, item[0])
                        self.player_listbox.itemconfig(i, {'bg': SURFACE_COLOR, 'fg': TEXT_MUTED})
                    else:
                        p = item[0]
                        prefix = "  "
                        conds = f" {{{', '.join(p.conditions)}}}" if getattr(p, "conditions", []) else ""
                        hidden_str = "[N] " if getattr(p, "is_hidden", False) else ""
                        init_badge = _t('sheet_init_badge')
                        display_text = f"{prefix}{hidden_str}{p.name} (HP: {p.hp}/{p.max_hp}) [{init_badge}: {p.initiative}]{conds}"
                        self.player_listbox.insert(tk.END, display_text)
                        self.player_listbox.itemconfig(i, {'bg': SURFACE_COLOR, 'fg': TEXT_COLOR})
            else:
                for i, p in enumerate(players): 
                    in_combat = getattr(p, 'in_combat', True) if self.server.game_state.combat_active else True
                    is_turn = self.server.game_state.combat_active and in_combat and i == self.server.game_state.turn_index
                    
                    prefix = "➡️ " if is_turn else "  "
                    conds = f" {{{', '.join(p.conditions)}}}" if getattr(p, "conditions", []) else ""
                    
                    hidden_str = "[N] " if getattr(p, "is_hidden", False) else ""
                    if not in_combat and self.server.game_state.combat_active:
                        display_text = f"  {hidden_str}{p.name} [{_t('not_in_combat')}]{conds}"
                    else:
                        init_badge = _t('sheet_init_badge')
                        display_text = f"{prefix}{hidden_str}{p.name} (HP: {p.hp}/{p.max_hp}) [{init_badge}: {p.initiative}]{conds}"
                        
                    self.player_listbox.insert(tk.END, display_text)
                    
                    if is_turn:
                        self.player_listbox.itemconfig(i, {'bg': '#D4AF37', 'fg': 'black'})
                    elif not in_combat and self.server.game_state.combat_active:
                        self.player_listbox.itemconfig(i, {'bg': SURFACE_COLOR, 'fg': TEXT_MUTED})
                    else:
                        self.player_listbox.itemconfig(i, {'bg': SURFACE_COLOR, 'fg': TEXT_COLOR})

        if current_selection:
            try: self.player_listbox.selection_set(current_selection[0])
            except tk.TclError: pass

    def process_queue(self):
        try:
            while True:
                msg = self.gui_queue.get_nowait()
                msg_type = msg.get("type")
                if msg_type == "UPDATE_STATE":
                    self.update_player_list()
                    self.redraw_map_and_players()
                elif msg_type == "LOG_MESSAGE":
                    self.log_to_chat(msg.get("payload"))
                elif msg_type == "SHOW_COMBAT_CONFIG":
                    self.open_combat_config(msg.get("payload", {}).get("initiator"))
                elif msg_type == "PRIVATE_MESSAGE_RECEIVED":
                    payload = msg.get("payload", {})
                    player_name, text = payload.get("from"), payload.get("text")
                    if player_name and text:
                        self.create_chat_tab(player_name)
                        self.log_to_chat(text, tab_name=player_name, sender=player_name, color="#5865F2")
                elif msg_type == "PING_BROADCAST":
                    payload = msg.get("payload", {})
                    self.map_canvas.draw_ping(payload.get("q"), payload.get("r"), payload.get("color", "yellow"))
                elif msg_type == "CUSTOM_SPELL_REQUEST":
                    self.prompt_custom_spell_approval(msg.get("player"), msg.get("spell"))
                elif msg_type == "CURRENCY_REQUEST":
                    self.prompt_currency_approval(msg.get("player"), msg.get("coin"), msg.get("amount"), msg.get("reason"))
                elif msg_type == "ITEM_APPROVAL_REQUEST":
                    self.prompt_item_approval(msg.get("player"), msg.get("item"), msg.get("slot_idx"))
        except queue.Empty: pass
        self.master.after(100, self.process_queue)

    def prompt_currency_approval(self, player, coin, amount, reason):
        if not player or amount <= 0: return
        p_name = getattr(player, "name", "Giocatore")
        coin_labels = {
            "MO": "Monete d'Oro (MO / gp)", "gp": "Monete d'Oro (MO / gp)",
            "MA": "Monete d'Argento (MA / sp)", "sp": "Monete d'Argento (MA / sp)",
            "MR": "Monete di Rame (MR / cp)", "cp": "Monete di Rame (MR / cp)",
            "ME": "Monete d'Electrum (ME / ep)", "ep": "Monete d'Electrum (ME / ep)",
            "MP": "Monete di Platino (MP / pp)", "pp": "Monete di Platino (MP / pp)"
        }
        coin_display = coin_labels.get(coin, coin)
        reason_display = reason if reason else "Nessuna motivazione specificata"
        prompt_text = (
            f"Il giocatore '{p_name}' richiede di ricevere valuta:\n\n"
            f"• Quantità: +{amount} {coin_display}\n"
            f"• Motivazione: {reason_display}\n\n"
            f"Vuoi approvare la richiesta e accreditare le monete a {p_name}?"
        )
        approved = messagebox.askyesno("Richiesta Valuta Giocatore", prompt_text, parent=self.master)
        
        from common.protocol import make_currency_response, make_chat_broadcast, make_game_state
        from common.network_utils import send_message, broadcast
        if approved:
            sheet = getattr(player, "full_sheet", None)
            if sheet:
                if not isinstance(sheet.get("currency"), dict):
                    sheet["currency"] = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
                sheet["currency"][coin] = sheet["currency"].get(coin, 0) + amount
                if coin in ["MO", "gp"]:
                    sheet["gp"] = sheet.get("gp", 0) + amount
            if player.conn:
                send_message(player.conn, make_currency_response(p_name, coin, amount, approved=True, reason=reason))
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", f"[VALUTA] Il Master ha APPROVATO e concesso +{amount} {coin_display} a {p_name}!"))
            self.log_to_chat(f"[SISTEMA] Concessi +{amount} {coin_display} a {p_name}.")
            self.server.game_state._trigger_gui_update()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
        else:
            if player.conn:
                send_message(player.conn, make_currency_response(p_name, coin, amount, approved=False, reason="Richiesta respinta dal Dungeon Master."))
            self.log_to_chat(f"[SISTEMA] Respinta richiesta valuta da {p_name} (+{amount} {coin_display}).")

    def prompt_item_approval(self, player, item, slot_idx):
        if not player or not item: return
        p_name = getattr(player, "name", "Giocatore")
        it_name = item.get("name", "Oggetto Sconosciuto")
        it_type = item.get("type", "Equipaggiamento")
        it_qty = item.get("qty", 1)
        it_weight = item.get("weight", 0.0)
        it_attuned = "Sì" if item.get("attuned") else "No"
        it_desc = item.get("desc", "")
        
        prompt_text = (
            f"Il giocatore '{p_name}' richiede di aggiungere un oggetto allo zaino:\n\n"
            f"• Oggetto: {it_name}\n"
            f"• Categoria: {it_type} (Quantità: {it_qty}, Peso: {it_weight} lbs)\n"
            f"• Richiede Sintonia: {it_attuned}\n\n"
            f"Descrizione:\n{it_desc}\n\n"
            f"Vuoi approvare questo oggetto per l'inventario di {p_name}?"
        )
        approved = messagebox.askyesno("Approvazione Oggetto Inventario", prompt_text, parent=self.master)
        
        from common.protocol import make_item_approval_response, make_chat_broadcast, make_game_state
        from common.network_utils import send_message, broadcast
        if approved:
            sheet = getattr(player, "full_sheet", None)
            if sheet:
                if not isinstance(sheet.get("inventory_grid"), list):
                    sheet["inventory_grid"] = [None] * 25
                target_slot = slot_idx if (slot_idx is not None and 0 <= slot_idx < 25) else None
                if target_slot is None or sheet["inventory_grid"][target_slot] is not None:
                    for s_i in range(len(sheet["inventory_grid"])):
                        if sheet["inventory_grid"][s_i] is None:
                            target_slot = s_i
                            break
                if target_slot is not None and target_slot < 25:
                    sheet["inventory_grid"][target_slot] = item
                    slot_idx = target_slot
            if player.conn:
                send_message(player.conn, make_item_approval_response(p_name, item, slot_idx, approved=True))
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", f"[INVENTARIO] Il Master ha APPROVATO l'oggetto '{it_name}' per {p_name}!"))
            self.log_to_chat(f"[SISTEMA] Approvato oggetto '{it_name}' per {p_name}.")
            self.server.game_state._trigger_gui_update()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
        else:
            if player.conn:
                send_message(player.conn, make_item_approval_response(p_name, item, slot_idx, approved=False, reason="Il Master ha respinto l'aggiunta di questo oggetto."))
            self.log_to_chat(f"[SISTEMA] Respinto oggetto '{it_name}' per {p_name}.")

    def prompt_custom_spell_approval(self, player, spell):
        if not player or not spell: return
        p_name = getattr(player, "name", "Giocatore")
        s_name = spell.get("name", "Incantesimo Sconosciuto")
        s_lvl = spell.get("level", 0)
        s_time = spell.get("time", "1 Azione")
        s_rng = spell.get("range", "Contatto")
        s_desc = spell.get("desc", "")
        
        lvl_str = "Trucchetto (Lvl 0)" if s_lvl == 0 else f"Livello {s_lvl}"
        prompt_text = (
            f"Il giocatore '{p_name}' richiede il permesso di creare il seguente incantesimo:\n\n"
            f"• Nome: {s_name}\n"
            f"• Livello: {lvl_str}\n"
            f"• Tempo di Lancio: {s_time}\n"
            f"• Raggio / Gittata: {s_rng}\n\n"
            f"Descrizione:\n{s_desc}\n\n"
            f"Vuoi approvare questo incantesimo e permetterne l'aggiunta al suo Grimorio?"
        )
        approved = messagebox.askyesno("Richiesta Incantesimo Custom", prompt_text, parent=self.master)
        
        from common.protocol import make_custom_spell_response, make_chat_broadcast
        from common.network_utils import send_message, broadcast
        if approved:
            if player.conn:
                send_message(player.conn, make_custom_spell_response(p_name, spell, approved=True))
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", f"[MAGIA] Il Master ha APPROVATO l'incantesimo custom '{s_name}' per {p_name}!"))
            self.log_to_chat(f"[SISTEMA] Approvato incantesimo custom '{s_name}' per {p_name}.")
        else:
            if player.conn:
                send_message(player.conn, make_custom_spell_response(p_name, spell, approved=False, reason="Il Master ha respinto la richiesta per questo incantesimo."))
            self.log_to_chat(f"[SISTEMA] Respinto incantesimo custom '{s_name}' per {p_name}.")

    def on_closing(self):
        if messagebox.askokcancel(_t("menu_exit"), _t("confirm_exit_server")):
            try:
                unregister_language_listener(self.on_language_changed)
            except Exception:
                pass
            try:
                unregister_unit_listener(self.on_unit_changed)
            except Exception:
                pass
            if hasattr(self, 'audio_manager'):
                try: self.audio_manager.stop("all")
                except Exception: pass
            if hasattr(self, 'voice_client'):
                self.voice_client.stop()
            self.server.stop()
            self.master.destroy()

    def share_text_handout(self):
        TextHandoutDialog(self)

    def share_image_handout(self):
        filepath = filedialog.askopenfilename(
            title="Seleziona Immagine da Condividere",
            filetypes=[("Immagini", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")]
        )
        if not filepath:
            return
            
        try:
            from PIL import Image
            import base64
            from io import BytesIO
            
            # Downscale image to avoid huge payloads
            img = Image.open(filepath)
            img.thumbnail((800, 800))
            
            buffered = BytesIO()
            fmt = img.format if img.format else "PNG"
            img.save(buffered, format=fmt)
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            title = simpledialog.askstring("Titolo Handout", "Inserisci il titolo dell'immagine:", parent=self.master)
            if not title:
                title = "Handout Condiviso"
                
            from common.protocol import make_handout_broadcast
            from common.network_utils import broadcast
            
            broadcast(self.server.game_state, make_handout_broadcast(title, img_b64))
            messagebox.showinfo("Successo", "Immagine condivisa con tutti i giocatori connessi!")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile condividere l'immagine:\n{e}")

    def open_map_editor(self):
        editor_window=MapEditorWindow(self.master); editor_window.grab_set()

    def create_chat_tab(self, name):
        if name in self.chat_tabs: return
        tab_frame = ttk.Frame(self.notebook)
        text_widget = scrolledtext.ScrolledText(tab_frame, state='disabled', wrap=tk.WORD, bg=SURFACE_COLOR, 
fg=TEXT_COLOR, borderwidth=0, highlightthickness=0, font=FONT_MAIN)
        text_widget.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(tab_frame, text=name)
        self.chat_tabs[name] = text_widget
        
        # Configure tags for Dark Fantasy / Discord-like format
        text_widget.tag_config("timestamp", foreground=TEXT_MUTED, font=("Segoe UI", 8))
        text_widget.tag_config("sender", font=FONT_BOLD, foreground=ACCENT_GOLD)
        text_widget.tag_config("text", foreground=TEXT_COLOR, font=FONT_MAIN)
        
    def open_private_chat_from_list(self, event):
        selected_indices = self.player_listbox.curselection()
        if not selected_indices: return
        display_text = self.player_listbox.get(selected_indices[0])
        if display_text.startswith('---'): return
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
        self.create_chat_tab(player_name)
        for i, tab in enumerate(self.notebook.tabs()):
            if self.notebook.tab(i, "text") == player_name: self.notebook.select(i); break
        self.chat_entry.focus_set()

    def open_private_chat_from_context(self):
        self.open_private_chat_from_list(None)

    def show_player_context_menu(self, event):
        try:
            index = self.player_listbox.nearest(event.y)
            display_text = self.player_listbox.get(index)
            if display_text.startswith("---"): return
            self.player_listbox.selection_clear(0, tk.END)
            self.player_listbox.selection_set(index)
            self.player_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.player_menu.grab_release()

    def view_player_sheet(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
        player = self.server.game_state.find_player(player_name)
        
        if not player or not player.full_sheet:
            messagebox.showinfo("Nessuna Scheda", f"Nessuna scheda disponibile per {player_name}.")
            return
            
        DMPlayerSheetViewer(self.master, player_name, player.full_sheet)

    def open_campaign_starter_kit_dialog(self):
        CampaignStarterKitDialog(self)

    def open_assign_item_dialog(self, prefill_item=None):
        sel = self.player_listbox.curselection()
        if not sel:
            messagebox.showinfo("Attenzione", "Seleziona prima un giocatore dalla lista a cui assegnare l'oggetto.")
            return
            
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
        player = self.server.game_state.find_player(player_name)
        
        if not player or not player.conn:
            messagebox.showinfo("Errore", f"Il giocatore {player_name} non è connesso.")
            return

        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        apply_modern_window_style(win)
        win.title(f"Assegna Oggetto a {player_name}")
        win.minsize(300, 350)

        ttk.Label(win, text="Nome Oggetto:").pack(pady=(10, 0))
        name_entry = ttk.Entry(win)
        name_entry.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(win, text="Tipo (es. Arma, Pozione):").pack(pady=(10, 0))
        type_entry = ttk.Entry(win)
        type_entry.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(win, text="Quantità:").pack(pady=(10, 0))
        qty_entry = ttk.Entry(win)
        qty_entry.insert(0, "1")
        qty_entry.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(win, text="Descrizione:").pack(pady=(10, 0))
        desc_entry = ttk.Entry(win)
        desc_entry.pack(fill=tk.X, padx=20, pady=5)
        
        if prefill_item:
            name_entry.insert(0, prefill_item.get("name", ""))
            type_entry.insert(0, prefill_item.get("equipment_category", {}).get("name", "Oggetto"))
            desc = prefill_item.get("desc", [])
            if isinstance(desc, list):
                desc = " ".join(desc)
            desc_entry.insert(0, desc[:50] + "..." if len(desc)>50 else desc)

        def submit():
            try:
                qty = int(qty_entry.get().strip())
            except ValueError:
                qty = 1
            item = {
                "name": name_entry.get().strip(),
                "type": type_entry.get().strip(),
                "qty": qty,
                "desc": desc_entry.get().strip()
            }
            if not item["name"]:
                messagebox.showerror("Errore", "Il nome dell'oggetto è obbligatorio.")
                return
            
            with self.server.game_state.lock:
                if not getattr(player, "full_sheet", None) or not isinstance(player.full_sheet, dict):
                    player.full_sheet = {}
                grid = player.full_sheet.get("inventory_grid")
                if not isinstance(grid, list) or len(grid) == 0:
                    grid = [None] * 25
                for idx in range(len(grid)):
                    if grid[idx] is None:
                        grid[idx] = dict(item)
                        break
                player.full_sheet["inventory_grid"] = grid

            if player.conn:
                send_message(player.conn, make_receive_item(item))
            messagebox.showinfo("Successo", f"Oggetto inviato a {player_name}!")
            win.destroy()

        ttk.Button(win, text="Assegna", command=submit).pack(pady=20)

    def open_modify_hp_dialog(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
        player = self.server.game_state.find_player(player_name)
        
        if not player: return

        delta_str = simpledialog.askstring("Modifica HP", f"Inserisci variazione HP per {player_name}\n(es. -5 per danno, +8 per cura):")
        if not delta_str: return
        
        try:
            delta = int(delta_str)
            with self.server.game_state.lock:
                player.hp = max(0, min(player.max_hp, player.hp + delta))
            self.server.game_state._trigger_gui_update()
            broadcast(self.server.game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative))
            self.log_to_chat(f"[SISTEMA] HP di {player.name} aggiornati a {player.hp}/{player.max_hp}")
        except ValueError:
            messagebox.showerror("Errore", "Valore non valido.")

    def open_conditions_dialog(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
        player = self.server.game_state.find_player(player_name)
        if not player: return

        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        apply_modern_window_style(win)
        win.title(f"Stati di {player_name}")
        win.minsize(250, 350)

        ttk.Label(win, text="Condizioni Attive:").pack(pady=5)
        
        listbox = tk.Listbox(win, bg=SURFACE_COLOR, fg=TEXT_COLOR, selectmode=tk.MULTIPLE, font=self.default_font)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        all_conditions = ["Accecato", "Affascinato", "Assordato", "Avvelenato", "In Fiamme", 
                          "Invisibile", "Prono", "Spaventato", "Stordito", "Svenuto", "Trattenuto", "Pietrificato"]
        
        for i, cond in enumerate(all_conditions):
            listbox.insert(tk.END, cond)
            if hasattr(player, "conditions") and cond in player.conditions:
                listbox.selection_set(i)

        def apply_conditions():
            selected_indices = listbox.curselection()
            new_conditions = [listbox.get(i) for i in selected_indices]
            with self.server.game_state.lock:
                player.conditions = new_conditions
            self.server.game_state._trigger_gui_update()
            broadcast(self.server.game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, new_conditions))
            self.log_to_chat(f"[SISTEMA] Condizioni di {player.name} aggiornate: {', '.join(new_conditions) if new_conditions else 'Nessuna'}")
            win.destroy()

        ttk.Button(win, text="Applica", command=apply_conditions).pack(pady=10)

    def open_aura_dialog(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
        player = self.server.game_state.find_player(player_name)
        
        if not player: return
        
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        apply_modern_window_style(win)
        win.title(f"Imposta Aura per {player_name}")
        win.minsize(250, 200)

        ttk.Label(win, text="Raggio (esagoni, 0 per disabilitare):").pack(pady=(10, 0))
        radius_entry = ttk.Entry(win)
        radius_entry.insert(0, str(getattr(player, 'aura_radius', 0)))
        radius_entry.pack(fill=tk.X, padx=20, pady=5)


        ttk.Label(win, text="Colore:").pack(pady=(10, 0))
        color_var = tk.StringVar(value=getattr(player, 'aura_color', 'yellow'))
        color_combo = ttk.Combobox(win, textvariable=color_var, values=["yellow", "blue", "red", "green", "purple", "white", "black"], state="readonly")
        color_combo.pack(fill=tk.X, padx=20, pady=5)

        def submit():
            try:
                rad = int(radius_entry.get().strip())
                col = color_var.get().strip()
                if rad < 0: rad = 0
                
                with self.server.game_state.lock:
                    player.aura_radius = rad
                    player.aura_color = col
                    
                self.server.game_state._trigger_gui_update()
                
                # Invia un aggiornamento dello stato intero in modo che client lo riceva
                from common.protocol import make_game_state
                broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
                
                self.log_to_chat(f"[SISTEMA] Aura di {player.name} impostata a raggio {rad} ({col})")
                win.destroy()
            except ValueError:
                messagebox.showerror("Errore", "Il raggio deve essere un numero intero.")

        ttk.Button(win, text="Applica", command=submit).pack(pady=20)

    def get_selected_player_name(self):
        sel = self.player_listbox.curselection()
        if not sel: return None
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return None
        name = display_text.split(" (HP")[0].replace("▶", "").replace("[N]", "").strip()
        return name

    def open_light_source_dialog(self):
        player_name = self.get_selected_player_name()
        if not player_name: return
        player = self.server.game_state.find_player(player_name)
        if not player: return

        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        apply_modern_window_style(win)
        win.title(f"Sorgente di Luce: {player_name}")
        win.minsize(360, 320)

        container = tk.Frame(win, bg=BG_COLOR, padx=16, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text=f"🔦 Sorgente Luminosa - {player_name}", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 10))

        presets = [
            ("Spento / Nessuna Luce", 0, "#FFD700"),
            ("Torcia (4 hex / 20 ft)", 4, "#FFD700"),
            ("Lanterna Schermata (6 hex / 30 ft)", 6, "#FFA500"),
            ("Incantesimo Luce (4 hex - Bianca)", 4, "#66D9E8"),
            ("Luce Diurna (12 hex / 60 ft)", 12, "#FFFFFF")
        ]

        tk.Label(container, text="Preset Rapido:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        preset_var = tk.StringVar(value=presets[1][0] if getattr(player, "light_radius", 0) > 0 else presets[0][0])
        preset_combo = ttk.Combobox(container, textvariable=preset_var, values=[p[0] for p in presets], state="readonly")
        preset_combo.pack(fill=tk.X, pady=(2, 10))

        tk.Label(container, text="Raggio Personalizzato (Esagoni):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        rad_entry = ttk.Entry(container)
        rad_entry.insert(0, str(getattr(player, "light_radius", 0)))
        rad_entry.pack(fill=tk.X, pady=(2, 10))

        tk.Label(container, text="Colore Luce (Esadecimale o Nome):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        color_entry = ttk.Entry(container)
        color_entry.insert(0, getattr(player, "light_color", "#FFD700"))
        color_entry.pack(fill=tk.X, pady=(2, 12))

        def on_preset_select(e):
            sel_text = preset_var.get()
            for name, r, c in presets:
                if name == sel_text:
                    rad_entry.delete(0, tk.END); rad_entry.insert(0, str(r))
                    color_entry.delete(0, tk.END); color_entry.insert(0, c)
                    break
        preset_combo.bind("<<ComboboxSelected>>", on_preset_select)

        def save_light():
            try:
                r = int(rad_entry.get().strip())
                c = color_entry.get().strip() or "#FFD700"
                player.light_radius = max(0, r)
                player.light_color = c
                self.server.game_state._trigger_gui_update()
                from common.protocol import make_player_stats_update
                from server.network import broadcast
                broadcast(self.server.game_state, make_player_stats_update(
                    player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)
                ))
                self.redraw_map_and_players()
                self.log_to_chat(f"[LUCE] Luce per {player.name} impostata a {r} hex ({c}).")
                win.destroy()
            except ValueError:
                messagebox.showerror("Errore", "Il raggio deve essere un numero intero.", parent=win)

        btn_row = tk.Frame(container, bg=BG_COLOR)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="Salva Luce", command=save_light, style="Gold.TButton").pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="Annulla", command=win.destroy).pack(side=tk.RIGHT, padx=6)

    def open_boss_config_dialog(self):
        player_name = self.get_selected_player_name()
        if not player_name: return
        player = self.server.game_state.find_player(player_name)
        if not player: return

        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        apply_modern_window_style(win)
        win.title(f"👑 Configura Boss Leggendario: {player_name}")
        win.minsize(360, 320)

        container = tk.Frame(win, bg=BG_COLOR, padx=16, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text=f"👑 Meccaniche Boss - {player_name}", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 10))

        tk.Label(container, text="Resistenze Leggendarie Max (es. 3):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        res_max_entry = ttk.Entry(container)
        res_max_entry.insert(0, str(getattr(player, "legendary_resistances_max", 3)))
        res_max_entry.pack(fill=tk.X, pady=(2, 6))

        tk.Label(container, text="Resistenze Leggendarie Attuali:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        res_cur_entry = ttk.Entry(container)
        res_cur_entry.insert(0, str(getattr(player, "legendary_resistances_current", getattr(player, "legendary_resistances_max", 3))))
        res_cur_entry.pack(fill=tk.X, pady=(2, 10))

        tk.Label(container, text="Azioni Leggendarie per Round (es. 3):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        act_max_entry = ttk.Entry(container)
        act_max_entry.insert(0, str(getattr(player, "legendary_actions_max", 3)))
        act_max_entry.pack(fill=tk.X, pady=(2, 6))

        tk.Label(container, text="Azioni Leggendarie Attuali:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        act_cur_entry = ttk.Entry(container)
        act_cur_entry.insert(0, str(getattr(player, "legendary_actions_current", getattr(player, "legendary_actions_max", 3))))
        act_cur_entry.pack(fill=tk.X, pady=(2, 12))

        def save_boss():
            try:
                rmax = int(res_max_entry.get().strip())
                rcur = int(res_cur_entry.get().strip())
                amax = int(act_max_entry.get().strip())
                acur = int(act_cur_entry.get().strip())
                player.legendary_resistances_max = max(0, rmax)
                player.legendary_resistances_current = max(0, min(rmax, rcur))
                player.legendary_actions_max = max(0, amax)
                player.legendary_actions_current = max(0, min(amax, acur))
                self.server.game_state._trigger_gui_update()
                self.redraw_map_and_players()
                self.log_to_chat(f"[BOSS] {player.name} configurato: {rmax} Resistenze, {amax} Azioni.")
                win.destroy()
            except ValueError:
                messagebox.showerror("Errore", "Tutti i valori devono essere numeri interi.", parent=win)

        btn_row = tk.Frame(container, bg=BG_COLOR)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="Salva Boss", command=save_boss, style="Gold.TButton").pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="Annulla", command=win.destroy).pack(side=tk.RIGHT, padx=6)

    def open_spend_legendary_action_dialog(self):
        player_name = self.get_selected_player_name()
        if not player_name: return
        player = self.server.game_state.find_player(player_name)
        if not player: return

        cur_act = getattr(player, "legendary_actions_current", 0)
        max_act = getattr(player, "legendary_actions_max", 0)
        if max_act == 0:
            messagebox.showinfo("Non è un Boss", f"{player_name} non ha azioni leggendarie configurate.\nConfigurale prima da 'Configura Boss Leggendario'.", parent=self.master)
            return

        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        apply_modern_window_style(win)
        win.title(f"👑 Spendi Azione Leggendaria: {player_name}")
        win.minsize(360, 240)

        container = tk.Frame(win, bg=BG_COLOR, padx=16, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text=f"👑 Azioni Disponibili: {cur_act}/{max_act}", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 10))

        tk.Label(container, text="Nome Azione (es. Colpo di Coda, Movimento, Soffio):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        name_entry = ttk.Entry(container)
        name_entry.insert(0, "Azione Leggendaria")
        name_entry.pack(fill=tk.X, pady=(2, 8))

        tk.Label(container, text="Costo Azioni (1, 2 o 3):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        cost_combo = ttk.Combobox(container, values=["1", "2", "3"], state="readonly")
        cost_combo.set("1")
        cost_combo.pack(fill=tk.X, pady=(2, 12))

        def do_spend():
            cost = int(cost_combo.get())
            if cur_act < cost:
                messagebox.showerror("Azioni Insufficienti", f"Questo boss ha solo {cur_act} azioni rimaste (richieste: {cost}).", parent=win)
                return
            act_name = name_entry.get().strip() or "Azione Leggendaria"
            from server.commands import command_handlers
            command_handlers["SPEND_LEGENDARY_ACTION_REQUEST"]({"boss_name": player.name, "action_name": act_name, "cost": cost}, player, self.server.game_state)
            win.destroy()

        btn_row = tk.Frame(container, bg=BG_COLOR)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="⚡ Esegui Azione", command=do_spend, style="Gold.TButton").pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="Annulla", command=win.destroy).pack(side=tk.RIGHT, padx=6)

    def open_place_trap_dialog(self, clicked_hex):
        if not self.server.game_state.current_map:
            messagebox.showinfo("Nessuna Mappa", "Nessuna mappa attiva su cui piazzare trappole.", parent=self.master)
            return

        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        apply_modern_window_style(win)
        win.title(f"⚠️ Piazza Trappola 5e [{clicked_hex.q}, {clicked_hex.r}]")
        win.minsize(380, 360)

        container = tk.Frame(win, bg=BG_COLOR, padx=16, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text=f"⚠️ Nuova Trappola D&D 5e - Hex ({clicked_hex.q}, {clicked_hex.r})", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 10))

        presets = [
            ("Fossa con Punte (CD 13, 2d10 Perforante)", "Trappola a Fossa con Punte", 13, "2d10", "Perforante"),
            ("Dardi Avvelenati (CD 15, 2d8 Veleno)", "Trappola a Dardi Avvelenati", 15, "2d8", "Veleno"),
            ("Runa di Fuoco (CD 14, 4d6 Fuoco)", "Runa Esplosiva di Fuoco", 14, "4d6", "Fuoco"),
            ("Gabbia Cadente (CD 12, 1d10 Contundente)", "Trappola a Gabbia Pesante", 12, "1d10", "Contundente"),
            ("Spruzzo d'Acido (CD 14, 3d6 Acido)", "Trappola a Getto d'Acido", 14, "3d6", "Acido")
        ]

        tk.Label(container, text="Preset Trappola:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        preset_var = tk.StringVar(value=presets[0][0])
        preset_combo = ttk.Combobox(container, textvariable=preset_var, values=[p[0] for p in presets], state="readonly")
        preset_combo.pack(fill=tk.X, pady=(2, 6))

        tk.Label(container, text="Nome Trappola:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        name_entry = ttk.Entry(container)
        name_entry.insert(0, presets[0][1])
        name_entry.pack(fill=tk.X, pady=(2, 6))

        tk.Label(container, text="CD Tiro Salvezza (Destrezza):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        dc_entry = ttk.Entry(container)
        dc_entry.insert(0, str(presets[0][2]))
        dc_entry.pack(fill=tk.X, pady=(2, 6))

        tk.Label(container, text="Formula Danno (es. 2d10, 4d6):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        dmg_entry = ttk.Entry(container)
        dmg_entry.insert(0, presets[0][3])
        dmg_entry.pack(fill=tk.X, pady=(2, 6))

        tk.Label(container, text="Tipo di Danno:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        dtype_combo = ttk.Combobox(container, values=["Perforante", "Tagliente", "Contundente", "Fuoco", "Veleno", "Acido", "Fulmine"], state="readonly")
        dtype_combo.set(presets[0][4])
        dtype_combo.pack(fill=tk.X, pady=(2, 8))

        hidden_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(container, text="Nascosta ai giocatori finché non scatta", variable=hidden_var).pack(anchor="w", pady=(0, 10))

        def on_preset_sel(e):
            sel_text = preset_var.get()
            for p_title, p_name, p_dc, p_dmg, p_type in presets:
                if p_title == sel_text:
                    name_entry.delete(0, tk.END); name_entry.insert(0, p_name)
                    dc_entry.delete(0, tk.END); dc_entry.insert(0, str(p_dc))
                    dmg_entry.delete(0, tk.END); dmg_entry.insert(0, p_dmg)
                    dtype_combo.set(p_type)
                    break
        preset_combo.bind("<<ComboboxSelected>>", on_preset_sel)

        def save_trap():
            try:
                dc = int(dc_entry.get().strip())
                name = name_entry.get().strip() or "Trappola"
                dmg = dmg_entry.get().strip() or "1d10"
                dtype = dtype_combo.get() or "Perforante"
                traps = self.server.game_state.current_map.setdefault("traps", [])
                traps.append({
                    "q": clicked_hex.q,
                    "r": clicked_hex.r,
                    "name": name,
                    "dc": dc,
                    "damage": dmg,
                    "damage_type": dtype,
                    "triggered": False,
                    "hidden": hidden_var.get()
                })
                self.redraw_map_and_players()
                from common.protocol import make_map_data_update_broadcast
                from server.network import broadcast
                broadcast(self.server.game_state, make_map_data_update_broadcast(self.server.game_state.current_map))
                self.log_to_chat(f"[MAPPA] Trappola '{name}' (CD {dc}, {dmg} {dtype}) piazzata a [{clicked_hex.q}, {clicked_hex.r}].")
                win.destroy()
            except ValueError:
                messagebox.showerror("Errore", "La CD deve essere un numero intero.", parent=win)

        btn_row = tk.Frame(container, bg=BG_COLOR)
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="⚠️ Piazza Trappola", command=save_trap, style="Gold.TButton").pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="Annulla", command=win.destroy).pack(side=tk.RIGHT, padx=6)

    def remove_trap_at(self, clicked_hex):
        cur_map = getattr(self.server.game_state, "current_map", None)
        if not cur_map: return
        traps = cur_map.get("traps", [])
        cur_map["traps"] = [t for t in traps if not (t.get("q") == clicked_hex.q and t.get("r") == clicked_hex.r)]
        self.redraw_map_and_players()
        from common.protocol import make_map_data_update_broadcast
        from server.network import broadcast
        broadcast(self.server.game_state, make_map_data_update_broadcast(cur_map))
        self.log_to_chat(f"[MAPPA] Trappola a [{clicked_hex.q}, {clicked_hex.r}] rimossa.")

    def reset_trap_at(self, clicked_hex):
        cur_map = getattr(self.server.game_state, "current_map", None)
        if not cur_map: return
        traps = cur_map.get("traps", [])
        for t in traps:
            if t.get("q") == clicked_hex.q and t.get("r") == clicked_hex.r:
                t["triggered"] = False
                t["hidden"] = True
        self.redraw_map_and_players()
        from common.protocol import make_map_data_update_broadcast
        from server.network import broadcast
        broadcast(self.server.game_state, make_map_data_update_broadcast(cur_map))
        self.log_to_chat(f"[MAPPA] Trappola a [{clicked_hex.q}, {clicked_hex.r}] riattivata e nascosta.")


    def split_loot_dialog(self):
        amount = simpledialog.askinteger("Dividi Denaro", "Quante Monete d'Oro (MO) vuoi distribuire?", parent=self.master, minvalue=1)
        if amount:
            if hasattr(self.server, "send_loot_split"):
                self.server.send_loot_split(amount)
            else:
                messagebox.showerror("Errore", "Funzione non supportata dal server attuale.")

    def open_action_dialog(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return
        target_name = display_text.split(" (HP")[0].replace("▶", "").strip()
        target_player = self.server.game_state.find_player(target_name)
        if not target_player: return

        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        apply_modern_window_style(win)
        win.title(f"Azione su {target_name}")
        win.minsize(300, 300)

        ttk.Label(win, text="Tipo di Azione:").pack(pady=(10, 0))
        action_var = tk.StringVar(value="damage")
        frame_radio = ttk.Frame(win)
        frame_radio.pack(pady=5)
        ttk.Radiobutton(frame_radio, text="Danno", variable=action_var, value="damage").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(frame_radio, text="Cura", variable=action_var, value="heal").pack(side=tk.LEFT, padx=10)

        ttk.Label(win, text="Formula (es. 1d8+3 oppure 5):").pack(pady=(10, 0))
        formula_entry = ttk.Entry(win)
        formula_entry.pack(pady=5, padx=20, fill=tk.X)

        ttk.Label(win, text="Motivo (Opzionale):").pack(pady=(10, 0))
        reason_entry = ttk.Entry(win)
        reason_entry.pack(pady=5, padx=20, fill=tk.X)

        def submit():
            action_type = action_var.get()
            formula = formula_entry.get().strip()
            reason = reason_entry.get().strip()
            
            if not formula:
                messagebox.showerror("Errore", "Inserisci una formula valida.")
                return
                
            from common.dice import roll_dice
            try:
                result = roll_dice(formula)
                total = result['total']
                
                with self.server.game_state.lock:
                    if action_type == "damage":
                        target_player.hp = max(0, target_player.hp - total)
                        action_text = "infliggendo danni"
                    elif action_type == "heal":
                        target_player.hp = min(target_player.max_hp, target_player.hp + total)
                        action_text = "curando"
                
                log_msg = f"DM usa '{reason}' su {target_name} {action_text}: {total} (Tiro: {formula} = {result['rolls']}+{result['modifier']})"
                self.log_to_chat(f"[COMBAT] {log_msg}")
                broadcast(self.server.game_state, make_chat_broadcast("Sistema", log_msg))
                
                self.server.game_state._trigger_gui_update()
                broadcast(self.server.game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, getattr(target_player, "conditions", [])))
                win.destroy()
            except ValueError as e:
                messagebox.showerror("Errore Dadi", str(e))

        ttk.Button(win, text="Esegui Azione", command=submit, style="Primary.TButton").pack(pady=20)

    def send_dm_chat(self):
        text = self.chat_entry.get().strip()
        if not text: return
        try: active_tab_name = self.notebook.tab(self.notebook.select(), "text")
        except tk.TclError: return
        
        if active_tab_name == "Sistema":
            broadcast(self.server.game_state, make_chat_broadcast("DM", text))
            self.log_to_chat(text, tab_name="Sistema", sender="DM", color="#EB459E")
        else:
            target_player = self.server.game_state.find_player(active_tab_name)
            if target_player:
                if target_player.conn:
                    send_message(target_player.conn, make_chat_broadcast("DM", text, is_whisper=True))
                    self.log_to_chat(text, tab_name=active_tab_name, sender="DM", color="#EB459E")
                else:
                    messagebox.showerror("Errore", f"L'entità '{active_tab_name}' è offline o è un NPC.")
            else: messagebox.showerror("Errore", f"Entità '{active_tab_name}' non trovata.")
        self.chat_entry.delete(0, tk.END)

    def log_to_chat(self, message, tab_name="Sistema", sender="DM", color="white"):
        text_widget = self.chat_tabs.get(tab_name)
        if not text_widget: return
        text_widget.config(state="normal")
        
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
            
        text_widget.config(state="disabled")
        text_widget.see(tk.END)

    def add_npc(self):
        CustomNPCDialog(self)

    def toggle_hide_reveal(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return
        player_name = display_text.split(" (HP")[0].replace("▶", "").replace("➡️", "").strip()
        if player_name.startswith("[N] "):
            player_name = player_name[4:]
        player = self.server.game_state.find_player(player_name)
        if not player: return
        
        player.is_hidden = not getattr(player, "is_hidden", False)
        self.server.game_state._trigger_gui_update()
        broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
        self.log_to_chat(f"[SISTEMA] {player_name} è ora {'nascosto' if player.is_hidden else 'visibile'}.")

    def on_player_selected(self, event):
        for widget in self.npc_actions_frame.winfo_children():
            widget.destroy()
            
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return
        if display_text.startswith("---"): return
        
        player_name = display_text.split(" (HP")[0].replace("▶", "").replace("➡️", "").strip()
        if player_name.startswith("[N] "):
            player_name = player_name[4:]
            
        player = self.server.game_state.find_player(player_name)
        if not player or not getattr(player, "full_sheet", None): return
        
        actions = player.full_sheet.get("actions", [])
        if not actions:
            ttk.Label(self.npc_actions_frame, text="Nessuna azione SRD").pack(pady=2)
            return
            
        for act in actions:
            btn = ttk.Button(self.npc_actions_frame, text=act.get("name", "Azione"), 
                             command=lambda a=act, n=player_name: self.roll_npc_action(n, a))
            btn.pack(fill=tk.X, pady=1)
            
    def roll_npc_action(self, npc_name, action_dict):
        from common.dice import roll_dice
        act_name = action_dict.get("name", "Azione")
        msg = f"{npc_name} usa {act_name}!"
        
        atk_bonus = action_dict.get("attack_bonus")
        if atk_bonus is not None:
            mod_str = f"+{atk_bonus}" if int(atk_bonus) >= 0 else str(atk_bonus)
            try:
                res = roll_dice(f"1d20{mod_str}")
                msg += f"\nTiro per Colpire: {res['total']} (Dado: {res['rolls'][0]})"
            except:
                pass
            
        dmg_dice = action_dict.get("damage_dice")
        if dmg_dice:
            try:
                res = roll_dice(dmg_dice)
                msg += f"\nDanni: {res['total']} (Dadi: {res['rolls']})"
            except:
                pass
            
        self.log_to_chat(f"[COMBAT] {msg}")
        from common.protocol import make_chat_broadcast
        broadcast(self.server.game_state, make_chat_broadcast("DM", msg))

    def toggle_mute(self):
        if not hasattr(self, 'voice_client'):
            return
        self.voice_client.is_muted = not self.voice_client.is_muted
        if self.voice_client.is_muted:
            self.btn_mute.config(fg="red", text=" 🔇 ")
        else:
            self.btn_mute.config(fg="white", text=" 🎤 ")

    def toggle_deafen(self):
        if not hasattr(self, 'voice_client'):
            return
        self.voice_client.is_deafened = not self.voice_client.is_deafened
        if self.voice_client.is_deafened:
            self.btn_deafen.config(fg="red", text=" 🔇 ")
        else:
            self.btn_deafen.config(fg="white", text=" 🎧 ")

    def search_bestiario(self):
        if hasattr(self, 'bestiary_panel'):
            self.bestiary_panel.search_bestiario()
            self.bestiario_results = self.bestiary_panel.bestiario_results

    def _search_bestiario_thread(self, query, initial_results):
        if hasattr(self, 'bestiary_panel'):
            self.bestiary_panel._search_bestiario_thread(query, initial_results)

    def _update_bestiario_list(self, results):
        if hasattr(self, 'bestiary_panel'):
            self.bestiary_panel._update_bestiario_list(results)
            self.bestiario_results = self.bestiary_panel.bestiario_results

    def _on_bestiario_selected(self, event=None):
        if hasattr(self, 'bestiary_panel'):
            self.bestiary_panel._on_bestiario_selected(event)

    def open_bestiario_manual_entry(self):
        if hasattr(self, 'bestiary_panel'):
            self.bestiary_panel.open_bestiario_manual_entry()

    def spawn_bestiario(self):
        if hasattr(self, 'bestiary_panel'):
            self.bestiary_panel.spawn_bestiario()

    def _spawn_bestiario_thread(self, index_selezionato):
        if hasattr(self, 'bestiary_panel'):
            self.bestiary_panel._spawn_bestiario_thread(index_selezionato)


    def open_set_owner_dialog(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return
        player_name = display_text.split(" (HP")[0].replace("? ", "").strip()
        player = self.server.game_state.find_player(player_name)
        
        if not player: return
        
        from common.messagebox import messagebox
        from tkinter import simpledialog
        owner = simpledialog.askstring("Imposta Proprietario", f"Chi controlla {player_name}? (Nome esatto del giocatore, vuoto per DM):", parent=self.master, initialvalue=getattr(player, 'owner', '') or '')
        if owner is not None:
            player.owner = owner.strip() if owner.strip() else None
            self.server.game_state._trigger_gui_update()
            from common.protocol import make_game_state
            from server.network import broadcast
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            self.log_to_chat(f"[SISTEMA] Proprietario di {player_name} impostato a {player.owner or 'DM'}.")



    def open_loot_generator_dialog(self):
        from server.dm_generators import LootGeneratorDialog
        LootGeneratorDialog(self.master, self.server.game_state)

    def open_random_npc_dialog(self):
        from server.dm_generators import RandomNPCDialog
        RandomNPCDialog(self.master, self.server.game_state)

    def toggle_inspiration(self):
        sel_name = self.get_selected_player_name()
        if not sel_name: return
        p = self.server.game_state.find_player(sel_name)
        if not p: return
        
        cur = getattr(p, "has_inspiration", False)
        new_val = not cur
        p.has_inspiration = new_val
        if p.full_sheet:
            p.full_sheet["has_inspiration"] = new_val
            
        from common.protocol import make_chat_broadcast, make_update_inspiration
        if new_val:
            msg = f"🌟 {p.name} ha ricevuto l'Ispirazione dal Dungeon Master!"
        else:
            msg = f"☆ L'Ispirazione di {p.name} è stata rimossa dal Dungeon Master."
            
        broadcast(self.server.game_state, make_chat_broadcast("Sistema", msg))
        self.log_to_chat(f"[ISPIRAZIONE] {msg}")
        
        if getattr(p, "conn", None):
            send_message(p.conn, make_update_inspiration(new_val))
            
        self.server.game_state._trigger_gui_update()
        messagebox.showinfo("Ispirazione", f"Ispirazione per {p.name}: {'CONCESSA (⭐)' if new_val else 'RIMOSSA'}", parent=self.master)

    def toggle_fow_quick_tool(self):
        """Abilita la Nebbia di Guerra e cicla rapidamente lo strumento Nebbia (Muovi -> Cancella -> Disegna)."""
        modes = [_t("fow_mode_move"), _t("fow_mode_erase"), _t("fow_mode_draw")]
        cur_mode = self.fow_mode_var.get()
        if not self.fow_enabled_var.get():
            self.fow_enabled_var.set(True)
            self.toggle_fow()
            next_mode = _t("fow_mode_erase")
        else:
            try:
                idx = (modes.index(cur_mode) + 1) % len(modes)
                next_mode = modes[idx]
            except ValueError:
                next_mode = modes[0]
        self.fow_mode_var.set(next_mode)
        is_fow_brush = next_mode != _t("fow_mode_move")
        if hasattr(self, "btn_fow_tool"):
            self.btn_fow_tool.configure(style="ToolActive.TButton" if is_fow_brush else "Tool.TButton")
        if self.map_canvas:
            self.map_canvas.config(cursor="dotbox" if is_fow_brush else "")
        self.show_toast(
            f"Modalità Nebbia: {next_mode} (Nebbia {'Attiva' if self.fow_enabled_var.get() else 'Disattivata'})",
            title="☁️ Nebbia di Guerra",
            toast_type="gold" if is_fow_brush else "info"
        )

    def quick_roll_dm_die(self, sides, event=None):
        """Tira rapidamente 1dX dalla barra sopra la chat DM (Shift+Click=Vantaggio, Ctrl+Click=Svantaggio su d20)."""
        from common.dice import roll_dice
        from common.protocol import make_chat_broadcast
        from server.network import broadcast
        state = getattr(event, "state", 0) if event else 0
        is_shift = bool(state & 0x0001)
        is_ctrl = bool(state & 0x0004)
        formula = f"1d{sides}"
        adv_tag = ""
        if sides == 20 and (is_shift or is_ctrl):
            r1 = roll_dice("1d20")["total"]
            r2 = roll_dice("1d20")["total"]
            chosen = max(r1, r2) if is_shift else min(r1, r2)
            adv_tag = " [Vantaggio]" if is_shift else " [Svantaggio]"
            res = {
                "total": chosen,
                "rolls": [r1, r2],
                "is_crit": (chosen == 20),
                "is_fumble": (chosen == 1)
            }
        else:
            res = roll_dice(formula)

        crit_badge = ""
        if res.get("is_crit"):
            crit_badge = " 🌟 SUCCESSO CRITICO! (20 Naturale)"
            self.show_toast(f"20 NATURALE su {formula}{adv_tag}!", title="🌟 Successo Critico!", toast_type="gold")
        elif res.get("is_fumble"):
            crit_badge = " 💀 FALLIMENTO CRITICO! (1 Naturale)"
            self.show_toast(f"1 NATURALE su {formula}{adv_tag}!", title="💀 Fallimento Critico!", toast_type="danger")

        msg = f"🎲 [DM Tiro Rapido] {formula}{adv_tag} -> Risultato: {res['total']} ({res['rolls']}){crit_badge}"
        broadcast(self.server.game_state, make_chat_broadcast("DM", msg))
        self.log_to_chat(msg, tab_name="Sistema", sender="DM", color="#EB459E")

    def toggle_ruler_mode(self):
        active = self.map_canvas.toggle_ruler_mode()
        style = "ToolActive.TButton" if active else "Tool.TButton"
        if hasattr(self, 'btn_ruler'):
            self.btn_ruler.configure(style=style)
        msg = "Righello attivato: clicca e trascina sulla mappa per misurare la distanza." if active else "Righello disattivato."
        self.show_toast(msg, title="📏 Righello", toast_type="info" if active else "secondary")

    def open_aoe_dialog(self):
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        win.title(_t("aoe_dialog_title", default="Piazza Area d'Effetto (AoE)"))
        win.minsize(360, 380)
        apply_modern_window_style(win)

        ttk.Label(win, text=_t("aoe_shape", default="Forma Area:"), font=FONT_BOLD).pack(pady=5)
        type_var = tk.StringVar(value="sfera")
        frame_radio = ttk.Frame(win)
        frame_radio.pack()
        ttk.Radiobutton(frame_radio, text=_t("aoe_sphere_cube", default="Sfera/Cubo"), variable=type_var, value="sfera").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(frame_radio, text=_t("aoe_cone", default="Cono"), variable=type_var, value="cono").pack(side=tk.LEFT, padx=3)
        ttk.Radiobutton(frame_radio, text=_t("aoe_line", default="Linea"), variable=type_var, value="linea").pack(side=tk.LEFT, padx=3)

        ttk.Label(win, text=_t("aoe_size_hexes", default="Raggio / Lunghezza (esagoni):"), font=FONT_BOLD).pack(pady=5)
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
            ttk.Radiobutton(color_frame, text=cname, variable=color_var, value=cval).pack(side=tk.LEFT, padx=2)

        ttk.Separator(win, orient="horizontal").pack(fill="x", pady=8)

        req_save_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(win, text=_t("aoe_save_auto_npc", default="Richiede Tiro Salvezza (Auto-roll per NPC)"), variable=req_save_var).pack(pady=2)

        save_frame = ttk.Frame(win)
        save_frame.pack(pady=4)

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

        def submit():
            try: sz = int(size_entry.get())
            except: sz = 3
            self.aoe_mode = True
            dc = 10
            if req_save_var.get():
                try: dc = int(dc_entry.get())
                except: dc = 10

            self.aoe_params = {
                "type": type_var.get(), "size": sz, "color": color_var.get(),
                "req_save": req_save_var.get(), "stat": stat_var.get(), "dc": dc,
                "dmg": dmg_entry.get(), "half": half_var.get()
            }
            messagebox.showinfo("AoE", _t("aoe_click_map_prompt", default="Clicca sulla mappa per confermare il bersaglio / centro dell'area d'effetto."), parent=win)
            win.destroy()

        ttk.Button(win, text=_t("btn_confirm_select_center", default="Conferma & Seleziona Centro"), command=submit, style="Primary.TButton").pack(pady=10)

    def _auto_play_battle_music(self):
        try:
            active_c = getattr(self.server.game_state, "active_campaign", None)
            combat_track = None
            if active_c and getattr(active_c, "combat_music", None):
                c_m = active_c.combat_music
                tr_id = c_m.get("id") if isinstance(c_m, dict) else c_m
                combat_track = self.server.game_state.audio_library.get_track(tr_id)
            if not combat_track:
                for tr in self.server.game_state.audio_library.list_tracks():
                    name_l = tr["name"].lower()
                    if any(k in name_l for k in ["battaglia", "combat", "battle", "boss", "combattimento", "lotta"]):
                        combat_track = tr
                        break
            if combat_track:
                self._previous_music = getattr(self.server.game_state, "current_music", None)
                from common.protocol import make_audio_track_play
                msg = make_audio_track_play(combat_track["id"], combat_track["name"], combat_track["ext"], combat_track["size"], channel="music", loop=True, volume=0.8)
                self.server.game_state.current_music = msg
                broadcast(self.server.game_state, msg)
                if getattr(self, "audio_dm_listen_var", None) and self.audio_dm_listen_var.get():
                    self.audio_manager.play(self.server.game_state.audio_library.get_path(combat_track["id"]), channel="music", loop=True, volume=0.8, name=combat_track["name"])
                if hasattr(self, "audio_now_playing"):
                    self.audio_now_playing.config(text=f"In riproduzione: ⚔️ {combat_track['name']} (loop)")
                self.log_to_chat(f"[SOUNDSCAPE] ⚔️ Colonna sonora di combattimento: {combat_track['name']}")
        except Exception as e:
            print(f"[SOUNDSCAPE] Errore musica combattimento: {e}")

    def _auto_restore_scene_music(self):
        try:
            from common.protocol import make_audio_stop
            prev = getattr(self, "_previous_music", None)
            if prev:
                self.server.game_state.current_music = prev
                broadcast(self.server.game_state, prev)
                t_id = prev["data"]["track_id"]
                t_name = prev["data"]["name"]
                if getattr(self, "audio_dm_listen_var", None) and self.audio_dm_listen_var.get():
                    self.audio_manager.play(self.server.game_state.audio_library.get_path(t_id), channel="music", loop=prev["data"].get("loop", True), volume=prev["data"].get("volume", 0.8), name=t_name)
                if hasattr(self, "audio_now_playing"):
                    self.audio_now_playing.config(text=f"In riproduzione: 🎵 {t_name}")
                self.log_to_chat(f"[SOUNDSCAPE] 🎵 Musica di scena ripristinata: {t_name}")
                self._previous_music = None
            else:
                broadcast(self.server.game_state, make_audio_stop("music"))
                self.audio_manager.stop("music")
                self.server.game_state.current_music = None
                if hasattr(self, "audio_now_playing"):
                    self.audio_now_playing.config(text="In riproduzione: -")
        except Exception as e:
            print(f"[SOUNDSCAPE] Errore ripristino musica: {e}")

    def open_manuals_dialog(self, initial_query=""):
        try:
            from client.manuals_ui import ManualsDialog
            def on_share(text):
                from common.protocol import make_chat_broadcast
                from server.network import broadcast
                self.log_to_chat(text, tab_name="Sistema")
                broadcast(self.server.game_state, make_chat_broadcast("Manuali 5e", text))
            ManualsDialog(self.master, share_callback=on_share, initial_query=initial_query)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire i manuali: {e}")


if __name__ == "__main__":
    import tkinter as tk
    root = tk.Tk()
    DM_GUI(root)
    root.mainloop()
