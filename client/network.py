import threading
import socket
from common.network_utils import send_message, receive_message


class ClientNetwork:
    DEFAULT_CONNECT_TIMEOUT = 6.0
    DEFAULT_READ_TIMEOUT = 20.0

    def __init__(self, gui_queue, on_disconnect_callback):
        self.client_socket = None
        self.is_connected = False
        self.gui_queue = gui_queue
        self.on_disconnect_callback = on_disconnect_callback
        self._sock_lock = threading.Lock()
        self._connect_generation = 0

    def connect(self, host, port, timeout: float = DEFAULT_CONNECT_TIMEOUT):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(float(timeout or self.DEFAULT_CONNECT_TIMEOUT))
        try:
            sock.connect((host, port))
        except Exception:
            try:
                sock.close()
            except Exception:
                pass
            raise
        if hasattr(socket, "SO_KEEPALIVE"):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            except Exception:
                pass
        try:
            sock.settimeout(self.DEFAULT_READ_TIMEOUT)
        except Exception:
            pass
        with self._sock_lock:
            self._connect_generation += 1
            gen = self._connect_generation
            self.client_socket = sock
            self.is_connected = True
        threading.Thread(target=self.listen_to_server, args=(sock, gen), daemon=True).start()

    def connect_async(self, host, port, on_success=None, on_error=None, timeout: float = DEFAULT_CONNECT_TIMEOUT):
        """Connect off the GUI thread so unreachable hosts never freeze Tkinter."""
        with self._sock_lock:
            self._connect_generation += 1
            req_gen = self._connect_generation

        def _worker():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(float(timeout or self.DEFAULT_CONNECT_TIMEOUT))
                try:
                    sock.connect((host, port))
                except Exception:
                    try:
                        sock.close()
                    except Exception:
                        pass
                    raise
                if hasattr(socket, "SO_KEEPALIVE"):
                    try:
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    except Exception:
                        pass
                try:
                    sock.settimeout(self.DEFAULT_READ_TIMEOUT)
                except Exception:
                    pass
                with self._sock_lock:
                    if req_gen != self._connect_generation:
                        try:
                            sock.close()
                        except Exception:
                            pass
                        return
                    self.client_socket = sock
                    self.is_connected = True
                threading.Thread(target=self.listen_to_server, args=(sock, req_gen), daemon=True).start()
                if on_success:
                    on_success()
            except Exception as exc:
                with self._sock_lock:
                    stale = (req_gen != self._connect_generation)
                if not stale and on_error:
                    on_error(exc)

        threading.Thread(target=_worker, daemon=True).start()
        return req_gen

    def cancel_pending_connect(self):
        with self._sock_lock:
            self._connect_generation += 1

    def _notify_disconnect_once(self, sock=None):
        notify = False
        with self._sock_lock:
            if sock is None or self.client_socket is sock:
                was_connected = self.is_connected
                self.is_connected = False
                old_sock = self.client_socket
                self.client_socket = None
                notify = was_connected
            else:
                old_sock = None
        if old_sock is not None:
            try:
                old_sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                old_sock.close()
            except Exception:
                pass
        if notify and self.on_disconnect_callback:
            try:
                self.on_disconnect_callback()
            except Exception:
                pass

    def listen_to_server(self, sock=None, gen=None):
        target_sock = sock or self.client_socket
        while self.is_connected and target_sock is not None:
            with self._sock_lock:
                if not self.is_connected or self.client_socket is not target_sock:
                    break
            try:
                try:
                    msg = receive_message(target_sock, raise_on_timeout=True)
                except TypeError as _te:
                    if "raise_on_timeout" not in str(_te):
                        raise
                    msg = receive_message(target_sock)
            except socket.timeout:
                # Application-level keepalive probe over idle TCP links
                if not self.is_connected:
                    break
                if not self.send({"type": "PING", "data": {}}):
                    break
                continue
            if msg is None:
                break
            if isinstance(msg, dict) and msg.get("type") == "PONG":
                continue
            if isinstance(msg, dict) and msg.get("type") == "PING":
                self.send({"type": "PONG", "data": {}})
                continue
            self.gui_queue.put(msg)
        self._notify_disconnect_once(target_sock)

    def send(self, msg) -> bool:
        with self._sock_lock:
            sock = self.client_socket
            connected = self.is_connected
        if not connected or not sock:
            return False
        ok = send_message(sock, msg)
        if ok is False:
            self._notify_disconnect_once(sock)
            return False
        return True

    def disconnect(self):
        with self._sock_lock:
            self._connect_generation += 1
            self.is_connected = False
            sock = self.client_socket
            self.client_socket = None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass
