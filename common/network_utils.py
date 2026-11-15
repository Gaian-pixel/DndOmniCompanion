# network_utils.py
import os
import base64
import socket
import select
import struct
import json
import hashlib
import threading
import weakref


def compute_asset_hash(b64_data: str) -> str:
    """Calcola un digest breve deterministico per asset immagine codificati in base64."""
    if not isinstance(b64_data, str) or not b64_data:
        return ""
    return hashlib.sha256(b64_data.encode("utf-8")).hexdigest()[:16]


def compute_hexes_hash(hexes_data) -> str:
    """Calcola un digest breve deterministico per la lista/mappa statica delle celle (hexes)."""
    if not isinstance(hexes_data, (list, dict)) or len(hexes_data) == 0:
        return ""
    try:
        raw = json.dumps(hexes_data, separators=(",", ":"))
    except TypeError:
        raw = json.dumps(hexes_data, separators=(",", ":"), sort_keys=True, default=str)
    return "hx_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


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
        try:
            chunk = sock.recv(n - len(buf))
        except socket.timeout:
            # Timeout a frame integro (0 byte letti): propagabile al caller senza corrompere lo stream.
            if not buf:
                raise
            raise ConnectionError("Timeout durante la ricezione di un frame parziale.")
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)

def _send_message_impl(sock, message_data, pre_encoded=None, write_timeout: float = 2.0, lock_timeout=None) -> bool:
    """Codifica (o riusa buffer pre-serializzato) e invia un messaggio TCP in modo non bloccante per chunk."""
    if sock is None:
        return False
    try:
        if isinstance(pre_encoded, (bytes, bytearray)):
            payload = bytes(pre_encoded)
        else:
            message_json = json.dumps(message_data)
            message_bytes = message_json.encode('utf-8')
            header = struct.pack('!I', len(message_bytes))
            payload = header + message_bytes
        lock = _get_send_lock(sock)
        if lock_timeout is not None:
            if not lock.acquire(timeout=float(lock_timeout)):
                return False
        else:
            lock.acquire()
        try:
            can_chunk_select = False
            if hasattr(sock, "fileno") and hasattr(sock, "send"):
                try:
                    fd = sock.fileno()
                    can_chunk_select = isinstance(fd, int) and fd >= 0
                except (ValueError, TypeError, OSError):
                    can_chunk_select = False

            if can_chunk_select:
                chunk_size = 65536
                total = len(payload)
                offset = 0
                import time as _time
                deadline = _time.monotonic() + max(0.05, float(write_timeout))
                while offset < total:
                    remaining = deadline - _time.monotonic()
                    if remaining <= 0:
                        raise socket.timeout("Timeout attesa scrittura socket")
                    _, writable, _ = select.select([], [sock], [], remaining)
                    if not writable:
                        raise socket.timeout("Timeout attesa scrittura socket")
                    chunk = payload[offset:offset + chunk_size]
                    try:
                        sent = sock.send(chunk)
                    except BlockingIOError:
                        continue
                    if not sent:
                        raise ConnectionResetError("Socket chiusa durante l'invio")
                    offset += sent
            else:
                sock.sendall(payload)
        finally:
            lock.release()
        return True
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, socket.timeout):
        # Errori normali di disconnessione client o timeout invio
        return False
    except OSError as e:
        # Codici normali di socket chiuso/reimpostato su Windows (10038, 10054, 10053, 10058) o POSIX
        if getattr(e, 'winerror', None) in (10038, 10054, 10053, 10058) or e.errno in (9, 104, 32):
            return False
        else:
            print(f"Errore socket durante l'invio: {e}")
            return False
    except Exception as e:
        print(f"Errore imprevisto durante l'invio: {e}")
        return False

def send_message(sock, message_data) -> bool:
    """Codifica un dizionario Python in JSON e lo invia in modo robusto."""
    return _send_message_impl(sock, message_data)

def receive_message(sock, raise_on_timeout: bool = False):
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
    except socket.timeout:
        if raise_on_timeout:
            raise
        return None
    except (ConnectionError, struct.error, json.JSONDecodeError, BrokenPipeError, ConnectionResetError, OSError, ValueError):
        return None

