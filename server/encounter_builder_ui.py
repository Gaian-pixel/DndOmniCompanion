import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from common.theme import apply_modern_window_style
from server.compendium_manager import CompendiumManager

class EncounterBuilderUI(tk.Toplevel):
    def __init__(self, master, on_start_encounter_callback):
        super().__init__(master)
        self.title("Preparazione Combattimento")
        self.geometry("800x600")
        apply_modern_window_style(self)
        
        self.on_start_encounter_callback = on_start_encounter_callback
        self.compendium_manager = CompendiumManager()
        self.encounter_monsters = []  # List of dicts: {"name": str, "hp": int, "initiative": int, "count": int}
        self.available_monsters = []
        
        self.setup_ui()
        self.load_monsters()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # LEFT: Compendium (Mostri)
        left_frame = ttk.LabelFrame(main_frame, text="Compendio Mostri (Custom & Offline)")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(search_frame, text="Cerca:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.filter_monsters)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.monster_listbox = tk.Listbox(left_frame)
        self.monster_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Button(left_frame, text="Aggiungi all'Incontro >>>", command=self.add_to_encounter).pack(pady=5)
        
        # RIGHT: Current Encounter
        right_frame = ttk.LabelFrame(main_frame, text="Incontro Attuale")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.encounter_tree = ttk.Treeview(right_frame, columns=("count", "hp", "init"), show="headings")
        self.encounter_tree.heading("count", text="Q.tà")
        self.encounter_tree.heading("hp", text="HP")
        self.encounter_tree.heading("init", text="Iniziativa")
        self.encounter_tree.column("count", width=40)
        self.encounter_tree.column("hp", width=50)
        self.encounter_tree.column("init", width=60)
        self.encounter_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="Rimuovi", command=self.remove_from_encounter).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Modifica Q.tà/HP", command=self.edit_encounter_item).pack(side=tk.LEFT, padx=5)
        
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(bottom_frame, text="Svuota Incontro", command=self.clear_encounter).pack(side=tk.LEFT)
        ttk.Button(bottom_frame, text="Manda in Mappa (Avvia)", command=self.start_encounter, style="Success.TButton").pack(side=tk.RIGHT)
        
    def load_monsters(self):
        self.available_monsters = []
        # Load from Custom Compendium
        custom = self.compendium_manager.get_items("Mostri")
        for m in custom:
            self.available_monsters.append(m)
            
        # Try to load Offline SRD monsters
        try:
            import os, json
            from server.srd_downloader import DOWNLOADABLE_COMPENDIUMS
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "srd_data")
            for comp in DOWNLOADABLE_COMPENDIUMS:
                if comp["type"] == "Mostri":
                    path = os.path.join(data_dir, comp["filename"])
                    if os.path.exists(path):
                        with open(path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            self.available_monsters.extend(data)
        except:
            pass
            
        self.filter_monsters()
        
    def filter_monsters(self, *args):
        self.monster_listbox.delete(0, tk.END)
        q = self.search_var.get().lower()
        for m in self.available_monsters:
            if q in m.get("name", "").lower():
                prefix = "[Custom] " if m.get("is_custom") else ""
                self.monster_listbox.insert(tk.END, prefix + m.get("name", "Sconosciuto"))
                
    def add_to_encounter(self):
        sel = self.monster_listbox.curselection()
        if not sel: return
        name_str = self.monster_listbox.get(sel[0])
        real_name = name_str.replace("[Custom] ", "", 1)
        
        monster_data = None
        for m in self.available_monsters:
            if m.get("name") == real_name:
                monster_data = m
                break
                
        if not monster_data: return
        
        # Check if already exists
        for item in self.encounter_monsters:
            if item["name"] == real_name:
                item["count"] += 1
                self.update_encounter_tree()
                return
                
        # Add new
        hp = monster_data.get("hp", 10)
        init = monster_data.get("initiative", 0)
        
        self.encounter_monsters.append({
            "name": real_name,
            "hp": hp,
            "initiative": init,
            "count": 1
        })
        self.update_encounter_tree()
        
    def update_encounter_tree(self):
        for row in self.encounter_tree.get_children():
            self.encounter_tree.delete(row)
        for idx, item in enumerate(self.encounter_monsters):
            self.encounter_tree.insert("", "end", iid=str(idx), text=item["name"], values=(item["count"], item["hp"], item["initiative"]))
            
    def remove_from_encounter(self):
        sel = self.encounter_tree.selection()
        if not sel: return
        idx = int(sel[0])
        del self.encounter_monsters[idx]
        self.update_encounter_tree()
        
    def edit_encounter_item(self):
        sel = self.encounter_tree.selection()
        if not sel: return
        idx = int(sel[0])
        item = self.encounter_monsters[idx]
        
        new_count = simpledialog.askinteger("Quantità", f"Quantità per {item['name']}:", initialvalue=item["count"], parent=self)
        if new_count is not None and new_count > 0:
            item["count"] = new_count
            
        new_hp = simpledialog.askinteger("HP", f"HP base per {item['name']}:", initialvalue=item["hp"], parent=self)
        if new_hp is not None:
            item["hp"] = new_hp
            
        self.update_encounter_tree()
        
    def clear_encounter(self):
        self.encounter_monsters = []
        self.update_encounter_tree()
        
    def start_encounter(self):
        if not self.encounter_monsters:
            messagebox.showinfo("Avviso", "L'incontro è vuoto.")
            return
            
        if messagebox.askyesno("Avvia Incontro", "Vuoi inviare tutti i mostri alla mappa e preparare il combattimento?"):
            self.on_start_encounter_callback(self.encounter_monsters)
            self.destroy()

