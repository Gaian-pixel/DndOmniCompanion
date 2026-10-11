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
from common.theme import setup_theme, apply_modern_window_style, BG_COLOR, SURFACE_COLOR, TEXT_COLOR, TEXT_MUTED, FONT_MAIN, FONT_TITLE, FONT_BOLD, ACCENT_RED
from server.commands import command_handlers
from common.game_state import GameState, Player
from server.map_editor import MapEditorWindow
from server.map_downloader import MapDownloaderDialog
from .network import Server
from common.hex_utils import Hex
from common.network_utils import send_message, receive_message, broadcast
from components.ui_components import HexMapCanvas, ToolTip
from client.voice_client import VoiceClient

class DM_GUI:
    def __init__(self, master):
        self.master = master; self.master.title("Dungeon Master - Server")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.gui_queue=queue.Queue()
        self.server=Server('', 5000, self.gui_queue)
        self.map_canvas = None # Il nostro nuovo componente
        self.notebook = None
        self.chat_tabs = {}
        self.default_font = ("Georgia", 10)
        setup_theme(self.master)
        self.setup_gui()
        self.server_thread=threading.Thread(target=self.server.start, daemon=True); self.server_thread.start()
        self.voice_client = VoiceClient("127.0.0.1", 53912)
        self.voice_client.start()
        self.master.after(100, self.process_queue)

    def setup_gui(self):
        # 1. MENU BAR GLOBALE
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Carica Mappa...", command=self.load_map_from_file)
        file_menu.add_separator()
        file_menu.add_command(label="Salva Sessione...", command=self.save_session)
        file_menu.add_command(label="Carica Sessione...", command=self.load_session)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Editor Mappe", command=self.open_map_editor)
        tools_menu.add_command(label="Condividi Immagine (Handout)", command=self.share_image_handout)
        tools_menu.add_command(label="Condividi Documento testuale", command=self.share_text_handout)
        tools_menu.add_command(label="Scarica Mappe Famose", command=self.open_map_downloader)
        tools_menu.add_command(label="Compendio & SRD", command=self.open_srd_importer)
        tools_menu.add_command(label="Preparazione Combattimenti", command=self.open_encounter_builder)
        tools_menu.add_separator()
        tools_menu.add_command(label="Pannello Viaggio", command=self.open_travel_panel)
        tools_menu.add_command(label="Starter Pack Campagna", command=self.open_campaign_starter_kit_dialog)
        menubar.add_cascade(label="Strumenti", menu=tools_menu)
        
        # 2. LAYOUT PRINCIPALE (3 Colonne: Sinistra=Toolbar, Centro=Mappa, Destra=Notebook)
        main_frame = ttk.Frame(self.master, padding="15 15 15 15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=0, minsize=350)
        main_frame.rowconfigure(0, weight=1)
        
        # --- COLONNA 0: LEFT TOOLBAR (Strumenti Mappa) ---
        left_toolbar = ttk.Frame(main_frame)
        left_toolbar.grid(row=0, column=0, sticky="ns", padx=(0, 5))
        
        btn1 = ttk.Button(left_toolbar, text="👆", width=3, command=lambda: self.map_canvas.center_view() if self.map_canvas else None)
        btn1.pack(pady=5)
        ToolTip(btn1, "Centra Mappa")
        btn2 = ttk.Button(left_toolbar, text="☁️", width=3, command=lambda: print("Nebbia: Placeholder"))
        btn2.pack(pady=5)
        ToolTip(btn2, "Nebbia")
        btn3 = ttk.Button(left_toolbar, text="📏", width=3, command=lambda: print("Misura: Placeholder"))
        btn3.pack(pady=5)
        ToolTip(btn3, "Misura Distanza")
        btn4 = ttk.Button(left_toolbar, text="🧹", width=3, command=self.clear_aoes)
        btn4.pack(pady=5)
        ToolTip(btn4, "Pulisci Aree di Effetto")
        
        self.teleport_mode_var = tk.BooleanVar(value=False)
        btn_teleport = ttk.Checkbutton(left_toolbar, text="🚪", width=3, style="Toolbutton", variable=self.teleport_mode_var)
        btn_teleport.pack(pady=5)
        ToolTip(btn_teleport, "Aggiungi/Rimuovi Teletrasporto")

        
        # --- COLONNA 1: MAPPA (Viewport pulita) ---
        map_outer_frame = ttk.Frame(main_frame)
        map_outer_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        
        # Toolbar mappa fluttuante (minimalista)
        map_top_bar = ttk.Frame(map_outer_frame)
        map_top_bar.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(map_top_bar, text="Mappa di Gioco", font=self.default_font, foreground="#E0E0E0").pack(side=tk.LEFT)
        
        fow_toolbar = ttk.Frame(map_top_bar)
        fow_toolbar.pack(side=tk.RIGHT, padx=5)
        
        self.fow_enabled_var = tk.BooleanVar(value=False)
        self.fow_mode_var = tk.StringVar(value="Muovi Token")
        
        ttk.Label(fow_toolbar, text="Strumento Mappa:", font=self.default_font).pack(side=tk.LEFT, padx=(0, 5))
        
        # Tool combobox
        self.map_tool_combo = ttk.Combobox(fow_toolbar, textvariable=self.fow_mode_var, state="readonly", width=18)
        self.map_tool_combo['values'] = ("Muovi Token", "Cancella Nebbia", "Disegna Nebbia")
        self.map_tool_combo.pack(side=tk.LEFT, padx=5)
        
        # Vista Giocatori
        self.dm_player_view_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(fow_toolbar, text="Vista Giocatori", variable=self.dm_player_view_var, command=self.redraw_map_and_players).pack(side=tk.LEFT, padx=5)

        # Bottone per il Push manuale della nebbia
        ttk.Button(fow_toolbar, text="Invia Nebbia", command=self._broadcast_fow_update, style="Success.TButton").pack(side=tk.LEFT, padx=5)
        
        # Fog options MenuButton
        self.fow_options_btn = ttk.Menubutton(fow_toolbar, text="Opzioni Nebbia di Guerra")
        self.fow_options_menu = tk.Menu(self.fow_options_btn, tearoff=0)
        self.fow_options_btn["menu"] = self.fow_options_menu
        
        self.fow_options_menu.add_checkbutton(label="Abilita Sistema Nebbia", variable=self.fow_enabled_var, command=self.toggle_fow)
        self.fow_options_menu.add_separator()
        self.fow_options_menu.add_command(label="Oscura Tutta la Mappa (Nascondi Tutto)", command=self.hide_all_fow)
        self.fow_options_menu.add_command(label="Rivela Tutta la Mappa (Rivela Tutto)", command=self.reveal_all_fow)
        self.fow_options_btn.pack(side=tk.LEFT, padx=5)
        self.map_canvas = HexMapCanvas(map_outer_frame, bg="#1e1e1e")
        self.map_canvas.pack(fill=tk.BOTH, expand=True)
        self.map_canvas.set_on_click_callback(self.on_hex_clicked)
        self.map_canvas.on_token_drop_callback = self.on_token_drop
        self.map_canvas.set_on_ping_callback(self.on_ping_callback)
        self.map_canvas.set_on_hex_right_click_callback(self.on_hex_right_clicked)
        
        # --- COLONNA 2: RIGHT SIDEBAR (Notebook a Tabs) ---
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        
        self.right_notebook = ttk.Notebook(right_panel)
        self.right_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1 ("Chat & Log")
        tab_chat = ttk.Frame(self.right_notebook)
        self.right_notebook.add(tab_chat, text="Chat & Log")
        
        self.notebook = ttk.Notebook(tab_chat)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=0)
        self.create_chat_tab("Sistema")
        
        # Tab Bestiario
        self.tab_bestiario = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_bestiario, text="Bestiario")
        
        ttk.Label(self.tab_bestiario, text="Ricerca Mostro:", font=self.default_font).pack(pady=(5,0))
        self.bestiario_search_var = tk.StringVar()
        ttk.Entry(self.tab_bestiario, textvariable=self.bestiario_search_var).pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(self.tab_bestiario, text="Cerca in SRD", command=self.search_bestiario).pack(pady=5)
        
        self.bestiario_listbox = tk.Listbox(self.tab_bestiario, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=self.default_font)
        self.bestiario_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.bestiario_results = []
        
        ttk.Button(self.tab_bestiario, text="Spawna sulla Mappa", command=self.spawn_bestiario).pack(pady=5)

        
        chat_input_frame = ttk.Frame(tab_chat)
        chat_input_frame.pack(fill=tk.X, pady=(5, 0))
        self.chat_entry = ttk.Entry(chat_input_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_entry.bind("<Return>", lambda e: self.send_dm_chat())
        ttk.Button(chat_input_frame, text="Invia", command=self.send_dm_chat).pack(side=tk.LEFT)

        self.voice_controls_frame = tk.Frame(tab_chat, bg="#292B2F", pady=5, padx=5)
        self.voice_controls_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(self.voice_controls_frame, text="Voice Channel: Disconnesso", bg="#292B2F", fg="#8E9297", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        self.btn_deafen = tk.Button(self.voice_controls_frame, text=" 🎧 ", bg="#36393F", fg="white", relief=tk.FLAT, command=self.toggle_deafen)
        self.btn_deafen.pack(side=tk.RIGHT, padx=2)
        self.btn_mute = tk.Button(self.voice_controls_frame, text=" 🎤 ", bg="#36393F", fg="white", relief=tk.FLAT, command=self.toggle_mute)
        self.btn_mute.pack(side=tk.RIGHT, padx=2)
        
        btn_frame = ttk.Frame(tab_chat)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Tira Dadi", command=self.roll_dice_dialog, style="Primary.TButton").pack(side=tk.LEFT)
        
        # Tab 2 ("Iniziativa & PG")
        tab_combat = ttk.Frame(self.right_notebook)
        self.right_notebook.add(tab_combat, text="Iniziativa & PG")
        
        ttk.Label(tab_combat, text="Avventurieri & NPC", font=self.default_font, foreground="#E0E0E0").pack(anchor="w", pady=(0, 5))
        list_frame = ttk.Frame(tab_combat)
        list_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=(0, 5))

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.player_listbox = tk.Listbox(list_frame, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=self.default_font, selectbackground=ACCENT_RED, borderwidth=0, relief="flat", highlightthickness=0, yscrollcommand=scrollbar.set)
        self.player_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.player_listbox.yview)
        self.player_listbox.bind("<Double-Button-1>", self.open_private_chat_from_list)
        self.player_listbox.bind("<Button-3>", self.show_player_context_menu)
        self.player_listbox.bind("<<ListboxSelect>>", self.on_player_selected)

        self.btn_hide_reveal = ttk.Button(tab_combat, text="Nascondi/Rivela PNG", command=self.toggle_hide_reveal)
        self.btn_hide_reveal.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))

        self.npc_actions_frame = ttk.LabelFrame(tab_combat, text="Azioni PNG Selezionato")
        self.npc_actions_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
        
        self.btn_combat = ttk.Button(tab_combat, text="🗡 Inizia Combattimento", command=self.toggle_combat, style='Primary.TButton')
        self.btn_combat.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
        
        self.combat_controls_frame = ttk.Frame(tab_combat)
        
        self.lbl_round = ttk.Label(self.combat_controls_frame, text="Round: -", font=self.default_font)
        self.lbl_round.pack(fill=tk.X, pady=(0, 5))
        
        turn_nav_frame = ttk.Frame(self.combat_controls_frame)
        turn_nav_frame.pack(fill=tk.X, pady=(0, 5))
        self.btn_prev_turn = ttk.Button(turn_nav_frame, text="⬅ Precedente", command=self.prev_turn_gui, state=tk.DISABLED)
        self.btn_prev_turn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        self.btn_next_turn = ttk.Button(turn_nav_frame, text="Prossimo ➡", command=self.next_turn_gui, state=tk.DISABLED)
        self.btn_next_turn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        ttk.Button(tab_combat, text="+ Aggiungi NPC/Mostro", command=self.add_npc).pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        btn_frame_bottom = ttk.Frame(tab_combat)
        btn_frame_bottom.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        ttk.Button(btn_frame_bottom, text="Spawna PNG", command=self.spawn_png_dialog, style="Primary.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(btn_frame_bottom, text="Encounter Builder", command=self.open_encounter_builder, style="Primary.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        ttk.Button(tab_combat, text="Dividi Denaro", command=self.split_loot_dialog, style="Primary.TButton").pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))

        
        # Tab 3 ("Mondo")
        tab_world = ttk.Frame(self.right_notebook)
        self.right_notebook.add(tab_world, text="Mondo")
        
        ttk.Label(tab_world, text="Gestione Tempo", font=("Arial", 12, "bold")).pack(anchor="w", pady=(5, 5))
        self.lbl_time = ttk.Label(tab_world, text="Giorno 1 - 08:00 (Mattina)")
        self.lbl_time.pack(anchor="w", pady=(0, 10))
        
        time_btn_frame = ttk.Frame(tab_world)
        time_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(time_btn_frame, text="+1 Ora", command=lambda: self.advance_time(1)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(time_btn_frame, text="+8 Ore (Riposo)", command=lambda: self.advance_time(8)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 2))
        ttk.Button(time_btn_frame, text="+1 Giorno", command=lambda: self.advance_time(24)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        ttk.Button(tab_world, text="📅 Apri Calendario Campagna", command=self.open_calendar_dialog, style='Info.TButton').pack(fill=tk.X, pady=10)
        
        ttk.Button(tab_world, text="📜 Diario e Missioni", command=self.open_quest_dialog, style='Info.TButton').pack(fill=tk.X, pady=5)
        
        ttk.Button(tab_world, text="🛒 Negozi", command=self.open_shop_dialog, style='Info.TButton').pack(fill=tk.X, pady=5)
        
        ttk.Label(tab_world, text="Clima", font=("Arial", 12, "bold")).pack(anchor="w", pady=(15, 5))
        self.weather_var = tk.StringVar(value="Sereno")
        weather_combo = ttk.Combobox(tab_world, textvariable=self.weather_var, values=["Sereno", "Pioggia", "Tempesta", "Neve", "Nebbia"], state="readonly")
        weather_combo.pack(fill=tk.X)
        weather_combo.bind("<<ComboboxSelected>>", self.on_weather_changed)
        
        # Tab 4 ("Audio/Sfx")
        tab_audio = ttk.Frame(self.right_notebook)
        self.right_notebook.add(tab_audio, text="Audio/Sfx")
        ttk.Label(tab_audio, text="Soundboard", font=("Arial", 12, "bold")).pack(anchor="w", pady=(5, 5))
        ttk.Button(tab_audio, text="Musica Taverna", command=lambda: self.play_audio("https://www.youtube.com/watch?v=sW-KikD1b4k")).pack(fill=tk.X, pady=5)
        ttk.Button(tab_audio, text="Musica Battaglia", command=lambda: self.play_audio("https://www.youtube.com/watch?v=1F_CgepehcE")).pack(fill=tk.X, pady=5)
        ttk.Button(tab_audio, text="Effetto Esplosione", command=lambda: self.play_audio("https://www.youtube.com/watch?v=W0nL94EaH7I")).pack(fill=tk.X, pady=5)

        self.player_menu = tk.Menu(self.master, tearoff=0, bg="#3E2723", fg="#F5F5DC", font=self.default_font)
        self.player_menu.add_command(label="Visualizza Scheda", command=self.view_player_sheet)
        self.player_menu.add_command(label="Assegna Oggetto", command=self.open_assign_item_dialog)
        self.player_menu.add_command(label="Modifica HP", command=self.open_modify_hp_dialog)
        self.player_menu.add_command(label="Modifica Stati/Condizioni", command=self.open_conditions_dialog)
        self.player_menu.add_command(label="Esegui Azione (Danno/Cura)", command=self.open_action_dialog)
        self.player_menu.add_command(label="Imposta Aura", command=self.open_aura_dialog)
        self.player_menu.add_command(label="Imposta Proprietario", command=self.open_set_owner_dialog)
        self.player_menu.add_command(label="Apri Chat Privata", command=self.open_private_chat_from_context)
        self.player_menu.add_separator()
        self.player_menu.add_command(label="Aggiungi/Rimuovi da Combattimento", command=self.toggle_player_combat_status)
        self.player_menu.add_command(label="Aggiungi/Rimuovi dal Party", command=self.toggle_party_status)
        self.player_menu.add_separator()
        self.player_menu.add_command(label="Rimuovi", command=self.remove_entity)

    def play_audio(self, url):
        from common.protocol import make_audio_play_broadcast
        broadcast(self.server.game_state, make_audio_play_broadcast(url))
        self.log_to_chat(f"Audio avviato: {url}")

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
            if messagebox.askyesno("Fine Combattimento", "Vuoi terminare il combattimento?"):
                self.server.game_state.end_combat()
                self.server.game_state.add_calendar_event(f"Combattimento Terminato al Round {self.server.game_state.combat_round}")
                self.log_to_chat("[SISTEMA] Fine Combattimento.")
                from common.protocol import make_chat_broadcast, make_game_state
                broadcast(self.server.game_state, make_chat_broadcast("Sistema", "Fine Combattimento."))
                broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))

    def open_combat_config(self, initiator_name=None):
        if self.server.game_state.combat_active:
            messagebox.showinfo("Combattimento", "Un combattimento è già in corso.")
            return

        all_players = self.server.game_state.get_all_players()
        if not all_players:
            messagebox.showinfo("Combattimento", "Nessun personaggio/NPC per iniziare il combattimento.")
            return

        dialog = tk.Toplevel(self.master)
        dialog.title("Configurazione Combattimento")
        dialog.minsize(400, 550)
        dialog.transient(self.master)
        dialog.grab_set()

        from common.theme import apply_modern_window_style
        apply_modern_window_style(dialog)

        if initiator_name:
            ttk.Label(dialog, text=f"{initiator_name} ha richiesto l'inizio del combattimento!", font=self.default_font, foreground="#D4AF37").pack(pady=(10, 5))

        # Filtro per distanza
        filter_frame = ttk.LabelFrame(dialog, text="Filtro per Distanza (Auto-selezione)")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text="Origine:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        origin_var = tk.StringVar(value=initiator_name if initiator_name else all_players[0].name)
        origin_combo = ttk.Combobox(filter_frame, textvariable=origin_var, values=[p.name for p in all_players], state="readonly")
        origin_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Label(filter_frame, text="Raggio (esagoni):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
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

        ttk.Button(filter_frame, text="Seleziona Vicini", command=apply_filter).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(dialog, text="Partecipanti:", font=self.default_font).pack(pady=(10,0))

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
                messagebox.showwarning("Attenzione", "Seleziona almeno un partecipante.")
                return
            
            import random
            npcs_in_combat = [p for p in self.server.game_state.get_all_players() if p.name in selected_names and p.conn is None]
            
            if not npcs_in_combat:
                finalize_combat(selected_names, {})
                return
                
            # Mostra dialog per l'iniziativa degli NPC
            init_dialog = tk.Toplevel(dialog)
            init_dialog.title("Iniziativa NPC")
            init_dialog.minsize(300, 400)
            init_dialog.transient(dialog)
            init_dialog.grab_set()
            apply_modern_window_style(init_dialog)
            
            ttk.Label(init_dialog, text="Inserisci l'iniziativa per gli NPC:", font=self.default_font).pack(pady=10)
            
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
                
            ttk.Button(init_dialog, text="Conferma Iniziative", command=submit_init, style="Primary.TButton").pack(pady=10)

        ttk.Button(dialog, text="Avanti", command=confirm, style='Primary.TButton').pack(pady=15)

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
                log_msg = f"DM tira {formula} {'(' + reason + ')' if reason else ''}: {result['rolls']} + {result['modifier']} = {result['total']}"
                self.log_to_chat(f"[ROLL] {log_msg}")
                broadcast(self.server.game_state, make_dice_roll_result("DM", formula, reason, result))
            except Exception as e:
                messagebox.showerror("Errore Dadi", str(e))

    def toggle_fow(self):
        if not self.server.game_state.current_map: return
        self.server.game_state.current_map["fow_enabled"] = self.fow_enabled_var.get()
        self.redraw_map_and_players()
        self._broadcast_fow_update()
        
    def reveal_all_fow(self):
        if not self.server.game_state.current_map: return
        self.server.game_state.current_map["fow_draft"] = self.server.game_state.current_map.get("hexes", [])[:]
        self.redraw_map_and_players()

    def hide_all_fow(self):
        if not self.server.game_state.current_map: return
        self.server.game_state.current_map["fow_draft"] = []
        self.redraw_map_and_players()

    def advance_time(self, hours):
        gs = self.server.game_state
        gs.time_hour += hours
        while gs.time_hour >= 24:
            gs.time_hour -= 24
            gs.time_day += 1
            while gs.time_day > 30:
                gs.time_day -= 30
                gs.time_month += 1
                while gs.time_month > 12:
                    gs.time_month -= 12
                    gs.time_year += 1
            
        if hours >= 8:
            gs.travel_hours_today = 0
            self.log_to_chat(f"Il party ha completato un Riposo Lungo! (Giorno {gs.time_day})")
            gs.add_calendar_event("Il party ha completato un Riposo Lungo")
            for p in gs.players:
                p.hp = p.max_hp
                if p.full_sheet:
                    # In a real scenario, this would reset spell slots, hit dice, etc.
                    pass
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
        if self.server.game_state.current_map and "fow_draft" in self.server.game_state.current_map:
            self.server.game_state.current_map["fow_revealed"] = self.server.game_state.current_map["fow_draft"].copy()
            from common.protocol import make_fow_update_broadcast
            fow_rev = self.server.game_state.current_map["fow_revealed"]
            fow_draft = self.server.game_state.current_map["fow_draft"]
            broadcast(self.server.game_state, make_fow_update_broadcast(fow_rev, fow_draft))
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
        if mode_str == "Cancella Nebbia": mode = "reveal"
        elif mode_str == "Disegna Nebbia": mode = "hide"
        
        map_hexes = {Hex(q, r) for q, r in self.server.game_state.current_map.get("hexes", [])}
        if clicked_hex not in map_hexes: return
        
        if mode in ("reveal", "hide"):
            drafted = {Hex(h[0], h[1]) for h in self.server.game_state.current_map.get("fow_draft", self.server.game_state.current_map.get("fow_revealed", []))}
            changed = False
            
            if mode == "reveal" and clicked_hex not in drafted:
                drafted.add(clicked_hex)
                changed = True
            elif mode == "hide" and clicked_hex in drafted:
                drafted.remove(clicked_hex)
                changed = True
                
            if changed:
                self.server.game_state.current_map["fow_draft"] = [[h.q, h.r] for h in drafted]
                self.redraw_map_and_players()
                # Broadcast manuale tramite il bottone "Invia Nebbia"
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
        players_data = {p.name: p.position for p in self.server.game_state.get_all_players()}
        turn_player = self.server.game_state.get_current_turn_player()
        turn_name = turn_player.name if turn_player else ""
        view_name = "DM_TEST" if getattr(self, "dm_player_view_var", None) and self.dm_player_view_var.get() else ""
        
        time_hour = getattr(self.server.game_state, "time_hour", 12)
        weather = getattr(self.server.game_state, "weather", "Sereno")
        combat_active = getattr(self.server.game_state, "combat_active", False)
        combat_order = [p.name for p in self.server.game_state.players] if combat_active else []
        
        self.map_canvas.update_data(
            map_data, 
            players_data, 
            player_name=view_name, 
            turn_player_name=turn_name, 
            aoes_data=getattr(self.server.game_state, "active_aoes", []),
            time_hour=time_hour,
            weather=weather,
            combat_active=combat_active,
            combat_order=combat_order
        )
        

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
        from common.theme import apply_modern_window_style
        apply_modern_window_style(win)
        win.title("Gestione Viaggio (Hex Crawl)")
        win.minsize(450, 450)
        
        ttk.Label(win, text="Impostazioni di Viaggio").pack(pady=10)
        
        info_frame = ttk.Frame(win)
        info_frame.pack(fill=tk.X, padx=10)
        
        gs = self.server.game_state
        months = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
        month_name = months[gs.time_month] if hasattr(gs, 'time_month') and 1 <= gs.time_month <= 12 else "Mese Sconosciuto"
        
        lbl_time = ttk.Label(info_frame, text=f"Tempo attuale: {gs.time_day} {month_name} {getattr(gs, 'time_year', 1492)} - {gs.time_hour:02d}:00")
        lbl_time.pack(anchor="w")
        
        ttk.Label(info_frame, text="Ore viaggiate oggi: " + str(getattr(gs, "travel_hours_today", 0))).pack(anchor="w")
        
        ttk.Label(info_frame, text="Andatura:").pack(anchor="w", pady=(10,0))
        pace_var = tk.StringVar(value="Normale")
        pace_frame = ttk.Frame(info_frame)
        pace_frame.pack(anchor="w")
        ttk.Radiobutton(pace_frame, text="Lenta", variable=pace_var, value="Lenta").pack(side=tk.LEFT)
        ttk.Radiobutton(pace_frame, text="Normale", variable=pace_var, value="Normale").pack(side=tk.LEFT)
        ttk.Radiobutton(pace_frame, text="Veloce", variable=pace_var, value="Veloce").pack(side=tk.LEFT)
        
        roles_frame = ttk.LabelFrame(win, text="Ruoli del Party")
        roles_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        party_members = [p for p in gs.get_all_players() if getattr(p, "is_party_member", False) or not gs.combat_active]
        if not party_members: party_members = gs.get_all_players()
        
        for p in party_members:
            role = getattr(p, "travel_role", "Nessuna")
            ttk.Label(roles_frame, text=f"{p.name}: {role}").pack(anchor="w")
            
        def consume_rations():
            from common.protocol import make_chat_broadcast
            from server.network import broadcast
            
            msg = "[SISTEMA] Consumo Razioni Giornaliere:\n"
            for p in party_members:
                if not getattr(p, "full_sheet", None):
                    continue
                inv = p.full_sheet.setdefault("inventory", [])
                
                has_ration = False
                has_water = False
                
                for item in inv:
                    name_lower = item.get("name", "").lower()
                    if "razion" in name_lower and int(item.get("quantity", 0)) > 0 and not has_ration:
                        item["quantity"] = str(int(item["quantity"]) - 1)
                        has_ration = True
                    elif ("acqua" in name_lower or "otre" in name_lower) and int(item.get("quantity", 0)) > 0 and not has_water:
                        item["quantity"] = str(int(item["quantity"]) - 1)
                        has_water = True
                        
                inv = [i for i in inv if int(i.get("quantity", 1)) > 0]
                p.full_sheet["inventory"] = inv
                
                if not has_ration or not has_water:
                    # Gain exhaustion
                    if "Sfinimento" not in p.conditions:
                        p.conditions.append("Sfinimento")
                    msg += f"- {p.name}: NON aveva cibo/acqua sufficiente! Guadagna Sfinimento.\n"
                else:
                    msg += f"- {p.name}: Ha consumato 1 Razione e 1 Otre d'Acqua.\n"
            
            gs._trigger_gui_update()
            from common.protocol import make_game_state
            broadcast(gs, make_game_state(gs.get_state_dict()))
            broadcast(gs, make_chat_broadcast("Sistema", msg))
            self.log_to_chat(msg)
            messagebox.showinfo("Razioni Consumate", "Razioni e acqua consumate per il party.")
            
        def do_travel():
            from common.dice import roll_dice
            from common.protocol import make_chat_broadcast
            
            enc_roll = roll_dice("1d20")["total"]
            encounter = "SI! (Tiro: " + str(enc_roll) + ")" if enc_roll >= 16 else "No (" + str(enc_roll) + ")"
            
            nav_roll = roll_dice("1d20")["total"]
            
            # Exhaustion check if traveling > 8 hours
            gs.travel_hours_today = getattr(gs, "travel_hours_today", 0) + 4
            
            exhaustion_msg = ""
            if gs.travel_hours_today > 8:
                exhaustion_msg = "\n[ATTENZIONE] Viaggio Forzato: I giocatori devono superare un TS Costituzione o subire Sfinimento!"
            
            self.advance_time(4) # this broadcasts and updates gui
            
            gs = self.server.game_state
            months = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
            month_name = months[gs.time_month] if hasattr(gs, 'time_month') and 1 <= gs.time_month <= 12 else "Mese Sconosciuto"

            msg = f"--- AVANZAMENTO VIAGGIO (4 Ore) ---\n"
            msg += f"Nuovo Orario: {gs.time_day} {month_name} {getattr(gs, 'time_year', 1492)} - {gs.time_hour:02d}:00\n"
            msg += f"Ore viaggiate oggi: {gs.travel_hours_today}\n"
            msg += f"Andatura: {pace_var.get()}\n"
            msg += f"Incontro Casuale: {encounter}\n"
            msg += f"Tiro Base Navigazione: {nav_roll} (il DM somma i bonus del Navigatore)"
            msg += exhaustion_msg
            
            gs.add_calendar_event(f"Avanzamento Viaggio (Andatura: {pace_var.get()}). Incontro: {encounter}")
            
            self.log_to_chat(msg, tab_name="Sistema")
            from server.network import broadcast
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", msg))
            
            win.destroy()
            
        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Button(btn_frame, text="?? Consuma Razioni", command=consume_rations).pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Button(btn_frame, text="Viaggia (4 Ore / 1 Turno)", command=do_travel, style="Primary.TButton").pack(side=tk.RIGHT, expand=True, padx=5)

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

    def update_player_list(self):
        current_selection=self.player_listbox.curselection()
        self.player_listbox.delete(0, tk.END)
        
        gs = self.server.game_state
        time_str = f"{gs.time_hour:02d}:00"
        if 6 <= gs.time_hour < 12: period = "Mattina"
        elif 12 <= gs.time_hour < 18: period = "Pomeriggio"
        elif 18 <= gs.time_hour < 22: period = "Sera"
        else: period = "Notte"
        
        months = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
        month_name = months[gs.time_month] if hasattr(gs, 'time_month') and 1 <= gs.time_month <= 12 else "Mese Sconosciuto"
        
        self.lbl_time.config(text=f"{gs.time_day} {month_name} {getattr(gs, 'time_year', 1492)} - {time_str} ({period})")
        if self.weather_var.get() != gs.weather:
            self.weather_var.set(gs.weather)
            
        if self.server.game_state.combat_active:
            self.combat_controls_frame.pack(fill=tk.X, side=tk.TOP, pady=5, before=self.player_listbox)
            self.btn_combat.config(text="⏹ Termina Combattimento", style='Danger.TButton')
            self.lbl_round.config(text=f"Round: {self.server.game_state.round_number}")
            self.btn_prev_turn.config(state=tk.NORMAL)
            self.btn_next_turn.config(state=tk.NORMAL)
        else:
            self.combat_controls_frame.pack_forget()
            self.btn_combat.config(text="🗡 Inizia Combattimento", style='Primary.TButton')
            self.lbl_round.config(text="Round: -")
            self.btn_prev_turn.config(state=tk.DISABLED)
            self.btn_next_turn.config(state=tk.DISABLED)

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
                        display_text = f"{prefix}{hidden_str}{p.name} (HP: {p.hp}/{p.max_hp}) [Iniz: {p.initiative}]{conds}"
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
                        display_text = f"  {hidden_str}{p.name} [Non in Combattimento]{conds}"
                    else:
                        display_text = f"{prefix}{hidden_str}{p.name} (HP: {p.hp}/{p.max_hp}) [Iniz: {p.initiative}]{conds}"
                        
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
        except queue.Empty: pass
        self.master.after(100, self.process_queue)

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
        if messagebox.askokcancel("Esci", "Vuoi chiudere il server?"):
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
        text_widget = scrolledtext.ScrolledText(tab_frame, state='disabled', wrap=tk.WORD, bg="#36393F", 
fg="#DCDDDE", borderwidth=0, highlightthickness=0, font=("Arial", 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(tab_frame, text=name)
        self.chat_tabs[name] = text_widget
        
        # Configure tags for Discord-like format
        text_widget.tag_config("timestamp", foreground="#72767D", font=("Arial", 8))
        text_widget.tag_config("sender", font=("Arial", 10, "bold"))
        text_widget.tag_config("text", foreground="#DCDDDE")
        
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
        query = self.bestiario_search_var.get()
        threading.Thread(target=self._search_bestiario_thread, args=(query,), daemon=True).start()

    def _search_bestiario_thread(self, query):
        import urllib.request
        import json
        try:
            url = f"https://www.dnd5eapi.co/api/monsters/?name={query}".replace(" ", "+")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                results = data.get("results", [])
                self.master.after(0, self._update_bestiario_list, results)
        except Exception as e:
            print("Error searching bestiario:", e)

    def _update_bestiario_list(self, results):
        self.bestiario_listbox.delete(0, tk.END)
        self.bestiario_results = results
        for res in results:
            self.bestiario_listbox.insert(tk.END, res.get("name", "Unknown"))

    def spawn_bestiario(self):
        selection = self.bestiario_listbox.curselection()
        if not selection: return
        index_selezionato = self.bestiario_results[selection[0]].get("index")
        if not index_selezionato: return
        threading.Thread(target=self._spawn_bestiario_thread, args=(index_selezionato,), daemon=True).start()

    def _spawn_bestiario_thread(self, index_selezionato):
        import urllib.request
        import json
        from common.game_state import Player
        from common.protocol import make_player_joined, make_player_stats_update
        from common.network_utils import broadcast
        try:
            url = f"https://www.dnd5eapi.co/api/monsters/{index_selezionato}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
                name = data.get("name", "Mostro")
                hit_points = data.get("hit_points", 10)
                
                ac_list = data.get("armor_class", [])
                ac_value = 10
                if ac_list:
                    ac_item = ac_list[0]
                    if isinstance(ac_item, dict):
                        ac_value = ac_item.get("value", 10)
                    else:
                        ac_value = ac_item
                        
                dex = data.get("dexterity", 10)
                initiative = (dex - 10) // 2
                
                pos = [0, 0]
                if hasattr(self, 'map_canvas') and self.map_canvas and hasattr(self.map_canvas, '_last_clicked_hex') and self.map_canvas._last_clicked_hex:
                    pos = [self.map_canvas._last_clicked_hex.q, self.map_canvas._last_clicked_hex.r]
                
                base_name = name
                idx = 1
                new_name = base_name
                while self.server.game_state.find_player(new_name):
                    idx += 1
                    new_name = f"{base_name} {idx}"
                
                npc = Player(new_name, None, None)
                npc.hp = hit_points
                npc.max_hp = hit_points
                npc.initiative = initiative
                npc.position = pos
                npc.full_sheet = {
                    "name": npc.name,
                    "hp_current": npc.hp,
                    "hp_max": npc.max_hp,
                    "ac": ac_value
                }
                
                self.server.game_state.add_player(npc)
                
                self.server.game_state._trigger_gui_update()
                broadcast(self.server.game_state, make_player_joined(npc.to_dict()))
                broadcast(self.server.game_state, make_player_stats_update(npc.name, npc.hp, npc.max_hp, npc.initiative, []))
                
        except Exception as e:
            print("Error spawning bestiario:", e)


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


class TextHandoutDialog(tk.Toplevel):
    def __init__(self, dm_gui):
        super().__init__(dm_gui.master)
        self.dm_gui = dm_gui
        self.title("Condividi Documento / Nota Testuale")
        self.minsize(580, 450)
        self.transient(dm_gui.master)
        self.grab_set()

        from common.theme import apply_modern_window_style
        apply_modern_window_style(self)

        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Titolo del Documento:", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.title_entry = ttk.Entry(main_frame, font=("Helvetica", 12))
        self.title_entry.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(main_frame, text="Testo da mostrare ai giocatori:", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
        from tkinter import scrolledtext
        self.content_text = scrolledtext.ScrolledText(main_frame, font=("Helvetica", 11), wrap=tk.WORD, height=10)
        self.content_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Invia ai Giocatori", style="Success.TButton", command=self.on_share).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=self.destroy).pack(side=tk.RIGHT)

        self.title_entry.focus_set()

    def on_share(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Attenzione", "Il titolo è obbligatorio.", parent=self)
            return
        content = self.content_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("Attenzione", "Il contenuto non può essere vuoto.", parent=self)
            return

        from common.protocol import make_handout_broadcast
        from common.network_utils import broadcast
        broadcast(self.dm_gui.server.game_state, make_handout_broadcast(title, None, content))
        messagebox.showinfo("Successo", "Documento condiviso con tutti i giocatori connessi!")
        self.destroy()


class CustomNPCDialog(tk.Toplevel):
    def __init__(self, dm_gui):
        super().__init__(dm_gui.master)
        self.dm_gui = dm_gui
        self.title("Crea Nuovo NPC / Mostro Custom")
        self.minsize(550, 480)
        self.transient(dm_gui.master)
        self.grab_set()

        from common.theme import apply_modern_window_style
        apply_modern_window_style(self)

        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Nome del PNG/Mostro:", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.name_entry = ttk.Entry(main_frame, font=("Helvetica", 12))
        self.name_entry.pack(fill=tk.X, pady=(0, 15))

        grid_frame = ttk.Frame(main_frame)
        grid_frame.pack(fill=tk.X, pady=(0, 15))
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(3, weight=1)

        ttk.Label(grid_frame, text="HP Massimi:", font=("Helvetica", 11)).grid(row=0, column=0, padx=(0, 10), pady=5, sticky=tk.W)
        self.hp_entry = ttk.Entry(grid_frame, font=("Helvetica", 11), width=10)
        self.hp_entry.insert(0, "10")
        self.hp_entry.grid(row=0, column=1, pady=5, sticky=tk.W)

        ttk.Label(grid_frame, text="Iniziativa:", font=("Helvetica", 11)).grid(row=0, column=2, padx=(20, 10), pady=5, sticky=tk.W)
        self.init_entry = ttk.Entry(grid_frame, font=("Helvetica", 11), width=10)
        self.init_entry.insert(0, "0")
        self.init_entry.grid(row=0, column=3, pady=5, sticky=tk.W)

        ttk.Label(grid_frame, text="Classe Armatura (CA):", font=("Helvetica", 11)).grid(row=1, column=0, padx=(0, 10), pady=5, sticky=tk.W)
        self.ac_entry = ttk.Entry(grid_frame, font=("Helvetica", 11), width=10)
        self.ac_entry.insert(0, "10")
        self.ac_entry.grid(row=1, column=1, pady=5, sticky=tk.W)

        ttk.Label(grid_frame, text="Velocità (ft):", font=("Helvetica", 11)).grid(row=1, column=2, padx=(20, 10), pady=5, sticky=tk.W)
        self.speed_entry = ttk.Entry(grid_frame, font=("Helvetica", 11), width=10)
        self.speed_entry.insert(0, "30")
        self.speed_entry.grid(row=1, column=3, pady=5, sticky=tk.W)

        ttk.Label(main_frame, text="Note/Descrizione (opzionale):", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))
        from tkinter import scrolledtext
        self.notes_text = scrolledtext.ScrolledText(main_frame, font=("Helvetica", 11), height=5, wrap=tk.WORD)
        self.notes_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Salva", style="Success.TButton", command=self.on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=self.destroy).pack(side=tk.RIGHT)

        self.name_entry.focus_set()

    def on_save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Attenzione", "Il nome è obbligatorio.", parent=self)
            return
        if self.dm_gui.server.game_state.find_player(name):
            messagebox.showerror("Errore", "Un'entità con questo nome esiste già.", parent=self)
            return

        try:
            hp = int(self.hp_entry.get() or 10)
            init = int(self.init_entry.get() or 0)
            ac = int(self.ac_entry.get() or 10)
            speed = int(self.speed_entry.get() or 30)
        except ValueError:
            messagebox.showerror("Errore", "I valori statistici devono essere numeri interi.", parent=self)
            return

        npc = Player(name, None, None)
        npc.hp = hp
        npc.max_hp = hp
        npc.initiative = init
        npc.speed = speed
        
        # Add basic full_sheet for CA and notes
        npc.full_sheet = {
            "ac": ac,
            "notes": self.notes_text.get("1.0", tk.END).strip()
        }

        self.dm_gui.server.game_state.add_player(npc)
        from common.protocol import make_player_joined
        from common.network_utils import broadcast
        broadcast(self.dm_gui.server.game_state, make_player_joined(npc.to_dict()))
        self.dm_gui.log_to_chat(f"[SISTEMA] NPC Custom '{name}' aggiunto alla sessione.")
        self.destroy()


class DMPlayerSheetViewer(tk.Toplevel):
    def __init__(self, master, player_name, sheet):
        super().__init__(master)
        self.title(f"Scheda Personaggio: {player_name}")
        self.minsize(700, 680)
        self.transient(master)
        self.grab_set()
        apply_modern_window_style(self)
        
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Header Card
        header_card = ttk.LabelFrame(main_frame, text="Informazioni Generali", padding="10")
        header_card.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header_card, text=sheet.get("name", player_name), font=("Helvetica", 14, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 5))
        
        ttk.Label(header_card, text="Classe:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, sticky="w", padx=(0, 5))
        ttk.Label(header_card, text=f"{sheet.get('char_class', '-')} (Lvl {sheet.get('level', 1)})").grid(row=1, column=1, sticky="w", padx=(0, 20))
        ttk.Label(header_card, text="Razza:", font=("Helvetica", 10, "bold")).grid(row=1, column=2, sticky="w", padx=(0, 5))
        ttk.Label(header_card, text=f"{sheet.get('race', '-')}").grid(row=1, column=3, sticky="w")

        ttk.Label(header_card, text="Allineamento:", font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky="w", padx=(0, 5), pady=(4, 0))
        ttk.Label(header_card, text=f"{sheet.get('alignment', '-')}").grid(row=2, column=1, sticky="w", padx=(0, 20), pady=(4, 0))
        ttk.Label(header_card, text="Background:", font=("Helvetica", 10, "bold")).grid(row=2, column=2, sticky="w", padx=(0, 5), pady=(4, 0))
        ttk.Label(header_card, text=f"{sheet.get('background', '-')}").grid(row=2, column=3, sticky="w", pady=(4, 0))

        # 2. Notebook a Schede Tabellari
        nb = ttk.Notebook(main_frame)
        nb.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Statistiche & Caratteristiche
        tab_stats = ttk.Frame(nb, padding="10")
        nb.add(tab_stats, text="📊 Statistiche & Attributi")

        vital_frame = ttk.LabelFrame(tab_stats, text="Combattimento", padding="10")
        vital_frame.pack(fill=tk.X, pady=(0, 10))
        
        hp_cur = sheet.get("hp_current", 0)
        hp_max = sheet.get("hp_max", 0)
        ac = sheet.get("ac", 10)
        init = sheet.get("initiative", 0)
        speed = sheet.get("speed", 30)

        for col, (label, val) in enumerate([
            ("Punti Ferita (HP)", f"{hp_cur} / {hp_max}"),
            ("Classe Armatura (CA)", str(ac)),
            ("Iniziativa", f"{'+' if init >= 0 else ''}{init}"),
            ("Velocità", f"{speed} ft.")
        ]):
            box = ttk.Frame(vital_frame, relief="ridge", padding="8")
            box.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5)
            ttk.Label(box, text=label, font=("Helvetica", 9), anchor="center").pack()
            ttk.Label(box, text=val, font=("Helvetica", 13, "bold"), anchor="center").pack(pady=2)

        attr_frame = ttk.LabelFrame(tab_stats, text="Punteggi di Caratteristica", padding="10")
        attr_frame.pack(fill=tk.BOTH, expand=True)

        attr_tree = ttk.Treeview(attr_frame, columns=("Attr", "Score", "Mod"), show="headings", height=6)
        attr_tree.heading("Attr", text="Caratteristica")
        attr_tree.heading("Score", text="Punteggio Base")
        attr_tree.heading("Mod", text="Modificatore")
        attr_tree.column("Attr", width=150, anchor="center")
        attr_tree.column("Score", width=120, anchor="center")
        attr_tree.column("Mod", width=120, anchor="center")
        attr_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        attrs = sheet.get("attributes", {})
        attr_names = {
            "FOR": "Forza (FOR)", "DES": "Destrezza (DES)", "COS": "Costituzione (COS)",
            "INT": "Intelligenza (INT)", "SAG": "Saggezza (SAG)", "CAR": "Carisma (CAR)"
        }
        for k in ["FOR", "DES", "COS", "INT", "SAG", "CAR"]:
            score = attrs.get(k, 10)
            mod = (score - 10) // 2
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            attr_tree.insert("", tk.END, values=(attr_names.get(k, k), score, mod_str))

        # Tab 2: Equipaggiamento & Inventario (Tabella)
        tab_inv = ttk.Frame(nb, padding="10")
        nb.add(tab_inv, text="🎒 Inventario")

        inv_tree_frame = ttk.Frame(tab_inv)
        inv_tree_frame.pack(fill=tk.BOTH, expand=True)

        inv_tree = ttk.Treeview(inv_tree_frame, columns=("Slot", "Nome", "Tipo", "Qty", "Desc"), show="headings")
        inv_tree.heading("Slot", text="#")
        inv_tree.heading("Nome", text="Nome Oggetto")
        inv_tree.heading("Tipo", text="Tipologia")
        inv_tree.heading("Qty", text="Quantità")
        inv_tree.heading("Desc", text="Descrizione / Effetto")
        inv_tree.column("Slot", width=40, anchor="center")
        inv_tree.column("Nome", width=150)
        inv_tree.column("Tipo", width=110, anchor="center")
        inv_tree.column("Qty", width=60, anchor="center")
        inv_tree.column("Desc", width=250)
        inv_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inv_scroll = ttk.Scrollbar(inv_tree_frame, orient=tk.VERTICAL, command=inv_tree.yview)
        inv_tree.configure(yscroll=inv_scroll.set)
        inv_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        grid = sheet.get("inventory_grid", [])
        slot_idx = 1
        if isinstance(grid, list):
            for it in grid:
                if it:
                    inv_tree.insert("", tk.END, values=(
                        str(slot_idx),
                        it.get("name", "Sconosciuto"),
                        it.get("type", "Oggetto"),
                        str(it.get("qty", 1)),
                        it.get("desc", "-")
                    ))
                    slot_idx += 1
        raw_inv = sheet.get("inventory")
        if raw_inv and isinstance(raw_inv, str) and slot_idx == 1:
            inv_tree.insert("", tk.END, values=("1", "Inventario Testuale", "Testo", "1", raw_inv))

        curr_frame = ttk.LabelFrame(tab_inv, text="Borsa delle Monete", padding="8")
        curr_frame.pack(fill=tk.X, pady=(10, 0))
        currency = sheet.get("currency", {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0})
        if not isinstance(currency, dict):
            currency = {"MO": sheet.get("gp", 0)}
        for c_key, c_name in [("MR", "Rame (MR)"), ("MA", "Argento (MA)"), ("ME", "Electrum (ME)"), ("MO", "Oro (MO)"), ("MP", "Platino (MP)")]:
            c_box = ttk.Frame(curr_frame, padding="5")
            c_box.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
            ttk.Label(c_box, text=c_name, font=("Helvetica", 9)).pack()
            ttk.Label(c_box, text=str(currency.get(c_key, 0)), font=("Helvetica", 11, "bold"), foreground="#FFD700" if c_key=="MO" else TEXT_COLOR).pack()

        # Tab 3: Grimorio & Incantesimi (Tabella)
        tab_spells = ttk.Frame(nb, padding="10")
        nb.add(tab_spells, text="✨ Grimorio")

        slots_frame = ttk.LabelFrame(tab_spells, text="Slot Incantesimo", padding="8")
        slots_frame.pack(fill=tk.X, pady=(0, 10))
        spell_slots = sheet.get("spell_slots", {})
        if isinstance(spell_slots, dict):
            for i in range(1, 10):
                s_info = spell_slots.get(str(i), {"max": 0, "current": 0})
                if isinstance(s_info, dict):
                    m = s_info.get("max", 0)
                    c = s_info.get("current", 0)
                elif isinstance(s_info, list):
                    m = s_info[1] if len(s_info) > 1 else 0
                    c = s_info[0] if len(s_info) > 0 else 0
                else:
                    m, c = 0, 0
                s_box = ttk.Frame(slots_frame, padding="4")
                s_box.pack(side=tk.LEFT, expand=True)
                ttk.Label(s_box, text=f"Lvl {i}", font=("Helvetica", 8)).pack()
                ttk.Label(s_box, text=f"{c}/{m}", font=("Helvetica", 10, "bold")).pack()

        spells_tree_frame = ttk.Frame(tab_spells)
        spells_tree_frame.pack(fill=tk.BOTH, expand=True)

        spells_tree = ttk.Treeview(spells_tree_frame, columns=("Lvl", "Nome", "Tempo", "Raggio", "Desc"), show="headings")
        spells_tree.heading("Lvl", text="Livello")
        spells_tree.heading("Nome", text="Nome Incantesimo")
        spells_tree.heading("Tempo", text="Lancio")
        spells_tree.heading("Raggio", text="Raggio / Gittata")
        spells_tree.heading("Desc", text="Descrizione / Effetto")
        spells_tree.column("Lvl", width=70, anchor="center")
        spells_tree.column("Nome", width=140)
        spells_tree.column("Tempo", width=80, anchor="center")
        spells_tree.column("Raggio", width=80, anchor="center")
        spells_tree.column("Desc", width=250)
        spells_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        spells_scroll = ttk.Scrollbar(spells_tree_frame, orient=tk.VERTICAL, command=spells_tree.yview)
        spells_tree.configure(yscroll=spells_scroll.set)
        spells_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        spellbook = sheet.get("spellbook", [])
        if isinstance(spellbook, list):
            for sp in spellbook:
                if isinstance(sp, dict):
                    lvl = sp.get("level", 0)
                    lvl_display = "Trucchetto" if lvl == 0 else f"Livello {lvl}"
                    spells_tree.insert("", tk.END, values=(
                        lvl_display,
                        sp.get("name", "Sconosciuto"),
                        sp.get("time", "-"),
                        sp.get("range", "-"),
                        sp.get("desc", "-")
                    ))
        raw_spells = sheet.get("spells")
        if raw_spells and isinstance(raw_spells, str) and not spellbook:
            spells_tree.insert("", tk.END, values(("-", "Incantesimi Testuali", "-", "-", raw_spells)))

        # Tab 4: Privilegi & Note
        tab_notes = ttk.Frame(nb, padding="10")
        nb.add(tab_notes, text="📜 Privilegi & Note")

        ttk.Label(tab_notes, text="Tratti e Privilegi:", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=(0, 2))
        features_txt = scrolledtext.ScrolledText(tab_notes, height=8, wrap=tk.WORD, font=("Helvetica", 10))
        features_txt.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        features_txt.insert("1.0", sheet.get("features", "Nessun tratto speciale registrato."))
        features_txt.config(state="disabled")

        ttk.Label(tab_notes, text="Note e Background:", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=(0, 2))
        notes_txt = scrolledtext.ScrolledText(tab_notes, height=6, wrap=tk.WORD, font=("Helvetica", 10))
        notes_txt.pack(fill=tk.BOTH, expand=True)
        notes_txt.insert("1.0", sheet.get("notes", "Nessuna nota presente."))
        notes_txt.config(state="disabled")

        close_btn = ttk.Button(main_frame, text="Chiudi Scheda", command=self.destroy)
        close_btn.pack(side=tk.BOTTOM, pady=(10, 0))


class CampaignStarterKitDialog(tk.Toplevel):
    def __init__(self, dm_gui):
        super().__init__(dm_gui.master)
        self.dm_gui = dm_gui
        self.title("Configura Starter Pack Campagna (Equipaggiamento Iniziale)")
        self.minsize(650, 500)
        self.transient(dm_gui.master)
        self.grab_set()
        apply_modern_window_style(self)

        from common.starter_equipment import get_campaign_starter_kit, DEFAULT_CAMPAIGN_STARTER_KIT
        cur_kit = getattr(self.dm_gui.server.game_state, "campaign_starter_kit", None)
        if not cur_kit:
            cur_kit = get_campaign_starter_kit()
        self.items = [i.copy() for i in cur_kit]

        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Equipaggiamento Iniziale della Campagna", font=("Helvetica", 13, "bold")).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(main_frame, text="I nuovi PG riceveranno automaticamente questi oggetti al loro primo login in questa campagna:", 
                  wraplength=600).pack(anchor=tk.W, pady=(0, 10))

        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.tree = ttk.Treeview(tree_frame, columns=("Nome", "Tipo", "Qty", "Peso", "Desc"), show="headings", height=8)
        self.tree.heading("Nome", text="Nome Oggetto")
        self.tree.heading("Tipo", text="Tipo")
        self.tree.heading("Qty", text="Quantità")
        self.tree.heading("Peso", text="Peso (lbs)")
        self.tree.heading("Desc", text="Descrizione")
        self.tree.column("Nome", width=150)
        self.tree.column("Tipo", width=100, anchor="center")
        self.tree.column("Qty", width=60, anchor="center")
        self.tree.column("Peso", width=70, anchor="center")
        self.tree.column("Desc", width=220)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.refresh_list()

        btn_row = ttk.Frame(main_frame)
        btn_row.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(btn_row, text="+ Aggiungi Oggetto", command=self.on_add_item).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="Rimuovi Selezionato", command=self.on_remove_item).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="Ripristina Predefiniti", command=self.on_reset_defaults).pack(side=tk.LEFT, padx=3)

        bottom_row = ttk.Frame(main_frame)
        bottom_row.pack(fill=tk.X)
        ttk.Button(bottom_row, text="Salva Configurazione", style="Success.TButton", command=self.on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_row, text="Annulla", command=self.destroy).pack(side=tk.RIGHT)

    def refresh_list(self):
        for it in self.tree.get_children():
            self.tree.delete(it)
        for idx, item in enumerate(self.items):
            self.tree.insert("", tk.END, iid=str(idx), values=(
                item.get("name", ""),
                item.get("type", "Oggetto"),
                str(item.get("qty", 1)),
                str(item.get("weight", 0.0)),
                item.get("desc", "")
            ))

    def on_add_item(self):
        name = simpledialog.askstring("Nuovo Oggetto", "Nome dell'oggetto:", parent=self)
        if not name or not name.strip(): return
        item_type = simpledialog.askstring("Tipo Oggetto", "Tipo (Arma, Armatura, Consumabile, Documento, Valuta, Equipaggiamento):", initialvalue="Equipaggiamento", parent=self) or "Equipaggiamento"
        qty = simpledialog.askinteger("Quantità", "Quantità:", initialvalue=1, minvalue=1, parent=self) or 1
        desc = simpledialog.askstring("Descrizione", "Descrizione o effetto dell'oggetto:", parent=self) or ""
        self.items.append({
            "name": name.strip(),
            "type": item_type.strip(),
            "qty": qty,
            "weight": 1.0,
            "desc": desc.strip()
        })
        self.refresh_list()

    def on_remove_item(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])
        self.items.pop(idx)
        self.refresh_list()

    def on_reset_defaults(self):
        from common.starter_equipment import DEFAULT_CAMPAIGN_STARTER_KIT
        if messagebox.askyesno("Ripristina", "Vuoi ripristinare il kit iniziale predefinito della campagna?", parent=self):
            self.items = [i.copy() for i in DEFAULT_CAMPAIGN_STARTER_KIT]
            self.refresh_list()

    def on_save(self):
        from common.starter_equipment import save_campaign_starter_kit
        save_campaign_starter_kit(self.items)
        self.dm_gui.server.game_state.campaign_starter_kit = [i.copy() for i in self.items]
        messagebox.showinfo("Salvato", "Equipaggiamento iniziale della campagna salvato con successo!", parent=self)
        self.destroy()



if __name__ == "__main__":
    import tkinter as tk
    root = tk.Tk()
    DM_GUI(root)
    root.mainloop()
