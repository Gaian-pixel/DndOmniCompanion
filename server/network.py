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
from common.hex_utils import Hex
from common.network_utils import send_message, receive_message, broadcast
from components.ui_components import HexMapCanvas
from server.voice_server import VoiceServer

class Server:
    def __init__(self, host, port, gui_queue):
        self.host=host; self.port=port; self.server_socket=None; self.running=False
        self.active_sockets = set()
        self.active_sockets_lock = threading.Lock()
        self.game_state=GameState(gui_queue)
        from common.starter_equipment import get_campaign_starter_kit
        self.game_state.campaign_starter_kit = get_campaign_starter_kit()
        from server.audio_library import AudioLibrary
        self.game_state.audio_library = AudioLibrary()
        self.game_state.current_music = None  # ultimo messaggio AUDIO_TRACK_PLAY in loop, per chi si collega dopo
        self.voice_server = VoiceServer(self.host, 53912)

    def send_loot_split(self, amount):
        from common.protocol import make_chat_broadcast, make_game_state
        all_p = self.game_state.get_all_players()
        players = [p for p in all_p if getattr(p, 'is_party_member', False)]
        if not players:
            players = [p for p in all_p if getattr(p, 'conn', None) is not None]
            
        if not players:
            return
            
        share = amount // len(players)
        
        for p in players:
            if p.full_sheet is None:
                p.full_sheet = {}
            try:
                cur_gp = int(p.full_sheet.get("gp", 0) or 0)
            except (ValueError, TypeError):
                cur_gp = 0
            
            if "currency" not in p.full_sheet or not isinstance(p.full_sheet["currency"], dict):
                p.full_sheet["currency"] = {"MR": 0, "MA": 0, "ME": 0, "MO": cur_gp, "MP": 0}
            try:
                cur_mo = int(p.full_sheet["currency"].get("MO", cur_gp) or 0)
            except (ValueError, TypeError):
                cur_mo = cur_gp
            new_mo = cur_mo + share
            p.full_sheet["currency"]["MO"] = new_mo
            p.full_sheet["gp"] = new_mo
                
            if getattr(p, 'conn', None):
                send_message(p.conn, {"type": "RECEIVE_GOLD", "data": {"amount": share}})
                
        msg = f"Il DM ha distribuito {amount} MO ({share} a testa)."
        broadcast(self.game_state, make_chat_broadcast("Sistema", msg))
        self.game_state._trigger_gui_update()
        broadcast(self.game_state, make_game_state(self.game_state.get_state_dict()))

    def start(self):
        self.voice_server.start()
        self.server_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port)); self.server_socket.listen(); self.running=True
        while self.running:
            try:
                conn, addr=self.server_socket.accept()
                with self.active_sockets_lock:
                    self.active_sockets.add(conn)
                thread=threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True); thread.start()
            except OSError: break
    def stop(self):
        self.running=False
        self.voice_server.stop()
        if self.server_socket:
            try: self.server_socket.close()
            except Exception: pass
        with self.active_sockets_lock:
            for s in list(self.active_sockets):
                try: s.close()
                except Exception: pass
            self.active_sockets.clear()
    def handle_client(self, conn, addr):
        print(f"[CONNESSIONE] Nuova connessione da {addr}"); player = None
        try:
            conn.settimeout(15.0)
            join_msg = receive_message(conn)
            conn.settimeout(None)
            if hasattr(socket, "SO_KEEPALIVE"):
                try:
                    conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                except Exception:
                    pass
            print('RICEVUTO MESSAGGIO INIZIALE:', join_msg)
            if join_msg is None or join_msg.get("type") != "JOIN":
                return
            name = join_msg["data"]["name"]
            
            existing_player = self.game_state.find_player(name)
            if existing_player:
                is_human = bool(getattr(existing_player, "is_party_member", False) or getattr(existing_player, "addr", None) is not None)
                if is_human:
                    # Riconnessione consentita per membro del party anche in caso di socket zombie
                    if existing_player.conn is not None and existing_player.conn != conn:
                        try:
                            existing_player.conn.close()
                        except Exception:
                            pass
                    existing_player.conn = conn
                    existing_player.addr = addr
                    existing_player.is_party_member = True
                    player = existing_player
                    send_message(conn, make_game_state(self.game_state.get_state_dict(is_dm=False)))
                    broadcast(self.game_state, make_player_joined(player.to_dict()), exclude_player=player)
                    self.game_state._trigger_gui_update()
                else:
                    send_message(conn, make_error_reply(f"Il nome '{name}' è già in uso o appartiene a un PNG."))
                    return
            else:
                player = Player(name, addr, conn)
                player.is_party_member = True
                
                req_pos = join_msg.get("data", {}).get("position")
                if req_pos and self.game_state.current_map:
                    # Controlla se la posizione  valida (non dentro un muro)
                    walls = self.game_state.current_map.get("walls", [])
                    if req_pos not in walls:
                        player.position = req_pos
                    elif "spawn_point" in self.game_state.current_map:
                        player.position = self.game_state.current_map["spawn_point"]
                elif self.game_state.current_map and "spawn_point" in self.game_state.current_map:
                    player.position = self.game_state.current_map["spawn_point"]
                    
                self.game_state.add_player(player)
                if self.game_state.current_map and self.game_state.current_map.get("fow_enabled", False) and getattr(player, "position", None):
                    from server.rules.movement import auto_explore_fow
                    if auto_explore_fow(player, self.game_state):
                        self.game_state._trigger_gui_update()
                send_message(conn, make_game_state(self.game_state.get_state_dict(is_dm=False)))
                broadcast(self.game_state, make_player_joined(player.to_dict()), exclude_player=player)
                if self.game_state.current_map and self.game_state.current_map.get("fow_enabled", False):
                    broadcast(self.game_state, make_fow_update_broadcast(self.game_state.current_map.get("fow_revealed", []), self.game_state.current_map.get("fow_draft", []), fow_enabled=True))

            current_music = getattr(self.game_state, "current_music", None)
            if player and current_music:
                send_message(conn, current_music)

            if player and player.full_sheet:
                from common.starter_equipment import apply_class_and_race_starter_kit, apply_campaign_starter_kit
                if not player.full_sheet.get("starting_kit_applied"):
                    apply_class_and_race_starter_kit(player.full_sheet)
                if not player.full_sheet.get("campaign_starter_received"):
                    campaign_kit = getattr(self.game_state, "campaign_starter_kit", None)
                    apply_campaign_starter_kit(player.full_sheet, campaign_kit)
                    send_message(conn, make_campaign_starter_granted(player.full_sheet.get("inventory_grid", []), full_sheet=player.full_sheet))
                    broadcast(self.game_state, make_chat_broadcast("Sistema", f"[CAMPAGNA] {player.name} ha ricevuto l'equipaggiamento iniziale della campagna dal Master!"))
            
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
            with self.active_sockets_lock:
                self.active_sockets.discard(conn)
            if player:
                curr_sock = getattr(player, "conn", None)
                self.game_state.disconnect_player(player, conn=conn)
                # Avvisiamo in chat solo se il giocatore non si è già riconnesso con un nuovo socket
                if curr_sock is conn:
                    broadcast(self.game_state, make_chat_broadcast("Sistema", f"{player.name} si è disconnesso."))
            try:
                conn.close()
            except Exception:
                pass

