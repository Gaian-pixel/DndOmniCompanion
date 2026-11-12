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
        self.ac = 10
        self.damage_resistances = []
        self.damage_immunities = []
        self.damage_vulnerabilities = []
        self.exhaustion_level = 0
        self.initiative = 0
        self.initiative_bonus = None
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
        self.elevation = 0
        # Estensioni D&D 5e RAW (PHB, DMG, MM)
        self.bonus_action_used_this_turn = False
        self.reckless_attack_active = False
        self.non_lethal_mode = False
        self.moved_straight_hexes = 0
        self.last_move_dir = None
        self.swallowed_by = None
        self.mount_name = None
        self.stealth_score = 0
        self.surprised = False
        self.spell_cast_bonus_action_this_turn = False
        self.spell_cast_action_level_this_turn = None
        self.bardic_inspiration_die = None
        self.relentless_rage_uses = 0
        self.frightful_immune_list = []
        self.hunger_days = 0
        self.water_days = 0
        self.breath_rounds_left = None
        self.chases_dashes_used = 0
        self.madness_effects = []
        self.injuries = []
        self.diseases = []
        self.is_submerged = False
        self.is_object = False
        self.damage_threshold = 0



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
            traits_raw = sheet.get("traits", [])
            traits = [traits_raw.lower()] if isinstance(traits_raw, str) else [str(t).lower() for t in traits_raw]
            if any("scurovisione" in t or "darkvision" in t for t in traits):
                return True
            feats_raw = sheet.get("features", [])
            feats = [feats_raw.lower()] if isinstance(feats_raw, str) else [str(f).lower() for f in feats_raw]
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

    def get_initiative_bonus(self) -> int:
        """Restituisce il modificatore fisso di Iniziativa (separato dal totale tirato in combattimento)."""
        if getattr(self, "initiative_bonus", None) is not None:
            try:
                return int(self.initiative_bonus)
            except (ValueError, TypeError):
                pass
        sheet = getattr(self, "full_sheet", None)
        if isinstance(sheet, dict):
            if sheet.get("initiative") is not None:
                try:
                    return int(sheet["initiative"])
                except (ValueError, TypeError):
                    pass
            attrs = sheet.get("attributes", {})
            if isinstance(attrs, dict) and ("DES" in attrs or "DEX" in attrs):
                try:
                    dex = int(attrs.get("DES", attrs.get("DEX", 10)))
                    return (dex - 10) // 2
                except (ValueError, TypeError):
                    pass
        try:
            return int(getattr(self, "initiative", 0) or 0)
        except (ValueError, TypeError):
            return 0

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
            "initiative_bonus": getattr(self, "initiative_bonus", None),
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
            "is_companion": getattr(self, "is_companion", False),
            "elevation": getattr(self, "elevation", 0),
            "ac": getattr(self, "ac", 10),
            "concentrating_on": getattr(self, "concentrating_on", None),
            "in_combat": getattr(self, "in_combat", False),
            "death_save_successes": getattr(self, "death_save_successes", 0),
            "death_save_failures": getattr(self, "death_save_failures", 0),
            "combat_initiative": getattr(self, "combat_initiative", None),
            "bonus_action_used_this_turn": getattr(self, "bonus_action_used_this_turn", False),
            "reckless_attack_active": getattr(self, "reckless_attack_active", False),
            "non_lethal_mode": getattr(self, "non_lethal_mode", False),
            "moved_straight_hexes": getattr(self, "moved_straight_hexes", 0),
            "last_move_dir": getattr(self, "last_move_dir", None),
            "swallowed_by": getattr(self, "swallowed_by", None),
            "mount_name": getattr(self, "mount_name", None),
            "stealth_score": getattr(self, "stealth_score", 0),
            "surprised": getattr(self, "surprised", False),
            "spell_cast_bonus_action_this_turn": getattr(self, "spell_cast_bonus_action_this_turn", False),
            "spell_cast_action_level_this_turn": getattr(self, "spell_cast_action_level_this_turn", None),
            "bardic_inspiration_die": getattr(self, "bardic_inspiration_die", None),
            "relentless_rage_uses": getattr(self, "relentless_rage_uses", 0),
            "frightful_immune_list": getattr(self, "frightful_immune_list", []),
            "hunger_days": getattr(self, "hunger_days", 0),
            "water_days": getattr(self, "water_days", 0),
            "breath_rounds_left": getattr(self, "breath_rounds_left", None),
            "chases_dashes_used": getattr(self, "chases_dashes_used", 0),
            "madness_effects": getattr(self, "madness_effects", []),
            "injuries": getattr(self, "injuries", []),
            "diseases": getattr(self, "diseases", []),
            "is_submerged": getattr(self, "is_submerged", False),
            "is_object": getattr(self, "is_object", False),
            "damage_threshold": getattr(self, "damage_threshold", 0),
        }

    @classmethod
    def from_dict(cls, data):
        p = cls(data.get("name", "Unknown"))
        p.position = data.get("position", [0, 0])
        p.elevation = data.get("elevation", 0)
        p.ac = data.get("ac", 10)
        p.concentrating_on = data.get("concentrating_on", None)
        p.in_combat = data.get("in_combat", False)
        p.death_save_successes = data.get("death_save_successes", 0)
        p.death_save_failures = data.get("death_save_failures", 0)
        p.combat_initiative = data.get("combat_initiative", None)
        p.hp = data.get("hp", 10)
        p.max_hp = data.get("max_hp", 10)
        p.temp_hp = data.get("temp_hp", 0)
        p.initiative = data.get("initiative", 0)
        p.initiative_bonus = data.get("initiative_bonus", None)
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
        p.bonus_action_used_this_turn = data.get("bonus_action_used_this_turn", False)
        p.reckless_attack_active = data.get("reckless_attack_active", False)
        p.non_lethal_mode = data.get("non_lethal_mode", False)
        p.moved_straight_hexes = data.get("moved_straight_hexes", 0)
        p.last_move_dir = data.get("last_move_dir", None)
        p.swallowed_by = data.get("swallowed_by", None)
        p.mount_name = data.get("mount_name", None)
        p.stealth_score = data.get("stealth_score", 0)
        p.surprised = data.get("surprised", False)
        p.spell_cast_bonus_action_this_turn = data.get("spell_cast_bonus_action_this_turn", False)
        p.spell_cast_action_level_this_turn = data.get("spell_cast_action_level_this_turn", None)
        p.bardic_inspiration_die = data.get("bardic_inspiration_die", None)
        p.relentless_rage_uses = data.get("relentless_rage_uses", 0)
        p.frightful_immune_list = data.get("frightful_immune_list", [])
        p.hunger_days = data.get("hunger_days", 0)
        p.water_days = data.get("water_days", 0)
        p.breath_rounds_left = data.get("breath_rounds_left", None)
        p.chases_dashes_used = data.get("chases_dashes_used", 0)
        p.madness_effects = data.get("madness_effects", [])
        p.injuries = data.get("injuries", [])
        p.diseases = data.get("diseases", [])
        p.is_submerged = data.get("is_submerged", False)
        p.is_object = data.get("is_object", False)
        p.damage_threshold = data.get("damage_threshold", 0)
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
        from common.campaign_journal import CampaignJournal
        self.campaign_journal = CampaignJournal()
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
            "enable_flanking": True,
            "auto_explore_fow": True,
            "auto_apply_rest_recovery": True,
            "auto_advance_time": True,
            "auto_day_night_cycle": True,
            "auto_distribute_xp": True,
            "square_diagonal_rule": "standard",
            # Regole Opzionali DMG (Selezionabili dal DM nel pannello automazioni)
            "opt_cleaving": False,
            "opt_massive_damage": False,
            "opt_lingering_injuries": False,
            "opt_madness": False,
            "opt_rest_variant": "standard",
            "opt_dmg_maneuvers": False,
            "opt_spell_points": False,
            "opt_hunger_thirst_weather": False,
        }
        self.pending_damages = {} # id -> dict
        self.pending_doors = {}   # id -> dict

    def set_automation_mode(self, mode: str, custom_settings: dict = None):
        """Imposta il profilo di automazione della campagna (manual, hybrid, full) e aggiorna i flag."""
        cur = getattr(self, "automation_settings", {}) or {}
        preserved_opts = {
            "square_diagonal_rule": cur.get("square_diagonal_rule", "standard"),
            "opt_cleaving": bool(cur.get("opt_cleaving", False)),
            "opt_massive_damage": bool(cur.get("opt_massive_damage", False)),
            "opt_lingering_injuries": bool(cur.get("opt_lingering_injuries", False)),
            "opt_madness": bool(cur.get("opt_madness", False)),
            "opt_rest_variant": cur.get("opt_rest_variant", "standard"),
            "opt_dmg_maneuvers": bool(cur.get("opt_dmg_maneuvers", False)),
            "opt_spell_points": bool(cur.get("opt_spell_points", False)),
            "opt_hunger_thirst_weather": bool(cur.get("opt_hunger_thirst_weather", False)),
        }
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
                "enable_flanking": False,
                "auto_explore_fow": False,
                "auto_apply_rest_recovery": False,
                "auto_advance_time": False,
                "auto_day_night_cycle": False,
                "auto_distribute_xp": False,
                **preserved_opts,
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
                "enable_flanking": True,
                "auto_explore_fow": True,
                "auto_apply_rest_recovery": True,
                "auto_advance_time": True,
                "auto_day_night_cycle": True,
                "auto_distribute_xp": True,
                **preserved_opts,
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
                "enable_flanking": True,
                "auto_explore_fow": True,
                "auto_apply_rest_recovery": True,
                "auto_advance_time": True,
                "auto_day_night_cycle": True,
                "auto_distribute_xp": True,
                **preserved_opts,
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

    def record_journal_event(self, category: str, title: str, description: str = "", actor: str = "", data: dict = None):
        with self.lock:
            if not hasattr(self, "campaign_journal") or self.campaign_journal is None:
                from common.campaign_journal import CampaignJournal
                camp_name = getattr(self.active_campaign, "name", "Campagna") if getattr(self, "active_campaign", None) else "Campagna"
                self.campaign_journal = CampaignJournal(campaign_name=camp_name)

            active_sess = self.campaign_journal.get_active_session()
            if not active_sess.weather:
                active_sess.weather = getattr(self, "weather", "Sereno")
            if not active_sess.location and getattr(self, "current_map", None):
                active_sess.location = self.current_map.get("name", "Mappa Tattica")
            if not active_sess.game_date:
                active_sess.game_date = {
                    "year": getattr(self, "time_year", 1492),
                    "month": getattr(self, "time_month", 1),
                    "day": getattr(self, "time_day", 1),
                    "hour": getattr(self, "time_hour", 8),
                    "minute": getattr(self, "time_minute", 0)
                }

            evt = self.campaign_journal.record_event(category, title, description, actor, data)
            if getattr(self, "active_campaign", None):
                self.active_campaign.journal = self.campaign_journal
            return evt

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
                    p.bonus_action_used_this_turn = False
                    p.reckless_attack_active = False
                    p.moved_straight_hexes = 0
                    p.last_move_dir = None
                    p.spell_cast_bonus_action_this_turn = False
                    p.spell_cast_action_level_this_turn = None
            else:
                for p in self.players:
                    p.in_combat = True
                    p.movement_spent_this_turn = 0
                    p.has_acted_this_turn = False
                    p.bonus_action_used_this_turn = False
                    p.reckless_attack_active = False
                    p.moved_straight_hexes = 0
                    p.last_move_dir = None
                    p.spell_cast_bonus_action_this_turn = False
                    p.spell_cast_action_level_this_turn = None
                    
            # Ordina i giocatori in combattimento per iniziativa decrescente, e sposta gli altri in fondo
            self.players.sort(key=lambda p: (getattr(p, 'in_combat', True), p.initiative), reverse=True)
            active = self.get_current_turn_player()
            if active:
                active.movement_spent_this_turn = 0
                active.has_acted_this_turn = False

            try:
                enemies = [p.name for p in self.players if getattr(p, 'in_combat', True) and not getattr(p, 'is_party_member', False)]
                en_str = ", ".join(enemies) if enemies else "forze ostili"
                self.record_journal_event("combat", "Inizio Combattimento", f"Il gruppo ingaggia battaglia contro: {en_str}.", actor="Party")
            except Exception:
                pass
        self._trigger_gui_update()

    def end_combat(self):
        temp_combat_conds = {"Scatto", "Disimpegno", "Schivata", "Aiutato", "Dash", "Disengage", "Dodge", "Helped", "Scudo", "Attacco Irruento", "Reckless Attack", "Sorpreso", "Surprised"}
        with self.lock:
            self.combat_active = False
            for p in self.players:
                p.in_combat = False
                p.movement_spent_this_turn = 0
                p.has_acted_this_turn = False
                p.bonus_action_used_this_turn = False
                p.reckless_attack_active = False
                p.moved_straight_hexes = 0
                p.last_move_dir = None
                p.spell_cast_bonus_action_this_turn = False
                p.spell_cast_action_level_this_turn = None
                p.surprised = False
                p.attacks_made_this_turn = 0
                if hasattr(p, "conditions") and p.conditions:
                    p.conditions = [c for c in p.conditions if c not in temp_combat_conds]
                if getattr(p, "full_sheet", None) and isinstance(p.full_sheet.get("conditions"), list):
                    p.full_sheet["conditions"] = [c for c in p.full_sheet["conditions"] if c not in temp_combat_conds]
            try:
                from server.rules.combat import recover_expended_ammunition
                for p in list(self.players):
                    recover_expended_ammunition(p, self)
            except Exception:
                pass
            try:
                self.record_journal_event("combat", "Fine Combattimento", f"Scontro risolto dopo {self.round_number} round.", actor="Party")
            except Exception:
                pass

            # Distribuzione Automatica Punti Esperienza (XP) RAW 5e se abilitata dal DM
            auto_xp = False
            if hasattr(self, "automation_settings") and isinstance(self.automation_settings, dict):
                auto_xp = self.automation_settings.get("auto_distribute_xp", True)
            if auto_xp:
                try:
                    from common.encounter_calc import CR_TO_XP, get_xp_for_level
                    from common.network_utils import broadcast
                    from common.protocol import make_chat_broadcast, make_player_stats_update

                    defeated_monsters = []
                    total_combat_xp = 0
                    for p in self.players:
                        is_party = getattr(p, "is_party_member", False) or getattr(p, "conn", None) is not None
                        if not is_party:
                            conds = [str(c).lower() for c in getattr(p, "conditions", [])]
                            if "morto" in conds or "dead" in conds or getattr(p, "hp", 1) <= 0:
                                cr_val = "1"
                                if getattr(p, "full_sheet", None) and isinstance(p.full_sheet, dict):
                                    cr_val = str(p.full_sheet.get("cr", "1")).strip()
                                m_xp = CR_TO_XP.get(cr_val, 0)
                                if m_xp == 0:
                                    try:
                                        m_xp = CR_TO_XP.get(str(float(cr_val)), 0)
                                    except Exception:
                                        m_xp = 200
                                total_combat_xp += m_xp
                                defeated_monsters.append((p.name, cr_val, m_xp))

                    living_party = [
                        p for p in self.players
                        if (getattr(p, "is_party_member", False) or getattr(p, "conn", None) is not None)
                        and "morto" not in [str(c).lower() for c in getattr(p, "conditions", [])]
                    ]

                    if total_combat_xp > 0 and living_party:
                        share_xp = total_combat_xp // len(living_party)
                        lvl_up_alerts = []
                        for p in living_party:
                            if not p.full_sheet or not isinstance(p.full_sheet, dict):
                                p.full_sheet = {"exp": 0, "level": getattr(p, "level", 1)}
                            old_xp = int(p.full_sheet.get("exp", 0) or 0)
                            new_xp = old_xp + share_xp
                            p.full_sheet["exp"] = new_xp
                            p_lvl = int(p.full_sheet.get("level", getattr(p, "level", 1)) or 1)
                            if p_lvl < 20:
                                next_lvl_req = get_xp_for_level(p_lvl + 1)
                                if new_xp >= next_lvl_req:
                                    lvl_up_alerts.append(f"🎉 {p.name}: {new_xp}/{next_lvl_req} PE — Pronto per il Livello {p_lvl + 1}!")

                        xp_msg = (
                            f"🏆 [ESPERIENZA] Fine Scontro: {len(defeated_monsters)} mostri sconfitti "
                            f"({total_combat_xp} PE totali).\n"
                            f"Ciascun eroe ({len(living_party)}) ottiene +{share_xp} PE!"
                        )
                        if lvl_up_alerts:
                            xp_msg += "\n" + "\n".join(lvl_up_alerts)
                        broadcast(self, make_chat_broadcast("Sistema", xp_msg))
                        self.log_dm_message(f"[XP] {xp_msg}")
                        for p in living_party:
                            broadcast(self, make_player_stats_update(p.name, p.hp, p.max_hp, p.initiative, p.conditions, getattr(p, "temp_hp", 0)))
                except Exception:
                    pass
        self._trigger_gui_update()
        
    def _get_combatants(self):
        return [p for p in self.players if getattr(p, 'in_combat', True)]

    def next_turn(self, tick_end_of_turn=True):
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
                if tick_end_of_turn and hasattr(prev_active, "active_effects") and isinstance(prev_active.active_effects, list):
                    expired_fx = []
                    for fx in prev_active.active_effects:
                        if fx.get("decrement_timing") == "end_of_turn" and fx.get("duration_rounds") is not None:
                            fx["duration_rounds"] -= 1
                            if fx["duration_rounds"] <= 0:
                                expired_fx.append(fx.get("id") or fx.get("name"))
                    for fx_id in expired_fx:
                        prev_active.remove_effect(fx_id)
                # PHB p. 189: La condizione Sorpreso termina alla fine del primo turno della creatura sorpresa (consentendo reazioni da lì in poi)
                if getattr(prev_active, "surprised", False) or any(c in ("Sorpreso", "Surprised") for c in getattr(prev_active, "conditions", [])):
                    prev_active.surprised = False
                    if hasattr(prev_active, "conditions") and prev_active.conditions:
                        prev_active.conditions = [c for c in prev_active.conditions if c not in ("Sorpreso", "Surprised")]
                    if getattr(prev_active, "full_sheet", None) and isinstance(prev_active.full_sheet.get("conditions"), list):
                        prev_active.full_sheet["conditions"] = [c for c in prev_active.full_sheet["conditions"] if c not in ("Sorpreso", "Surprised")]
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
                active.bonus_action_used_this_turn = False
                active.reckless_attack_active = False
                active.moved_straight_hexes = 0
                active.last_move_dir = None
                active.spell_cast_bonus_action_this_turn = False
                active.spell_cast_action_level_this_turn = None
                active.attacks_made_this_turn = 0
                active.has_reacted_this_turn = False
                active.sneak_attack_used_this_turn = False
                start_of_turn_conds = start_of_turn_conds | {"Attacco Irruento", "Reckless Attack"}
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

                # Gestione Inizio Turno: Ricarica Abilità Mostro (Recharge 5-6) & Rigenerazione / Danni Continui (D&D 5e RAW)
                try:
                    import random
                    from common.network_utils import broadcast
                    from common.protocol import make_chat_broadcast, make_player_stats_update
                    
                    fs = getattr(active, "full_sheet", None) or {}
                    
                    # 1. Ricarica Abilità Mostri (Recharge 5-6 / 6)
                    actions = fs.get("actions", []) if isinstance(fs, dict) else []
                    special_abs = fs.get("special_abilities", []) if isinstance(fs, dict) else []
                    recharge_candidates = getattr(active, "recharge_abilities", []) or []
                    all_abilities = list(recharge_candidates)
                    if isinstance(actions, list):
                        all_abilities.extend(actions)
                    if isinstance(special_abs, list):
                        all_abilities.extend(special_abs)
                        
                    for ab in all_abilities:
                        if isinstance(ab, dict) and ab.get("expended", False):
                            ab_desc = f"{ab.get('name', '')} {ab.get('desc', '')}".lower()
                            thresh = 6
                            if "5-6" in ab_desc or "5–6" in ab_desc or "recharge 5" in ab_desc:
                                thresh = 5
                            elif "6" in ab_desc or "recharge 6" in ab_desc:
                                thresh = 6
                            d6_roll = random.randint(1, 6)
                            if d6_roll >= thresh:
                                ab["expended"] = False
                                ab_name = ab.get("name", "Abilità")
                                msg = f"🎲 [RICARICA] {active.name} tira un {d6_roll} sul d6! L'abilità '{ab_name}' è di nuovo RICARICATA e pronta all'uso!"
                                broadcast(self, make_chat_broadcast("Sistema", msg))
                                self.log_dm_message(f"[RECHARGE] {msg}")

                    # 2. Rigenerazione (MM p. 11: Troll 10 PV, Vampiro 20 PV)
                    traits_str = ""
                    if isinstance(fs, dict):
                        traits_raw = fs.get("traits", []) + fs.get("special_abilities", [])
                        traits_str = " ".join(
                            f"{t.get('name', '')} {t.get('desc', '')}" if isinstance(t, dict) else str(t)
                            for t in traits_raw
                        ).lower()
                    
                    if "rigenerazione" in traits_str or "regeneration" in traits_str:
                        if active.hp > 0 and active.hp < active.max_hp:
                            conds = [str(c).lower() for c in getattr(active, "conditions", [])]
                            # Se ha subito fuoco o acido (Troll), la rigenerazione è inibita fino al prossimo turno
                            fire_acid_inhibited = any(k in conds for k in ("danno da fuoco subito", "danno da acido subito", "bruciatura", "acido"))
                            if not fire_acid_inhibited:
                                regen_val = 10
                                if "20" in traits_str or "vampiro" in str(active.name).lower() or "vampire" in str(active.name).lower():
                                    regen_val = 20
                                active.hp = min(active.max_hp, active.hp + regen_val)
                                msg = f"💚 [RIGENERAZIONE] {active.name} rigenera {regen_val} PV all'inizio del proprio turno ({active.hp}/{active.max_hp} PV)!"
                                broadcast(self, make_chat_broadcast("Sistema", msg))
                                broadcast(self, make_player_stats_update(active.name, active.hp, active.max_hp, active.initiative, active.conditions, getattr(active, "temp_hp", 0)))
                            else:
                                msg = f"⚠️ [RIGENERAZIONE] La rigenerazione di {active.name} è inibita dai danni da fuoco o acido subiti!"
                                broadcast(self, make_chat_broadcast("Sistema", msg))

                    # 3. Danno Continuo (es. In Fiamme, Veleno Attivo)
                    for eff in getattr(active, "active_effects", []):
                        if isinstance(eff, dict) and eff.get("periodic_damage"):
                            p_dmg = int(eff.get("periodic_damage", 0))
                            p_type = eff.get("damage_type", "Fuoco")
                            if p_dmg > 0 and active.hp > 0:
                                active.hp = max(0, active.hp - p_dmg)
                                msg = f"🔥 [DANNO CONTINUO] {active.name} subisce {p_dmg} danni da {p_type} ({eff.get('name', 'Effetto')}) all'inizio del turno! (PV: {active.hp}/{active.max_hp})"
                                broadcast(self, make_chat_broadcast("Sistema", msg))
                                broadcast(self, make_player_stats_update(active.name, active.hp, active.max_hp, active.initiative, active.conditions, getattr(active, "temp_hp", 0)))

                    # 4. Inghiottito / Engulfed (MM: es. Gelatina Ocra/Cubo Gelatinoso/Verme Purpureo/Rospo Gigante -> danno acido a inizio turno)
                    swallower_name = getattr(active, "swallowed_by", None)
                    if swallower_name and active.hp > 0:
                        swallower = next((p for p in self.players if p.name == swallower_name and p.hp > 0), None)
                        if swallower:
                            from server.rules.combat import apply_damage as _apply_dmg
                            acid_roll = random.randint(1, 6) + random.randint(1, 6) + random.randint(1, 6)  # 3d6 Acido base (o parametrizzabile)
                            sw_fs = getattr(swallower, "full_sheet", None) or {}
                            sw_acid_dice = sw_fs.get("swallow_damage_formula")
                            if sw_acid_dice:
                                try:
                                    from common.dice import roll_dice
                                    acid_roll = roll_dice(sw_acid_dice)["total"]
                                except Exception:
                                    pass
                            final_a, _, _, _ = _apply_dmg(active, acid_roll, damage_type="Acido", game_state=self)
                            msg = f"🧪 [INGHIOTTITO] All'inizio del turno nello stomaco di {swallower_name}, {active.name} subisce {final_a} danni da Acido (PV: {active.hp}/{active.max_hp})!"
                            broadcast(self, make_chat_broadcast("Sistema", msg))
                            broadcast(self, make_player_stats_update(active.name, active.hp, active.max_hp, active.initiative, active.conditions, getattr(active, "temp_hp", 0)))
                        else:
                            # Predatore morto/scomparso: liberato automaticamente
                            active.swallowed_by = None
                            if hasattr(active, "conditions"):
                                active.conditions = [c for c in active.conditions if c not in ("Inghiottito", "Swallowed", "Accecato", "Blinded", "Trattenuto", "Restrained")]
                except Exception:
                    pass

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
            combatants_before = self._get_combatants()
            combat_idx = -1
            for ci, cp in enumerate(combatants_before):
                if cp.name == target_name:
                    combat_idx = ci
                    break
            idx_to_remove = -1
            for i, p in enumerate(self.players):
                if p.name == target_name:
                    idx_to_remove = i
                    break
            if idx_to_remove != -1:
                self.players.pop(idx_to_remove)
                if getattr(self, "combat_active", False) and combat_idx != -1:
                    combatants_after = self._get_combatants()
                    if not combatants_after:
                        self.turn_index = 0
                    elif combat_idx < self.turn_index:
                        self.turn_index -= 1
                    elif combat_idx == self.turn_index and self.turn_index >= len(combatants_after):
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

    def get_state_dict(self, is_dm=False):
        """Restituisce una rappresentazione dell'intero stato del gioco come dizionario."""
        with self.lock:
            fow_enabled = False
            revealed_set = set()
            if self.current_map and isinstance(self.current_map, dict):
                fow_enabled = bool(self.current_map.get("fow_enabled", False))
                for h in self.current_map.get("fow_revealed", []):
                    if isinstance(h, (list, tuple)) and len(h) >= 2:
                        revealed_set.add((h[0], h[1]))

            players_data = []
            for p in self.players:
                if not is_dm:
                    if getattr(p, "layer", "token") == "gm" or getattr(p, "is_hidden", False):
                        continue
                    is_party = getattr(p, "is_party_member", False) or getattr(p, "is_companion", False)
                    if fow_enabled and not is_party:
                        pos = getattr(p, "position", None)
                        if pos and (pos[0], pos[1]) not in revealed_set:
                            continue

                p_dict = p.to_dict()
                if not is_dm and p_dict.get("full_sheet"):
                    # Rimuovi segreti confidenziali e note DM dai payload inviati ai giocatori
                    p_dict["full_sheet"] = dict(p_dict["full_sheet"])
                    p_dict["full_sheet"].pop("secret", None)
                    p_dict["full_sheet"].pop("dm_notes", None)
                    if not getattr(p, "is_party_member", False) and not getattr(p, "is_companion", False):
                        for priv_k in ["special_abilities", "legendary_actions_details", "reactions_details", "features", "actions"]:
                            p_dict["full_sheet"].pop(priv_k, None)
                players_data.append(p_dict)

            curr_turn = self.get_current_turn_player()
            turn_name = curr_turn.name if curr_turn else None
            if not is_dm and curr_turn and (getattr(curr_turn, "layer", "token") == "gm" or getattr(curr_turn, "is_hidden", False)):
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
                "active_campaign_folder": getattr(self.active_campaign, 'folder_path', None) if is_dm and getattr(self, 'active_campaign', None) else None,
                "automation_mode": getattr(self, "automation_mode", "hybrid"),
                "automation_settings": getattr(self, "automation_settings", {}),
                "pending_damages": getattr(self, "pending_damages", {}) if is_dm else {},
                "pending_doors": getattr(self, "pending_doors", {}) if is_dm else {},
                "campaign_journal": self.campaign_journal.to_dict(include_dm_notes=True) if is_dm and hasattr(self, "campaign_journal") and self.campaign_journal else (self.campaign_journal.sanitize_for_players() if hasattr(self, "campaign_journal") and self.campaign_journal else None)
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
            state = copy.deepcopy(self.get_state_dict(is_dm=True))
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
            self.active_aoes = state.get("active_aoes", [])
            self.drawn_lines = state.get("drawn_lines", [])
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
                merged_settings = dict(self.automation_settings)
                merged_settings.update(state["automation_settings"])
                self.automation_settings = merged_settings
            if "pending_damages" in state:
                self.pending_damages = state.get("pending_damages", {})
            if "pending_doors" in state:
                self.pending_doors = state.get("pending_doors", {})
            
            camp_folder = state.get("active_campaign_folder")
            if camp_folder and os.path.exists(camp_folder):
                try:
                    from common.campaign import Campaign
                    self.active_campaign = Campaign.load(camp_folder)
                    if hasattr(self.active_campaign, "journal") and self.active_campaign.journal:
                        self.campaign_journal = self.active_campaign.journal
                except Exception as e:
                    print(f"[GAME_STATE] Errore ripristino campagna: {e}")

            if "campaign_journal" in state and state["campaign_journal"]:
                from common.campaign_journal import CampaignJournal
                self.campaign_journal = CampaignJournal.from_dict(state["campaign_journal"])
                if getattr(self, "active_campaign", None):
                    self.active_campaign.journal = self.campaign_journal
            
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
                    existing.elevation = p_data.get("elevation", 0)
                    existing.ac = p_data.get("ac", 10)
                    existing.size = p_data.get("size", 1)
                    existing.is_hidden = p_data.get("is_hidden", False)
                    existing.concentrating_on = p_data.get("concentrating_on", None)
                    existing.in_combat = p_data.get("in_combat", False)
                    existing.death_save_successes = p_data.get("death_save_successes", 0)
                    existing.death_save_failures = p_data.get("death_save_failures", 0)
                    existing.combat_initiative = p_data.get("combat_initiative", None)
                    existing.active_effects = p_data.get("active_effects", [])
                    existing.is_companion = p_data.get("is_companion", False)
                    existing.in_pocket_dimension = p_data.get("in_pocket_dimension", False)
                    existing.swallowed_by = p_data.get("swallowed_by", None)
                    existing.mount_name = p_data.get("mount_name", None)
                    existing.stealth_score = p_data.get("stealth_score", 0)
                    existing.surprised = p_data.get("surprised", False)
                    existing.bardic_inspiration_die = p_data.get("bardic_inspiration_die", None)
                    existing.hunger_days = p_data.get("hunger_days", 0)
                    existing.water_days = p_data.get("water_days", 0)
                    existing.breath_rounds_left = p_data.get("breath_rounds_left", None)
                    existing.madness_effects = p_data.get("madness_effects", [])
                    existing.injuries = p_data.get("injuries", [])
                    existing.diseases = p_data.get("diseases", [])
                    existing.is_submerged = p_data.get("is_submerged", False)
                    existing.is_object = p_data.get("is_object", False)
                    existing.damage_threshold = p_data.get("damage_threshold", 0)
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
