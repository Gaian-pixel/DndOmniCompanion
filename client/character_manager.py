import os
from common.file_utils import atomic_save_json, load_json

CHARACTER_FILE = "client_data/characters.json"

class Character:
    def __init__(self, name="Nuovo Personaggio", campaign="Nessuna Campagna"):
        self.id = os.urandom(4).hex() # Unique ID
        self.name = name
        self.campaign = campaign
        self.race = ""
        self.char_class = ""
        self.level = 1
        self.exp = 0
        self.alignment = ""
        self.background = ""
        
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
        self.death_saves = {"successes": 0, "failures": 0}
        self.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
        self.hotbar = [""] * 10
        self.last_position = None
        
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
            elif isinstance(self.spell_slots[lvl], list):
                self.spell_slots[lvl][0] = 0
        lvl = getattr(self, "level", 1) or 1
        max_rage = 2 if lvl < 3 else (3 if lvl < 6 else (4 if lvl < 12 else 5))
        self.class_resources = {
            "second_wind": True,
            "action_surge": True,
            "rage_current": max_rage,
            "rage_max": max_rage
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
        if not hasattr(c, "travel_role"):
            c.travel_role = "Nessuna"
        if not hasattr(c, "marching_order"):
            c.marching_order = "Centro"
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
