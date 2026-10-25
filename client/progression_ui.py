import tkinter as tk
from tkinter import ttk
import threading
try:
    import requests
except ImportError:
    requests = None
import urllib.request
import json
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
        self.minsize(500, 600)
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

        # Sottoclasse / Archetipo (se non ancora scelta)
        if not getattr(self.character, "subclass", ""):
            subclass_frame = ttk.LabelFrame(self.tab_health, text="🌟 Sottoclasse / Archetipo 5e")
            subclass_frame.pack(fill=tk.X, padx=10, pady=(6, 10))
            
            ttk.Label(subclass_frame, text="Scegli o inserisci il tuo Archetipo per questa classe:").pack(anchor="w", padx=5, pady=(2, 2))
            self.subclass_choice_var = tk.StringVar(value="")
            from client.character_sheet_ui import SRD_SUBCLASSES
            c_cls = (self.character.char_class or "").lower().strip()
            options = []
            for k, v in SRD_SUBCLASSES.items():
                if k in c_cls or c_cls in k:
                    options = v
                    break
            self.subclass_choice_combo = ttk.Combobox(subclass_frame, textvariable=self.subclass_choice_var, values=options, width=32)
            self.subclass_choice_combo.pack(anchor="w", padx=5, pady=(2, 6))
        
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

    def _safe_ui(self, callback):
        try:
            if hasattr(self, "winfo_exists") and not self.winfo_exists():
                return
            if hasattr(self, "master") and hasattr(self.master, "winfo_exists") and not self.master.winfo_exists():
                return
            self.master.after(0, callback)
        except Exception:
            pass

    def _fallback_offline(self, new_level):
        try:
            from common.srd_offline import get_class_level_features_offline
            off = get_class_level_features_offline(self.character.char_class, new_level)
            features_list = [{"name": f} if isinstance(f, str) else f for f in off.get("features", [])]
            spellcasting = {}
            for lvl_str, count in off.get("spell_slots", {}).items():
                spellcasting[f"spell_slots_level_{lvl_str}"] = count

            asi = 0
            for f in off.get("features", []):
                if "Aumento Punteggi" in str(f) or "ASI" in str(f):
                    asi = 1
                    break

            data = {
                "level": new_level,
                "ability_score_bonuses": asi,
                "features": features_list,
                "spellcasting": spellcasting if spellcasting else None,
                "offline": True
            }
            if features_list or spellcasting or asi:
                self._safe_ui(lambda: self.on_api_success(data, is_offline=True))
                return True
        except Exception as e:
            print("[PROGRESSION] Errore fallback offline:", e)
        return False

    def fetch_level_data(self):
        raw_cls = (getattr(self.character, "char_class", "") or "").lower().strip()
        base_cls = raw_cls.split("(")[0].split("/")[0].strip()
        char_class_en = CLASS_MAP.get(base_cls, base_cls if base_cls in HIT_DICE_MAP else None)
        new_level = self.character.level + 1

        if not char_class_en:
            if not self._fallback_offline(new_level):
                self.lbl_loading.config(text=f"Classe '{self.character.char_class}' non supportata.")
                self.btn_apply.state(["!disabled"])
            return

        url = f"https://www.dnd5eapi.co/api/classes/{char_class_en}/levels/{new_level}"
        
        def _fetch():
            try:
                data = None
                if requests:
                    resp = requests.get(url, timeout=3)
                    if resp.status_code == 200:
                        data = resp.json()
                else:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=3) as response:
                        if response.status == 200:
                            data = json.loads(response.read().decode('utf-8'))
                
                if data:
                    self._safe_ui(lambda d=data: self.on_api_success(d))
                else:
                    if not self._fallback_offline(new_level):
                        self._safe_ui(lambda: self.on_api_error("Dati non disponibili"))
            except Exception as e:
                err_msg = str(e)
                if not self._fallback_offline(new_level):
                    self._safe_ui(lambda msg=err_msg: self.on_api_error(msg))
                
        threading.Thread(target=_fetch, daemon=True).start()
        
    def on_api_error(self, error_msg):
        self.lbl_loading.config(text=f"Errore API: {error_msg}")
        self.btn_apply.state(["!disabled"])
        
    def on_api_success(self, data, is_offline=False):
        self.api_data = data
        if is_offline or data.get("offline"):
            self.lbl_loading.config(text="Dati caricati da SRD locale (offline)")
        else:
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
                
        # Sottoclasse
        chosen_sub = getattr(self, "subclass_choice_var", None)
        if chosen_sub and chosen_sub.get().strip():
            self.character.subclass = chosen_sub.get().strip()

        # Spellcasting
        if self.api_data and "spellcasting" in self.api_data:
            sc = self.api_data["spellcasting"]
            for i in range(1, 10):
                key = f"spell_slots_level_{i}"
                if key in sc:
                    max_slots = sc[key]
                    if str(i) in self.character.spell_slots:
                        if isinstance(self.character.spell_slots[str(i)], dict):
                            self.character.spell_slots[str(i)]["max"] = max_slots
                            self.character.spell_slots[str(i)]["current"] = max_slots
                        else:
                            self.character.spell_slots[str(i)] = [max_slots, max_slots]
                    else:
                        self.character.spell_slots[str(i)] = {"max": max_slots, "current": max_slots}
                        
        self.update_callback()
        self.destroy()
