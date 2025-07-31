# client_gui.py
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext, ttk
import socket, threading, json, base64
from io import BytesIO
from PIL import Image, ImageTk

from common.protocol import *
from common.hex_utils import Hex, HexLayout
from common.network_utils import send_message, receive_message
from components.ui_components import HexMapCanvas

class ClientGUI:
    def __init__(self, master):
        self.master=master; master.configure(bg="#2b2b2b"); self.master.title("D&D Client")
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.client_socket=None; self.name=None; self.is_connected=False
        self.players_positions={}; self.local_map_data=None
        self.notebook=None; self.chat_tabs={}; self.player_listbox=None
        self.map_canvas = None
        self.setup_gui()

    def setup_gui(self):
        top_frame=tk.Frame(self.master, bg="#2b2b2b", padx=10, pady=10); top_frame.pack(fill=tk.BOTH, expand=True)
        
        map_frame=tk.LabelFrame(top_frame, text="Mappa", bg="#333333", fg="white", padx=5, pady=5); map_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.map_canvas = HexMapCanvas(map_frame)
        self.map_canvas.pack(fill=tk.BOTH, expand=True)

        player_list_frame=tk.LabelFrame(top_frame, text="In Partita", bg="#333333", fg="white", padx=5, pady=5); player_list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        self.player_listbox=tk.Listbox(player_list_frame, width=20, bg="#404040", fg="white", selectbackground="#555555", borderwidth=0, highlightthickness=0); self.player_listbox.pack(fill=tk.Y, expand=True); self.player_listbox.bind("<Double-Button-1>", self.open_private_chat_from_list)
        tk.Label(player_list_frame, text="Doppio click per chattare", font=("", 8, "italic"), bg="#333333", fg="grey").pack()
        
        bottom_frame=tk.Frame(self.master, bg="#2b2b2b", padx=10, pady=5); bottom_frame.pack(fill=tk.X)
        conn_frame=tk.LabelFrame(bottom_frame, text="Connessione", bg="#333333", fg="white", padx=10, pady=10); conn_frame.pack(fill=tk.X, pady=5)
        self.connect_button=tk.Button(conn_frame, text="Connetti al Server", command=self.connect_to_server, bg="#007bff", fg="white", activebackground="#0056b3"); self.connect_button.pack(pady=5)
        self.status_label=tk.Label(conn_frame, text="Stato: Disconnesso", fg="red", bg="#333333"); self.status_label.pack(pady=5)
        action_frame=tk.LabelFrame(bottom_frame, text="Azioni e Chat", bg="#333333", fg="white", padx=10, pady=10); action_frame.pack(fill=tk.X, pady=5)
        self.notebook=ttk.Notebook(action_frame); self.create_chat_tab("Global"); self.notebook.pack(fill=tk.X, expand=True, pady=5)
        self.entry=tk.Entry(action_frame, bg="#404040", fg="white", insertbackground="white"); self.entry.pack(fill=tk.X, pady=(0, 5)); self.entry.bind("<Return>", self.send_chat_message)
        self.roll_button=tk.Button(action_frame, text="Tira Dadi", command=self.roll_dice_dialog, bg="#6c757d", fg="white", activebackground="#5a6268"); self.roll_button.pack(pady=5)
        self.set_controls_state(tk.DISABLED)

    def connect_to_server(self):
        if self.is_connected: return
        server_ip=simpledialog.askstring("Connessione", "IP del server:", initialvalue="127.0.0.1")
        if not server_ip: return
        self.name=simpledialog.askstring("Nome", "Il tuo nome:")
        if not self.name: return
        try:
            self.client_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((server_ip, 5000)); self.is_connected = True
            send_message(self.client_socket, make_join(self.name))
            listen_thread=threading.Thread(target=self.listen_to_server, daemon=True); listen_thread.start()
            self.log_to_chat(f"Connesso a {server_ip} come {self.name}.", "Global")
            self.master.title(f"D&D Client - {self.name}")
            self.status_label.config(text=f"Stato: Connesso a {server_ip}", fg="lightgreen")
            self.connect_button.config(state=tk.DISABLED); self.set_controls_state(tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile connettersi a {server_ip}: {e}"); self.is_connected = False

    def listen_to_server(self):
        while self.is_connected:
            msg = receive_message(self.client_socket)
            if msg is None: break
            self.master.after(0, self.handle_server_message, msg)
        self.is_connected = False
        self.master.after(0, self.handle_disconnection)

    def redraw_map_and_players(self):
        players_data = self.players_positions
        self.map_canvas.update_data(self.local_map_data, players_data, self.name)

    def handle_game_state(self, data):
        self.players_positions = {p['name']: p['position'] for p in data.get('players', [])}
        self.local_map_data = data.get("map")
        self.update_player_listbox()
        self.redraw_map_and_players()

    def handle_player_joined(self, data):
        self.players_positions[data.get('name')] = data.get('position')
        self.update_player_listbox()
        self.redraw_map_and_players()

    def handle_player_left(self, data):
        name = data.get('name')
        if name in self.players_positions: del self.players_positions[name]
        self.update_player_listbox()
        self.redraw_map_and_players()

    def handle_player_move(self, data):
        self.players_positions[data.get('name')] = data.get('position')
        self.redraw_map_and_players()

    def set_controls_state(self, state):
        self.entry.config(state=state); self.roll_button.config(state=state); self.player_listbox.config(state=state)

    def on_closing(self):
        if self.is_connected: self.client_socket.close()
        self.master.destroy()

    def handle_disconnection(self):
        messagebox.showinfo("Disconnesso", "La connessione con il server è stata persa."); self.master.title("D&D Client - Disconnesso")
        self.status_label.config(text="Stato: Disconnesso", fg="red"); self.connect_button.config(state=tk.NORMAL); self.set_controls_state(tk.DISABLED)
        self.local_map_data=None; self.players_positions={}; self.update_player_listbox(); self.redraw_map_and_players()

    def handle_server_message(self, msg):
        msg_type=msg.get("type"); data=msg.get("data", {})
        handler_map={"ERROR_REPLY": lambda d: messagebox.showerror("Errore dal Server", d.get("text")), "SIMPLE_REPLY": lambda d: self.log_to_chat(f"[SERVER]: {d.get('text')}", "Global", "lightblue"), "CHAT_BROADCAST": self.handle_chat_broadcast, "GAME_STATE": self.handle_game_state, "PLAYER_JOINED": self.handle_player_joined, "PLAYER_LEFT": self.handle_player_left, "PLAYER_MOVE": self.handle_player_move, "DICE_ROLL_RESULT": self.handle_dice_roll}
        handler=handler_map.get(msg_type)
        if handler: handler(data)

    def handle_chat_broadcast(self, data):
        sender, text, is_whisper=data.get('sender'), data.get('text'), data.get('is_whisper')
        if not is_whisper: self.log_to_chat(f"[{sender}]: {text}", "Global", "white")
        else:
            tab_name=sender.replace("Tu -> ", "") if sender.startswith("Tu -> ") else sender
            prefix="Tu" if sender.startswith("Tu -> ") else sender
            self.create_chat_tab(tab_name); self.log_to_chat(f"[{prefix}]: {text}", tab_name, "#87CEFA")

    def handle_dice_roll(self, data):
        res, reason_text=data.get('result', {}), f" ({data.get('reason')})" if data.get('reason') else ""
        log_text=(f"[{data.get('player_name')}] tira {data.get('formula')}{reason_text}: " f"{res.get('rolls')} + {res.get('modifier')} = {res.get('total')}")
        self.log_to_chat(log_text, "Global", "orange")
    
    def open_private_chat_from_list(self, event):
        selected_indices=self.player_listbox.curselection();
        if not selected_indices: return
        player_name=self.player_listbox.get(selected_indices[0]); self.create_chat_tab(player_name)
        for i, tab_text in enumerate(self.notebook.tabs()):
            if self.notebook.tab(i, "text") == player_name: self.notebook.select(i); break
        self.entry.focus_set(); self.log_to_chat(f"Hai aperto una chat con {player_name}.", player_name, "grey")

    def create_chat_tab(self, name):
        if name in self.chat_tabs: return
        tab_frame=tk.Frame(self.notebook, bg="#333333")
        text_widget=scrolledtext.ScrolledText(tab_frame, state='disabled', wrap=tk.WORD, height=8, bg="#404040", fg="white", borderwidth=0, highlightthickness=0)
        text_widget.pack(fill=tk.BOTH, expand=True); self.notebook.add(tab_frame, text=name); self.chat_tabs[name]=text_widget

    def update_player_listbox(self):
        self.player_listbox.delete(0, tk.END); self.player_listbox.insert(tk.END, "DM"); self.player_listbox.itemconfig(0, {'fg': '#DDA0DD'})
        other_players=sorted([name for name in self.players_positions if name != self.name])
        for name in other_players: self.player_listbox.insert(tk.END, name)

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
        if active_tab_name == "Global": send_message(self.client_socket, make_chat(text))
        else: send_message(self.client_socket, make_whisper(active_tab_name, text))
        self.entry.delete(0, tk.END)

    def roll_dice_dialog(self):
        formula=simpledialog.askstring("Tira Dadi", "Inserisci formula (es: 2d6+1):")
        if formula:
            reason=simpledialog.askstring("Motivo", "Motivo del tiro (facoltativo):") or ""
            send_message(self.client_socket, make_roll_request(formula, reason))

if __name__ == "__main__":
    root=tk.Tk()
    ClientGUI(root)
    root.mainloop()