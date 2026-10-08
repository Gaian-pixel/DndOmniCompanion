import json
import os

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
        self.ac = 10
        self.initiative = 0
        self.speed = 9
        self.proficiency_bonus = 2
        self.hit_dice_total = 1
        self.hit_dice_current = 1
        self.hit_dice_type = "d8"
        self.death_saves = {"successes": 0, "failures": 0}
        self.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
        self.hotbar = [""] * 10
        
        # Testo libero / Griglia
        self.inventory_grid = [None] * 25 # Griglia 5x5
        self.features = ""
        self.spell_slots = {str(i): [0,0] for i in range(1, 10)} # "livello": [usati, massimi]
        self.spell_list = [] # [{"name": "Palla di Fuoco", "level": 3, "time": "1 Azione", "range": "36m", "desc": "..."}]
        self.notes = ""
        self.skills = {
            "Acrobazia": 0, "Addestrare Animali": 0, "Arcano": 0, "Atletica": 0,
            "Furtività": 0, "Indagare": 0, "Inganno": 0, "Intimidire": 0,
            "Intrattenere": 0, "Intuizione": 0, "Medicina": 0, "Natura": 0,
            "Percezione": 0, "Persuasione": 0, "Prestidigitazione": 0,
            "Religione": 0, "Sopravvivenza": 0, "Storia": 0
        }

    
    def long_rest(self):
        self.hp_current = self.hp_max
        regained = max(1, self.hit_dice_total // 2) if self.hit_dice_total > 0 else 0
        self.hit_dice_current = min(self.hit_dice_total, self.hit_dice_current + regained)
        self.death_saves = {"successes": 0, "failures": 0}
        for lvl in self.spell_slots:
            self.spell_slots[lvl][0] = 0

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
            c.spell_slots = {str(i): [0,0] for i in range(1, 10)}
        if not hasattr(c, "spell_list") or not isinstance(c.spell_list, list):
            c.spell_list = []
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
            
        return c

class CharacterManager:
    def __init__(self):
        self.characters = []
        self.load_characters()
        
    def load_characters(self):
        if not os.path.exists("client_data"):
            os.makedirs("client_data")
        if not os.path.exists(CHARACTER_FILE):
            self.characters = []
            return
            
        with open(CHARACTER_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                self.characters = [Character.from_dict(d) for d in data]
            except json.JSONDecodeError:
                self.characters = []
                
    def save_characters(self):
        if not os.path.exists("client_data"):
            os.makedirs("client_data")
        with open(CHARACTER_FILE, "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in self.characters], f, indent=4)
            
    def add_character(self, character):
        self.characters.append(character)
        self.save_characters()
        
    def update_character(self, character):
        for i, c in enumerate(self.characters):
            if c.id == character.id:
                self.characters[i] = character
                break
        self.save_characters()

    def get_character_by_id(self, char_id):
        for c in self.characters:
            if c.id == char_id:
                return c
        return None

