# network_utils.py
import socket
import struct
import json
import threading
import weakref

# Un lock per socket: impedisce che due thread (es. GUI del DM e thread di un client)
# scrivano contemporaneamente sullo stesso socket mescolando i byte di messaggi diversi.
# Fondamentale ora che si inviano messaggi grandi (blocchi di tracce audio).
_send_locks = weakref.WeakKeyDictionary()
_send_locks_guard = threading.Lock()

def _get_send_lock(sock):
    with _send_locks_guard:
        lock = _send_locks.get(sock)
        if lock is None:
            lock = threading.Lock()
            _send_locks[sock] = lock
        return lock

def _recv_exact(sock, n):
    """Riceve esattamente n byte (recv può restituirne meno di quelli richiesti)."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)

def send_message(sock, message_data):
    """Codifica un dizionario Python in JSON e lo invia in modo robusto."""
    if sock is None:
        return
    try:
        message_json = json.dumps(message_data)
        message_bytes = message_json.encode('utf-8')
        header = struct.pack('!I', len(message_bytes))
        with _get_send_lock(sock):
            sock.sendall(header + message_bytes)
    except (BrokenPipeError, ConnectionResetError):
        # Questi errori sono normali se un client si disconnette, non stampiamo nulla
        pass
    except Exception as e:
        print(f"Errore imprevisto durante l'invio: {e}")

def receive_message(sock):
    """Riceve un messaggio in modo robusto e lo decodifica da JSON a dizionario."""
    try:
        header_bytes = _recv_exact(sock, 4)
        if not header_bytes: return None
        msg_len = struct.unpack('!I', header_bytes)[0]
        if msg_len > 64 * 1024 * 1024: # Limite di sicurezza: 64 MB max payload
            raise ValueError(f"Messaggio troppo grande: {msg_len} byte")
        full_message_bytes = _recv_exact(sock, msg_len)
        if full_message_bytes is None:
            raise ConnectionError("Connessione interrotta.")
        return json.loads(full_message_bytes.decode('utf-8'))
    except (ConnectionError, struct.error, json.JSONDecodeError, BrokenPipeError, ConnectionResetError, OSError, ValueError):
        return None

def broadcast(game_state, message_data, exclude_player=None):
    """ NUOVO: La funzione broadcast ora vive qui per evitare import circolari. """
    msg_type = message_data.get("type") if isinstance(message_data, dict) else None
    
    # Pre-filter for GAME_STATE
    player_filtered_game_state = None
    if msg_type == "GAME_STATE" and isinstance(message_data.get("data"), dict):
        base_data = message_data["data"]
        raw_players = base_data.get("players", [])
        filtered_players = [pl for pl in raw_players if pl.get("layer", "token") != "gm"]
        copy_data = dict(base_data)
        copy_data["players"] = filtered_players
        player_filtered_game_state = {"type": "GAME_STATE", "data": copy_data}

    for p in game_state.get_all_players():
        if exclude_player and p.name == exclude_player.name:
            continue
        if not getattr(p, "conn", None):
            continue

        # If token on GM layer, don't broadcast movements or joins to regular player clients
        if msg_type == "PLAYER_JOINED" and isinstance(message_data.get("data"), dict):
            if message_data["data"].get("layer", "token") == "gm":
                continue
        elif msg_type == "PLAYER_MOVE" and isinstance(message_data.get("data"), dict):
            mv_name = message_data["data"].get("name")
            target_p = game_state.find_player(mv_name)
            if target_p and getattr(target_p, "layer", "token") == "gm":
                continue

        if player_filtered_game_state is not None:
            send_message(p.conn, player_filtered_game_state)
        else:
            send_message(p.conn, message_data)