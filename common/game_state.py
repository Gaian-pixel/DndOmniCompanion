# game_state.py
import os
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
        self.temp_hp = 0
        self.damage_resistances = []
        self.damage_immunities = []
        self.damage_vulnerabilities = []
        self.exhaustion_level = 0
        self.initiative = 0
        self.full_sheet = None
        self.conditions = []
        self.condition_durations = {}
        self.active_effects = []
        self.travel_role = "Nessuna"
        self.marching_order = "Centro"
        self.is_hidden = False
        self.size = 1
        self.aura_radius = 0
        self.aura_color = "yellow"
        self.vision_radius = 6
        self.light_radius = 0
        self.light_color = "#FFA500"
        self.legendary_resistances_max = 0
        self.legendary_resistances_current = 0
        self.legendary_actions_max = 0
        self.legendary_actions_current = 0
        self.is_party_member = False
        self.owner = None
        self.speed = 30
        self.speed_unit = None
        self.movement_spent_this_turn = 0
        self.has_acted_this_turn = False
        self.layer = "token"
        self.has_darkvision = None
        self.has_lair_actions = False
        self.companion_type = None
        self.master_name = None
        self.in_pocket_dimension = False
        self.can_attack = True
        self.is_companion = False



    def check_has_darkvision(self) -> bool:
        """Determina se il personaggio possiede Scurovisione secondo le regole D&D 5e."""
        if getattr(self, "has_darkvision", None) is not None:
            return bool(self.has_darkvision)
        conds = [str(c).lower() for c in getattr(self, "conditions", [])]
        if any("scurovisione" in c or "darkvision" in c for c in conds):
            return True
        sheet = getattr(self, "full_sheet", None)
        if isinstance(sheet, dict):
            race = str(sheet.get("race", "")).lower()
            dv_races = ("elfo", "elf", "nano", "dwarf", "mezzelfo", "half-elf", "mezzorco", "half-orc", "gnomo", "gnome", "tiefling", "drow", "duergar")
            if any(r in race for r in dv_races):
                return True
            senses = str(sheet.get("senses", "")).lower()
            if "scurovisione" in senses or "darkvision" in senses:
                return True
            traits = [str(t).lower() for t in sheet.get("traits", [])]
            if any("scurovisione" in t or "darkvision" in t for t in traits):
                return True
            feats = [str(f).lower() for f in sheet.get("features", [])]
            if any("scurovisione" in f or "darkvision" in f for f in feats):
                return True
        return getattr(self, "vision_radius", 6) > 6

    def add_effect(self, effect_dict: dict) -> dict:
        """Aggiunge o aggiorna un effetto attivo (5e RAW) sincronizzando condizioni e durate."""
        if not hasattr(self, "active_effects") or not isinstance(self.active_effects, list):
            self.active_effects = []
        if not hasattr(self, "conditions") or not isinstance(self.conditions, list):
            self.conditions = []
        if not hasattr(self, "condition_durations") or not isinstance(self.condition_durations, dict):
            self.condition_durations = {}
            
        import uuid
        eff = dict(effect_dict)
        if not eff.get("id"):
            eff["id"] = f"fx_{uuid.uuid4().hex[:8]}"
            
        eff_name = eff.get("name", "")
        # Rimuovi eventuale effetto duplicato con stesso id o stesso nome dallo stesso incantatore
        self.active_effects = [
            e for e in self.active_effects 
            if e.get("id") != eff["id"] and not (e.get("name") == eff_name and e.get("source") == eff.get("source") and eff_name)
        ]
        self.active_effects.append(eff)
        
        # Sincronizza condizione associata
        cond = eff.get("condition")
        dur = eff.get("duration_rounds")
        if cond:
            if cond not in self.conditions:
                self.conditions.append(cond)
            if dur is not None and dur > 0:
                self.condition_durations[cond] = dur
        if eff_name and dur is not None and dur > 0:
            self.condition_durations[eff_name] = dur
            
        return eff

    def remove_effect(self, effect_id_or_name: str):
        """Rimuove un effetto attivo per ID o per nome e pulisce la condizione associata se non più applicata da altri effetti."""
        if not hasattr(self, "active_effects") or not isinstance(self.active_effects, list):
            return None
        target_idx = None
        for i, eff in enumerate(self.active_effects):
            if eff.get("id") == effect_id_or_name or eff.get("name") == effect_id_or_name:
                target_idx = i
                break
        if target_idx is None:
            return None
            
        removed = self.active_effects.pop(target_idx)
        cond = removed.get("condition")
        if cond and hasattr(self, "conditions") and isinstance(self.conditions, list):
            other_has_cond = any(e.get("condition") == cond for e in self.active_effects)
            if not other_has_cond and cond in self.conditions:
                self.conditions.remove(cond)
            if not other_has_cond and hasattr(self, "condition_durations") and cond in self.condition_durations:
                del self.condition_durations[cond]
                
        rem_name = removed.get("name")
        if rem_name and hasattr(self, "condition_durations") and rem_name in self.condition_durations:
            del self.condition_durations[rem_name]
            
        return removed

    def get_effect(self, effect_id_or_name: str):
        if not hasattr(self, "active_effects") or not isinstance(self.active_effects, list):
            return None
        for eff in self.active_effects:
            if eff.get("id") == effect_id_or_name or eff.get("name") == effect_id_or_name:
                return eff
        return None

    def get_active_effects(self) -> list:
        return list(getattr(self, "active_effects", []))

    def to_dict(self):
        return {
            "name": self.name, 
            "position": self.position,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "temp_hp": getattr(self, "temp_hp", 0),
            "damage_resistances": getattr(self, "damage_resistances", []),
            "damage_immunities": getattr(self, "damage_immunities", []),
            "damage_vulnerabilities": getattr(self, "damage_vulnerabilities", []),
            "exhaustion_level": getattr(self, "exhaustion_level", 0),
            "initiative": self.initiative,
            "full_sheet": self.full_sheet,
            "conditions": self.conditions,
            "condition_durations": getattr(self, "condition_durations", {}),
            "active_effects": [dict(e) for e in getattr(self, "active_effects", [])],
            "travel_role": getattr(self, "travel_role", "Nessuna"),
            "marching_order": getattr(self, "marching_order", "Centro"),
            "is_hidden": getattr(self, "is_hidden", False),
            "size": getattr(self, "size", 1),
            "aura_radius": getattr(self, "aura_radius", 0),
            "aura_color": getattr(self, "aura_color", "yellow"),
            "vision_radius": getattr(self, "vision_radius", 6),
            "light_radius": getattr(self, "light_radius", 0),
            "light_color": getattr(self, "light_color", "#FFA500"),
            "legendary_resistances_max": getattr(self, "legendary_resistances_max", 0),
            "legendary_resistances_current": getattr(self, "legendary_resistances_current", 0),
            "legendary_actions_max": getattr(self, "legendary_actions_max", 0),
            "legendary_actions_current": getattr(self, "legendary_actions_current", 0),
            "avatar_b64": getattr(self, "avatar_b64", None) or (self.full_sheet.get("avatar_b64") if isinstance(getattr(self, "full_sheet", None), dict) else None),
            "is_party_member": getattr(self, "is_party_member", False),
            "owner": getattr(self, "owner", None),
            "speed": getattr(self, "speed", 30),
            "speed_unit": getattr(self, "speed_unit", None),
            "layer": getattr(self, "layer", "token"),
            "has_darkvision": getattr(self, "has_darkvision", None),
            "has_lair_actions": getattr(self, "has_lair_actions", False),
            "companion_type": getattr(self, "companion_type", None),
            "master_name": getattr(self, "master_name", None),
            "in_pocket_dimension": getattr(self, "in_pocket_dimension", False),
            "can_attack": getattr(self, "can_attack", True),
            "is_companion": getattr(self, "is_companion", False)
        }

    @classmethod
    def from_dict(cls, data):
        p = cls(data.get("name", "Unknown"))
        p.position = data.get("position", [0, 0])
        p.hp = data.get("hp", 10)
        p.max_hp = data.get("max_hp", 10)
        p.temp_hp = data.get("temp_hp", 0)
        p.initiative = data.get("initiative", 0)
        p.full_sheet = data.get("full_sheet", None)
        p.conditions = data.get("conditions", [])
        p.condition_durations = data.get("condition_durations", {})
        p.active_effects = data.get("active_effects", [])
        p.damage_resistances = data.get("damage_resistances", [])
        p.damage_immunities = data.get("damage_immunities", [])
        p.damage_vulnerabilities = data.get("damage_vulnerabilities", [])
        p.exhaustion_level = data.get("exhaustion_level", 0)
        p.travel_role = data.get("travel_role", "Nessuna")
        p.marching_order = data.get("marching_order", "Centro")
        p.is_hidden = data.get("is_hidden", False)
        p.size = data.get("size", 1)
        p.aura_radius = data.get("aura_radius", 0)
        p.aura_color = data.get("aura_color", "yellow")
        p.vision_radius = data.get("vision_radius", 6)
        p.light_radius = data.get("light_radius", 0)
        p.light_color = data.get("light_color", "#FFA500")
        p.legendary_resistances_max = data.get("legendary_resistances_max", 0)
        p.legendary_resistances_current = data.get("legendary_resistances_current", 0)
        p.legendary_actions_max = data.get("legendary_actions_max", 0)
        p.legendary_actions_current = data.get("legendary_actions_current", 0)
        p.is_party_member = data.get("is_party_member", False)
        p.owner = data.get("owner", None)
        p.speed = data.get("speed", 30)
        p.speed_unit = data.get("speed_unit", None)
        p.layer = data.get("layer", "token")
        p.has_darkvision = data.get("has_darkvision", None)
        p.has_lair_actions = data.get("has_lair_actions", False)
        p.avatar_b64 = data.get("avatar_b64", None)
        p.companion_type = data.get("companion_type", None)
        p.master_name = data.get("master_name", None)
        p.in_pocket_dimension = data.get("in_pocket_dimension", False)
        p.can_attack = data.get("can_attack", True)
        p.is_companion = data.get("is_companion", False)
        return p



