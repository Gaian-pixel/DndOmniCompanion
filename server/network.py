# dm_server.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import socket
import threading
import hmac
import time
import queue
import tkinter as tk
import json
import base64
from common.messagebox import messagebox
from tkinter import filedialog, ttk, scrolledtext, simpledialog
from PIL import Image, ImageTk

from common.protocol import (
    make_campaign_starter_granted,
    make_chat_broadcast,
    make_error_reply,
    make_fow_update_broadcast,
    make_game_state,
    make_player_joined,
)
from common.theme import setup_theme, apply_modern_window_style, BG_COLOR, SURFACE_COLOR, TEXT_COLOR, TEXT_MUTED, FONT_MAIN, FONT_TITLE, FONT_BOLD, ACCENT_RED
from server.commands import command_handlers
from common.game_state import GameState, Player
from server.map_editor import MapEditorWindow
from server.map_downloader import MapDownloaderDialog
from common.hex_utils import Hex
from common.network_utils import send_message, receive_message, broadcast, prepare_per_player_state_payload
from components.ui_components import HexMapCanvas
from server.voice_server import VoiceServer

def sanitize_client_payload(data, player):
    """Rimuove override di test/debug (`forced_*`, `free_test`) dai payload provenienti da client non DM."""
    from common.network_utils import is_dm_actor
    if not isinstance(data, dict) or is_dm_actor(player):
        return data
    stripped = {
        k: v for k, v in data.items()
        if not (isinstance(k, str) and (k.startswith("forced_") or k == "free_test"))
    }
    return stripped


