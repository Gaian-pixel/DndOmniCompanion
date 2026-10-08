# game_state.py
import threading
import json

class Player:
    def __init__(self, name, addr=None, conn=None):
        self.name = name
        self.addr = addr
        self.conn = conn
        self.position = [0, 0] # Ora rappresenta le coordinate esagonali [q, r]
        self.hp = 10
        self.max_hp = 10
        self.initiative = 0
        self.full_sheet = None
        self.conditions = []
        self.travel_role = "Nessuna"

    def to_dict(self):
        return {
            "name": self.name, 
            "position": self.position,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "initiative": self.initiative,
            "full_sheet": self.full_sheet,
            "conditions": self.conditions,
            "travel_role": getattr(self, "travel_role", "Nessuna")
        }

class GameState:
    def __init__(self, gui_queue):
        self.players = []
        self.lock = threading.Lock()
        self.gui_queue = gui_queue
        self.current_map = None # NUOVO: conterrà i dati della mappa caricata
        self.combat_active = False
        self.turn_index = 0
        self.round_number = 1
        self.active_aoes = []
        self.time_day = 1
        self.time_hour = 8

    def _trigger_gui_update(self):
        """Notifica alla GUI che il suo stato principale deve essere ridisegnato."""
        self.gui_queue.put({"type": "UPDATE_STATE"})

    def start_combat(self, participant_names=None):
        with self.lock:
            self.combat_active = True
            self.round_number = 1
            self.turn_index = 0
            if participant_names is not None:
                for p in self.players:
                    p.in_combat = (p.name in participant_names)
            else:
                for p in self.players:
                    p.in_combat = True
                    
            # Ordina i giocatori in combattimento per iniziativa decrescente, e sposta gli altri in fondo
            self.players.sort(key=lambda p: (getattr(p, 'in_combat', True), p.initiative), reverse=True)
        self._trigger_gui_update()

    def end_combat(self):
        with self.lock:
            self.combat_active = False
            for p in self.players:
                p.in_combat = False
        self._trigger_gui_update()
        
    def _get_combatants(self):
        return [p for p in self.players if getattr(p, 'in_combat', True)]

    def next_turn(self):
        with self.lock:
            combatants = self._get_combatants()
            if not self.combat_active or not combatants: return
            self.turn_index += 1
            if self.turn_index >= len(combatants):
                self.turn_index = 0
                self.round_number += 1
        self._trigger_gui_update()

    def prev_turn(self):
        with self.lock:
            combatants = self._get_combatants()
            if not self.combat_active or not combatants: return
            self.turn_index -= 1
            if self.turn_index < 0:
                self.turn_index = len(combatants) - 1
                self.round_number = max(1, self.round_number - 1)
        self._trigger_gui_update()

    def get_current_turn_player(self):
        with self.lock:
            combatants = self._get_combatants()
            if not self.combat_active or not combatants: return None
            if 0 <= self.turn_index < len(combatants):
                return combatants[self.turn_index]
            return None

    def log_dm_message(self, message):
        """Invia un messaggio di log da visualizzare nel pannello chat del DM."""
        self.gui_queue.put({"type": "LOG_MESSAGE", "payload": message})

    def load_map(self, map_data):
        """Carica i dati della mappa e aggiorna lo stato."""
        with self.lock:
            if "fow_enabled" not in map_data:
                map_data["fow_enabled"] = False
            if "fow_revealed" not in map_data:
                map_data["fow_revealed"] = []
            
            # Mantiene uno stato locale "draft" della nebbia per il master
            map_data["fow_draft"] = map_data["fow_revealed"][:]
                
            self.current_map = map_data
            # Resetta la posizione dei giocatori quando carichi una nuova mappa
            for p in self.players:
                p.position = [0, 0]
        self._trigger_gui_update()


    def add_player(self, player):
        with self.lock:
            self.players.append(player)
        self._trigger_gui_update()

    def remove_player(self, player_to_remove):
        with self.lock:
            idx_to_remove = -1
            for i, p in enumerate(self.players):
                if p.name == player_to_remove.name:
                    idx_to_remove = i
                    break
            if idx_to_remove != -1:
                self.players.pop(idx_to_remove)
                if getattr(self, "combat_active", False):
                    if idx_to_remove < self.turn_index:
                        self.turn_index -= 1
                    elif idx_to_remove == self.turn_index and self.turn_index >= len(self.players):
                        self.turn_index = 0
                        self.round_number += 1
        self._trigger_gui_update()

    def disconnect_player(self, player_to_disconnect):
        with self.lock:
            for p in self.players:
                if p.name == player_to_disconnect.name:
                    p.conn = None
                    p.addr = None
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
                "map": self.current_map,
                "combat_active": self.combat_active,
                "turn_index": self.turn_index,
                "round_number": self.round_number,
                "active_aoes": self.active_aoes
            }

    def move_player(self, name, new_pos):
        player = self.find_player(name)
        if player:
            with self.lock:
                player.position = new_pos
            self._trigger_gui_update()
            return True
        return False

    def add_aoe(self, aoe_data):
        with self.lock:
            self.active_aoes.append(aoe_data)
        self._trigger_gui_update()

    def clear_aoes(self):
        with self.lock:
            self.active_aoes = []
        self.time_day = 1
        self.time_hour = 8
        self._trigger_gui_update()

    def save_session(self, filepath):
        """Salva lo stato corrente in un file JSON."""
        state = self.get_state_dict()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)
        self.log_dm_message(f"[SISTEMA] Sessione salvata in {filepath}")

    def load_session(self, filepath):
        """Carica lo stato da un file JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        with self.lock:
            self.current_map = state.get("map")
            self.combat_active = state.get("combat_active", False)
            self.turn_index = state.get("turn_index", 0)
            self.round_number = state.get("round_number", 1)
            loaded_players = []
            for p_data in state.get("players", []):
                # Cerchiamo se il giocatore è già tra quelli connessi
                existing = None
                for ep in self.players:
                    if ep.name == p_data["name"]:
                        existing = ep
                        break
                
                if existing:
                    existing.position = p_data.get("position", [0, 0])
                    existing.hp = p_data.get("hp", 10)
                    existing.max_hp = p_data.get("max_hp", 10)
                    existing.initiative = p_data.get("initiative", 0)
                    existing.full_sheet = p_data.get("full_sheet")
                    existing.conditions = p_data.get("conditions", [])
                    loaded_players.append(existing)
                else:
                    p = Player(name=p_data["name"])
                    p.position = p_data.get("position", [0, 0])
                    p.hp = p_data.get("hp", 10)
                    p.max_hp = p_data.get("max_hp", 10)
                    p.initiative = p_data.get("initiative", 0)
                    p.full_sheet = p_data.get("full_sheet")
                    p.conditions = p_data.get("conditions", [])
                    loaded_players.append(p)
            self.players = loaded_players
        
        self._trigger_gui_update()
        self.log_dm_message(f"[SISTEMA] Sessione caricata da {filepath}")



