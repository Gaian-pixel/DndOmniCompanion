# network_utils.py
import socket
import select
import struct
import json
import threading
import weakref


def is_dm_actor(player) -> bool:
    """Ritorna True se il mittente è il DM (player is None o role=='DM')."""
    return player is None or getattr(player, "role", "") == "DM"

# Un lock per socket: impedisce che due thread (es. GUI del DM e thread di un client)
# scrivano contemporaneamente sullo stesso socket mescolando i byte di messaggi diversi.
# Fondamentale ora che si inviano messaggi grandi (blocchi di tracce audio).
_send_locks = weakref.WeakKeyDictionary()
_send_locks_guard = threading.Lock()

def _get_send_lock(sock):
    if hasattr(sock, "_send_lock"):
        return sock._send_lock
    with _send_locks_guard:
        try:
            lock = _send_locks.get(sock)
            if lock is None:
                lock = threading.Lock()
                _send_locks[sock] = lock
            return lock
        except TypeError:
            try:
                sock._send_lock = threading.Lock()
                return sock._send_lock
            except Exception:
                return threading.Lock()

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
            # Attesa scrivibilità non invasiva: evita di mutare sock.settimeout() sul thread condiviso con receive_message()
            if hasattr(sock, "fileno"):
                try:
                    fd = sock.fileno()
                    if isinstance(fd, int) and fd >= 0:
                        _, writable, _ = select.select([], [sock], [], 5.0)
                        if not writable:
                            raise socket.timeout("Timeout attesa scrittura socket")
                except socket.timeout:
                    raise
                except (ValueError, TypeError, OSError):
                    pass
            sock.sendall(header + message_bytes)
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, socket.timeout):
        # Errori normali di disconnessione client o timeout invio
        pass
    except OSError as e:
        # Codici normali di socket chiuso/reimpostato su Windows (10038, 10054, 10053, 10058) o POSIX
        if getattr(e, 'winerror', None) in (10038, 10054, 10053, 10058) or e.errno in (9, 104, 32):
            pass
        else:
            print(f"Errore socket durante l'invio: {e}")
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

def sanitize_map_for_players(map_data: dict) -> dict:
    """Filtra elementi segreti della mappa (trappole nascoste, porte segrete, note del Master, POI segreti) per i giocatori."""
    if not isinstance(map_data, dict):
        return map_data
    clean = dict(map_data)

    # 1. Trappole: mostra solo quelle rilevate o innescate (o esplicitamente non nascoste)
    if "traps" in clean and isinstance(clean["traps"], list):
        clean["traps"] = [
            t for t in clean["traps"]
            if (t.get("triggered", False) or t.get("detected", False) or not t.get("hidden", True))
            and not t.get("secret", False)
        ]

    # 2. Porte: le porte segrete non scoperte vengono rimosse dall'array 'doors'
    #    e il loro bordo viene aggiunto a 'walls' per bloccare movimento e LoS senza svelare l'icona
    if "doors" in clean and isinstance(clean["doors"], list):
        clean_doors = []
        secret_walls_to_add = []
        for d in clean["doors"]:
            is_secret = (d.get("is_secret") or d.get("state") == "secret") and not d.get("discovered", False)
            if is_secret:
                edge = d.get("edge")
                if edge and edge not in clean.get("walls", []):
                    secret_walls_to_add.append(edge)
            else:
                clean_doors.append(d)
        clean["doors"] = clean_doors
        if secret_walls_to_add:
            clean["walls"] = list(clean.get("walls", [])) + secret_walls_to_add

    # 3. Room Pins: escludi pin segreti o dm_only, e rimuovi dm_notes e secret
    if "room_pins" in clean and isinstance(clean["room_pins"], list):
        clean_pins = []
        for pin in clean["room_pins"]:
            if isinstance(pin, dict):
                if pin.get("secret", False) or pin.get("dm_only", False) or pin.get("is_secret", False):
                    continue
                p_copy = dict(pin)
                p_copy.pop("dm_notes", None)
                p_copy.pop("secret", None)
                clean_pins.append(p_copy)
            else:
                clean_pins.append(pin)
        clean["room_pins"] = clean_pins

    # 4. POIs: escludi POI marcati segreti o dm_only e rimuovi dm_notes
    if "pois" in clean and isinstance(clean["pois"], dict):
        clean_pois = {}
        for k, pdata in clean["pois"].items():
            if isinstance(pdata, dict):
                if pdata.get("secret", False) or pdata.get("dm_only", False) or pdata.get("is_secret", False):
                    continue
                poi_copy = dict(pdata)
                poi_copy.pop("dm_notes", None)
                poi_copy.pop("secret", None)
                clean_pois[k] = poi_copy
            else:
                clean_pois[k] = pdata
        clean["pois"] = clean_pois

    # 5. Bottini (Loots): escludi loots non scoperti o nascosti dalla FoW
    if "loots" in clean and isinstance(clean["loots"], list):
        fow_enabled = bool(clean.get("fow_enabled", False))
        if fow_enabled:
            rev_set = set()
            for h in clean.get("fow_revealed", []):
                if isinstance(h, (list, tuple)) and len(h) >= 2:
                    rev_set.add((h[0], h[1]))
            clean["loots"] = [
                l for l in clean["loots"]
                if not l.get("hidden", False) and (not rev_set or (l.get("q"), l.get("r")) in rev_set)
            ]
        else:
            clean["loots"] = [l for l in clean["loots"] if not l.get("hidden", False)]

    return clean

