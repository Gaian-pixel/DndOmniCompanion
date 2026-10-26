import tkinter as tk
from tkinter import ttk, messagebox
import threading
import random
try:
    import requests
except ImportError:
    requests = None
import urllib.request
import json

from common.theme import apply_modern_window_style
from server.compendium_ui import CompendiumDialog
from common.srd_offline import (
    OfflineSRD,
    get_class_level_features_offline,
    get_all_spells_offline,
    SPELL_EN_TO_IT,
    STANDARD_5E_FEATS_CATALOG
)
from common.srd_subclasses_complete import ALL_OFFICIAL_SUBCLASSES

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
    "warlock": "warlock",
    "artefice": "artificer",
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
    "artificer": 8,
    "sorcerer": 6,
    "wizard": 6
}

# Livelli in cui le classi sbloccano l'Archetipo / Sottoclasse
SUBCLASS_LEVEL_MAP = {
    "cleric": 1,
    "sorcerer": 1,
    "warlock": 1,
    "wizard": 2,
    "druid": 2,
    "fighter": 3,
    "barbarian": 3,
    "rogue": 3,
    "bard": 3,
    "monk": 3,
    "paladin": 3,
    "ranger": 3,
    "artificer": 3,
}

# Livelli standard di Aumento Punteggi di Caratteristica (ASI)
ASI_LEVELS = {
    "default": [4, 8, 12, 16, 19],
    "fighter": [4, 6, 8, 12, 14, 16, 19],
    "rogue": [4, 8, 10, 12, 16, 19],
}


