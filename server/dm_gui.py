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
from tkinter import messagebox, filedialog, ttk, scrolledtext, simpledialog
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
from components.ui_components import HexMapCanvas

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
        tools_menu.add_command(label="Scarica Mappe Famose", command=self.open_map_downloader)
        tools_menu.add_command(label="Compendio & SRD", command=self.open_srd_importer)
        tools_menu.add_command(label="Preparazione Combattimenti", command=self.open_encounter_builder)
        tools_menu.add_separator()
        tools_menu.add_command(label="Pannello Viaggio", command=self.open_travel_panel)
        tools_menu.add_command(label="Condividi Handout (Immagine)", command=self.share_handout)
        menubar.add_cascade(label="Strumenti", menu=tools_menu)
        
        # 2. LAYOUT PRINCIPALE (3 Colonne: Sinistra=Gestione, Centro=Mappa, Destra=Chat)
        main_frame = ttk.Frame(self.master, padding="15 15 15 15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=4)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(2, weight=2)
        main_frame.rowconfigure(0, weight=1)
        
        # --- COLONNA 0: PANNELLO SINISTRO (Gestione e Combattimento) ---
        left_panel = ttk.Frame(main_frame)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ttk.Label(left_panel, text="Avventurieri & NPC", font=self.default_font, foreground="#E0E0E0").pack(anchor="w", pady=(0, 5))
        self.player_listbox = tk.Listbox(left_panel, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=self.default_font, selectbackground=ACCENT_RED, borderwidth=0, relief="flat", highlightthickness=0)
        self.player_listbox.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=(0, 5))
        self.player_listbox.bind("<Double-Button-1>", self.open_private_chat_from_list)
        self.player_listbox.bind("<Button-3>", self.show_player_context_menu)
        self.player_listbox.bind("<<ListboxSelect>>", self.on_player_selected)

        self.btn_hide_reveal = ttk.Button(left_panel, text="Nascondi/Rivela PNG", command=self.toggle_hide_reveal)
        self.btn_hide_reveal.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))

        self.npc_actions_frame = ttk.LabelFrame(left_panel, text="Azioni PNG Selezionato")
        self.npc_actions_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
        
        self.btn_combat = ttk.Button(left_panel, text="🗡 Inizia Combattimento", command=self.toggle_combat, style='Primary.TButton')
        self.btn_combat.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
        
        # Questo frame combat apparirà solo quando si entra in combat
        self.combat_controls_frame = ttk.Frame(left_panel)
        # Non lo packiamo subito. Verrà packato in update_state() o toggle_combat()
        
        self.lbl_round = ttk.Label(self.combat_controls_frame, text="Round: -", font=self.default_font)
        self.lbl_round.pack(fill=tk.X, pady=(0, 5))
        
        turn_nav_frame = ttk.Frame(self.combat_controls_frame)
        turn_nav_frame.pack(fill=tk.X, pady=(0, 5))
        self.btn_prev_turn = ttk.Button(turn_nav_frame, text="⬅ Precedente", command=self.prev_turn_gui, state=tk.DISABLED)
        self.btn_prev_turn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        self.btn_next_turn = ttk.Button(turn_nav_frame, text="Prossimo ➡", command=self.next_turn_gui, state=tk.DISABLED)
        self.btn_next_turn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        ttk.Button(left_panel, text="+ Aggiungi NPC/Mostro", command=self.add_npc).pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        btn_frame_bottom = ttk.Frame(left_panel)
        btn_frame_bottom.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        ttk.Button(btn_frame_bottom, text="Spawna PNG", command=self.spawn_png_dialog, style="Primary.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(btn_frame_bottom, text="Encounter Builder", command=self.open_encounter_builder, style="Primary.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        self.player_menu = tk.Menu(self.master, tearoff=0, bg="#3E2723", fg="#F5F5DC", font=self.default_font)
        self.player_menu.add_command(label="Visualizza Scheda", command=self.view_player_sheet)
        self.player_menu.add_command(label="Assegna Oggetto", command=self.open_assign_item_dialog)
        self.player_menu.add_command(label="Modifica HP", command=self.open_modify_hp_dialog)
        self.player_menu.add_command(label="Modifica Stati/Condizioni", command=self.open_conditions_dialog)
        self.player_menu.add_command(label="Esegui Azione (Danno/Cura)", command=self.open_action_dialog)
        self.player_menu.add_command(label="Apri Chat Privata", command=self.open_private_chat_from_context)
        self.player_menu.add_separator()
        self.player_menu.add_command(label="Aggiungi/Rimuovi da Combattimento", command=self.toggle_player_combat_status)
        self.player_menu.add_separator()
        self.player_menu.add_command(label="Rimuovi", command=self.remove_entity)
        
        # --- COLONNA 1: MAPPA (Viewport pulita) ---
        map_outer_frame = ttk.Frame(main_frame)
        map_outer_frame.grid(row=0, column=1, sticky="nsew", padx=10)
        
        # Toolbar mappa fluttuante (minimalista)
        map_top_bar = ttk.Frame(map_outer_frame)
        map_top_bar.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(map_top_bar, text="Mappa di Gioco", font=self.default_font, foreground="#E0E0E0").pack(side=tk.LEFT)
        
        self.btn_clear_aoe = ttk.Button(map_top_bar, text="Pulisci AoE", command=self.clear_aoes)
        self.btn_clear_aoe.pack(side=tk.RIGHT, padx=5)
        
        fow_toolbar = ttk.Frame(map_top_bar)
        fow_toolbar.pack(side=tk.RIGHT, padx=5)
        
        self.fow_enabled_var = tk.BooleanVar(value=False)
        self.fow_mode_var = tk.StringVar(value="Muovi Token")
        
        ttk.Label(fow_toolbar, text="Strumento Mappa:", font=self.default_font).pack(side=tk.LEFT, padx=(0, 5))
        
        # Tool combobox
        self.map_tool_combo = ttk.Combobox(fow_toolbar, textvariable=self.fow_mode_var, state="readonly", width=18)
        self.map_tool_combo['values'] = ("Muovi Token", "Cancella Nebbia", "Disegna Nebbia")
        self.map_tool_combo.pack(side=tk.LEFT, padx=5)
        
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
        self.map_canvas.set_on_ping_callback(self.on_ping_callback)
        
        chat_panel=ttk.Frame(main_frame)
        chat_panel.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        ttk.Label(chat_panel, text="Messaggi", font=self.default_font, foreground="#E0E0E0").pack(anchor="w", pady=(0, 5))
        
        # We need a container inside chat_panel for rowconfigure to work if we used grid, but we use pack for Notebook
        self.notebook = ttk.Notebook(chat_panel); self.notebook.pack(fill=tk.BOTH, expand=True, pady=0)
        self.create_chat_tab("Sistema")
        
        chat_input_frame = ttk.Frame(chat_panel)
        chat_input_frame.pack(fill=tk.X, pady=(5, 0))
        self.chat_entry=ttk.Entry(chat_input_frame); self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.chat_entry.bind("<Return>", lambda e: self.send_dm_chat())
        ttk.Button(chat_input_frame, text="Invia", command=self.send_dm_chat).pack(side=tk.LEFT)
        
        btn_frame = ttk.Frame(chat_panel)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Tira Dadi", command=self.roll_dice_dialog, style="Primary.TButton").pack(side=tk.LEFT)

    def on_ping_callback(self, clicked_hex):
        broadcast(self.server.game_state, make_ping_broadcast(clicked_hex.q, clicked_hex.r, "red"))
        self.map_canvas.show_ping(clicked_hex.q, clicked_hex.r, "red")

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
            from tkinter import messagebox
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
            from tkinter import messagebox
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
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
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
        dialog.geometry("400x550")
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
            init_dialog.geometry("300x400")
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

    def _broadcast_fow_update(self):
        if self.server.game_state.current_map and "fow_draft" in self.server.game_state.current_map:
            self.server.game_state.current_map["fow_revealed"] = self.server.game_state.current_map["fow_draft"].copy()
        broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
        self.log_to_chat("[SISTEMA] Nebbia di Guerra sincronizzata con i giocatori.")

    def on_hex_clicked(self, clicked_hex):
        if not self.server.game_state.current_map: return
        
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
        selected_name = display_text.split(" (HP")[0].replace("▶", "").strip()

        if self.server.game_state.move_player(selected_name, [clicked_hex.q, clicked_hex.r]):
            broadcast(self.server.game_state, make_player_move(selected_name, [clicked_hex.q, clicked_hex.r]))
            self.redraw_map_and_players()
    
    def redraw_map_and_players(self):
        map_data = self.server.game_state.current_map
        players_data = {p.name: p.position for p in self.server.game_state.get_all_players()}
        turn_player = self.server.game_state.get_current_turn_player()
        turn_name = turn_player.name if turn_player else ""
        self.map_canvas.update_data(map_data, players_data, turn_player_name=turn_name)
        

    def open_travel_panel(self):
        win = tk.Toplevel(self.master)
        apply_modern_window_style(win)
        win.title("Gestione Viaggio (Hex Crawl)")
        win.geometry("400x350")
        
        ttk.Label(win, text="Impostazioni di Viaggio").pack(pady=10)
        
        info_frame = ttk.Frame(win)
        info_frame.pack(fill=tk.X, padx=10)
        
        lbl_time = ttk.Label(info_frame, text=f"Tempo attuale: Giorno {self.server.game_state.time_day}, Ore {self.server.game_state.time_hour}:00")
        lbl_time.pack(anchor="w")
        
        ttk.Label(info_frame, text="Andatura:").pack(anchor="w", pady=(10,0))
        pace_var = tk.StringVar(value="Normale")
        pace_frame = ttk.Frame(info_frame)
        pace_frame.pack(anchor="w")
        ttk.Radiobutton(pace_frame, text="Lenta", variable=pace_var, value="Lenta").pack(side=tk.LEFT)
        ttk.Radiobutton(pace_frame, text="Normale", variable=pace_var, value="Normale").pack(side=tk.LEFT)
        ttk.Radiobutton(pace_frame, text="Veloce", variable=pace_var, value="Veloce").pack(side=tk.LEFT)
        
        roles_frame = ttk.LabelFrame(win, text="Ruoli del Party")
        roles_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for p in self.server.game_state.get_all_players():
            role = getattr(p, "travel_role", "Nessuna")
            ttk.Label(roles_frame, text=f"{p.name}: {role}").pack(anchor="w")
            
        def do_travel():
            from common.dice import roll_dice
            from common.protocol import make_chat_broadcast, make_game_state
            
            self.server.game_state.time_hour += 4
            if self.server.game_state.time_hour >= 24:
                self.server.game_state.time_hour -= 24
                self.server.game_state.time_day += 1
                
            enc_roll = roll_dice("1d20")["total"]
            encounter = "SI! (Tiro: " + str(enc_roll) + ")" if enc_roll >= 16 else "No (" + str(enc_roll) + ")"
            
            nav_roll = roll_dice("1d20")["total"]
            
            msg = f"--- AVANZAMENTO VIAGGIO (4 Ore) ---\n"
            msg += f"Nuovo Orario: Giorno {self.server.game_state.time_day}, Ore {self.server.game_state.time_hour}:00\n"
            msg += f"Andatura: {pace_var.get()}\n"
            msg += f"Incontro Casuale: {encounter}\n"
            msg += f"Tiro Base Navigazione: {nav_roll} (il DM somma i bonus del Navigatore)"
            
            self.log_to_chat(msg, tab_name="Sistema")
            from server.server import broadcast
            broadcast(self.server.game_state, make_chat_broadcast("Sistema", msg))
            
            self.server.game_state._trigger_gui_update()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            win.destroy()
            
        ttk.Button(win, text="Viaggia (4 Ore / 1 Turno)", command=do_travel, style="Primary.TButton").pack(pady=10)

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
                players = sorted(players, key=lambda p: p.initiative, reverse=True)

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
                        self.log_to_chat(f"[{player_name}]: {text}", tab_name=player_name)
                elif msg_type == "PING_BROADCAST":
                    payload = msg.get("payload", {})
                    self.map_canvas.show_ping(payload.get("q"), payload.get("r"), payload.get("color", "yellow"))
        except queue.Empty: pass
        self.master.after(100, self.process_queue)

    def on_closing(self):
        if messagebox.askokcancel("Esci", "Vuoi chiudere il server?"): self.server.stop(); self.master.destroy()

    def share_handout(self):
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
        text_widget = scrolledtext.ScrolledText(tab_frame, state='disabled', wrap=tk.WORD, bg=SURFACE_COLOR, fg=TEXT_COLOR, borderwidth=0, highlightthickness=0)
        text_widget.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(tab_frame, text=name)
        self.chat_tabs[name] = text_widget
        
    def open_private_chat_from_list(self, event):
        selected_indices = self.player_listbox.curselection()
        if not selected_indices: return
        display_text = self.player_listbox.get(selected_indices[0])
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
            self.player_listbox.selection_clear(0, tk.END)
            self.player_listbox.selection_set(index)
            self.player_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.player_menu.grab_release()

    def view_player_sheet(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
        player = self.server.game_state.find_player(player_name)
        
        if not player or not player.full_sheet:
            messagebox.showinfo("Nessuna Scheda", f"Nessuna scheda disponibile per {player_name}.")
            return
            
        sheet = player.full_sheet
        win = tk.Toplevel(self.master)
        apply_modern_window_style(win)
        win.title(f"Scheda di {player_name}")
        win.geometry("450x600")
        
        txt = scrolledtext.ScrolledText(win, font=self.default_font, bg=SURFACE_COLOR, fg=TEXT_COLOR)
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        lines = [
            f"=== {sheet.get('name', 'Sconosciuto')} ===",
            f"Classe: {sheet.get('char_class', '')} - Livello: {sheet.get('level', 1)}",
            f"Razza: {sheet.get('race', '')}",
            f"Allineamento: {sheet.get('alignment', '')} - Background: {sheet.get('background', '')}",
            f"Campagna: {sheet.get('campaign', '')}",
            "",
            "=== STATISTICHE ===",
            f"HP: {sheet.get('hp_current', 0)} / {sheet.get('hp_max', 0)}",
            f"CA: {sheet.get('ac', 10)} | Iniziativa: {sheet.get('initiative', 0)} | Velocità: {sheet.get('speed', 30)} ft.",
            ""
        ]
        
        attrs = sheet.get("attributes", {})
        for k, v in attrs.items():
            mod = (v - 10) // 2
            lines.append(f"{k}: {v} ({'+' if mod >= 0 else ''}{mod})")
            
        lines.extend([
            "",
            "=== INVENTARIO ==="
        ])
        
        inv_grid = sheet.get("inventory_grid")
        if inv_grid is not None and isinstance(inv_grid, list):
            items_str = []
            for item in inv_grid:
                if item:
                    items_str.append(f"- {item.get('name', '')} (x{item.get('qty', 1)}) [{item.get('type', '')}]")
            if not items_str:
                lines.append("Nessun equipaggiamento.")
            else:
                lines.extend(items_str)
        else:
            lines.append(sheet.get("inventory", "Nessun equipaggiamento."))

        lines.extend([
            "",
            "=== TRATTI E PRIVILEGI ===",
            sheet.get("features", "Nessun tratto speciale."),
            "",
            "=== INCANTESIMI ===",
            sheet.get("spells", "Nessun incantesimo."),
            "",
            "=== NOTE ===",
            sheet.get("notes", "")
        ])
        
        txt.insert("1.0", "\n".join(lines))
        txt.config(state="disabled")

    def open_assign_item_dialog(self, prefill_item=None):
        sel = self.player_listbox.curselection()
        if not sel:
            messagebox.showinfo("Attenzione", "Seleziona prima un giocatore dalla lista a cui assegnare l'oggetto.")
            return
            
        display_text = self.player_listbox.get(sel[0])
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
        player = self.server.game_state.find_player(player_name)
        
        if not player or not player.conn:
            messagebox.showinfo("Errore", f"Il giocatore {player_name} non è connesso.")
            return

        win = tk.Toplevel(self.master)
        apply_modern_window_style(win)
        win.title(f"Assegna Oggetto a {player_name}")
        win.geometry("300x350")

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
        player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
        player = self.server.game_state.find_player(player_name)
        if not player: return

        win = tk.Toplevel(self.master)
        apply_modern_window_style(win)
        win.title(f"Stati di {player_name}")
        win.geometry("250x350")

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

    def open_action_dialog(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
        target_name = display_text.split(" (HP")[0].replace("▶", "").strip()
        target_player = self.server.game_state.find_player(target_name)
        if not target_player: return

        win = tk.Toplevel(self.master)
        apply_modern_window_style(win)
        win.title(f"Azione su {target_name}")
        win.geometry("300x300")

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
            self.log_to_chat(f"[DM -> Tutti]: {text}", tab_name="Sistema")
        else:
            target_player = self.server.game_state.find_player(active_tab_name)
            if target_player:
                if target_player.conn:
                    send_message(target_player.conn, make_chat_broadcast("DM", text, is_whisper=True))
                    self.log_to_chat(f"[Tu -> {active_tab_name}]: {text}", tab_name=active_tab_name)
                else:
                    messagebox.showerror("Errore", f"L'entità '{active_tab_name}' è offline o è un NPC.")
            else: messagebox.showerror("Errore", f"Entità '{active_tab_name}' non trovata.")
        self.chat_entry.delete(0, tk.END)

    def log_to_chat(self, message, tab_name="Sistema"):
        text_widget = self.chat_tabs.get(tab_name)
        if not text_widget: return
        text_widget.config(state="normal"); text_widget.insert(tk.END, message + "\n")
        text_widget.config(state="disabled"); text_widget.see(tk.END)

    def add_npc(self):
        name = simpledialog.askstring("Nuovo NPC", "Nome dell'NPC o Mostro (es. Goblin 1):")
        if not name: return
        if self.server.game_state.find_player(name):
            messagebox.showerror("Errore", "Un'entità con questo nome esiste già.")
            return
            
        hp_str = simpledialog.askstring("Nuovo NPC", f"HP Massimi per {name}:", initialvalue="10")
        init_str = simpledialog.askstring("Nuovo NPC", f"Iniziativa per {name}:", initialvalue="0")
        
        try:
            hp = int(hp_str or 10)
            init = int(init_str or 0)
        except ValueError:
            messagebox.showerror("Errore", "Valori numerici non validi.")
            return

        npc = Player(name, None, None)
        npc.hp = hp
        npc.max_hp = hp
        npc.initiative = init
        
        self.server.game_state.add_player(npc)
        broadcast(self.server.game_state, make_player_joined(npc.to_dict()))
        self.log_to_chat(f"[SISTEMA] NPC '{name}' aggiunto alla sessione.")

    def toggle_hide_reveal(self):
        sel = self.player_listbox.curselection()
        if not sel: return
        display_text = self.player_listbox.get(sel[0])
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

if __name__ == "__main__":
    root=tk.Tk()
    DM_GUI(root)
    root.mainloop()