import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from common.theme import BG_COLOR, TEXT_COLOR, SURFACE_COLOR, apply_modern_window_style

class CharacterSheetUI(tk.Toplevel):
    def __init__(self, master, character, manager, on_save_callback=None, roll_callback=None, trade_callback=None, players_list_callback=None):
        super().__init__(master)
        self.title(f"Scheda PG - {character.name}")
        self.geometry("600x700")
        apply_modern_window_style(self)
        self.character = character
        self.manager = manager
        self.on_save_callback = on_save_callback
        self.roll_callback = roll_callback
        self.trade_callback = trade_callback
        self.players_list_callback = players_list_callback
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
        ttk.Entry(header_frame, textvariable=self.level_var).grid(row=1, column=3, padx=5, pady=2, sticky="w")
        
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

        ttk.Label(combat_frame, text="Velocità:").grid(row=4, column=0, sticky="e", pady=2)
        self.speed_var = tk.IntVar()
        ttk.Entry(combat_frame, textvariable=self.speed_var).grid(row=4, column=1, pady=2)
        
        ttk.Button(combat_frame, text="Riposo Lungo", command=self.long_rest).grid(row=5, column=0, columnspan=3, pady=15, sticky="ew")

        # Tab Notebook (Destra per note/inventario/incantesimi)
        tabs_frame = ttk.Frame(body_frame)
        tabs_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(tabs_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.text_widgets = {}
        for tab_name, attr in [("Zaino (Griglia)", "inventory_grid"), ("Tratti e Privilegi", "features"), ("Incantesimi", "spell_slots"), ("Note", "notes")]:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=tab_name)
            
            if attr == "inventory_grid":
                grid_container = ttk.Frame(frame)
                grid_container.pack(expand=True, pady=10)
                
                compendium_btn = ttk.Button(frame, text="Cerca nel Compendio", command=self.open_inventory_compendium)
                compendium_btn.pack(side=tk.TOP, pady=5)
                
                self.inventory_buttons = []
                for i in range(25):
                    btn = ttk.Button(grid_container, text="", width=12, command=lambda idx=i: self.on_inventory_click(idx))
                    btn.grid(row=i//5, column=i%5, padx=2, pady=2)
                    self.inventory_buttons.append(btn)
            elif attr == "spell_slots":
                self.build_spells_tab(frame)
            else:
                txt = tk.Text(frame, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=self.default_font, wrap=tk.WORD)
                txt.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
                self.text_widgets[attr] = txt

        # Pulsanti (in fondo alla scheda)
        btn_frame = ttk.Frame(main_frame, padding=(0, 10))
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(btn_frame, text="Salva", command=self.save_character, style="Primary.TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def build_spells_tab(self, parent_frame):
        slots_frame = ttk.LabelFrame(parent_frame, text="Slot Incantesimo (Usati / Massimi)")
        slots_frame.pack(fill=tk.X, padx=5, pady=5)
        self.slot_vars = {}
        for i in range(1, 10):
            lvl_frame = ttk.Frame(slots_frame)
            lvl_frame.pack(side=tk.LEFT, padx=3, expand=True)
            ttk.Label(lvl_frame, text=f"Lvl {i}").pack()
            sub_frame = ttk.Frame(lvl_frame)
            sub_frame.pack()
            usati = tk.IntVar(value=0); massimi = tk.IntVar(value=0)
            self.slot_vars[str(i)] = [usati, massimi]
            ttk.Entry(sub_frame, textvariable=usati, width=2, justify="center").pack(side=tk.LEFT)
            ttk.Label(sub_frame, text="/").pack(side=tk.LEFT)
            ttk.Entry(sub_frame, textvariable=massimi, width=2, justify="center").pack(side=tk.LEFT)
            
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
        ttk.Button(btn_frame, text="Compendio", command=self.open_inventory_compendium).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Rimuovi", command=self.remove_spell).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Dettagli / Lancia", command=self.cast_spell).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Riposo Lungo", command=self.recover_spell_slots).pack(side=tk.RIGHT, padx=5)

    def sort_spells(self, col):
        if not hasattr(self.character, "spell_list"): return
        self.character.spell_list.sort(key=lambda s: int(s.get("level", 0)))
        self.refresh_spell_list()

    def refresh_spell_list(self):
        if not hasattr(self, 'spell_tree'): return
        for item in self.spell_tree.get_children(): self.spell_tree.delete(item)
        for i, s in enumerate(getattr(self.character, "spell_list", [])):
            lvl = s.get("level", 0)
            lvl_str = "Trucchetto" if lvl == 0 else str(lvl)
            self.spell_tree.insert("", tk.END, iid=str(i), values=(lvl_str, s.get("name", ""), s.get("time", ""), s.get("range", "")))

    def add_spell(self):
        name = simpledialog.askstring("Incantesimo", "Nome Incantesimo:")
        if not name: return
        lvl = simpledialog.askinteger("Incantesimo", "Livello (0 per Trucchetto, 1-9):", minvalue=0, maxvalue=9)
        if lvl is None: return
        time = simpledialog.askstring("Incantesimo", "Tempo di Lancio (es. 1 Azione):") or ""
        rng = simpledialog.askstring("Incantesimo", "Raggio (es. 18m):") or ""
        desc = simpledialog.askstring("Incantesimo", "Effetto/Descrizione breve:") or ""
        
        if not hasattr(self.character, "spell_list"): self.character.spell_list = []
        self.character.spell_list.append({"name": name, "level": lvl, "time": time, "range": rng, "desc": desc})
        self.refresh_spell_list()

    def remove_spell(self):
        sel = self.spell_tree.selection()
        if not sel: return
        idx = int(sel[0])
        if messagebox.askyesno("Conferma", "Vuoi rimuovere questo incantesimo?"):
            self.character.spell_list.pop(idx)
            self.refresh_spell_list()

    def cast_spell(self):
        sel = self.spell_tree.selection()
        if not sel: return
        idx = int(sel[0])
        spell = self.character.spell_list[idx]
        
        msg = f"INCANTESIMO: {spell['name']}\nLivello: {spell['level']}\nTempo: {spell['time']}\nRaggio: {spell['range']}\n\nDescrizione: {spell['desc']}\n\nVuoi LANCIARE questo incantesimo in chat?"
        if messagebox.askyesno("Dettagli Incantesimo", msg):
            lvl = str(spell['level'])
            if spell['level'] > 0 and lvl in self.slot_vars:
                usati_var, massimi_var = self.slot_vars[lvl]
                if usati_var.get() < massimi_var.get():
                    usati_var.set(usati_var.get() + 1)
                else:
                    if not messagebox.askyesno("Slot Esauriti", f"Non hai più slot di livello {lvl}. Vuoi lanciarlo lo stesso (es. da un oggetto o livello superiore)?"):
                        return
            
            if self.roll_callback:
                chat_msg = f"Lancia '{spell['name']}'! (Livello {spell['level']}, Raggio {spell['range']})"
                # Simuliamo un lancio fittizio per usare la funzione di chat globale
                self.roll_callback("0d0", chat_msg)

    def recover_spell_slots(self):
        if messagebox.askyesno("Riposo Lungo", "Recuperare tutti gli slot incantesimo e la salute?"):
            for lvl, vars_ in self.slot_vars.items():
                vars_[0].set(0) # Azzera usati
            self.hp_cur_var.set(self.hp_max_var.get())

    def load_data(self):
        self.name_var.set(self.character.name)
        self.campaign_var.set(self.character.campaign)
        self.class_var.set(self.character.char_class)
        self.level_var.set(self.character.level)
        self.race_var.set(self.character.race)
        
        for k, v in self.character.attributes.items():
            self.attr_vars[k].set(v)
            
        self.hp_cur_var.set(self.character.hp_current)
        self.hp_max_var.set(self.character.hp_max)
        self.ac_var.set(self.character.ac)
        self.init_var.set(self.character.initiative)
        self.speed_var.set(self.character.speed)

        for attr, txt in self.text_widgets.items():
            txt.insert("1.0", getattr(self.character, attr, ""))
            
        # Carica slot incantesimi
        if hasattr(self.character, "spell_slots"):
            for lvl, vals in self.character.spell_slots.items():
                if lvl in self.slot_vars:
                    self.slot_vars[lvl][0].set(vals[0])
                    self.slot_vars[lvl][1].set(vals[1])
                    
        self.refresh_spell_list()
        self.refresh_inventory_grid()

    def refresh_inventory_grid(self):
        for i, item in enumerate(self.character.inventory_grid):
            btn = self.inventory_buttons[i]
            if item:
                name = item.get("name", "Oggetto")
                qty = item.get("qty", 1)
                short_name = name[:10] + ".." if len(name) > 12 else name
                btn.config(text=f"{short_name}\nx{qty}", style="SlotFilled.TButton")
            else:
                btn.config(text="", style="Slot.TButton")

    def on_inventory_click(self, idx):
        item = self.character.inventory_grid[idx]
        if not item: return
        
        info = f"Nome: {item.get('name')}\nTipo: {item.get('type')}\nQuantità: {item.get('qty')}\n\nDescrizione:\n{item.get('desc')}"
        
        win = tk.Toplevel(self)
        apply_modern_window_style(win)
        win.title("Dettagli Oggetto")
        win.geometry("300x300")
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
            if not hasattr(self.character, "spell_list"):
                self.character.spell_list = []
            
            desc = item_data.get("desc", "")
            if isinstance(desc, list):
                desc = "\n".join(desc)
                
            self.character.spell_list.append({
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
                
            self.character.hp_current = self.hp_cur_var.get()
            self.character.hp_max = self.hp_max_var.get()
            self.character.ac = self.ac_var.get()
            self.character.initiative = self.init_var.get()
            self.character.speed = self.speed_var.get()
            
            for attr, txt in self.text_widgets.items():
                val = txt.get("1.0", tk.END).strip()
                setattr(self.character, attr, val)
                
            # Salva slot incantesimi
            if not hasattr(self.character, "spell_slots"):
                self.character.spell_slots = {}
            for lvl, vars_ in self.slot_vars.items():
                self.character.spell_slots[lvl] = [vars_[0].get(), vars_[1].get()]
                
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
            self.roll_callback(f"1d20{mod_str}", f"Check {stat_name}")
        except ValueError:
            pass

    def roll_initiative(self):
        if not self.roll_callback: return
        try:
            des_val = int(self.attr_vars["DES"].get())
            mod = (des_val - 10) // 2
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            self.roll_callback(f"1d20{mod_str}", "Iniziativa")
        except ValueError:
            pass

    def long_rest(self):
        try:
            max_hp = self.hp_max_var.get()
            self.hp_cur_var.set(max_hp)
            messagebox.showinfo("Riposo Lungo", "Hai recuperato tutti i Punti Ferita! Ricordati di salvare la scheda.")
        except ValueError:
            pass
