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
        full_message_bytes = _recv_exact(sock, msg_len)
        if full_message_bytes is None:
            raise ConnectionError("Connessione interrotta.")
        return json.loads(full_message_bytes.decode('utf-8'))
    except (ConnectionError, struct.error, json.JSONDecodeError, BrokenPipeError, ConnectionResetError, OSError):
        return None

def broadcast(game_state, message_data, exclude_player=None):
    """ NUOVO: La funzione broadcast ora vive qui per evitare import circolari. """
    for p in game_state.get_all_players():
        if exclude_player and p.name == exclude_player.name:
            continue
        send_message(p.conn, message_data)