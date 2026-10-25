import os
from common.file_utils import atomic_save_json, load_json

CHARACTER_FILE = "client_data/characters.json"

CONTAINERS = {
    "backpack": {
        "id": "backpack",
        "icon": "🎒",
        "name_it": "Zaino",
        "name_en": "Backpack",
        "max_capacity": None,
        "extradimensional": False,
        "affects_char_weight": True,
    },
    "equipped": {
        "id": "equipped",
        "icon": "⚔️",
        "name_it": "Equipaggiato / Addosso",
        "name_en": "Equipped / On Person",
        "max_capacity": None,
        "extradimensional": False,
        "affects_char_weight": True,
    },
    "bag_of_holding": {
        "id": "bag_of_holding",
        "icon": "🔮",
        "name_it": "Borsa Conservante",
        "name_en": "Bag of Holding",
        "max_capacity": 500.0,
        "extradimensional": True,
        "affects_char_weight": False,
    },
    "haversack": {
        "id": "haversack",
        "icon": "✨",
        "name_it": "Zaino Pratico di Heward",
        "name_en": "Heward's Handy Haversack",
        "max_capacity": 120.0,
        "extradimensional": True,
        "affects_char_weight": False,
    },
    "mount": {
        "id": "mount",
        "icon": "🐴",
        "name_it": "Sacca da Sella / Cavalcatura",
        "name_en": "Saddlebag / Mount",
        "max_capacity": None,
        "extradimensional": False,
        "affects_char_weight": False,
    }
}

LIGHT_PRESETS = {
    "torch": {
        "id": "torch",
        "icon": "🕯️",
        "name_it": "Torcia",
        "name_en": "Torch",
        "bright_radius": 4,  # 20 ft / 6 m
        "dim_radius": 4,     # 20 ft / 6 m
        "total_radius": 8,   # 40 ft / 12 m
        "color": "#FFD700"
    },
    "hooded_lantern": {
        "id": "hooded_lantern",
        "icon": "🏮",
        "name_it": "Lanterna a Cappuccio",
        "name_en": "Hooded Lantern",
        "bright_radius": 6,  # 30 ft / 9 m
        "dim_radius": 6,     # 30 ft / 9 m
        "total_radius": 12,  # 60 ft / 18 m
        "color": "#FFA500"
    },
    "dim_hooded": {
        "id": "dim_hooded",
        "icon": "🌑",
        "name_it": "Lanterna Schermata (Luce Fioca 1.5m)",
        "name_en": "Hooded Lantern (Dim 5 ft)",
        "bright_radius": 0,
        "dim_radius": 1,     # 5 ft / 1.5 m
        "total_radius": 1,
        "color": "#FF8C00"
    },
    "light_spell": {
        "id": "light_spell",
        "icon": "✨",
        "name_it": "Incantesimo Luce",
        "name_en": "Light Spell",
        "bright_radius": 4,  # 20 ft / 6 m
        "dim_radius": 4,     # 20 ft / 6 m
        "total_radius": 8,   # 40 ft / 12 m
        "color": "#66D9E8"
    }
}

