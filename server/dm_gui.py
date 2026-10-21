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
from io import BytesIO
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
from common.hex_utils import Hex, get_sphere_hexes
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
from common.srd_offline import (
    extract_and_normalize_attributes,
    format_monster_action_tooltip,
    get_monster_offline,
    normalize_ac_value,
    normalize_speed_value,
    normalize_size_value,
    normalize_damage_list,
    extract_legendary_stats,
    extract_darkvision_flag,
)
from server.dm_bestiary_panel import DMBestiaryPanel
from server.dm_soundboard_panel import DMSoundboardPanel
from server.dm_automation_panel import (
    open_automation_settings_dialog as dm_open_automation_settings_dialog,
    update_pending_actions_ui as dm_update_pending_actions_ui,
    apply_pending_damage_gui as dm_apply_pending_damage_gui,
    apply_pending_damage_custom_gui as dm_apply_pending_damage_custom_gui,
    resolve_pending_door_gui as dm_resolve_pending_door_gui
)
from server.dm_travel_dialog import (
    open_travel_panel as dm_open_travel_panel
)
from server.dm_entity_dialogs import (
    open_combat_config as dm_open_combat_config,
    open_room_pin_dialog as dm_open_room_pin_dialog,
    open_assign_item_dialog as dm_open_assign_item_dialog,
    open_modify_hp_dialog as dm_open_modify_hp_dialog,
    open_conditions_dialog as dm_open_conditions_dialog,
    open_aura_dialog as dm_open_aura_dialog,
    open_light_source_dialog as dm_open_light_source_dialog,
    open_boss_config_dialog as dm_open_boss_config_dialog,
    open_spend_legendary_action_dialog as dm_open_spend_legendary_action_dialog,
    open_place_trap_dialog as dm_open_place_trap_dialog,
    remove_trap_at as dm_remove_trap_at,
    reset_trap_at as dm_reset_trap_at
)

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

        # Inizializza SessionLedger per il tracking live e la cronistoria
        from common.session_chronicle import SessionLedger
        c_name = self.initial_campaign.name if self.initial_campaign else "Campagna"
        s_date = getattr(self.initial_campaign, "start_date", {"year": 1492, "month": 1, "day": 1, "hour": 8}) if self.initial_campaign else {"year": 1492, "month": 1, "day": 1, "hour": 8}
        s_weather = getattr(self.initial_campaign, "start_weather", "Sereno") if self.initial_campaign else "Sereno"
        self.session_ledger = SessionLedger(
            campaign_name=c_name,
            start_game_date=s_date,
            current_game_date=s_date,
            current_weather=s_weather
        )
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
        file_menu.add_command(label=_t("menu_close_campaign"), command=self.close_active_campaign)
        file_menu.add_separator()
        file_menu.add_command(label="🧭 Flusso Live della Campagna (Ctrl+N)", command=self.open_live_flow_controller)
        file_menu.add_command(label="📜 Cronistoria & Recap Sessione...", command=self.open_session_chronicle_dialog)
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
        tools_menu.add_command(label=_t("menu_encounter_builder"), command=self.open_encounter_builder)
        tools_menu.add_command(label=_t("menu_loot_gen"), command=self.open_loot_generator_dialog)
        tools_menu.add_command(label=_t("menu_npc_gen"), command=self.open_random_npc_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label=_t("menu_map_editor"), command=self.open_map_editor)
        tools_menu.add_command(label=_t("menu_download_maps"), command=self.open_map_downloader)
        tools_menu.add_separator()
        tools_menu.add_command(label=_t("menu_quest_log"), command=self.open_quest_dialog)
        tools_menu.add_command(label=_t("menu_share_image"), command=self.share_image_handout)
        tools_menu.add_command(label=_t("menu_share_text"), command=self.share_text_handout)
        tools_menu.add_separator()
        tools_menu.add_command(label=_t("menu_srd_compendium"), command=self.open_srd_importer)
        tools_menu.add_command(label=_t("tool_command_palette"), command=self.open_command_palette)
        tools_menu.add_command(label=_t("menu_manuals"), command=self.open_manuals_dialog)
        tools_menu.add_command(label=_t("menu_travel_panel"), command=self.open_travel_panel)
        tools_menu.add_command(label=_t("menu_starter_pack"), command=self.open_campaign_starter_kit_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label=_t("menu_automation_settings"), command=self.open_automation_settings_dialog)
        menubar.add_cascade(label=_t("menu_tools"), menu=tools_menu)

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
        if hasattr(self, 'btn_encounter_builder'):
            self.btn_encounter_builder.config(text=_t("btn_encounter_builder", default="⚔️ Encounter Builder"))
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
            self.weather_combo['values'] = [_t("weather_clear"), _t("weather_rain"), _t("weather_storm"), _t("weather_snow"), _t("weather_fog"), _t("weather_darkness")]

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
        
        self.btn_ruler = None

        self.btn_fow_tool = ttk.Button(left_toolbar, text="☁️", width=3, style="Tool.TButton", command=self.toggle_fow_quick_tool)
        self.btn_fow_tool.pack(pady=3)
        ToolTip(self.btn_fow_tool, lambda: _t("tool_fog_of_war"))
        
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
        btn_teleport = ttk.Checkbutton(left_toolbar, text="🌀", width=3, style="Toolbutton", variable=self.teleport_mode_var)
        btn_teleport.pack(pady=3)
        ToolTip(btn_teleport, "Teletrasporto / Transizione Mappa (Click su esagono per impostare teleport)")

        self.door_mode_var = tk.BooleanVar(value=False)
        self.btn_door = ttk.Checkbutton(left_toolbar, text="🚪", width=3, style="Toolbutton", variable=self.door_mode_var)
        self.btn_door.pack(pady=3)
        ToolTip(self.btn_door, "Porte Interattive 5e (Click per aggiungere o gestire porte: aperta, chiusa, serrata, segreta)")

        self.room_pin_mode_var = tk.BooleanVar(value=False)
        self.btn_room_pin = ttk.Checkbutton(left_toolbar, text="📌", width=3, style="Toolbutton", variable=self.room_pin_mode_var)
        self.btn_room_pin.pack(pady=3)
        ToolTip(self.btn_room_pin, "Spille Stanza DM (Note segrete e testo da leggere al gruppo)")

        self.terrain_paint_mode = False
        self.active_terrain_brush = "fango"
        self.btn_terrain = ttk.Button(left_toolbar, text="🪨", width=3, style="Tool.TButton", command=self.toggle_terrain_paint_tool)
        self.btn_terrain.pack(pady=3)
        ToolTip(self.btn_terrain, "Pennello Terreno Difficile (Click per dipingere Fango/Ghiaccio/Rovi/Macerie/Palude)")

        self.btn_darkness = ttk.Button(left_toolbar, text="🌑", width=3, style="Tool.TButton", command=self.toggle_darkness_filter)
        self.btn_darkness.pack(pady=3)
        ToolTip(self.btn_darkness, "Filtro Oscurità D&D 5e (Click per attivare/disattivare l'oscurità sulla mappa)")

        btn_manuals = ttk.Button(left_toolbar, text="📖", width=3, style="Tool.TButton", command=self.open_manuals_dialog)
        btn_manuals.pack(pady=3)
        ToolTip(btn_manuals, lambda: _t("tool_manuals"))

        btn_palette = ttk.Button(left_toolbar, text="🔍", width=3, style="Tool.TButton", command=self.open_command_palette)
        btn_palette.pack(pady=3)
        ToolTip(btn_palette, lambda: _t("tool_command_palette"))

        # Pulsante rapido Schermo Intero in fondo alla barra
        self.btn_fullscreen = ttk.Button(left_toolbar, text="⛶", width=3, style="Tool.TButton", command=self.toggle_fullscreen)
        self.btn_fullscreen.pack(side=tk.BOTTOM, pady=(0, 4))
        ToolTip(self.btn_fullscreen, lambda: _t("menu_fullscreen"))
        
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
            highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2"
        )
        self.top_status_time_lbl.pack(side=tk.LEFT, padx=3)
        self.top_status_time_lbl.bind("<Button-1>", self._show_time_fast_menu)
        ToolTip(self.top_status_time_lbl, "Orologio Campagna (Clicca per avanzare il tempo o aprire il calendario)")
        
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
        
        self.top_status_env_lbl = tk.Label(
            pills_frame, text=_t("map_env_outdoor"), font=FONT_SMALL,
            bg=SURFACE_COLOR_ALT, fg=ACCENT_GREEN, padx=6, pady=2,
            highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2"
        )
        self.top_status_env_lbl.pack(side=tk.LEFT, padx=3)
        self.top_status_env_lbl.bind("<Button-1>", lambda e: self.toggle_map_outdoor())
        ToolTip(self.top_status_env_lbl, lambda: _t("map_env_tooltip"))
        
        self.top_status_automation_lbl = tk.Label(
            pills_frame, text="⚡ Full Auto", font=FONT_SMALL,
            bg=SURFACE_COLOR_ALT, fg=ACCENT_GREEN, padx=6, pady=2,
            highlightbackground=BORDER_COLOR, highlightthickness=1, cursor="hand2"
        )
        self.top_status_automation_lbl.pack(side=tk.LEFT, padx=3)
        self.top_status_automation_lbl.bind("<Button-1>", lambda e: self.open_automation_settings_dialog())
        ToolTip(self.top_status_automation_lbl, "Stile Gestione Campagna (Clicca per configurare)")
        
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

        # Contenitore Azioni in Sospeso (Decisioni DM per Danni / Porte / ecc.)
        self.pending_actions_container = tk.Frame(tab_chat, bg=SURFACE_COLOR_ALT, highlightbackground=ACCENT_GOLD, highlightthickness=1, padx=6, pady=6)
        
        # 1-Click Quick Dice Strip (DM)
        dm_quick_dice_strip = tk.Frame(tab_chat, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=3)
        self.dm_quick_dice_strip = dm_quick_dice_strip
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
        self.btn_encounter_builder = ttk.Button(btn_frame_bottom, text=_t("btn_encounter_builder", default="⚔️ Encounter Builder"), command=self.open_encounter_builder, style="Primary.TButton")
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

        flow_btn_box = tk.Frame(tab_world, bg=BG_COLOR)
        flow_btn_box.pack(fill=tk.X, pady=(0, 6))
        self.btn_live_flow = ttk.Button(flow_btn_box, text="🧭 Flusso Live", command=self.open_live_flow_controller, style='Gold.TButton')
        self.btn_live_flow.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        self.btn_chronicle = ttk.Button(flow_btn_box, text="📜 Cronistoria", command=self.open_session_chronicle_dialog, style='Info.TButton')
        self.btn_chronicle.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
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
        self.weather_combo = ttk.Combobox(tab_world, textvariable=self.weather_var, values=[_t("weather_clear"), _t("weather_rain"), _t("weather_storm"), _t("weather_snow"), _t("weather_fog"), _t("weather_darkness")], state="readonly")
        self.weather_combo.pack(fill=tk.X)
        self.weather_combo.bind("<<ComboboxSelected>>", self.on_weather_changed)
        
        # Tab 4 ("Audio/Sfx")
        tab_audio = ttk.Frame(self.right_notebook, padding=5)
        self.right_notebook.add(tab_audio, text=_t("tab_audio_sfx"))
        self.build_audio_tab(tab_audio)
        self.setup_player_context_menu()

        # Scorciatoia universale Command Palette (Ctrl+K)
        self.master.bind("<Control-k>", self.open_command_palette)
        self.master.bind("<Control-n>", lambda e: self.open_live_flow_controller())
        self.master.bind("<Control-N>", lambda e: self.open_live_flow_controller())
        self.master.bind("<Control-K>", self.open_command_palette)
        # Scorciatoia Schermo Intero (F11 / Esc)
        self.master.bind("<F11>", self.toggle_fullscreen)
        self.master.bind("<Escape>", self.exit_fullscreen)

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

    def _handle_command_palette_action(self, action_type, payload):
        if action_type == "action" and payload == "toggle_fullscreen":
            self.toggle_fullscreen()
            return
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
                
                attrs = extract_and_normalize_attributes(m.get("attributes"), m["name"])
                dex_val = attrs.get("DES", 10)
                npc.initiative = m.get("initiative") if m.get("initiative") is not None else (dex_val - 10) // 2
                
                ac = normalize_ac_value(m.get("ac", m.get("armor_class", 10)))
                speed_val, speed_disp, speed_unit = normalize_speed_value(m.get("speed", 30))
                npc.speed = speed_val
                npc.speed_unit = speed_unit
                npc.size = normalize_size_value(m.get("size"))
                npc.damage_resistances = normalize_damage_list(m.get("damage_resistances", m.get("resistances", [])))
                npc.damage_immunities = normalize_damage_list(m.get("damage_immunities", m.get("immunities", [])))
                npc.damage_vulnerabilities = normalize_damage_list(m.get("damage_vulnerabilities", m.get("vulnerabilities", [])))
                leg_res, leg_act, has_lair = extract_legendary_stats(m)
                npc.legendary_resistances_max = leg_res
                npc.legendary_resistances_current = leg_res
                npc.legendary_actions_max = leg_act
                npc.legendary_actions_current = leg_act
                npc.has_lair_actions = has_lair
                npc.has_darkvision = extract_darkvision_flag(m)

                npc.full_sheet = {
                    "name": npc.name,
                    "char_class": "Mostro/NPC",
                    "level": 1,
                    "hp_current": npc.hp,
                    "hp_max": npc.max_hp,
                    "ac": ac,
                    "speed": speed_val,
                    "speed_display": speed_disp,
                    "speed_unit": speed_unit,
                    "attributes": attrs,
                    "cr": str(m.get("cr", "1")),
                    "size": m.get("size", "Medium"),
                    "actions": m.get("actions", []),
                    "features": m.get("features", m.get("special_abilities", [])),
                    "damage_resistances": npc.damage_resistances,
                    "damage_immunities": npc.damage_immunities,
                    "damage_vulnerabilities": npc.damage_vulnerabilities,
                    "legendary_resistances_max": leg_res,
                    "legendary_actions_max": leg_act,
                    "has_lair_actions": has_lair
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
        ac = normalize_ac_value(item_data.get("armor_class", item_data.get("ac", 10)))
        speed_val, speed_disp, speed_unit = normalize_speed_value(item_data.get("speed", 30))

        attrs = extract_and_normalize_attributes(item_data, base_name)
        dex_val = attrs.get("DES", 10)
        initiative = item_data.get("initiative")
        if initiative is None or initiative == 0:
            initiative = (dex_val - 10) // 2
            
        npc = Player(new_name, None, None)
        npc.hp = hp
        npc.max_hp = hp
        npc.initiative = initiative
        npc.speed = speed_val
        npc.speed_unit = speed_unit
        npc.size = normalize_size_value(item_data.get("size"))
        npc.damage_resistances = normalize_damage_list(item_data.get("damage_resistances", item_data.get("resistances", [])))
        npc.damage_immunities = normalize_damage_list(item_data.get("damage_immunities", item_data.get("immunities", [])))
        npc.damage_vulnerabilities = normalize_damage_list(item_data.get("damage_vulnerabilities", item_data.get("vulnerabilities", [])))
        leg_res, leg_act, has_lair = extract_legendary_stats(item_data)
        npc.legendary_resistances_max = leg_res
        npc.legendary_resistances_current = leg_res
        npc.legendary_actions_max = leg_act
        npc.legendary_actions_current = leg_act
        npc.has_lair_actions = has_lair
        npc.has_darkvision = extract_darkvision_flag(item_data)
        
        npc.full_sheet = {
            "name": npc.name,
            "char_class": "Mostro/NPC",
            "level": 1,
            "hp_current": npc.hp,
            "hp_max": npc.max_hp,
            "ac": ac,
            "speed": speed_val,
            "speed_display": speed_disp,
            "speed_unit": speed_unit,
            "attributes": attrs,
            "cr": str(item_data.get("challenge_rating", item_data.get("cr", "1"))),
            "size": item_data.get("size", "Medium"),
            "actions": item_data.get("actions", []),
            "features": item_data.get("features", item_data.get("special_abilities", [])),
            "damage_resistances": npc.damage_resistances,
            "damage_immunities": npc.damage_immunities,
            "damage_vulnerabilities": npc.damage_vulnerabilities,
            "legendary_resistances_max": leg_res,
            "legendary_actions_max": leg_act,
            "has_lair_actions": has_lair
        }
        
        self.server.game_state.add_player(npc)
        
        from common.protocol import make_player_joined, make_game_state
        broadcast(self.server.game_state, make_player_joined(npc.to_dict()))
        broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
        
        self.log_to_chat(f"[SISTEMA] Mostro '{npc.name}' spawnato sulla mappa.")
        self.server.game_state._trigger_gui_update()

    def handle_srd_import(self, entity_data, category=None):
        name = entity_data.get("name", "Mostro")
        npc = Player(name, None, None)
        npc.hp = entity_data.get("hp", entity_data.get("hit_points", 10))
        npc.max_hp = npc.hp
        
        attrs = extract_and_normalize_attributes(entity_data, name)
        dex_val = attrs.get("DES", 10)
        initiative = entity_data.get("initiative")
        if initiative is None or initiative == 0:
            initiative = (dex_val - 10) // 2
        npc.initiative = initiative
        
        ac = normalize_ac_value(entity_data.get("ac", entity_data.get("armor_class", 10)))
        speed_val, speed_disp, speed_unit = normalize_speed_value(entity_data.get("speed", 30))
        npc.speed = speed_val
        npc.speed_unit = speed_unit
        npc.size = normalize_size_value(entity_data.get("size"))
        npc.damage_resistances = normalize_damage_list(entity_data.get("damage_resistances", entity_data.get("resistances", [])))
        npc.damage_immunities = normalize_damage_list(entity_data.get("damage_immunities", entity_data.get("immunities", [])))
        npc.damage_vulnerabilities = normalize_damage_list(entity_data.get("damage_vulnerabilities", entity_data.get("vulnerabilities", [])))
        leg_res, leg_act, has_lair = extract_legendary_stats(entity_data)
        npc.legendary_resistances_max = leg_res
        npc.legendary_resistances_current = leg_res
        npc.legendary_actions_max = leg_act
        npc.legendary_actions_current = leg_act
        npc.has_lair_actions = has_lair
        npc.has_darkvision = extract_darkvision_flag(entity_data)

        # Add basic full sheet data from SRD
        npc.full_sheet = {
            "name": npc.name,
            "char_class": "Mostro/NPC",
            "level": 1,
            "hp_current": npc.hp,
            "hp_max": npc.max_hp,
            "ac": ac,
            "speed": speed_val,
            "speed_display": speed_disp,
            "speed_unit": speed_unit,
            "attributes": attrs,
            "cr": str(entity_data.get("challenge_rating", entity_data.get("cr", "1"))),
            "size": entity_data.get("size", "Medium"),
            "actions": entity_data.get("actions", []),
            "features": entity_data.get("features", entity_data.get("special_abilities", "")),
            "damage_resistances": npc.damage_resistances,
            "damage_immunities": npc.damage_immunities,
            "damage_vulnerabilities": npc.damage_vulnerabilities,
            "legendary_resistances_max": leg_res,
            "legendary_actions_max": leg_act,
            "has_lair_actions": has_lair
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
        return dm_open_combat_config(self, initiator_name=initiator_name)

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
        
        if hasattr(self, "session_ledger") and self.session_ledger:
            self.session_ledger.record_time_advance(
                hours=hours,
                new_date={"year": gs.time_year, "month": gs.time_month, "day": gs.time_day, "hour": gs.time_hour},
                new_weather=getattr(gs, "weather", "Sereno")
            )
        gs._trigger_gui_update()
        broadcast(gs, make_game_state(gs.get_state_dict()))

    def on_weather_changed(self, event=None):
        gs = self.server.game_state
        raw_val = self.weather_var.get()
        from common.i18n import WEATHER_EN_TO_IT, translate_weather
        canonical = WEATHER_EN_TO_IT.get(raw_val.strip(), raw_val.strip())
        gs.weather = canonical
        weather_icons = {
            "Sereno": "☀️", "Pioggia": "🌧️", "Tempesta": "⛈️", "Neve": "❄️", "Nebbia": "🌫️", "Oscurità": "🌑",
            "Clear": "☀️", "Rain": "🌧️", "Storm": "⛈️", "Snow": "❄️", "Fog": "🌫️", "Darkness": "🌑"
        }
        w_icon = weather_icons.get(canonical, "🌤️")
        disp_weather = translate_weather(canonical)
        if canonical in ("Oscurità", "Darkness"):
            msg = f"{w_icon} Filtro Oscurità D&D 5e attivato! (Svantaggio all'attacco per chi non vede, Vantaggio per chi possiede Scurovisione)"
        else:
            msg = f"{w_icon} Il clima cambia in: {disp_weather}"
        self.log_to_chat(msg)
        from common.protocol import make_chat_broadcast, make_game_state
        from server.network import broadcast
        broadcast(gs, make_chat_broadcast("Sistema", msg))
        if hasattr(self, "session_ledger") and self.session_ledger:
            self.session_ledger.current_weather = canonical
        gs._trigger_gui_update()
        broadcast(gs, make_game_state(gs.get_state_dict()))
        self.update_state()

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

            # Menu Terreno Difficile al volo D&D 5e
            diff_menu = tk.Menu(map_menu, tearoff=0)
            diff_terrain = cur_map.setdefault("difficult_terrain", {}) if cur_map else {}
            pos_key = f"{clicked_hex.q},{clicked_hex.r}"
            current_t = diff_terrain.get(pos_key)

            diff_menu.add_command(label="💩 Fango / Melma (x2 Movimento)", command=lambda: self.set_difficult_terrain_at(clicked_hex, "fango"))
            diff_menu.add_command(label="🧊 Ghiaccio / Scivoloso (TS Des o Prono, Svantaggio)", command=lambda: self.set_difficult_terrain_at(clicked_hex, "ghiaccio"))
            diff_menu.add_command(label="🌿 Rovi / Spine (1d4 Danno, Svantaggio)", command=lambda: self.set_difficult_terrain_at(clicked_hex, "rovi"))
            diff_menu.add_command(label="🪨 Macerie / Rocce (x2 Movimento)", command=lambda: self.set_difficult_terrain_at(clicked_hex, "macerie"))
            diff_menu.add_command(label="🌊 Palude / Acqua Profonda (x2 Movimento, Svantaggio)", command=lambda: self.set_difficult_terrain_at(clicked_hex, "palude"))
            if current_t:
                diff_menu.add_separator()
                diff_menu.add_command(label=f"🗑️ Rimuovi Terreno Difficile ({str(current_t).capitalize()})", command=lambda: self.remove_difficult_terrain_at(clicked_hex))

            map_menu.add_cascade(label=f"🌾 Terreno Difficile{' (' + str(current_t).capitalize() + ')' if current_t else ''}...", menu=diff_menu)
            map_menu.add_separator()
            map_menu.add_command(label="🌑 Piazza Sfera di Oscurità Magica (R=3)", command=lambda: self.place_darkness_sphere_at(clicked_hex))

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

    def set_difficult_terrain_at(self, clicked_hex, terrain_type="fango"):
        """Imposta un tipo di terreno difficile al volo su un esagono e sincronizza tutti i client."""
        if not getattr(self.server.game_state, "current_map", None): return
        cur_map = self.server.game_state.current_map
        diff_terrain = cur_map.setdefault("difficult_terrain", {})
        pos_key = f"{clicked_hex.q},{clicked_hex.r}"
        diff_terrain[pos_key] = terrain_type

        from common.protocol import make_map_data_update_broadcast
        from server.network import broadcast
        broadcast(self.server.game_state, make_map_data_update_broadcast(cur_map))
        self.server.game_state._trigger_gui_update()
        self.log_to_chat(f"[TERRENO] Applicato terreno difficile ({terrain_type.capitalize()}) a [{clicked_hex.q}, {clicked_hex.r}].")
        self.redraw_map_and_players()

    def remove_difficult_terrain_at(self, clicked_hex):
        """Rimuove il terreno difficile da un esagono al volo e sincronizza i client."""
        if not getattr(self.server.game_state, "current_map", None): return
        cur_map = self.server.game_state.current_map
        diff_terrain = cur_map.get("difficult_terrain", {})
        pos_key = f"{clicked_hex.q},{clicked_hex.r}"
        if pos_key in diff_terrain:
            del diff_terrain[pos_key]
        pos_tup = [clicked_hex.q, clicked_hex.r]
        if isinstance(diff_terrain, list) and pos_tup in diff_terrain:
            diff_terrain.remove(pos_tup)

        from common.protocol import make_map_data_update_broadcast
        from server.network import broadcast
        broadcast(self.server.game_state, make_map_data_update_broadcast(cur_map))
        self.server.game_state._trigger_gui_update()
        self.log_to_chat(f"[TERRENO] Rimosso terreno difficile a [{clicked_hex.q}, {clicked_hex.r}].")
        self.redraw_map_and_players()

    def toggle_terrain_paint_tool(self):
        """Attiva o disattiva la modalità pennello per dipingere terreni difficili al volo sulla mappa."""
        if getattr(self, "terrain_paint_mode", False):
            self.terrain_paint_mode = False
            self.btn_terrain.config(style="Tool.TButton")
            self.log_to_chat("[SISTEMA] Modalità pennello terreno difficile disattivata.")
            return

        menu = tk.Menu(self.master, tearoff=0)
        types = [
            ("fango", "💩 Fango (x2 Movimento)"),
            ("ghiaccio", "🧊 Ghiaccio (TS Des CD10 o Prono)"),
            ("rovi", "🌿 Rovi (1d4 Danno da Spine)"),
            ("macerie", "🪨 Macerie (x2 Movimento)"),
            ("palude", "🌊 Palude (x2 Movimento, Svantaggio)"),
            ("clear", "🗑️ Cancella Terreno (Gomma)")
        ]
        def pick_brush(t):
            self.active_terrain_brush = t
            self.terrain_paint_mode = True
            self.btn_terrain.config(style="Primary.TButton")
            self.log_to_chat(f"[SISTEMA] Pennello terreno difficile attivo: {t.capitalize()}. Clicca sulle caselle della mappa per applicare.")

        for code, label in types:
            menu.add_command(label=label, command=lambda c=code: pick_brush(c))

        bx = self.btn_terrain.winfo_rootx() + self.btn_terrain.winfo_width()
        by = self.btn_terrain.winfo_rooty()
        menu.tk_popup(bx, by)

    def toggle_darkness_filter(self):
        """Attiva o disattiva istantaneamente il filtro di Oscurità ambientale sulla mappa (D&D 5e)."""
        gs = self.server.game_state
        cur_w = str(getattr(gs, "weather", "Sereno")).strip().lower()
        if cur_w in ("oscurita", "oscurità", "darkness", "buio"):
            new_w = "Sereno"
            if hasattr(self, "btn_darkness"):
                self.btn_darkness.config(style="Tool.TButton")
            msg = "☀️ Filtro Oscurità disattivato. L'ambiente torna Sereno / Illuminato."
        else:
            new_w = "Oscurità"
            if hasattr(self, "btn_darkness"):
                self.btn_darkness.config(style="Primary.TButton")
            msg = "🌑 Filtro Oscurità D&D 5e attivato! (Svantaggio all'attacco per chi non vede, Vantaggio per chi possiede Scurovisione)."
        
        gs.weather = new_w
        if hasattr(self, "weather_var"):
            from common.i18n import translate_weather
            self.weather_var.set(translate_weather(new_w))
        self.log_to_chat(msg)
        from common.protocol import make_chat_broadcast, make_game_state
        from server.network import broadcast
        broadcast(gs, make_chat_broadcast("Sistema", msg))
        if hasattr(self, "session_ledger") and self.session_ledger:
            self.session_ledger.current_weather = new_w
        gs._trigger_gui_update()
        broadcast(gs, make_game_state(gs.get_state_dict()))
        self.update_state()
        self.redraw_map_and_players()

    def place_darkness_sphere_at(self, clicked_hex, radius=3):
        """Piazza un'area di Oscurità Magica (AoE) centrata sull'esagono selezionato."""
        aoes = self.server.game_state.active_aoes
        aoe_entry = {
            "type": "sfera",
            "size": radius,
            "origin": [clicked_hex.q, clicked_hex.r],
            "color": "#09090b",
            "name": "Oscurità Magica",
            "creator": "DM"
        }
        aoes.append(aoe_entry)
        from common.protocol import make_game_state, make_chat_broadcast
        from server.network import broadcast
        self.server.game_state._trigger_gui_update()
        broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
        broadcast(self.server.game_state, make_chat_broadcast("Sistema", f"🌑 Una sfera di Oscurità Magica (Raggio={radius}) avvolge le coordinate [{clicked_hex.q}, {clicked_hex.r}]!"))
        self.redraw_map_and_players()

    def _show_door_management_menu(self, door, clicked_hex):
        menu = tk.Menu(self.master, tearoff=0)
        cur_st = door.get("state", "closed").upper()
        menu.add_command(label=f"🚪 Porta a [{clicked_hex.q}, {clicked_hex.r}] (Stato: {cur_st})", state="disabled")
        menu.add_separator()
        
        def set_state(st):
            door["state"] = st
            from common.protocol import make_map_data_update_broadcast, make_chat_broadcast, make_fow_update_broadcast
            from server.network import broadcast
            from server.rules.movement import auto_explore_fow
            broadcast(self.server.game_state, make_map_data_update_broadcast(self.server.game_state.current_map))
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", f"🚪 Porta a ({clicked_hex.q}, {clicked_hex.r}) impostata su '{st.upper()}' dal DM."))
            for p in self.server.game_state.players:
                if auto_explore_fow(p, self.server.game_state):
                    broadcast(self.server.game_state, make_fow_update_broadcast(self.server.game_state.current_map["fow_revealed"], self.server.game_state.current_map["fow_draft"]))
            self.server.game_state._trigger_gui_update()
            self.redraw_map_and_players()

        menu.add_command(label="🔓 Imposta: Aperta", command=lambda: set_state("open"))
        menu.add_command(label="🚪 Imposta: Chiusa", command=lambda: set_state("closed"))
        menu.add_command(label="🔒 Imposta: Serrata (a Chiave)", command=lambda: set_state("locked"))
        menu.add_command(label="🚪S Imposta: Segreta (Nascosta ai PG)", command=lambda: set_state("secret"))
        menu.add_separator()
        
        def set_dc():
            cur_dc = door.get("dc", 15)
            new_dc = simpledialog.askinteger("CD Serratura", "Inserisci CD per scassinare la porta (1-30):", initialvalue=cur_dc, minvalue=1, maxvalue=30)
            if new_dc is not None:
                door["dc"] = new_dc
                from common.protocol import make_map_data_update_broadcast
                from server.network import broadcast
                broadcast(self.server.game_state, make_map_data_update_broadcast(self.server.game_state.current_map))
                self.server.game_state._trigger_gui_update()

        def rename_door():
            cur_name = door.get("name", "Porta")
            new_name = simpledialog.askstring("Rinomina Porta", "Inserisci il nome della porta (es. Porta di Ferro, Cancello):", initialvalue=cur_name)
            if new_name:
                door["name"] = new_name
                from common.protocol import make_map_data_update_broadcast
                from server.network import broadcast
                broadcast(self.server.game_state, make_map_data_update_broadcast(self.server.game_state.current_map))
                self.server.game_state._trigger_gui_update()

        def delete_door():
            if messagebox.askyesno("Elimina Porta", f"Rimuovere questa porta a [{clicked_hex.q}, {clicked_hex.r}]?"):
                doors = self.server.game_state.current_map.get("doors", [])
                if door in doors:
                    doors.remove(door)
                from common.protocol import make_map_data_update_broadcast, make_chat_broadcast
                from server.network import broadcast
                from server.rules.movement import auto_explore_fow
                broadcast(self.server.game_state, make_map_data_update_broadcast(self.server.game_state.current_map))
                broadcast(self.server.game_state, make_chat_broadcast("Sistema", f"🚪 Porta a ({clicked_hex.q}, {clicked_hex.r}) rimossa dal DM."))
                for p in self.server.game_state.players:
                    auto_explore_fow(p, self.server.game_state)
                self.server.game_state._trigger_gui_update()
                self.redraw_map_and_players()

        def set_break_dc():
            cur_bdc = door.get("break_dc", door.get("dc", 15) + 2)
            new_bdc = simpledialog.askinteger("CD Sfondare", "Inserisci CD per sfondare la porta con Forza (1-30):", initialvalue=cur_bdc, minvalue=1, maxvalue=30)
            if new_bdc is not None:
                door["break_dc"] = new_bdc
                from common.protocol import make_map_data_update_broadcast
                from server.network import broadcast
                broadcast(self.server.game_state, make_map_data_update_broadcast(self.server.game_state.current_map))
                self.server.game_state._trigger_gui_update()

        def set_key_name():
            cur_key = door.get("key_name", "")
            new_key = simpledialog.askstring("Chiave Richiesta", "Nome dell'oggetto chiave che apre questa porta (es. Chiave di Ferro):", initialvalue=cur_key)
            if new_key is not None:
                door["key_name"] = new_key.strip()
                from common.protocol import make_map_data_update_broadcast
                from server.network import broadcast
                broadcast(self.server.game_state, make_map_data_update_broadcast(self.server.game_state.current_map))
                self.server.game_state._trigger_gui_update()

        menu.add_command(label=f"🔑 Imposta CD Scassinamento (Attuale: {door.get('dc', 15)})...", command=set_dc)
        menu.add_command(label=f"🔨 Imposta CD Sfondare con Forza (Attuale: {door.get('break_dc', door.get('dc', 15) + 2)})...", command=set_break_dc)
        menu.add_command(label=f"🗝️ Assegna Nome Chiave (Attuale: '{door.get('key_name', '') or 'Nessuna'}')...", command=set_key_name)
        menu.add_command(label=f"🏷️ Rinomina (Attuale: {door.get('name', 'Porta')})...", command=rename_door)
        menu.add_separator()
        menu.add_command(label="🗑️ Rimuovi Porta", command=delete_door)

        try:
            x = self.master.winfo_pointerx()
            y = self.master.winfo_pointery()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def open_room_pin_dialog(self, pin, clicked_hex):
        return dm_open_room_pin_dialog(self, pin, clicked_hex)

    def _show_time_fast_menu(self, event=None):
        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(label="⏱️ Avanzamento Rapido Tempo (Orologio Campagna)", state="disabled")
        menu.add_separator()
        
        def adv(seconds=0, minutes=0, hours=0, label=""):
            if hours > 0:
                self.advance_time(hours, is_rest=(hours >= 8))
            else:
                self.server.game_state.advance_game_time(seconds=seconds, minutes=minutes)
                from common.protocol import make_game_state
                from server.network import broadcast
                broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
                self.server.game_state._trigger_gui_update()
                self.log_to_chat(f"⏱️ Il tempo avanza di {label}.")

        menu.add_command(label="+6 Secondi (1 Round)", command=lambda: adv(seconds=6, label="6 secondi (1 round)"))
        menu.add_command(label="+1 Minuto (10 Round)", command=lambda: adv(minutes=1, label="1 minuto"))
        menu.add_command(label="+10 Minuti (Esplorazione Stanza)", command=lambda: adv(minutes=10, label="10 minuti"))
        menu.add_command(label="+1 Ora (Riposo Breve)", command=lambda: adv(hours=1, label="1 ora"))
        menu.add_command(label="+8 Ore (Riposo Lungo)", command=lambda: adv(hours=8, label="8 ore (Riposo Lungo)"))
        menu.add_separator()
        menu.add_command(label="📅 Apri Calendario di Harptos...", command=self.open_calendar_dialog)

        try:
            x = self.master.winfo_pointerx()
            y = self.master.winfo_pointery()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def on_hex_clicked(self, clicked_hex):
        if not self.server.game_state.current_map: return

        if getattr(self, "terrain_paint_mode", False):
            brush = getattr(self, "active_terrain_brush", "fango")
            if brush == "clear":
                self.remove_difficult_terrain_at(clicked_hex)
            else:
                self.set_difficult_terrain_at(clicked_hex, brush)
            return
        
        if getattr(self, "door_mode_var", None) and self.door_mode_var.get():
            doors = self.server.game_state.current_map.setdefault("doors", [])
            target_door = next((d for d in doors if d.get("q") == clicked_hex.q and d.get("r") == clicked_hex.r), None)
            if target_door:
                self._show_door_management_menu(target_door, clicked_hex)
            else:
                doors.append({"q": clicked_hex.q, "r": clicked_hex.r, "state": "closed", "name": "Porta in Legno", "dc": 15, "break_dc": 17, "key_name": ""})
                from common.protocol import make_map_data_update_broadcast, make_chat_broadcast
                from server.network import broadcast
                broadcast(self.server.game_state, make_map_data_update_broadcast(self.server.game_state.current_map))
                broadcast(self.server.game_state, make_chat_broadcast("Sistema", f"🚪 Il DM ha posizionato una Porta Chiusa a ({clicked_hex.q}, {clicked_hex.r})."))
                self.server.game_state._trigger_gui_update()
                self.redraw_map_and_players()
                self.show_toast(f"Porta posizionata a [{clicked_hex.q}, {clicked_hex.r}]", title="🚪 Nuova Porta", toast_type="success")
            return

        if getattr(self, "room_pin_mode_var", None) and self.room_pin_mode_var.get():
            pins = self.server.game_state.current_map.setdefault("room_pins", [])
            target_pin = next((p for p in pins if p.get("q") == clicked_hex.q and p.get("r") == clicked_hex.r), None)
            self.open_room_pin_dialog(target_pin, clicked_hex)
            return

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

        # Se non si sta dipingendo la nebbia, un click su una spilla esistente apre le sue note
        pins = self.server.game_state.current_map.get("room_pins", [])
        pin_under_click = next((p for p in pins if p.get("q") == clicked_hex.q and p.get("r") == clicked_hex.r), None)
        if pin_under_click and mode == "move":
            self.open_room_pin_dialog(pin_under_click, clicked_hex)
            return
        
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
        time_minute = getattr(self.server.game_state, "time_minute", 0)
        weather = getattr(self.server.game_state, "weather", "Sereno")
        combat_active = getattr(self.server.game_state, "combat_active", False)
        combat_order = [p.name for p in self.server.game_state.players] if combat_active else []
        round_number = getattr(self.server.game_state, "round_number", 1)
        
        auto_day_night = True
        if hasattr(self.server.game_state, "automation_settings") and isinstance(self.server.game_state.automation_settings, dict):
            auto_day_night = self.server.game_state.automation_settings.get("auto_day_night_cycle", True)

        self._update_map_scale_pill()
        self._update_map_env_pill()
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
            round_number=round_number,
            time_minute=time_minute,
            auto_day_night=auto_day_night
        )

    def _update_map_env_pill(self):
        if not hasattr(self, "top_status_env_lbl"):
            return
        cur_map = getattr(self.server.game_state, "current_map", None) if hasattr(self, "server") and hasattr(self.server, "game_state") else None
        is_outdoor = cur_map.get("outdoor", True) if isinstance(cur_map, dict) else True
        if is_outdoor:
            self.top_status_env_lbl.config(
                text=_t("map_env_outdoor"),
                fg=ACCENT_GREEN
            )
        else:
            self.top_status_env_lbl.config(
                text=_t("map_env_indoor"),
                fg="#818CF8"
            )

    def toggle_map_outdoor(self):
        cur_map = getattr(self.server.game_state, "current_map", None) if hasattr(self, "server") and hasattr(self.server, "game_state") else None
        if not cur_map or not isinstance(cur_map, dict):
            return
        cur_val = cur_map.get("outdoor", True)
        cur_map["outdoor"] = not cur_val
        new_val = cur_map["outdoor"]
        
        env_label = _t("map_env_outdoor") if new_val else _t("map_env_indoor")
        msg = _t("map_env_switched", env=env_label)
        self.log_to_chat(msg, sender="Sistema", color="#10B981" if new_val else "#818CF8")
        
        from common.protocol import make_map_data_update_broadcast, make_chat_broadcast
        from server.network import broadcast
        broadcast(self.server.game_state, make_map_data_update_broadcast(cur_map))
        broadcast(self.server.game_state, make_chat_broadcast("Sistema", msg))
        
        self._update_map_env_pill()
        self.update_canvas()

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
                "Inserisci la distanza per 1 esagono (es. '10 ft', '3 m', '24 mi', '36 km'):",
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
            QuestLogDialog(self.master, self.server.game_state, is_dm=True, network_or_server=self.server)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire il diario: {e}")

    def open_shop_dialog(self):
        try:
            from components.shop_ui import ShopDialog
            ShopDialog(self.master, self.server.game_state, is_dm=True, network_or_server=self.server)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire i negozi: {e}")

    def open_travel_panel(self):
        return dm_open_travel_panel(self)

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
        CampaignEditorDialog(self.master, campaign=new_camp, game_state=self.server.game_state, on_save_callback=on_saved)

    def open_load_campaign_dialog(self):
        from server.campaign_editor_ui import CampaignSelectorDialog
        def on_selected(camp):
            camp.apply_to_game_state(self.server.game_state)
            if hasattr(self, "session_ledger") and self.session_ledger:
                self.session_ledger.campaign_name = camp.name
                if getattr(camp, "start_date", None):
                    self.session_ledger.start_game_date = dict(camp.start_date)
                    self.session_ledger.current_game_date = dict(camp.start_date)
                if getattr(camp, "start_weather", None):
                    self.session_ledger.current_weather = camp.start_weather
            if self.server.game_state.current_map:
                self.fow_enabled_var.set(self.server.game_state.current_map.get("fow_enabled", False))
                self.redraw_map_and_players()
            self.log_to_chat(f"[SISTEMA] Campagna '{camp.name}' caricata e attiva.")
            messagebox.showinfo("Campagna Caricata", f"Campagna '{camp.name}' caricata con successo!", parent=self.master)
        CampaignSelectorDialog(self.master, on_select_callback=on_selected)

    def open_campaign_editor_dialog(self):
        from server.campaign_editor_ui import CampaignEditorDialog
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        if active_camp:
            def on_saved(camp):
                camp.apply_to_game_state(self.server.game_state)
                self.log_to_chat(f"[SISTEMA] Campagna '{camp.name}' aggiornata.")
            CampaignEditorDialog(self.master, campaign=active_camp, game_state=self.server.game_state, on_save_callback=on_saved)
        else:
            choice = messagebox.askyesno(
                _t("campaign_none_title", default="Nessuna Campagna Attiva"),
                _t("campaign_none_prompt", default="Non c'è una campagna attualmente caricata.\n\nVuoi caricare una campagna esistente?\n(Scegli 'No' per creare una Nuova Campagna)"),
                parent=self.master
            )
            if choice:
                self.open_load_campaign_dialog()
            else:
                self.open_new_campaign_dialog()

    def close_active_campaign(self):
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        if not active_camp:
            messagebox.showinfo(_t("campaign_none_title", default="Nessuna Campagna"), _t("msg_no_active_campaign", default="Nessuna campagna attiva da chiudere."), parent=self.master)
            return
        camp_name = active_camp.name
        self.server.game_state.active_campaign = None
        if hasattr(self, 'lbl_campaign_name'):
            self.lbl_campaign_name.config(text=_t("campaign_none"))
        self.log_to_chat(f"[SISTEMA] Campagna '{camp_name}' chiusa. Modalità sessione libera attiva.")
        self.show_toast(f"Campagna '{camp_name}' chiusa.", title="Campagna", toast_type="info")

    def open_live_flow_controller(self):
        from server.dm_live_flow import DMLiveFlowDialog
        DMLiveFlowDialog(self, self.server.game_state, self.session_ledger)

    def open_session_chronicle_dialog(self):
        from server.dm_live_flow import SessionChronicleDialog
        active_camp = getattr(self.server.game_state, 'active_campaign', None)
        SessionChronicleDialog(self, self.session_ledger, campaign=active_camp)

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
            weather_icons = {"Sereno": "🌤️", "Pioggia": "🌧️", "Tempesta": "⛈️", "Neve": "❄️", "Nebbia": "🌫️", "Oscurità": "🌑",
                             "Clear": "🌤️", "Rain": "🌧️", "Storm": "⛈️", "Snow": "❄️", "Fog": "🌫️", "Darkness": "🌑"}
            w_icon = weather_icons.get(gs.weather, "🌤️")
            self.top_status_weather_lbl.config(text=f"{w_icon} {translate_weather(gs.weather)}")
        if hasattr(self, "btn_darkness"):
            is_dark = str(getattr(gs, "weather", "")).lower() in ("oscurita", "oscurità", "darkness", "buio")
            self.btn_darkness.config(style="Primary.TButton" if is_dark else "Tool.TButton")
            
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

        if hasattr(self, "top_status_automation_lbl") and hasattr(self.server, "game_state"):
            mode = getattr(self.server.game_state, "automation_mode", "full")
            mode_data = {
                "manual": ("🎲 Tavolo", ACCENT_GOLD),
                "hybrid": ("⚖️ Ibrido", ACCENT_BLUE),
                "full": ("⚡ Full Auto", ACCENT_GREEN),
                "tactical": ("⚡ Full Auto", ACCENT_GREEN)
            }
            txt, color = mode_data.get(mode, ("⚖️ Ibrido", ACCENT_BLUE))
            self.top_status_automation_lbl.config(text=txt, fg=color)

        if hasattr(self, "update_pending_actions_ui"):
            self.update_pending_actions_ui()

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
                elif msg_type in ("PENDING_DAMAGE_PROMPT", "PENDING_DOOR_PROMPT"):
                    self.update_pending_actions_ui()
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

    def open_automation_settings_dialog(self):
        return dm_open_automation_settings_dialog(self)

    def update_pending_actions_ui(self):
        return dm_update_pending_actions_ui(self)

    def apply_pending_damage_gui(self, pending_id, action):
        return dm_apply_pending_damage_gui(self, pending_id, action)

    def apply_pending_damage_custom_gui(self, pending_id, default_amount):
        return dm_apply_pending_damage_custom_gui(self, pending_id, default_amount)

    def resolve_pending_door_gui(self, pending_id, outcome):
        return dm_resolve_pending_door_gui(self, pending_id, outcome)

    def open_assign_item_dialog(self, prefill_item=None):
        return dm_open_assign_item_dialog(self, prefill_item=prefill_item)

    def open_modify_hp_dialog(self):
        return dm_open_modify_hp_dialog(self)

    def open_conditions_dialog(self):
        return dm_open_conditions_dialog(self)

    def open_aura_dialog(self):
        return dm_open_aura_dialog(self)

    def get_selected_player_name(self):
        sel = self.player_listbox.curselection()
        if not sel: return None
        display_text = self.player_listbox.get(sel[0])
        if display_text.startswith('---'): return None
        name = display_text.split(" (HP")[0].replace("▶", "").replace("[N]", "").strip()
        return name

    def open_light_source_dialog(self):
        return dm_open_light_source_dialog(self)

    def open_boss_config_dialog(self):
        return dm_open_boss_config_dialog(self)

    def open_spend_legendary_action_dialog(self):
        return dm_open_spend_legendary_action_dialog(self)

    def open_place_trap_dialog(self, clicked_hex):
        return dm_open_place_trap_dialog(self, clicked_hex)

    def remove_trap_at(self, clicked_hex):
        return dm_remove_trap_at(self, clicked_hex)

    def reset_trap_at(self, clicked_hex):
        return dm_reset_trap_at(self, clicked_hex)


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
        
        player_name = display_text.split(" (HP")[0].replace("▶", "").replace("➡️", "").strip()
        if player_name.startswith("[N] "):
            player_name = player_name[4:]
            
        player = self.server.game_state.find_player(player_name)
        if not player or not getattr(player, "full_sheet", None): return
        
        actions = player.full_sheet.get("actions", [])
        if not actions:
            srd_rec = get_monster_offline(player_name)
            if srd_rec and srd_rec.get("actions"):
                actions = srd_rec.get("actions", [])
                player.full_sheet["actions"] = actions
                if "features" not in player.full_sheet and srd_rec.get("special_abilities"):
                    player.full_sheet["features"] = srd_rec.get("special_abilities")
        
        if not actions:
            ttk.Label(self.npc_actions_frame, text="Nessuna azione SRD registrata", font=FONT_SMALL).pack(pady=2)
            return
            
        for act in actions:
            act_name = act.get("name", "Azione") if isinstance(act, dict) else str(act).split(".")[0].strip()
            btn = ttk.Button(self.npc_actions_frame, text=act_name, 
                             command=lambda a=act, n=player_name: self.roll_npc_action(n, a))
            btn.pack(fill=tk.X, pady=1)
            # Tooltip al passaggio del mouse con le caratteristiche complete dell'azione (TpC, Danni, Gittata, TS, ecc.)
            tip_text = format_monster_action_tooltip(act, player_name)
            ToolTip(btn, tip_text)
            
    def roll_npc_action(self, npc_name, action_dict):
        from common.dice import roll_dice
        import re
        if isinstance(action_dict, str):
            act_name = action_dict.split(".")[0].strip()
            desc = action_dict
            atk_bonus = None
            dmg_dice = None
        else:
            act_name = action_dict.get("name", "Azione")
            desc = action_dict.get("desc", "")
            atk_bonus = action_dict.get("attack_bonus")
            dmg_dice = action_dict.get("damage_dice")

        msg = f"{npc_name} usa {act_name}!"
        
        if atk_bonus is None:
            m_atk = re.search(r'([+-]\d+)\s+to\s+hit', desc, re.I)
            if m_atk:
                try:
                    atk_bonus = int(m_atk.group(1))
                except (ValueError, TypeError):
                    pass

        if atk_bonus is not None:
            mod_str = f"+{atk_bonus}" if int(atk_bonus) >= 0 else str(atk_bonus)
            try:
                res = roll_dice(f"1d20{mod_str}")
                msg += f"\nTiro per Colpire: {res['total']} (Dado: {res['rolls'][0]})"
            except Exception:
                pass
            
        if not dmg_dice:
            m_dmg = re.search(r'\(([0-9]+d[0-9]+(?:\s*[+-]\s*[0-9]+)?)\)', desc)
            if m_dmg:
                dmg_dice = m_dmg.group(1).replace(" ", "")

        if dmg_dice:
            try:
                res = roll_dice(dmg_dice)
                msg += f"\nDanni: {res['total']} (Dadi: {res['rolls']})"
            except Exception:
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
        if hasattr(self, 'btn_ruler') and self.btn_ruler:
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
            except (ValueError, TypeError): sz = 3
            self.aoe_mode = True
            dc = 10
            if req_save_var.get():
                try: dc = int(dc_entry.get())
                except (ValueError, TypeError): dc = 10

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
    root = tk.Tk()
    DM_GUI(root)
    root.mainloop()
