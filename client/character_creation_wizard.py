import tkinter as tk
from common.messagebox import messagebox
from tkinter import ttk
from .character_manager import Character
from common.theme import apply_modern_window_style

RACES = {
    "Umano": {"desc": "Gli umani sono i più adattabili e ambiziosi tra le razze comuni. \nBonus: +1 a tutte le caratteristiche.\nVelocità: 30 ft.", "bonuses": {"FOR": 1, "DES": 1, "COS": 1, "INT": 1, "SAG": 1, "CAR": 1}, "speed": 30},
    "Elfo": {"desc": "Un popolo magico e di fascino ultraterreno, longevo e affine alla natura.\nBonus: +2 Destrezza.\nTratti: Scurovisione, Sensi Acuti, Retaggio Fatato, Trance.\nVelocità: 30 ft.", "bonuses": {"DES": 2}, "speed": 30},
    "Nano": {"desc": "Fieri e resistenti, noti come abili guerrieri, minatori e lavoratori di pietra e metallo.\nBonus: +2 Costituzione.\nTratti: Scurovisione, Resilienza Nanica, Addestramento in combattimento.\nVelocità: 25 ft.", "bonuses": {"COS": 2}, "speed": 25},
    "Halfling": {"desc": "Un popolo minuto e pacifico, noto per la sua fortuna e destrezza.\nBonus: +2 Destrezza.\nTratti: Fortunato, Coraggioso, Agilità Halfling.\nVelocità: 25 ft.", "bonuses": {"DES": 2}, "speed": 25},
    "Draconide": {"desc": "Umanoidi nati dal sangue dei draghi, fieri e dediti all'onore.\nBonus: +2 Forza, +1 Carisma.\nTratti: Ascendenza Draconica, Arma a Soffio, Resistenza ai Danni.\nVelocità: 30 ft.", "bonuses": {"FOR": 2, "CAR": 1}, "speed": 30},
    "Mezzelfo": {"desc": "Uniscono il meglio di due mondi: la curiosità umana e la grazia elfica.\nBonus: +2 Carisma, +1 a altre due caratteristiche a scelta.\nTratti: Scurovisione, Retaggio Fatato, Versatilità nelle Competenze.\nVelocità: 30 ft.", "bonuses": {"CAR": 2, "DES": 1, "INT": 1}, "speed": 30},
    "Mezzorco": {"desc": "Fieri e selvaggi, guidati da forti passioni e da una forza fisica impressionante.\nBonus: +2 Forza, +1 Costituzione.\nTratti: Scurovisione, Minaccioso, Tenacia Implacabile, Attacchi Selvaggi.\nVelocità: 30 ft.", "bonuses": {"FOR": 2, "COS": 1}, "speed": 30},
    "Gnomo": {"desc": "Pieni di energia ed entusiasmo, inventori curiosi e maghi ingegnosi.\nBonus: +2 Intelligenza.\nTratti: Scurovisione, Astuzia Gnomesca.\nVelocità: 25 ft.", "bonuses": {"INT": 2}, "speed": 25},
    "Tiefling": {"desc": "Umanoidi toccati dai piani infernali, spesso guardati con sospetto.\nBonus: +2 Carisma, +1 Intelligenza.\nTratti: Scurovisione, Resistenza Infernale, Eredità Infernale.\nVelocità: 30 ft.", "bonuses": {"CAR": 2, "INT": 1}, "speed": 30}
}

