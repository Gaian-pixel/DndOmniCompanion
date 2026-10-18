import socket
import threading
import sounddevice as sd

class VoiceClient:
    def __init__(self, server_ip, server_port=53912):
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind(('', 0))
        except Exception as e:
            print(f"[VoiceClient] Binding error: {e}")
        self.running = False
        self.is_muted = False
        self.is_deafened = False
        self.samplerate = 44100
        self.channels = 1
        self.chunk = 512 # small chunk to avoid UDP fragmentation

    def start(self):
        import os
        if os.environ.get("DND_MOCK_AUDIO") == "1":
            self.running = True
            print("[VoiceClient] (Mocked via DND_MOCK_AUDIO) Avviato.")
            return

        self.running = True
        try:
            self.sock.sendto(b'JOIN', (self.server_ip, self.server_port))
        except Exception as e:
            print(f"[VoiceClient] Errore connessione UDP: {e}")
            return
            
        self.record_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        
        self.record_thread.start()
        self.play_thread.start()
        print("[VoiceClient] Avviato.")

    def stop(self):
        import os
        if os.environ.get("DND_MOCK_AUDIO") == "1":
            self.running = False
            try:
                self.sock.close()
            except Exception:
                pass
            print("[VoiceClient] (Mocked via DND_MOCK_AUDIO) Fermato.")
            return

        self.running = False
        try:
            self.sock.sendto(b'LEAVE', (self.server_ip, self.server_port))
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass
        print("[VoiceClient] Fermato.")

    def _record_loop(self):
        try:
            with sd.RawInputStream(samplerate=self.samplerate, channels=self.channels, dtype='int16', blocksize=self.chunk) as stream:
                while self.running:
                    data, overflowed = stream.read(self.chunk)
                    if not self.is_muted:
                        try:
                            # converte i byte per essere spediti
                            data_bytes = bytes(data)
                            self.sock.sendto(data_bytes, (self.server_ip, self.server_port))
                        except Exception:
                            pass
        except sd.PortAudioError as e:
            print(f"[VoiceClient] Nessun microfono o errore audio in ingresso: {e}")
            self.is_muted = True
        except Exception as e:
            print(f"[VoiceClient] Errore registrazione audio: {e}")
            
    def _play_loop(self):
        try:
            self.sock.settimeout(1.0)
            with sd.RawOutputStream(samplerate=self.samplerate, channels=self.channels, dtype='int16', blocksize=self.chunk) as stream:
                while self.running:
                    try:
                        data, addr = self.sock.recvfrom(4096)
                        if not self.is_deafened and data not in (b'JOIN', b'LEAVE'):
                            stream.write(data)
                    except socket.timeout:
                        continue
                    except socket.error:
                        if not self.running:
                            break
        except sd.PortAudioError as e:
            print(f"[VoiceClient] Nessun dispositivo audio o errore in uscita: {e}")
            self.is_deafened = True
        except Exception as e:
            print(f"[VoiceClient] Errore riproduzione audio: {e}")