class LevelUpDialog(tk.Toplevel):
    def __init__(self, master, character, update_callback):
        super().__init__(master)
        self.title("Sali di Livello - Guida Ufficiale D&D 5e")
        self.geometry("740x700")
        self.minsize(660, 620)
        apply_modern_window_style(self)

        self.character = character
        self.update_callback = update_callback
        self.api_data = None
        self.new_features = []
        self.new_feature_details = {}
        self.selected_spells = []
        self.all_eligible_spells = []

        # Risolvi classe e dado vita
        raw_cls = (getattr(self.character, "char_class", "") or "").lower().strip()
        base_cls = raw_cls.split("(")[0].split("/")[0].strip()
        self.char_class_en = CLASS_MAP.get(base_cls, base_cls if base_cls in HIT_DICE_MAP else None)
        if not self.char_class_en:
            for k_it, k_en in CLASS_MAP.items():
                if k_it in base_cls or k_en in base_cls:
                    self.char_class_en = k_en
                    break
        if not self.char_class_en:
            self.char_class_en = "fighter"

        self.hit_die = HIT_DICE_MAP.get(self.char_class_en, 8)
        self.avg_hp = (self.hit_die // 2) + 1
        self.new_level = self.character.level + 1

        self.setup_ui()
        self.fetch_level_data()

    def setup_ui(self):
        # Header superiore
        header_frame = ttk.Frame(self, padding=(12, 10, 12, 6))
        header_frame.pack(fill=tk.X)

        title_lbl = ttk.Label(
            header_frame,
            text=f"✨ Sali di Livello: {self.character.name} (Livello {self.character.level} ➔ {self.new_level})",
            font=("Georgia", 14, "bold"),
            foreground="#D4AF37"
        )
        title_lbl.pack(side=tk.LEFT)

        sub_info = f"Classe: {self.character.char_class.title()} | Dado Vita: d{self.hit_die}"
        if getattr(self.character, "subclass", ""):
            sub_info += f" | {self.character.subclass}"
        ttk.Label(header_frame, text=sub_info, font=("Segoe UI", 9, "italic")).pack(side=tk.RIGHT)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # TAB 1: Salute e Dado Vita
        self.tab_health = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_health, text="❤️ Salute")
        self._build_tab_health()

        # TAB 2: Sottoclasse / Archetipo (se applicabile o presente)
        self.tab_subclass = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_subclass, text="🌟 Sottoclasse")
        self._build_tab_subclass()

        # TAB 3: Nuovi Privilegi
        self.tab_features = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_features, text="⚔️ Nuovi Privilegi")
        self._build_tab_features()

        # TAB 4: Incantesimi & Slot (se classe con magia)
        self.tab_magic = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_magic, text="✨ Incantesimi")
        self._build_tab_magic()

        # TAB 5: Caratteristiche / Talenti (ASI)
        self.tab_asi = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_asi, text="💪 Caratteristiche (ASI)")
        self._build_tab_asi()

        # Barra inferiore pulsanti
        bottom_bar = ttk.Frame(self, padding=(10, 8))
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.lbl_loading = ttk.Label(bottom_bar, text="Caricamento progressione D&D 5e...", font=("Segoe UI", 9, "italic"))
        self.lbl_loading.pack(side=tk.LEFT, padx=5)

        self.btn_apply = ttk.Button(bottom_bar, text="✅ Applica e Sali di Livello", command=self.apply, style="Primary.TButton")
        self.btn_apply.pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_bar, text="Annulla", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _build_tab_health(self):
        hp_frame = ttk.LabelFrame(self.tab_health, text="Incremento Punti Ferita (HP)", padding=10)
        hp_frame.pack(fill=tk.X, pady=6)

        cos_val = self.character.attributes.get("COS", 10)
        cos_mod = (cos_val - 10) // 2
        self.cos_mod = cos_mod

        ttk.Label(
            hp_frame,
            text=f"A ogni livello aumenti i Punti Ferita massimi in base al Dado Vita della tua classe (d{self.hit_die}) "
                 f"più il tuo modificatore di Costituzione ({cos_mod:+d}).",
            wraplength=660
        ).pack(anchor="w", pady=(0, 8))

        self.hp_choice = tk.StringVar(value="media")

        row_media = ttk.Frame(hp_frame)
        row_media.pack(fill=tk.X, pady=3)
        rb_media = ttk.Radiobutton(
            row_media,
            text=f"Prendi il valore medio fisso: {self.avg_hp} PF (+ {cos_mod} COS = {max(1, self.avg_hp + cos_mod)} PF totali)",
            variable=self.hp_choice,
            value="media",
            command=self.update_hp_entry
        )
        rb_media.pack(side=tk.LEFT)

        row_roll = ttk.Frame(hp_frame)
        row_roll.pack(fill=tk.X, pady=3)
        rb_roll = ttk.Radiobutton(
            row_roll,
            text=f"Tira il Dado Vita (1d{self.hit_die}): ",
            variable=self.hp_choice,
            value="roll",
            command=self.update_hp_entry
        )
        rb_roll.pack(side=tk.LEFT)

        self.btn_roll_hd = ttk.Button(row_roll, text="🎲 Tira Dado", command=self._roll_hit_die, width=12)
        self.btn_roll_hd.pack(side=tk.LEFT, padx=8)

        input_frame = ttk.Frame(hp_frame)
        input_frame.pack(fill=tk.X, pady=(10, 4))
        ttk.Label(input_frame, text="Risultato Dado (senza Costituzione):").pack(side=tk.LEFT, padx=(0, 6))

        self.hp_add_var = tk.IntVar(value=self.avg_hp)
        self.hp_entry = ttk.Entry(input_frame, textvariable=self.hp_add_var, width=6)
        self.hp_entry.pack(side=tk.LEFT)
        self.hp_entry.configure(state="readonly")
        self.hp_add_var.trace_add("write", lambda *a: self._update_hp_preview())

        self.lbl_hp_preview = ttk.Label(hp_frame, text="", font=("Segoe UI", 10, "bold"), foreground="#40C057")
        self.lbl_hp_preview.pack(anchor="w", pady=(8, 0))
        self._update_hp_preview()

        # Box riassuntivo dadi vita totali
        hd_box = ttk.LabelFrame(self.tab_health, text="Dadi Vita Totali", padding=10)
        hd_box.pack(fill=tk.X, pady=8)
        cur_hd = getattr(self.character, "hit_dice_total", self.character.level)
        ttk.Label(
            hd_box,
            text=f"Dadi Vita disponibili: {cur_hd}d{self.hit_die} ➔ {cur_hd + 1}d{self.hit_die}\n"
                 f"Recuperabili durante i Riposi Brevi per curarsi.",
            font=("Segoe UI", 9)
        ).pack(anchor="w")

    def _roll_hit_die(self):
        self.hp_choice.set("roll")
        val = random.randint(1, self.hit_die)
        self.hp_entry.configure(state="normal")
        self.hp_add_var.set(val)
        self._update_hp_preview()

    def update_hp_entry(self):
        if self.hp_choice.get() == "media":
            self.hp_add_var.set(self.avg_hp)
            self.hp_entry.configure(state="readonly")
        else:
            self.hp_entry.configure(state="normal")
        self._update_hp_preview()

    def _update_hp_preview(self):
        try:
            val = self.hp_add_var.get()
        except Exception:
            val = self.avg_hp
        tot = max(1, val + self.cos_mod)
        cur_max = getattr(self.character, "hp_max", 10)
        self.lbl_hp_preview.config(text=f"➡ Punti Ferita Massimi: {cur_max} ➔ {cur_max + tot} (+{tot} PF a questo livello)")

    def _build_tab_subclass(self):
        sub_frame = ttk.LabelFrame(self.tab_subclass, text="Sottoclasse Ufficiale D&D 5e", padding=10)
        sub_frame.pack(fill=tk.BOTH, expand=True)

        existing_sub = getattr(self.character, "subclass", "").strip()
        unlock_lvl = SUBCLASS_LEVEL_MAP.get(self.char_class_en, 3)

        # Recupera tutte le sottoclassi della classe da srd_subclasses_complete
        self.matching_subclasses = [
            s for s in ALL_OFFICIAL_SUBCLASSES
            if self.char_class_en in s.get("class_name", "").lower()
            or any(k_it in s.get("class_name", "").lower() for k_it, k_en in CLASS_MAP.items() if k_en == self.char_class_en)
        ]

        if existing_sub:
            ttk.Label(
                sub_frame,
                text=f"🌟 Sottoclasse Attuale: {existing_sub}",
                font=("Segoe UI", 11, "bold"),
                foreground="#D4AF37"
            ).pack(anchor="w", pady=(0, 6))

            matched = [s for s in self.matching_subclasses if s["name"].lower().startswith(existing_sub.lower()) or existing_sub.lower() in s["name"].lower()]
            if matched:
                sub_data = matched[0]
                ttk.Label(sub_frame, text=f"Fonte: {sub_data.get('source', 'Manuale Ufficiale')}", font=("Segoe UI", 9, "italic")).pack(anchor="w")
                ttk.Label(sub_frame, text=sub_data.get("description", ""), wraplength=640, justify=tk.LEFT).pack(anchor="w", pady=(4, 10))

            ttk.Label(sub_frame, text="Eventuali privilegi di questa sottoclasse per il nuovo livello sono inclusi nella scheda Privilegi.").pack(anchor="w", pady=4)
            self.subclass_choice_var = tk.StringVar(value=existing_sub)
        else:
            if self.new_level >= unlock_lvl:
                ttk.Label(
                    sub_frame,
                    text=f"🎉 Sblocco Archetipo / Sottoclasse al Livello {self.new_level}!",
                    font=("Segoe UI", 11, "bold"),
                    foreground="#40C057"
                ).pack(anchor="w", pady=(0, 4))
                ttk.Label(
                    sub_frame,
                    text=f"La tua classe sceglie la sua specializzazione al livello {unlock_lvl}. Seleziona una tra le {len(self.matching_subclasses)} sottoclassi ufficiali:",
                    wraplength=640
                ).pack(anchor="w", pady=(0, 8))
            else:
                ttk.Label(
                    sub_frame,
                    text=f"La tua classe sbloccherà l'Archetipo / Sottoclasse al Livello {unlock_lvl} (puoi comunque pre-selezionarlo se lo desideri):",
                    wraplength=640
                ).pack(anchor="w", pady=(0, 8))

            opts = [s["name"] for s in self.matching_subclasses]
            self.subclass_choice_var = tk.StringVar(value="")
            self.subclass_combo = ttk.Combobox(sub_frame, textvariable=self.subclass_choice_var, values=opts, width=45, state="readonly")
            self.subclass_combo.pack(anchor="w", pady=(0, 8))
            self.subclass_combo.bind("<<ComboboxSelected>>", self._on_subclass_selected)

            self.subclass_info_box = ttk.Frame(sub_frame)
            self.subclass_info_box.pack(fill=tk.BOTH, expand=True, pady=4)

            self.lbl_sub_source = ttk.Label(self.subclass_info_box, text="", font=("Segoe UI", 9, "italic"))
            self.lbl_sub_source.pack(anchor="w")

            self.txt_sub_desc = tk.Text(self.subclass_info_box, wrap=tk.WORD, height=6, font=("Segoe UI", 9))
            self.txt_sub_desc.pack(fill=tk.BOTH, expand=True, pady=4)
            self.txt_sub_desc.configure(state="disabled")

    def _on_subclass_selected(self, event=None):
        sub_name = self.subclass_choice_var.get()
        matched = [s for s in self.matching_subclasses if s["name"] == sub_name]
        if matched:
            sub = matched[0]
            self.lbl_sub_source.config(text=f"Fonte: {sub.get('source', 'Ufficiale')}")
            self.txt_sub_desc.configure(state="normal")
            self.txt_sub_desc.delete("1.0", tk.END)
            self.txt_sub_desc.insert(tk.END, sub.get("description", ""))
            self.txt_sub_desc.configure(state="disabled")

            # Rinfresca i privilegi se questa sottoclasse conferisce privilegi a new_level
            self._refresh_subclass_features(sub)

    def _refresh_subclass_features(self, sub_obj):
        sub_feats = [f for f in sub_obj.get("features", []) if f.get("level") == self.new_level]
        for f in sub_feats:
            fname = f.get("name", "")
            fdesc = f.get("desc", "")
            if fname and fname not in self.new_features:
                self.new_features.append(fname)
                self.new_feature_details[fname] = fdesc
                self.features_listbox.insert(tk.END, f"🌟 [Sottoclasse] {fname}")

    def _build_tab_features(self):
        feat_paned = ttk.PanedWindow(self.tab_features, orient=tk.VERTICAL)
        feat_paned.pack(fill=tk.BOTH, expand=True)

        top_f = ttk.Frame(feat_paned)
        feat_paned.add(top_f, weight=1)

        ttk.Label(top_f, text=f"Privilegi sbloccati al Livello {self.new_level}:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        self.features_listbox = tk.Listbox(top_f, font=("Segoe UI", 10), height=7)
        self.features_listbox.pack(fill=tk.BOTH, expand=True)
        self.features_listbox.bind("<<ListboxSelect>>", self._on_feature_selected)

        bot_f = ttk.Frame(feat_paned)
        feat_paned.add(bot_f, weight=1)

        ttk.Label(bot_f, text="Dettaglio e Descrizione Privilegio:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(6, 2))
        self.txt_feat_detail = tk.Text(bot_f, wrap=tk.WORD, font=("Segoe UI", 9), height=6)
        self.txt_feat_detail.pack(fill=tk.BOTH, expand=True)
        self.txt_feat_detail.configure(state="disabled")

    def _on_feature_selected(self, event=None):
        sel = self.features_listbox.curselection()
        if not sel:
            return
        item_text = self.features_listbox.get(sel[0])
        # Pulisci eventuale prefisso
        clean_name = item_text.replace("🌟 [Sottoclasse] ", "").replace("⚔️ ", "").strip()
        desc = self.new_feature_details.get(clean_name, "Nessuna descrizione testuale aggiuntiva per questo privilegio.")

        self.txt_feat_detail.configure(state="normal")
        self.txt_feat_detail.delete("1.0", tk.END)
        self.txt_feat_detail.insert(tk.END, f"Privilegio: {clean_name}\n\n{desc}")
        self.txt_feat_detail.configure(state="disabled")

    def _build_tab_magic(self):
        self.magic_header_frame = ttk.LabelFrame(self.tab_magic, text="Progressione Slot Incantesimo", padding=8)
        self.magic_header_frame.pack(fill=tk.X, pady=(0, 6))

        self.lbl_slots_summary = ttk.Label(self.magic_header_frame, text="Verifica slot incantesimo...", font=("Segoe UI", 9))
        self.lbl_slots_summary.pack(anchor="w")

        self.lbl_new_circle = ttk.Label(self.magic_header_frame, text="", font=("Segoe UI", 10, "bold"), foreground="#1971C2")
        self.lbl_new_circle.pack(anchor="w", pady=(2, 0))

        self.lbl_class_guidance = ttk.Label(self.magic_header_frame, text="", font=("Segoe UI", 9, "italic"), wraplength=660)
        self.lbl_class_guidance.pack(anchor="w", pady=(4, 0))

        # Selettore incantesimi
        self.spells_paned = ttk.PanedWindow(self.tab_magic, orient=tk.HORIZONTAL)
        self.spells_paned.pack(fill=tk.BOTH, expand=True, pady=6)

        left_side = ttk.Frame(self.spells_paned, padding=4)
        self.spells_paned.add(left_side, weight=3)

        filter_bar = ttk.Frame(left_side)
        filter_bar.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(filter_bar, text="Cerchio:").pack(side=tk.LEFT)
        self.spell_level_filter = ttk.Combobox(filter_bar, values=["Tutti i Cerchi"], width=16, state="readonly")
        self.spell_level_filter.set("Tutti i Cerchi")
        self.spell_level_filter.pack(side=tk.LEFT, padx=4)
        self.spell_level_filter.bind("<<ComboboxSelected>>", lambda e: self._filter_spells_list())

        ttk.Label(filter_bar, text="Cerca:").pack(side=tk.LEFT, padx=(6, 0))
        self.spell_search_var = tk.StringVar()
        self.spell_search_entry = ttk.Entry(filter_bar, textvariable=self.spell_search_var, width=16)
        self.spell_search_entry.pack(side=tk.LEFT, padx=4)
        self.spell_search_var.trace_add("write", lambda *a: self._filter_spells_list())

        cols = ("lvl", "name", "school", "time")
        self.tree_spells = ttk.Treeview(left_side, columns=cols, show="headings", height=8, selectmode="browse")
        self.tree_spells.heading("lvl", text="Lv")
        self.tree_spells.heading("name", text="Incantesimo (IT / EN)")
        self.tree_spells.heading("school", text="Scuola")
        self.tree_spells.heading("time", text="Tempo")

        self.tree_spells.column("lvl", width=40, anchor="center")
        self.tree_spells.column("name", width=220)
        self.tree_spells.column("school", width=90)
        self.tree_spells.column("time", width=80)

        tree_scroll = ttk.Scrollbar(left_side, orient=tk.VERTICAL, command=self.tree_spells.yview)
        self.tree_spells.configure(yscrollcommand=tree_scroll.set)
        self.tree_spells.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_spells.bind("<<TreeviewSelect>>", self._on_spell_selected)

        # Destra: Dettaglio incantesimo e pulsante di selezione
        right_side = ttk.Frame(self.spells_paned, padding=4)
        self.spells_paned.add(right_side, weight=2)

        ttk.Label(right_side, text="Dettaglio Incantesimo:", font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.txt_spell_desc = tk.Text(right_side, wrap=tk.WORD, font=("Segoe UI", 9), height=10)
        self.txt_spell_desc.pack(fill=tk.BOTH, expand=True, pady=4)
        self.txt_spell_desc.configure(state="disabled")

        action_f = ttk.Frame(right_side)
        action_f.pack(fill=tk.X, pady=4)

        self.btn_toggle_spell = ttk.Button(action_f, text="➕ Aggiungi al Grimorio", command=self._toggle_spell_selection)
        self.btn_toggle_spell.pack(fill=tk.X)

        self.lbl_selected_spells_count = ttk.Label(right_side, text="Incantesimi selezionati: 0", font=("Segoe UI", 9, "bold"), foreground="#2B8A3E")
        self.lbl_selected_spells_count.pack(anchor="w", pady=(4, 0))

        self.lst_selected_spells = tk.Listbox(right_side, height=4, font=("Segoe UI", 8))
        self.lst_selected_spells.pack(fill=tk.X, pady=(2, 0))

    def _build_tab_asi(self):
        asi_frame = ttk.LabelFrame(self.tab_asi, text="Aumento Punteggi di Caratteristica o Talento", padding=10)
        asi_frame.pack(fill=tk.BOTH, expand=True)

        allowed_levels = ASI_LEVELS.get(self.char_class_en, ASI_LEVELS["default"])
        self.has_asi = (self.new_level in allowed_levels)

        if not self.has_asi:
            next_lvl = min([lvl for lvl in allowed_levels if lvl > self.new_level], default="20")
            ttk.Label(
                asi_frame,
                text=f"Nessun Aumento Caratteristiche a questo livello.\nIl prossimo aumento per la tua classe sarà al Livello {next_lvl}.",
                font=("Segoe UI", 10),
                justify=tk.LEFT
            ).pack(anchor="w", pady=10)
            self.lbl_stats = ttk.Label(asi_frame, text="Nessun aumento in questo livello.")
            return

        ttk.Label(
            asi_frame,
            text="🎉 Hai ottenuto un Aumento dei Punteggi di Caratteristica (ASI)!\n"
                 "Puoi aumentare una caratteristica di +2, oppure due caratteristiche diverse di +1 ciascuna, "
                 "oppure scegliere un Talento Ufficiale:",
            font=("Segoe UI", 10, "bold"),
            foreground="#D4AF37",
            justify=tk.LEFT
        ).pack(anchor="w", pady=(0, 10))

        self.lbl_stats = ttk.Label(asi_frame, text="Aumento Caratteristiche Disponibile!")

        self.asi_choice_var = tk.StringVar(value="single")

        # Opzione 1: +2 a una stat
        rb1 = ttk.Radiobutton(asi_frame, text="+2 a un Punteggio di Caratteristica:", variable=self.asi_choice_var, value="single", command=self._on_asi_mode_changed)
        rb1.pack(anchor="w", pady=(4, 2))

        f_single = ttk.Frame(asi_frame)
        f_single.pack(fill=tk.X, padx=20, pady=(0, 6))
        ttk.Label(f_single, text="Caratteristica:").pack(side=tk.LEFT)
        attrs = ["FOR", "DES", "COS", "INT", "SAG", "CAR"]
        self.asi_single_stat = ttk.Combobox(f_single, values=[f"{a} (attuale: {self.character.attributes.get(a, 10)})" for a in attrs], width=24, state="readonly")
        self.asi_single_stat.set(f"INT (attuale: {self.character.attributes.get('INT', 10)})" if self.char_class_en == "wizard" else f"FOR (attuale: {self.character.attributes.get('FOR', 10)})")
        self.asi_single_stat.pack(side=tk.LEFT, padx=6)

        # Opzione 2: +1 a due stat
        rb2 = ttk.Radiobutton(asi_frame, text="+1 a due Punteggi di Caratteristica differenti:", variable=self.asi_choice_var, value="dual", command=self._on_asi_mode_changed)
        rb2.pack(anchor="w", pady=(6, 2))

        f_dual = ttk.Frame(asi_frame)
        f_dual.pack(fill=tk.X, padx=20, pady=(0, 6))
        ttk.Label(f_dual, text="Stat 1:").pack(side=tk.LEFT)
        self.asi_dual_stat1 = ttk.Combobox(f_dual, values=[f"{a} (attuale: {self.character.attributes.get(a, 10)})" for a in attrs], width=20, state="readonly")
        self.asi_dual_stat1.set(f"DES (attuale: {self.character.attributes.get('DES', 10)})")
        self.asi_dual_stat1.pack(side=tk.LEFT, padx=4)

        ttk.Label(f_dual, text="Stat 2:").pack(side=tk.LEFT, padx=(6, 0))
        self.asi_dual_stat2 = ttk.Combobox(f_dual, values=[f"{a} (attuale: {self.character.attributes.get(a, 10)})" for a in attrs], width=20, state="readonly")
        self.asi_dual_stat2.set(f"COS (attuale: {self.character.attributes.get('COS', 10)})")
        self.asi_dual_stat2.pack(side=tk.LEFT, padx=4)

        # Opzione 3: Talento
        rb3 = ttk.Radiobutton(asi_frame, text="Scegli un Talento Ufficiale D&D 5e (Feat):", variable=self.asi_choice_var, value="feat", command=self._on_asi_mode_changed)
        rb3.pack(anchor="w", pady=(6, 2))

        f_feat = ttk.Frame(asi_frame)
        f_feat.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 4))
        feat_names = [f["name"] for f in STANDARD_5E_FEATS_CATALOG]
        self.asi_feat_choice = ttk.Combobox(f_feat, values=feat_names, width=42, state="readonly")
        if feat_names:
            self.asi_feat_choice.set(feat_names[0])
        self.asi_feat_choice.pack(anchor="w", pady=(0, 4))
        self.asi_feat_choice.bind("<<ComboboxSelected>>", self._on_feat_selected)

        self.txt_feat_preview = tk.Text(f_feat, wrap=tk.WORD, height=4, font=("Segoe UI", 9))
        self.txt_feat_preview.pack(fill=tk.BOTH, expand=True)
        self.txt_feat_preview.configure(state="disabled")
        self._on_feat_selected()

    def _on_asi_mode_changed(self):
        pass

    def _on_feat_selected(self, event=None):
        if not hasattr(self, "asi_feat_choice"):
            return
        fname = self.asi_feat_choice.get()
        matched = [f for f in STANDARD_5E_FEATS_CATALOG if f["name"] == fname]
        if matched and hasattr(self, "txt_feat_preview"):
            f = matched[0]
            self.txt_feat_preview.configure(state="normal")
            self.txt_feat_preview.delete("1.0", tk.END)
            prereq = f.get("prerequisite", "Nessuno")
            desc = f.get("desc", "")
            src = f.get("source", "D&D 5e")
            self.txt_feat_preview.insert(tk.END, f"Requisito: {prereq} | Fonte: {src}\n{desc}")
            self.txt_feat_preview.configure(state="disabled")

    def _safe_ui(self, callback):
        try:
            if hasattr(self, "winfo_exists") and not self.winfo_exists():
                return
            if hasattr(self, "master") and hasattr(self.master, "winfo_exists") and not self.master.winfo_exists():
                return
            self.master.after(0, callback)
        except Exception:
            pass

    def fetch_level_data(self):
        """Carica immediatamente i dati dalla progressione locale SRD 5e senza attese di rete."""
        try:
            off_data = get_class_level_features_offline(self.character.char_class, self.new_level, getattr(self.character, "subclass", ""))
            features_list = [{"name": f} if isinstance(f, str) else f for f in off_data.get("features", [])]
            spellcasting = {}
            for lvl_str, count in off_data.get("spell_slots", {}).items():
                spellcasting[f"spell_slots_level_{lvl_str}"] = count

            asi_flag = 1 if self.new_level in ASI_LEVELS.get(self.char_class_en, ASI_LEVELS["default"]) else 0

            data = {
                "level": self.new_level,
                "ability_score_bonuses": asi_flag,
                "features": features_list,
                "spellcasting": spellcasting if spellcasting else None,
                "spell_slots": off_data.get("spell_slots", {}),
                "offline": True
            }
            self.on_api_success(data, is_offline=True)
        except Exception as e:
            print("[PROGRESSION] Errore caricamento SRD offline:", e)
            self.lbl_loading.config(text=f"Errore caricamento: {e}")

    def on_api_success(self, data, is_offline=True):
        self.api_data = data
        self.lbl_loading.config(text="Dati di progressione caricati (SRD 5e Ufficiale)")
        self.btn_apply.state(["!disabled"])

        # Popola privilegi di classe base
        if "features" in data:
            for f in data["features"]:
                fname = f["name"] if isinstance(f, dict) else str(f)
                if fname not in self.new_features:
                    self.new_features.append(fname)
                    self.new_feature_details[fname] = f.get("desc", f"Privilegio di classe conferito al Livello {self.new_level}.")
                    self.features_listbox.insert(tk.END, f"⚔️ {fname}")

        # Se la sottoclasse è già selezionata, aggiungi anche i privilegi di sottoclasse
        existing_sub = getattr(self.character, "subclass", "").strip()
        if existing_sub:
            matched = [s for s in self.matching_subclasses if s["name"].lower().startswith(existing_sub.lower()) or existing_sub.lower() in s["name"].lower()]
            if matched:
                self._refresh_subclass_features(matched[0])

        if not self.new_features:
            self.features_listbox.insert(tk.END, "Nessun nuovo privilegio specifico per questo livello.")

        # Aggiorna scheda Incantesimi
        self._setup_magic_tab_data(data)

    def _setup_magic_tab_data(self, data):
        slots = data.get("spell_slots", {})
        if not slots and data.get("spellcasting"):
            sc = data["spellcasting"]
            for i in range(1, 10):
                k = f"spell_slots_level_{i}"
                if k in sc and sc[k] > 0:
                    slots[str(i)] = sc[k]

        max_slot_lvl = max([int(k) for k, v in slots.items() if v > 0], default=0)

        # Controllo se classe o sottoclasse è magica
        sub_name = getattr(self.character, "subclass", "").lower()
        is_sub_caster = any(k in sub_name for k in ["mistico", "arcano", "eldritch", "trickster"])
        is_magic_class = self.char_class_en in [
            "wizard", "cleric", "druid", "bard", "sorcerer", "warlock", "paladin", "ranger", "artificer"
        ] or is_sub_caster

        if not is_magic_class and max_slot_lvl == 0:
            self.lbl_slots_summary.config(text="Questa classe non utilizza slot incantesimo per lanciare magie.")
            self.lbl_new_circle.config(text="")
            self.lbl_class_guidance.config(text="Puoi consultare il compendio incantesimi in qualunque momento con il pulsante sottostante.")
            btn = ttk.Button(self.magic_header_frame, text="📖 Apri Compendio Generale", command=self.open_compendium)
            btn.pack(anchor="w", pady=4)
            return

        # Riepilogo slot
        if slots:
            slot_parts = [f"Liv. {lvl}: {cnt} slot" for lvl, cnt in sorted(slots.items(), key=lambda x: int(x[0])) if cnt > 0]
            self.lbl_slots_summary.config(text="✨ Slot Incantesimo al Livello " + str(self.new_level) + ":  " + " | ".join(slot_parts))
        else:
            self.lbl_slots_summary.config(text=f"Nessuno slot attivo al Livello {self.new_level}.")

        # Nuovo cerchio sbloccato
        prev_level_data = get_class_level_features_offline(self.character.char_class, self.character.level)
        prev_slots = prev_level_data.get("spell_slots", {})
        prev_max_lvl = max([int(k) for k, v in prev_slots.items() if v > 0], default=0)
        if max_slot_lvl > prev_max_lvl and max_slot_lvl > 0:
            self.lbl_new_circle.config(text=f"🌟 NUOVO CERCHIO SBLOCCATO: Incantesimi di {max_slot_lvl}° Livello!")
        else:
            self.lbl_new_circle.config(text="")

        # Linee guida classe
        guidance = {
            "wizard": "📖 In qualità di Mago, trascrivi normalmente 2 nuovi incantesimi di qualsiasi cerchio per cui possiedi slot.",
            "sorcerer": "🔮 In qualità di Stregone, puoi imparare 1 nuovo incantesimo di classe e opzionalmente sostituirne uno esistente.",
            "bard": "🎶 In qualità di Bardo, puoi imparare 1 nuovo incantesimo di classe e opzionalmente sostituirne uno esistente.",
            "warlock": "👁️ In qualità di Warlock, puoi imparare 1 nuovo incantesimo di classe (e tutti i tuoi slot scalano automaticamente).",
            "ranger": "🏹 In qualità di Ranger, impari 1 nuovo incantesimo di classe tra quelli del tuo cerchio.",
            "cleric": "☀️ In qualità di Chierico, hai accesso all'intera lista divina: seleziona gli incantesimi che intendi preparare.",
            "druid": "🍃 In qualità di Druido, hai accesso all'intera lista naturale: seleziona gli incantesimi che intendi preparare.",
            "paladin": "🛡️ In qualità di Paladino, prepari i tuoi incantesimi dalla lista sacra di classe.",
            "artificer": "⚙️ In qualità di Artefice, prepari le tue infusioni e incantesimi dalla lista di classe."
        }
        self.lbl_class_guidance.config(text=guidance.get(self.char_class_en, "Seleziona gli incantesimi da aggiungere alla tua scheda."))

        # Popola lista di incantesimi idonei da srd_offline
        cls_key = "wizard" if is_sub_caster else self.char_class_en
        all_spells = get_all_spells_offline()

        existing_names = set()
        for s in getattr(self.character, "spellbook", []):
            if isinstance(s, dict):
                existing_names.add(s.get("name", "").lower())
                existing_names.add(s.get("name_en", "").lower())

        self.all_eligible_spells = []
        for sp in all_spells:
            sp_cls = str(sp.get("class", "") or sp.get("dnd_class", "")).lower()
            lvl = sp.get("level_int", 0)
            if (cls_key in sp_cls) and (lvl <= max_slot_lvl):
                en_name = sp.get("name", "")
                it_name = SPELL_EN_TO_IT.get(en_name.lower(), en_name)
                if en_name.lower() not in existing_names and it_name.lower() not in existing_names:
                    sp_copy = dict(sp)
                    sp_copy["name_it"] = it_name
                    sp_copy["name_en"] = en_name
                    self.all_eligible_spells.append(sp_copy)

        # Popola filtro cerchio
        filter_vals = ["Tutti i Cerchi", "Trucchetti (Liv. 0)"]
        for i in range(1, max_slot_lvl + 1):
            filter_vals.append(f"Livello {i}")
        self.spell_level_filter["values"] = filter_vals

        self._filter_spells_list()

    def _filter_spells_list(self):
        for item in self.tree_spells.get_children():
            self.tree_spells.delete(item)

        filter_choice = self.spell_level_filter.get()
        query = self.spell_search_var.get().strip().lower()

        filtered = []
        for sp in self.all_eligible_spells:
            lvl = sp.get("level_int", 0)
            if filter_choice == "Trucchetti (Liv. 0)" and lvl != 0:
                continue
            elif filter_choice.startswith("Livello "):
                target_lvl = int(filter_choice.split()[1])
                if lvl != target_lvl:
                    continue

            name_it = sp.get("name_it", "").lower()
            name_en = sp.get("name_en", "").lower()
            if query and (query not in name_it and query not in name_en):
                continue

            filtered.append(sp)

        # Ordina per livello e poi per nome
        filtered.sort(key=lambda s: (s.get("level_int", 0), s.get("name_it", s.get("name", ""))))

        for sp in filtered:
            lvl_str = "0" if sp.get("level_int") == 0 else str(sp.get("level_int"))
            display_name = f"{sp.get('name_it')} ({sp.get('name_en')})" if sp.get("name_it") != sp.get("name_en") else sp.get("name")
            self.tree_spells.insert(
                "",
                tk.END,
                iid=sp["name"],
                values=(lvl_str, display_name, sp.get("school", "-"), sp.get("casting_time", "-"))
            )

    def _on_spell_selected(self, event=None):
        sel = self.tree_spells.selection()
        if not sel:
            return
        sp_id = sel[0]
        matched = [s for s in self.all_eligible_spells if s["name"] == sp_id]
        if not matched:
            return
        sp = matched[0]

        is_already_selected = any(s["name"] == sp["name"] for s in self.selected_spells)
        if is_already_selected:
            self.btn_toggle_spell.config(text="➖ Rimuovi Selezione", style="Danger.TButton")
        else:
            self.btn_toggle_spell.config(text="➕ Aggiungi al Grimorio", style="Primary.TButton")

        self.txt_spell_desc.configure(state="normal")
        self.txt_spell_desc.delete("1.0", tk.END)

        header = f"{sp.get('name_it')} ({sp.get('name_en')})\n"
        header += f"Livello: {sp.get('level_int', 0)} | Scuola: {sp.get('school', '-')} | Tempo: {sp.get('casting_time', '-')}\n"
        header += f"Gittata: {sp.get('range', '-')} | Componenti: {sp.get('components', '-')} | Durata: {sp.get('duration', '-')}\n"
        if str(sp.get("concentration", "")).lower() in ["yes", "true", "si"]:
            header += "⭐ Concentrazione: Sì\n"
        if str(sp.get("ritual", "")).lower() in ["yes", "true", "si"]:
            header += "📖 Rituale: Sì\n"
        header += "-" * 40 + "\n\n"

        self.txt_spell_desc.insert(tk.END, header + sp.get("desc", ""))
        self.txt_spell_desc.configure(state="disabled")

    def _toggle_spell_selection(self):
        sel = self.tree_spells.selection()
        if not sel:
            return
        sp_id = sel[0]
        matched = [s for s in self.all_eligible_spells if s["name"] == sp_id]
        if not matched:
            return
        sp = matched[0]

        existing_idx = next((i for i, s in enumerate(self.selected_spells) if s["name"] == sp["name"]), None)
        if existing_idx is not None:
            self.selected_spells.pop(existing_idx)
            self.btn_toggle_spell.config(text="➕ Aggiungi al Grimorio", style="Primary.TButton")
        else:
            self.selected_spells.append(sp)
            self.btn_toggle_spell.config(text="➖ Rimuovi Selezione", style="Danger.TButton")

        self._refresh_selected_spells_ui()

    def _refresh_selected_spells_ui(self):
        self.lbl_selected_spells_count.config(text=f"Incantesimi selezionati: {len(self.selected_spells)}")
        self.lst_selected_spells.delete(0, tk.END)
        for s in self.selected_spells:
            lvl = s.get("level_int", 0)
            self.lst_selected_spells.insert(tk.END, f"[Lv {lvl}] {s.get('name_it', s.get('name'))}")

    def open_compendium(self):
        CompendiumDialog(self.master, is_dm=False)

    def apply(self):
        # 1. Punti Ferita
        try:
            hp_inc = self.hp_add_var.get()
        except (ValueError, tk.TclError):
            hp_inc = self.avg_hp

        cos_mod = (self.character.attributes.get("COS", 10) - 10) // 2
        total_hp_inc = max(1, hp_inc + cos_mod)

        self.character.level += 1
        self.character.hp_max += total_hp_inc
        self.character.hp_current += total_hp_inc

        # Incremento Dadi Vita
        if hasattr(self.character, "hit_dice_total"):
            self.character.hit_dice_total += 1
            self.character.hit_dice_current = getattr(self.character, "hit_dice_current", 0) + 1

        # 2. Sottoclasse
        chosen_sub = getattr(self, "subclass_choice_var", None)
        if chosen_sub and chosen_sub.get().strip():
            self.character.subclass = chosen_sub.get().strip()

        # 3. Privilegi di Classe & Sottoclasse
        if self.new_features:
            feats_str = "\n".join([f"- {feat}" for feat in self.new_features])
            if hasattr(self.character, "features") and self.character.features:
                self.character.features += f"\n\n--- Livello {self.character.level} ---\n{feats_str}"
            else:
                self.character.features = f"--- Livello {self.character.level} ---\n{feats_str}"
            if not hasattr(self.character, "features_list") or not isinstance(self.character.features_list, list):
                self.character.features_list = []
            for feat_name in self.new_features:
                desc = self.new_feature_details.get(feat_name, "")
                self.character.features_list.append({
                    "name": feat_name,
                    "category": f"Privilegio (Lv {self.character.level})",
                    "desc": desc
                })

        # 4. Aumento Caratteristiche (ASI / Talento)
        if getattr(self, "has_asi", False):
            mode = getattr(self, "asi_choice_var", None)
            mode_val = mode.get() if mode else "single"
            if mode_val == "single" and hasattr(self, "asi_single_stat"):
                raw_stat = self.asi_single_stat.get().split()[0].upper()
                if raw_stat in self.character.attributes:
                    old_val = self.character.attributes[raw_stat]
                    new_val = min(20, old_val + 2)
                    self.character.attributes[raw_stat] = new_val
                    # Se aumentata Costituzione, retroattivamente aggiunge 1 PF per livello
                    if raw_stat == "COS" and (new_val // 2 > old_val // 2):
                        extra_hp = self.character.level * ((new_val - 10) // 2 - (old_val - 10) // 2)
                        self.character.hp_max += extra_hp
                        self.character.hp_current += extra_hp
            elif mode_val == "dual" and hasattr(self, "asi_dual_stat1") and hasattr(self, "asi_dual_stat2"):
                s1 = self.asi_dual_stat1.get().split()[0].upper()
                s2 = self.asi_dual_stat2.get().split()[0].upper()
                if s1 == s2:
                    s2 = None
                if s1 in self.character.attributes:
                    old_val = self.character.attributes[s1]
                    new_val = min(20, old_val + 1)
                    self.character.attributes[s1] = new_val
                    if s1 == "COS" and (new_val // 2 > old_val // 2):
                        extra_hp = self.character.level
                        self.character.hp_max += extra_hp
                        self.character.hp_current += extra_hp
                if s2 and s2 in self.character.attributes:
                    old_val = self.character.attributes[s2]
                    new_val = min(20, old_val + 1)
                    self.character.attributes[s2] = new_val
                    if s2 == "COS" and (new_val // 2 > old_val // 2):
                        extra_hp = self.character.level
                        self.character.hp_max += extra_hp
                        self.character.hp_current += extra_hp
            elif mode_val == "feat" and hasattr(self, "asi_feat_choice"):
                feat_name = self.asi_feat_choice.get()
                matched = [f for f in STANDARD_5E_FEATS_CATALOG if f["name"] == feat_name]
                feat_desc = matched[0].get("desc", "") if matched else ""
                feat_entry = f"Talento: {feat_name}\n{feat_desc}"
                if hasattr(self.character, "features") and self.character.features:
                    self.character.features += f"\n\n--- Talento (Livello {self.character.level}) ---\n{feat_entry}"
                else:
                    self.character.features = f"--- Talento (Livello {self.character.level}) ---\n{feat_entry}"
                if not hasattr(self.character, "features_list") or not isinstance(self.character.features_list, list):
                    self.character.features_list = []
                self.character.features_list.append({
                    "name": feat_name,
                    "category": f"Talento (Lv {self.character.level})",
                    "desc": feat_desc
                })

        self.character.proficiency_bonus = 2 + (self.character.level - 1) // 4

        # 5. Slot Incantesimo (D&D 5e: Warlock sostituisce slot inferiori con slot superiori)
        if self.api_data and isinstance(self.api_data.get("spellcasting"), dict):
            sc = self.api_data["spellcasting"]
            is_warlock = "warlock" in str(getattr(self.character, "char_class", "")).lower()
            if is_warlock:
                for i in range(1, 10):
                    key = f"spell_slots_level_{i}"
                    if key not in sc and str(i) in self.character.spell_slots:
                        if isinstance(self.character.spell_slots[str(i)], dict):
                            self.character.spell_slots[str(i)]["max"] = 0
                            self.character.spell_slots[str(i)]["current"] = 0
                        else:
                            self.character.spell_slots[str(i)] = [0, 0]
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

        # 6. Incantesimi Selezionati aggiunti direttamente al Grimorio
        if getattr(self, "selected_spells", None):
            if not hasattr(self.character, "spellbook") or not isinstance(self.character.spellbook, list):
                self.character.spellbook = []

            for sp in self.selected_spells:
                s_name = sp.get("name_it", sp.get("name"))
                if not any(s.get("name") == s_name for s in self.character.spellbook):
                    self.character.spellbook.append({
                        "name": s_name,
                        "name_en": sp.get("name_en", sp.get("name")),
                        "level": sp.get("level_int", 0),
                        "time": sp.get("casting_time", "-"),
                        "range": sp.get("range", "-"),
                        "school": sp.get("school", "-"),
                        "desc": sp.get("desc", "")
                    })

        self.update_callback()
        self.destroy()
