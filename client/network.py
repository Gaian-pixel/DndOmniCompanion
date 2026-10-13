import threading
import socket
from common.network_utils import send_message, receive_message

class ClientNetwork:
    def __init__(self, gui_queue, on_disconnect_callback):
        self.client_socket = None
        self.is_connected = False
        self.gui_queue = gui_queue
        self.on_disconnect_callback = on_disconnect_callback

    def connect(self, host, port):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))
        self.is_connected = True
        threading.Thread(target=self.listen_to_server, daemon=True).start()

    def listen_to_server(self):
        while self.is_connected:
            msg = receive_message(self.client_socket)
            if msg is None: break
            self.gui_queue.put(msg)
        self.is_connected = False
        if self.on_disconnect_callback:
            try:
                self.on_disconnect_callback()
            except Exception:
                pass

    def send(self, msg):
        if self.is_connected and self.client_socket:
            send_message(self.client_socket, msg)

    def disconnect(self):
        self.is_connected = False
        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None
