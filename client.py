import socket
import json
import threading
from protocol import make_join, make_chat, make_roll, make_move, make_whisper, parse_message

def listen_for_messages(sock):
    try:
        while True:
            data = sock.recv(1024)
            if not data:
                break
            msg = parse_message(data.decode())
            if msg["type"] == "SERVER_REPLY":
                print("\n[SERVER]", msg["data"]["text"])
                print("> ", end="", flush=True)
    except Exception as e:
        print("[ERRORE RICEZIONE]", e)

def connect_to_server(host='127.0.0.1', port=5000):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))

            welcome = s.recv(1024).decode()
            print("[SERVER]", welcome)

            name = input("Inserisci il tuo nome: ")
            if not name.strip():
                print("Il nome non può essere vuoto!")
                return

            s.sendall(make_join(name).encode())

            msg = parse_message(s.recv(1024).decode())
            if msg["type"] == "SERVER_REPLY":
                print("Server dice:", msg["data"]["text"])

            # 🔥 Avvia il thread di ascolto
            recv_thread = threading.Thread(target=listen_for_messages, args=(s,), daemon=True)
            recv_thread.start()

            while True:
                msg = input("> ")

                if msg.lower() == "exit":
                    break

                if msg.startswith("/roll "):
                    formula = msg.split(" ", 1)[1]
                    s.sendall(make_roll(formula).encode())

                elif msg.startswith("/move "):
                    coords = msg.split(" ", 1)[1]
                    x, y = map(int, coords.split(","))
                    s.sendall(make_move(x, y).encode())
                
                elif msg.strip() == "/players":
                    s.sendall(json.dumps({"type": "LIST_PLAYERS", "data": {}}).encode())

                elif msg.startswith("/w "):
                    _, to_name, text = msg.split(" ", 2)
                    s.sendall(make_whisper(to_name, text).encode())

                else:
                    s.sendall(make_chat(msg).encode())

    except Exception as e:
        print("[ERRORE CLIENT]", e)

if __name__ == "__main__":
    try:
        connect_to_server()
    except KeyboardInterrupt:
        print("\n[CLIENT] Interruzione da tastiera. Uscita in corso...")