class Server:
    AUTH_MAX_ATTEMPTS = 5
    AUTH_LOCKOUT_SECONDS = 30.0
    AUTH_WINDOW_SECONDS = 60.0

    def __init__(self, host, port, gui_queue, session_password: str = ""):
        self.host=host; self.port=port; self.server_socket=None; self.running=False
        self.active_sockets = set()
        self.active_sockets_lock = threading.Lock()
        self.session_password = str(session_password or "").strip()
        self._auth_failures = {}
        self._auth_lock = threading.Lock()
        self.game_state=GameState(gui_queue)
        from common.starter_equipment import get_campaign_starter_kit
        self.game_state.campaign_starter_kit = get_campaign_starter_kit()
        from server.audio_library import AudioLibrary
        self.game_state.audio_library = AudioLibrary()
        self.game_state.current_music = None  # ultimo messaggio AUDIO_TRACK_PLAY in loop, per chi si collega dopo
        self.voice_server = VoiceServer(self.host, 53912)

    def set_session_password(self, password: str):
        """Imposta o rimuove la password/PIN di sessione richiesta per il JOIN."""
        with self._auth_lock:
            self.session_password = str(password or "").strip()
            self._auth_failures.clear()

    def _is_ip_rate_limited(self, ip: str, now: float = None) -> bool:
        if now is None:
            now = time.monotonic()
        with self._auth_lock:
            rec = self._auth_failures.get(ip)
            if not rec:
                return False
            locked_until = float(rec.get("locked_until", 0.0) or 0.0)
            if locked_until > now:
                return True
            if locked_until > 0.0 and locked_until <= now:
                self._auth_failures.pop(ip, None)
            elif (now - float(rec.get("window_start", now))) > self.AUTH_WINDOW_SECONDS:
                self._auth_failures.pop(ip, None)
            return False

    def _record_auth_failure(self, ip: str, now: float = None) -> bool:
        if now is None:
            now = time.monotonic()
        with self._auth_lock:
            rec = self._auth_failures.get(ip)
            if not rec or (now - float(rec.get("window_start", now))) > self.AUTH_WINDOW_SECONDS:
                rec = {"count": 0, "window_start": now, "locked_until": 0.0}
            rec["count"] += 1
            if rec["count"] >= self.AUTH_MAX_ATTEMPTS:
                rec["locked_until"] = now + self.AUTH_LOCKOUT_SECONDS
                self._auth_failures[ip] = rec
                return True
            self._auth_failures[ip] = rec
            return False

    def _clear_auth_failures(self, ip: str):
        with self._auth_lock:
            self._auth_failures.pop(ip, None)

    def _verify_join_password(self, join_data: dict, addr, now: float = None) -> tuple[bool, str]:
        expected = str(getattr(self, "session_password", "") or "").strip()
        if not expected:
            return True, ""
        client_ip = str(addr[0]) if isinstance(addr, (tuple, list)) and addr else str(addr or "unknown")
        if self._is_ip_rate_limited(client_ip, now=now):
            return False, "Troppi tentativi di accesso errati. Riprova tra qualche secondo."
        provided = str((join_data or {}).get("password") or "").strip()
        if hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
            self._clear_auth_failures(client_ip)
            return True, ""
        locked = self._record_auth_failure(client_ip, now=now)
        if locked:
            return False, "Troppi tentativi di accesso errati. Account IP temporaneamente bloccato."
        return False, "Password o PIN della sessione errato o mancante."

    def send_loot_split(self, amount):
        from common.protocol import make_chat_broadcast, make_game_state
        pending_msgs = []
        with self.game_state.lock:
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
                    pending_msgs.append((p.conn, {"type": "RECEIVE_GOLD", "data": {"amount": share}}))

        for c_conn, c_msg in pending_msgs:
            send_message(c_conn, c_msg)

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
            log_join_msg = join_msg
            if isinstance(join_msg, dict) and isinstance(join_msg.get("data"), dict) and join_msg["data"].get("password"):
                log_join_msg = dict(join_msg)
                safe_data = dict(join_msg["data"])
                safe_data["password"] = "***"
                log_join_msg["data"] = safe_data
            print('RICEVUTO MESSAGGIO INIZIALE:', log_join_msg)
            if join_msg is None or not isinstance(join_msg, dict) or join_msg.get("type") != "JOIN":
                return
            join_data = join_msg.get("data")
            if not isinstance(join_data, dict):
                send_message(conn, make_error_reply("Payload JOIN non valido."))
                return
            raw_name = join_data.get("name")
            name = str(raw_name).strip() if isinstance(raw_name, str) else ""
            if not name or len(name) > 64:
                send_message(conn, make_error_reply("Nome personaggio non valido."))
                return
            auth_ok, auth_err = self._verify_join_password(join_data, addr)
            if not auth_ok:
                send_message(conn, make_error_reply(auth_err))
                return
            
            with self.game_state.lock:
                existing_player = self.game_state.find_player(name)
                if existing_player:
                    is_human = bool(getattr(existing_player, "is_party_member", False) or getattr(existing_player, "addr", None) is not None)
                    existing_conn = getattr(existing_player, "conn", None)
                    existing_addr = getattr(existing_player, "addr", None)
                    same_host = bool(existing_addr and addr and existing_addr[0] == addr[0])
                    if is_human and existing_conn is not None and existing_conn != conn and not same_host:
                        reject_msg = f"Il personaggio '{name}' è già connesso da un altro indirizzo."
                        player_action = "reject"
                    elif is_human:
                        # Riconnessione consentita dallo stesso host anche in caso di socket zombie
                        old_conn_to_close = existing_conn if (existing_conn is not None and existing_conn != conn) else None
                        existing_player.conn = conn
                        existing_player.addr = addr
                        existing_player.is_party_member = True
                        existing_player._preserve_server_state_on_join = True
                        existing_player._preserve_stats_on_join = True
                        existing_player._preserve_join_until = time.monotonic() + 5.0
                        player = existing_player
                        player_action = "reconnect"
                    else:
                        reject_msg = f"Il nome '{name}' è già in uso o appartiene a un PNG."
                        player_action = "reject"
                else:
                    old_conn_to_close = None
                    reject_msg = None
                    player_action = "join_new"
                    player = Player(name, addr, conn)
                    player.is_party_member = True

                    raw_pos = join_data.get("position")
                    req_pos = (
                        [int(raw_pos[0]), int(raw_pos[1])]
                        if isinstance(raw_pos, (list, tuple))
                        and len(raw_pos) == 2
                        and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in raw_pos)
                        else None
                    )
                    if req_pos is not None and self.game_state.current_map:
                        walls = self.game_state.current_map.get("walls", [])
                        if req_pos not in walls:
                            player.position = req_pos
                        elif "spawn_point" in self.game_state.current_map:
                            player.position = self.game_state.current_map["spawn_point"]
                    elif self.game_state.current_map and "spawn_point" in self.game_state.current_map:
                        player.position = self.game_state.current_map["spawn_point"]

                    self.game_state.add_player(player)

            if player_action == "reject":
                send_message(conn, make_error_reply(reject_msg))
                return
            elif player_action == "reconnect":
                if old_conn_to_close is not None:
                    try:
                        old_conn_to_close.close()
                    except Exception:
                        pass
                player._sent_asset_hashes = {}
                init_gs = prepare_per_player_state_payload(
                    make_game_state(self.game_state.get_state_dict(is_dm=False)),
                    player,
                )
                send_message(conn, init_gs)
                broadcast(self.game_state, make_player_joined(player.to_dict()), exclude_player=player)
                self.game_state._trigger_gui_update()
            else:
                if self.game_state.current_map and self.game_state.current_map.get("fow_enabled", False) and getattr(player, "position", None):
                    from server.rules.movement import auto_explore_fow
                    if auto_explore_fow(player, self.game_state):
                        self.game_state._trigger_gui_update()
                player._sent_asset_hashes = {}
                init_gs = prepare_per_player_state_payload(
                    make_game_state(self.game_state.get_state_dict(is_dm=False)),
                    player,
                )
                send_message(conn, init_gs)
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
                if msg is None:
                    break
                if not isinstance(msg, dict):
                    send_message(conn, make_error_reply("Formato pacchetto non valido."))
                    continue
                msg_type = msg.get("type")
                if not isinstance(msg_type, str) or not msg_type:
                    send_message(conn, make_error_reply("Tipo comando mancante o non valido."))
                    continue
                raw_data = msg.get("data", {})
                if raw_data is None:
                    raw_data = {}
                if not isinstance(raw_data, dict):
                    send_message(conn, make_error_reply("Payload 'data' non valido."))
                    continue
                handler = command_handlers.get(msg_type)
                if handler:
                    try:
                        payload = sanitize_client_payload(raw_data, player)
                        handler(payload, player, self.game_state)
                    except (ValueError, TypeError, KeyError, IndexError, AttributeError) as payload_err:
                        print(f"[ERRORE PAYLOAD] {msg_type} da {addr}: {payload_err}")
                        send_message(conn, make_error_reply("Richiesta non valida o parametri malformati."))
                    except Exception as handler_err:
                        print(f"[ERRORE HANDLER] {msg_type} da {addr}: {handler_err}")
                        send_message(conn, make_error_reply("Errore interno nell'elaborazione del comando."))
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

