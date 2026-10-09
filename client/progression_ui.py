import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import requests
from common.theme import apply_modern_window_style
from server.compendium_ui import CompendiumDialog

CLASS_MAP = {
    "barbaro": "barbarian",
    "guerriero": "fighter",
    "mago": "wizard",
    "chierico": "cleric",
    "ladro": "rogue",
    "paladino": "paladin",
    "ranger": "ranger",
    "stregone": "sorcerer",
    "bardo": "bard",
    "druido": "druid",
    "monaco": "monk",
    "warlock": "warlock"
}

HIT_DICE_MAP = {
    "barbarian": 12,
    "fighter": 10,
    "paladin": 10,
    "ranger": 10,
    "bard": 8,
    "cleric": 8,
    "druid": 8,
    "monk": 8,
    "rogue": 8,
    "warlock": 8,
    "sorcerer": 6,
    "wizard": 6
}

class LevelUpDialog(tk.Toplevel):
    def __init__(self, master, character, update_callback):
        super().__init__(master)
        self.title("Sali di Livello!")
        self.geometry("500x600")
        apply_modern_window_style(self)
        self.character = character
        self.update_callback = update_callback
        self.api_data = None
        self.new_features = []
        
        self.setup_ui()
        self.fetch_level_data()
        
    def setup_ui(self):
        ttk.Label(self, text=f"Livello {self.character.level} -> {self.character.level + 1}!", font=("Georgia", 14, "bold")).pack(pady=10)
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # TAB 1: Salute e Progressione Base
        self.tab_health = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_health, text="Salute")
        
        hp_frame = ttk.LabelFrame(self.tab_health, text="Aumento Punti Ferita")
        hp_frame.pack(fill=tk.X, padx=10, pady=10)
        
        char_class_en = CLASS_MAP.get(self.character.char_class.lower(), None)
        hd = HIT_DICE_MAP.get(char_class_en, 8) if char_class_en else 8
        avg_hp = (hd // 2) + 1
        
        self.hp_choice = tk.StringVar(value="media")
        
        rb_media = ttk.Radiobutton(hp_frame, text=f"Prendi il valore medio ({avg_hp})", variable=self.hp_choice, value="media", command=self.update_hp_entry)
        rb_media.pack(anchor="w", padx=5, pady=2)
        
        rb_roll = ttk.Radiobutton(hp_frame, text=f"Tira il Dado Vita (1d{hd})", variable=self.hp_choice, value="roll", command=self.update_hp_entry)
        rb_roll.pack(anchor="w", padx=5, pady=2)
        
        ttk.Label(hp_frame, text="Valore da aggiungere (senza Costituzione, aggiunto in automatico):").pack(anchor="w", padx=5, pady=(10,0))
        self.hp_add_var = tk.IntVar(value=avg_hp)
        self.hp_entry = ttk.Entry(hp_frame, textvariable=self.hp_add_var, width=10)
        self.hp_entry.pack(anchor="w", padx=5, pady=2)
        self.hp_entry.configure(state="readonly")
        self.avg_hp = avg_hp
        
        # TAB 2: Privilegi (Popolati da API)
        self.tab_features = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_features, text="Nuovi Privilegi")
        
        self.features_listbox = tk.Listbox(self.tab_features, font=("Georgia", 10))
        self.features_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.lbl_loading = ttk.Label(self.tab_features, text="Caricamento dati dall'API...")
        self.lbl_loading.pack(pady=5)
        
        # TAB 3: Magia e Statistiche
        self.tab_magic = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_magic, text="Statistiche/Magia")
        
        self.stats_frame = ttk.LabelFrame(self.tab_magic, text="Aumento Punteggi di Caratteristica")
        self.stats_frame.pack(fill=tk.X, padx=10, pady=10)
        self.lbl_stats = ttk.Label(self.stats_frame, text="Nessun aumento in questo livello.")
        self.lbl_stats.pack(padx=5, pady=5)
        
        self.magic_frame = ttk.LabelFrame(self.tab_magic, text="Incantesimi")
        self.magic_frame.pack(fill=tk.X, padx=10, pady=10)
        self.lbl_magic = ttk.Label(self.magic_frame, text="Nessun aggiornamento magico o classe non magica.")
        self.lbl_magic.pack(padx=5, pady=5)
        
        btn_spells = ttk.Button(self.magic_frame, text="Cerca Incantesimi", command=self.open_compendium)
        btn_spells.pack(padx=5, pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=10)
        self.btn_apply = ttk.Button(btn_frame, text="Applica", command=self.apply, style="Primary.TButton")
        self.btn_apply.pack(side=tk.RIGHT, padx=10)
        self.btn_apply.state(["disabled"]) # Disable until API loaded
        ttk.Button(btn_frame, text="Annulla", command=self.destroy).pack(side=tk.RIGHT)
        
    def update_hp_entry(self):
        if self.hp_choice.get() == "media":
            self.hp_add_var.set(self.avg_hp)
            self.hp_entry.configure(state="readonly")
        else:
            self.hp_entry.configure(state="normal")
            
    def open_compendium(self):
        CompendiumDialog(self.master, is_dm=False)

    def fetch_level_data(self):
        char_class_en = CLASS_MAP.get(self.character.char_class.lower(), None)
        if not char_class_en:
            self.lbl_loading.config(text=f"Classe '{self.character.char_class}' non supportata dall'API.")
            self.btn_apply.state(["!disabled"])
            return
            
        new_level = self.character.level + 1
        url = f"https://www.dnd5eapi.co/api/classes/{char_class_en}/levels/{new_level}"
        
        def _fetch():
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    self.master.after(0, lambda: self.on_api_success(data))
                else:
                    self.master.after(0, lambda: self.on_api_error(f"Errore {resp.status_code}"))
            except Exception as e:
                self.master.after(0, lambda: self.on_api_error(str(e)))
                
        threading.Thread(target=_fetch, daemon=True).start()
        
    def on_api_error(self, error_msg):
        self.lbl_loading.config(text=f"Errore API: {error_msg}")
        self.btn_apply.state(["!disabled"])
        
    def on_api_success(self, data):
        self.api_data = data
        self.lbl_loading.config(text="Dati caricati con successo!")
        self.btn_apply.state(["!disabled"])
        
        # Features
        if "features" in data:
            for f in data["features"]:
                self.new_features.append(f["name"])
                self.features_listbox.insert(tk.END, f["name"])
        if not self.new_features:
            self.features_listbox.insert(tk.END, "Nessun nuovo privilegio in questo livello.")
            
        # Stats
        abi = data.get("ability_score_bonuses", 0)
        if abi > 0:
            self.lbl_stats.config(text="Hai ottenuto un Aumento dei Punteggi di Caratteristica!\nRicordati di aggiungere +2 a una stat o +1 a due stat\n(o prendere un talento) nella scheda principale.")
            
        # Magic
        spellcasting = data.get("spellcasting")
        if spellcasting:
            slots_text = "I tuoi slot incantesimo verranno aggiornati automaticamente."
            self.lbl_magic.config(text=slots_text)
            
    def apply(self):
        try:
            hp_inc = self.hp_add_var.get()
        except ValueError:
            hp_inc = 0
            
        cos_mod = (self.character.attributes.get("COS", 10) - 10) // 2
        total_hp_inc = hp_inc + cos_mod
        if total_hp_inc < 1:
            total_hp_inc = 1 # Minimum 1 HP per level
            
        self.character.level += 1
        self.character.hp_max += total_hp_inc
        self.character.hp_current += total_hp_inc
        
        # Increment hit dice total
        if hasattr(self.character, "hit_dice_total"):
            self.character.hit_dice_total += 1
            self.character.hit_dice_current += 1
        
        # Features
        if self.new_features:
            feats_str = "\n".join([f"- {feat}" for feat in self.new_features])
            if hasattr(self.character, "features") and self.character.features:
                self.character.features += f"\n\n--- Livello {self.character.level} ---\n{feats_str}"
            else:
                self.character.features = f"--- Livello {self.character.level} ---\n{feats_str}"
                
        # Spellcasting
        if self.api_data and "spellcasting" in self.api_data:
            sc = self.api_data["spellcasting"]
            for i in range(1, 10):
                key = f"spell_slots_level_{i}"
                if key in sc:
                    max_slots = sc[key]
                    if str(i) in self.character.spell_slots:
                        self.character.spell_slots[str(i)][1] = max_slots
                    else:
                        self.character.spell_slots[str(i)] = [0, max_slots]
                        
        self.update_callback()
        self.destroy()