def player_has_darkvision(player) -> bool:
    """Verifica se una creatura o token possiede Scurovisione attiva (D&D 5e)."""
    if hasattr(player, "check_has_darkvision"):
        return player.check_has_darkvision()
    return False

class GameState:
    def __init__(self, gui_queue):
        self.players = []
        self.lock = threading.RLock()
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
        self.time_minute = 0
        self.time_second = 0
        self.weather = "Sereno"
        self.calendar_events = {}
        self.quests = []
        self.handouts = []
        self.shops = {}  # dict of shop_name: {"type": "blacksmith", "items": [{"name": "Sword", "price": 15, "qty": 1}], "gold": 100}
        self.travel_hours_today = 0
        self.travel_pace = "Normale"
        self.travel_terrain = "Foresta"
        self.travel_biome = "foresta"
        self.travel_danger = "moderate"
        self.travel_miles_today = 0
        self.camp_watch_shifts = {}
        self.camp_has_campfire = True
        self.active_campaign = None
        self.campaign_starter_kit = []
        self.automation_mode = "full" # "manual" | "hybrid" | "full"
        self.automation_settings = {
            "auto_apply_damage": True,
            "auto_apply_aoe_damage": True,
            "auto_resolve_doors": True,
            "strict_turn_lock": False,
            "strict_movement_limits": True,
            "auto_prompt_reactions": True,
            "auto_concentration_check": True,
            "auto_death_saves": True,
            "auto_calc_advantage": True,
            "auto_explore_fow": True,
            "auto_apply_rest_recovery": True,
            "auto_advance_time": True,
            "auto_day_night_cycle": True
        }
        self.pending_damages = {} # id -> dict
        self.pending_doors = {}   # id -> dict

    def set_automation_mode(self, mode: str, custom_settings: dict = None):
        """Imposta il profilo di automazione della campagna (manual, hybrid, full) e aggiorna i flag."""
        with self.lock:
            self.automation_mode = mode
        if mode == "manual":
            self.automation_settings = {
                "auto_apply_damage": False,
                "auto_apply_aoe_damage": False,
                "auto_resolve_doors": False,
                "strict_turn_lock": False,
                "strict_movement_limits": False,
                "auto_prompt_reactions": False,
                "auto_concentration_check": False,
                "auto_death_saves": False,
                "auto_calc_advantage": False,
                "auto_explore_fow": False,
                "auto_apply_rest_recovery": False,
                "auto_advance_time": False,
                "auto_day_night_cycle": False
            }
        elif mode == "full":
            self.automation_settings = {
                "auto_apply_damage": True,
                "auto_apply_aoe_damage": True,
                "auto_resolve_doors": True,
                "strict_turn_lock": True,
                "strict_movement_limits": True,
                "auto_prompt_reactions": True,
                "auto_concentration_check": True,
                "auto_death_saves": True,
                "auto_calc_advantage": True,
                "auto_explore_fow": True,
                "auto_apply_rest_recovery": True,
                "auto_advance_time": True,
                "auto_day_night_cycle": True
            }
        else: # "hybrid" (predefinito)
            self.automation_mode = "hybrid"
            self.automation_settings = {
                "auto_apply_damage": False,
                "auto_apply_aoe_damage": False,
                "auto_resolve_doors": True,
                "strict_turn_lock": False,
                "strict_movement_limits": True,
                "auto_prompt_reactions": True,
                "auto_concentration_check": True,
                "auto_death_saves": True,
                "auto_calc_advantage": True,
                "auto_explore_fow": True,
                "auto_apply_rest_recovery": True,
                "auto_advance_time": True,
                "auto_day_night_cycle": True
            }
        if custom_settings and isinstance(custom_settings, dict):
            self.automation_settings.update(custom_settings)
        self._trigger_gui_update()
        
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
                    p.movement_spent_this_turn = 0
                    p.has_acted_this_turn = False
            else:
                for p in self.players:
                    p.in_combat = True
                    p.movement_spent_this_turn = 0
                    p.has_acted_this_turn = False
                    
            # Ordina i giocatori in combattimento per iniziativa decrescente, e sposta gli altri in fondo
            self.players.sort(key=lambda p: (getattr(p, 'in_combat', True), p.initiative), reverse=True)
            active = self.get_current_turn_player()
            if active:
                active.movement_spent_this_turn = 0
                active.has_acted_this_turn = False
        self._trigger_gui_update()

    def end_combat(self):
        temp_combat_conds = {"Scatto", "Disimpegno", "Schivata", "Aiutato", "Dash", "Disengage", "Dodge", "Helped", "Scudo"}
        with self.lock:
            self.combat_active = False
            for p in self.players:
                p.in_combat = False
                p.movement_spent_this_turn = 0
                p.has_acted_this_turn = False
                if hasattr(p, "conditions") and p.conditions:
                    p.conditions = [c for c in p.conditions if c not in temp_combat_conds]
                if getattr(p, "full_sheet", None) and isinstance(p.full_sheet.get("conditions"), list):
                    p.full_sheet["conditions"] = [c for c in p.full_sheet["conditions"] if c not in temp_combat_conds]
        self._trigger_gui_update()
        
    def _get_combatants(self):
        return [p for p in self.players if getattr(p, 'in_combat', True)]

    def next_turn(self):
        end_of_turn_conds = {"Scatto", "Disimpegno", "Dash", "Disengage"}
        start_of_turn_conds = {"Schivata", "Dodge", "Scatto", "Disimpegno", "Dash", "Disengage"}
        with self.lock:
            combatants = self._get_combatants()
            if not self.combat_active or not combatants: return
            if 0 <= self.turn_index < len(combatants):
                prev_active = combatants[self.turn_index]
                if hasattr(prev_active, "conditions") and prev_active.conditions:
                    prev_active.conditions = [c for c in prev_active.conditions if c not in end_of_turn_conds]
                if getattr(prev_active, "full_sheet", None) and isinstance(prev_active.full_sheet.get("conditions"), list):
                    prev_active.full_sheet["conditions"] = [c for c in prev_active.full_sheet["conditions"] if c not in end_of_turn_conds]
                if hasattr(prev_active, "active_effects") and isinstance(prev_active.active_effects, list):
                    expired_fx = []
                    for fx in prev_active.active_effects:
                        if fx.get("decrement_timing") == "end_of_turn" and fx.get("duration_rounds") is not None:
                            fx["duration_rounds"] -= 1
                            if fx["duration_rounds"] <= 0:
                                expired_fx.append(fx.get("id") or fx.get("name"))
                    for fx_id in expired_fx:
                        prev_active.remove_effect(fx_id)
            self.turn_index += 1
            round_advanced = False
            if self.turn_index >= len(combatants):
                self.turn_index = 0
                self.round_number += 1
                round_advanced = True
                auto_time = True
                if hasattr(self, "automation_settings") and isinstance(self.automation_settings, dict):
                    auto_time = self.automation_settings.get("auto_advance_time", True)
                if auto_time:
                    self.advance_game_time(seconds=6)

            if 0 <= self.turn_index < len(combatants):
                active = combatants[self.turn_index]
                active.movement_spent_this_turn = 0
                active.has_acted_this_turn = False
                active.has_reacted_this_turn = False
                active.sneak_attack_used_this_turn = False
                for c_p in combatants:
                    c_p.sneak_attack_used_this_turn = False
                if hasattr(active, "conditions") and active.conditions:
                    active.conditions = [c for c in active.conditions if c not in start_of_turn_conds and c not in ("Scudo", "Shield")]
                if getattr(active, "full_sheet", None) and isinstance(active.full_sheet.get("conditions"), list):
                    active.full_sheet["conditions"] = [c for c in active.full_sheet["conditions"] if c not in start_of_turn_conds and c not in ("Scudo", "Shield")]
                if hasattr(active, "active_effects") and isinstance(active.active_effects, list):
                    expired_start_fx = []
                    for fx in active.active_effects:
                        if fx.get("decrement_timing") == "start_of_turn" and fx.get("duration_rounds") is not None:
                            fx["duration_rounds"] -= 1
                            if fx["duration_rounds"] <= 0:
                                expired_start_fx.append(fx.get("id") or fx.get("name"))
                    for fx_id in expired_start_fx:
                        active.remove_effect(fx_id)

            if round_advanced:
                for p in self.players:
                    if hasattr(p, "condition_durations") and isinstance(p.condition_durations, dict):
                        expired = []
                        for cond, rounds_left in list(p.condition_durations.items()):
                            p.condition_durations[cond] = rounds_left - 1
                            if p.condition_durations[cond] <= 0:
                                expired.append(cond)
                        for cond in expired:
                            del p.condition_durations[cond]
                            if hasattr(p, "conditions") and cond in p.conditions:
                                p.conditions.remove(cond)
                    if hasattr(p, "active_effects") and isinstance(p.active_effects, list):
                        exp_round_fx = []
                        for fx in p.active_effects:
                            if fx.get("decrement_timing", "round_end") == "round_end" and fx.get("duration_rounds") is not None:
                                fx["duration_rounds"] -= 1
                                if fx["duration_rounds"] <= 0:
                                    exp_round_fx.append(fx.get("id") or fx.get("name"))
                        for fx_id in exp_round_fx:
                            p.remove_effect(fx_id)
        self._trigger_gui_update()

    def advance_game_time(self, seconds=0, minutes=0, hours=0, days=0):
        """Avanza l'orologio di gioco nel rispetto della cronologia e del calendario Harptos 5e."""
        with self.lock:
            if not hasattr(self, "time_minute"): self.time_minute = 0
            if not hasattr(self, "time_second"): self.time_second = 0
            
            self.time_second += seconds
            if self.time_second >= 60:
                minutes += self.time_second // 60
                self.time_second %= 60
                
            self.time_minute += minutes
            if self.time_minute >= 60:
                hours += self.time_minute // 60
                self.time_minute %= 60
                
            self.time_hour += hours
            if self.time_hour >= 24:
                days += self.time_hour // 24
                self.time_hour %= 24
                
            self.time_day += days
            if self.time_day > 30:
                months = self.time_day // 30
                self.time_day = ((self.time_day - 1) % 30) + 1
                self.time_month += months
                if self.time_month > 12:
                    self.time_year += (self.time_month - 1) // 12
                    self.time_month = ((self.time_month - 1) % 12) + 1
                    
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
            
            if "outdoor" not in map_data:
                map_name = str(map_data.get("name", "") or map_data.get("id", "")).lower()
                indoor_keywords = ("dungeon", "sotterraneo", "caverna", "cave", "crypt", "cripta", "indoor", "interno", "taverna", "tavern", "catacombe")
                map_data["outdoor"] = not any(kw in map_name for kw in indoor_keywords)
                
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
        target_name = player_to_remove if isinstance(player_to_remove, str) else getattr(player_to_remove, "name", None)
        with self.lock:
            idx_to_remove = -1
            for i, p in enumerate(self.players):
                if p.name == target_name:
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

    def disconnect_player(self, player_to_disconnect, conn=None):
        with self.lock:
            for p in self.players:
                if p.name == player_to_disconnect.name:
                    if conn is None or getattr(p, "conn", None) is conn:
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

    def get_companions_of(self, player_name: str):
        """Restituisce tutti i famigli, compagni o creature evocate controllate da un giocatore."""
        with self.lock:
            return [
                p for p in self.players 
                if getattr(p, "master_name", None) == player_name or 
                (getattr(p, "owner", None) == player_name and getattr(p, "is_companion", False))
            ]

    def get_state_dict(self, is_dm=True):
        """Restituisce una rappresentazione dell'intero stato del gioco come dizionario."""
        with self.lock:
            players_data = []
            for p in self.players:
                if not is_dm and getattr(p, "layer", "token") == "gm":
                    continue
                p_dict = p.to_dict()
                if not is_dm and p_dict.get("full_sheet"):
                    # Rimuovi segreti confidenziali del PG dai payload inviati ad altri giocatori
                    p_dict["full_sheet"] = dict(p_dict["full_sheet"])
                    p_dict["full_sheet"].pop("secret", None)
                players_data.append(p_dict)
            curr_turn = self.get_current_turn_player()
            turn_name = curr_turn.name if curr_turn else None
            if not is_dm and curr_turn and getattr(curr_turn, "layer", "token") == "gm":
                turn_name = "Sconosciuto"

            from common.network_utils import sanitize_map_for_players
            export_map = self.current_map if is_dm else (sanitize_map_for_players(self.current_map) if self.current_map else None)

            return {
                "players": players_data,
                "map": export_map,
                "combat_active": self.combat_active,
                "turn_index": self.turn_index,
                "turn_player_name": turn_name,
                "round_number": self.round_number,
                "active_aoes": self.active_aoes,
                "drawn_lines": getattr(self, "drawn_lines", []),
                "time_day": getattr(self, 'time_day', 1),
                "time_month": getattr(self, 'time_month', 1),
                "time_year": getattr(self, 'time_year', 1492),
                "time_hour": getattr(self, 'time_hour', 8),
                "time_minute": getattr(self, 'time_minute', 0),
                "time_second": getattr(self, 'time_second', 0),
                "weather": getattr(self, 'weather', "Sereno"),
                "calendar_events": getattr(self, 'calendar_events', {}) if is_dm else {},
                "quests": getattr(self, 'quests', []),
                "handouts": getattr(self, 'handouts', []),
                "shops": getattr(self, 'shops', {}),
                "travel_hours_today": getattr(self, 'travel_hours_today', 0),
                "travel_pace": getattr(self, 'travel_pace', "Normale"),
                "travel_terrain": getattr(self, 'travel_terrain', "Foresta"),
                "travel_biome": getattr(self, 'travel_biome', "foresta"),
                "travel_danger": getattr(self, 'travel_danger', "moderate"),
                "travel_miles_today": getattr(self, 'travel_miles_today', 0),
                "camp_watch_shifts": getattr(self, 'camp_watch_shifts', {}),
                "camp_has_campfire": getattr(self, 'camp_has_campfire', True),
                "active_campaign_folder": getattr(self.active_campaign, 'folder_path', None) if getattr(self, 'active_campaign', None) else None,
                "automation_mode": getattr(self, "automation_mode", "hybrid"),
                "automation_settings": getattr(self, "automation_settings", {}),
                "pending_damages": getattr(self, "pending_damages", {}) if is_dm else {},
                "pending_doors": getattr(self, "pending_doors", {}) if is_dm else {}
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
        """Salva lo stato corrente in un file JSON in modo atomico."""
        from common.file_utils import atomic_save_json
        import copy
        with self.lock:
            state = copy.deepcopy(self.get_state_dict())
        atomic_save_json(filepath, state, indent=4, ensure_ascii=False)
        self.log_dm_message(f"[SISTEMA] Sessione salvata in {filepath}")

    def load_session(self, filepath):
        """Carica lo stato da un file JSON."""
        from common.file_utils import load_json
        state = load_json(filepath, default={})
        if not state:
            return
        
        with self.lock:
            self.current_map = state.get("map")
            self.combat_active = state.get("combat_active", False)
            self.turn_index = state.get("turn_index", 0)
            self.round_number = state.get("round_number", 1)
            self.time_day = state.get("time_day", 1)
            self.time_month = state.get("time_month", 1)
            self.time_year = state.get("time_year", 1492)
            self.time_hour = state.get("time_hour", 8)
            self.time_minute = state.get("time_minute", 0)
            self.time_second = state.get("time_second", 0)
            self.weather = state.get("weather", "Sereno")
            self.calendar_events = state.get("calendar_events", {})
            self.quests = state.get("quests", [])
            self.handouts = state.get("handouts", [])
            self.shops = state.get("shops", {})
            self.travel_hours_today = state.get("travel_hours_today", 0)
            self.travel_pace = state.get("travel_pace", "Normale")
            self.travel_terrain = state.get("travel_terrain", "Foresta")
            self.travel_biome = state.get("travel_biome", "foresta")
            self.travel_danger = state.get("travel_danger", "moderate")
            self.travel_miles_today = state.get("travel_miles_today", 0)
            self.camp_watch_shifts = state.get("camp_watch_shifts", {})
            self.camp_has_campfire = state.get("camp_has_campfire", True)
            if "automation_mode" in state:
                self.automation_mode = state.get("automation_mode", "hybrid")
            if "automation_settings" in state and isinstance(state["automation_settings"], dict):
                self.automation_settings = dict(state["automation_settings"])
            if "pending_damages" in state:
                self.pending_damages = state.get("pending_damages", {})
            if "pending_doors" in state:
                self.pending_doors = state.get("pending_doors", {})
            
            camp_folder = state.get("active_campaign_folder")
            if camp_folder and os.path.exists(camp_folder):
                try:
                    from common.campaign import Campaign
                    self.active_campaign = Campaign.load(camp_folder)
                except Exception as e:
                    print(f"[GAME_STATE] Errore ripristino campagna: {e}")
            
            loaded_players = []
            for p_data in state.get("players", []):
                # Cerchiamo se il giocatore è già tra quelli connessi
                existing = None
                for ep in self.players:
                    if ep.name == p_data.get("name"):
                        existing = ep
                        break
                
                if existing:
                    existing.position = p_data.get("position", [0, 0])
                    existing.hp = p_data.get("hp", 10)
                    existing.max_hp = p_data.get("max_hp", 10)
                    existing.temp_hp = p_data.get("temp_hp", 0)
                    existing.damage_resistances = p_data.get("damage_resistances", [])
                    existing.damage_immunities = p_data.get("damage_immunities", [])
                    existing.damage_vulnerabilities = p_data.get("damage_vulnerabilities", [])
                    existing.exhaustion_level = p_data.get("exhaustion_level", 0)
                    existing.initiative = p_data.get("initiative", 0)
                    existing.full_sheet = p_data.get("full_sheet")
                    existing.conditions = p_data.get("conditions", [])
                    existing.condition_durations = p_data.get("condition_durations", {})
                    existing.vision_radius = p_data.get("vision_radius", 6)
                    existing.aura_radius = p_data.get("aura_radius", 0)
                    existing.aura_color = p_data.get("aura_color", "yellow")
                    existing.is_party_member = p_data.get("is_party_member", False)
                    existing.travel_role = p_data.get("travel_role", "Nessuna")
                    existing.marching_order = p_data.get("marching_order", "Centro")
                    existing.light_radius = p_data.get("light_radius", 0)
                    existing.light_color = p_data.get("light_color", "#FFA500")
                    existing.legendary_resistances_max = p_data.get("legendary_resistances_max", 0)
                    existing.legendary_resistances_current = p_data.get("legendary_resistances_current", 0)
                    existing.legendary_actions_max = p_data.get("legendary_actions_max", 0)
                    existing.legendary_actions_current = p_data.get("legendary_actions_current", 0)
                    existing.speed = p_data.get("speed", 30)
                    existing.speed_unit = p_data.get("speed_unit", None)
                    existing.layer = p_data.get("layer", "token")
                    existing.has_darkvision = p_data.get("has_darkvision", None)
                    existing.has_lair_actions = p_data.get("has_lair_actions", False)
                    existing.owner = p_data.get("owner", None)
                    loaded_players.append(existing)
                else:
                    loaded_players.append(Player.from_dict(p_data))
            self.players = loaded_players
        
        self._trigger_gui_update()
        self.log_dm_message(f"[SISTEMA] Sessione caricata da {filepath}")




    def switch_map(self, map_name):
        with self.lock:
            if map_name in self.maps:
                self.active_map_id = map_name
                self.current_map = self.maps[map_name]
                if "outdoor" not in self.current_map:
                    m_name = str(self.current_map.get("name", "") or map_name).lower()
                    indoor_keywords = ("dungeon", "sotterraneo", "caverna", "cave", "crypt", "cripta", "indoor", "interno", "taverna", "tavern", "catacombe")
                    self.current_map["outdoor"] = not any(kw in m_name for kw in indoor_keywords)
                cur_m = dict(self.current_map)
            else:
                return
        self._trigger_gui_update()
        
        from common.protocol import make_map_data_update_broadcast, make_chat_broadcast
        from common.network_utils import broadcast
        broadcast(self, make_map_data_update_broadcast(cur_m))
        broadcast(self, make_chat_broadcast("Sistema", f"Il DM ha cambiato la mappa in: {map_name}"))
