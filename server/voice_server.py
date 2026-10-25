import socket
import threading

class VoiceServer:
    def __init__(self, host, port=53912):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Allows reusing address if restarted quickly
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SIO_UDP_CONNRESET"):
            try:
                self.sock.ioctl(socket.SIO_UDP_CONNRESET, False)
            except Exception:
                pass
        self.clients = set()
        self.running = False

    def start(self):
        try:
            self.sock.bind((self.host, self.port))
            self.running = True
            threading.Thread(target=self._listen, daemon=True).start()
            print(f"[VoiceServer] In ascolto su UDP {self.host}:{self.port}")
        except Exception as e:
            print(f"[VoiceServer] Errore avvio server UDP: {e}")

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        print("[VoiceServer] Fermato.")

    def _listen(self):
        while self.running:
            try:
                # 2048 buffer should be enough for blocksize=512 (1024 bytes)
                data, addr = self.sock.recvfrom(4096)
                if data == b'JOIN':
                    if addr not in self.clients:
                        print(f"[VoiceServer] Client connesso: {addr}")
                        self.clients.add(addr)
                    continue
                elif data == b'LEAVE':
                    if addr in self.clients:
                        print(f"[VoiceServer] Client disconnesso: {addr}")
                        self.clients.remove(addr)
                    continue
                
                if addr not in self.clients:
                    self.clients.add(addr)

                # Broadcast audio to all OTHER clients
                for c in list(self.clients):
                    if c != addr:
                        try:
                            self.sock.sendto(data, c)
                        except Exception:
                            pass
            except ConnectionResetError:
                # Disconnessione ICMP su Windows: non interrompere il loop
                continue
            except OSError:
                if not self.running:
                    break
                continue
            except Exception as e:
                if self.running:
                    print(f"[VoiceServer] Errore recv: {e}")
