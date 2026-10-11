import tkinter as tk
import threading
import urllib.request
import urllib.parse
import json
from common.messagebox import messagebox
from tkinter import ttk, simpledialog
from common.theme import BG_COLOR, TEXT_COLOR, SURFACE_COLOR, apply_modern_window_style

class CharacterSheetUI(tk.Toplevel):
    def __init__(self, master, character, manager, on_save_callback=None, roll_callback=None, trade_callback=None, players_list_callback=None, attack_callback=None, long_rest_callback=None, custom_spell_request_callback=None, is_connected=False):
        super().__init__(master)
        self.title(f"Scheda PG - {character.name}")
        self.minsize(600, 700)
        apply_modern_window_style(self)
        self.character = character
        self.manager = manager
        self.on_save_callback = on_save_callback
        self.roll_callback = roll_callback
        self.long_rest_callback = long_rest_callback
        self.trade_callback = trade_callback
        self.players_list_callback = players_list_callback
        self.attack_callback = attack_callback
        self.custom_spell_request_callback = custom_spell_request_callback
        self.is_connected = is_connected
        self.default_font = ("Georgia", 10)
        
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Intestazione
        header_frame = ttk.Frame(main_frame, padding=5)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header_frame, text="Nome:").grid(row=0, column=0, sticky="e")
        self.name_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.name_var).grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(header_frame, text="Campagna:").grid(row=0, column=2, sticky="e")
        self.campaign_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.campaign_var).grid(row=0, column=3, padx=5, pady=2, sticky="ew")

        ttk.Label(header_frame, text="Classe:").grid(row=1, column=0, sticky="e")
        self.class_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.class_var).grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(header_frame, text="Livello:").grid(row=1, column=2, sticky="e")
        self.level_var = tk.IntVar()
        ttk.Entry(header_frame, textvariable=self.level_var, width=5, state="readonly").grid(row=1, column=3, padx=5, pady=2, sticky="w")
        
        ttk.Label(header_frame, text="EXP:").grid(row=1, column=4, sticky="e")
        self.exp_label = ttk.Label(header_frame, text="0 / 300")
        self.exp_label.grid(row=1, column=5, padx=5, pady=2, sticky="w")
        self.exp_progress = ttk.Progressbar(header_frame, length=100, mode='determinate')
        self.exp_progress.grid(row=1, column=6, padx=5, pady=2, sticky="w")
        
        self.levelup_btn = ttk.Button(header_frame, text="🌟 Sali di Livello!", command=self.level_up)
        
        ttk.Label(header_frame, text="Razza:").grid(row=2, column=0, sticky="e")
        self.race_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.race_var).grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        # Corpo centrale
        body_frame = ttk.Frame(main_frame)
        body_frame.pack(fill=tk.BOTH, expand=True)

        # Statistiche (Sinistra)
        stats_frame = ttk.LabelFrame(body_frame, text="Attributi")
        stats_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.attr_vars = {}
        for i, attr in enumerate(["FOR", "DES", "COS", "INT", "SAG", "CAR"]):
            ttk.Label(stats_frame, text=attr).grid(row=i, column=0, pady=5)
            var = tk.IntVar()
            self.attr_vars[attr] = var
            ttk.Entry(stats_frame, textvariable=var, width=5, justify="center").grid(row=i, column=1, pady=5, padx=5)
            ttk.Button(stats_frame, text="🎲", command=lambda a=attr, v=var: self.roll_stat(a, v.get())).grid(row=i, column=2, padx=2)

        # Abilità
        skills_frame = ttk.LabelFrame(body_frame, text="Abilità")
        skills_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        self.skill_vars = {}
        self.skill_map = {
            "Acrobazia": "DES", "Addestrare Animali": "SAG", "Arcano": "INT", "Atletica": "FOR",
            "Furtività": "DES", "Indagare": "INT", "Inganno": "CAR", "Intimidire": "CAR",
            "Intrattenere": "CAR", "Intuizione": "SAG", "Medicina": "SAG", "Natura": "INT",
            "Percezione": "SAG", "Persuasione": "CAR", "Prestidigitazione": "DES",
            "Religione": "INT", "Sopravvivenza": "SAG", "Storia": "INT"
        }
        
        skills_canvas = tk.Canvas(skills_frame, width=220)
        skills_scrollbar = ttk.Scrollbar(skills_frame, orient="vertical", command=skills_canvas.yview)
        skills_inner_frame = ttk.Frame(skills_canvas)
        
        skills_inner_frame.bind(
            "<Configure>",
            lambda e: skills_canvas.configure(
                scrollregion=skills_canvas.bbox("all")
            )
        )
        
        skills_canvas.create_window((0, 0), window=skills_inner_frame, anchor="nw")
        skills_canvas.configure(yscrollcommand=skills_scrollbar.set)
        
        skills_canvas.pack(side="left", fill="both", expand=True)
        skills_scrollbar.pack(side="right", fill="y")
        
        for i, (skill, stat) in enumerate(self.skill_map.items()):
            ttk.Label(skills_inner_frame, text=f"{skill} ({stat})").grid(row=i, column=0, sticky="w", pady=2)
            var = tk.IntVar()
            self.skill_vars[skill] = var
            combo = ttk.Combobox(skills_inner_frame, textvariable=var, values=[0, 1, 2], width=2, state="readonly")
            combo.grid(row=i, column=1, padx=5)
            ttk.Button(skills_inner_frame, text="🎲", width=3, command=lambda s=skill, st=stat: self.roll_skill(s, st)).grid(row=i, column=2, padx=2)


        # Combattimento (Centro)
        combat_frame = ttk.LabelFrame(body_frame, text="Combattimento")
        combat_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        ttk.Label(combat_frame, text="HP Attuali:").grid(row=0, column=0, sticky="e", pady=2)
        self.hp_cur_var = tk.IntVar()
        ttk.Entry(combat_frame, textvariable=self.hp_cur_var).grid(row=0, column=1, pady=2)

        ttk.Label(combat_frame, text="HP Massimi:").grid(row=1, column=0, sticky="e", pady=2)
        self.hp_max_var = tk.IntVar()
        ttk.Entry(combat_frame, textvariable=self.hp_max_var).grid(row=1, column=1, pady=2)

        ttk.Label(combat_frame, text="CA (Armor Class):").grid(row=2, column=0, sticky="e", pady=2)
        self.ac_var = tk.IntVar()
        ttk.Entry(combat_frame, textvariable=self.ac_var).grid(row=2, column=1, pady=2)

        ttk.Label(combat_frame, text="Iniziativa:").grid(row=3, column=0, sticky="e", pady=2)
        self.init_var = tk.IntVar()
        ttk.Entry(combat_frame, textvariable=self.init_var).grid(row=3, column=1, pady=2)
        ttk.Button(combat_frame, text="🎲", command=self.roll_initiative).grid(row=3, column=2, padx=2)

        self.adv_dis_var = tk.StringVar(value="Normale")
        self.adv_dis_combo = ttk.Combobox(combat_frame, textvariable=self.adv_dis_var, values=["Normale", "Vantaggio", "Svantaggio"], state="readonly", width=12)
        self.adv_dis_combo.grid(row=3, column=3, padx=5)

        ttk.Label(combat_frame, text="Velocità:").grid(row=4, column=0, sticky="e", pady=2)
        self.speed_var = tk.IntVar()
        ttk.Entry(combat_frame, textvariable=self.speed_var).grid(row=4, column=1, pady=2)
        
        btn_frame_rest = ttk.Frame(combat_frame)
        btn_frame_rest.grid(row=5, column=0, columnspan=4, pady=10, sticky="ew")
        ttk.Button(btn_frame_rest, text="Riposo Breve", command=self.short_rest).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(btn_frame_rest, text="Riposo Lungo", command=self.long_rest).pack(side=tk.LEFT, expand=True, padx=2)

        # Death Saves
        self.death_saves_frame = ttk.LabelFrame(combat_frame, text="Tiri contro la Morte")
        self.death_saves_frame.grid(row=6, column=0, columnspan=4, pady=5, sticky="ew")
        
        self.ds_succ_vars = [tk.BooleanVar() for _ in range(3)]
        self.ds_fail_vars = [tk.BooleanVar() for _ in range(3)]
        
        ds_subframe = ttk.Frame(self.death_saves_frame)
        ds_subframe.pack(pady=5)
        
        ttk.Label(ds_subframe, text="Successi:").grid(row=0, column=0, sticky="e")
        for i in range(3):
            cb = ttk.Checkbutton(ds_subframe, variable=self.ds_succ_vars[i], state=tk.DISABLED)
            cb.grid(row=0, column=i+1)
            
        ttk.Label(ds_subframe, text=" Fallimenti:").grid(row=0, column=4, sticky="e")
        for i in range(3):
            cb = ttk.Checkbutton(ds_subframe, variable=self.ds_fail_vars[i], state=tk.DISABLED)
            cb.grid(row=0, column=i+5)
            
        self.ds_roll_btn = ttk.Button(self.death_saves_frame, text="Tira TS Morte", command=self.roll_death_save)
        self.ds_roll_btn.pack(pady=5)
        self.hp_cur_var.trace_add("write", lambda *args: self.update_death_saves_ui())
        
        self.death_label = ttk.Label(combat_frame, text="SEI MORTO", foreground="red", font=("Georgia", 16, "bold"))
        self.death_label.grid(row=7, column=0, columnspan=4, pady=10)
        self.death_label.grid_remove()

        # Tab Notebook (Destra per note/inventario/incantesimi)
        tabs_frame = ttk.Frame(body_frame)
        tabs_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(tabs_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.text_widgets = {}
        for tab_name, attr in [("Inventario", "inventory_grid"), ("Tratti e Privilegi", "features"), ("Grimorio", "spellbook"), ("Note", "notes")]:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=tab_name)
            
            if attr == "inventory_grid":
                self.create_inventory_tab(frame)
            elif attr == "spellbook":
                self.build_spells_tab(frame)
            else:
                txt = tk.Text(frame, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=self.default_font, wrap=tk.WORD)
                txt.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
                self.text_widgets[attr] = txt

        if "FOR" in self.attr_vars:
            self.attr_vars["FOR"].trace_add("write", lambda *args: self.calculate_total_weight())

        # Pulsanti (in fondo alla scheda)
        btn_frame = ttk.Frame(main_frame, padding=(0, 10))
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(btn_frame, text="Salva", command=self.save_character, style="Primary.TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def create_inventory_tab(self, parent_frame):
        currency_frame = ttk.LabelFrame(parent_frame, text="Valuta")
        currency_frame.pack(fill=tk.X, padx=5, pady=5)
        self.currency_vars = {}
        for coin in ["MR", "MA", "ME", "MO", "MP"]:
            c_frame = ttk.Frame(currency_frame)
            c_frame.pack(side=tk.LEFT, expand=True, padx=2)
            ttk.Label(c_frame, text=coin).pack(side=tk.TOP)
            var = tk.IntVar(value=0)
            self.currency_vars[coin] = var
            ttk.Entry(c_frame, textvariable=var, width=5, justify="center").pack(side=tk.TOP)
            
        list_frame = ttk.Frame(parent_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        ttk.Label(scrollable_frame, text="Oggetto", font=("Georgia", 9, "bold")).grid(row=0, column=0, padx=5, pady=2)
        ttk.Label(scrollable_frame, text="Peso (lbs)", font=("Georgia", 9, "bold")).grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(scrollable_frame, text="Sintonia", font=("Georgia", 9, "bold")).grid(row=0, column=2, padx=5, pady=2)
        
        self.inventory_buttons = []
        self.weight_vars = []
        self.attuned_vars = []
        
        for i in range(25):
            btn = ttk.Button(scrollable_frame, text="Vuoto", width=20, command=lambda idx=i: self.on_inventory_click(idx))
            btn.grid(row=i+1, column=0, padx=5, pady=2)
            self.inventory_buttons.append(btn)
            
            w_var = tk.DoubleVar(value=0.0)
            w_var.trace_add("write", lambda *args: self.calculate_total_weight())
            w_entry = ttk.Entry(scrollable_frame, textvariable=w_var, width=8)
            w_entry.grid(row=i+1, column=1, padx=5, pady=2)
            self.weight_vars.append(w_var)
            
            a_var = tk.BooleanVar(value=False)
            a_var.trace_add("write", lambda *args, idx=i: self.check_attunement(idx))
            cb = ttk.Checkbutton(scrollable_frame, variable=a_var)
            cb.grid(row=i+1, column=2, padx=5, pady=2)
            self.attuned_vars.append(a_var)
            
        bottom_frame = ttk.Frame(parent_frame)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        self.weight_label = ttk.Label(bottom_frame, text="Peso Totale: 0 / 150 lbs", font=("Georgia", 10, "bold"))
        self.weight_label.pack(pady=5)
        
        compendium_btn = ttk.Button(bottom_frame, text="Cerca nel Compendio", command=self.open_inventory_compendium)
        compendium_btn.pack(pady=5)

    def calculate_total_weight(self):
        if not hasattr(self, 'weight_vars') or not hasattr(self, 'weight_label'):
            return
        total = 0.0
        for i in range(25):
            item = self.character.inventory_grid[i]
            if item:
                try:
                    w = float(self.weight_vars[i].get())
                    qty = item.get("qty", 1)
                    total += w * qty
                except (tk.TclError, ValueError):
                    pass
                    
        try:
            strength = int(self.attr_vars["FOR"].get())
        except (tk.TclError, ValueError, KeyError):
            strength = 10
            
        max_weight = strength * 15
        
        if total > max_weight:
            self.weight_label.config(text=f"Peso Totale: {total:.1f} / {max_weight} lbs (Ingombrato!)", foreground="red")
        else:
            self.weight_label.config(text=f"Peso Totale: {total:.1f} / {max_weight} lbs", foreground=TEXT_COLOR)

    def check_attunement(self, changed_idx):
        if not hasattr(self, 'attuned_vars'): return
        attuned_count = sum(1 for var in self.attuned_vars if var.get())
        if attuned_count > 3:
            messagebox.showwarning("Sintonia", "Non puoi sintonizzarti con più di 3 oggetti contemporaneamente!")
            self.attuned_vars[changed_idx].set(False)

    def build_spells_tab(self, parent_frame):
        slots_frame = ttk.LabelFrame(parent_frame, text="Slot Incantesimo (Max / Correnti)")
        slots_frame.pack(fill=tk.X, padx=5, pady=5)
        self.slot_vars = {}
        for i in range(1, 10):
            lvl_frame = ttk.Frame(slots_frame)
            lvl_frame.pack(side=tk.LEFT, padx=3, expand=True)
            ttk.Label(lvl_frame, text=f"Lvl {i}").pack()
            sub_frame = ttk.Frame(lvl_frame)
            sub_frame.pack()
            massimi = tk.IntVar(value=0)
            usati = tk.IntVar(value=0)
            self.slot_vars[str(i)] = {"max": massimi, "current": usati}
            ttk.Entry(sub_frame, textvariable=massimi, width=2, justify="center").pack(side=tk.LEFT)
            ttk.Label(sub_frame, text="/").pack(side=tk.LEFT)
            ttk.Entry(sub_frame, textvariable=usati, width=2, justify="center").pack(side=tk.LEFT)
            
        list_frame = ttk.Frame(parent_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.spell_tree = ttk.Treeview(list_frame, columns=("Lvl", "Nome", "Tempo", "Raggio"), show="headings", height=8)
        self.spell_tree.heading("Lvl", text="Lvl", command=lambda: self.sort_spells("Lvl"))
        self.spell_tree.heading("Nome", text="Nome")
        self.spell_tree.heading("Tempo", text="Lancio")
        self.spell_tree.heading("Raggio", text="Raggio")
        self.spell_tree.column("Lvl", width=30, anchor="center")
        self.spell_tree.column("Nome", width=150)
        self.spell_tree.column("Tempo", width=80)
        self.spell_tree.column("Raggio", width=80)
        self.spell_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.spell_tree.yview)
        self.spell_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        btn_frame = ttk.Frame(parent_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="Nuovo", command=self.add_spell).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cerca Incantesimo (SRD)", command=self.search_spell_srd).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Rimuovi", command=self.remove_spell).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Dettagli / Lancia", command=self.cast_spell).pack(side=tk.RIGHT, padx=5)

    def sort_spells(self, col):
        if not hasattr(self.character, "spellbook"): return
        self.character.spellbook.sort(key=lambda s: int(s.get("level", 0)))
        self.refresh_spell_list()

    def refresh_spell_list(self):
        if not hasattr(self, 'spell_tree'): return
        for item in self.spell_tree.get_children(): self.spell_tree.delete(item)
        for i, s in enumerate(getattr(self.character, "spellbook", [])):
            lvl = s.get("level", 0)
            lvl_str = "Trucchetto" if lvl == 0 else str(lvl)
            self.spell_tree.insert("", tk.END, iid=str(i), values=(lvl_str, s.get("name", ""), s.get("time", ""), s.get("range", "")))

    def add_spell(self):
        SpellEditorDialog(self)

    def remove_spell(self):
        sel = self.spell_tree.selection()
        if not sel: return
        idx = int(sel[0])
        if messagebox.askyesno("Conferma", "Vuoi rimuovere questo incantesimo?"):
            self.character.spellbook.pop(idx)
            self.refresh_spell_list()
            self.manager.save_characters()

    def cast_spell(self):
        sel = self.spell_tree.selection()
        if not sel: return
        idx = int(sel[0])
        spell = self.character.spellbook[idx]
        
        msg = (f"INCANTESIMO: {spell.get('name', '')}\n"
               f"Livello: {spell.get('level', 0)}\n"
               f"Tempo: {spell.get('time', '')}\n"
               f"Raggio: {spell.get('range', '')}\n\n"
               f"Descrizione: {spell.get('desc', '')}")
        
        win = tk.Toplevel(self)
        win.transient(self)
        win.grab_set()
        apply_modern_window_style(win)
        win.title("Dettagli Incantesimo")
        win.minsize(400, 400)
        
        txt = tk.Text(win, wrap=tk.WORD, bg="#1e1e1e", fg="white")
        txt.insert(tk.END, msg)
        txt.config(state=tk.DISABLED)
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, pady=10)
        
        def do_cast():
            lvl = str(spell.get('level', 0))
            if spell.get('level', 0) > 0 and lvl in self.slot_vars:
                massimi_var = self.slot_vars[lvl]["max"]
                usati_var = self.slot_vars[lvl]["current"]
                if usati_var.get() > 0:
                    usati_var.set(usati_var.get() - 1)
                    if not hasattr(self.character, "spell_slots"):
                        self.character.spell_slots = {str(i): {"max": 0, "current": 0} for i in range(1, 10)}
                    self.character.spell_slots[lvl]["current"] = usati_var.get()
                    self.character.spell_slots[lvl]["max"] = massimi_var.get()
                    self.manager.update_character(self.character)
                else:
                    if not messagebox.askyesno("Slot Esauriti", f"Non hai piu' slot di livello {lvl}. Vuoi lanciarlo lo stesso?", parent=win):
                        return
            
            if self.roll_callback:
                chat_msg = f"{self.character.name} lancia {spell.get('name', '')}!"
                self.roll_callback("0d0", chat_msg)
            win.destroy()
            
        def do_attack():
            if not getattr(self, 'attack_callback', None): return
            hit_bonus_str = tk.simpledialog.askstring("Bonus Colpire", "Inserisci bonus per colpire (es. 5):", parent=win)
            if not hit_bonus_str: return
            try: hit_bonus = int(hit_bonus_str)
            except: hit_bonus = 0
            
            dmg_str = tk.simpledialog.askstring("Danno", "Inserisci formula danno (es. 1d8+3):", parent=win)
            if not dmg_str: return
            
            self.attack_callback(spell.get('name', ''), hit_bonus, dmg_str)
            win.destroy()

        ttk.Button(btn_frame, text="Lancia in Chat", command=do_cast).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Attacca Bersaglio", command=do_attack, style="Danger.TButton").pack(side=tk.LEFT, padx=10)

    def search_spell_srd(self):
        query = simpledialog.askstring("Cerca SRD", "Nome incantesimo (in inglese, es. fireball):")
        if not query: return
        query_safe = urllib.parse.quote(query.lower().strip())
        
        def fetch_spell():
            try:
                url = f"https://www.dnd5eapi.co/api/spells/?name={query_safe}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode())
                
                if data.get("count", 0) > 0:
                    spell_url = data["results"][0]["url"]
                    if not spell_url.startswith("http"):
                        spell_url = "https://www.dnd5eapi.co" + spell_url
                    
                    req2 = urllib.request.Request(spell_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req2) as response2:
                        spell_data = json.loads(response2.read().decode())
                        
                    name = spell_data.get("name", "")
                    level = spell_data.get("level", 0)
                    time = spell_data.get("casting_time", "")
                    rng = spell_data.get("range", "")
                    desc_list = spell_data.get("desc", [])
                    desc = "\n".join(desc_list) if isinstance(desc_list, list) else str(desc_list)
                    
                    self.after(0, lambda: self._add_fetched_spell(name, level, time, rng, desc))
                else:
                    self.after(0, lambda: messagebox.showinfo("Nessun risultato", "Incantesimo non trovato nel SRD."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Errore di rete", str(e)))
                
        threading.Thread(target=fetch_spell, daemon=True).start()

    def _add_fetched_spell(self, name, level, time, rng, desc):
        if not hasattr(self.character, "spellbook"): self.character.spellbook = []
        self.character.spellbook.append({"name": name, "level": level, "time": time, "range": rng, "desc": desc})
        self.refresh_spell_list()
        self.manager.save_characters()
        messagebox.showinfo("Successo", f"{name} aggiunto al Grimorio!")

    def recover_spell_slots(self):
        if messagebox.askyesno("Riposo Lungo", "Recuperare tutti gli slot incantesimo e la salute?"):
            for lvl, vars_ in self.slot_vars.items():
                vars_["current"].set(vars_["max"].get())
            self.hp_cur_var.set(self.hp_max_var.get())

    def load_data(self):
        self.name_var.set(self.character.name)
        self.campaign_var.set(self.character.campaign)
        self.class_var.set(self.character.char_class)
        self.level_var.set(self.character.level)
        self.race_var.set(self.character.race)
        
        for k, v in self.character.attributes.items():
            self.attr_vars[k].set(v)
            
        if hasattr(self.character, "skills"):
            for k, v in self.character.skills.items():
                if k in self.skill_vars:
                    self.skill_vars[k].set(v)
            
        self.hp_cur_var.set(self.character.hp_current)
        self.hp_max_var.set(self.character.hp_max)
        self.ac_var.set(self.character.ac)
        self.init_var.set(self.character.initiative)
        self.speed_var.set(self.character.speed)
        if "Morto" in getattr(self.character, "conditions", []):
            self.death_label.grid()
        else:
            self.death_label.grid_remove()

        for attr, txt in self.text_widgets.items():
            txt.config(state=tk.NORMAL)
            txt.delete("1.0", tk.END)
            txt.insert("1.0", getattr(self.character, attr, ""))
            if attr == "features":
                txt.config(state=tk.DISABLED)
                
        if hasattr(self.character, "currency"):
            for coin, var in self.currency_vars.items():
                var.set(self.character.currency.get(coin, 0))
                
        self.update_death_saves_ui()
                
        # Carica slot incantesimi
        if hasattr(self.character, "spell_slots"):
            for lvl, vals in self.character.spell_slots.items():
                if lvl in self.slot_vars:
                    if isinstance(vals, dict):
                        self.slot_vars[lvl]["current"].set(vals.get("current", 0))
                        self.slot_vars[lvl]["max"].set(vals.get("max", 0))
                    elif isinstance(vals, list):
                        self.slot_vars[lvl]["current"].set(vals[0])
                        self.slot_vars[lvl]["max"].set(vals[1])
                    
        self.refresh_spell_list()
        self.refresh_inventory_grid()
        self.update_exp_ui()

    def update_exp_ui(self):
        exp = getattr(self.character, "exp", 0)
        level = self.character.level
        xp_thresholds = [0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000, 120000, 140000, 165000, 195000, 225000, 265000, 305000, 355000]
        
        if level < 20:
            next_xp = xp_thresholds[level]
            prev_xp = xp_thresholds[level-1] if level > 1 else 0
            self.exp_label.config(text=f"{exp} / {next_xp}")
            self.exp_progress['maximum'] = next_xp - prev_xp
            self.exp_progress['value'] = max(0, exp - prev_xp)
            if exp >= next_xp:
                self.levelup_btn.grid(row=1, column=7, padx=5, pady=2)
            else:
                self.levelup_btn.grid_forget()
        else:
            self.exp_label.config(text=f"{exp} (Max)")
            self.exp_progress['maximum'] = 1
            self.exp_progress['value'] = 1
            self.levelup_btn.grid_forget()

    def refresh_inventory_grid(self):
        for i, item in enumerate(self.character.inventory_grid):
            btn = self.inventory_buttons[i]
            if item:
                name = item.get("name", "Oggetto")
                qty = item.get("qty", 1)
                short_name = name[:15] + ".." if len(name) > 15 else name
                btn.config(text=f"{short_name} (x{qty})", style="SlotFilled.TButton")
                if hasattr(self, 'weight_vars'):
                    self.weight_vars[i].set(item.get("weight", 0.0))
                if hasattr(self, 'attuned_vars'):
                    self.attuned_vars[i].set(item.get("attuned", False))
            else:
                btn.config(text="Vuoto", style="Slot.TButton")
                if hasattr(self, 'weight_vars'):
                    self.weight_vars[i].set(0.0)
                if hasattr(self, 'attuned_vars'):
                    self.attuned_vars[i].set(False)
        if hasattr(self, 'calculate_total_weight'):
            self.calculate_total_weight()

    def on_inventory_click(self, idx):
        item = self.character.inventory_grid[idx]
        if not item: return
        
        info = f"Nome: {item.get('name')}\nTipo: {item.get('type')}\nQuantità: {item.get('qty')}\n\nDescrizione:\n{item.get('desc')}"
        
        win = tk.Toplevel(self)
        win.transient(self)
        win.grab_set()
        apply_modern_window_style(win)
        win.title("Dettagli Oggetto")
        win.minsize(300, 300)
        apply_modern_window_style(win)
        
        ttk.Label(win, text=info, justify="left", wraplength=280).pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, pady=10)
        
        def discard():
            if messagebox.askyesno("Conferma", "Vuoi scartare questo oggetto? Andrà perso.", parent=win):
                self.character.inventory_grid[idx] = None
                self.refresh_inventory_grid()
                win.destroy()
                
        def trade():
            if not hasattr(self, 'players_list_callback') or not hasattr(self, 'trade_callback'):
                messagebox.showinfo("Errore", "Funzione non disponibile offline.", parent=win)
                return
            players = self.players_list_callback()
            if not players:
                messagebox.showinfo("Nessuno", "Non ci sono altri giocatori connessi.", parent=win)
                return
                
            target = simpledialog.askstring("Dona Oggetto", "A chi vuoi donare l'oggetto?\nScegli tra: " + ", ".join(players), parent=win)
            if target and target in players:
                self.trade_callback(item, target)
                self.character.inventory_grid[idx] = None
                self.refresh_inventory_grid()
                win.destroy()
            elif target:
                messagebox.showerror("Errore", "Giocatore non trovato.", parent=win)

        ttk.Button(btn_frame, text="Dona a...", command=trade).pack(side=tk.LEFT, padx=15)
        ttk.Button(btn_frame, text="Scarta", command=discard).pack(side=tk.RIGHT, padx=15)

    def open_inventory_compendium(self):
        from server.compendium_ui import CompendiumDialog
        CompendiumDialog(self.master, on_import_callback=self.import_from_compendium, is_dm=False)

    def import_from_compendium(self, item_data, category):
        # Update spell list if category is Incantesimi
        if category == "Incantesimi":
            if not hasattr(self.character, "spellbook"):
                self.character.spellbook = []
            
            desc = item_data.get("desc", "")
            if isinstance(desc, list):
                desc = "\n".join(desc)
                
            self.character.spellbook.append({
                "name": item_data.get("name", ""),
                "level": item_data.get("level", 0),
                "time": item_data.get("casting_time", ""),
                "range": item_data.get("range", ""),
                "desc": desc
            })
            self.refresh_spell_list()
            self.manager.update_character(self.character)
            if hasattr(self.manager, 'save_characters'):
                self.manager.save_characters()
            messagebox.showinfo("Importato", f"{item_data.get('name')} importato con successo come Incantesimo!")
            return

        # Find first empty slot in inventory
        empty_idx = -1
        for i, item in enumerate(self.character.inventory_grid):
            if not item:
                empty_idx = i
                break
        if empty_idx == -1:
            messagebox.showerror("Zaino Pieno", "Non c'è spazio nello zaino!")
            return
            
        desc = item_data.get("desc", "")
        if isinstance(desc, list):
            desc = "\n".join(desc)
            
        entry = {
            "name": item_data.get("name"),
            "type": category,
            "qty": 1,
            "desc": desc
        }
            
        self.character.inventory_grid[empty_idx] = entry
        
        self.manager.update_character(self.character)
        if hasattr(self.manager, 'save_characters'):
            self.manager.save_characters()
            
        self.refresh_inventory_grid()
        messagebox.showinfo("Importato", f"{item_data.get('name')} importato con successo!")

    def save_character(self):
        try:
            self.character.name = self.name_var.get()
            self.character.campaign = self.campaign_var.get()
            self.character.char_class = self.class_var.get()
            self.character.level = self.level_var.get()
            self.character.race = self.race_var.get()
            
            for k, var in self.attr_vars.items():
                self.character.attributes[k] = var.get()
                
            if not hasattr(self.character, "skills"):
                self.character.skills = {}
            for k, var in self.skill_vars.items():
                try:
                    self.character.skills[k] = var.get()
                except tk.TclError:
                    self.character.skills[k] = 0
                
            self.character.hp_current = self.hp_cur_var.get()
            self.character.hp_max = self.hp_max_var.get()
            self.character.ac = self.ac_var.get()
            self.character.initiative = self.init_var.get()
            self.character.speed = self.speed_var.get()
            
            for attr, txt in self.text_widgets.items():
                val = txt.get("1.0", tk.END).strip()
                setattr(self.character, attr, val)
                
            if not hasattr(self.character, "currency"):
                self.character.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
            for coin, var in self.currency_vars.items():
                try:
                    self.character.currency[coin] = var.get()
                except tk.TclError:
                    pass
                
            # Salva slot incantesimi
            if not hasattr(self.character, "spell_slots"):
                self.character.spell_slots = {}
            for lvl, vars_ in self.slot_vars.items():
                self.character.spell_slots[lvl] = {"max": vars_["max"].get(), "current": vars_["current"].get()}
                
            # Salva peso e sintonia inventario
            if hasattr(self, 'weight_vars') and hasattr(self, 'attuned_vars'):
                for i in range(25):
                    item = self.character.inventory_grid[i]
                    if item:
                        try:
                            item["weight"] = float(self.weight_vars[i].get())
                        except (tk.TclError, ValueError):
                            item["weight"] = 0.0
                        item["attuned"] = self.attuned_vars[i].get()
                
            self.manager.update_character(self.character)
            
            if self.on_save_callback:
                self.on_save_callback(self.character)
                
            self.destroy()
        except ValueError:
            messagebox.showerror("Errore", "Assicurati di inserire valori numerici validi nei campi numerici.")

    def roll_stat(self, stat_name, stat_val):
        if not self.roll_callback: return
        try:
            val = int(stat_val)
            mod = (val - 10) // 2
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            
            formula = f"1d20{mod_str}"
            adv_state = self.adv_dis_var.get()
            if adv_state == "Vantaggio":
                formula += " adv"
            elif adv_state == "Svantaggio":
                formula += " dis"
                
            self.roll_callback(formula, f"Check {stat_name}")
        except ValueError:
            pass

    def roll_skill(self, skill_name, stat_name):
        if not self.roll_callback: return
        try:
            stat_val = int(self.attr_vars[stat_name].get())
            stat_mod = (stat_val - 10) // 2
            
            prof_level = self.skill_vars[skill_name].get()
            prof_bonus = getattr(self.character, "proficiency_bonus", 2)
            
            total_mod = stat_mod + (prof_bonus * prof_level)
            mod_str = f"+{total_mod}" if total_mod >= 0 else str(total_mod)
            
            formula = f"1d20{mod_str}"
            adv_state = self.adv_dis_var.get()
            if adv_state == "Vantaggio":
                formula += " adv"
            elif adv_state == "Svantaggio":
                formula += " dis"
                
            self.roll_callback(formula, f"Check {skill_name}")
        except ValueError:
            pass

    def roll_initiative(self):
        if not self.roll_callback: return
        try:
            des_val = int(self.attr_vars["DES"].get())
            mod = (des_val - 10) // 2
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            
            formula = f"1d20{mod_str}"
            adv_state = self.adv_dis_var.get()
            if adv_state == "Vantaggio":
                formula += " adv"
            elif adv_state == "Svantaggio":
                formula += " dis"

            self.roll_callback(formula, "Iniziativa")
        except ValueError:
            pass

    def short_rest(self):
        hd_cur = getattr(self.character, "hit_dice_current", 0)
        hd_tot = getattr(self.character, "hit_dice_total", 0)
        hd_type = getattr(self.character, "hit_dice_type", "d8")
        if hd_cur <= 0:
            messagebox.showinfo("Riposo Breve", "Non hai Dadi Vita disponibili.")
            return
            
        spend = simpledialog.askinteger("Riposo Breve", f"Quanti dadi spendere? ({hd_cur}/{hd_tot} {hd_type} disponibili)", minvalue=1, maxvalue=hd_cur)
        if not spend: return
        
        cos_mod = (self.character.attributes.get("COS", 10) - 10) // 2
        import random
        healed = 0
        die_sides = int(hd_type.replace("d", "")) if "d" in hd_type else 8
        for _ in range(spend):
            roll = random.randint(1, die_sides)
            healed += max(1, roll + cos_mod)
            
        self.character.hit_dice_current -= spend
        new_hp = min(self.hp_max_var.get(), self.hp_cur_var.get() + healed)
        self.hp_cur_var.set(new_hp)
        self.manager.update_character(self.character)
        messagebox.showinfo("Riposo Breve", f"Hai speso {spend} dadi vita e recuperato {healed} HP!")

    def long_rest(self):
        if hasattr(self, 'long_rest_callback') and self.long_rest_callback:
            self.long_rest_callback()
        else:
            if messagebox.askyesno("Riposo Lungo", "Effettuare un riposo lungo?"):
                self.character.long_rest()
                self.load_data()
                self.manager.update_character(self.character)
                messagebox.showinfo("Riposo Lungo", "Hai effettuato un riposo lungo! HP, Dadi Vita, Tiri contro la Morte e Slot Incantesimo sono stati recuperati.")

    def roll_death_save(self):
        import random
        roll = random.randint(1, 20)
        if not hasattr(self.character, "death_saves"):
            self.character.death_saves = {"successes": 0, "failures": 0}
            
        succ = self.character.death_saves["successes"]
        fail = self.character.death_saves["failures"]
        
        if roll == 1:
            fail += 2
        elif roll <= 9:
            fail += 1
        elif roll <= 19:
            succ += 1
        elif roll == 20:
            succ += 1
            self.hp_cur_var.set(1)
            succ = 0
            fail = 0
            
        self.character.death_saves["successes"] = min(3, succ)
        self.character.death_saves["failures"] = min(3, fail)
        self.update_death_saves_ui()
        self.manager.update_character(self.character)
        
        msg = f"Tiro: {roll}. "
        if roll == 1: msg += "Fallimento critico! (2 fallimenti)"
        elif roll <= 9: msg += "Fallimento."
        elif roll <= 19: msg += "Successo."
        else: msg += "Successo critico! Recuperi 1 HP."
        messagebox.showinfo("Tiro contro la Morte", msg)

    def update_dynamic_stats(self):
        self.hp_cur_var.set(self.character.hp_current)
        self.hp_max_var.set(self.character.hp_max)
        self.init_var.set(self.character.initiative)
        if "Morto" in getattr(self.character, "conditions", []):
            self.death_label.grid()
        else:
            self.death_label.grid_remove()

    def update_death_saves_ui(self):
        try:
            hp = self.hp_cur_var.get()
        except tk.TclError:
            hp = 1
            
        if hp <= 0:
            self.death_saves_frame.grid()
        else:
            self.death_saves_frame.grid_remove()
            if hasattr(self.character, "death_saves"):
                self.character.death_saves["successes"] = 0
                self.character.death_saves["failures"] = 0
                self.manager.save_characters()
            
        if not hasattr(self.character, "death_saves"):
            self.character.death_saves = {"successes": 0, "failures": 0}
            
        succ = self.character.death_saves["successes"]
        fail = self.character.death_saves["failures"]
        for i in range(3):
            self.ds_succ_vars[i].set(i < succ)
            self.ds_fail_vars[i].set(i < fail)

    def level_up(self):
        from .progression_ui import LevelUpDialog
        LevelUpDialog(self, self.character, self.on_level_up_applied)
        
    def on_level_up_applied(self):
        self.manager.update_character(self.character)
        if hasattr(self.manager, 'save_characters'):
            self.manager.save_characters()
        self.load_data()


class SpellEditorDialog(tk.Toplevel):
    def __init__(self, sheet_ui):
        super().__init__(sheet_ui)
        self.sheet_ui = sheet_ui
        self.title("Crea Incantesimo Custom (Richiede Approvazione DM)")
        self.minsize(500, 520)
        self.transient(sheet_ui)
        self.grab_set()
        
        from common.theme import apply_modern_window_style
        apply_modern_window_style(self)

        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="⚠️ Gli incantesimi custom richiedono l'approvazione del Dungeon Master prima di essere aggiunti alla scheda.", 
                  font=("Helvetica", 10, "italic"), wraplength=460, foreground="#FFA500").pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(main_frame, text="Nome Incantesimo:", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.name_entry = ttk.Entry(main_frame, font=("Helvetica", 11))
        self.name_entry.pack(fill=tk.X, pady=(0, 10))

        grid_frame = ttk.Frame(main_frame)
        grid_frame.pack(fill=tk.X, pady=(0, 10))
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(3, weight=1)

        ttk.Label(grid_frame, text="Livello (0 per trucchetto):", font=("Helvetica", 11)).grid(row=0, column=0, padx=(0, 5), pady=5, sticky=tk.W)
        self.lvl_entry = ttk.Entry(grid_frame, font=("Helvetica", 11), width=5)
        self.lvl_entry.insert(0, "1")
        self.lvl_entry.grid(row=0, column=1, pady=5, sticky=tk.W)

        ttk.Label(grid_frame, text="Tempo di Lancio:", font=("Helvetica", 11)).grid(row=0, column=2, padx=(15, 5), pady=5, sticky=tk.W)
        self.time_entry = ttk.Entry(grid_frame, font=("Helvetica", 11), width=15)
        self.time_entry.insert(0, "1 Azione")
        self.time_entry.grid(row=0, column=3, pady=5, sticky=tk.W)

        ttk.Label(grid_frame, text="Raggio:", font=("Helvetica", 11)).grid(row=1, column=0, padx=(0, 5), pady=5, sticky=tk.W)
        self.rng_entry = ttk.Entry(grid_frame, font=("Helvetica", 11), width=15)
        self.rng_entry.insert(0, "9m")
        self.rng_entry.grid(row=1, column=1, pady=5, sticky=tk.W)

        ttk.Label(main_frame, text="Descrizione / Effetto:", font=("Helvetica", 11, "bold")).pack(anchor=tk.W, pady=(5, 2))
        from tkinter import scrolledtext
        self.desc_text = scrolledtext.ScrolledText(main_frame, font=("Helvetica", 11), wrap=tk.WORD, height=6)
        self.desc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Invia Richiesta al Master", style="Success.TButton", command=self.on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=self.destroy).pack(side=tk.RIGHT)

        self.name_entry.focus_set()

    def on_save(self):
        name = self.name_entry.get().strip()
        if not name:
            from common.messagebox import messagebox
            messagebox.showwarning("Attenzione", "Il nome dell'incantesimo è obbligatorio.", parent=self)
            return
            
        try:
            lvl = int(self.lvl_entry.get() or 0)
        except ValueError:
            from common.messagebox import messagebox
            messagebox.showwarning("Errore", "Il livello deve essere un numero intero.", parent=self)
            return
            
        time = self.time_entry.get().strip()
        rng = self.rng_entry.get().strip()
        desc = self.desc_text.get("1.0", tk.END).strip()

        cb = getattr(self.sheet_ui, 'custom_spell_request_callback', None)
        is_conn = getattr(self.sheet_ui, 'is_connected', False)
        
        if cb and is_conn:
            spell_data = {"name": name, "level": lvl, "time": time, "range": rng, "desc": desc}
            cb(spell_data)
            from common.messagebox import messagebox
            messagebox.showinfo("Richiesta Inviata", f"La richiesta per l'incantesimo '{name}' è stata inviata al Master!\nQuando verrà approvata, comparirà nel tuo Grimorio.")
            self.destroy()
        else:
            from common.messagebox import messagebox
            messagebox.showwarning("Permesso Richiesto", 
                                   "Non puoi creare un incantesimo custom senza prima chiedere il permesso al Master!\n"
                                   "Devi essere connesso al server del Master per richiedere l'approvazione.")

