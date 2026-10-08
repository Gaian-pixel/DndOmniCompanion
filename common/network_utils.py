# network_utils.py
import socket
import struct
import json

def send_message(sock, message_data):
    """Codifica un dizionario Python in JSON e lo invia in modo robusto."""
    if sock is None:
        return
    try:
        message_json = json.dumps(message_data)
        message_bytes = message_json.encode('utf-8')
        header = struct.pack('!I', len(message_bytes))
        sock.sendall(header + message_bytes)
    except (BrokenPipeError, ConnectionResetError):
        # Questi errori sono normali se un client si disconnette, non stampiamo nulla
        pass
    except Exception as e:
        print(f"Errore imprevisto durante l'invio: {e}")

def receive_message(sock):
    """Riceve un messaggio in modo robusto e lo decodifica da JSON a dizionario."""
    try:
        header_bytes = sock.recv(4)
        if not header_bytes: return None
        msg_len = struct.unpack('!I', header_bytes)[0]
        full_message_bytes = b''
        while len(full_message_bytes) < msg_len:
            chunk = sock.recv(msg_len - len(full_message_bytes))
            if not chunk: raise ConnectionError("Connessione interrotta.")
            full_message_bytes += chunk
        return json.loads(full_message_bytes.decode('utf-8'))
    except (ConnectionError, struct.error, json.JSONDecodeError, BrokenPipeError, ConnectionResetError):
        return None

def broadcast(game_state, message_data, exclude_player=None):
    """ NUOVO: La funzione broadcast ora vive qui per evitare import circolari. """
    for p in game_state.get_all_players():
        if exclude_player and p.name == exclude_player.name:
            continue
        send_message(p.conn, message_data)