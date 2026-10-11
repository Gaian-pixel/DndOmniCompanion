import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import queue
# client_gui.py
import tkinter as tk
from common.messagebox import messagebox
from tkinter import simpledialog, scrolledtext, ttk
import socket
import threading
import json
import base64
from io import BytesIO
from PIL import Image, ImageTk

from common.protocol import *
from common.hex_utils import Hex, HexLayout
from common.network_utils import send_message, receive_message
from components.ui_components import HexMapCanvas, ToolTip
from client.character_manager import CharacterManager
from client.login_ui import LoginDialog
from client.character_sheet_ui import CharacterSheetUI
from client.voice_client import VoiceClient

from common.theme import setup_theme, apply_modern_window_style
from .network import ClientNetwork

class ClientGUI:
    def __init__(self, master):
        self.master = master
        setup_theme(master)
        self.master.title("D&D Client")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.name=None; self.is_connected=False
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
        self.voice_client = None
        self.network = ClientNetwork(self.gui_queue, lambda: self.master.after(0, self.handle_disconnection))
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
        
        # 2. LAYOUT PRINCIPALE (3 Colonne: Sinistra=Toolbar, Centro=Mappa, Destra=Notebook)
        main_frame = ttk.Frame(self.master, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=0) # Barra strumenti mappa a sinistra
        main_frame.columnconfigure(1, weight=1) # Mappa
        main_frame.columnconfigure(2, weight=0) # Pannello destro per i Tab
        main_frame.rowconfigure(0, weight=1)
        
        # --- COLONNA 0: LEFT TOOLBAR (Strumenti Mappa) ---
        left_panel = ttk.Frame(main_frame, width=40)
        left_panel.grid(row=0, column=0, sticky="ns", padx=(0, 5))
        
        self.center_map_btn = ttk.Button(left_panel, text=' 👆 ', width=3, command=lambda: self.map_canvas.center_view())
        self.center_map_btn.pack(pady=2)
        ToolTip(self.center_map_btn, "Centra Mappa")
        
        self.aoe_button = ttk.Button(left_panel, text=" 💥 ", width=3, command=self.open_aoe_dialog)
        self.aoe_button.pack(pady=2)
        ToolTip(self.aoe_button, "Area di Effetto")
        
        self.measure_btn = ttk.Button(left_panel, text=" 📏 ", width=3)
        self.measure_btn.pack(pady=2)
        ToolTip(self.measure_btn, "Misura Distanza")
        
        # --- COLONNA 1: MAPPA ---
        map_outer_frame = ttk.Frame(main_frame)
        map_outer_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        
        self.map_canvas = HexMapCanvas(map_outer_frame, bg="#1e1e1e")
        self.map_canvas.pack(fill=tk.BOTH, expand=True)
        self.aoe_mode = False
        self.aoe_params = None
        self.map_canvas.set_on_click_callback(self.on_hex_click)
        self.map_canvas.on_token_drop_callback = self.on_token_drop
        self.map_canvas.set_on_ping_callback(self.on_ping_callback)
        self.map_canvas.set_on_hex_right_click_callback(self.on_hex_right_clicked)
        self.map_canvas.set_on_wall_toggle_callback(self.on_wall_toggle_callback)
        self.map_canvas.set_on_cover_toggle_callback(self.on_cover_toggle_callback)
        self.map_canvas.set_on_draw_callback(self.on_draw_request)
        
        # --- COLONNA 2: RIGHT SIDEBAR (Notebook) ---
        right_panel = ttk.Frame(main_frame, width=350)
        right_panel.grid(row=0, column=2, sticky="ns", padx=(5, 0))
        right_panel.pack_propagate(False) # Mantieni la larghezza fissa a 350
        
        self.right_notebook = ttk.Notebook(right_panel)
        self.right_notebook.pack(fill=tk.BOTH, expand=True)
        
        # --- TAB 1: CHAT ---
        chat_tab = ttk.Frame(self.right_notebook)
        self.right_notebook.add(chat_tab, text="Chat")
        
        ttk.Label(chat_tab, text="Compagnia", font=self.default_font, foreground="#E0E0E0").pack(anchor="w", padx=5, pady=(5,0))
        ttk.Label(chat_tab, text="Doppio click per chattare", style="Muted.TLabel").pack(anchor="w", padx=5)
        
        self.player_listbox = tk.Listbox(chat_tab, font=self.default_font, relief="flat", bg="#1e1e1e", fg="white", height=6)
        self.player_listbox.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.player_listbox.bind("<Double-Button-1>", self.open_private_chat_from_list)
        
        self.notebook = ttk.Notebook(chat_tab)
        self.create_chat_tab("Globale")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        
        chat_cmd_frame = ttk.Frame(chat_tab)
        chat_cmd_frame.pack(fill=tk.X, padx=5, pady=(2, 5))
        self.entry = ttk.Entry(chat_cmd_frame, font=self.default_font)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry.bind("<Return>", self.send_chat_message)
        ttk.Button(chat_cmd_frame, text="Invia", command=self.send_chat_message).pack(side=tk.LEFT)

        self.voice_controls_frame = tk.Frame(chat_tab, bg="#292B2F", pady=5, padx=5)
        self.voice_controls_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(self.voice_controls_frame, text="Voice Channel: Disconnesso", bg="#292B2F", fg="#8E9297", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        self.btn_deafen = tk.Button(self.voice_controls_frame, text=" 🎧 ", bg="#36393F", fg="white", relief=tk.FLAT, command=self.toggle_deafen)
        self.btn_deafen.pack(side=tk.RIGHT, padx=2)
        self.btn_mute = tk.Button(self.voice_controls_frame, text=" 🎤 ", bg="#36393F", fg="white", relief=tk.FLAT, command=self.toggle_mute)
        self.btn_mute.pack(side=tk.RIGHT, padx=2)
        
        # --- TAB 2: CONTROLLI PG ---
        controls_tab = ttk.Frame(self.right_notebook, padding=10)
        self.right_notebook.add(controls_tab, text="Controlli PG")
        
        self.status_label = ttk.Label(controls_tab, text="Stato: Disconnesso", style="Danger.TLabel", font=self.default_font)
        self.status_label.pack(anchor="w", pady=(0, 10))
        
        ttk.Label(controls_tab, text="Personaggio Attivo:").pack(anchor="w")
        self.active_character_var = tk.StringVar(value=self.name)
        self.active_character_combo = ttk.Combobox(controls_tab, textvariable=self.active_character_var, state="readonly")
        self.active_character_combo.pack(fill=tk.X, pady=(0, 15))
        self.active_character_combo.bind("<<ComboboxSelected>>", self.on_active_character_changed)
        
        self.stats_button = ttk.Button(controls_tab, text="Scheda PG", command=self.open_stats_dialog, style='Info.TButton')
        self.stats_button.pack(fill=tk.X, pady=2)
        
        self.roll_button = ttk.Button(controls_tab, text="Tira Dadi", command=getattr(self, "roll_dice_dialog", lambda: None))
        self.roll_button.pack(fill=tk.X, pady=2)
        
        self.action_button = ttk.Button(controls_tab, text="Azione (Attacco/Cura)", command=getattr(self, "open_action_dialog", lambda: None))
        self.action_button.pack(fill=tk.X, pady=2)
        
        self.travel_button = ttk.Button(controls_tab, text="Azioni di Viaggio", command=getattr(self, "open_travel_dialog", lambda: None))
        self.travel_button.pack(fill=tk.X, pady=2)
        
        self.combat_btn = ttk.Button(controls_tab, text="Richiedi Combattimento", command=lambda: getattr(self, "network", None) and self.network.send({"type": "COMBAT_TOGGLE_REQUEST", "data": {}}))
        self.combat_btn.pack(fill=tk.X, pady=2)
        
        self.end_turn_btn = ttk.Button(controls_tab, text="Termina Turno", command=self.end_turn, style='Danger.TButton')
        
        # Hotbar al fondo del right_panel
        self.hotbar_frame = ttk.Frame(self.right_notebook.master) # right_panel is the parent of right_notebook
        self.hotbar_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5, padx=5)
        self.hotbar_buttons = []
        for i in range(10):
            btn = ttk.Button(self.hotbar_frame, text=f"{i+1}", width=4)
            btn.grid(row=0, column=i, padx=1)
            btn.bind("<Button-1>", lambda e, idx=i: getattr(self, "on_hotbar_click")(idx))
            btn.bind("<Button-3>", lambda e, idx=i: getattr(self, "on_hotbar_right_click")(idx))
            self.hotbar_buttons.append(btn)
        

        self.set_controls_state(tk.DISABLED)


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
    def on_hotbar_right_click(self, idx):
        if not self.active_character: return
        cmd = simpledialog.askstring("Hotbar", f"Imposta comando per lo slot {idx+1} (es: 1d20+5, oppure Ciao!)", initialvalue=self.active_character.hotbar[idx])
        if cmd is not None:
            self.active_character.hotbar[idx] = cmd
            self.hotbar_buttons[idx].config(text=cmd[:10] if cmd else f"{idx+1}")
            self.character_manager.save_characters()

    def on_hotbar_click(self, idx):
        if not self.active_character: return
        cmd = self.active_character.hotbar[idx]
        if not cmd: return
        if "d" in cmd and cmd[0].isdigit(): # basic check for roll
            self.do_roll(cmd, f"Hotbar {idx+1}")
        else:
            # Set the entry text and call send_chat_message to respect the active tab
            self.entry.delete(0, tk.END)
            self.entry.insert(0, cmd)
            self.send_chat_message()


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
        if token_name == self.name:
            self.send_message({"type": "MOVE_REQUEST", "data": {"to": [q, r]}})

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
            menu.add_command(label="Visualizza Scheda", command=self.open_stats_dialog)
            
        def _open_priv():
            self.open_private_chat_from_list(None)
            
        menu.add_command(label="Invia Messaggio Privato", command=_open_priv)
        
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
                
            from common.protocol import make_create_aoe_request
            self.network.send(make_create_aoe_request(aoe_data))
            self.aoe_mode = False
            messagebox.showinfo("AoE Piazzata", "L'area d'effetto è stata piazzata sulla mappa.")
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
                self.network.send(make_attack_request(target_name, params["weapon_name"], params["hit_bonus"], params["damage_formula"]))
                messagebox.showinfo("Attacco Inviato", f"Attacco contro {target_name} inviato!")
            else:
                messagebox.showinfo("Nessun Bersaglio", "Non c'e' nessuno in questo esagono.")
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
            loots = getattr(self, "map_data", {}).get("loots", []) if getattr(self, "map_data", None) else []
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

    def on_attack_action(self, weapon_name, hit_bonus, damage_formula):
        self.attack_targeting_mode = True
        self.attack_params = {
            "weapon_name": weapon_name,
            "hit_bonus": hit_bonus,
            "damage_formula": damage_formula
        }
        messagebox.showinfo("Modalita' Bersaglio", f"Seleziona un bersaglio sulla mappa per attaccare con {weapon_name}!")



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
            win = QuestLogDialog(self.master, self.game_state, is_dm=False, network_or_server=self.network)
        except Exception as e:
            from common.messagebox import messagebox
            messagebox.showerror("Errore", f"Impossibile aprire il diario: {e}")

    def open_shop_dialog(self):
        try:
            from components.shop_ui import ShopDialog
            win = ShopDialog(self.master, self.game_state, is_dm=False, network_or_server=self.network)
        except Exception as e:
            from common.messagebox import messagebox
            messagebox.showerror("Errore", f"Impossibile aprire i negozi: {e}")

    def open_travel_dialog(self):
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        win.title("Ruolo di Viaggio")
        win.minsize(300, 250)
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
            self.network.send(make_set_travel_role_request(role))
            win.destroy()
            
        ttk.Button(win, text="Conferma", command=submit, style='Success.TButton').pack(pady=15)

    def open_aoe_dialog(self):
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        win.title("Lancia Incantesimo / AoE")
        win.minsize(300, 250)
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
            
        ttk.Separator(win, orient="horizontal").pack(fill="x", pady=10)
        
        req_save_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(win, text="Richiede Tiro Salvezza (Danni Automatici)", variable=req_save_var).pack(pady=2)
        
        save_frame = ttk.Frame(win)
        save_frame.pack(pady=5)
        
        ttk.Label(save_frame, text="Stat:").grid(row=0, column=0, padx=2)
        stat_var = tk.StringVar(value="DES")
        ttk.Combobox(save_frame, textvariable=stat_var, values=["FOR", "DES", "COS", "INT", "SAG", "CAR"], width=5).grid(row=0, column=1, padx=2)
        
        ttk.Label(save_frame, text="CD:").grid(row=0, column=2, padx=2)
        dc_entry = ttk.Entry(save_frame, width=5)
        dc_entry.insert(0, "15")
        dc_entry.grid(row=0, column=3, padx=2)
        
        ttk.Label(save_frame, text="Danni:").grid(row=1, column=0, padx=2, pady=5)
        dmg_entry = ttk.Entry(save_frame, width=8)
        dmg_entry.insert(0, "8d6")
        dmg_entry.grid(row=1, column=1, padx=2, pady=5)
        
        half_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(save_frame, text="Dimezza Danni", variable=half_var).grid(row=1, column=2, columnspan=2, padx=2)
            
        def submit():
            try:
                sz = int(size_entry.get())
            except:
                sz = 3
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
            messagebox.showinfo("AoE", "Clicca sulla mappa per confermare il bersaglio / centro dell'area d'effetto.")
            win.destroy()
            
        ttk.Button(win, text="Prepara Lancio", command=submit).pack(pady=15)

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
            
            # Start Voice Client
            self.voice_client = VoiceClient(server_ip, 53912)
            self.voice_client.start()
            
            self.network.send(make_join(self.name, getattr(self.active_character, "last_position", None)))
            self.network.send(make_update_stats_request(self.active_character.hp_current, self.active_character.hp_max, self.active_character.initiative, getattr(self.active_character, "conditions", [])))
            self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
            self.log_to_chat(f"Connesso a {server_ip} come {self.name} (Lv.{char.level} {char.char_class}).", "Globale")
            self.master.title(f"D&D Client - {self.name}")
            self.status_label.config(text=f"Stato: Connesso a {server_ip}", style="Success.TLabel")
            self.set_controls_state(tk.NORMAL)
            for i in range(10):
                cmd = self.active_character.hotbar[i]
                self.hotbar_buttons[i].config(text=cmd[:10] if cmd else f"{i+1}")
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

    def redraw_map_and_players(self):
        # Pass the full players_data so UI components can access position, conditions, etc.
        players_info = {}
        for name, data in self.players_data.items():
            if data.get("is_hidden", False) and name != self.name:
                continue
            players_info[name] = data
            
        all_players = list(self.players_data.values())
        turn_name = ""
        if getattr(self, "combat_active", False) and 0 <= getattr(self, "turn_index", 0) < len(all_players):
            turn_name = all_players[self.turn_index]['name']
        
        time_hour = self.game_state.get("time_hour", 12) if self.game_state else 12
        weather = self.game_state.get("weather", "Sereno") if self.game_state else "Sereno"
        combat_active = self.combat_active
        combat_order = [p["name"] for p in all_players] if combat_active else []
        
        self.map_canvas.update_data(
            self.local_map_data, 
            players_info, 
            self.name, 
            turn_player_name=turn_name, 
            aoes_data=getattr(self, "aoes_data", []),
            time_hour=time_hour,
            weather=weather,
            combat_active=combat_active,
            combat_order=combat_order
        )

    def handle_map_data_update(self, data):
        self.local_map_data = data.get("map")
        self.redraw_map_and_players()
        
    def handle_combat_state_update(self, data):
        self.combat_active = data.get("combat_active", False)
        self.turn_index = data.get("turn_index", 0)
        self.round_number = data.get("round_number", 1)
        self.aoes_data = data.get("active_aoes", [])
        
        # update my turn indicator
        was_my_turn = getattr(self, "_is_my_turn", False)
        is_my_turn = False
        if self.combat_active:
            # We don't have the ordered list easily here unless we sort it.
            # But wait, in GAME_STATE we did this:
            # all_players_list = data.get('players', [])
            # In COMBAT_STATE_UPDATE, maybe we don't have players list. 
            # If server sends turn_player_name it would be easier.
            pass # We will rely on server sending GAME_STATE on turn change, or handle it better.
        self.update_player_listbox()
        self.redraw_map_and_players()

    def handle_game_state(self, data):
        self.game_state = data
        self.players_data = {p['name']: p for p in data.get('players', [])}
        self.local_map_data = data.get("map")
        
        if self.active_character and self.name in self.players_data:
            pos = self.players_data[self.name].get("position")
            if pos:
                self.active_character.last_position = pos
                self.character_manager.save_characters()
        
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
        if name == self.name and self.active_character:
            self.active_character.last_position = data.get('position')
            self.character_manager.save_characters()
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
            
            if hasattr(self, 'stats_window') and self.stats_window.winfo_exists():
                self.stats_window.update_dynamic_stats()
            
        self.update_player_listbox()

    def set_controls_state(self, state):
        for btn in ['entry', 'roll_button', 'player_listbox', 'stats_button', 'action_button', 'aoe_button', 'travel_button', 'calendar_button', 'combat_btn', 'end_turn_btn']:
            widget = getattr(self, btn, None)
            if widget:
                try: widget.config(state=state)
                except: pass


    def request_combat(self):
        from common.protocol import make_start_combat_request
        self.network.send(make_start_combat_request(self.name))
        self.log_to_chat("Hai richiesto l'inizio del combattimento al DM.", "Globale", "grey")

    def end_turn(self):
        from common.protocol import make_end_turn_request
        self.network.send(make_end_turn_request())
        self.end_turn_btn.pack_forget()

    def open_action_dialog(self):
        self.targeting_mode = True
        messagebox.showinfo("Seleziona Bersaglio", "Clicca sul token del bersaglio direttamente sulla mappa.")
        
    def show_action_dialog_for_target(self, target_name):
        win = tk.Toplevel(self.master)
        win.transient(self.master)
        win.grab_set()
        win.title(f"Azione su {target_name}")
        win.minsize(300, 300)
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
                
            self.network.send(make_targeted_action_request(target_name, action_type, formula, reason))
            win.destroy()

        ttk.Button(win, text="Esegui Azione", command=submit, style='Primary.TButton').pack(pady=20)

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

    def on_closing(self):
        if getattr(self, "voice_client", None): self.voice_client.stop()
        if self.is_connected: self.network.disconnect()
        self.master.destroy()

    def handle_disconnection(self):
        if self.voice_client: self.voice_client.stop()
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
            "PROMPT_LONG_REST_VOTE": self.handle_prompt_long_rest_vote,
            "DO_LONG_REST": self.handle_do_long_rest,
            "FOW_UPDATE_BROADCAST": self.handle_fow_update_broadcast,
            "AUDIO_PLAY_BROADCAST": self.handle_audio_play,
            "CUSTOM_SPELL_RESPONSE": self.handle_custom_spell_response,
            "CAMPAIGN_STARTER_GRANTED": self.handle_campaign_starter_granted
        }
        handler=handler_map.get(msg_type)
        if handler: handler(data)

    def handle_custom_spell_response(self, data):
        approved = data.get("approved", False)
        spell = data.get("spell", {})
        spell_name = spell.get("name", "Incantesimo")
        if approved:
            if self.active_character:
                if not hasattr(self.active_character, "spellbook") or not isinstance(self.active_character.spellbook, list):
                    self.active_character.spellbook = []
                if not any(s.get("name") == spell_name for s in self.active_character.spellbook):
                    self.active_character.spellbook.append(spell)
                    self.character_manager.save_characters()
                    if hasattr(self, 'stats_window') and self.stats_window and self.stats_window.winfo_exists():
                        self.stats_window.refresh_spell_list()
                    from common.protocol import make_update_full_sheet_request
                    self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
            messagebox.showinfo("Incantesimo Approvato!", f"Il Dungeon Master ha APPROVATO l'incantesimo '{spell_name}'!\nÈ stato aggiunto al tuo Grimorio.")
        else:
            reason = data.get("reason", "Il Master ha respinto la richiesta.")
            messagebox.showwarning("Incantesimo Rifiutato", f"Il Dungeon Master ha RESPINTO '{spell_name}'.\nMotivo: {reason}")

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

    def handle_audio_play(self, data):
        import webbrowser
        url = data.get("url")
        if url:
            webbrowser.open(url)
            self.log_to_chat("Stai ascoltando un audio avviato dal DM", "Globale", sender="Sistema", color="#99AAB5")

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
            messagebox.showinfo("Riposo Lungo Completato", "Il gruppo ha completato un Riposo Lungo. Hai recuperato le tue statistiche.")
            if getattr(self, "sheet_ui", None) and self.sheet_ui.winfo_exists():
                self.sheet_ui.load_data()

    def handle_draw_broadcast(self, data):
        points = data.get("points", [])
        color = data.get("color", "red")
        if hasattr(self, "map_canvas"):
            self.map_canvas.draw_remote_line(points, color)

    def handle_handout_broadcast(self, data):
        title = data.get("title", "Handout dal DM")
        img_b64 = data.get("image_b64")
        content = data.get("content")
        
        try:
            import tkinter as tk
            from tkinter import ttk
            
            top = tk.Toplevel(self.master)
            top.transient(self.master)
            top.grab_set()
            top.title(title)
            
            if img_b64:
                import base64
                from io import BytesIO
                from PIL import Image, ImageTk
                
                img_bytes = base64.b64decode(img_b64)
                img = Image.open(BytesIO(img_bytes))
                
                top.update_idletasks()
                width, height = img.width, img.height
                x = (top.winfo_screenwidth() // 2) - (width // 2)
                y = (top.winfo_screenheight() // 2) - (height // 2)
                top.geometry(f"{width}x{height}+{x}+{y}")
                
                tk_img = ImageTk.PhotoImage(img)
                lbl = tk.Label(top, image=tk_img)
                lbl.image = tk_img # keep reference
                lbl.pack(fill=tk.BOTH, expand=True)
            elif content:
                top.minsize(400, 300)
                txt = tk.Text(top, font=("Georgia", 14), wrap="word", bg="#f4ecd8", fg="#3e2723", padx=20, pady=20)
                txt.insert("1.0", content)
                txt.config(state=tk.DISABLED)
                txt.pack(fill=tk.BOTH, expand=True)
            
            top.focus_force()
            
        except Exception as e:
            print("Errore handout:", e)

    def handle_ping_broadcast(self, data):
        if self.map_canvas:
            self.map_canvas.draw_ping(data.get("q"), data.get("r"), data.get("color", "red"))

    def handle_fow_update_broadcast(self, data):
        if hasattr(self, 'map_data') and self.map_data:
            self.map_data["fow_revealed"] = data.get("fow_revealed", [])
            self.map_data["fow_draft"] = data.get("fow_draft", [])
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

    def handle_receive_gold(self, data):
        amount = data.get("amount", 0)
        if not self.active_character: return
        
        if not hasattr(self.active_character, "currency") or not isinstance(self.active_character.currency, dict):
            self.active_character.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
            
        self.active_character.currency["MO"] = self.active_character.currency.get("MO", 0) + amount
        
        self.character_manager.save_characters()
        from common.protocol import make_update_full_sheet_request
        self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
        
        if hasattr(self, "sheet_ui") and self.sheet_ui.winfo_exists():
            self.sheet_ui.load_data()
            
        messagebox.showinfo("Loot Ricevuto", f"Il DM ha distribuito il loot! Hai ricevuto {amount} MO.")

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
                self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
                return
        
        messagebox.showwarning("Inventario Pieno", f"{sender} ha provato ad inviarti '{item['name']}' ma non hai spazio nello zaino!")

    def handle_chat_broadcast(self, data):
        sender, text, is_whisper=data.get('sender'), data.get('text'), data.get('is_whisper')
        if not is_whisper: self.log_to_chat(text, "Globale", sender=sender, color="#5865F2")
        else:
            tab_name=sender.replace("Tu -> ", "") if sender.startswith("Tu -> ") else sender
            prefix="Tu" if sender.startswith("Tu -> ") else sender
            self.create_chat_tab(tab_name)
            self.log_to_chat(text, tab_name, sender=prefix, color="#EB459E")

    def handle_dice_roll(self, data):
        res, reason_text=data.get('result', {}), f" ({data.get('reason')})" if data.get('reason') else ""
        log_text=(f"tira {data.get('formula')}{reason_text}: " f"{res.get('rolls')} + {res.get('modifier')} = {res.get('total')}")
        self.log_to_chat(log_text, "Globale", sender=data.get('player_name'), color="#FEE75C")
    
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
        tab_frame=ttk.Frame(self.notebook)
        text_widget=scrolledtext.ScrolledText(tab_frame, state='disabled', wrap=tk.WORD, height=8, bg="#36393F", fg="#DCDDDE", borderwidth=0, highlightthickness=0, font=("Arial", 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(tab_frame, text=name)
        self.chat_tabs[name]=text_widget
        
        # Configure tags for Discord-like format
        text_widget.tag_config("timestamp", foreground="#72767D", font=("Arial", 8))
        text_widget.tag_config("sender", font=("Arial", 10, "bold"))
        text_widget.tag_config("text", foreground="#DCDDDE")

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

    def log_to_chat(self, message, tab_name, sender="Sistema", color="white"):
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
        
    def send_chat_message(self, event=None):
        text=self.entry.get().strip()
        if not text: return
        try: active_tab_name=self.notebook.tab(self.notebook.select(), "text")
        except tk.TclError: return
        if active_tab_name == "Globale": self.network.send(make_chat(text))
        else: self.network.send(make_whisper(active_tab_name, text))
        self.entry.delete(0, tk.END)

    def roll_dice_dialog(self):
        formula=simpledialog.askstring("Tira Dadi", "Inserisci formula (es: 2d6+1):")
        if formula:
            reason=simpledialog.askstring("Motivo", "Motivo del tiro (facoltativo):") or ""
            self.network.send(make_roll_request(formula, reason))

    def do_roll(self, formula, reason=""):
        if self.is_connected:
            self.network.send(make_roll_request(formula, reason))

    def open_stats_dialog(self):
        if not self.active_character: return
        self.stats_window = CharacterSheetUI(self.master, self.active_character, self.character_manager, 
                         on_save_callback=self.on_character_saved, 
                         roll_callback=self.do_roll, 
                         trade_callback=self.do_trade, attack_callback=self.on_attack_action, 
                         players_list_callback=self.get_player_names,
                         custom_spell_request_callback=self.request_custom_spell,
                         is_connected=self.is_connected)

    def do_trade(self, item, target_name):
        if self.is_connected:
            self.network.send(make_give_item_request(target_name, item))
            self.log_to_chat(f"Hai inviato l'oggetto '{item.get('name')}' a {target_name}.", "Globale", sender="Sistema", color="#00B0F4")

    def get_player_names(self):
        return [p for p in self.players_data.keys() if p != self.name]

    def handle_prompt_save(self, data):
        stat = data.get("stat")
        dc = data.get("dc")
        damage_formula = data.get("damage_formula")
        half_on_success = data.get("half_on_success")
        source_name = data.get("source_name")
        
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
                attr = self.active_character.attributes
                if stat in attr:
                    mod = (int(attr[stat]) - 10) // 2
                    
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            res = roll_dice(f"1d20{mod_str}")
            
            is_crit = res["rolls"][0] == 20
            is_fail = res["rolls"][0] == 1
            
            from common.protocol import make_save_result
            self.network.send(make_save_result(stat, res["total"], is_crit, is_fail, dc, damage_formula, half_on_success, source_name))
            win.destroy()
            
        ttk.Button(win, text=f"Tira Salvezza ({stat})", command=do_roll, style="Danger.TButton").pack(pady=20)

    def on_character_saved(self, char):
        self.active_character = char
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
    def toggle_mute(self):
        print("Mute toggled")

    def toggle_deafen(self):
        print("Deafen toggled")