def broadcast(game_state, message_data, exclude_player=None):
    """ La funzione broadcast invia messaggi filtrando le informazioni riservate del GM layer ai giocatori. """
    msg_type = message_data.get("type") if isinstance(message_data, dict) else None
    
    # Pre-filter for GAME_STATE
    player_filtered_game_state = None
    if msg_type == "GAME_STATE" and isinstance(message_data.get("data"), dict):
        base_data = message_data["data"]
        raw_players = base_data.get("players", [])
        filtered_players = [
            pl for pl in raw_players
            if pl.get("layer", "token") != "gm" and not pl.get("is_hidden", False)
        ]
        copy_data = dict(base_data)
        copy_data["players"] = filtered_players
        if "map" in copy_data:
            copy_data["map"] = sanitize_map_for_players(copy_data["map"])
        player_filtered_game_state = {"type": "GAME_STATE", "data": copy_data}

    # Pre-filter for MAP_DATA_UPDATE
    player_filtered_map_data = None
    if msg_type == "MAP_DATA_UPDATE" and isinstance(message_data.get("data"), dict):
        raw_map = message_data["data"].get("map", message_data["data"])
        clean_map = sanitize_map_for_players(raw_map)
        player_filtered_map_data = {"type": "MAP_DATA_UPDATE", "data": {"map": clean_map}}

    for p in game_state.get_all_players():
        if exclude_player and p.name == exclude_player.name:
            continue
        if not getattr(p, "conn", None):
            continue

        # Non inviare aggiornamenti o stats di entità sul GM layer o nascoste ai client regolari
        if msg_type == "PLAYER_JOINED" and isinstance(message_data.get("data"), dict):
            p_join = message_data["data"]
            if p_join.get("layer", "token") == "gm" or (p_join.get("is_hidden", False) and p_join.get("name") != p.name):
                continue
        elif msg_type == "PLAYER_MOVE" and isinstance(message_data.get("data"), dict):
            mv_name = message_data["data"].get("name")
            target_p = game_state.find_player(mv_name)
            if target_p and (getattr(target_p, "layer", "token") == "gm" or (getattr(target_p, "is_hidden", False) and mv_name != p.name)):
                continue
        elif msg_type == "PLAYER_STATS_UPDATE" and isinstance(message_data.get("data"), dict):
            stat_name = message_data["data"].get("name")
            target_p = game_state.find_player(stat_name)
            if target_p and (getattr(target_p, "layer", "token") == "gm" or (getattr(target_p, "is_hidden", False) and stat_name != p.name)):
                continue

        if player_filtered_game_state is not None:
            send_message(p.conn, player_filtered_game_state)
        elif player_filtered_map_data is not None:
            send_message(p.conn, player_filtered_map_data)
        else:
            send_message(p.conn, message_data)