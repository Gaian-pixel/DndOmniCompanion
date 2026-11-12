import os
from common.file_utils import atomic_save_json, load_json, get_writable_dir

CHARACTER_FILE = os.path.join(get_writable_dir(), "client_data", "characters.json")

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

    def __init__(self, name="Nuovo Personaggio", campaign="Nessuna Campagna", race="", char_class="", subclass="", level=1):
        self.id = os.urandom(4).hex() # Unique ID
        self.name = name
        self.campaign = campaign
        self.race = race
        self.char_class = char_class
        self.subclass = subclass
        self.level = int(level or 1)
        self.proficiency_bonus = 2 + (max(1, self.level) - 1) // 4
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
        self.proficiency_bonus = 2 + (max(1, self.level) - 1) // 4
        self.hit_dice_total = max(1, self.level)
        self.hit_dice_current = max(1, self.level)
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
        self.features_list = []
        self.conditions = []
        self.active_effects = []
        self.starting_kit_applied = False
        self.campaign_starter_received = False
        self.saving_throw_proficiencies = []
        self.subrace = ""
        self.origin_place = ""
        self.half_elf_bonuses = []
        self.has_darkvision = None
        self.senses = ""
        self.traits = []
        self.inspiration = False
        self.classes = {}
        self.portent_dice = []
        self.lucky_points = 0
        self.relentless_endurance_used = False
        self.arcane_recovery_used = False
        self.wild_shape = {
            "active": False,
            "beast_name": "",
            "beast_hp": 0,
            "beast_max_hp": 0,
            "original_hp": 10,
            "original_max_hp": 10,
            "original_ac": 10,
            "original_speed": 30,
            "original_attributes": {}
        }
        self.sorcery_points_current = 0
        self.sorcery_points_max = 0
        self.superiority_dice_current = 0
        self.superiority_dice_max = 0
        self.superiority_die_type = "d8"

    def short_rest(self, hd_to_spend=1):
        """Spende Dadi Vita (XdY + Mod COS) per recuperare HP e ricarica i privilegi da riposo breve."""
        actual_spend = 0
        if hd_to_spend > 0 and getattr(self, "hit_dice_current", 0) > 0:
            actual_spend = min(hd_to_spend, self.hit_dice_current)
            self.hit_dice_current -= actual_spend
        
        cos_mod = self.get_modifier("COS")
            
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
        self.superiority_dice_current = self.superiority_dice_max
        
        # Reset custom class resources configured for Short Rest
        for res in getattr(self, "custom_resources", []):
            if isinstance(res, dict) and res.get("reset_on") == "short":
                res["current"] = res.get("max", 0)
        
        # Regola D&D 5e: I Warlock (Magia del Patto) ricaricano tutti gli slot incantesimo con un Riposo Breve!
        c_class = str(getattr(self, "char_class", "")).strip().lower()
        if "warlock" in c_class:
            for lvl, slot in getattr(self, "spell_slots", {}).items():
                try: slot_lvl = int(lvl)
                except (ValueError, TypeError): slot_lvl = 1
                if slot_lvl <= 5:
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

        # Ripristina Tenacia Implacabile (Mezzorco), Talento Fortunato, Portento (Divinatore) e Cariche Oggetti Magici
        self.relentless_endurance_used = False
        self.arcane_recovery_used = False
        self.sorcery_points_current = self.sorcery_points_max
        self.superiority_dice_current = self.superiority_dice_max
        if self.is_in_wild_shape():
            self.revert_wild_shape()
        if self.has_lucky_feat():
            self.lucky_points = 3
        sub_low = str(getattr(self, "subclass", "")).lower()
        feats_str = self._get_all_features_text()
        if any(k in sub_low or k in feats_str for k in ("divinazione", "divination", "portento", "portent")) and lvl >= 2:
            import random
            num_portent = 3 if lvl >= 14 else 2
            self.portent_dice = [random.randint(1, 20) for _ in range(num_portent)]
        self.recharge_magic_items()

    def _get_all_features_text(self) -> str:
        parts = [str(getattr(self, "features", "") or "")]
        for f in (getattr(self, "features_list", []) or []):
            if isinstance(f, dict):
                parts.append(f"{f.get('name', '')} {f.get('desc', '')}")
            else:
                parts.append(str(f))
        for t in (getattr(self, "traits", []) or []):
            parts.append(str(t))
        return " ".join(parts).lower()

    def has_halfling_luck(self) -> bool:
        """Verifica se il personaggio possiede il tratto razziale Fortuna dell'Halfling (ritira gli 1 naturali sul d20)."""
        race_low = str(getattr(self, "race", "") or "").lower()
        if "halfling" in race_low:
            return True
        txt = self._get_all_features_text()
        return any(k in txt for k in ("fortuna dell'halfling", "fortunato (halfling)", "halfling luck"))

    def has_great_weapon_fighting(self) -> bool:
        """Verifica se il personaggio possiede lo Stile di Combattimento: Combattere con Armi Possenti (ritira 1 e 2 ai danni)."""
        txt = self._get_all_features_text()
        return any(k in txt for k in ("combattere con armi possenti", "great weapon fighting", "armi possenti:"))

    def has_two_weapon_fighting_style(self) -> bool:
        """Verifica se il personaggio possiede lo Stile di Combattimento: Combattere con Due Armi (+Mod ai danni secondari)."""
        txt = self._get_all_features_text()
        return any(k in txt for k in ("combattere con due armi", "two-weapon fighting", "due armi:"))

    # --- D&D 5e RAW Class & Race Features ---
    def has_jack_of_all_trades(self) -> bool:
        """Tuttofare (Jack of All Trades - Bardo 2+ PHB p. 54)."""
        c_class = str(getattr(self, "char_class", "")).lower()
        classes = getattr(self, "classes", {})
        lvl = getattr(self, "level", 1) or 1
        for ck, cv in classes.items():
            if any(k in str(ck).lower() for k in ("bardo", "bard")):
                return int(cv) >= 2
        return any(k in c_class for k in ("bardo", "bard")) and int(lvl) >= 2

    def has_reliable_talent(self) -> bool:
        """Talento Affidabile (Reliable Talent - Ladro 11+ PHB p. 96)."""
        c_class = str(getattr(self, "char_class", "")).lower()
        classes = getattr(self, "classes", {})
        lvl = getattr(self, "level", 1) or 1
        for ck, cv in classes.items():
            if any(k in str(ck).lower() for k in ("ladro", "rogue")):
                return int(cv) >= 11
        return any(k in c_class for k in ("ladro", "rogue")) and int(lvl) >= 11

    def get_crit_threshold(self) -> int:
        """Restituisce la soglia minima del d20 per il colpo critico (Campione 19-20 / 18-20 PHB p. 72)."""
        sub_low = str(getattr(self, "subclass", "")).lower()
        feats_txt = self._get_all_features_text()
        lvl = getattr(self, "level", 1) or 1
        is_champion = any(k in sub_low or k in feats_txt for k in ("campione", "champion", "critico migliorato", "improved critical"))
        if is_champion:
            f_lvl = lvl
            for ck, cv in getattr(self, "classes", {}).items():
                if any(k in str(ck).lower() for k in ("guerriero", "fighter")):
                    f_lvl = int(cv)
            if f_lvl >= 15:
                return 18
            elif f_lvl >= 3:
                return 19
        return 20

    def get_brutal_critical_dice(self) -> int:
        """Restituisce il numero di dadi danno arma aggiuntivi sui colpi critici in mischia (Barbaro / Mezzorco)."""
        extra_dice = 0
        race_low = str(getattr(self, "race", "")).lower()
        feats_txt = self._get_all_features_text()
        if "mezzorco" in race_low or "half-orc" in race_low or "attacchi selvaggi" in feats_txt or "savage attacks" in feats_txt:
            extra_dice += 1

        c_class = str(getattr(self, "char_class", "")).lower()
        barb_lvl = 0
        for ck, cv in getattr(self, "classes", {}).items():
            if any(k in str(ck).lower() for k in ("barbaro", "barbarian")):
                barb_lvl = max(barb_lvl, int(cv))
        if barb_lvl == 0 and any(k in c_class for k in ("barbaro", "barbarian")):
            barb_lvl = int(getattr(self, "level", 1) or 1)
        if barb_lvl >= 17:
            extra_dice += 3
        elif barb_lvl >= 13:
            extra_dice += 2
        elif barb_lvl >= 9:
            extra_dice += 1
        return extra_dice

    def is_in_wild_shape(self) -> bool:
        """Verifica se il personaggio è attualmente trasformato in Forma Selvatica."""
        ws = getattr(self, "wild_shape", None)
        return isinstance(ws, dict) and bool(ws.get("active", False))

    def enter_wild_shape(self, beast_name: str, beast_hp: int, beast_ac: int, beast_speed: int = 30, beast_attributes: dict = None) -> tuple:
        """Trasforma il Druido in Forma Selvatica secondo D&D 5e RAW (PHB p. 66)."""
        if self.is_in_wild_shape():
            return False, "Il personaggio è già in Forma Selvatica."
        if beast_hp <= 0:
            return False, "I PV della bestia devono essere maggiori di 0."
        
        orig_attrs = dict(self.attributes)
        ws_data = {
            "active": True,
            "beast_name": beast_name,
            "beast_hp": int(beast_hp),
            "beast_max_hp": int(beast_hp),
            "original_hp": int(self.hp_current),
            "original_max_hp": int(self.hp_max),
            "original_ac": int(self.ac),
            "original_speed": int(self.speed),
            "original_attributes": orig_attrs
        }
        self.wild_shape = ws_data
        self.hp_current = int(beast_hp)
        self.hp_max = int(beast_hp)
        self.ac = int(beast_ac)
        self.speed = int(beast_speed)
        if beast_attributes and isinstance(beast_attributes, dict):
            for k in ("FOR", "DES", "COS", "STR", "DEX", "CON"):
                if k in beast_attributes:
                    self.attributes[k] = beast_attributes[k]
        return True, f"Trasformazione in {beast_name} completata ({beast_hp} PV, CA {beast_ac})."

    def revert_wild_shape(self, excess_damage: int = 0) -> tuple:
        """Ritorna alla forma normale del Druido gestendo il danno in eccesso (PHB p. 66)."""
        if not self.is_in_wild_shape():
            return False, "Il personaggio non è in Forma Selvatica."
        ws = self.wild_shape
        orig_hp = ws.get("original_hp", self.hp_current)
        orig_max = ws.get("original_max_hp", self.hp_max)
        orig_ac = ws.get("original_ac", 10)
        orig_speed = ws.get("original_speed", 30)
        orig_attrs = ws.get("original_attributes", {})
        
        if orig_attrs:
            self.attributes.update(orig_attrs)
        self.hp_max = orig_max
        self.ac = orig_ac
        self.speed = orig_speed
        
        eff_excess = max(0, int(excess_damage))
        self.hp_current = max(0, orig_hp - eff_excess)
        beast_name = ws.get("beast_name", "Bestia")
        ws["active"] = False
        ws["beast_hp"] = 0
        return True, f"Ritorno alla forma originale da {beast_name}. PV attuali: {self.hp_current}/{self.hp_max}."

    def convert_slot_to_sorcery_points(self, slot_level: int) -> tuple:
        """Fonte di Magia (Stregone PHB p. 101): Converte uno slot incantesimo (1-5) in Punti Stregoneria."""
        s_lvl = int(slot_level)
        if not (1 <= s_lvl <= 5):
            return False, "È possibile convertire solo slot incantesimo dal 1° al 5° cerchio."
        lvl_str = str(s_lvl)
        cur_slots = 0
        if isinstance(self.spell_slots.get(lvl_str), dict):
            cur_slots = self.spell_slots[lvl_str].get("current", 0)
        elif isinstance(self.spell_slots.get(lvl_str), list) and len(self.spell_slots[lvl_str]) >= 2:
            cur_slots = self.spell_slots[lvl_str][0]
        if cur_slots <= 0:
            return False, f"Nessuno slot incantesimo di {s_lvl}° cerchio disponibile."
        
        sp_cur = getattr(self, "sorcery_points_current", 0) or 0
        sp_max = getattr(self, "sorcery_points_max", 0) or getattr(self, "level", 1) or 1
        if sp_cur >= sp_max:
            return False, f"Punti Stregoneria già al massimo ({sp_max}/{sp_max})."

        if isinstance(self.spell_slots.get(lvl_str), dict):
            self.spell_slots[lvl_str]["current"] -= 1
        elif isinstance(self.spell_slots.get(lvl_str), list):
            self.spell_slots[lvl_str][0] -= 1

        new_sp = min(sp_max, sp_cur + s_lvl)
        gained = new_sp - sp_cur
        self.sorcery_points_current = new_sp
        self.sorcery_points_max = sp_max
        return True, f"Slot di {s_lvl}° cerchio convertito in {gained} Punti Stregoneria (Totale: {new_sp}/{sp_max})."

    def convert_sorcery_points_to_slot(self, slot_level: int) -> tuple:
        """Fonte di Magia (Stregone PHB p. 101): Crea uno slot incantesimo (1-5) spendendo Punti Stregoneria."""
        s_lvl = int(slot_level)
        cost_map = {1: 2, 2: 3, 3: 5, 4: 6, 5: 7}
        if s_lvl not in cost_map:
            return False, "È possibile creare slot solo dal 1° al 5° cerchio."
        cost = cost_map[s_lvl]
        sp_cur = getattr(self, "sorcery_points_current", 0) or 0
        if sp_cur < cost:
            return False, f"Punti Stregoneria insufficienti: necessari {cost} PE, disponibili {sp_cur}."
        
        lvl_str = str(s_lvl)
        if not hasattr(self, "spell_slots"):
            self.spell_slots = {str(i): {"max": 0, "current": 0} for i in range(1, 10)}
        slot_obj = self.spell_slots.get(lvl_str)
        if isinstance(slot_obj, dict):
            slot_obj["current"] = slot_obj.get("current", 0) + 1
            if slot_obj["current"] > slot_obj.get("max", 0):
                slot_obj["max"] = slot_obj["current"]
        elif isinstance(slot_obj, list) and len(slot_obj) >= 2:
            slot_obj[0] += 1
            if slot_obj[0] > slot_obj[1]:
                slot_obj[1] = slot_obj[0]
        else:
            self.spell_slots[lvl_str] = {"max": 1, "current": 1}

        self.sorcery_points_current = sp_cur - cost
        return True, f"Creato 1 slot incantesimo di {s_lvl}° cerchio (Spesi {cost} Punti Stregoneria, residui: {self.sorcery_points_current})."

    def use_metamagic(self, metamagic_name: str, cost: int) -> tuple:
        """Spende Punti Stregoneria per applicare un'opzione di Metamagia (PHB p. 101)."""
        c = max(1, int(cost))
        sp_cur = getattr(self, "sorcery_points_current", 0) or 0
        if sp_cur < c:
            return False, f"Punti Stregoneria insufficienti per {metamagic_name} (richiesti: {c}, attuali: {sp_cur})."
        self.sorcery_points_current = sp_cur - c
        return True, f"Metamagia '{metamagic_name}' attivata (-{c} Punti Stregoneria, rimasti: {self.sorcery_points_current})."

    def arcane_recovery(self, slots_to_regain: dict) -> tuple:
        """Recupero Arcano (Mago PHB p. 115): Recupera slot incantesimo fino a ceil(Livello Mago / 2) al Riposo Breve 1/giorno."""
        if getattr(self, "arcane_recovery_used", False):
            return False, "Recupero Arcano è già stato utilizzato oggi (si ricarica al Riposo Lungo)."
        
        w_lvl = getattr(self, "level", 1) or 1
        for ck, cv in getattr(self, "classes", {}).items():
            if any(k in str(ck).lower() for k in ("mago", "wizard", "druido", "druid")):
                w_lvl = int(cv)
        import math
        max_total_levels = math.ceil(w_lvl / 2)
        
        total_requested = 0
        for lvl_k, count in slots_to_regain.items():
            try:
                l_int = int(lvl_k)
                cnt = int(count)
            except (ValueError, TypeError):
                continue
            if l_int >= 6:
                return False, "Recupero Arcano non può ripristinare slot di 6° cerchio o superiore."
            if cnt > 0:
                total_requested += l_int * cnt

        if total_requested <= 0:
            return False, "Nessuno slot selezionato per il recupero."
        if total_requested > max_total_levels:
            return False, f"Livelli slot richiesti ({total_requested}) superano il massimo consentito ({max_total_levels})."

        for lvl_k, count in slots_to_regain.items():
            l_int = int(lvl_k)
            cnt = int(count)
            if cnt > 0:
                lvl_str = str(l_int)
                slot = self.spell_slots.get(lvl_str)
                if isinstance(slot, dict):
                    slot["current"] = min(slot.get("max", 0), slot.get("current", 0) + cnt)
                elif isinstance(slot, list) and len(slot) >= 2:
                    slot[0] = min(slot[1], slot[0] + cnt)

        self.arcane_recovery_used = True
        return True, f"Recupero Arcano completato: recuperati {total_requested} livelli di slot."

    def spend_superiority_die(self) -> tuple:
        """Spende e tira 1 Dado di Superiorità (Maestro della Battaglia PHB p. 73)."""
        cur = getattr(self, "superiority_dice_current", 0) or 0
        if cur <= 0:
            return False, 0, "Dadi di Superiorità esauriti."
        self.superiority_dice_current = cur - 1
        die_type = getattr(self, "superiority_die_type", "d8")
        sides = int(str(die_type).replace("d", "")) if str(die_type).replace("d", "").isdigit() else 8
        import random
        roll_res = random.randint(1, sides)
        return True, roll_res, f"Speso 1 dado [{die_type}]: risultato {roll_res} (Rimasti: {self.superiority_dice_current}/{getattr(self, 'superiority_dice_max', 4)})."


    def has_lucky_feat(self) -> bool:
        """Verifica se il personaggio possiede il talento Fortunato (Lucky - 3 punti fortuna per riposo lungo)."""
        for f in (getattr(self, "features_list", []) or []):
            if isinstance(f, dict):
                nm = str(f.get("name", "")).strip().lower()
                if nm in ("fortunato", "lucky", "talento: fortunato"):
                    return True
        txt = self._get_all_features_text()
        return "punti fortuna" in txt or "luck points" in txt or "talento: fortunato" in txt

    def use_portent_die(self, index: int = 0):
        """Consuma e restituisce uno dei dadi di Portento pre-tirati dal Mago Divinatore (PHB p. 116)."""
        if not hasattr(self, "portent_dice") or not isinstance(self.portent_dice, list) or not self.portent_dice:
            return None
        if 0 <= index < len(self.portent_dice):
            return self.portent_dice.pop(index)
        return self.portent_dice.pop(0)

    def use_lucky_point(self) -> bool:
        """Spende 1 Punto Fortuna del talento Fortunato (PHB p. 167)."""
        pts = int(getattr(self, "lucky_points", 0) or 0)
        if pts <= 0:
            return False
        self.lucky_points = pts - 1
        return True

    def use_item_charge(self, slot_index: int, cost: int = 1) -> tuple:
        """Spende cariche da un oggetto magico nell'inventario a griglia."""
        from common.item_modifiers import use_item_charge_dict
        grid = getattr(self, "inventory_grid", []) or []
        if not (0 <= slot_index < len(grid)) or not isinstance(grid[slot_index], dict):
            return False, "Slot inventario vuoto o non valido."
        return use_item_charge_dict(grid[slot_index], cost=cost)

    def recharge_magic_items(self) -> list:
        """Ricarica tutti gli oggetti magici dotati di cariche nell'inventario (es. al Riposo Lungo)."""
        from common.item_modifiers import recharge_item_dict
        messages = []
        for it in (getattr(self, "inventory_grid", []) or []):
            if isinstance(it, dict):
                msg = recharge_item_dict(it)
                if msg:
                    messages.append(msg)
        return messages

    def add_class_level(self, target_class: str, add_levels: int = 1) -> tuple:
        """
        Aggiunge livelli nella classe specificata gestendo il Multiclasse D&D 5e RAW (PHB p. 163-165):
        - Verifica prerequisiti di caratteristica (min 13 nella classe attuale e nella nuova)
        - Aggiorna il dizionario 'classes', la stringa 'char_class' e il livello totale
        - Ricalcola gli slot incantesimo secondo la Tabella Multiclasse se applicabile
        """
        from common.character_schema import check_multiclass_prerequisites, calculate_multiclass_spell_slots
        t_cls = str(target_class or self.char_class or "Guerriero").strip()
        if not hasattr(self, "classes") or not isinstance(self.classes, dict) or not self.classes:
            base_c = str(self.char_class or t_cls).split("/")[0].strip()
            self.classes = {base_c: max(1, int(getattr(self, "level", 1) or 1))}

        ok, msg = check_multiclass_prerequisites(self, t_cls)
        if not ok:
            return False, msg

        matched_key = next((k for k in self.classes if k.lower() == t_cls.lower()), t_cls)
        self.classes[matched_key] = int(self.classes.get(matched_key, 0)) + max(1, int(add_levels))
        self.level = min(20, sum(self.classes.values()))
        self.proficiency_bonus = 2 + (self.level - 1) // 4
        self.hit_dice_total = self.level

        if len(self.classes) > 1:
            self.char_class = " / ".join(f"{k} {v}" for k, v in self.classes.items())
        else:
            self.char_class = matched_key

        mc_slots = calculate_multiclass_spell_slots(self.classes, getattr(self, "subclass", ""))
        if any(v["max"] > 0 for v in mc_slots.values()):
            self.spell_slots = mc_slots

        return True, f"Livello acquisito in {matched_key} (Totale: Liv. {self.level})."

    def auto_populate_class_resources(self):
        """Popola le risorse 5e note in base alla classe se custom_resources è vuota (D&D 5e RAW)."""
        if getattr(self, "custom_resources", None):
            return
        self.custom_resources = []
        c_cls = str(getattr(self, "char_class", "")).lower()
        lvl = max(1, int(getattr(self, "level", 1) or 1))
        car_val = self.get_effective_attribute("CAR") if hasattr(self, "get_effective_attribute") else int(self.attributes.get("CAR", self.attributes.get("CHA", 10)))
        car_mod = max(1, (car_val - 10) // 2)
        
        if any(k in c_cls for k in ["barbar", "barbarian"]):
            rage = 2 if lvl < 3 else (3 if lvl < 6 else (4 if lvl < 12 else (5 if lvl < 17 else (6 if lvl < 20 else 99))))
            self.custom_resources.append({"name": "Ira (Rage)", "current": rage, "max": rage, "reset_on": "long"})
        elif any(k in c_cls for k in ["monk", "monaco"]):
            if lvl >= 2:
                self.custom_resources.append({"name": "Punti Ki", "current": lvl, "max": lvl, "reset_on": "short"})
        elif any(k in c_cls for k in ["bard", "bardo"]):
            rst = "short" if lvl >= 5 else "long"
            self.custom_resources.append({"name": "Ispirazione Bardica", "current": car_mod, "max": car_mod, "reset_on": rst})
        elif any(k in c_cls for k in ["druid", "druido"]):
            if lvl >= 2:
                self.custom_resources.append({"name": "Forma Selvatica", "current": 2, "max": 2, "reset_on": "short"})
        elif any(k in c_cls for k in ["paladin", "paladino"]):
            self.custom_resources.append({"name": "Mani Curative (Lay on Hands)", "current": lvl * 5, "max": lvl * 5, "reset_on": "long"})
            if lvl >= 3:
                self.custom_resources.append({"name": "Canale di Divinità", "current": 1, "max": 1, "reset_on": "short"})
        elif any(k in c_cls for k in ["cleric", "chierico"]):
            if lvl >= 2:
                ch_uses = 1 if lvl < 6 else (2 if lvl < 18 else 3)
                self.custom_resources.append({"name": "Canale di Divinità", "current": ch_uses, "max": ch_uses, "reset_on": "short"})
        elif any(k in c_cls for k in ["fighter", "guerriero"]):
            self.custom_resources.append({"name": "Secondo Fiato (Second Wind)", "current": 1, "max": 1, "reset_on": "short"})
            if lvl >= 2:
                act = 2 if lvl >= 17 else 1
                self.custom_resources.append({"name": "Azione Impetuosa (Action Surge)", "current": act, "max": act, "reset_on": "short"})
        elif any(k in c_cls for k in ["sorcerer", "stregone"]):
            if lvl >= 2:
                self.custom_resources.append({"name": "Punti Stregoneria", "current": lvl, "max": lvl, "reset_on": "long"})
        elif any(k in c_cls for k in ["warlock"]):
            if lvl >= 11:
                self.custom_resources.append({"name": "Arcanum Mistico (6° liv)", "current": 1, "max": 1, "reset_on": "long"})
            if lvl >= 13:
                self.custom_resources.append({"name": "Arcanum Mistico (7° liv)", "current": 1, "max": 1, "reset_on": "long"})
            if lvl >= 15:
                self.custom_resources.append({"name": "Arcanum Mistico (8° liv)", "current": 1, "max": 1, "reset_on": "long"})
            if lvl >= 17:
                self.custom_resources.append({"name": "Arcanum Mistico (9° liv)", "current": 1, "max": 1, "reset_on": "long"})

    def get_item_modifiers(self):
        """Calcola tutti i modificatori passivi derivanti dagli oggetti (equipaggiati e sintonizzati) secondo D&D 5e RAW."""
        from common.item_modifiers import calculate_character_item_modifiers
        return calculate_character_item_modifiers(self)

    def get_attunement_bonuses(self):
        """Calcola i modificatori passivi derivanti dagli oggetti sintonizzati (retrocompatibilità)."""
        mods = self.get_item_modifiers()
        return {
            "bonus_ac": mods.get("bonus_ac", 0),
            "bonus_saves": mods.get("bonus_saves", 0),
            "bonus_stats": mods.get("bonus_stats", {}),
            "set_stats": mods.get("set_stats", {})
        }

    def get_spell_dc_bonus(self) -> int:
        """Restituisce il bonus magico alla CD degli incantesimi conferito dagli oggetti."""
        mods = self.get_item_modifiers()
        return mods.get("bonus_spell_dc", 0)

    def get_spell_attack_bonus(self) -> int:
        """Restituisce il bonus magico al tiro per colpire con incantesimi conferito dagli oggetti."""
        mods = self.get_item_modifiers()
        return mods.get("bonus_spell_attack", 0)

    def get_effective_attribute(self, attr_name):
        from common.item_modifiers import canonical_stat_key
        canon = canonical_stat_key(attr_name)
        base = int(self.attributes.get(canon, 10))
        mods = self.get_item_modifiers()
        if canon in mods.get("set_stats", {}):
            base = max(base, mods["set_stats"][canon])
        if canon in mods.get("bonus_stats", {}):
            base += mods["bonus_stats"][canon]
        return base

    def get_modifier(self, attr_name: str) -> int:
        """Calcola il modificatore d'abilità per la caratteristica richiesta considerando attributi effettivi (oggetti magici, sintonizzazione)."""
        from common.item_modifiers import canonical_stat_key
        canonical = canonical_stat_key(attr_name)
        val = self.get_effective_attribute(canonical)
        return (val - 10) // 2

    def get_effective_ac(self):
        """Restituisce la CA effettiva calcolata da recalculate_ac() considerando armature magiche, scudi e sintonizzazioni."""
        return self.recalculate_ac()

    def get_effective_save_bonus(self, stat_name):
        from common.item_modifiers import canonical_stat_key
        canonical = canonical_stat_key(stat_name)
        stat_val = self.get_effective_attribute(canonical)
        mod = (stat_val - 10) // 2
        mods = self.get_item_modifiers()
        save_bonus = mod + mods.get("bonus_saves", 0)
        prof_saves = [canonical_stat_key(s) for s in getattr(self, "saving_throw_proficiencies", [])]
        if canonical in prof_saves:
            lvl = getattr(self, "level", 1) or 1
            pb = 2 + (max(1, int(lvl)) - 1) // 4
            save_bonus += pb
        return save_bonus

    def recalculate_ac(self):
        """Ricalcola dinamicamente la CA conforme a D&D 5e RAW considerando armature magiche (+1/+2/+3), scudi e oggetti."""
        from common.item_modifiers import compute_effective_ac
        self.ac = compute_effective_ac(self)
        return self.ac

    def check_has_darkvision(self) -> bool:
        """Determina se il personaggio possiede Scurovisione secondo le regole D&D 5e."""
        if getattr(self, "has_darkvision", None) is not None:
            return bool(self.has_darkvision)
        conds = [str(c).lower() for c in getattr(self, "conditions", [])]
        if any("scurovisione" in c or "darkvision" in c for c in conds):
            return True
        race = str(getattr(self, "race", "")).lower()
        dv_races = (
            "elfo", "elf", "nano", "dwarf", "mezzelfo", "half-elf", "mezzorco", 
            "half-orc", "gnomo", "gnome", "tiefling", "drow", "duergar", "aasimar", 
            "tabaxi", "coboldo", "kobold", "bugbear", "hobgoblin", "orco", "orc", 
            "goblin", "genasi del fuoco", "fire genasi", "genasi della terra", "earth genasi",
            "tritone", "triton"
        )
        if any(r in race for r in dv_races):
            return True
        senses = str(getattr(self, "senses", "")).lower()
        if "scurovisione" in senses or "darkvision" in senses:
            return True
        features_list = getattr(self, "features", [])
        if isinstance(features_list, str):
            features_list = [features_list]
        elif not isinstance(features_list, (list, tuple, set)):
            features_list = []
        feats = [str(f).lower() for f in features_list]
        if any("scurovisione" in f or "darkvision" in f for f in feats):
            return True
        traits = [str(t).lower() for t in getattr(self, "traits", [])]
        if any("scurovisione" in t or "darkvision" in t for t in traits):
            return True
        return getattr(self, "vision_radius", 6) > 6

    def update_class_resources_for_level(self, new_level: int):
        """Aggiorna le risorse di classe scalabili in base al livello (Ki, Rage, Mani Curative, ecc. - D&D 5e RAW)."""
        cls_name = str(getattr(self, "char_class", "")).lower()
        if not hasattr(self, "custom_resources") or not isinstance(self.custom_resources, list):
            self.custom_resources = []

        res_dict = {r.get("name"): r for r in self.custom_resources if isinstance(r, dict)}

        if "monaco" in cls_name or "monk" in cls_name:
            ki = res_dict.get("Punti Ki") or res_dict.get("Ki")
            if ki:
                ki["max"] = new_level
                ki["current"] = min(ki["max"], ki.get("current", new_level))
            elif new_level >= 2:
                self.custom_resources.append({"name": "Punti Ki", "current": new_level, "max": new_level, "reset_on": "short"})
        elif "barbaro" in cls_name or "barbarian" in cls_name:
            max_r = 2 if new_level < 3 else (3 if new_level < 6 else (4 if new_level < 12 else (5 if new_level < 17 else (6 if new_level < 20 else 99))))
            rage = res_dict.get("Ire") or res_dict.get("Ira") or res_dict.get("Rage") or res_dict.get("Ira (Rage)")
            if rage:
                rage["max"] = max_r
                rage["current"] = min(max_r, rage.get("current", max_r))
            else:
                self.custom_resources.append({"name": "Ira (Rage)", "current": max_r, "max": max_r, "reset_on": "long"})
        elif "paladino" in cls_name or "paladin" in cls_name:
            loh = res_dict.get("Imposizione delle Mani") or res_dict.get("Mani Curative") or res_dict.get("Mani Curative (Lay on Hands)")
            if loh:
                loh["max"] = new_level * 5
                loh["current"] = min(loh["max"], loh.get("current", loh["max"]))
            else:
                self.custom_resources.append({"name": "Mani Curative (Lay on Hands)", "current": new_level * 5, "max": new_level * 5, "reset_on": "long"})
            if new_level >= 3 and not (res_dict.get("Canale di Divinità") or res_dict.get("Incanalare Divinità")):
                self.custom_resources.append({"name": "Canale di Divinità", "current": 1, "max": 1, "reset_on": "short"})
        elif "chierico" in cls_name or "cleric" in cls_name:
            ch_uses = 1 if new_level < 6 else (2 if new_level < 18 else 3)
            ch = res_dict.get("Canale di Divinità") or res_dict.get("Incanalare Divinità")
            if ch:
                ch["max"] = ch_uses
                ch["current"] = min(ch_uses, ch.get("current", ch_uses))
            elif new_level >= 2:
                self.custom_resources.append({"name": "Canale di Divinità", "current": ch_uses, "max": ch_uses, "reset_on": "short"})
        elif "guerriero" in cls_name or "fighter" in cls_name:
            act = 2 if new_level >= 17 else 1
            asurge = res_dict.get("Azione Impetuosa (Action Surge)") or res_dict.get("Azione Impetuosa") or res_dict.get("Action Surge")
            if asurge:
                asurge["max"] = act
                asurge["current"] = min(act, asurge.get("current", act))
            elif new_level >= 2:
                self.custom_resources.append({"name": "Azione Impetuosa (Action Surge)", "current": act, "max": act, "reset_on": "short"})
        elif "druido" in cls_name or "druid" in cls_name:
            if new_level >= 2 and not res_dict.get("Forma Selvatica"):
                self.custom_resources.append({"name": "Forma Selvatica", "current": 2, "max": 2, "reset_on": "short"})
        elif "bardo" in cls_name or "bard" in cls_name:
            binsp = res_dict.get("Ispirazione Bardica") or res_dict.get("Bardic Inspiration")
            if binsp and new_level >= 5:
                binsp["reset_on"] = "short"
        elif "stregone" in cls_name or "sorcerer" in cls_name:
            sp = res_dict.get("Punti Stregoneria") or res_dict.get("Sorcery Points")
            if sp and new_level >= 2:
                sp["max"] = new_level
                sp["current"] = min(sp["max"], sp.get("current", sp["max"]))
            elif new_level >= 2:
                self.custom_resources.append({"name": "Punti Stregoneria", "current": new_level, "max": new_level, "reset_on": "long"})
        elif "warlock" in cls_name:
            arcanum_levels = [(11, 6), (13, 7), (15, 8), (17, 9)]
            for min_lvl, slot_lvl in arcanum_levels:
                if new_level >= min_lvl:
                    name = f"Arcanum Mistico ({slot_lvl}° liv)"
                    if name not in res_dict:
                        self.custom_resources.append({"name": name, "current": 1, "max": 1, "reset_on": "long"})

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
            if item.get("_coins_synced") and hasattr(self, "currency") and isinstance(self.currency, dict) and sum(max(0, int(v)) for v in self.currency.values() if isinstance(v, (int, float, str)) and str(v).isdigit()) > 0:
                continue
            c = item.get("container")
            if not c:
                itype = str(item.get("type", "")).strip().lower()
                c = "equipped" if itype in ("arma", "armatura", "scudo", "weapon", "armor", "shield") else "backpack"
            if c == container_key:
                try:
                    w = float(item.get("weight", 0.0) or 0.0)
                    if w <= 0.0 and item.get("name"):
                        from common.starter_equipment import lookup_standard_weight
                        w = lookup_standard_weight(item.get("name", ""))
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
            "tiny": 0.5, "minuscola": 0.5, "piccolissima": 0.5,
            "small": 1.0, "piccola": 1.0,
            "medium": 1.0, "media": 1.0,
            "large": 2.0, "grande": 2.0,
            "huge": 4.0, "enorme": 4.0,
            "gargantuan": 8.0, "mastodontica": 8.0
        }
        sz = str(getattr(self, "size", "medium") or "medium").lower().strip()
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
            "boh_max": 500.0,
            "boh_overloaded": (boh_weight > 500.0),
            "haversack_weight": haversack_weight,
            "mount_weight": mount_weight
        }

    def get_effective_speed(self) -> int | float:
        """
        Calcola la velocità di movimento effettiva del personaggio (in ft o m)
        applicando bonus magici degli oggetti, le penalità dell'Ingombro (PHB p. 176) e dell'Affaticamento (Exhaustion).
        """
        base_speed = float(getattr(self, "speed", 30) or 30)
        unit = getattr(self, "speed_unit", "ft")
        mods = self.get_item_modifiers() if hasattr(self, "get_item_modifiers") else {}
        bonus_spd = float(mods.get("bonus_speed", 0))
        if unit == "m" and abs(bonus_spd) >= 5.0:
            bonus_spd = round(bonus_spd * 0.3, 1)
        base_speed += bonus_spd
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
        cos_mod = self.get_modifier("COS")
            
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

    def sync_weapons_from_inventory(self):
        """
        Sincronizza automaticamente gli oggetti di tipo Arma presenti in inventory_grid
        con la lista self.weapons per il pannello Combattimento, estraendo dadi danno,
        tipo danno, caratteristica (FOR/DES) e bonus magico (+1/+2/+3).
        """
        import re
        from common.item_modifiers import extract_magic_bonus

        if not hasattr(self, "weapons") or not isinstance(self.weapons, list):
            self.weapons = []

        existing_by_name = {
            str(w.get("name", "")).strip().lower(): w
            for w in self.weapons
            if isinstance(w, dict) and w.get("name")
        }

        for it in (getattr(self, "inventory_grid", []) or []):
            if not it or not isinstance(it, dict):
                continue
            itype = str(it.get("type", "")).strip().lower()
            iname = str(it.get("name", "")).strip()
            if not iname:
                continue
            if itype not in ("arma", "weapon", "arma da mischia", "arma a distanza", "arma semplice", "arma da guerra"):
                continue
            norm_nm = iname.lower()
            desc = str(it.get("desc", "") or "")
            desc_l = desc.lower()

            m_bonus = int(it.get("bonus", 0) or 0)
            if m_bonus == 0:
                m_bonus = extract_magic_bonus(iname) or extract_magic_bonus(desc)

            if norm_nm in existing_by_name:
                if m_bonus > 0 and int(existing_by_name[norm_nm].get("bonus", 0) or 0) == 0:
                    existing_by_name[norm_nm]["bonus"] = m_bonus
                continue

            # Estrai dado danno dalla descrizione (es. '1d8', '2d6', '1d12')
            d_match = re.search(r'\b(\d+d\d+)\b', desc_l)
            dmg_dice = d_match.group(1) if d_match else str(it.get("damage_dice", "1d8"))

            # Estrai tipo di danno
            dmg_type = str(it.get("damage_type", ""))
            if not dmg_type:
                if "taglient" in desc_l or "slashing" in desc_l:
                    dmg_type = "Tagliente"
                elif "perforant" in desc_l or "piercing" in desc_l:
                    dmg_type = "Perforante"
                elif "contundent" in desc_l or "bludgeoning" in desc_l:
                    dmg_type = "Contundente"
                else:
                    dmg_type = "Tagliente"

            is_ranged = any(k in norm_nm or k in desc_l for k in ["arco", "balestra", "fionda", "cerbottana", "gittata", "munizioni", "ranged"])
            is_finesse = any(k in norm_nm or k in desc_l for k in ["stocco", "pugnale", "scimitarra", "spada corta", "frusta", "accurata", "finesse"])
            w_type = "Distanza (Munizioni)" if is_ranged else ("Mischia (Accurata)" if is_finesse else "Mischia")
            ability = "DES" if (is_ranged or is_finesse) else "FOR"

            new_w = {
                "name": iname,
                "type": w_type,
                "ability": ability,
                "damage_dice": dmg_dice,
                "damage_type": dmg_type,
                "bonus": m_bonus,
                "proficient": True
            }
            self.weapons.append(new_w)
            existing_by_name[norm_nm] = new_w


    def to_dict(self):
        import copy
        from common.character_schema import normalize_character_dict
        raw = copy.deepcopy(self.__dict__)
        return normalize_character_dict(raw)
    
    @staticmethod
    def from_dict(data):
        from common.character_schema import normalize_character_dict
        norm_data = normalize_character_dict(data) if isinstance(data, dict) else {}
        c = Character()
        for key, value in norm_data.items():
            if hasattr(c, key):
                setattr(c, key, value)
        # Assicuriamoci che l'inventario a griglia esista anche se carichiamo un vecchio PG
        if not hasattr(c, "inventory_grid") or not isinstance(c.inventory_grid, list):
            c.inventory_grid = [None] * 25
            # Retrocompatibilità
            old_inv = getattr(c, "inventory", "")
            if old_inv:
                c.inventory_grid[0] = {"name": "Vecchio Inv.", "type": "Misto", "desc": old_inv, "qty": 1}
        else:
            while len(c.inventory_grid) < 25:
                c.inventory_grid.append(None)
        
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
        if not hasattr(c, "active_effects") or not isinstance(c.active_effects, list):
            c.active_effects = []
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
            
        if not getattr(c, "starting_kit_applied", False) and getattr(c, "char_class", None) and getattr(c, "level", 1) == 1:
            has_real_items = any(it and it.get("name") != "Zaino Base" for it in c.inventory_grid)
            if not has_real_items and len(getattr(c, "spellbook", [])) == 0:
                from common.starter_equipment import apply_class_and_race_starter_kit
                apply_class_and_race_starter_kit(c)

        c.sync_weapons_from_inventory()

        # Se la lista armi è ancora vuota, crea armi base compatibili
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
