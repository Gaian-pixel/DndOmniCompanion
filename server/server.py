# dm_server.py
import socket, threading, queue, tkinter as tk, json, base64, os
from tkinter import messagebox, filedialog, ttk, scrolledtext
from PIL import Image, ImageTk

from common.protocol import *
from server.commands import command_handlers
from common.game_state import GameState, Player
from server.map_editor import MapEditorWindow
from common.hex_utils import Hex
from common.network_utils import send_message, receive_message, broadcast
from components.ui_components import HexMapCanvas

class Server:
    def __init__(self, host, port, gui_queue):
        self.host=host; self.port=port; self.server_socket=None; self.running=False
        self.game_state=GameState(gui_queue)
    def start(self):
        self.server_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port)); self.server_socket.listen(); self.running=True
        while self.running:
            try:
                conn, addr=self.server_socket.accept()
                thread=threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True); thread.start()
            except OSError: break
    def stop(self):
        self.running=False;
        if self.server_socket: self.server_socket.close()
    def handle_client(self, conn, addr):
        print(f"[CONNESSIONE] Nuova connessione da {addr}"); player = None
        try:
            join_msg = receive_message(conn)
            if join_msg is None or join_msg.get("type") != "JOIN":
                return
            name = join_msg["data"]["name"]
            if self.game_state.find_player(name):
                send_message(conn, make_error_reply(f"Il nome '{name}' è già in uso.")); return
            player = Player(name, addr, conn)
            send_message(conn, make_game_state(self.game_state.get_state_dict()))
            broadcast(self.game_state, make_player_joined(player.to_dict()), exclude_player=player)
            self.game_state.add_player(player)
            
            while True:
                msg = receive_message(conn)
                if msg is None: break
                handler = command_handlers.get(msg.get("type"))
                if handler:
                    handler(msg.get("data", {}), player, self.game_state)
                else:
                    send_message(conn, make_error_reply("Comando non riconosciuto."))
        except Exception as e:
            print(f"[ERRORE] nel thread di {addr}: {e}")
        finally:
            if player:
                self.game_state.remove_player(player)
                broadcast(self.game_state, make_player_left(player.name))
            conn.close()