CLASSES = {
    "Barbaro": {"desc": "Un feroce guerriero di origini primitive che può entrare in un'ira da battaglia.\nDado Vita: d12.\nCompetenze: Armature leggere/medie, scudi, armi semplici e marziali.", "hd": 12},
    "Bardo": {"desc": "Un incantatore la cui magia deriva dalla musica, dall'arte o dall'oratoria.\nDado Vita: d8.\nCompetenze: Armature leggere, armi semplici, balestre a mano, spade lunghe, spade corte.", "hd": 8},
    "Chierico": {"desc": "Un campione sacerdotale che impugna la magia divina al servizio di una divinità.\nDado Vita: d8.\nCompetenze: Armature leggere/medie, scudi, armi semplici.", "hd": 8},
    "Druido": {"desc": "Un sacerdote dell'Antica Fede, incantatore legato ai poteri della natura e della mutaforma.\nDado Vita: d8.\nCompetenze: Armature leggere/medie (non di metallo), scudi, clave, pugnali, dardi.", "hd": 8},
    "Guerriero": {"desc": "Un maestro del combattimento marziale, addestrato in un'ampia varietà di armi e armature.\nDado Vita: d10.\nCompetenze: Tutte le armature, scudi, armi semplici e marziali.", "hd": 10},
    "Ladro": {"desc": "Un mascalzone che usa la furtività e i trucchetti per superare ostacoli e nemici.\nDado Vita: d8.\nCompetenze: Armature leggere, armi semplici, balestre a mano, spade lunghe, spade corte.", "hd": 8},
    "Mago": {"desc": "Un incantatore arcano che attinge la magia dallo studio rigoroso dei tomi e dei segreti arcani.\nDado Vita: d6.\nCompetenze: Pugnali, dardi, fionde, bastoni ferrati, balestre leggere.", "hd": 6},
    "Monaco": {"desc": "Un maestro delle arti marziali che imbriglia il potere del corpo per perseguire la perfezione fisica e spirituale.\nDado Vita: d8.\nCompetenze: Armi semplici, spade corte.", "hd": 8},
    "Paladino": {"desc": "Un sacro guerriero vincolato da un giuramento, che unisce poteri divini ad addestramento militare.\nDado Vita: d10.\nCompetenze: Tutte le armature, scudi, armi semplici e marziali.", "hd": 10},
    "Ranger": {"desc": "Un esploratore e cacciatore che usa il suo retaggio marziale e naturale per contrastare le minacce oltre i confini della civiltà.\nDado Vita: d10.\nCompetenze: Armature leggere/medie, scudi, armi semplici e marziali.", "hd": 10},
    "Stregone": {"desc": "Un incantatore arcano la cui magia è innata, ereditata o il risultato di una discendenza misteriosa.\nDado Vita: d6.\nCompetenze: Pugnali, dardi, fionde, bastoni ferrati, balestre leggere.", "hd": 6},
    "Warlock": {"desc": "Un incantatore arcano vincolato da un patto con un'entità ultraterrena, come un folletto o un demone.\nDado Vita: d8.\nCompetenze: Armature leggere, armi semplici.", "hd": 8}
}

ALIGNMENTS = {
    "LB (Legale Buono)": "Un personaggio Legale Buono si comporta come la società si aspetta, in modo giusto e difendendo i deboli (es. i Paladini).",
    "NB (Neutrale Buono)": "Fanno del loro meglio per aiutare gli altri assecondando le loro necessità. Re e governanti sono importanti, ma l'aiuto diretto è primario.",
    "CB (Caotico Buono)": "Agiscono secondo coscienza senza preoccuparsi delle regole, aiutando chi ne ha bisogno seguendo la propria morale.",
    "LN (Legale Neutrale)": "Seguono la legge, le tradizioni o un codice personale senza farsi guidare da compassione o malvagità. L'ordine è assoluto.",
    "N (Neutrale Puro)": "Preferiscono tenersi a distanza dai problemi morali, evitando di schierarsi e agendo in modo naturale.",
    "CN (Caotico Neutrale)": "Seguono i loro capricci, valutando la propria libertà personale al di sopra di tutto. Sfuggono alle imposizioni.",
    "LM (Legale Malvagio)": "Sfruttano sistematicamente il sistema, le regole o una gerarchia per ottenere ciò che vogliono senza pietà.",
    "NM (Neutrale Malvagio)": "Fanno tutto ciò che serve per ottenere i loro scopi, senza alcun rimorso. Pensano solo ed esclusivamente a sé stessi.",
    "CM (Caotico Malvagio)": "Agiscono mossi da brama, odio e sete di distruzione. Brutali e imprevedibili."
}

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]
ATTRIBUTES = ["FOR", "DES", "COS", "INT", "SAG", "CAR"]

