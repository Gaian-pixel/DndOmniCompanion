# game_state.py
import threading

import threading

class Player:
    def __init__(self, name, addr, conn):
        self.name = name
        self.addr = addr
        self.conn = conn
        self.position = [0, 0] # Ora rappresenta le coordinate esagonali [q, r]

    def to_dict(self):
        return {"name": self.name, "position": self.position}

class GameState:
    def __init__(self, gui_queue):
        self.players = []
        self.lock = threading.Lock()
        self.gui_queue = gui_queue
        self.current_map = None # NUOVO: conterrà i dati della mappa caricata

    def _trigger_gui_update(self):
        self.gui_queue.put({"type": "UPDATE_STATE"})

    def log_dm_message(self, message):
        self.gui_queue.put({"type": "LOG_MESSAGE", "payload": message})

    def load_map(self, map_data):
        """Carica i dati della mappa e aggiorna lo stato."""
        with self.lock:
            self.current_map = map_data
            # Resetta la posizione dei giocatori quando carichi una nuova mappa
            for p in self.players:
                p.position = [0, 0]
        self._trigger_gui_update()

    def _trigger_gui_update(self):
        """Notifica alla GUI che il suo stato principale deve essere ridisegnato."""
        self.gui_queue.put({"type": "UPDATE_STATE"})

    def log_dm_message(self, message):
        """Invia un messaggio di log da visualizzare nel pannello chat del DM."""
        self.gui_queue.put({"type": "LOG_MESSAGE", "payload": message})

    def add_player(self, player):
        with self.lock:
            self.players.append(player)
        self._trigger_gui_update()

    def remove_player(self, player_to_remove):
        with self.lock:
            self.players = [p for p in self.players if p.name != player_to_remove.name]
        self._trigger_gui_update()

    def find_player(self, name):
        with self.lock:
            for p in self.players:
                if p.name == name:
                    return p
        return None

    def get_all_players(self):
        with self.lock:
            return self.players[:]

    def get_state_dict(self):
        """Restituisce una rappresentazione dell'intero stato del gioco come dizionario."""
        with self.lock:
            return {
                "players": [p.to_dict() for p in self.players],
                "map": self.current_map  # <-- ECCO LA RIGA MANCANTE E CORRETTA
            }

    def move_player(self, name, new_pos):
        player = self.find_player(name)
        if player:
            with self.lock:
                player.position = new_pos
            self._trigger_gui_update()
            return True
        return False