def resolve_map_image_data(map_data: dict, extra_dirs=None):
    """Risolve in sicurezza bg_image_data da embedded base64 o da base_image_path (con fallback relativi).
    Non solleva FileNotFoundError se l'immagine embedded e' gia' presente o il percorso originale appartiene a un altro host.
    """
    if not isinstance(map_data, dict):
        return None
    existing = map_data.get("bg_image_data")
    if isinstance(existing, str) and existing:
        map_data["bg_image_hash"] = compute_asset_hash(existing)
        return existing

    base_path = map_data.get("base_image_path")
    if not base_path or not isinstance(base_path, str):
        return None

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    search_dirs = []
    if extra_dirs:
        for d in extra_dirs:
            if d and d not in search_dirs:
                search_dirs.append(d)
    for d in (os.path.join(repo_root, "maps"), repo_root):
        if d not in search_dirs:
            search_dirs.append(d)

    candidates = [base_path]
    basename = os.path.basename(base_path)
    for d in search_dirs:
        if not os.path.isabs(base_path):
            candidates.append(os.path.join(d, base_path))
        if basename:
            candidates.append(os.path.join(d, basename))
            candidates.append(os.path.join(d, "assets", basename))

    for cand in candidates:
        if cand and os.path.isfile(cand):
            try:
                with open(cand, "rb") as image_file:
                    encoded = base64.b64encode(image_file.read()).decode("utf-8")
                map_data["bg_image_data"] = encoded
                map_data["bg_image_hash"] = compute_asset_hash(encoded)
                return encoded
            except OSError:
                continue
    return None


def _extract_rev_set(map_data) -> set[tuple[int, int]]:
    rev_set = set()
    if not isinstance(map_data, dict):
        return rev_set
    for h in map_data.get("fow_revealed", []) or []:
        if isinstance(h, (list, tuple)) and len(h) >= 2:
            rev_set.add((h[0], h[1]))
    return rev_set


def is_entity_visible_to_players(
    entity,
    cur_map,
    game_state=None,
    rev_set=None,
    recipient_name=None,
    allow_self_hidden: bool = False,
) -> bool:
    """Restituisce True solo se un'entita' (Player o dict) deve essere visibile ai giocatori."""
    if entity is None:
        return False

    if isinstance(entity, dict):
        name = entity.get("name")
        layer = entity.get("layer", "token")
        is_hidden = bool(entity.get("is_hidden", False))
        in_pocket = bool(entity.get("in_pocket_dimension", False))
        pos = entity.get("position")
        is_party_flag = bool(entity.get("is_party_member", False) or entity.get("is_companion", False))
        has_conn = entity.get("conn") is not None
    else:
        name = getattr(entity, "name", None)
        layer = getattr(entity, "layer", "token")
        is_hidden = bool(getattr(entity, "is_hidden", False))
        in_pocket = bool(getattr(entity, "in_pocket_dimension", False))
        pos = getattr(entity, "position", None)
        is_party_flag = bool(getattr(entity, "is_party_member", False) or getattr(entity, "is_companion", False))
        has_conn = getattr(entity, "conn", None) is not None

    if layer == "gm" or in_pocket:
        return False
    if is_hidden and not (allow_self_hidden and recipient_name and name == recipient_name):
        return False

    fow_enabled = bool(cur_map.get("fow_enabled", False)) if isinstance(cur_map, dict) else False
    if fow_enabled:
        if not has_conn and game_state is not None and name:
            src = game_state.find_player(name)
            if src is not None:
                is_party_flag = is_party_flag or bool(
                    getattr(src, "is_party_member", False)
                    or getattr(src, "is_companion", False)
                    or getattr(src, "conn", None) is not None
                )
        is_self = bool(recipient_name and name == recipient_name)
        is_party = is_party_flag or has_conn or is_self
        if not is_party:
            if rev_set is None:
                rev_set = _extract_rev_set(cur_map)
            if not isinstance(pos, (list, tuple)) or len(pos) < 2:
                return False
            if (pos[0], pos[1]) not in rev_set:
                return False
    return True


