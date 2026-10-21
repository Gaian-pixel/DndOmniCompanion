# server/campaign_editor_ui.py
"""
Modulo UI per la creazione, modifica e selezione delle Campagne in D&D OmniCompanion.
Supporta l'organizzazione completa di metadati, scene/mappe, incontri preparati,
missioni, PNG, handouts ed equipaggiamento iniziale.
"""

import os
import shutil
import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog, filedialog
from typing import Optional, Callable, Dict, Any, List

from common.theme import (
    apply_modern_window_style, BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT,
    BORDER_COLOR, BORDER_GOLD, ACCENT_GOLD, ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE,
    TEXT_COLOR, TEXT_MUTED, TEXT_DARK,
    FONT_TITLE, FONT_HEADER, FONT_MAIN, FONT_BOLD, FONT_SMALL, FONT_BADGE
)
from common.messagebox import messagebox
from common.campaign import Campaign, get_available_campaigns, DEFAULT_CAMPAIGNS_DIR
from common.game_state import GameState, Player
from common.protocol import make_player_joined, make_handout_broadcast, make_chat_broadcast
from common.network_utils import broadcast
from common.srd_offline import (
    extract_and_normalize_attributes,
    normalize_ac_value,
    normalize_speed_value,
)


class CampaignEncounterDialog(tk.Toplevel):
    """Finestra di creazione/modifica di un singolo incontro della campagna."""
    def __init__(self, master, encounter_data: Optional[Dict[str, Any]] = None, on_save_callback: Optional[Callable] = None):
        super().__init__(master)
        self.encounter_data = encounter_data or {
            "name": "Nuovo Incontro",
            "act": "Atto 1",
            "description": "",
            "monsters": []
        }
        self.on_save_callback = on_save_callback
        self.monsters = [m.copy() for m in self.encounter_data.get("monsters", [])]
        
        self.title("D&D OmniCompanion • Editor Incontro Campagna")
        self.minsize(620, 500)
        self.transient(master)
        self.grab_set()
        apply_modern_window_style(self)
        self.configure(bg=BG_COLOR)
        
        self.setup_ui()
        self.bind("<F11>", self.toggle_fullscreen, add="+")
        self.bind("<Escape>", self.exit_fullscreen, add="+")
        
    def setup_ui(self):
        container = tk.Frame(self, bg=BG_COLOR, padx=15, pady=12)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Header Info
        header_card = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        header_card.pack(fill=tk.X, pady=(0, 10))
        
        row1 = tk.Frame(header_card, bg=SURFACE_COLOR)
        row1.pack(fill=tk.X, pady=(0, 6))
        
        tk.Label(row1, text="Nome Incontro:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT, padx=(0, 6))
        self.ent_name = ttk.Entry(row1, font=FONT_MAIN)
        self.ent_name.insert(0, self.encounter_data.get("name", "Nuovo Incontro"))
        self.ent_name.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))
        
        tk.Label(row1, text="Atto / Capitolo:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT, padx=(0, 6))
        self.ent_act = ttk.Entry(row1, font=FONT_MAIN, width=16)
        self.ent_act.insert(0, self.encounter_data.get("act", "Atto 1"))
        self.ent_act.pack(side=tk.LEFT)
        
        row2 = tk.Frame(header_card, bg=SURFACE_COLOR)
        row2.pack(fill=tk.X)
        tk.Label(row2, text="Descrizione / Note Tattiche:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w")
        self.txt_desc = tk.Text(row2, height=3, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_SMALL,
                                relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, wrap=tk.WORD)
        self.txt_desc.insert("1.0", self.encounter_data.get("description", ""))
        self.txt_desc.pack(fill=tk.X, pady=(3, 0))
        
        # Monster List Section
        monster_card = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        monster_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        m_top = tk.Frame(monster_card, bg=SURFACE_COLOR)
        m_top.pack(fill=tk.X, pady=(0, 6))
        tk.Label(m_top, text="👾 Mostri & PNG dell'Incontro", font=FONT_HEADER, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        
        btn_comp = ttk.Button(m_top, text="+ Compendio SRD", command=self.add_from_compendium, style="Primary.TButton")
        btn_comp.pack(side=tk.RIGHT, padx=(4, 0))
        btn_manual = ttk.Button(m_top, text="+ Mostro Manuale", command=self.add_monster_manual)
        btn_manual.pack(side=tk.RIGHT)
        
        tree_frame = tk.Frame(monster_card, bg=SURFACE_COLOR)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        cols = ("Nome", "Quantità", "HP", "Iniziativa", "XP")
        self.tree_monsters = ttk.Treeview(tree_frame, columns=cols, show="headings", height=6)
        for c in cols:
            self.tree_monsters.heading(c, text=c)
        self.tree_monsters.column("Nome", width=220)
        self.tree_monsters.column("Quantità", width=70, anchor="center")
        self.tree_monsters.column("HP", width=70, anchor="center")
        self.tree_monsters.column("Iniziativa", width=80, anchor="center")
        self.tree_monsters.column("XP", width=70, anchor="center")
        
        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_monsters.yview)
        self.tree_monsters.configure(yscrollcommand=sb.set)
        self.tree_monsters.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        m_ctrl = tk.Frame(monster_card, bg=SURFACE_COLOR)
        m_ctrl.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(m_ctrl, text="+1 Quantità", command=lambda: self.adjust_qty(1)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(m_ctrl, text="-1 Quantità", command=lambda: self.adjust_qty(-1)).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(m_ctrl, text="🗑️ Rimuovi Mostro", command=self.remove_monster).pack(side=tk.LEFT, padx=(0, 4))
        
        self.lbl_summary = tk.Label(m_ctrl, text="Totale mostri: 0", font=FONT_SMALL, bg=SURFACE_COLOR, fg=ACCENT_GOLD)
        self.lbl_summary.pack(side=tk.RIGHT)
        
        # Bottom Buttons
        bottom_row = tk.Frame(container, bg=BG_COLOR)
        bottom_row.pack(fill=tk.X)
        ttk.Button(bottom_row, text="💾 Salva Incontro", command=self.save_encounter, style="Gold.TButton").pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(bottom_row, text="Annulla", command=self.destroy).pack(side=tk.RIGHT)
        
        self.refresh_monsters_list()

    def refresh_monsters_list(self):
        for item in self.tree_monsters.get_children():
            self.tree_monsters.delete(item)
        tot_count = 0
        tot_xp = 0
        for idx, m in enumerate(self.monsters):
            cnt = m.get("count", 1)
            xp = m.get("xp", 50)
            tot_count += cnt
            tot_xp += xp * cnt
            self.tree_monsters.insert("", tk.END, iid=str(idx), values=(
                m.get("name", "Mostro"),
                str(cnt),
                str(m.get("hp", 10)),
                str(m.get("initiative", 0)),
                str(xp)
            ))
        self.lbl_summary.config(text=f"Mostri: {tot_count} | XP Totali: {tot_xp}")

    def adjust_qty(self, delta: int):
        sel = self.tree_monsters.selection()
        if not sel: return
        idx = int(sel[0])
        self.monsters[idx]["count"] = max(1, self.monsters[idx].get("count", 1) + delta)
        self.refresh_monsters_list()

    def remove_monster(self):
        sel = self.tree_monsters.selection()
        if not sel: return
        idx = int(sel[0])
        self.monsters.pop(idx)
        self.refresh_monsters_list()

    def add_monster_manual(self):
        name = simpledialog.askstring("Nuovo Mostro", "Nome del mostro/avversario:", parent=self)
        if not name or not name.strip(): return
        hp = simpledialog.askinteger("Punti Ferita", "HP massimi:", initialvalue=15, minvalue=1, parent=self) or 15
        init = simpledialog.askinteger("Iniziativa", "Bonus iniziativa (Des):", initialvalue=0, parent=self) or 0
        xp = simpledialog.askinteger("XP", "Punti Esperienza (XP):", initialvalue=50, minvalue=0, parent=self) or 50
        self.monsters.append({
            "name": name.strip(),
            "count": 1,
            "hp": hp,
            "initiative": init,
            "xp": xp
        })
        self.refresh_monsters_list()

    def add_from_compendium(self):
        try:
            from server.compendium_ui import CompendiumDialog
            def on_imported(item_data, category):
                name = item_data.get("name", "Mostro")
                hp = item_data.get("hit_points", 15)
                # Calcolo des mod per iniziativa
                dex = item_data.get("dexterity", 10)
                init_mod = (dex - 10) // 2
                xp = item_data.get("xp", 50)
                self.monsters.append({
                    "name": name,
                    "count": 1,
                    "hp": hp,
                    "initiative": init_mod,
                    "xp": xp
                })
                self.refresh_monsters_list()
                
            dlg = CompendiumDialog(self, on_import_callback=on_imported, is_dm=True, initial_category="Mostri", action_label="➕ Aggiungi all'Incontro")
            dlg.grab_set()
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire il compendio: {e}", parent=self)

    def save_encounter(self):
        name = self.ent_name.get().strip()
        if not name:
            messagebox.showwarning("Attenzione", "Inserisci un nome per l'incontro.", parent=self)
            return
        self.encounter_data["name"] = name
        self.encounter_data["act"] = self.ent_act.get().strip() or "Atto 1"
        self.encounter_data["description"] = self.txt_desc.get("1.0", tk.END).strip()
        self.encounter_data["monsters"] = self.monsters
        if self.on_save_callback:
            self.on_save_callback(self.encounter_data)
        self.destroy()


class CampaignEditorDialog(tk.Toplevel):
    """Editor moderno completo per la preparazione in anticipo di una campagna."""
    def __init__(self, master, campaign: Optional[Campaign] = None, game_state: Optional[GameState] = None, on_save_callback: Optional[Callable] = None):
        super().__init__(master)
        self.campaign = campaign or Campaign(name="Nuova Campagna Avventura")
        if not self.campaign.starter_kit:
            from common.starter_equipment import DEFAULT_CAMPAIGN_STARTER_KIT
            self.campaign.starter_kit = [item.copy() for item in DEFAULT_CAMPAIGN_STARTER_KIT]
        self.game_state = game_state
        self.on_save_callback = on_save_callback
        
        self.title(f"D&D OmniCompanion • Preparazione Campagna: {self.campaign.name}")
        self.minsize(1050, 720)
        self.geometry("1150x760")
        self.transient(master)
        self.grab_set()
        apply_modern_window_style(self)
        self.configure(bg=BG_COLOR)
        
        self.setup_ui()

    def setup_ui(self):
        container = tk.Frame(self, bg=BG_COLOR, padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)
        
        # --- TOP HEADER & ACTIONS BAR ---
        top_bar = tk.Frame(container, bg=BG_COLOR)
        top_bar.pack(fill=tk.X, pady=(0, 10))
        
        title_box = tk.Frame(top_bar, bg=BG_COLOR)
        title_box.pack(side=tk.LEFT)
        tk.Label(title_box, text="🏰 Gestione & Preparazione Campagna", font=("Georgia", 15, "bold"), bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
        tk.Label(title_box, text="Prepara in anticipo scene, incontri tattici, quest, PNG chiave, loot e segreti", 
                 font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w")
        
        actions_box = tk.Frame(top_bar, bg=BG_COLOR)
        actions_box.pack(side=tk.RIGHT)
        
        ttk.Button(actions_box, text="📖 Compendio 5e", command=self.open_global_compendium, style="Primary.TButton").pack(side=tk.LEFT, padx=4)
        
        self.btn_fs = ttk.Button(actions_box, text="⛶ Schermo Intero", command=self.toggle_fullscreen)
        self.btn_fs.pack(side=tk.LEFT, padx=4)
        
        if self.game_state:
            ttk.Button(actions_box, text="⚡ Applica Subito al Gioco", command=self.apply_to_running_game, style="Gold.TButton").pack(side=tk.LEFT, padx=4)
        
        ttk.Button(actions_box, text="💾 Salva Campagna", command=self.save_campaign, style="Success.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(actions_box, text="Chiudi", command=self.destroy).pack(side=tk.LEFT, padx=4)
        
        # --- NOTEBOOK TABS ---
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # TAB 1: STUDIO FLUSSO & DNDSCRIPT (Campaign-as-Code & Visual Graph)
        tab_studio = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(tab_studio, text="🧭 Flusso & DndScript")
        self.build_tab_studio(tab_studio)
        
        # TAB 2: GENERALE & METADATI
        tab_general = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab_general, text="📜 Generale & Note DM")
        self.build_tab_general(tab_general)
        
        # TAB 3: SCENE & MAPPE
        tab_scenes = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab_scenes, text="🗺️ Scene & Mappe")
        self.build_tab_scenes(tab_scenes)
        
        # TAB 4: INCONTRI PREPARATI
        tab_encounters = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab_encounters, text="⚔️ Incontri Tattici")
        self.build_tab_encounters(tab_encounters)
        
        # TAB 5: MISSIONI & STORIA
        tab_quests = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab_quests, text="📖 Trame & Missioni")
        self.build_tab_quests(tab_quests)
        
        # TAB 6: PNG & FAZIONI
        tab_npcs = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab_npcs, text="🎭 PNG & Fazioni")
        self.build_tab_npcs(tab_npcs)
        
        # TAB 7: HANDOUTS
        tab_handouts = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab_handouts, text="📜 Handouts & Indizi")
        self.build_tab_handouts(tab_handouts)

    def build_tab_studio(self, parent):
        from server.campaign_studio_ui import CampaignStudioFrame
        self.studio_frame = CampaignStudioFrame(parent, campaign=self.campaign, on_change_callback=self._on_studio_changed)
        self.studio_frame.pack(fill=tk.BOTH, expand=True)

    def _on_studio_changed(self):
        try:
            if hasattr(self, "tree_scenes"):
                self.refresh_scenes_tree()
            if hasattr(self, "tree_encounters"):
                self.refresh_encounters_tree()
            if hasattr(self, "tree_quests"):
                self.refresh_quests_tree()
            if hasattr(self, "tree_npcs"):
                self.refresh_npcs_tree()
        except Exception:
            pass

    # -------------------------------------------------------------
    # TAB 1: GENERALE
    # -------------------------------------------------------------
    def build_tab_general(self, parent):
        grid_frame = tk.Frame(parent, bg=BG_COLOR)
        grid_frame.pack(fill=tk.BOTH, expand=True)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(0, weight=1)
        
        # Colonna Sinistra: Metadati e Calendario
        col_left = tk.Frame(grid_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=14, pady=12)
        col_left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        
        tk.Label(col_left, text="Informazioni Campagna", font=FONT_HEADER, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 10))
        
        # Nome
        tk.Label(col_left, text="Titolo Campagna:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        self.ent_title = ttk.Entry(col_left, font=FONT_MAIN)
        self.ent_title.insert(0, self.campaign.name)
        self.ent_title.pack(fill=tk.X, pady=(2, 10))
        
        # Livello e Meteo
        row_lv = tk.Frame(col_left, bg=SURFACE_COLOR)
        row_lv.pack(fill=tk.X, pady=(0, 10))
        
        sub_lv = tk.Frame(row_lv, bg=SURFACE_COLOR)
        sub_lv.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Label(sub_lv, text="Livello Consigliato:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        self.ent_level = ttk.Entry(sub_lv, font=FONT_MAIN)
        self.ent_level.insert(0, self.campaign.level_range)
        self.ent_level.pack(fill=tk.X, pady=(2, 0))
        
        sub_wt = tk.Frame(row_lv, bg=SURFACE_COLOR)
        sub_wt.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        tk.Label(sub_wt, text="Meteo Iniziale:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        self.combo_weather = ttk.Combobox(sub_wt, values=["Sereno", "Pioggia", "Tempesta", "Neve", "Nebbia", "Oscurità"], state="readonly")
        self.combo_weather.set(self.campaign.start_weather)
        self.combo_weather.pack(fill=tk.X, pady=(2, 0))
        
        # Calendario Iniziale
        cal_frame = tk.Frame(col_left, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=8)
        cal_frame.pack(fill=tk.X, pady=(0, 12))
        
        cal_header = tk.Frame(cal_frame, bg=SURFACE_COLOR_ALT)
        cal_header.pack(fill=tk.X, pady=(0, 4))
        tk.Label(cal_header, text="📅 Data & Ora di Partenza", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        
        r_cal = tk.Frame(cal_frame, bg=SURFACE_COLOR_ALT)
        r_cal.pack(fill=tk.X)
        
        tk.Label(r_cal, text="Anno:", bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_SMALL).pack(side=tk.LEFT)
        self.sp_year = ttk.Spinbox(r_cal, from_=1, to=3000, width=6, font=FONT_MAIN, command=self._update_date_preview)
        self.sp_year.set(self.campaign.start_date.get("year", 1492))
        self.sp_year.pack(side=tk.LEFT, padx=(3, 8))
        self.sp_year.bind("<KeyRelease>", lambda e: self._update_date_preview())
        
        tk.Label(r_cal, text="Mese:", bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_SMALL).pack(side=tk.LEFT)
        self.sp_month = ttk.Spinbox(r_cal, from_=1, to=12, width=4, font=FONT_MAIN, command=self._update_date_preview)
        self.sp_month.set(self.campaign.start_date.get("month", 1))
        self.sp_month.pack(side=tk.LEFT, padx=(3, 8))
        self.sp_month.bind("<KeyRelease>", lambda e: self._update_date_preview())
        
        tk.Label(r_cal, text="Giorno:", bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_SMALL).pack(side=tk.LEFT)
        self.sp_day = ttk.Spinbox(r_cal, from_=1, to=30, width=4, font=FONT_MAIN, command=self._update_date_preview)
        self.sp_day.set(self.campaign.start_date.get("day", 1))
        self.sp_day.pack(side=tk.LEFT, padx=(3, 8))
        self.sp_day.bind("<KeyRelease>", lambda e: self._update_date_preview())
        
        tk.Label(r_cal, text="Ora:", bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_SMALL).pack(side=tk.LEFT)
        self.sp_hour = ttk.Spinbox(r_cal, from_=0, to=23, width=4, font=FONT_MAIN, command=self._update_date_preview)
        self.sp_hour.set(self.campaign.start_date.get("hour", 8))
        self.sp_hour.pack(side=tk.LEFT, padx=(3, 0))
        self.sp_hour.bind("<KeyRelease>", lambda e: self._update_date_preview())
        
        # Badge anteprima Harptos
        self.lbl_date_preview = tk.Label(
            cal_frame,
            text="",
            font=FONT_BADGE,
            bg=SURFACE_COLOR,
            fg=ACCENT_GOLD,
            padx=8,
            pady=3,
            relief="solid",
            borderwidth=1,
            highlightbackground=BORDER_COLOR
        )
        self.lbl_date_preview.pack(fill=tk.X, pady=(6, 0))
        self._update_date_preview()
        
        # Starter Kit Campagna
        kit_frame = tk.Frame(col_left, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=8)
        kit_frame.pack(fill=tk.X, pady=(0, 10))
        
        kit_hdr = tk.Frame(kit_frame, bg=SURFACE_COLOR_ALT)
        kit_hdr.pack(fill=tk.X)
        tk.Label(kit_hdr, text="🎒 Equipaggiamento Iniziale del Party", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.lbl_kit_count = tk.Label(kit_hdr, text=self._get_kit_summary_text(), font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD)
        self.lbl_kit_count.pack(side=tk.RIGHT)
        
        tk.Label(
            kit_frame,
            text="Oggetti assegnati automaticamente ai PG al loro primo ingresso in questa campagna.",
            font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED
        ).pack(anchor="w", pady=(2, 6))
        
        kit_btn_box = tk.Frame(kit_frame, bg=SURFACE_COLOR_ALT)
        kit_btn_box.pack(fill=tk.X)
        ttk.Button(kit_btn_box, text="✏️ Modifica Kit Iniziale...", command=self.edit_starter_kit, style="Gold.TButton").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        ttk.Button(kit_btn_box, text="📖 Da Compendio...", command=self.add_starter_kit_from_compendium, style="Primary.TButton").pack(side=tk.RIGHT)
        
        # Sinossi / Descrizione pubblica
        tk.Label(col_left, text="Descrizione / Sinossi per i Giocatori:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(5, 0))
        self.txt_synopsis = scrolledtext.ScrolledText(col_left, height=6, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_SMALL,
                                                     relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, wrap=tk.WORD)
        self.txt_synopsis.insert("1.0", self.campaign.description)
        self.txt_synopsis.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        
        # Colonna Destra: Note Segrete DM
        col_right = tk.Frame(grid_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=14, pady=12)
        col_right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        
        tk.Label(col_right, text="🔒 Note Segrete & Canovaccio del DM", font=FONT_HEADER, bg=SURFACE_COLOR, fg=ACCENT_RED).pack(anchor="w")
        tk.Label(col_right, text="Colpi di scena, segreti dei PNG, CD prove e indizi nascosti (invisibili ai PG)", 
                 font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 8))
        
        self.txt_dm_notes = scrolledtext.ScrolledText(col_right, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_MAIN,
                                                     relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, wrap=tk.WORD)
        self.txt_dm_notes.insert("1.0", self.campaign.dm_notes)
        self.txt_dm_notes.pack(fill=tk.BOTH, expand=True)

    def _update_date_preview(self, *args):
        try:
            y = int(self.sp_year.get())
        except (ValueError, AttributeError):
            y = 1492
        try:
            m = int(self.sp_month.get())
        except (ValueError, AttributeError):
            m = 1
        try:
            d = int(self.sp_day.get())
        except (ValueError, AttributeError):
            d = 1
        try:
            h = int(self.sp_hour.get())
        except (ValueError, AttributeError):
            h = 8
        
        harptos_months = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
        m_name = harptos_months[m] if 1 <= m <= 12 else f"Mese {m}"
        if hasattr(self, "lbl_date_preview") and self.lbl_date_preview:
            self.lbl_date_preview.config(text=f"📅 {d} {m_name}, {y} CV • Ore {h:02d}:00")

    def _get_kit_summary_text(self):
        c = len(self.campaign.starter_kit) if getattr(self, "campaign", None) and getattr(self.campaign, "starter_kit", None) else 0
        return f"{c} oggetti configurati"

    def edit_starter_kit(self):
        try:
            from server.dm_dialogs import CampaignStarterKitDialog
            def on_saved(saved_items):
                self.campaign.starter_kit = [i.copy() for i in saved_items]
                if hasattr(self, "lbl_kit_count"):
                    self.lbl_kit_count.config(text=self._get_kit_summary_text())

            dlg = CampaignStarterKitDialog(self, initial_items=self.campaign.starter_kit, on_save_callback=on_saved)
            dlg.wait_window()
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire l'editor del kit: {e}", parent=self)

    # -------------------------------------------------------------
    # TAB 2: SCENE & MAPPE
    # -------------------------------------------------------------
    def build_tab_scenes(self, parent):
        top_row = tk.Frame(parent, bg=BG_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(top_row, text="Mappe e Scene della Campagna", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        ttk.Button(top_row, text="+ Collega Nuova Scena / Mappa", command=self.add_scene_dialog, style="Primary.TButton").pack(side=tk.RIGHT)
        
        tree_frame = tk.Frame(parent, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        cols = ("Nome", "File Mappa", "Iniziale", "Descrizione")
        self.tree_scenes = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        self.tree_scenes.heading("Nome", text="Nome Scena")
        self.tree_scenes.heading("File Mappa", text="File Mappa (.json)")
        self.tree_scenes.heading("Iniziale", text="Partenza")
        self.tree_scenes.heading("Descrizione", text="Descrizione / Note")
        
        self.tree_scenes.column("Nome", width=180)
        self.tree_scenes.column("File Mappa", width=220)
        self.tree_scenes.column("Iniziale", width=80, anchor="center")
        self.tree_scenes.column("Descrizione", width=320)
        
        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_scenes.yview)
        self.tree_scenes.configure(yscrollcommand=sb.set)
        self.tree_scenes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        ctrl_row = tk.Frame(parent, bg=BG_COLOR)
        ctrl_row.pack(fill=tk.X)
        ttk.Button(ctrl_row, text="★ Imposta come Mappa Iniziale", command=self.set_starting_map).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(ctrl_row, text="✏️ Modifica Scena", command=self.edit_scene_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(ctrl_row, text="🗑️ Rimuovi Scena", command=self.remove_scene).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(ctrl_row, text="🗺️ Apri Editor Mappe", command=self.open_map_editor).pack(side=tk.RIGHT)
        
        self.refresh_scenes()

    def refresh_scenes(self):
        for item in self.tree_scenes.get_children():
            self.tree_scenes.delete(item)
        for idx, sc in enumerate(self.campaign.scenes):
            is_start = "★ SÌ" if sc.get("map_file") == self.campaign.starting_map_file else ""
            self.tree_scenes.insert("", tk.END, iid=str(idx), values=(
                sc.get("name", "Scena"),
                sc.get("map_file", ""),
                is_start,
                sc.get("description", "")
            ))

    def add_scene_dialog(self):
        name = simpledialog.askstring("Nuova Scena", "Nome identificativo della scena (es. 'Taverna del Cinghiale'):", parent=self)
        if not name or not name.strip(): return
        
        map_file = filedialog.askopenfilename(
            title="Seleziona file mappa JSON",
            initialdir=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "maps")),
            filetypes=[("Mappe JSON", "*.json"), ("Tutti i file", "*.*")],
            parent=self
        )
        if not map_file: return
        
        # Relativizza il percorso se possibile
        proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        try:
            rel_map = os.path.relpath(map_file, proj_root).replace("\\", "/")
        except Exception:
            rel_map = map_file
            
        desc = simpledialog.askstring("Descrizione", "Note della scena per il DM:", initialvalue="", parent=self) or ""
        self.campaign.add_scene(name.strip(), rel_map, desc.strip())
        self.refresh_scenes()

    def edit_scene_dialog(self):
        sel = self.tree_scenes.selection()
        if not sel: return
        idx = int(sel[0])
        sc = self.campaign.scenes[idx]
        new_name = simpledialog.askstring("Modifica Scena", "Nome della scena:", initialvalue=sc.get("name"), parent=self)
        if not new_name: return
        new_desc = simpledialog.askstring("Descrizione", "Descrizione:", initialvalue=sc.get("description"), parent=self) or ""
        sc["name"] = new_name.strip()
        sc["description"] = new_desc.strip()
        self.refresh_scenes()

    def set_starting_map(self):
        sel = self.tree_scenes.selection()
        if not sel: return
        idx = int(sel[0])
        sc = self.campaign.scenes[idx]
        self.campaign.starting_map_file = sc.get("map_file")
        self.refresh_scenes()
        messagebox.showinfo("Mappa Iniziale", f"'{sc.get('name')}' impostata come mappa di partenza della campagna!", parent=self)

    def remove_scene(self):
        sel = self.tree_scenes.selection()
        if not sel: return
        idx = int(sel[0])
        self.campaign.scenes.pop(idx)
        self.refresh_scenes()

    def open_map_editor(self):
        try:
            from server.map_editor import MapEditorWindow
            MapEditorWindow(self)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire l'editor mappe: {e}", parent=self)

    # -------------------------------------------------------------
    # TAB 3: INCONTRI PREPARATI
    # -------------------------------------------------------------
    def build_tab_encounters(self, parent):
        top_row = tk.Frame(parent, bg=BG_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(top_row, text="Incontri e Battaglie Preparate", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        ttk.Button(top_row, text="+ Nuovo Incontro", command=self.add_encounter_dialog, style="Primary.TButton").pack(side=tk.RIGHT)
        
        tree_frame = tk.Frame(parent, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        cols = ("Nome", "Atto / Capitolo", "N. Mostri", "Dettaglio Mostri", "Descrizione")
        self.tree_enc = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        self.tree_enc.heading("Nome", text="Nome Incontro")
        self.tree_enc.heading("Atto / Capitolo", text="Atto")
        self.tree_enc.heading("N. Mostri", text="Mostri")
        self.tree_enc.heading("Dettaglio Mostri", text="Composizione")
        self.tree_enc.heading("Descrizione", text="Note Tattiche")
        
        self.tree_enc.column("Nome", width=180)
        self.tree_enc.column("Atto / Capitolo", width=110)
        self.tree_enc.column("N. Mostri", width=70, anchor="center")
        self.tree_enc.column("Dettaglio Mostri", width=250)
        self.tree_enc.column("Descrizione", width=240)
        
        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_enc.yview)
        self.tree_enc.configure(yscrollcommand=sb.set)
        self.tree_enc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        ctrl_row = tk.Frame(parent, bg=BG_COLOR)
        ctrl_row.pack(fill=tk.X)
        ttk.Button(ctrl_row, text="✏️ Modifica Incontro", command=self.edit_encounter_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(ctrl_row, text="🗑️ Rimuovi Incontro", command=self.remove_encounter).pack(side=tk.LEFT, padx=(0, 6))
        
        if self.game_state:
            ttk.Button(ctrl_row, text="⚡ Schiera Subito sulla Mappa", command=self.deploy_selected_encounter, style="Gold.TButton").pack(side=tk.RIGHT)
            
        self.refresh_encounters()

    def refresh_encounters(self):
        for item in self.tree_enc.get_children():
            self.tree_enc.delete(item)
        for idx, enc in enumerate(self.campaign.encounters):
            monsters = enc.get("monsters", [])
            tot_count = sum(m.get("count", 1) for m in monsters)
            summary = ", ".join(f"{m.get('name')} (x{m.get('count', 1)})" for m in monsters[:3])
            if len(monsters) > 3: summary += f" + altri {len(monsters)-3}"
            self.tree_enc.insert("", tk.END, iid=str(idx), values=(
                enc.get("name", "Incontro"),
                enc.get("act", "Atto 1"),
                str(tot_count),
                summary,
                enc.get("description", "")
            ))

    def add_encounter_dialog(self):
        def on_saved(data):
            self.campaign.encounters.append(data)
            self.refresh_encounters()
        dlg = CampaignEncounterDialog(self, on_save_callback=on_saved)
        dlg.wait_window()

    def edit_encounter_dialog(self):
        sel = self.tree_enc.selection()
        if not sel: return
        idx = int(sel[0])
        def on_saved(data):
            self.campaign.encounters[idx] = data
            self.refresh_encounters()
        dlg = CampaignEncounterDialog(self, encounter_data=self.campaign.encounters[idx], on_save_callback=on_saved)
        dlg.wait_window()

    def remove_encounter(self):
        sel = self.tree_enc.selection()
        if not sel: return
        idx = int(sel[0])
        self.campaign.encounters.pop(idx)
        self.refresh_encounters()

    def deploy_selected_encounter(self):
        sel = self.tree_enc.selection()
        if not sel: return
        idx = int(sel[0])
        enc = self.campaign.encounters[idx]
        monsters = enc.get("monsters", [])
        if not monsters:
            messagebox.showwarning("Incontro Vuoto", "Questo incontro non contiene mostri.", parent=self)
            return
            
        added = []
        for m in monsters:
            for i in range(m.get("count", 1)):
                name = m.get("name", "Mostro")
                if m.get("count", 1) > 1:
                    name = f"{name} {i+1}"
                # Evita duplicati di nome
                base_name = name
                cnt = 1
                while self.game_state.find_player(name):
                    cnt += 1
                    name = f"{base_name} ({cnt})"
                    
                npc = Player(name=name)
                npc.hp = m.get("hp", 15)
                npc.max_hp = m.get("hp", 15)
                attrs = extract_and_normalize_attributes(m.get("attributes"), m.get("name", name))
                dex_val = attrs.get("DES", 10)
                npc.initiative = m.get("initiative") if m.get("initiative") is not None else (dex_val - 10) // 2
                ac = normalize_ac_value(m.get("ac", m.get("armor_class", 10)))
                speed_val, speed_disp, speed_unit = normalize_speed_value(m.get("speed", 30))
                npc.speed = speed_val
                npc.speed_unit = speed_unit
                npc.full_sheet = {
                    "name": npc.name,
                    "char_class": "Mostro/NPC",
                    "level": 1,
                    "hp_current": npc.hp,
                    "hp_max": npc.max_hp,
                    "ac": ac,
                    "speed": speed_val,
                    "speed_display": speed_disp,
                    "speed_unit": speed_unit,
                    "attributes": attrs,
                    "cr": str(m.get("cr", "1")),
                    "actions": m.get("actions", []),
                    "features": m.get("features", [])
                }
                self.game_state.add_player(npc)
                broadcast(self.game_state, make_player_joined(npc.to_dict()))
                added.append(npc.name)
                
        self.game_state._trigger_gui_update()
        broadcast(self.game_state, make_chat_broadcast("DM", f"⚡ Incontro '{enc.get('name')}' schierato sulla mappa! ({len(added)} creature)"))
        messagebox.showinfo("Incontro Schierato", f"Schierati con successo: {', '.join(added)}", parent=self)

    # -------------------------------------------------------------
    # TAB 4: MISSIONI & STORIA
    # -------------------------------------------------------------
    def build_tab_quests(self, parent):
        top_row = tk.Frame(parent, bg=BG_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(top_row, text="Registro Missioni della Campagna", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        ttk.Button(top_row, text="+ Nuova Missione", command=self.add_quest_dialog, style="Primary.TButton").pack(side=tk.RIGHT)
        
        tree_frame = tk.Frame(parent, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        cols = ("Titolo", "Capitolo", "Ricompensa XP", "Ricompensa MO", "Descrizione")
        self.tree_quests = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        self.tree_quests.heading("Titolo", text="Titolo Missione")
        self.tree_quests.heading("Capitolo", text="Capitolo / Atto")
        self.tree_quests.heading("Ricompensa XP", text="XP")
        self.tree_quests.heading("Ricompensa MO", text="Monete Oro")
        self.tree_quests.heading("Descrizione", text="Obiettivi e Dettagli")
        
        self.tree_quests.column("Titolo", width=200)
        self.tree_quests.column("Capitolo", width=120)
        self.tree_quests.column("Ricompensa XP", width=80, anchor="center")
        self.tree_quests.column("Ricompensa MO", width=90, anchor="center")
        self.tree_quests.column("Descrizione", width=340)
        
        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_quests.yview)
        self.tree_quests.configure(yscrollcommand=sb.set)
        self.tree_quests.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        ctrl_row = tk.Frame(parent, bg=BG_COLOR)
        ctrl_row.pack(fill=tk.X)
        ttk.Button(ctrl_row, text="✏️ Modifica Missione", command=self.edit_quest_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(ctrl_row, text="🗑️ Rimuovi Missione", command=self.remove_quest).pack(side=tk.LEFT, padx=(0, 6))
        
        self.refresh_quests()

    def refresh_quests(self):
        for item in self.tree_quests.get_children():
            self.tree_quests.delete(item)
        for idx, q in enumerate(self.campaign.quests):
            rew = q.get("rewards", {})
            if isinstance(rew, dict):
                xp_val = str(rew.get("xp", q.get("xp", 100)))
                gp_val = str(rew.get("gp", 25))
            else:
                xp_val = str(q.get("xp", 100))
                gp_val = str(rew) if rew else "0"
            self.tree_quests.insert("", tk.END, iid=str(idx), values=(
                q.get("title", "Missione"),
                q.get("chapter", q.get("act", "Atto 1")),
                xp_val,
                gp_val,
                q.get("description", "")
            ))

    def add_quest_dialog(self):
        title = simpledialog.askstring("Nuova Missione", "Titolo della missione:", parent=self)
        if not title or not title.strip(): return
        chapter = simpledialog.askstring("Capitolo", "Capitolo / Atto:", initialvalue="Atto 1", parent=self) or "Atto 1"
        desc = simpledialog.askstring("Descrizione", "Obiettivo e informazioni:", parent=self) or ""
        xp = simpledialog.askinteger("Ricompensa XP", "XP:", initialvalue=150, minvalue=0, parent=self) or 150
        gp = simpledialog.askinteger("Ricompensa Oro", "Monete d'Oro (MO):", initialvalue=50, minvalue=0, parent=self) or 50
        self.campaign.add_quest(title.strip(), desc.strip(), chapter.strip(), {"xp": xp, "gp": gp})
        self.refresh_quests()

    def edit_quest_dialog(self):
        sel = self.tree_quests.selection()
        if not sel: return
        idx = int(sel[0])
        q = self.campaign.quests[idx]
        title = simpledialog.askstring("Modifica Missione", "Titolo:", initialvalue=q.get("title"), parent=self)
        if not title: return
        q["title"] = title.strip()
        q["chapter"] = simpledialog.askstring("Capitolo", "Capitolo:", initialvalue=q.get("chapter"), parent=self) or "Atto 1"
        q["description"] = simpledialog.askstring("Descrizione", "Descrizione:", initialvalue=q.get("description"), parent=self) or ""
        self.refresh_quests()

    def remove_quest(self):
        sel = self.tree_quests.selection()
        if not sel: return
        idx = int(sel[0])
        self.campaign.quests.pop(idx)
        self.refresh_quests()

    # -------------------------------------------------------------
    # TAB 5: PNG & FAZIONI
    # -------------------------------------------------------------
    def build_tab_npcs(self, parent):
        top_row = tk.Frame(parent, bg=BG_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(top_row, text="Personaggi Non Giocanti (PNG) Chiave", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        btn_box = tk.Frame(top_row, bg=BG_COLOR)
        btn_box.pack(side=tk.RIGHT)
        ttk.Button(btn_box, text="📖 Aggiungi da Compendio...", command=self.add_npc_from_compendium, style="Gold.TButton").pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_box, text="+ Nuovo PNG Manuale", command=self.add_npc_dialog, style="Primary.TButton").pack(side=tk.RIGHT)
        
        tree_frame = tk.Frame(parent, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        cols = ("Nome", "Ruolo", "Fazione", "HP", "CA", "Note Private")
        self.tree_npcs = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        self.tree_npcs.heading("Nome", text="Nome PNG")
        self.tree_npcs.heading("Ruolo", text="Ruolo / Professione")
        self.tree_npcs.heading("Fazione", text="Fazione / Allineamento")
        self.tree_npcs.heading("HP", text="HP")
        self.tree_npcs.heading("CA", text="CA")
        self.tree_npcs.heading("Note Private", text="Note DM & Segreti")
        
        self.tree_npcs.column("Nome", width=180)
        self.tree_npcs.column("Ruolo", width=160)
        self.tree_npcs.column("Fazione", width=130)
        self.tree_npcs.column("HP", width=60, anchor="center")
        self.tree_npcs.column("CA", width=60, anchor="center")
        self.tree_npcs.column("Note Private", width=280)
        
        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_npcs.yview)
        self.tree_npcs.configure(yscrollcommand=sb.set)
        self.tree_npcs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        ctrl_row = tk.Frame(parent, bg=BG_COLOR)
        ctrl_row.pack(fill=tk.X)
        ttk.Button(ctrl_row, text="✏️ Modifica PNG", command=self.edit_npc_dialog).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(ctrl_row, text="🗑️ Rimuovi PNG", command=self.remove_npc).pack(side=tk.LEFT, padx=(0, 6))
        
        if self.game_state:
            ttk.Button(ctrl_row, text="⚡ Spawna Token sulla Mappa", command=self.spawn_selected_npc, style="Gold.TButton").pack(side=tk.RIGHT)
            
        self.refresh_npcs()

    def refresh_npcs(self):
        for item in self.tree_npcs.get_children():
            self.tree_npcs.delete(item)
        for idx, npc in enumerate(self.campaign.npcs):
            self.tree_npcs.insert("", tk.END, iid=str(idx), values=(
                npc.get("name", "PNG"),
                npc.get("role", "Comune"),
                npc.get("faction", "Neutrale"),
                str(npc.get("hp", 20)),
                str(npc.get("ac", 12)),
                npc.get("notes", "")
            ))

    def add_npc_dialog(self):
        name = simpledialog.askstring("Nuovo PNG", "Nome del PNG:", parent=self)
        if not name or not name.strip(): return
        role = simpledialog.askstring("Ruolo", "Ruolo o mestiere (es. 'Locandiere', 'Capoguardia'):", parent=self) or "Cittadino"
        faction = simpledialog.askstring("Fazione", "Fazione (Alleato, Nemico, Neutrale):", initialvalue="Neutrale", parent=self) or "Neutrale"
        hp = simpledialog.askinteger("HP", "Punti ferita:", initialvalue=20, minvalue=1, parent=self) or 20
        ac = simpledialog.askinteger("Classe Armatura", "CA:", initialvalue=12, minvalue=1, parent=self) or 12
        notes = simpledialog.askstring("Note DM", "Note DM, personalità e segreti:", parent=self) or ""
        self.campaign.add_npc(name.strip(), role.strip(), hp, ac, notes.strip(), faction.strip())
        self.refresh_npcs()

    def edit_npc_dialog(self):
        sel = self.tree_npcs.selection()
        if not sel: return
        idx = int(sel[0])
        npc = self.campaign.npcs[idx]
        name = simpledialog.askstring("Modifica PNG", "Nome:", initialvalue=npc.get("name"), parent=self)
        if not name: return
        npc["name"] = name.strip()
        npc["role"] = simpledialog.askstring("Ruolo", "Ruolo:", initialvalue=npc.get("role"), parent=self) or "Cittadino"
        npc["faction"] = simpledialog.askstring("Fazione", "Fazione:", initialvalue=npc.get("faction"), parent=self) or "Neutrale"
        npc["notes"] = simpledialog.askstring("Note DM", "Note:", initialvalue=npc.get("notes"), parent=self) or ""
        self.refresh_npcs()

    def remove_npc(self):
        sel = self.tree_npcs.selection()
        if not sel: return
        idx = int(sel[0])
        self.campaign.npcs.pop(idx)
        self.refresh_npcs()

    def spawn_selected_npc(self):
        sel = self.tree_npcs.selection()
        if not sel: return
        idx = int(sel[0])
        npc_data = self.campaign.npcs[idx]
        name = npc_data.get("name", "PNG")
        
        # Evita conflitti
        orig_name = name
        c = 1
        while self.game_state.find_player(name):
            c += 1
            name = f"{orig_name} ({c})"
            
        p = Player(name=name)
        p.hp = npc_data.get("hp", 20)
        p.max_hp = npc_data.get("hp", 20)
        p.is_party_member = (npc_data.get("faction") == "Alleato")
        attrs = extract_and_normalize_attributes(npc_data.get("attributes"), name)
        dex_val = attrs.get("DES", 10)
        p.initiative = npc_data.get("initiative") if npc_data.get("initiative") is not None else (dex_val - 10) // 2
        ac = normalize_ac_value(npc_data.get("ac", npc_data.get("armor_class", 10)))
        speed_val, speed_disp, speed_unit = normalize_speed_value(npc_data.get("speed", 30))
        p.speed = speed_val
        p.speed_unit = speed_unit
        p.full_sheet = {
            "name": p.name,
            "char_class": npc_data.get("role", "PNG"),
            "level": 1,
            "hp_current": p.hp,
            "hp_max": p.max_hp,
            "ac": ac,
            "speed": speed_val,
            "speed_display": speed_disp,
            "speed_unit": speed_unit,
            "attributes": attrs,
            "actions": npc_data.get("actions", []),
            "features": npc_data.get("features", [])
        }
        self.game_state.add_player(p)
        broadcast(self.game_state, make_player_joined(p.to_dict()))
        self.game_state._trigger_gui_update()
        broadcast(self.game_state, make_chat_broadcast("DM", f"🎭 PNG '{name}' schierato sulla mappa."))
        messagebox.showinfo("PNG Schierato", f"PNG '{name}' aggiunto alla sessione!", parent=self)

    # -------------------------------------------------------------
    # TAB 6: HANDOUTS
    # -------------------------------------------------------------
    def build_tab_handouts(self, parent):
        top_row = tk.Frame(parent, bg=BG_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(top_row, text="Handouts, Documenti e Indizi Grafici", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        btn_box = tk.Frame(top_row, bg=BG_COLOR)
        btn_box.pack(side=tk.RIGHT)
        ttk.Button(btn_box, text="📖 Aggiungi da Compendio...", command=self.add_handout_from_compendium, style="Gold.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_box, text="+ Handout Testuale", command=self.add_text_handout, style="Primary.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_box, text="+ Handout Immagine", command=self.add_image_handout, style="Primary.TButton").pack(side=tk.LEFT, padx=3)
        
        tree_frame = tk.Frame(parent, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        cols = ("Titolo", "Tipo", "Dettaglio / Contenuto")
        self.tree_handouts = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        self.tree_handouts.heading("Titolo", text="Titolo")
        self.tree_handouts.heading("Tipo", text="Tipo")
        self.tree_handouts.heading("Dettaglio / Contenuto", text="Contenuto o Percorso")
        
        self.tree_handouts.column("Titolo", width=220)
        self.tree_handouts.column("Tipo", width=100, anchor="center")
        self.tree_handouts.column("Dettaglio / Contenuto", width=480)
        
        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_handouts.yview)
        self.tree_handouts.configure(yscrollcommand=sb.set)
        self.tree_handouts.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        ctrl_row = tk.Frame(parent, bg=BG_COLOR)
        ctrl_row.pack(fill=tk.X)
        ttk.Button(ctrl_row, text="👁 Visualizza / Modifica", command=self.view_handout).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(ctrl_row, text="🗑️ Rimuovi Handout", command=self.remove_handout).pack(side=tk.LEFT, padx=(0, 6))
        
        if self.game_state:
            ttk.Button(ctrl_row, text="📢 Rivela ai Giocatori Connessi", command=self.broadcast_selected_handout, style="Gold.TButton").pack(side=tk.RIGHT)
            
        self.refresh_handouts()

    def refresh_handouts(self):
        for item in self.tree_handouts.get_children():
            self.tree_handouts.delete(item)
        for idx, h in enumerate(self.campaign.handouts):
            t = "Immagine" if h.get("image_path") else "Testo"
            detail = h.get("image_path") if t == "Immagine" else (h.get("content", "")[:70] + "...")
            self.tree_handouts.insert("", tk.END, iid=str(idx), values=(
                h.get("title", "Handout"),
                t,
                detail
            ))

    def add_text_handout(self):
        title = simpledialog.askstring("Nuovo Handout Testuale", "Titolo del documento:", parent=self)
        if not title or not title.strip(): return
        
        # Finestra di input multiriga
        dlg = tk.Toplevel(self)
        dlg.title(f"Contenuto: {title}")
        dlg.minsize(500, 350)
        dlg.transient(self)
        dlg.grab_set()
        apply_modern_window_style(dlg)
        dlg.configure(bg=BG_COLOR)
        
        tk.Label(dlg, text=f"Scrivi il contenuto di '{title}':", font=FONT_BOLD, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=15, pady=(12, 4))
        txt = scrolledtext.ScrolledText(dlg, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=FONT_MAIN, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))
        
        def save_h():
            content = txt.get("1.0", tk.END).strip()
            self.campaign.add_handout(title.strip(), content=content)
            self.refresh_handouts()
            dlg.destroy()
            
        b_box = tk.Frame(dlg, bg=BG_COLOR)
        b_box.pack(fill=tk.X, padx=15, pady=(0, 12))
        ttk.Button(b_box, text="Salva Handout", command=save_h, style="Success.TButton").pack(side=tk.RIGHT)
        ttk.Button(b_box, text="Annulla", command=dlg.destroy).pack(side=tk.RIGHT, padx=6)

    def add_image_handout(self):
        title = simpledialog.askstring("Nuovo Handout Immagine", "Titolo dell'immagine:", parent=self)
        if not title or not title.strip(): return
        
        img_file = filedialog.askopenfilename(
            title="Seleziona Immagine Handout",
            filetypes=[("Immagini", "*.png;*.jpg;*.jpeg;*.gif;*.bmp"), ("Tutti i file", "*.*")],
            parent=self
        )
        if not img_file: return
        self.campaign.add_handout(title.strip(), image_path=img_file)
        self.refresh_handouts()

    def view_handout(self):
        sel = self.tree_handouts.selection()
        if not sel: return
        idx = int(sel[0])
        h = self.campaign.handouts[idx]
        
        dlg = tk.Toplevel(self)
        dlg.title(f"Handout: {h.get('title')}")
        dlg.minsize(500, 350)
        dlg.transient(self)
        dlg.grab_set()
        apply_modern_window_style(dlg)
        dlg.configure(bg=BG_COLOR)
        
        tk.Label(dlg, text=h.get("title", ""), font=("Georgia", 14, "bold"), bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=15, pady=(12, 6))
        
        if h.get("image_path"):
            tk.Label(dlg, text=f"File immagine: {h.get('image_path')}", font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w", padx=15, pady=(0, 8))
        else:
            txt = scrolledtext.ScrolledText(dlg, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=FONT_MAIN, wrap=tk.WORD)
            txt.insert("1.0", h.get("content", ""))
            txt.configure(state=tk.DISABLED)
            txt.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 12))
            
        ttk.Button(dlg, text="Chiudi", command=dlg.destroy).pack(pady=(0, 12))

    def remove_handout(self):
        sel = self.tree_handouts.selection()
        if not sel: return
        idx = int(sel[0])
        self.campaign.handouts.pop(idx)
        self.refresh_handouts()

    def broadcast_selected_handout(self):
        sel = self.tree_handouts.selection()
        if not sel: return
        idx = int(sel[0])
        h = self.campaign.handouts[idx]
        
        import base64
        title = h.get("title", "Documento")
        content = h.get("content")
        img_b64 = None
        img_path = h.get("image_path")
        if img_path and os.path.exists(img_path):
            try:
                with open(img_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                print(f"[CAMPAIGN] Errore lettura immagine handout: {e}")
                
        broadcast(self.game_state, make_handout_broadcast(title, img_b64, content))
        messagebox.showinfo("Handout Inviato", f"'{title}' condiviso con tutti i giocatori!", parent=self)

    # -------------------------------------------------------------
    # SALVATAGGIO & APPLICAZIONE
    # -------------------------------------------------------------
    def sync_campaign_data(self):
        """Sincronizza le modifiche della UI nell'oggetto Campaign."""
        if hasattr(self, "studio_frame") and self.studio_frame:
            try:
                self.studio_frame.sync_text_to_canvas()
            except Exception as e:
                print(f"[CAMPAIGN] Errore sync studio_frame: {e}")
        self.campaign.name = self.ent_title.get().strip() or "Campagna Senza Nome"
        self.campaign.level_range = self.ent_level.get().strip() or "1-3"
        self.campaign.start_weather = self.combo_weather.get() or "Sereno"
        try:
            self.campaign.start_date = {
                "year": int(self.sp_year.get()),
                "month": int(self.sp_month.get()),
                "day": int(self.sp_day.get()),
                "hour": int(self.sp_hour.get())
            }
        except ValueError:
            pass
        self.campaign.description = self.txt_synopsis.get("1.0", tk.END).strip()
        self.campaign.dm_notes = self.txt_dm_notes.get("1.0", tk.END).strip()

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not getattr(self, "is_fullscreen", False)
        try:
            self.attributes("-fullscreen", self.is_fullscreen)
            if hasattr(self, "btn_fs"):
                self.btn_fs.config(text="🗗 Finestra" if self.is_fullscreen else "⛶ Schermo Intero")
        except Exception:
            pass

    def exit_fullscreen(self, event=None):
        if getattr(self, "is_fullscreen", False):
            self.is_fullscreen = False
            try:
                self.attributes("-fullscreen", False)
                if hasattr(self, "btn_fs"):
                    self.btn_fs.config(text="⛶ Schermo Intero")
            except Exception:
                pass

    def save_campaign(self):
        self.sync_campaign_data()
        try:
            folder = self.campaign.save()
            messagebox.showinfo("Campagna Salvata", f"Campagna '{self.campaign.name}' salvata con successo in:\n{folder}", parent=self)
            if self.on_save_callback:
                self.on_save_callback(self.campaign)
        except Exception as e:
            messagebox.showerror("Errore Salvataggio", f"Impossibile salvare la campagna: {e}", parent=self)

    # -------------------------------------------------------------
    # METODI IMPORTAZIONE DAL COMPENDIO 5E
    # -------------------------------------------------------------
    def _import_starter_kit_data(self, item_data: Dict[str, Any], category: str):
        name = item_data.get("name") or item_data.get("title", "Nuovo Oggetto")
        raw_cat = ""
        eq_cat = item_data.get("equipment_category")
        if isinstance(eq_cat, dict):
            raw_cat = eq_cat.get("name", "")
        elif isinstance(eq_cat, str):
            raw_cat = eq_cat
        if not raw_cat:
            raw_cat = item_data.get("type", category or "Equipaggiamento")

        cat_lower = (str(raw_cat) + " " + str(category)).lower()
        if "weapon" in cat_lower or "arma" in cat_lower:
            item_type = "Arma"
        elif "armor" in cat_lower or "armatura" in cat_lower:
            item_type = "Armatura"
        elif "shield" in cat_lower or "scudo" in cat_lower:
            item_type = "Scudo"
        elif "potion" in cat_lower or "pozione" in cat_lower or "consumab" in cat_lower:
            item_type = "Consumabile"
        elif "ammunition" in cat_lower or "munizion" in cat_lower:
            item_type = "Munizioni"
        elif "magic" in cat_lower or "magico" in cat_lower:
            item_type = "Magico"
        elif "tool" in cat_lower or "strument" in cat_lower:
            item_type = "Strumenti"
        else:
            item_type = "Equipaggiamento"

        try:
            weight = float(item_data.get("weight", 1.0) or 0.0)
        except (ValueError, TypeError):
            weight = 0.0

        desc_parts = []
        if item_data.get("damage"):
            dmg = item_data["damage"]
            dice = dmg.get("damage_dice", "")
            dtype = dmg.get("damage_type", {}).get("name", "") if isinstance(dmg.get("damage_type"), dict) else str(dmg.get("damage_type", ""))
            if dice:
                desc_parts.append(f"Danno: {dice} {dtype}".strip())
        if item_data.get("armor_class"):
            ac_info = item_data["armor_class"]
            base_ac = ac_info.get("base", 10) if isinstance(ac_info, dict) else ac_info
            desc_parts.append(f"CA: {base_ac}")
        if item_data.get("properties"):
            props = [p.get("name") for p in item_data["properties"] if isinstance(p, dict) and p.get("name")]
            if props:
                desc_parts.append(f"Proprietà: {', '.join(props)}")

        raw_desc = item_data.get("desc", "") or item_data.get("content", "")
        if isinstance(raw_desc, list):
            raw_desc = " ".join(str(d) for d in raw_desc)
        if raw_desc:
            desc_parts.append(str(raw_desc).strip())

        full_desc = " | ".join(desc_parts) if desc_parts else "Oggetto dal Compendio 5e"

        new_item = {
            "name": name,
            "type": item_type,
            "qty": 1,
            "weight": weight,
            "desc": full_desc
        }
        self.campaign.starter_kit.append(new_item)
        if hasattr(self, "lbl_kit_count") and self.lbl_kit_count:
            self.lbl_kit_count.config(text=self._get_kit_summary_text())

    def add_starter_kit_from_compendium(self):
        try:
            from server.compendium_ui import CompendiumDialog
            dlg = CompendiumDialog(
                self,
                on_import_callback=self._import_starter_kit_data,
                is_dm=True,
                initial_category="Equipaggiamento",
                action_label="➕ Aggiungi al Kit"
            )
            dlg.grab_set()
        except Exception as e:
            messagebox.showerror("Errore Compendio", f"Impossibile aprire il compendio: {e}", parent=self)

    def _import_npc_data(self, item_data: Dict[str, Any], category: str):
        name = item_data.get("name") or item_data.get("title", "PNG Compendio")
        orig_name = name
        cnt = 1
        while any(n.get("name") == name for n in self.campaign.npcs):
            cnt += 1
            name = f"{orig_name} ({cnt})"

        hp = item_data.get("hit_points", item_data.get("hp", 20))
        ac_val = item_data.get("armor_class", item_data.get("ac", 12))
        ac = normalize_ac_value(ac_val)

        role = item_data.get("type", "Creatura/PNG")
        if item_data.get("subtype"):
            role = f"{role} ({item_data.get('subtype')})"

        notes_parts = []
        align = item_data.get("alignment", "")
        if align:
            notes_parts.append(f"Allineamento: {align}")
        cr = item_data.get("challenge_rating", item_data.get("cr"))
        if cr is not None:
            notes_parts.append(f"Grado Sfida (CR): {cr}")
        senses = item_data.get("senses", "")
        if senses:
            notes_parts.append(f"Sensi: {senses}")
        langs = item_data.get("languages", "")
        if langs:
            notes_parts.append(f"Linguaggi: {langs}")

        acts = item_data.get("actions", [])
        if acts:
            act_names = [a.get("name") for a in acts if isinstance(a, dict) and a.get("name")]
            if act_names:
                notes_parts.append(f"Azioni: {', '.join(act_names[:5])}")

        notes_str = " | ".join(notes_parts)

        npc_entry = {
            "name": name,
            "role": role,
            "hp": hp,
            "ac": ac,
            "faction": "Neutrale",
            "notes": notes_str,
            "attributes": extract_and_normalize_attributes(item_data.get("attributes"), name),
            "actions": acts,
            "features": item_data.get("special_abilities", item_data.get("features", [])),
            "speed": item_data.get("speed", 30),
            "cr": str(cr or "1")
        }
        self.campaign.npcs.append(npc_entry)
        self.refresh_npcs()

    def add_npc_from_compendium(self):
        try:
            from server.compendium_ui import CompendiumDialog
            dlg = CompendiumDialog(
                self,
                on_import_callback=self._import_npc_data,
                is_dm=True,
                initial_category="Mostri",
                action_label="➕ Aggiungi ai PNG Campagna"
            )
            dlg.grab_set()
        except Exception as e:
            messagebox.showerror("Errore Compendio", f"Impossibile aprire il compendio: {e}", parent=self)

    def _import_handout_data(self, item_data: Dict[str, Any], category: str):
        name = item_data.get("name") or item_data.get("title", "Documento Compendio")
        title = name
        c = 1
        while any(h.get("title") == title for h in self.campaign.handouts):
            c += 1
            title = f"{name} ({c})"

        lines = [f"📜 {title.upper()}", f"Categoria: {category}"]
        if item_data.get("type"):
            lines.append(f"Tipo: {item_data.get('type')}")
        if item_data.get("rarity"):
            lines.append(f"Rarità: {item_data.get('rarity')}")
        if item_data.get("level") is not None:
            lines.append(f"Livello: {item_data.get('level')}")
        if item_data.get("school"):
            sch = item_data['school'].get('name') if isinstance(item_data['school'], dict) else item_data['school']
            lines.append(f"Scuola: {sch}")
        if item_data.get("casting_time"):
            lines.append(f"Tempo di lancio: {item_data.get('casting_time')}")
        if item_data.get("range"):
            lines.append(f"Gittata: {item_data.get('range')}")
        if item_data.get("duration"):
            lines.append(f"Durata: {item_data.get('duration')}")
        if item_data.get("damage"):
            dmg = item_data["damage"]
            dice = dmg.get("damage_dice", "")
            dtype = dmg.get("damage_type", {}).get("name", "") if isinstance(dmg.get("damage_type"), dict) else str(dmg.get("damage_type", ""))
            if dice:
                lines.append(f"Danno: {dice} {dtype}".strip())
        if item_data.get("armor_class"):
            ac_info = item_data["armor_class"]
            base_ac = ac_info.get("base", 10) if isinstance(ac_info, dict) else ac_info
            lines.append(f"Classe Armatura: {base_ac}")

        if item_data.get("manual_name"):
            lines.insert(2, f"Fonte Manuale: {item_data.get('manual_name')} {item_data.get('page_ref', '')}".strip())
        desc = item_data.get("desc", "") or item_data.get("content", "")
        if isinstance(desc, list):
            desc = "\n\n".join(str(d) for d in desc)
        if desc:
            lines.append(f"\n{desc}")

        full_content = "\n".join(lines).strip()
        self.campaign.add_handout(title, content=full_content)
        self.refresh_handouts()

    def add_handout_from_compendium(self):
        try:
            from server.compendium_ui import CompendiumDialog
            dlg = CompendiumDialog(
                self,
                on_import_callback=self._import_handout_data,
                is_dm=True,
                initial_category="Oggetti Magici",
                action_label="➕ Aggiungi agli Handout"
            )
            dlg.grab_set()
        except Exception as e:
            messagebox.showerror("Errore Compendio", f"Impossibile aprire il compendio: {e}", parent=self)

    def open_global_compendium(self):
        try:
            from server.compendium_ui import CompendiumDialog
            def _on_global_imported(item_data, category):
                cat_lower = category.lower() if category else ""
                cur_tab = ""
                try:
                    cur_tab = self.notebook.tab(self.notebook.select(), "text")
                except Exception:
                    pass

                if "incontri" in cur_tab.lower() or ("mostri" in cat_lower and "png" not in cur_tab.lower()):
                    name = item_data.get("name", "Mostro")
                    hp = item_data.get("hit_points", 15)
                    dex = item_data.get("dexterity", 10)
                    init_mod = (dex - 10) // 2
                    xp = item_data.get("xp", 50)
                    if not self.campaign.encounters:
                        self.campaign.add_encounter("Incontro Compendio", [])
                    self.campaign.encounters[-1]["monsters"].append({
                        "name": name, "count": 1, "hp": hp, "initiative": init_mod, "xp": xp
                    })
                    self.refresh_encounters()
                    messagebox.showinfo("Incontro Aggiornato", f"'{name}' aggiunto all'ultimo incontro preparato!", parent=self)
                elif "png" in cur_tab.lower():
                    self._import_npc_data(item_data, category)
                elif "handout" in cur_tab.lower() or "regole" in cat_lower:
                    self._import_handout_data(item_data, category)
                elif "generale" in cur_tab.lower() or any(k in cat_lower for k in ["equipaggiamento", "armi", "pozioni", "oggetti"]):
                    self._import_starter_kit_data(item_data, category)
                else:
                    self._import_handout_data(item_data, category)

            dlg = CompendiumDialog(self, on_import_callback=_on_global_imported, is_dm=True, action_label="➕ Importa nella Campagna")
            dlg.grab_set()
        except Exception as e:
            messagebox.showerror("Errore Compendio", f"Impossibile aprire il compendio: {e}", parent=self)

    def apply_to_running_game(self):
        if not self.game_state:
            return
        self.sync_campaign_data()
        self.campaign.apply_to_game_state(self.game_state)
        messagebox.showinfo("Applicato", f"La campagna '{self.campaign.name}' è ora attiva nella sessione corrente!", parent=self)


class CampaignSelectorDialog(tk.Toplevel):
    """Dialogo per visualizzare, scegliere o creare campagne prima di iniziare la sessione."""
    def __init__(self, master, on_select_callback: Callable[[Campaign], None], on_edit_callback: Optional[Callable[[Campaign], None]] = None):
        super().__init__(master)
        self.on_select_callback = on_select_callback
        self.on_edit_callback = on_edit_callback
        
        self.title("D&D OmniCompanion • Seleziona Campagna")
        self.minsize(820, 520)
        self.transient(master)
        self.grab_set()
        apply_modern_window_style(self)
        self.configure(bg=BG_COLOR)
        
        self.available_campaigns: List[Dict[str, Any]] = []
        self.selected_campaign: Optional[Campaign] = None
        
        self.setup_ui()
        self.refresh_campaigns()

    def setup_ui(self):
        container = tk.Frame(self, bg=BG_COLOR, padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Header
        hdr = tk.Frame(container, bg=BG_COLOR)
        hdr.pack(fill=tk.X, pady=(0, 10))
        tk.Label(hdr, text="📚 Libreria Campagne Preparate", font=("Georgia", 16, "bold"), bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
        tk.Label(hdr, text="Seleziona una campagna esistente, preparane una nuova offline oppure modifica i contenuti",
                 font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w")
        
        # Main Split Frame
        main_split = tk.Frame(container, bg=BG_COLOR)
        main_split.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        main_split.columnconfigure(0, weight=1)
        main_split.columnconfigure(1, weight=1)
        main_split.rowconfigure(0, weight=1)
        
        # Left: Treeview elenco campagne
        left_card = tk.Frame(main_split, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=10)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        
        tk.Label(left_card, text="Campagne Disponibili", font=FONT_HEADER, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(0, 6))
        
        tree_box = tk.Frame(left_card, bg=SURFACE_COLOR)
        tree_box.pack(fill=tk.BOTH, expand=True)
        
        cols = ("Nome", "Livello", "Scene", "Incontri", "Quest")
        self.tree_camps = ttk.Treeview(tree_box, columns=cols, show="headings", height=10)
        self.tree_camps.heading("Nome", text="Nome Campagna")
        self.tree_camps.heading("Livello", text="Livello")
        self.tree_camps.heading("Scene", text="Scene")
        self.tree_camps.heading("Incontri", text="Incontri")
        self.tree_camps.heading("Quest", text="Quest")
        
        self.tree_camps.column("Nome", width=170)
        self.tree_camps.column("Livello", width=70, anchor="center")
        self.tree_camps.column("Scene", width=60, anchor="center")
        self.tree_camps.column("Incontri", width=65, anchor="center")
        self.tree_camps.column("Quest", width=60, anchor="center")
        
        sb = ttk.Scrollbar(tree_box, orient=tk.VERTICAL, command=self.tree_camps.yview)
        self.tree_camps.configure(yscrollcommand=sb.set)
        self.tree_camps.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree_camps.bind("<<TreeviewSelect>>", self.on_campaign_selected)
        
        l_btn_box = tk.Frame(left_card, bg=SURFACE_COLOR)
        l_btn_box.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(l_btn_box, text="+ Nuova Campagna", command=self.create_new_campaign, style="Primary.TButton").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(l_btn_box, text="🗑️ Elimina", command=self.delete_campaign).pack(side=tk.LEFT)
        ttk.Button(l_btn_box, text="🔄 Ricarica", command=self.refresh_campaigns).pack(side=tk.RIGHT)
        
        # Right: Dettaglio / Anteprima
        right_card = tk.Frame(main_split, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=14, pady=12)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        
        self.lbl_det_title = tk.Label(right_card, text="Nessuna campagna selezionata", font=("Georgia", 13, "bold"), bg=SURFACE_COLOR, fg=ACCENT_GOLD)
        self.lbl_det_title.pack(anchor="w", pady=(0, 2))
        
        self.lbl_det_meta = tk.Label(right_card, text="", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
        self.lbl_det_meta.pack(anchor="w", pady=(0, 8))
        
        tk.Label(right_card, text="Sinossi & Ambientazione:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        self.txt_det_desc = scrolledtext.ScrolledText(right_card, height=10, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_SMALL,
                                                     relief="flat", highlightbackground=BORDER_COLOR, highlightthickness=1, wrap=tk.WORD)
        self.txt_det_desc.pack(fill=tk.BOTH, expand=True, pady=(4, 10))
        self.txt_det_desc.configure(state=tk.DISABLED)
        
        ttk.Button(right_card, text="✏️ Modifica Contenuti Campagna", command=self.edit_selected_campaign).pack(fill=tk.X)
        
        # Bottom Actions Bar
        bottom_row = tk.Frame(container, bg=BG_COLOR)
        bottom_row.pack(fill=tk.X)
        
        self.btn_play = ttk.Button(bottom_row, text="🚀 Avvia Partita con Questa Campagna", command=self.confirm_and_play, style="Gold.TButton")
        self.btn_play.pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(bottom_row, text="Annulla", command=self.destroy).pack(side=tk.RIGHT)

    def refresh_campaigns(self):
        for it in self.tree_camps.get_children():
            self.tree_camps.delete(it)
        self.available_campaigns = get_available_campaigns()
        for idx, c_info in enumerate(self.available_campaigns):
            self.tree_camps.insert("", tk.END, iid=str(idx), values=(
                c_info.get("name", "Campagna"),
                c_info.get("level_range", "1-3"),
                str(c_info.get("scenes_count", 0)),
                str(c_info.get("encounters_count", 0)),
                str(c_info.get("quests_count", 0))
            ))
        if self.available_campaigns:
            self.tree_camps.selection_set("0")
            self.on_campaign_selected(None)

    def on_campaign_selected(self, event):
        sel = self.tree_camps.selection()
        if not sel: return
        idx = int(sel[0])
        c_info = self.available_campaigns[idx]
        try:
            self.selected_campaign = Campaign.load(c_info["folder_path"])
            self.lbl_det_title.config(text=f"🏰 {self.selected_campaign.name}")
            sdate = self.selected_campaign.start_date or {}
            harptos_months = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
            m_idx = sdate.get("month", 1)
            m_name = harptos_months[m_idx] if 1 <= m_idx <= 12 else f"Mese {m_idx}"
            date_str = f"📅 {sdate.get('day', 1)} {m_name} {sdate.get('year', 1492)} CV (Ore {sdate.get('hour', 8):02d}:00)"
            self.lbl_det_meta.config(
                text=f"Livello: {self.selected_campaign.level_range} | {date_str} | Meteo: {self.selected_campaign.start_weather}\n"
                     f"Scene: {len(self.selected_campaign.scenes)} | Incontri: {len(self.selected_campaign.encounters)} | "
                     f"Quest: {len(self.selected_campaign.quests)} | PNG: {len(self.selected_campaign.npcs)}"
            )
            self.txt_det_desc.configure(state=tk.NORMAL)
            self.txt_det_desc.delete("1.0", tk.END)
            self.txt_det_desc.insert("1.0", self.selected_campaign.description or "Nessuna descrizione specificata.")
            self.txt_det_desc.configure(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile leggere la campagna: {e}", parent=self)

    def create_new_campaign(self):
        new_camp = Campaign(name="Nuova Campagna")
        def on_saved(saved_camp):
            self.refresh_campaigns()
        dlg = CampaignEditorDialog(self, campaign=new_camp, on_save_callback=on_saved)
        dlg.wait_window()

    def edit_selected_campaign(self):
        if not self.selected_campaign:
            messagebox.showwarning("Attenzione", "Seleziona prima una campagna.", parent=self)
            return
        def on_saved(saved_camp):
            self.refresh_campaigns()
        dlg = CampaignEditorDialog(self, campaign=self.selected_campaign, on_save_callback=on_saved)
        dlg.wait_window()

    def delete_campaign(self):
        sel = self.tree_camps.selection()
        if not sel: return
        idx = int(sel[0])
        c_info = self.available_campaigns[idx]
        name = c_info.get("name", "Campagna")
        if messagebox.askyesno("Elimina Campagna", f"Sei sicuro di voler eliminare la campagna '{name}' e tutti i suoi file?", parent=self):
            try:
                shutil.rmtree(c_info["folder_path"])
                messagebox.showinfo("Eliminata", f"Campagna '{name}' eliminata.", parent=self)
                self.refresh_campaigns()
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile eliminare la cartella: {e}", parent=self)

    def confirm_and_play(self):
        if not self.selected_campaign:
            messagebox.showwarning("Attenzione", "Seleziona una campagna prima di avviare.", parent=self)
            return
        camp = self.selected_campaign
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
        self.on_select_callback(camp)