class CharacterCreationWizard(tk.Toplevel):
    def __init__(self, master, manager, on_complete_callback):
        super().__init__(master)
        self.title("Creazione Guidata Personaggio (D&D 5e)")
        self.minsize(550, 550)
        apply_modern_window_style(self)
        self.transient(master)
        self.grab_set()
        
        self.manager = manager
        self.on_complete_callback = on_complete_callback
        self.default_font = ("Georgia", 11)
        
        # Dati in costruzione
        self.char_data = {
            "race": "Umano",
            "char_class": "Guerriero",
            "attributes": {"FOR": 15, "DES": 14, "COS": 13, "INT": 12, "SAG": 10, "CAR": 8},
            "name": "",
            "campaign": "",
            "background": "",
            "alignment": "NB (Neutrale Buono)"
        }
        
        self.current_step = 0
        self.steps = [
            self.build_step_race,
            self.build_step_class,
            self.build_step_attributes,
            self.build_step_details
        ]
        
        self.container = ttk.Frame(self, padding=20)
        self.container.pack(fill=tk.BOTH, expand=True)
        
        self.btn_frame = ttk.Frame(self, style="Surface.TFrame", padding=10)
        self.btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.prev_btn = ttk.Button(self.btn_frame, text="< Indietro", command=self.prev_step)
        self.prev_btn.pack(side=tk.LEFT)
        
        self.next_btn = ttk.Button(self.btn_frame, text="Avanti >", command=self.next_step, style="Primary.TButton")
        self.next_btn.pack(side=tk.RIGHT)
        
        self.show_step()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_step(self):
        self.clear_container()
        self.steps[self.current_step]()
        
        if self.current_step == 0:
            self.prev_btn.config(state=tk.DISABLED)
        else:
            self.prev_btn.config(state=tk.NORMAL)
            
        if self.current_step == len(self.steps) - 1:
            self.next_btn.config(text="Fine e Crea")
        else:
            self.next_btn.config(text="Avanti >")

    def prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step()

    def next_step(self):
        if self.current_step == 2:
            vals = [var.get() for var in self.attr_vars.values()]
            if len(set(vals)) != len(STANDARD_ARRAY) or sorted(vals, reverse=True) != STANDARD_ARRAY:
                messagebox.showerror("Errore", "Devi assegnare ogni valore della Array Standard (15,14,13,12,10,8) esattamente una volta.")
                return
            for k in ATTRIBUTES:
                self.char_data["attributes"][k] = self.attr_vars[k].get()
                
        if self.current_step == 3:
            name = self.name_var.get().strip()
            if not name:
                messagebox.showerror("Errore", "Il nome del personaggio è obbligatorio.")
                return
            self.char_data["name"] = name
            self.char_data["campaign"] = self.camp_var.get().strip()
            self.char_data["background"] = self.bg_var.get().strip()
            self.char_data["alignment"] = self.align_var.get().split(" ")[0].strip()
            
            self.finish_creation()
            return
            
        self.current_step += 1
        self.show_step()

    def build_step_race(self):
        ttk.Label(self.container, text="Passo 1: Scegli la Razza", style="Title.TLabel").pack(pady=(0, 10))
        
        self.race_var = tk.StringVar(value=self.char_data["race"])
        
        desc_label = ttk.Label(self.container, text="", wraplength=450, justify=tk.LEFT)
        
        def update_desc(*args):
            r = self.race_var.get()
            self.char_data["race"] = r
            desc_label.config(text=RACES[r]["desc"])
            
        self.race_var.trace_add("write", update_desc)
        
        cb = ttk.Combobox(self.container, textvariable=self.race_var, values=list(RACES.keys()), state="readonly", font=self.default_font)
        cb.pack(pady=10)
            
        desc_label.pack(pady=15, fill=tk.X)
        update_desc()

    def build_step_class(self):
        ttk.Label(self.container, text="Passo 2: Scegli la Classe", style="Title.TLabel").pack(pady=(0, 10))
        
        self.class_var = tk.StringVar(value=self.char_data["char_class"])
        
        desc_label = ttk.Label(self.container, text="", wraplength=450, justify=tk.LEFT)
        
        def update_desc(*args):
            c = self.class_var.get()
            self.char_data["char_class"] = c
            desc_label.config(text=CLASSES[c]["desc"])
            
        self.class_var.trace_add("write", update_desc)
        
        cb = ttk.Combobox(self.container, textvariable=self.class_var, values=list(CLASSES.keys()), state="readonly", font=self.default_font)
        cb.pack(pady=10)
            
        desc_label.pack(pady=15, fill=tk.X)
        update_desc()

    def build_step_attributes(self):
        ttk.Label(self.container, text="Passo 3: Caratteristiche (Standard Array)", style="Title.TLabel").pack(pady=(0, 10))
        ttk.Label(self.container, text="Assegna i valori: 15, 14, 13, 12, 10, 8\nI valori si scambieranno automaticamente per non avere duplicati.").pack(pady=(0, 15))
        
        self.attr_vars = {}
        self.old_attr_values = {}
        
        frame = ttk.Frame(self.container)
        frame.pack()
        
        for i, attr in enumerate(ATTRIBUTES):
            val = STANDARD_ARRAY[i]
            var = tk.IntVar(value=val)
            self.attr_vars[attr] = var
            self.old_attr_values[attr] = val
            
        self._is_swapping = False
        
        def on_var_change(changed_attr, *args):
            if self._is_swapping: return
            new_val = self.attr_vars[changed_attr].get()
            old_val = self.old_attr_values.get(changed_attr)
            
            if new_val == old_val:
                return
                
            self._is_swapping = True
            for other_attr in ATTRIBUTES:
                if other_attr != changed_attr and self.attr_vars[other_attr].get() == new_val:
                    self.attr_vars[other_attr].set(old_val)
                    self.old_attr_values[other_attr] = old_val
                    break
                    
            self.old_attr_values[changed_attr] = new_val
            self._is_swapping = False

        for i, attr in enumerate(ATTRIBUTES):
            ttk.Label(frame, text=attr).grid(row=i, column=0, sticky="e", padx=5, pady=2)
            
            var = self.attr_vars[attr]
            var.trace_add("write", lambda name, index, mode, a=attr: on_var_change(a))
            
            cb = ttk.Combobox(frame, textvariable=var, values=STANDARD_ARRAY, state="readonly", width=5)
            cb.grid(row=i, column=1, padx=5, pady=2)

    def build_step_details(self):
        ttk.Label(self.container, text="Passo 4: Dettagli Finali", style="Title.TLabel").pack(pady=(0, 10))
        
        frame = ttk.Frame(self.container)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Nome:").grid(row=0, column=0, sticky="e", pady=5)
        self.name_var = tk.StringVar(value=self.char_data["name"])
        ttk.Entry(frame, textvariable=self.name_var).grid(row=0, column=1, pady=5, padx=5, sticky="ew")
        
        ttk.Label(frame, text="Campagna:").grid(row=1, column=0, sticky="e", pady=5)
        self.camp_var = tk.StringVar(value=self.char_data["campaign"])
        ttk.Entry(frame, textvariable=self.camp_var).grid(row=1, column=1, pady=5, padx=5, sticky="ew")

        ttk.Label(frame, text="Background:").grid(row=2, column=0, sticky="e", pady=5)
        self.bg_var = tk.StringVar(value=self.char_data["background"])
        ttk.Entry(frame, textvariable=self.bg_var).grid(row=2, column=1, pady=5, padx=5, sticky="ew")

        ttk.Label(frame, text="Allineamento:").grid(row=3, column=0, sticky="e", pady=5)
        
        align_keys = list(ALIGNMENTS.keys())
        # Cerchiamo di pre-selezionare quello corretto
        initial_align = align_keys[1]
        for k in align_keys:
            if k.startswith(self.char_data["alignment"]):
                initial_align = k
                break
                
        self.align_var = tk.StringVar(value=initial_align)
        align_cb = ttk.Combobox(frame, textvariable=self.align_var, values=align_keys, state="readonly", width=20)
        align_cb.grid(row=3, column=1, pady=5, padx=5, sticky="w")
        
        align_desc_label = ttk.Label(frame, text="", style="Muted.TLabel", wraplength=450, justify=tk.LEFT)
        align_desc_label.grid(row=4, column=0, columnspan=2, pady=10)
        
        def update_align_desc(*args):
            a = self.align_var.get()
            align_desc_label.config(text=ALIGNMENTS.get(a, ""))
            
        self.align_var.trace_add("write", update_align_desc)
        update_align_desc()
        
        frame.columnconfigure(1, weight=1)

    def finish_creation(self):
        c = Character(name=self.char_data["name"], campaign=self.char_data["campaign"])
        c.race = self.char_data["race"]
        c.char_class = self.char_data["char_class"]
        c.background = self.char_data["background"]
        c.alignment = self.char_data["alignment"]
        c.level = 1
        
        # Calcolo attributi = array + bonus razza
        race_info = RACES[c.race]
        for attr in ATTRIBUTES:
            base = self.char_data["attributes"][attr]
            bonus = race_info["bonuses"].get(attr, 0)
            c.attributes[attr] = base + bonus
            
        def get_mod(val):
            return (val - 10) // 2

        con_mod = get_mod(c.attributes["COS"])
        dex_mod = get_mod(c.attributes["DES"])
        
        # Calcolo HP
        class_info = CLASSES[c.char_class]
        c.hp_max = class_info["hd"] + con_mod
        c.hp_current = c.hp_max
        
        # Calcolo AC base (10 + Dex) - l'armatura potrà essere aggiunta dopo
        c.ac = 10 + dex_mod
        
        # Iniziativa = Dex mod
        c.initiative = dex_mod
        
        # Velocità
        c.speed = race_info["speed"]
        
        # Equipaggiamento iniziale di classe (armi, armature, scudi) e incantesimi
        from common.starter_equipment import apply_class_and_race_starter_kit
        apply_class_and_race_starter_kit(c)
        c.features = f"Tratti razziali:\n{race_info['desc']}\n\nTratti classe:\n{class_info['desc']}"
        
        # Async fetch for Level 1 features
        def _fetch_level_1():
            try:
                import requests
                from .progression_ui import CLASS_MAP
                class_en = CLASS_MAP.get(c.char_class.lower())
                if class_en:
                    resp = requests.get(f"https://www.dnd5eapi.co/api/classes/{class_en}/levels/1", timeout=3)
                    if resp.status_code == 200:
                        data = resp.json()
                        feats = [f["name"] for f in data.get("features", [])]
                        if feats:
                            c.features += "\n\n--- Privilegi di Livello 1 (API) ---\n" + "\n".join(f"- {ft}" for ft in feats)
                        sc = data.get("spellcasting")
                        if sc:
                            for i in range(1, 10):
                                key = f"spell_slots_level_{i}"
                                if key in sc:
                                    c.spell_slots[str(i)] = [0, sc[key]]
            except Exception as e:
                print("Error fetching API level 1 data:", e)
            
            self.master.after(0, self._on_creation_done, c)
            
        import threading
        threading.Thread(target=_fetch_level_1, daemon=True).start()

    def _on_creation_done(self, c):
        self.manager.add_character(c)
        messagebox.showinfo("Successo", f"Personaggio '{c.name}' creato con successo!")
        if self.on_complete_callback:
            self.on_complete_callback(c)
        self.destroy()
