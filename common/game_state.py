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
        self.condition_durations = {}
        self.travel_role = "Nessuna"
        self.is_hidden = False
        self.size = 1
        self.aura_radius = 0
        self.aura_color = "yellow"
        self.vision_radius = 6
        self.is_party_member = False
        self.owner = None

    def to_dict(self):
        return {
            "name": self.name, 
            "position": self.position,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "initiative": self.initiative,
            "full_sheet": self.full_sheet,
            "conditions": self.conditions,
            "condition_durations": getattr(self, "condition_durations", {}),
            "travel_role": getattr(self, "travel_role", "Nessuna"),
            "is_hidden": getattr(self, "is_hidden", False),
            "size": getattr(self, "size", 1),
            "aura_radius": getattr(self, "aura_radius", 0),
            "aura_color": getattr(self, "aura_color", "yellow"),
            "vision_radius": getattr(self, "vision_radius", 6),
            "avatar_b64": self.full_sheet.get("avatar_b64") if self.full_sheet else None,
            "is_party_member": getattr(self, "is_party_member", False)
        }

class GameState:
    def __init__(self, gui_queue):
        self.players = []
        self.lock = threading.Lock()
        self.gui_queue = gui_queue
        self.maps = {}
        self.active_map_id = "default"
        self.current_map = None # NUOVO: conterrà i dati della mappa caricata
        self.combat_active = False
        self.turn_index = 0
        self.round_number = 1
        self.active_aoes = []
        self.time_day = 1
        self.time_month = 1
        self.time_year = 1492
        self.time_hour = 8
        self.weather = "Sereno"
        self.calendar_events = {}
        self.quests = []
        self.shops = {}  # dict of shop_name: {"type": "blacksmith", "items": [{"name": "Sword", "price": 15, "qty": 1}], "gold": 100}
        self.travel_hours_today = 0
        
    def add_calendar_event(self, text):
        date_key = f"{self.time_year}-{self.time_month}-{self.time_day}"
        if not hasattr(self, 'calendar_events'):
            self.calendar_events = {}
        if date_key not in self.calendar_events:
            self.calendar_events[date_key] = []
        self.calendar_events[date_key].append(f"[{self.time_hour:02d}:00] {text}")

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
            spawn_pt = map_data.get("spawn_point", [0, 0])
            for p in self.players:
                p.position = list(spawn_pt)
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
                "active_aoes": self.active_aoes,
                "time_day": getattr(self, 'time_day', 1),
                "time_month": getattr(self, 'time_month', 1),
                "time_year": getattr(self, 'time_year', 1492),
                "time_hour": getattr(self, 'time_hour', 8),
                "weather": getattr(self, 'weather', "Sereno"),
                "calendar_events": getattr(self, 'calendar_events', {}),
                "quests": getattr(self, 'quests', []),
                "shops": getattr(self, 'shops', {}),
                "travel_hours_today": getattr(self, 'travel_hours_today', 0)
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
            self.time_day = state.get("time_day", 1)
            self.time_month = state.get("time_month", 1)
            self.time_year = state.get("time_year", 1492)
            self.time_hour = state.get("time_hour", 8)
            self.weather = state.get("weather", "Sereno")
            self.calendar_events = state.get("calendar_events", {})
            self.quests = state.get("quests", [])
            self.shops = state.get("shops", {})
            self.travel_hours_today = state.get("travel_hours_today", 0)
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
                    existing.vision_radius = p_data.get("vision_radius", 6)
                    existing.aura_radius = p_data.get("aura_radius", 0)
                    existing.aura_color = p_data.get("aura_color", "yellow")
                    existing.is_party_member = p_data.get("is_party_member", False)
                    existing.owner = p_data.get("owner", None)
                    loaded_players.append(existing)
                else:
                    p = Player(name=p_data["name"])
                    p.position = p_data.get("position", [0, 0])
                    p.hp = p_data.get("hp", 10)
                    p.max_hp = p_data.get("max_hp", 10)
                    p.initiative = p_data.get("initiative", 0)
                    p.full_sheet = p_data.get("full_sheet")
                    p.conditions = p_data.get("conditions", [])
                    p.vision_radius = p_data.get("vision_radius", 6)
                    p.aura_radius = p_data.get("aura_radius", 0)
                    p.aura_color = p_data.get("aura_color", "yellow")
                    p.is_party_member = p_data.get("is_party_member", False)
                    p.owner = p_data.get("owner", None)
                    loaded_players.append(p)
            self.players = loaded_players
        
        self._trigger_gui_update()
        self.log_dm_message(f"[SISTEMA] Sessione caricata da {filepath}")




    def switch_map(self, map_name):
        if map_name in self.maps:
            self.active_map_id = map_name
            self.current_map = self.maps[map_name]
            self._trigger_gui_update()
            
            from common.protocol import make_map_data_update_broadcast, make_chat_broadcast
            from common.network_utils import broadcast
            broadcast(self, make_map_data_update_broadcast(self.current_map))
            broadcast(self, make_chat_broadcast("Sistema", f"Il DM ha cambiato la mappa in: {map_name}"))