def sanitize_map_for_players(map_data: dict) -> dict:
    """Filtra elementi segreti della mappa (trappole nascoste, porte segrete, note del Master, POI segreti, teleports/spawn/fow_draft) per i giocatori."""
    if not isinstance(map_data, dict):
        return map_data
    clean = dict(map_data)

    # 1. Trappole: mostra solo quelle rilevate o innescate (o esplicitamente visibili e non segrete)
    if "traps" in clean and isinstance(clean["traps"], list):
        clean_traps = []
        for t in clean["traps"]:
            if not isinstance(t, dict):
                continue
            is_triggered_or_detected = bool(t.get("triggered", False) or t.get("detected", False))
            is_explicitly_visible = (not t.get("hidden", True)) and (not t.get("secret", False))
            if is_triggered_or_detected or is_explicitly_visible:
                t_copy = dict(t)
                t_copy.pop("dm_notes", None)
                t_copy.pop("secret", None)
                clean_traps.append(t_copy)
        clean["traps"] = clean_traps

    # 2. Porte: le porte segrete non scoperte vengono rimosse dall'array 'doors'
    #    e la loro cella (q,r) o edge viene aggiunta a 'walls' per bloccare movimento e LoS senza svelare l'icona
    if "doors" in clean and isinstance(clean["doors"], list):
        clean_doors = []
        existing_walls = clean.get("walls", [])
        wall_keys = set()
        for w in existing_walls:
            if isinstance(w, (list, tuple)) and len(w) >= 2:
                wall_keys.add((w[0], w[1]))
            else:
                wall_keys.add(w)
        secret_walls_to_add = []
        for d in clean["doors"]:
            is_secret = (d.get("is_secret") or d.get("state") == "secret") and not d.get("discovered", False)
            if is_secret:
                edge = d.get("edge")
                if edge and edge not in wall_keys:
                    secret_walls_to_add.append(edge)
                    wall_keys.add(edge)
                if "q" in d and "r" in d:
                    cell_key = (d["q"], d["r"])
                    if cell_key not in wall_keys:
                        secret_walls_to_add.append([d["q"], d["r"]])
                        wall_keys.add(cell_key)
            else:
                clean_doors.append(d)
        clean["doors"] = clean_doors
        if secret_walls_to_add:
            clean["walls"] = list(existing_walls) + secret_walls_to_add

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

    # 5. Bottini (Loots): escludi loots nascosti o in celle non ancora rivelate dalla FoW
    if "loots" in clean and isinstance(clean["loots"], list):
        fow_enabled = bool(clean.get("fow_enabled", False))
        if fow_enabled:
            rev_set = _extract_rev_set(clean)
            clean["loots"] = [
                l for l in clean["loots"]
                if not l.get("hidden", False) and (l.get("q"), l.get("r")) in rev_set
            ]
        else:
            clean["loots"] = [l for l in clean["loots"] if not l.get("hidden", False)]

    # 6. Rimuovi informazioni riservate al DM (portali/teleports, punto di spawn e bozza FoW non pubblicata)
    clean.pop("teleports", None)
    clean.pop("spawn_point", None)
    clean.pop("fow_draft", None)

    if isinstance(clean.get("bg_image_data"), str) and clean["bg_image_data"]:
        clean["bg_image_hash"] = compute_asset_hash(clean["bg_image_data"])
    hexes_obj = clean.get("hexes")
    if isinstance(hexes_obj, (list, dict)) and len(hexes_obj) > 0:
        clean["hexes_hash"] = compute_hexes_hash(hexes_obj)
    else:
        clean.pop("hexes_hash", None)
        clean.pop("hexes_cached", None)

    return clean


MAX_TRACKED_SENT_ASSET_HASHES = 24


def _track_and_check_sent_hash(sent_hashes, asset_hash: str) -> bool:
    """Record an asset hash in bounded LRU/FIFO order; return True if already tracked."""
    if not asset_hash:
        return False
    if isinstance(sent_hashes, dict):
        if asset_hash in sent_hashes:
            sent_hashes.pop(asset_hash, None)
            sent_hashes[asset_hash] = True
            return True
        while len(sent_hashes) >= MAX_TRACKED_SENT_ASSET_HASHES:
            oldest = next(iter(sent_hashes), None)
            if oldest is None:
                break
            sent_hashes.pop(oldest, None)
        sent_hashes[asset_hash] = True
        return False
    if isinstance(sent_hashes, list):
        if asset_hash in sent_hashes:
            sent_hashes.remove(asset_hash)
            sent_hashes.append(asset_hash)
            return True
        while len(sent_hashes) >= MAX_TRACKED_SENT_ASSET_HASHES:
            sent_hashes.pop(0)
        sent_hashes.append(asset_hash)
        return False
    if isinstance(sent_hashes, set):
        if asset_hash in sent_hashes:
            return True
        while len(sent_hashes) >= MAX_TRACKED_SENT_ASSET_HASHES:
            sent_hashes.pop()
        sent_hashes.add(asset_hash)
        return False
    return False


