import tkinter as tk
from common.messagebox import messagebox
from tkinter import ttk
from common.theme import apply_modern_window_style
from common.srd_offline import (
    extract_and_normalize_attributes,
    normalize_ac_value,
    normalize_speed_value,
)

class EncounterBuilderDialog(tk.Toplevel):
    def __init__(self, master, game_state, on_start_encounter_callback=None):
        super().__init__(master)
        self.title("Encounter Builder")
        self.minsize(600, 500)
        apply_modern_window_style(self)
        
        self.game_state = game_state
        self.on_start_encounter_callback = on_start_encounter_callback
        
        self.monsters = []  # List of dicts
        self.party_thresholds = {"Facile": 0, "Medio": 0, "Difficile": 0, "Mortale": 0}
        
        self.setup_ui()
        self.calculate_party_level()
        
    def setup_ui(self):
        # Top Frame: Party Info
        party_frame = ttk.LabelFrame(self, text="Gruppo Giocatori")
        party_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.lbl_party_info = ttk.Label(party_frame, text="Calcolo in corso...")
        self.lbl_party_info.pack(padx=10, pady=5, anchor="w")
        
        # Middle Frame: Monsters
        monster_frame = ttk.LabelFrame(self, text="Mostri nell'Incontro")
        monster_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        btn_add = ttk.Button(monster_frame, text="+ Aggiungi Mostro (Compendio)", command=self.open_compendium)
        btn_add.pack(pady=5)
        
        columns = ("name", "xp", "count", "hp", "init")
        self.tree = ttk.Treeview(monster_frame, columns=columns, show="headings")
        self.tree.heading("name", text="Nome")
        self.tree.heading("xp", text="XP")
        self.tree.heading("count", text="Q.tà")
        self.tree.heading("hp", text="HP")
        self.tree.heading("init", text="Iniz.")
        
        self.tree.column("name", width=150)
        self.tree.column("xp", width=50, anchor="center")
        self.tree.column("count", width=50, anchor="center")
        self.tree.column("hp", width=50, anchor="center")
        self.tree.column("init", width=50, anchor="center")
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Buttons to adjust quantity
        qty_frame = ttk.Frame(monster_frame)
        qty_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(qty_frame, text="- 1", command=self.decrease_qty).pack(side=tk.LEFT, padx=5)
        ttk.Button(qty_frame, text="+ 1", command=self.increase_qty).pack(side=tk.LEFT, padx=5)
        ttk.Button(qty_frame, text="Rimuovi", command=self.remove_monster).pack(side=tk.RIGHT, padx=5)
        
        # Bottom Frame: Difficulty & Deploy
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.lbl_difficulty = ttk.Label(bottom_frame, text="Difficoltà: -- (0 XP)", font=("Georgia", 11, "bold"))
        self.lbl_difficulty.pack(side=tk.LEFT, padx=5)
        
        btn_deploy = ttk.Button(bottom_frame, text="Schiera Incontro!", command=self.deploy_encounter, style="Primary.TButton")
        btn_deploy.pack(side=tk.RIGHT, padx=5)
        
    def calculate_party_level(self):
        players = self.game_state.get_all_players()
        real_players = [p for p in players if getattr(p, "conn", None) is not None]
        
        if not real_players:
            self.lbl_party_info.config(text="Nessun giocatore connesso. Imposto budget di default (Livello 1 x 4).")
            # Fake 4 players of level 1
            levels = [1, 1, 1, 1]
        else:
            levels = []
            for p in real_players:
                lvl = 1
                if hasattr(p, "full_sheet") and isinstance(p.full_sheet, dict):
                    lvl = int(p.full_sheet.get("level", 1))
                levels.append(lvl)
        
        from common.encounter_calc import calculate_encounter_difficulty
        self.party_levels = list(levels) if levels else [1]
        res = calculate_encounter_difficulty(self.party_levels, [])
        t = res["thresholds"]
        total_easy, total_medium, total_hard, total_deadly = t["easy"], t["medium"], t["hard"], t["deadly"]
        self.party_thresholds = {
            "Facile": total_easy,
            "Medio": total_medium,
            "Difficile": total_hard,
            "Mortale": total_deadly
        }
        
        avg_lvl = sum(levels) / len(levels) if levels else 1
        
        info_text = f"Giocatori: {len(levels)} | Livello Medio: {avg_lvl:.1f}\n"
        info_text += f"Soglie XP Gruppo -> Facile: {total_easy}, Medio: {total_medium}, Difficile: {total_hard}, Mortale: {total_deadly}"
        self.lbl_party_info.config(text=info_text)
        
        self.update_difficulty()

    def open_compendium(self):
        try:
            from server.compendium_ui import CompendiumDialog
            win = CompendiumDialog(
                self,
                on_import_callback=self.on_monster_imported,
                is_dm=True,
                initial_category="Mostri",
                monsters_only=True,
                action_label="➕ Aggiungi all'Incontro"
            )
            win.grab_set()
        except Exception as e:
            messagebox.showerror("Errore", str(e))
            
    def on_monster_imported(self, item_data, category):
        name = item_data.get("name", "Mostro")
        xp = item_data.get("xp", 50)
        hp = item_data.get("hit_points", item_data.get("hp", 10))
        
        ac = normalize_ac_value(item_data.get("armor_class", item_data.get("ac", 10)))
        speed_val, speed_disp, speed_unit = normalize_speed_value(item_data.get("speed", 30))
            
        attrs = extract_and_normalize_attributes(item_data, name)
        dex_val = attrs.get("DES", 10)
        initiative = item_data.get("initiative")
        if initiative is None or initiative == 0:
            initiative = (dex_val - 10) // 2
        
        # Check if already in list
        for m in self.monsters:
            if m["name"] == name:
                m["count"] += 1
                if "attributes" not in m or not m["attributes"]:
                    m["attributes"] = attrs
                self.refresh_list()
                return
                
        self.monsters.append({
            "name": name,
            "xp": xp,
            "count": 1,
            "hp": hp,
            "ac": ac,
            "initiative": initiative,
            "attributes": attrs,
            "cr": str(item_data.get("challenge_rating", item_data.get("cr", "1"))),
            "speed": speed_val,
            "speed_display": speed_disp,
            "speed_unit": speed_unit,
            "actions": item_data.get("actions", []),
            "features": item_data.get("features", item_data.get("special_abilities", []))
        })
        self.refresh_list()
        
    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for idx, m in enumerate(self.monsters):
            self.tree.insert("", "end", iid=str(idx), values=(m["name"], m["xp"], m["count"], m["hp"], m["initiative"]))
            
        self.update_difficulty()
        
    def get_selected_index(self):
        sel = self.tree.selection()
        if not sel: return None
        return int(sel[0])

    def increase_qty(self):
        idx = self.get_selected_index()
        if idx is not None:
            self.monsters[idx]["count"] += 1
            self.refresh_list()
            self.tree.selection_set(str(idx))

    def decrease_qty(self):
        idx = self.get_selected_index()
        if idx is not None:
            if self.monsters[idx]["count"] > 1:
                self.monsters[idx]["count"] -= 1
            else:
                self.monsters.pop(idx)
            self.refresh_list()
            if idx < len(self.monsters):
                self.tree.selection_set(str(idx))
            elif self.monsters:
                self.tree.selection_set(str(len(self.monsters)-1))

    def remove_monster(self):
        idx = self.get_selected_index()
        if idx is not None:
            self.monsters.pop(idx)
            self.refresh_list()

    def update_difficulty(self):
        from common.encounter_calc import calculate_encounter_difficulty
        monster_xps = []
        for m in self.monsters:
            monster_xps.extend([int(m.get("xp", 0))] * int(m.get("count", 0)))
            
        if not monster_xps:
            self.lbl_difficulty.config(text="Difficoltà: -- (0 XP)", foreground="white")
            return
            
        levels = getattr(self, "party_levels", None) or [1]
        res = calculate_encounter_difficulty(levels, monster_xps)
        adj_xp = res["adjusted_xp"]
        raw_xp = res["raw_xp"]
        mult = res["multiplier"]
        
        diff_str = "Facile"
        color = "green"
        if adj_xp >= self.party_thresholds["Mortale"]:
            diff_str = "Mortale"
            color = "red"
        elif adj_xp >= self.party_thresholds["Difficile"]:
            diff_str = "Difficile"
            color = "orange"
        elif adj_xp >= self.party_thresholds["Medio"]:
            diff_str = "Medio"
            color = "yellow"
            
        self.lbl_difficulty.config(text=f"Difficoltà: {diff_str} ({adj_xp} XP Adattati | Base {raw_xp} x{mult})", foreground=color)
        
    def deploy_encounter(self):
        if not self.monsters:
            messagebox.showwarning("Attenzione", "Nessun mostro nell'incontro!")
            return
            
        if self.on_start_encounter_callback:
            self.on_start_encounter_callback(self.monsters)
            
        self.destroy()