class Character:

    def __init__(self, name="Nuovo Personaggio", campaign="Nessuna Campagna"):
        self.id = os.urandom(4).hex() # Unique ID
        self.name = name
        self.campaign = campaign
        self.race = ""
        self.char_class = ""
        self.subclass = ""
        self.level = 1
        self.exp = 0
        self.alignment = ""
        self.background = ""
        self.background_feature_name = ""
        self.background_feature_desc = ""
        self.personality_trait = ""
        self.ideal = ""
        self.bond = ""
        self.flaw = ""
        self.personal_quest = ""
        self.secret = ""
        self.party_tie = ""
        self.trinket = ""
        self.backstory = ""
        self.avatar_b64 = ""
        self.avatar_path = ""
        
        # Statistiche Base
        self.attributes = {"FOR": 10, "DES": 10, "COS": 10, "INT": 10, "SAG": 10, "CAR": 10}
        
        # Valori di Combattimento
        self.hp_max = 10
        self.hp_current = 10
        self.temp_hp = 0
        self.ac = 10
        self.initiative = 0
        from common.i18n import get_distance_unit
        self.speed_unit = get_distance_unit()
        self.speed = 9 if self.speed_unit == "m" else 30
        self.proficiency_bonus = 2
        self.hit_dice_total = 1
        self.hit_dice_current = 1
        self.hit_dice_type = "d8"
        self.exhaustion_level = 0
        self.damage_resistances = []
        self.damage_immunities = []
        self.damage_vulnerabilities = []
        self.class_resources = {
            "second_wind": True,
            "action_surge": True,
            "rage_current": 2,
            "rage_max": 2
        }
        self.custom_resources = []
        self.size = "medium"
        self.death_saves = {"successes": 0, "failures": 0}
        self.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
        self.hotbar = [""] * 10
        self.last_position = None
        self.backpack_dropped = False
        self.active_light = None
        
        # Testo libero / Griglia
        self.inventory_grid = [None] * 25 # Griglia 5x5
        self.inventory = []
        self.features = ""
        self.spell_slots = {str(i): {"max": 0, "current": 0} for i in range(1, 10)}
        self.spellbook = []
        self.weapons = []
        self.has_inspiration = False
        self.journal_notes = ""
        self.notes = ""
        self.skills = {
            "Acrobazia": 0, "Addestrare Animali": 0, "Arcano": 0, "Atletica": 0,
            "Furtività": 0, "Indagare": 0, "Inganno": 0, "Intimidire": 0,
            "Intrattenere": 0, "Intuizione": 0, "Medicina": 0, "Natura": 0,
            "Percezione": 0, "Persuasione": 0, "Prestidigitazione": 0,
            "Religione": 0, "Sopravvivenza": 0, "Storia": 0
        }
        self.travel_role = "Nessuna"
        self.marching_order = "Centro"

    def short_rest(self, hd_to_spend=1):
        """Spende Dadi Vita (XdY + Mod COS) per recuperare HP e ricarica i privilegi da riposo breve."""
        if hd_to_spend <= 0 or self.hit_dice_current <= 0:
            return 0
        actual_spend = min(hd_to_spend, self.hit_dice_current)
        self.hit_dice_current -= actual_spend
        
        cos_val = self.attributes.get("COS", 10)
        try:
            cos_mod = (int(cos_val) - 10) // 2
        except (ValueError, TypeError):
            cos_mod = 0
            
        die_str = str(self.hit_dice_type).lower().replace("d", "")
        sides = int(die_str) if die_str.isdigit() else 8
        
        recovered = 0
        import random
        for _ in range(actual_spend):
            roll = random.randint(1, sides)
            total = max(1, roll + cos_mod)
            recovered += total
            
        self.hp_current = min(self.hp_max, self.hp_current + recovered)
        if not hasattr(self, "class_resources") or not isinstance(self.class_resources, dict):
            self.class_resources = {}
        self.class_resources["second_wind"] = True
        self.class_resources["action_surge"] = True
        
        # Reset custom class resources configured for Short Rest
        for res in getattr(self, "custom_resources", []):
            if isinstance(res, dict) and res.get("reset_on") == "short":
                res["current"] = res.get("max", 0)
        
        # Regola D&D 5e: I Warlock (Magia del Patto) ricaricano tutti gli slot incantesimo con un Riposo Breve!
        c_class = str(getattr(self, "char_class", "")).strip().lower()
        if "warlock" in c_class:
            for lvl, slot in getattr(self, "spell_slots", {}).items():
                if isinstance(slot, dict) and "current" in slot:
                    slot["current"] = slot.get("max", 0)
                elif isinstance(slot, list) and len(slot) >= 2:
                    slot[0] = slot[1]
                    
        return recovered

    def long_rest(self):
        self.hp_current = self.hp_max
        self.temp_hp = 0
        regained = max(1, self.hit_dice_total // 2) if self.hit_dice_total > 0 else 0
        self.hit_dice_current = min(self.hit_dice_total, self.hit_dice_current + regained)
        self.death_saves = {"successes": 0, "failures": 0}
        self.exhaustion_level = max(0, getattr(self, "exhaustion_level", 0) - 1)
        for lvl in self.spell_slots:
            if isinstance(self.spell_slots[lvl], dict) and "current" in self.spell_slots[lvl]:
                self.spell_slots[lvl]["current"] = self.spell_slots[lvl]["max"]
            elif isinstance(self.spell_slots[lvl], list) and len(self.spell_slots[lvl]) > 1:
                self.spell_slots[lvl][0] = self.spell_slots[lvl][1]
        lvl = getattr(self, "level", 1) or 1
        max_rage = 2 if lvl < 3 else (3 if lvl < 6 else (4 if lvl < 12 else 5))
        self.class_resources = {
            "second_wind": True,
            "action_surge": True,
            "rage_current": max_rage,
            "rage_max": max_rage
        }
        # Reset ALL custom class resources on Long Rest
        for res in getattr(self, "custom_resources", []):
            if isinstance(res, dict):
                res["current"] = res.get("max", 0)

    def auto_populate_class_resources(self):
        """Popola le risorse 5e note in base alla classe se custom_resources è vuota."""
        if getattr(self, "custom_resources", None):
            return
        self.custom_resources = []
        c_cls = str(getattr(self, "char_class", "")).lower()
        lvl = max(1, int(getattr(self, "level", 1) or 1))
        car = int(self.attributes.get("CAR", 10))
        car_mod = max(1, (car - 10) // 2)
        
        if any(k in c_cls for k in ["barbar", "barbarian"]):
            rage = 2 if lvl < 3 else (3 if lvl < 6 else (4 if lvl < 12 else 5))
            self.custom_resources.append({"name": "Ira (Rage)", "current": rage, "max": rage, "reset_on": "long"})
        elif any(k in c_cls for k in ["monk", "monaco"]):
            self.custom_resources.append({"name": "Punti Ki", "current": lvl, "max": lvl, "reset_on": "short"})
        elif any(k in c_cls for k in ["bard", "bardo"]):
            rst = "short" if lvl >= 5 else "long"
            self.custom_resources.append({"name": "Ispirazione Bardica", "current": car_mod, "max": car_mod, "reset_on": rst})
        elif any(k in c_cls for k in ["druid", "druido"]):
            self.custom_resources.append({"name": "Forma Selvatica", "current": 2, "max": 2, "reset_on": "short"})
        elif any(k in c_cls for k in ["paladin", "paladino"]):
            self.custom_resources.append({"name": "Mani Curative (Lay on Hands)", "current": lvl * 5, "max": lvl * 5, "reset_on": "long"})
            self.custom_resources.append({"name": "Canale di Divinità", "current": 1, "max": 1, "reset_on": "short"})
        elif any(k in c_cls for k in ["cleric", "chierico"]):
            ch_uses = 1 if lvl < 6 else (2 if lvl < 18 else 3)
            self.custom_resources.append({"name": "Canale di Divinità", "current": ch_uses, "max": ch_uses, "reset_on": "short"})
        elif any(k in c_cls for k in ["fighter", "guerriero"]):
            self.custom_resources.append({"name": "Secondo Fiato (Second Wind)", "current": 1, "max": 1, "reset_on": "short"})
            act = 2 if lvl >= 17 else 1
            self.custom_resources.append({"name": "Azione Impetuosa (Action Surge)", "current": act, "max": act, "reset_on": "short"})
        elif any(k in c_cls for k in ["sorcerer", "stregone"]):
            if lvl >= 2:
                self.custom_resources.append({"name": "Punti Stregoneria", "current": lvl, "max": lvl, "reset_on": "long"})

    def get_attunement_bonuses(self):
        """Calcola i modificatori passivi derivanti dagli oggetti attualmente sintonizzati (🔮 max 3)."""
        bonuses = {
            "bonus_ac": 0,
            "bonus_saves": 0,
            "bonus_stats": {},
            "set_stats": {}
        }
        attuned_items = []
        for item in getattr(self, "inventory_grid", []):
            if isinstance(item, dict) and item.get("attuned"):
                attuned_items.append(item)
                if len(attuned_items) >= 3:
                    break

        for item in attuned_items:
            name = str(item.get("name", "")).lower()
            desc = str(item.get("desc", "")).lower()
            
            # Proprietà esplicite
            if "bonus_ac" in item:
                try: bonuses["bonus_ac"] += int(item["bonus_ac"])
                except Exception: pass
            if "bonus_saves" in item:
                try: bonuses["bonus_saves"] += int(item["bonus_saves"])
                except Exception: pass
            if "set_str" in item:
                try: bonuses["set_stats"]["FOR"] = max(bonuses["set_stats"].get("FOR", 0), int(item["set_str"]))
                except Exception: pass
            if "set_int" in item:
                try: bonuses["set_stats"]["INT"] = max(bonuses["set_stats"].get("INT", 0), int(item["set_int"]))
                except Exception: pass
            if "set_con" in item:
                try: bonuses["set_stats"]["COS"] = max(bonuses["set_stats"].get("COS", 0), int(item["set_con"]))
                except Exception: pass

            # Oggetti magici celebri 5e
            if any(k in name for k in ["anello di protezione", "mantello della protezione", "ring of protection", "cloak of protection"]):
                bonuses["bonus_ac"] += 1
                bonuses["bonus_saves"] += 1
            elif any(k in name for k in ["bracciali della difesa", "bracers of defense"]):
                bonuses["bonus_ac"] += 2
            elif any(k in name for k in ["guanti della forza dell'orco", "gauntlets of ogre power"]):
                bonuses["set_stats"]["FOR"] = max(bonuses["set_stats"].get("FOR", 0), 19)
            elif any(k in name for k in ["fascia dell'intelletto", "headband of intellect"]):
                bonuses["set_stats"]["INT"] = max(bonuses["set_stats"].get("INT", 0), 19)
            elif any(k in name for k in ["amuleto della salute", "amulet of health"]):
                bonuses["set_stats"]["COS"] = max(bonuses["set_stats"].get("COS", 0), 19)
            elif "cintura della forza dei giganti" in name or ("belt" in name and "giant strength" in name):
                if any(k in name for k in ["tempesta", "storm"]):
                    bonuses["set_stats"]["FOR"] = max(bonuses["set_stats"].get("FOR", 0), 29)
                elif any(k in name for k in ["nuvole", "cloud"]):
                    bonuses["set_stats"]["FOR"] = max(bonuses["set_stats"].get("FOR", 0), 27)
                elif any(k in name for k in ["fuoco", "fire"]):
                    bonuses["set_stats"]["FOR"] = max(bonuses["set_stats"].get("FOR", 0), 25)
                elif any(k in name for k in ["pietra", "gelo", "frost", "stone"]):
                    bonuses["set_stats"]["FOR"] = max(bonuses["set_stats"].get("FOR", 0), 23)
                else:
                    bonuses["set_stats"]["FOR"] = max(bonuses["set_stats"].get("FOR", 0), 21)
            else:
                import re
                ac_match = re.search(r'\+(\d+)\s*(?:alla\s*)?(?:ca|ac|armatura|classe armatura)', desc)
                if ac_match and "bonus_ac" not in item:
                    try: bonuses["bonus_ac"] += int(ac_match.group(1))
                    except Exception: pass
                save_match = re.search(r'\+(\d+)\s*(?:a\s*tutti\s*i\s*)?(?:tiri\s*salvezza|ts|saving\s*throws)', desc)
                if save_match and "bonus_saves" not in item:
                    try: bonuses["bonus_saves"] += int(save_match.group(1))
                    except Exception: pass

        return bonuses

    def get_effective_attribute(self, attr_name):
        base = int(self.attributes.get(attr_name, 10))
        bonuses = self.get_attunement_bonuses()
        if attr_name in bonuses["set_stats"]:
            base = max(base, bonuses["set_stats"][attr_name])
        if attr_name in bonuses["bonus_stats"]:
            base += bonuses["bonus_stats"][attr_name]
        return base

    def get_effective_ac(self):
        bonuses = self.get_attunement_bonuses()
        return self.ac + bonuses["bonus_ac"]

    def get_effective_save_bonus(self, stat_name):
        stat_val = self.get_effective_attribute(stat_name)
        mod = (stat_val - 10) // 2
        bonuses = self.get_attunement_bonuses()
        return mod + bonuses["bonus_saves"]

    def get_carried_weight(self) -> float:
        """
        Calcola il peso totale trasportato sul corpo dal personaggio (in lbs).
        Regole 5e RAW:
        - 50 monete = 1 lb (trasportate nella borsa alla cintura, PHB p. 143).
        - Oggetti con container "equipped" (addosso) gravano sempre sul PG.
        - Oggetti con container "backpack" (nello zaino) gravano solo se lo zaino è indossato (backpack_dropped == False).
        - Oggetti in spazi extradimensionali (bag_of_holding, haversack) o su cavalcatura (mount) non gravano sul PG.
        """
        total = 0.0
        if hasattr(self, "currency") and isinstance(self.currency, dict):
            coin_count = 0
            for v in self.currency.values():
                try:
                    coin_count += max(0, int(v))
                except (ValueError, TypeError):
                    pass
            total += round(coin_count / 50.0, 2)
            
        backpack_dropped = getattr(self, "backpack_dropped", False)
        for item in getattr(self, "inventory_grid", []):
            if not item or not isinstance(item, dict):
                continue
            if item.get("_coins_synced") and hasattr(self, "currency") and isinstance(self.currency, dict) and sum(max(0, int(v)) for v in self.currency.values() if isinstance(v, (int, float, str)) and str(v).isdigit()) > 0:
                continue
            try:
                w = float(item.get("weight", 0.0) or 0.0)
                if w <= 0.0 and item.get("name"):
                    from common.starter_equipment import lookup_standard_weight
                    w = lookup_standard_weight(item.get("name", ""))
                qty = int(item.get("qty", 1) or 1)
                item_weight = w * qty
            except (ValueError, TypeError):
                continue
            
            c = item.get("container")
            if not c:
                itype = str(item.get("type", "")).strip().lower()
                c = "equipped" if itype in ("arma", "armatura", "scudo", "weapon", "armor", "shield") else "backpack"
            
            if c == "equipped":
                total += item_weight
            elif c == "backpack":
                if not backpack_dropped:
                    total += item_weight
            elif c in ("bag_of_holding", "haversack", "mount"):
                pass
            else:
                if not backpack_dropped:
                    total += item_weight
                    
        return round(total, 2)

    def find_ammunition(self, weapon_name: str, include_empty: bool = False):
        """Trova le munizioni corrispondenti a un'arma (es. frecce per archi, dardi per balestre)."""
        w_lower = str(weapon_name).lower()
        target_ammo = None
        if any(k in w_lower for k in ["arco", "bow"]):
            target_ammo = ["frecc", "arrow"]
        elif any(k in w_lower for k in ["balestra", "crossbow"]):
            target_ammo = ["dard", "bolt"]
        elif any(k in w_lower for k in ["fionda", "sling"]):
            target_ammo = ["proiettil", "bullet", "sassi"]
            
        if not target_ammo:
            return None, None
            
        empty_match = (None, None)
        for idx, it in enumerate(getattr(self, "inventory_grid", [])):
            if not it or not isinstance(it, dict):
                continue
            nm = str(it.get("name", "")).lower()
            try:
                qty = int(it.get("qty", 0))
            except (ValueError, TypeError):
                qty = 0
            if any(t in nm for t in target_ammo):
                if qty > 0:
                    return it, idx
                elif empty_match[0] is None:
                    empty_match = (it, idx)
        if include_empty and empty_match[0] is not None:
            return empty_match
        return None, None

    def get_container_contents_weight(self, container_key: str) -> float:
        """Restituisce la somma dei pesi degli oggetti collocati in uno specifico contenitore."""
        tot = 0.0
        for item in getattr(self, "inventory_grid", []):
            if not item or not isinstance(item, dict):
                continue
            c = item.get("container")
            if not c:
                itype = str(item.get("type", "")).strip().lower()
                c = "equipped" if itype in ("arma", "armatura", "scudo", "weapon", "armor", "shield") else "backpack"
            if c == container_key:
                try:
                    w = float(item.get("weight", 0.0) or 0.0)
                    qty = int(item.get("qty", 1) or 1)
                    tot += w * qty
                except (ValueError, TypeError):
                    pass
        return round(tot, 2)

    def get_encumbrance_status(self) -> dict:
        """
        Calcola lo scaglione di ingombro secondo la Regola Variante 5e (PHB p. 176):
        - Normale: fino a FOR * 5 lbs
        - Ingombrato: fino a FOR * 10 lbs (-10 ft / -3 m velocità)
        - Gravemente Ingombrato: fino a FOR * 15 lbs (-20 ft / -6 m velocità, Svantaggio prove/attacchi FOR/DES/COS)
        - Sovraccarico: oltre FOR * 15 lbs (Velocità ridotta a 0)
        """
        size_mults = {
            "tiny": 0.5,
            "small": 1.0,
            "medium": 1.0,
            "large": 2.0,
            "huge": 4.0,
            "gargantuan": 8.0
        }
        sz = str(getattr(self, "size", "medium") or "medium").lower()
        size_mult = size_mults.get(sz, 1.0)
        
        strength = max(1, self.get_effective_attribute("FOR"))
        limit_normal = strength * 5.0 * size_mult
        limit_encumbered = strength * 10.0 * size_mult
        limit_max = strength * 15.0 * size_mult
        
        carried = self.get_carried_weight()
        backpack_dropped = getattr(self, "backpack_dropped", False)
        
        if carried <= limit_normal:
            tier = "normal"
            penalty_ft = 0
            penalty_m = 0.0
            disadvantage = False
            color = "#10B981"
        elif carried <= limit_encumbered:
            tier = "encumbered"
            penalty_ft = 10
            penalty_m = 3.0
            disadvantage = False
            color = "#F59E0B"
        elif carried <= limit_max:
            tier = "heavily_encumbered"
            penalty_ft = 20
            penalty_m = 6.0
            disadvantage = True
            color = "#EF4444"
        else:
            tier = "overloaded"
            penalty_ft = 999
            penalty_m = 999.0
            disadvantage = True
            color = "#DC2626"
            
        boh_weight = self.get_container_contents_weight("bag_of_holding")
        haversack_weight = self.get_container_contents_weight("haversack")
        mount_weight = self.get_container_contents_weight("mount")
        backpack_weight = self.get_container_contents_weight("backpack")
        
        return {
            "tier": tier,
            "carried_weight": carried,
            "limit_normal": limit_normal,
            "limit_encumbered": limit_encumbered,
            "limit_max": limit_max,
            "speed_penalty_ft": penalty_ft,
            "speed_penalty_m": penalty_m,
            "disadvantage": disadvantage,
            "color": color,
            "backpack_dropped": backpack_dropped,
            "backpack_weight": backpack_weight,
            "boh_weight": boh_weight,
            "haversack_weight": haversack_weight,
            "mount_weight": mount_weight
        }

    def get_effective_speed(self) -> int | float:
        """
        Calcola la velocità di movimento effettiva del personaggio (in ft o m)
        applicando le penalità dell'Ingombro (PHB p. 176) e dell'Affaticamento (Exhaustion).
        """
        base_speed = float(getattr(self, "speed", 30) or 30)
        unit = getattr(self, "speed_unit", "ft")
        enc = self.get_encumbrance_status()
        
        if enc["tier"] == "overloaded":
            return 0 if unit == "ft" else 0.0
            
        penalty = enc["speed_penalty_m"] if unit == "m" else enc["speed_penalty_ft"]
        eff = max(0.0, base_speed - penalty)
        
        exh = int(getattr(self, "exhaustion_level", 0) or 0)
        if exh >= 5:
            return 0 if unit == "ft" else 0.0
        elif exh >= 2:
            eff = eff / 2.0
            
        return int(round(eff)) if unit == "ft" else round(eff, 1)

    def toggle_drop_backpack(self) -> bool:
        """Inverte lo stato dello zaino (a terra vs indossato)."""
        self.backpack_dropped = not getattr(self, "backpack_dropped", False)
        return self.backpack_dropped

    def toggle_light(self, preset_key: str = "torch") -> tuple[bool, str, dict]:
        """
        Attiva o spegne la sorgente di luce portatile (Torcia, Lanterna, Incantesimo Luce).
        Restituisce (is_active, stato_testo, preset_dict).
        """
        if getattr(self, "active_light", None):
            old = self.active_light
            self.active_light = None
            return False, "spenta", old
        preset = LIGHT_PRESETS.get(preset_key, LIGHT_PRESETS["torch"])
        self.active_light = preset.copy()
        return True, "accesa", self.active_light

    def get_light_specs(self) -> tuple[int, str]:
        """Restituisce (raggio_totale_esagoni, colore_esadecimale)."""
        if not getattr(self, "active_light", None):
            return 0, "#FFD700"
        return self.active_light.get("total_radius", 0), self.active_light.get("color", "#FFD700")

    def spend_hit_die_single(self) -> dict:
        """
        Spende 1 singolo Dado Vita D&D 5e (1dY + Mod COS) secondo le regole RAW del Riposo Breve (PHB p. 186).
        Restituisce il dettaglio del tiro, cura gli HP e aggiorna il conteggio rimanente.
        """
        if getattr(self, "hit_dice_current", 0) <= 0:
            return {"success": False, "reason": "Nessun Dado Vita rimasto"}
            
        self.hit_dice_current -= 1
        cos_val = self.attributes.get("COS", 10)
        try:
            cos_mod = (int(cos_val) - 10) // 2
        except (ValueError, TypeError):
            cos_mod = 0
            
        die_str = str(getattr(self, "hit_dice_type", "d8")).lower().replace("d", "")
        sides = int(die_str) if die_str.isdigit() else 8
        
        import random
        roll = random.randint(1, sides)
        healed = max(1, roll + cos_mod)
        old_hp = self.hp_current
        self.hp_current = min(self.hp_max, self.hp_current + healed)
        actual_gain = self.hp_current - old_hp
        
        return {
            "success": True,
            "die": f"1d{sides}",
            "roll": roll,
            "con_mod": cos_mod,
            "healed": healed,
            "actual_gain": actual_gain,
            "hp_current": self.hp_current,
            "hp_max": self.hp_max,
            "hit_dice_left": self.hit_dice_current,
            "hit_dice_total": self.hit_dice_total
        }


    def to_dict(self):
        return self.__dict__
    
    @staticmethod
    def from_dict(data):
        c = Character()
        for key, value in data.items():
            if hasattr(c, key):
                setattr(c, key, value)
        # Assicuriamoci che l'inventario a griglia esista anche se carichiamo un vecchio PG
        if not hasattr(c, "inventory_grid") or not isinstance(c.inventory_grid, list):
            c.inventory_grid = [None] * 25
            # Retrocompatibilità
            old_inv = getattr(c, "inventory", "")
            if old_inv:
                c.inventory_grid[0] = {"name": "Vecchio Inv.", "type": "Misto", "desc": old_inv, "qty": 1}
        
        if not hasattr(c, "spell_slots"):
            c.spell_slots = {str(i): {"max": 0, "current": 0} for i in range(1, 10)}
        else:
            # Upgrade old format to new format
            for i in range(1, 10):
                lvl = str(i)
                if lvl in c.spell_slots and isinstance(c.spell_slots[lvl], list):
                    c.spell_slots[lvl] = {"max": c.spell_slots[lvl][1], "current": c.spell_slots[lvl][0]}
                elif lvl not in c.spell_slots:
                    c.spell_slots[lvl] = {"max": 0, "current": 0}

        if not hasattr(c, "spellbook") or not isinstance(c.spellbook, list):
            # Try to migrate from spell_list if it exists
            if hasattr(c, "spell_list") and isinstance(c.spell_list, list):
                c.spellbook = c.spell_list
            else:
                c.spellbook = []
        if hasattr(c, "spell_list"):
            delattr(c, "spell_list")

        if not hasattr(c, "skills"):
            c.skills = {
                "Acrobazia": 0, "Addestrare Animali": 0, "Arcano": 0, "Atletica": 0,
                "Furtività": 0, "Indagare": 0, "Inganno": 0, "Intimidire": 0,
                "Intrattenere": 0, "Intuizione": 0, "Medicina": 0, "Natura": 0,
                "Percezione": 0, "Persuasione": 0, "Prestidigitazione": 0,
                "Religione": 0, "Sopravvivenza": 0, "Storia": 0
            }
        
        if not hasattr(c, "hotbar") or not isinstance(c.hotbar, list) or len(c.hotbar) != 10:
            c.hotbar = [""] * 10
            
        if not hasattr(c, "weapons") or not isinstance(c.weapons, list):
            c.weapons = []
            
        if not hasattr(c, "has_inspiration"):
            c.has_inspiration = False
            
        if not hasattr(c, "journal_notes"):
            c.journal_notes = ""
            
        if not hasattr(c, "temp_hp"):
            c.temp_hp = 0
        if not hasattr(c, "exhaustion_level"):
            c.exhaustion_level = 0
        if not hasattr(c, "damage_resistances"):
            c.damage_resistances = []
        if not hasattr(c, "damage_immunities"):
            c.damage_immunities = []
        if not hasattr(c, "damage_vulnerabilities"):
            c.damage_vulnerabilities = []
        if not hasattr(c, "class_resources") or not isinstance(c.class_resources, dict):
            c.class_resources = {
                "second_wind": True,
                "action_surge": True,
                "rage_current": 2,
                "rage_max": 2
            }
        if not hasattr(c, "custom_resources") or not isinstance(c.custom_resources, list):
            c.custom_resources = []
            c.auto_populate_class_resources()
        if not hasattr(c, "size") or not c.size:
            c.size = "medium"
        if not hasattr(c, "travel_role"):
            c.travel_role = "Nessuna"
        if not hasattr(c, "marching_order"):
            c.marching_order = "Centro"
        if not hasattr(c, "backpack_dropped"):
            c.backpack_dropped = bool(data.get("backpack_dropped", False))
        if not hasattr(c, "active_light"):
            c.active_light = data.get("active_light", None)

        if "speed_unit" not in data or data.get("speed_unit") not in ("ft", "m"):
            try:
                c.speed_unit = "m" if float(getattr(c, "speed", 30)) <= 18 else "ft"
            except (ValueError, TypeError):
                c.speed_unit = "ft"
            
        # Se la lista armi è vuota, crea armi base compatibili
        if len(c.weapons) == 0:
            c_cls = getattr(c, "char_class", "").lower()
            if any(k in c_cls for k in ["mago", "wizard", "stregone", "sorcerer", "warlock"]):
                c.weapons = [
                    {"name": "Bastone Ferrato", "type": "Mischia", "ability": "FOR", "damage_dice": "1d6", "damage_type": "Contundente", "bonus": 0, "proficient": True},
                    {"name": "Pugnale", "type": "Mischia/Lancio", "ability": "DES", "damage_dice": "1d4", "damage_type": "Perforante", "bonus": 0, "proficient": True}
                ]
            elif any(k in c_cls for k in ["ladro", "rogue", "ranger", "bardo", "bard"]):
                c.weapons = [
                    {"name": "Stocco", "type": "Mischia (Accurata)", "ability": "DES", "damage_dice": "1d8", "damage_type": "Perforante", "bonus": 0, "proficient": True},
                    {"name": "Arco Corto", "type": "Distanza (80/320 ft)", "ability": "DES", "damage_dice": "1d6", "damage_type": "Perforante", "bonus": 0, "proficient": True}
                ]
            else:
                c.weapons = [
                    {"name": "Spada Lunga", "type": "Mischia (Versatile 1d10)", "ability": "FOR", "damage_dice": "1d8", "damage_type": "Tagliente", "bonus": 0, "proficient": True},
                    {"name": "Balestra Leggera", "type": "Distanza (80/320 ft)", "ability": "DES", "damage_dice": "1d8", "damage_type": "Perforante", "bonus": 0, "proficient": True}
                ]
            
        if not getattr(c, "starting_kit_applied", False) and getattr(c, "char_class", None) and getattr(c, "level", 1) == 1:
            has_real_items = any(it and it.get("name") != "Zaino Base" for it in c.inventory_grid)
            if not has_real_items and len(getattr(c, "spellbook", [])) == 0:
                from common.starter_equipment import apply_class_and_race_starter_kit
                apply_class_and_race_starter_kit(c)

        return c

class CharacterManager:
    def __init__(self):
        self.characters = []
        self.load_characters()
        
    def load_characters(self):
        data = load_json(CHARACTER_FILE, default=[])
        if isinstance(data, list):
            self.characters = [Character.from_dict(d) for d in data if isinstance(d, dict)]
        else:
            self.characters = []

    def save_characters(self):
        atomic_save_json(CHARACTER_FILE, [c.to_dict() for c in self.characters], indent=4)
            
    def add_character(self, character):
        self.characters.append(character)
        self.save_characters()
        
    def update_character(self, character):
        for i, c in enumerate(self.characters):
            if c.id == character.id:
                self.characters[i] = character
                break
        self.save_characters()
        
    def delete_character(self, character):
        self.characters = [c for c in self.characters if c.id != character.id]
        self.save_characters()

    def get_character_by_id(self, char_id):
        for c in self.characters:
            if c.id == char_id:
                return c
        return None


    def get_character_by_name(self, name):
        for c in self.characters:
            if c.name == name:
                return c
        return None

    def get_or_create(self, name):
        c = self.get_character_by_name(name)
        if not c:
            c = Character(name=name)
            self.add_character(c)
        return c

    def set_active(self, name):
        self.active_character = self.get_or_create(name)
        return self.active_character
