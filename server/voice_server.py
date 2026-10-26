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
        self.clients_last_seen = {}
        self.running = False

    @property
    def clients(self):
        return set(self.clients_last_seen.keys())

    @clients.setter
    def clients(self, val):
        import time
        now = time.time()
        self.clients_last_seen = {addr: now for addr in val}

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
        import time
        self.sock.settimeout(1.0)
        while self.running:
            try:
                now = time.time()
                # Prune client inattivi da oltre 10 secondi
                expired = [c for c, t in list(self.clients_last_seen.items()) if now - t > 10.0]
                for c in expired:
                    self.clients_last_seen.pop(c, None)

                data, addr = self.sock.recvfrom(4096)
                self.clients_last_seen[addr] = time.time()
                if data == b'JOIN':
                    print(f"[VoiceServer] Client connesso: {addr}")
                    continue
                elif data == b'LEAVE':
                    print(f"[VoiceServer] Client disconnesso: {addr}")
                    self.clients_last_seen.pop(addr, None)
                    continue

                # Broadcast audio a tutti gli ALTRI client attivi
                for c in list(self.clients_last_seen.keys()):
                    if c != addr:
                        try:
                            self.sock.sendto(data, c)
                        except Exception:
                            pass
            except (socket.timeout, TimeoutError):
                continue
            except ConnectionResetError:
                continue
            except OSError:
                if not self.running:
                    break
                continue
            except Exception as e:
                if self.running:
                    print(f"[VoiceServer] Errore recv: {e}")
