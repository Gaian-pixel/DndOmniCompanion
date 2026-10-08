import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import queue
# client_gui.py
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext, ttk
import socket
import threading
import json
import base64
from io import BytesIO
from PIL import Image, ImageTk

from common.protocol import *
from common.hex_utils import Hex, HexLayout
from common.network_utils import send_message, receive_message
from components.ui_components import HexMapCanvas
from client.character_manager import CharacterManager
from client.login_ui import LoginDialog
from client.character_sheet_ui import CharacterSheetUI

from common.theme import setup_theme, apply_modern_window_style

class ClientGUI:
    def __init__(self, master):
        self.master = master
        setup_theme(master)
        self.master.title("D&D Client")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.client_socket=None; self.name=None; self.is_connected=False
        self.players_data={}; self.local_map_data=None
        self.notebook=None; self.chat_tabs={}; self.player_listbox=None
        self.map_canvas = None
        self.default_font = ("Georgia", 10)
        self.character_manager = CharacterManager()
        self.active_character = None
        self.combat_active = False
        self.turn_index = 0
        self.round_number = 1
        self.gui_queue = queue.Queue()
        self.setup_gui()
        self.master.after(100, self.process_queue)

    def setup_gui(self):
        # 1. MENU BAR GLOBALE
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        
        server_menu = tk.Menu(menubar, tearoff=0)
        server_menu.add_command(label="Connetti al Server...", command=self.connect_to_server)
        # Disconnetti could be added here later if needed
        menubar.add_cascade(label="Server", menu=server_menu)
        
        library_menu = tk.Menu(menubar, tearoff=0)
        library_menu.add_command(label="Compendio SRD", command=self.open_srd_compendium)
        menubar.add_cascade(label="Libreria", menu=library_menu)
        
        # 2. LAYOUT PRINCIPALE (3 Colonne: Sinistra=Azioni, Centro=Mappa, Destra=Social)
        main_frame = ttk.Frame(self.master, padding="15 15 15 15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=4) # Mappa
        main_frame.columnconfigure(0, weight=1) # Azioni
        main_frame.columnconfigure(2, weight=2) # Social/Chat
        main_frame.rowconfigure(0, weight=1)
        
        # --- COLONNA 0: PANNELLO SINISTRO (Azioni PG) ---
        left_panel = ttk.Frame(main_frame)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        self.status_label = ttk.Label(left_panel, text="Stato: Disconnesso", style="Danger.TLabel", font=self.default_font)
        self.status_label.pack(anchor="w", pady=(0, 20))
        
        ttk.Label(left_panel, text="Controlli Giocatore", font=self.default_font, foreground="#E0E0E0").pack(anchor="w", pady=(0, 5))
        
        self.stats_button = ttk.Button(left_panel, text="Scheda PG", command=self.open_stats_dialog, style='Info.TButton')
        self.stats_button.pack(fill=tk.X, pady=2)
        
        self.roll_button = ttk.Button(left_panel, text="Tira Dadi", command=self.roll_dice_dialog)
        self.roll_button.pack(fill=tk.X, pady=2)
        
        self.action_button = ttk.Button(left_panel, text="Azione", command=self.open_action_dialog, style='Primary.TButton')
        self.action_button.pack(fill=tk.X, pady=2)
        
        self.aoe_button = ttk.Button(left_panel, text="Area d'Effetto (AoE)", command=self.open_aoe_dialog)
        self.aoe_button.pack(fill=tk.X, pady=2)
        
        self.travel_button = ttk.Button(left_panel, text="Azioni di Viaggio", command=self.open_travel_dialog, style='Success.TButton')
        self.travel_button.pack(fill=tk.X, pady=2)
        
        ttk.Separator(left_panel, orient="horizontal").pack(fill=tk.X, pady=10)
        
        self.combat_btn = ttk.Button(left_panel, text="🗡 Richiedi Combattimento", command=self.request_combat)
        self.combat_btn.pack(fill=tk.X, pady=2)
        
        self.end_turn_btn = ttk.Button(left_panel, text="⏹ Termina Turno", command=self.end_turn, style='Success.TButton')
        # Not packed initially
        
        # --- COLONNA 1: MAPPA ---
        map_outer_frame = ttk.Frame(main_frame)
        map_outer_frame.grid(row=0, column=1, sticky="nsew", padx=10)
        
        map_top_bar = ttk.Frame(map_outer_frame)
        map_top_bar.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(map_top_bar, text="Mappa di Gioco", font=self.default_font, foreground="#E0E0E0").pack(side=tk.LEFT)
        
        self.map_canvas = HexMapCanvas(map_outer_frame, bg="#1e1e1e")
        self.map_canvas.pack(fill=tk.BOTH, expand=True)
        self.aoe_mode = False
        self.aoe_params = None
        self.map_canvas.set_on_click_callback(self.on_hex_click)
        self.map_canvas.set_on_ping_callback(self.on_ping_callback)
        
        # --- COLONNA 2: PANNELLO DESTRO (Social & Chat) ---
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        
        ttk.Label(right_panel, text="Compagnia", font=self.default_font, foreground="#E0E0E0").pack(anchor="w")
        ttk.Label(right_panel, text="Doppio click per chattare", style="Muted.TLabel").pack(anchor="w", pady=(0, 5))
        
        self.player_listbox = tk.Listbox(right_panel, font=self.default_font, relief="flat", bg="#1e1e1e", fg="white", height=6)
        self.player_listbox.pack(fill=tk.X, pady=(0, 10))
        self.player_listbox.bind("<Double-Button-1>", self.open_private_chat_from_list)
        
        ttk.Label(right_panel, text="Chat e Azioni", font=self.default_font, foreground="#E0E0E0").pack(anchor="w", pady=(0, 5))
        self.notebook = ttk.Notebook(right_panel)
        self.create_chat_tab("Globale")
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=2)
        
        chat_cmd_frame = ttk.Frame(right_panel)
        chat_cmd_frame.pack(fill=tk.X, pady=(5, 0))
        self.entry = ttk.Entry(chat_cmd_frame, font=self.default_font)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry.bind("<Return>", self.send_chat_message)
        ttk.Button(chat_cmd_frame, text="Invia", command=self.send_chat_message).pack(side=tk.LEFT)
        
        self.set_controls_state(tk.DISABLED)

    def on_ping_callback(self, clicked_hex):
        if not self.is_connected: return
        from common.protocol import make_ping_request
        send_message(self.client_socket, make_ping_request(clicked_hex.q, clicked_hex.r, "yellow"))


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
                
            from common.protocol import make_create_aoe_request
            send_message(self.client_socket, make_create_aoe_request(aoe_data))
            self.aoe_mode = False
            messagebox.showinfo("AoE Piazzata", "L'area d'effetto è stata piazzata sulla mappa.")
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
                messagebox.showinfo("Nessun Bersaglio", "Non c'è nessuno in questo esagono.")
        else:
            self.request_move(clicked_hex)


    def open_travel_dialog(self):
        win = tk.Toplevel(self.master)
        win.title("Ruolo di Viaggio")
        win.geometry("300x250")
        apply_modern_window_style(win)
        
        ttk.Label(win, text="Scegli la tua attività per il viaggio:").pack(pady=10)
        role_var = tk.StringVar(value=getattr(self.active_character, "travel_role", "Nessuna"))
        roles = ["Nessuna", "Navigare", "Fare la Guardia", "Cercare Cibo", "Mappare", "Furtivo"]
        
        for r in roles:
            ttk.Radiobutton(win, text=r, variable=role_var, value=r).pack(anchor="w", padx=40)
            
        def submit():
            role = role_var.get()
            self.active_character.travel_role = role
            from common.protocol import make_set_travel_role_request
            from common.network_utils import send_message
            send_message(self.client_socket, make_set_travel_role_request(role))
            win.destroy()
            
        ttk.Button(win, text="Conferma", command=submit, style='Success.TButton').pack(pady=15)

    def open_aoe_dialog(self):
        win = tk.Toplevel(self.master)
        win.title("Lancia Incantesimo / AoE")
        win.geometry("300x250")
        apply_modern_window_style(win)
        
        ttk.Label(win, text="Forma Area:").pack(pady=5)
        type_var = tk.StringVar(value="sfera")
        frame_radio = ttk.Frame(win)
        frame_radio.pack()
        ttk.Radiobutton(frame_radio, text="Sfera/Cubo", variable=type_var, value="sfera").pack(side=tk.LEFT)
        ttk.Radiobutton(frame_radio, text="Cono", variable=type_var, value="cono").pack(side=tk.LEFT)
        ttk.Radiobutton(frame_radio, text="Linea", variable=type_var, value="linea").pack(side=tk.LEFT)
        
        ttk.Label(win, text="Raggio / Lunghezza (esagoni):").pack(pady=5)
        size_entry = ttk.Entry(win, width=10)
        size_entry.insert(0, "3")
        size_entry.pack()
        
        ttk.Label(win, text="Colore:").pack(pady=5)
        color_var = tk.StringVar(value="red")
        color_frame = ttk.Frame(win)
        color_frame.pack()
        colors = {"Rosso": "red", "Blu": "blue", "Verde": "green", "Giallo": "yellow", "Viola": "purple"}
        for cname, cval in colors.items():
            ttk.Radiobutton(color_frame, text=cname, variable=color_var, value=cval).pack(side=tk.LEFT)
            
        def submit():
            try:
                sz = int(size_entry.get())
            except:
                sz = 3
            self.aoe_mode = True
            self.aoe_params = {"type": type_var.get(), "size": sz, "color": color_var.get()}
            messagebox.showinfo("AoE", "Clicca sulla mappa per confermare il bersaglio / centro dell'area d'effetto.")
            win.destroy()
            
        ttk.Button(win, text="Prepara Lancio", command=submit).pack(pady=15)

    def request_move(self, clicked_hex):
        """Invia una richiesta di movimento al server quando il giocatore clicca su un esagono."""
        if not self.is_connected: return
        send_message(self.client_socket, make_move_request(clicked_hex.q, clicked_hex.r))

    def connect_to_server(self):
        if self.is_connected: return
        
        login_dialog = LoginDialog(self.master, self.character_manager)
        self.master.wait_window(login_dialog)
        
        if not login_dialog.result: return
        
        server_ip, char = login_dialog.result
        self.name = char.name
        self.active_character = char
        
        try:
            self.client_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((server_ip, 5000)); self.is_connected = True
            
            send_message(self.client_socket, make_join(self.name))
            send_message(self.client_socket, make_update_stats_request(self.active_character.hp_current, self.active_character.hp_max, self.active_character.initiative, getattr(self.active_character, "conditions", [])))
            send_message(self.client_socket, make_update_full_sheet_request(self.active_character.to_dict()))
            
            listen_thread=threading.Thread(target=self.listen_to_server, daemon=True); listen_thread.start()
            self.log_to_chat(f"Connesso a {server_ip} come {self.name} (Lv.{char.level} {char.char_class}).", "Globale")
            self.master.title(f"D&D Client - {self.name}")
            self.status_label.config(text=f"Stato: Connesso a {server_ip}", style="Success.TLabel")
            self.set_controls_state(tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile connettersi a {server_ip}: {e}"); self.is_connected = False

    def process_queue(self):
        try:
            while True:
                msg = self.gui_queue.get_nowait()
                self.handle_server_message(msg)
        except queue.Empty:
            pass
        self.master.after(100, self.process_queue)

    def listen_to_server(self):
        while self.is_connected:
            msg = receive_message(self.client_socket)
            if msg is None: break
            self.gui_queue.put(msg)
        self.is_connected = False
        try:
            self.master.after(0, self.handle_disconnection)
        except RuntimeError:
            pass

    def redraw_map_and_players(self):
        # Pass the full players_data so UI components can access position, conditions, etc.
        players_info = {name: data for name, data in self.players_data.items()}
        all_players = list(self.players_data.values())
        turn_name = ""
        if getattr(self, "combat_active", False) and 0 <= getattr(self, "turn_index", 0) < len(all_players):
            turn_name = all_players[self.turn_index]['name']
        self.map_canvas.update_data(self.local_map_data, players_info, self.name, turn_player_name=turn_name, aoes_data=getattr(self, "aoes_data", []))

    def handle_game_state(self, data):
        self.players_data = {p['name']: p for p in data.get('players', [])}
        self.local_map_data = data.get("map")
        
        was_my_turn = getattr(self, "_is_my_turn", False)
        
        self.combat_active = data.get("combat_active", False)
        self.turn_index = data.get("turn_index", 0)
        self.round_number = data.get("round_number", 1)
        self.aoes_data = data.get("active_aoes", [])
        
        is_my_turn = False
        if self.combat_active:
            all_players_list = data.get('players', [])
            combatants_list = [p for p in all_players_list if p.get('in_combat', True)]
            if 0 <= self.turn_index < len(combatants_list):
                if combatants_list[self.turn_index]['name'] == self.name:
                    is_my_turn = True
        
        self._is_my_turn = is_my_turn
        
        if is_my_turn:
            self.end_turn_btn.pack(fill=tk.X, pady=2, before=self.combat_btn)
            if not was_my_turn:
                self.show_turn_banner()
        else:
            self.end_turn_btn.pack_forget()

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
        
        self.master.after(2000, banner.destroy)

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
        if name in self.players_data:
            self.players_data[name]['position'] = data.get('position')
        self.redraw_map_and_players()

    def handle_player_stats_update(self, data):
        name = data.get('name')
        if name in self.players_data:
            self.players_data[name]['hp'] = data.get('hp')
            self.players_data[name]['max_hp'] = data.get('max_hp')
            self.players_data[name]['initiative'] = data.get('initiative')
            if 'conditions' in data:
                self.players_data[name]['conditions'] = data.get('conditions')
            
        if name == self.name and self.active_character:
            self.active_character.hp_current = data.get('hp')
            self.active_character.hp_max = data.get('max_hp')
            self.active_character.initiative = data.get('initiative')
            if 'conditions' in data:
                self.active_character.conditions = data.get('conditions')
            self.character_manager.save_characters()
            
        self.update_player_listbox()

    def set_controls_state(self, state):
        self.entry.config(state=state); self.roll_button.config(state=state); self.player_listbox.config(state=state); self.stats_button.config(state=state); self.action_button.config(state=state); self.aoe_button.config(state=state); self.travel_button.config(state=state)
        self.combat_btn.config(state=state)

    def request_combat(self):
        from common.protocol import make_start_combat_request
        send_message(self.client_socket, make_start_combat_request(self.name))
        self.log_to_chat("Hai richiesto l'inizio del combattimento al DM.", "Globale", "grey")

    def end_turn(self):
        from common.protocol import make_end_turn_request
        send_message(self.client_socket, make_end_turn_request())
        self.end_turn_btn.pack_forget()

    def open_action_dialog(self):
        self.targeting_mode = True
        messagebox.showinfo("Seleziona Bersaglio", "Clicca sul token del bersaglio direttamente sulla mappa.")
        
    def show_action_dialog_for_target(self, target_name):
        win = tk.Toplevel(self.master)
        win.title(f"Azione su {target_name}")
        win.geometry("300x300")
        from common.theme import apply_modern_window_style
        apply_modern_window_style(win)

        ttk.Label(win, text=f"Bersaglio: {target_name}", font=("Georgia", 12, "bold"), foreground="#D4AF37").pack(pady=(10, 0))

        ttk.Label(win, text="Tipo di Azione:").pack(pady=(10, 0))
        action_var = tk.StringVar(value="damage")
        frame_radio = ttk.Frame(win)
        frame_radio.pack(pady=5)
        ttk.Radiobutton(frame_radio, text="Danno", variable=action_var, value="damage").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(frame_radio, text="Cura", variable=action_var, value="heal").pack(side=tk.LEFT, padx=10)

        ttk.Label(win, text="Formula (es. 1d8+3 oppure 5):").pack(pady=(10, 0))
        formula_entry = ttk.Entry(win, font=self.default_font)
        formula_entry.pack(pady=5, padx=20, fill=tk.X)

        ttk.Label(win, text="Arma / Motivo (Opzionale):").pack(pady=(10, 0))
        reason_entry = ttk.Entry(win, font=self.default_font)
        reason_entry.pack(pady=5, padx=20, fill=tk.X)

        def submit():
            action_type = action_var.get()
            formula = formula_entry.get().strip()
            reason = reason_entry.get().strip()
            
            if not formula:
                messagebox.showerror("Errore", "Devi inserire una formula o un valore numerico.")
                return
                
            send_message(self.client_socket, make_targeted_action_request(target_name, action_type, formula, reason))
            win.destroy()

        ttk.Button(win, text="Esegui Azione", command=submit, style='Primary.TButton').pack(pady=20)

    def on_closing(self):
        if self.is_connected: self.client_socket.close()
        self.master.destroy()

    def handle_disconnection(self):
        messagebox.showinfo("Disconnesso", "La connessione con il server è stata persa."); self.master.title("D&D Client - Disconnesso")
        self.status_label.config(text="Stato: Disconnesso", style="Danger.TLabel"); self.set_controls_state(tk.DISABLED)
        self.local_map_data=None; self.players_data={}; self.update_player_listbox(); self.redraw_map_and_players()

    def handle_server_message(self, msg):
        msg_type=msg.get("type"); data=msg.get("data", {})
        handler_map={
            "ERROR_REPLY": lambda d: messagebox.showerror("Errore dal Server", d.get("text")), 
            "SIMPLE_REPLY": lambda d: self.log_to_chat(f"[SERVER]: {d.get('text')}", "Globale", "lightblue"), 
            "CHAT_BROADCAST": self.handle_chat_broadcast, 
            "GAME_STATE": self.handle_game_state, 
            "PLAYER_JOINED": self.handle_player_joined, 
            "PLAYER_LEFT": self.handle_player_left, 
            "PLAYER_MOVE": self.handle_player_move, 
            "DICE_ROLL_RESULT": self.handle_dice_roll, 
            "PLAYER_STATS_UPDATE": self.handle_player_stats_update,
            "RECEIVE_ITEM": self.handle_receive_item,
            "REQUEST_INITIATIVE": self.handle_request_initiative,
            "PING_BROADCAST": self.handle_ping_broadcast
        }
        handler=handler_map.get(msg_type)
        if handler: handler(data)

    def handle_ping_broadcast(self, data):
        if self.map_canvas:
            self.map_canvas.show_ping(data.get("q"), data.get("r"), data.get("color", "yellow"))

    def handle_request_initiative(self, data):
        win = tk.Toplevel(self.master)
        win.title("Iniziativa")
        win.geometry("300x200")
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
            send_message(self.client_socket, make_submit_initiative(total))
            self.log_to_chat(f"Hai tirato iniziativa: {roll_val} + {mod} = {total}", "Globale", "orange")
            win.destroy()
            
        ttk.Button(win, text="Tira 1d20 + Iniziativa", command=roll, style='Primary.TButton').pack(pady=15)

    def handle_receive_item(self, data):
        item = data.get("item")
        if not self.active_character or not item: return
        
        sender = item.pop("_sender", "Il DM")
        
        # Trova il primo slot libero nella griglia
        for i in range(len(self.active_character.inventory_grid)):
            if self.active_character.inventory_grid[i] is None:
                self.active_character.inventory_grid[i] = item
                self.character_manager.save_characters()
                messagebox.showinfo("Oggetto Ricevuto", f"{sender} ti ha assegnato/inviato: {item['name']}")
                # Invia l'aggiornamento della scheda al server
                send_message(self.client_socket, make_update_full_sheet_request(self.active_character.to_dict()))
                return
        
        messagebox.showwarning("Inventario Pieno", f"{sender} ha provato ad inviarti '{item['name']}' ma non hai spazio nello zaino!")

    def handle_chat_broadcast(self, data):
        sender, text, is_whisper=data.get('sender'), data.get('text'), data.get('is_whisper')
        if not is_whisper: self.log_to_chat(f"[{sender}]: {text}", "Globale", "white")
        else:
            tab_name=sender.replace("Tu -> ", "") if sender.startswith("Tu -> ") else sender
            prefix="Tu" if sender.startswith("Tu -> ") else sender
            self.create_chat_tab(tab_name); self.log_to_chat(f"[{prefix}]: {text}", tab_name, "#87CEFA")

    def handle_dice_roll(self, data):
        res, reason_text=data.get('result', {}), f" ({data.get('reason')})" if data.get('reason') else ""
        log_text=(f"[{data.get('player_name')}] tira {data.get('formula')}{reason_text}: " f"{res.get('rolls')} + {res.get('modifier')} = {res.get('total')}")
        self.log_to_chat(log_text, "Globale", "orange")
    
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
        self.entry.focus_set(); self.log_to_chat(f"Hai aperto una chat con {player_name}.", player_name, "grey")

    def create_chat_tab(self, name):
        if name in self.chat_tabs: return
        tab_frame=ttk.Frame(self.notebook)
        text_widget=scrolledtext.ScrolledText(tab_frame, state='disabled', wrap=tk.WORD, height=8, bg="#1E1E1E", fg="#E0E0E0", borderwidth=0, highlightthickness=0)
        text_widget.pack(fill=tk.BOTH, expand=True); self.notebook.add(tab_frame, text=name); self.chat_tabs[name]=text_widget

    def update_player_listbox(self):
        self.player_listbox.delete(0, tk.END)
        self.player_listbox.insert(tk.END, "DM")
        self.player_listbox.itemconfig(0, {'fg': '#DDA0DD'})
        
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

    def log_to_chat(self, message, tab_name, color="white"):
        text_widget=self.chat_tabs.get(tab_name)
        if not text_widget: return
        text_widget.config(state='normal')
        if color not in text_widget.tag_names(): text_widget.tag_config(color, foreground=color)
        text_widget.insert(tk.END, message + "\n", color)
        text_widget.config(state='disabled'); text_widget.see(tk.END)
        
    def send_chat_message(self, event=None):
        text=self.entry.get().strip()
        if not text: return
        try: active_tab_name=self.notebook.tab(self.notebook.select(), "text")
        except tk.TclError: return
        if active_tab_name == "Globale": send_message(self.client_socket, make_chat(text))
        else: send_message(self.client_socket, make_whisper(active_tab_name, text))
        self.entry.delete(0, tk.END)

    def roll_dice_dialog(self):
        formula=simpledialog.askstring("Tira Dadi", "Inserisci formula (es: 2d6+1):")
        if formula:
            reason=simpledialog.askstring("Motivo", "Motivo del tiro (facoltativo):") or ""
            send_message(self.client_socket, make_roll_request(formula, reason))

    def do_roll(self, formula, reason=""):
        if self.is_connected:
            send_message(self.client_socket, make_roll_request(formula, reason))

    def open_stats_dialog(self):
        if not self.active_character: return
        CharacterSheetUI(self.master, self.active_character, self.character_manager, 
                         on_save_callback=self.on_character_saved, 
                         roll_callback=self.do_roll, 
                         trade_callback=self.do_trade, 
                         players_list_callback=self.get_player_names)

    def do_trade(self, item, target_name):
        if self.is_connected:
            send_message(self.client_socket, make_give_item_request(target_name, item))
            self.log_to_chat(f"Hai inviato l'oggetto '{item.get('name')}' a {target_name}.", "Globale", "lightblue")

    def get_player_names(self):
        return [p for p in self.players_data.keys() if p != self.name]

    def on_character_saved(self, char):
        self.active_character = char
        if self.is_connected:
            send_message(self.client_socket, make_update_stats_request(char.hp_current, char.hp_max, char.initiative, getattr(char, "conditions", [])))
            send_message(self.client_socket, make_update_full_sheet_request(char.to_dict()))

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