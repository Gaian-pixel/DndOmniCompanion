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
from common.hex_utils import Hex
from common.network_utils import send_message, receive_message, broadcast
from components.ui_components import HexMapCanvas

class Server:
    def __init__(self, host, port, gui_queue):
        self.host=host; self.port=port; self.server_socket=None; self.running=False
        self.game_state=GameState(gui_queue)
    def start(self):
        self.server_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port)); self.server_socket.listen(); self.running=True
        while self.running:
            try:
                conn, addr=self.server_socket.accept()
                thread=threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True); thread.start()
            except OSError: break
    def stop(self):
        self.running=False
        if self.server_socket: self.server_socket.close()
    def handle_client(self, conn, addr):
        print(f"[CONNESSIONE] Nuova connessione da {addr}"); player = None
        try:
            join_msg = receive_message(conn)
            print('RICEVUTO MESSAGGIO INIZIALE:', join_msg)
            if join_msg is None or join_msg.get("type") != "JOIN":
                return
            name = join_msg["data"]["name"]
            
            existing_player = self.game_state.find_player(name)
            if existing_player:
                if existing_player.conn is None:
                    # Riconnessione di un giocatore offline
                    existing_player.conn = conn
                    existing_player.addr = addr
                    player = existing_player
                    send_message(conn, make_game_state(self.game_state.get_state_dict()))
                    broadcast(self.game_state, make_player_joined(player.to_dict()), exclude_player=player)
                    self.game_state._trigger_gui_update()
                else:
                    send_message(conn, make_error_reply(f"Il nome '{name}' è già in uso.")); return
            else:
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
                # Invece di rimuovere il giocatore, lo disconnettiamo per mantenere la sessione
                self.game_state.disconnect_player(player)
                # Avvisiamo in chat che si è disconnesso, ma manteniamo il token sulla mappa
                broadcast(self.game_state, make_chat_broadcast("Sistema", f"{player.name} si è disconnesso."))
            conn.close()