class DM_GUI:
    def __init__(self, master):
        self.master = master; master.configure(bg="#2b2b2b"); self.master.title("Dungeon Master - Server")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.gui_queue=queue.Queue()
        self.server=Server('', 5000, self.gui_queue)
        self.map_canvas = None # Il nostro nuovo componente
        self.notebook = None
        self.chat_tabs = {}
        self.setup_gui()
        self.server_thread=threading.Thread(target=self.server.start, daemon=True); self.server_thread.start()
        self.master.after(100, self.process_queue)

    def setup_gui(self):
        main_frame=tk.Frame(self.master, bg="#2b2b2b", padx=15, pady=15); main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=3); main_frame.columnconfigure(0, weight=1); main_frame.columnconfigure(2, weight=2)
        main_frame.rowconfigure(0, weight=1)
        
        player_frame=tk.LabelFrame(main_frame, text="Avventurieri", padx=10, pady=10, bg="#333333", fg="white"); player_frame.grid(row=0, column=0, sticky="nsew", padx=5)
        self.player_listbox=tk.Listbox(player_frame, bg="#404040", fg="white", selectbackground="#555555", borderwidth=0, highlightthickness=0); self.player_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT); self.player_listbox.bind("<Double-Button-1>", self.open_private_chat_from_list)
        
        map_outer_frame=tk.LabelFrame(main_frame, text="Mappa di Gioco", padx=10, pady=10, bg="#333333", fg="white"); map_outer_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        map_toolbar=tk.Frame(map_outer_frame, bg="#333333"); map_toolbar.pack(fill=tk.X, pady=5)
        tk.Button(map_toolbar, text="Carica Mappa", command=self.load_map_from_file, bg="#007bff", fg="white", activebackground="#0056b3").pack(side=tk.LEFT, padx=5)
        tk.Button(map_toolbar, text="Editor Mappe", command=self.open_map_editor, bg="#17a2b8", fg="white", activebackground="#117a8b").pack(side=tk.LEFT, padx=5)

        self.map_canvas = HexMapCanvas(map_outer_frame)
        self.map_canvas.pack(fill=tk.BOTH, expand=True)
        self.map_canvas.set_on_click_callback(self.on_hex_clicked)
        
        chat_panel=tk.LabelFrame(main_frame, text="Messaggi", padx=10, pady=10, bg="#333333", fg="white"); chat_panel.grid(row=0, column=2, sticky="nsew", padx=5)
        chat_panel.rowconfigure(0, weight=1); chat_panel.columnconfigure(0, weight=1)
        self.notebook = ttk.Notebook(chat_panel); self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        self.create_chat_tab("Sistema")
        self.chat_entry=tk.Entry(chat_panel, bg="#404040", fg="white", insertbackground="white"); self.chat_entry.pack(fill=tk.X, pady=5)
        self.chat_entry.bind("<Return>", lambda e: self.send_dm_chat())
        tk.Button(chat_panel, text="Invia", command=self.send_dm_chat, bg="#007bff", fg="white", activebackground="#0056b3").pack(anchor="e", padx=5)

    def on_hex_clicked(self, clicked_hex):
        if not self.server.game_state.current_map: return
        sel_indices = self.player_listbox.curselection()
        if not sel_indices: return
        
        selected_name = self.player_listbox.get(sel_indices[0])
        map_hexes = {Hex(q, r) for q, r in self.server.game_state.current_map.get("hexes", [])}

        if clicked_hex in map_hexes:
            if self.server.game_state.move_player(selected_name, [clicked_hex.q, clicked_hex.r]):
                broadcast(self.server.game_state, make_player_move(selected_name, [clicked_hex.q, clicked_hex.r]))
                self.redraw_map_and_players()
    
    def redraw_map_and_players(self):
        map_data = self.server.game_state.current_map
        players_data = {p.name: p.position for p in self.server.game_state.get_all_players()}
        self.map_canvas.update_data(map_data, players_data)
        
    def load_map_from_file(self):
        file_path=filedialog.askopenfilename(filetypes=[("Mappe D&D", "*.json")]);
        if not file_path: return
        try:
            with open(file_path, 'r') as f: map_data=json.load(f)
            if 'base_image_path' in map_data and map_data['base_image_path']:
                with open(map_data['base_image_path'], "rb") as image_file:
                    encoded_string=base64.b64encode(image_file.read()).decode('utf-8')
                    map_data['bg_image_data']=encoded_string
            
            self.server.game_state.load_map(map_data)
            self.redraw_map_and_players()
            broadcast(self.server.game_state, make_game_state(self.server.game_state.get_state_dict()))
            self.log_to_chat(f"[SISTEMA] Mappa '{os.path.basename(file_path)}' caricata.")
        except Exception as e:
            messagebox.showerror("Errore Caricamento", f"Impossibile caricare la mappa: {e}")

    def update_player_list(self):
        current_selection=self.player_listbox.curselection()
        self.player_listbox.delete(0, tk.END)
        if self.server.game_state:
            for p in self.server.game_state.get_all_players(): self.player_listbox.insert(tk.END, p.name)
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
                elif msg_type == "PRIVATE_MESSAGE_RECEIVED":
                    payload = msg.get("payload", {})
                    player_name, text = payload.get("from"), payload.get("text")
                    if player_name and text:
                        self.create_chat_tab(player_name)
                        self.log_to_chat(f"[{player_name}]: {text}", tab_name=player_name)
        except queue.Empty: pass
        self.master.after(100, self.process_queue)

    def on_closing(self):
        if messagebox.askokcancel("Esci", "Vuoi chiudere il server?"): self.server.stop(); self.master.destroy()

    def open_map_editor(self):
        editor_window=MapEditorWindow(self.master); editor_window.grab_set()

    def create_chat_tab(self, name):
        if name in self.chat_tabs: return
        tab_frame = tk.Frame(self.notebook, bg="#333333")
        text_widget = scrolledtext.ScrolledText(tab_frame, state='disabled', wrap=tk.WORD, bg="#404040", fg="white", borderwidth=0, highlightthickness=0)
        text_widget.pack(fill=tk.BOTH, expand=True)
        self.notebook.add(tab_frame, text=name)
        self.chat_tabs[name] = text_widget
        
    def open_private_chat_from_list(self, event):
        selected_indices = self.player_listbox.curselection()
        if not selected_indices: return
        player_name = self.player_listbox.get(selected_indices[0])
        self.create_chat_tab(player_name)
        for i, tab in enumerate(self.notebook.tabs()):
            if self.notebook.tab(i, "text") == player_name: self.notebook.select(i); break
        self.chat_entry.focus_set()

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
                send_message(target_player.conn, make_chat_broadcast("DM", text, is_whisper=True))
                self.log_to_chat(f"[Tu -> {active_tab_name}]: {text}", tab_name=active_tab_name)
            else: messagebox.showerror("Errore", f"Giocatore '{active_tab_name}' non più connesso.")
        self.chat_entry.delete(0, tk.END)

    def log_to_chat(self, message, tab_name="Sistema"):
        text_widget = self.chat_tabs.get(tab_name)
        if not text_widget: return
        text_widget.config(state="normal"); text_widget.insert(tk.END, message + "\n")
        text_widget.config(state="disabled"); text_widget.see(tk.END)

if __name__ == "__main__":
    root=tk.Tk()
    DM_GUI(root)
    root.mainloop()