def _deduplicate_map_payload(map_dict: dict, sent_hashes, trust_hashes: bool = False) -> dict:
    if not isinstance(map_dict, dict):
        return map_dict

    asset_specs = (
        ("bg_image_data", "bg_image_hash", "bg_image_cached", compute_asset_hash, lambda v: isinstance(v, str) and bool(v), lambda h: bool(h)),
        ("hexes", "hexes_hash", "hexes_cached", compute_hexes_hash, lambda v: isinstance(v, (list, dict)) and len(v) > 0, lambda h: h.startswith("hx_")),
    )
    active_specs = [spec for spec in asset_specs if spec[4](map_dict.get(spec[0]))]
    if not active_specs:
        return map_dict

    map_copy = dict(map_dict)
    for data_key, hash_key, flag_key, hash_fn, _is_raw, is_valid_hash in active_specs:
        raw_val = map_dict.get(data_key)
        existing_hash = map_dict.get(hash_key)
        if trust_hashes and isinstance(existing_hash, str) and is_valid_hash(existing_hash):
            digest = existing_hash
        else:
            digest = hash_fn(raw_val)
        map_copy[hash_key] = digest
        if _track_and_check_sent_hash(sent_hashes, digest):
            map_copy[data_key] = None
            map_copy[flag_key] = True
        else:
            map_copy.pop(flag_key, None)
    return map_copy


def _deduplicate_handout_dict(handout_dict: dict, sent_hashes) -> dict:
    if not isinstance(handout_dict, dict):
        return handout_dict
    img_b64 = handout_dict.get("image_b64")
    if not isinstance(img_b64, str) or not img_b64:
        return handout_dict
    img_hash = compute_asset_hash(img_b64)
    h_copy = dict(handout_dict)
    h_copy["image_hash"] = img_hash
    if _track_and_check_sent_hash(sent_hashes, img_hash):
        h_copy["image_b64"] = None
        h_copy["image_cached"] = True
    return h_copy


def _deduplicate_player_dict(player_dict: dict, sent_hashes) -> dict:
    if not isinstance(player_dict, dict):
        return player_dict
    av_b64 = player_dict.get("avatar_b64")
    fs = player_dict.get("full_sheet")
    fs_av = fs.get("avatar_b64") if isinstance(fs, dict) else None
    has_top_av = isinstance(av_b64, str) and bool(av_b64)
    has_fs_av = isinstance(fs_av, str) and bool(fs_av)
    if not has_top_av and not has_fs_av:
        return player_dict

    p_copy = dict(player_dict)
    if has_top_av:
        av_hash = compute_asset_hash(av_b64)
        p_copy["avatar_hash"] = av_hash
        if _track_and_check_sent_hash(sent_hashes, av_hash):
            p_copy["avatar_b64"] = None
            p_copy["avatar_cached"] = True
    if has_fs_av:
        fs_hash = compute_asset_hash(fs_av)
        fs_copy = dict(fs)
        fs_copy["avatar_hash"] = fs_hash
        # Se già presente al top-level con stesso hash o già in cache client, evita duplicazione nella full_sheet
        if (has_top_av and fs_hash == p_copy.get("avatar_hash")) or _track_and_check_sent_hash(sent_hashes, fs_hash):
            fs_copy["avatar_b64"] = None
            fs_copy["avatar_cached"] = True
        p_copy["full_sheet"] = fs_copy
    return p_copy


def prepare_per_player_state_payload(message_data: dict, player, _trust_map_hashes: bool = False) -> dict:
    """Deduplica blob immagine (mappa, handout e avatar) e griglia statica (hexes) gia inviati al singolo client."""
    if not isinstance(message_data, dict):
        return message_data
    msg_type = message_data.get("type")
    if msg_type not in ("GAME_STATE", "MAP_DATA_UPDATE", "HANDOUT_BROADCAST", "PLAYER_JOINED"):
        return message_data

    data = message_data.get("data")
    if not isinstance(data, dict):
        return message_data

    sent_hashes = getattr(player, "_sent_asset_hashes", None)
    if not isinstance(sent_hashes, (dict, list, set)):
        sent_hashes = {}
        if player is not None:
            try:
                player._sent_asset_hashes = sent_hashes
            except Exception:
                pass

    if msg_type == "HANDOUT_BROADCAST":
        new_data = _deduplicate_handout_dict(data, sent_hashes)
        return message_data if new_data is data else {"type": msg_type, "data": new_data}

    if msg_type == "PLAYER_JOINED":
        new_data = _deduplicate_player_dict(data, sent_hashes)
        return message_data if new_data is data else {"type": msg_type, "data": new_data}

    data_copy = dict(data)
    if "map" in data_copy and isinstance(data_copy["map"], dict):
        data_copy["map"] = _deduplicate_map_payload(data_copy["map"], sent_hashes, trust_hashes=_trust_map_hashes)
    elif msg_type == "MAP_DATA_UPDATE" and ("bg_image_data" in data_copy or "hexes" in data_copy):
        data_copy = _deduplicate_map_payload(data_copy, sent_hashes, trust_hashes=_trust_map_hashes)

    if msg_type == "GAME_STATE" and isinstance(data_copy.get("handouts"), list):
        data_copy["handouts"] = [
            _deduplicate_handout_dict(h, sent_hashes) for h in data_copy["handouts"]
        ]

    if msg_type == "GAME_STATE" and isinstance(data_copy.get("players"), list):
        data_copy["players"] = [
            _deduplicate_player_dict(pl, sent_hashes) for pl in data_copy["players"]
        ]

    return {"type": msg_type, "data": data_copy}

