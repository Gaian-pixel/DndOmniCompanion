import socket
import threading
import json
from protocol import parse_message, make_server_reply, make_error
from dice import roll_dice
import sys

players = []

def dispatch_command(msg, player, conn):
    msg_type = msg.get("type")
    data = msg.get("data", {})

    if msg_type == "CHAT":
        text = data.get("text", "")
        print(f"[CHAT] {player['name']}: {text}")
        response = f"{player['name']} dice: {text}"
        msg = make_server_reply(response).encode()
        broadcast(msg)  # invia a tutti

    elif msg_type == "MOVE":
        destination = data.get("to", [])
        player["position"] = destination
        print(f"[MOVE] {player['name']} si muove a {destination}")
        message = f"{player['name']} si è mosso a {destination}"
        broadcast(make_server_reply(message).encode())

    elif msg_type == "LIST_PLAYERS":
        info = []
        for p in players:
            pos = p.get("position", [0, 0])
            status = "in combattimento" if p.get("in_combat") else "libero"
            info.append(f"{p['name']} - posizione {pos} - {status}")
        summary = "\n".join(info)
        conn.sendall(make_server_reply("Giocatori connessi:\n" + summary).encode())

    elif msg_type == "WHISPER":
        to_name = data.get("to")
        text = data.get("text")
        # Trova il destinatario tra i giocatori
        for p in players:
            if p['name'] == to_name:
                p['conn'].sendall(make_server_reply(f"[Sussurro da {player['name']}] {text}").encode())
                conn.sendall(make_server_reply(f"Sussurro inviato a {to_name}.").encode())
                return
        conn.sendall(make_error("Giocatore non trovato.").encode())

    elif msg_type == "ROLL":
        formula = data.get("formula")
        reason = data.get("reason", "")
        try:
            result = roll_dice(formula)
            response = f"{player['name']} ha tirato {formula} ({reason}): {result['rolls']} + {result['modifier']} = {result['total']}"
            print(f"[ROLL] {response}")
            broadcast(make_server_reply(response).encode())
        except ValueError as e:
            conn.sendall(make_error(str(e)).encode())

    else:
        print(f"[DISPATCHER] Comando sconosciuto: {msg_type}")
        conn.sendall(make_error("Comando non riconosciuto.").encode())

def broadcast(message_json, exclude=None):
    for p in players:
        if exclude and p == exclude:
            continue
        try:
            p['conn'].sendall(message_json)
        except:
            print(f"[BROADCAST] Impossibile inviare a {p['name']}")


def handle_client(conn, addr):
    try:
        conn.sendall(b"Benvenuto, avventuriero!")

        raw = conn.recv(1024).decode()
        msg = json.loads(raw)

        if msg["type"] == "JOIN":
            name = msg["data"]["name"]
        else:
            name = "???"

        player = {
            "name": name,
            "addr": addr,
            "conn": conn,
            "position": [0, 0],
            "in_combat": False,
            "initiative": None
            }
        players.append(player)

        print(f"[GIOCATORE] {name} si è connesso da {addr}")
        conn.sendall(json.dumps({
            "type": "SERVER_REPLY",
            "data": {"text": f"Benvenuto, {name}!"}
        }).encode())

        while True:
            data = conn.recv(1024)
            if not data:
                break
            msg = parse_message(data.decode())
            dispatch_command(msg, player, conn)

    except Exception as e:
        print(f"[ERRORE] {addr}: {e}")
    finally:
        players.remove(player)
        conn.close()
        print(f"[DISCONNESSO] {addr}")


def start_server(port=5000):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', port))
    server.listen()
    server.settimeout(1.0)  # timeout per accettare connessioni ogni secondo
    print(f"[SERVER] In ascolto sulla porta {port}...")

    try:
        while True:
            try:
                conn, addr = server.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except socket.timeout:
                continue  # Ricontrolla il loop ogni secondo
    finally:
        server.close()
        print("[SERVER] Socket chiuso, server terminato.")

# 👇 Questa è la parte che sopprime il traceback
if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n[SERVER] Arresto server richiesto da tastiera")
        sys.exit(0)