def _dispatch_native_broadcast(
    tasks_by_conn: dict,
    flush_timeout: float = 0.35,
    write_timeout: float = 0.5,
    lock_timeout: float = 0.25,
):
    """Invia in parallelo i frame nativi per socket isolando eventuali client lenti o bloccati."""
    import threading as _threading
    import time as _time

    def _worker(sock, items):
        for msg_obj, pre_buf in items:
            ok = _send_message_impl(
                sock,
                msg_obj,
                pre_encoded=pre_buf,
                write_timeout=write_timeout,
                lock_timeout=lock_timeout,
            )
            if ok is False:
                break

    threads = []
    for sock, items in tasks_by_conn.values():
        t = _threading.Thread(target=_worker, args=(sock, items), daemon=True)
        t.start()
        threads.append(t)

    deadline = _time.monotonic() + float(flush_timeout)
    for t in threads:
        remaining = deadline - _time.monotonic()
        t.join(timeout=max(0.0, remaining))


def broadcast(game_state, message_data, exclude_player=None):
    """ La funzione broadcast invia messaggi filtrando le informazioni riservate del GM layer, dimension pocket e FoW ai giocatori. """
    msg_type = message_data.get("type") if isinstance(message_data, dict) else None
    cur_map = getattr(game_state, "current_map", None)

    # Pre-filter for GAME_STATE
    player_filtered_game_state = None
    if msg_type == "GAME_STATE" and isinstance(message_data.get("data"), dict):
        base_data = message_data["data"]
        raw_players = base_data.get("players", [])
        raw_map = base_data.get("map") or cur_map
        rev_set = _extract_rev_set(raw_map)
        filtered_players = [
            pl for pl in raw_players
            if is_entity_visible_to_players(pl, raw_map, game_state=game_state, rev_set=rev_set)
        ]
        copy_data = dict(base_data)
        copy_data["players"] = filtered_players
        visible_names = {pl.get("name") for pl in filtered_players if isinstance(pl, dict)}
        t_name = copy_data.get("turn_player_name")
        if t_name and t_name not in visible_names:
            t_obj = game_state.find_player(t_name) if hasattr(game_state, "find_player") else None
            if t_obj is None or not is_entity_visible_to_players(t_obj, raw_map, game_state=game_state, rev_set=rev_set):
                copy_data["turn_player_name"] = "Sconosciuto"
        if "map" in copy_data:
            copy_data["map"] = sanitize_map_for_players(copy_data["map"])
        player_filtered_game_state = {"type": "GAME_STATE", "data": copy_data}

    # Pre-filter for MAP_DATA_UPDATE
    player_filtered_map_data = None
    if msg_type == "MAP_DATA_UPDATE" and isinstance(message_data.get("data"), dict):
        raw_map = message_data["data"].get("map", message_data["data"])
        clean_map = sanitize_map_for_players(raw_map)
        player_filtered_map_data = {"type": "MAP_DATA_UPDATE", "data": {"map": clean_map}}

    # Pre-filter for FOW_UPDATE_BROADCAST: scrub fow_draft and attach only visible players
    player_filtered_fow = None
    if msg_type == "FOW_UPDATE_BROADCAST" and isinstance(message_data.get("data"), dict):
        fow_data = dict(message_data["data"])
        fow_data["fow_draft"] = []
        temp_map = dict(cur_map) if isinstance(cur_map, dict) else {}
        if "fow_revealed" in fow_data:
            temp_map["fow_revealed"] = fow_data["fow_revealed"]
        if "fow_enabled" in fow_data:
            temp_map["fow_enabled"] = fow_data["fow_enabled"]
        rev_set = _extract_rev_set(temp_map)
        if fow_data.get("players") is None:
            fow_data["players"] = [
                pl.to_dict() for pl in game_state.get_all_players()
                if is_entity_visible_to_players(pl, temp_map, game_state=game_state, rev_set=rev_set)
            ]
        else:
            fow_data["players"] = [
                pl for pl in fow_data["players"]
                if is_entity_visible_to_players(pl, temp_map, game_state=game_state, rev_set=rev_set)
            ]
        player_filtered_fow = {"type": "FOW_UPDATE_BROADCAST", "data": fow_data}

    # Pre-filter for COMBAT_STATE_UPDATE: hide secret/unrevealed turn owner names
    player_filtered_combat = None
    if msg_type == "COMBAT_STATE_UPDATE" and isinstance(message_data.get("data"), dict):
        cdata = dict(message_data["data"])
        t_name = cdata.get("turn_player_name")
        if t_name and hasattr(game_state, "find_player"):
            t_obj = game_state.find_player(t_name)
            if t_obj is not None and not is_entity_visible_to_players(t_obj, cur_map, game_state=game_state):
                cdata["turn_player_name"] = "Sconosciuto"
        player_filtered_combat = {"type": "COMBAT_STATE_UPDATE", "data": cdata}

    send_is_native = (
        getattr(send_message, "__module__", "") == __name__
        and getattr(send_message, "__name__", "") == "send_message"
    )
    shared_payload = None
    shared_pre_encoded = None
    if msg_type not in ("GAME_STATE", "MAP_DATA_UPDATE", "HANDOUT_BROADCAST", "PLAYER_JOINED"):
        if player_filtered_fow is not None:
            shared_payload = player_filtered_fow
        elif player_filtered_combat is not None:
            shared_payload = player_filtered_combat
        else:
            shared_payload = message_data
        if send_is_native:
            try:
                raw_bytes = json.dumps(shared_payload).encode("utf-8")
                shared_pre_encoded = struct.pack("!I", len(raw_bytes)) + raw_bytes
            except Exception:
                shared_pre_encoded = None

    base_msg = (
        player_filtered_game_state
        or player_filtered_map_data
        or player_filtered_fow
        or player_filtered_combat
        or message_data
    )
    trust_hashes = (player_filtered_game_state is not None or player_filtered_map_data is not None)
    failed_conns = set()
    tasks_by_conn = {}
    for p in game_state.get_all_players():
        if exclude_player and p.name == exclude_player.name:
            continue
        conn = getattr(p, "conn", None)
        if not conn or id(conn) in failed_conns:
            continue

        # Non inviare aggiornamenti o stats di entità sul GM layer, in pocket dimension, nascoste o fuori FoW ai client regolari
        if msg_type == "PLAYER_JOINED" and isinstance(message_data.get("data"), dict):
            p_join = message_data["data"]
            if not is_entity_visible_to_players(p_join, cur_map, game_state=game_state, recipient_name=p.name, allow_self_hidden=True):
                continue
        elif msg_type == "PLAYER_MOVE" and isinstance(message_data.get("data"), dict):
            mv_data = message_data["data"]
            mv_name = mv_data.get("name")
            target_p = game_state.find_player(mv_name)
            entity_ref = target_p if target_p is not None else mv_data
            if not is_entity_visible_to_players(entity_ref, cur_map, game_state=game_state, recipient_name=p.name, allow_self_hidden=True):
                continue
        elif msg_type == "PLAYER_STATS_UPDATE" and isinstance(message_data.get("data"), dict):
            stat_data = message_data["data"]
            stat_name = stat_data.get("name")
            target_p = game_state.find_player(stat_name)
            entity_ref = target_p if target_p is not None else stat_data
            if not is_entity_visible_to_players(entity_ref, cur_map, game_state=game_state, recipient_name=p.name, allow_self_hidden=True):
                continue

        if shared_pre_encoded is not None:
            entry = (shared_payload, shared_pre_encoded)
        else:
            payload = prepare_per_player_state_payload(base_msg, p, _trust_map_hashes=trust_hashes)
            entry = (payload, None)

        if not send_is_native:
            ok = send_message(conn, entry[0])
            if ok is False:
                failed_conns.add(id(conn))
        else:
            cid = id(conn)
            if cid not in tasks_by_conn:
                tasks_by_conn[cid] = (conn, [])
            tasks_by_conn[cid][1].append(entry)

    if send_is_native and tasks_by_conn:
        _dispatch_native_broadcast(tasks_by_conn)