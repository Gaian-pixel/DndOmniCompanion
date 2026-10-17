import tkinter as tk
import re
import threading
import urllib.request
import urllib.parse
import json
from common.messagebox import messagebox
from tkinter import ttk, simpledialog
from common.theme import (
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, BORDER_COLOR,
    TEXT_COLOR, TEXT_MUTED, TEXT_DARK,
    ACCENT_GOLD, ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE,
    FONT_MAIN, FONT_TITLE, FONT_HEADER, FONT_BOLD, FONT_SMALL,
    apply_modern_window_style
)
from common.i18n import (
    _t, get_language, translate_condition, translate_ability, translate_skill,
    get_distance_unit, set_distance_unit, convert_speed_value
)
from components.ui_components import ToolTip


def get_item_icon(item):
    """Restituisce l'emoji più appropriata per la tipologia di oggetto."""
    if not item or not isinstance(item, dict):
        return "📦"
    t = str(item.get("type", "")).lower().strip()
    n = str(item.get("name", "")).lower()
    if any(k in t or k in n for k in ["armatura", "armor", "scudo", "shield", "cuoio", "leather", "maglia", "chain", "piastre", "plate", "pettorale"]):
        return "🛡️"
    if any(k in t or k in n for k in ["arma", "weapon", "spada", "sword", "arco", "bow", "pugnale", "dagger", "balestra", "crossbow", "ascia", "axe", "martello", "hammer", "bastone", "staff", "lancia", "spear", "stocco", "rapier", "scimitarra", "scimitar", "dardo", "dart", "giavellotto", "javelin"]):
        return "⚔️"
    if any(k in t or k in n for k in ["pozione", "potion", "consumabile", "consumable", "elisir", "elixir", "fiala", "vial", "unguento", "olio"]):
        return "🧪"
    if any(k in t or k in n for k in ["pergamena", "scroll", "documento", "document", "libro", "book", "mappa", "map", "lettera", "letter"]):
        return "📜"
    if any(k in t or k in n for k in ["anello", "ring", "amuleto", "amulet", "collana", "necklace", "gemma", "gem", "gioiello", "talismano"]):
        return "💍"
    if any(k in t or k in n for k in ["attrezzi", "strumento", "tools", "kit", "liuto", "lute", "flauto", "grimaldello", "lockpick", "focus"]):
        return "🧰"
    if any(k in t or k in n for k in ["razion", "ration", "cibo", "food", "acqua", "water", "otre", "torcia", "torch", "corda", "rope", "zaino", "backpack", "coperta", "equipaggiamento", "equipment"]):
        return "🎒"
    if any(k in t or k in n for k in ["valuta", "currency", "moneta", "coin", "borsa"]):
        return "🪙"
    return "📦"


class CharacterSheetUI(tk.Toplevel):
    def __init__(self, master, character, manager, on_save_callback=None, roll_callback=None, trade_callback=None, give_gold_callback=None, players_list_callback=None, attack_callback=None, long_rest_callback=None, custom_spell_request_callback=None, request_currency_callback=None, request_item_callback=None, is_connected=False):
        super().__init__(master)
        self.title(f"{_t('sheet_title')} - {character.name}")
        self.minsize(700, 700)
        apply_modern_window_style(self)
        self.character = character
        self.manager = manager
        self.on_save_callback = on_save_callback
        self.roll_callback = roll_callback
        self.long_rest_callback = long_rest_callback
        self.trade_callback = trade_callback
        self.give_gold_callback = give_gold_callback
        self.players_list_callback = players_list_callback
        self.attack_callback = attack_callback
        self.custom_spell_request_callback = custom_spell_request_callback
        self.request_currency_callback = request_currency_callback
        self.request_item_callback = request_item_callback
        self.is_connected = is_connected
        self.default_font = ("Georgia", 10)
        self.initial_currency = {}
        
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Intestazione (Dark Fantasy Card)
        header_frame = tk.Frame(main_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=8)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(header_frame, text=_t("sheet_name"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).grid(row=0, column=0, sticky="e", padx=(0, 4))
        self.name_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.name_var, width=16).grid(row=0, column=1, padx=4, pady=3, sticky="ew")

        tk.Label(header_frame, text=_t("sheet_campaign"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=0, column=2, sticky="e", padx=(8, 4))
        self.campaign_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.campaign_var, width=14).grid(row=0, column=3, padx=4, pady=3, sticky="ew")

        self.levelup_btn = ttk.Button(header_frame, text=_t("sheet_levelup_btn"), command=self.level_up, style="Gold.TButton")
        self.levelup_btn.grid(row=0, column=4, columnspan=3, padx=(10, 0), pady=3, sticky="ew")

        tk.Label(header_frame, text=_t("sheet_class"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=1, column=0, sticky="e", padx=(0, 4))
        self.class_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.class_var, width=16).grid(row=1, column=1, padx=4, pady=3, sticky="ew")

        tk.Label(header_frame, text=_t("sheet_level"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=1, column=2, sticky="e", padx=(8, 4))
        self.level_var = tk.IntVar()
        self.level_var.trace_add("write", lambda *args: self.update_skill_modifiers() if hasattr(self, "update_skill_modifiers") else None)
        ttk.Entry(header_frame, textvariable=self.level_var, width=4, state="readonly", justify="center").grid(row=1, column=3, padx=4, pady=3, sticky="w")
        
        tk.Label(header_frame, text=_t("sheet_exp"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=1, column=4, sticky="e", padx=(8, 4))
        self.exp_label = tk.Label(header_frame, text="0 / 300", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_COLOR)
        self.exp_label.grid(row=1, column=5, padx=4, pady=3, sticky="w")
        self.exp_progress = ttk.Progressbar(header_frame, length=90, mode='determinate')
        self.exp_progress.grid(row=1, column=6, padx=4, pady=3, sticky="w")

        tk.Label(header_frame, text=_t("sheet_race"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=2, column=0, sticky="e", padx=(0, 4))
        self.race_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.race_var, width=16).grid(row=2, column=1, padx=4, pady=3, sticky="ew")

        self.btn_inspiration = tk.Button(
            header_frame, text=_t("insp_none"), font=("Segoe UI", 9, "bold"),
            bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, activebackground=SURFACE_COLOR,
            relief=tk.FLAT, bd=0, padx=8, pady=2, command=self.on_inspiration_clicked
        )
        self.btn_inspiration.grid(row=2, column=2, columnspan=5, padx=(8, 0), pady=3, sticky="ew")

        # Corpo centrale
        body_frame = ttk.Frame(main_frame)
        body_frame.pack(fill=tk.BOTH, expand=True)

        # Statistiche (Sinistra - 5e Ability Boxes)
        stats_frame = tk.Frame(body_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=6)
        stats_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        tk.Label(stats_frame, text=_t("sheet_attributes"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(pady=(2, 6))

        self.attr_vars = {}
        self.attr_mod_labels = {}
        for attr in ["FOR", "DES", "COS", "INT", "SAG", "CAR"]:
            box = tk.Frame(stats_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=3)
            box.pack(fill=tk.X, pady=3)
            
            attr_text = translate_ability(attr)
            tk.Label(box, text=attr_text, font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack()
            
            var = tk.IntVar(value=10)
            self.attr_vars[attr] = var
            
            mod_lbl = tk.Label(box, text="+0", font=("Georgia", 13, "bold"), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR)
            mod_lbl.pack(pady=1)
            self.attr_mod_labels[attr] = mod_lbl
            
            bottom_row = tk.Frame(box, bg=SURFACE_COLOR_ALT)
            bottom_row.pack(pady=(1, 2))
            
            entry = ttk.Entry(bottom_row, textvariable=var, width=3, justify="center")
            if self.is_connected:
                entry.configure(state="readonly")
                ToolTip(entry, _t("msg_attr_locked_online"))
            entry.pack(side=tk.LEFT, padx=2)
            
            btn = ttk.Button(bottom_row, text="🎲", width=2, command=lambda a=attr, v=var: self.roll_stat(a, v.get()))
            btn.pack(side=tk.LEFT, padx=2)
            
            def make_mod_updater(a=attr, v=var, lbl=mod_lbl):
                def _update(*args):
                    try:
                        val = int(v.get())
                        mod = (val - 10) // 2
                        lbl.config(text=f"+{mod}" if mod >= 0 else str(mod))
                    except (ValueError, tk.TclError):
                        lbl.config(text="+0")
                    if hasattr(self, "update_skill_modifiers"):
                        self.update_skill_modifiers()
                return _update
            var.trace_add("write", make_mod_updater())

        # Abilità
        skills_frame = tk.Frame(body_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=6)
        skills_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        tk.Label(skills_frame, text=_t("sheet_skills"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(pady=(2, 6))
        
        self.skill_vars = {}
        self.skill_mod_labels = {}
        self.skill_map = {
            "Acrobazia": "DES", "Addestrare Animali": "SAG", "Arcano": "INT", "Atletica": "FOR",
            "Furtività": "DES", "Indagare": "INT", "Inganno": "CAR", "Intimidire": "CAR",
            "Intrattenere": "CAR", "Intuizione": "SAG", "Medicina": "SAG", "Natura": "INT",
            "Percezione": "SAG", "Persuasione": "CAR", "Prestidigitazione": "DES",
            "Religione": "INT", "Sopravvivenza": "SAG", "Storia": "INT"
        }
        
        skills_canvas = tk.Canvas(skills_frame, width=280, bg=SURFACE_COLOR, highlightthickness=0)
        skills_scrollbar = ttk.Scrollbar(skills_frame, orient="vertical", command=skills_canvas.yview)
        skills_inner_frame = tk.Frame(skills_canvas, bg=SURFACE_COLOR)
        
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

        def _on_skills_mousewheel(event):
            try:
                skills_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                pass

        skills_frame.bind("<Enter>", lambda e: skills_canvas.bind_all("<MouseWheel>", _on_skills_mousewheel))
        skills_frame.bind("<Leave>", lambda e: skills_canvas.unbind_all("<MouseWheel>"))
        
        # Intestazione colonne
        hdr_prof = tk.Label(skills_inner_frame, text=_t("col_skill_prof"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
        hdr_prof.grid(row=0, column=0, padx=2, pady=(0, 4), sticky="w")
        ToolTip(hdr_prof, _t("tooltip_skill_prof"))
        
        hdr_name = tk.Label(skills_inner_frame, text=_t("col_skill_name"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
        hdr_name.grid(row=0, column=1, padx=4, pady=(0, 4), sticky="w")
        
        hdr_bonus = tk.Label(skills_inner_frame, text=_t("col_skill_bonus"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
        hdr_bonus.grid(row=0, column=2, padx=4, pady=(0, 4), sticky="e")
        ToolTip(hdr_bonus, _t("tooltip_skill_bonus"))
        
        hdr_roll = tk.Label(skills_inner_frame, text=_t("col_skill_roll"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
        hdr_roll.grid(row=0, column=3, padx=2, pady=(0, 4))
        
        for i, (skill, stat) in enumerate(self.skill_map.items(), start=1):
            var = tk.IntVar(value=0)
            self.skill_vars[skill] = var
            var.trace_add("write", lambda *args: self.update_skill_modifiers() if hasattr(self, "update_skill_modifiers") else None)
            
            combo = ttk.Combobox(skills_inner_frame, textvariable=var, values=[0, 1, 2], width=2, state="readonly")
            combo.grid(row=i, column=0, padx=2, pady=2, sticky="w")
            ToolTip(combo, _t("tooltip_skill_combo"))

            skill_text = translate_skill(skill)
            stat_text = translate_ability(stat)
            name_lbl = tk.Label(skills_inner_frame, text=f"{skill_text} ({stat_text})", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_COLOR)
            name_lbl.grid(row=i, column=1, sticky="w", padx=4, pady=2)
            
            mod_lbl = tk.Label(skills_inner_frame, text="+0", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR, width=4, anchor="e")
            mod_lbl.grid(row=i, column=2, padx=4, pady=2, sticky="e")
            self.skill_mod_labels[skill] = mod_lbl
            ToolTip(mod_lbl, _t("tooltip_skill_bonus"))

            roll_btn = ttk.Button(skills_inner_frame, text="🎲", width=2, command=lambda s=skill, st=stat: self.roll_skill(s, st))
            roll_btn.grid(row=i, column=3, padx=2, pady=2)

        # Combattimento (Centro)
        combat_frame = tk.Frame(body_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=6)
        combat_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        tk.Label(combat_frame, text=_t("sheet_tab_actions"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 6))

        # Core 3 badges (CA, Iniziativa, Velocità)
        core_badges = tk.Frame(combat_frame, bg=SURFACE_COLOR)
        core_badges.pack(fill=tk.X, pady=(0, 6))

        # CA
        ca_box = tk.Frame(core_badges, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=4)
        ca_box.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        tk.Label(ca_box, text=f"🛡️ {_t('sheet_armor_class')}", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack()
        self.ac_var = tk.IntVar(value=10)
        ttk.Entry(ca_box, textvariable=self.ac_var, width=3, justify="center").pack(pady=2)

        # Iniziativa
        init_box = tk.Frame(core_badges, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=4)
        init_box.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Label(init_box, text=f"⚡ {_t('sheet_initiative_short')}", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack()
        self.init_var = tk.IntVar(value=0)
        init_sub = tk.Frame(init_box, bg=SURFACE_COLOR_ALT)
        init_sub.pack(pady=2)
        ttk.Entry(init_sub, textvariable=self.init_var, width=3, justify="center").pack(side=tk.LEFT)
        ttk.Button(init_sub, text="🎲", width=2, command=self.roll_initiative).pack(side=tk.LEFT, padx=(2, 0))

        # Velocità
        speed_box = tk.Frame(core_badges, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=4)
        speed_box.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        tk.Label(speed_box, text=f"👟 {_t('sheet_speed_short')}", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack()
        speed_input_row = tk.Frame(speed_box, bg=SURFACE_COLOR_ALT)
        speed_input_row.pack(pady=2)
        self.speed_var = tk.StringVar(value="30")
        ttk.Entry(speed_input_row, textvariable=self.speed_var, width=4, justify="center").pack(side=tk.LEFT, padx=(0, 2))
        self.speed_unit_var = tk.StringVar(value=get_distance_unit())
        self._last_speed_unit = self.speed_unit_var.get()
        self.speed_unit_combo = ttk.Combobox(speed_input_row, textvariable=self.speed_unit_var, values=["ft", "m"], width=3, state="readonly")
        self.speed_unit_combo.pack(side=tk.LEFT)
        self.speed_unit_combo.bind("<<ComboboxSelected>>", self._on_speed_unit_changed)
        ToolTip(self.speed_unit_combo, "Scegli unità di misura: Piedi (ft) o Metri (m)")

        # Vantaggio / Svantaggio selector
        adv_row = tk.Frame(combat_frame, bg=SURFACE_COLOR)
        adv_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(adv_row, text=_t("sheet_dice_roll"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 4))
        self.adv_dis_var = tk.StringVar(value=_t("adv_normal"))
        self.adv_dis_combo = ttk.Combobox(adv_row, textvariable=self.adv_dis_var, values=[_t("adv_normal"), _t("adv_advantage"), _t("adv_disadvantage")], state="readonly", width=12)
        self.adv_dis_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # HP Section
        hp_card = tk.Frame(combat_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=6)
        hp_card.pack(fill=tk.X, pady=(0, 6))
        
        hp_inputs = tk.Frame(hp_card, bg=SURFACE_COLOR_ALT)
        hp_inputs.pack(fill=tk.X, pady=(0, 3))
        tk.Label(hp_inputs, text="HP:", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).pack(side=tk.LEFT, padx=(0, 4))
        self.hp_cur_var = tk.IntVar()
        ttk.Entry(hp_inputs, textvariable=self.hp_cur_var, width=4, justify="center").pack(side=tk.LEFT)
        tk.Label(hp_inputs, text="/", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=3)
        self.hp_max_var = tk.IntVar()
        self.hp_max_entry = ttk.Entry(hp_inputs, textvariable=self.hp_max_var, width=4, justify="center")
        if self.is_connected:
            self.hp_max_entry.configure(state="readonly")
            ToolTip(self.hp_max_entry, _t("msg_hp_max_locked_online"))
        self.hp_max_entry.pack(side=tk.LEFT)

        # Pulsanti Rapidi Danno/Cura (-5, -1, +1, +5)
        hp_quick_row = tk.Frame(hp_card, bg=SURFACE_COLOR_ALT)
        hp_quick_row.pack(fill=tk.X, pady=(2, 2))
        for delta, lbl, st in [(-5, "-5", "Danger.TButton"), (-1, "-1", "Danger.TButton"), (1, "+1", "Success.TButton"), (5, "+5", "Success.TButton")]:
            q_btn = ttk.Button(hp_quick_row, text=lbl, width=3, style=st, command=lambda d=delta: self._adjust_hp_quick(d))
            q_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        
        # Health bar fill
        self.sheet_hp_bg = tk.Frame(hp_card, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, height=10)
        self.sheet_hp_bg.pack(fill=tk.X, pady=(2, 2))
        self.sheet_hp_fill = tk.Frame(self.sheet_hp_bg, bg=ACCENT_GREEN, height=8)
        self.sheet_hp_fill.place(x=0, y=0, width=0, relwidth=0.0, relheight=1.0)
        
        def update_sheet_hp_bar(*args):
            try:
                cur = int(self.hp_cur_var.get())
                mx = max(1, int(self.hp_max_var.get()))
                ratio = max(0.0, min(1.0, cur / mx))
                color = ACCENT_GREEN if ratio > 0.5 else ("#F59F00" if ratio > 0.25 else ACCENT_RED)
                self.sheet_hp_fill.config(bg=color)
                self.sheet_hp_fill.place(x=0, y=0, width=0, relwidth=ratio, relheight=1.0)
            except (ValueError, tk.TclError): pass
        self.hp_cur_var.trace_add("write", update_sheet_hp_bar)
        self.hp_max_var.trace_add("write", update_sheet_hp_bar)

        # Rest buttons
        btn_frame_rest = tk.Frame(combat_frame, bg=SURFACE_COLOR)
        btn_frame_rest.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btn_frame_rest, text=_t("sheet_short_rest"), command=self.short_rest).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(btn_frame_rest, text=_t("sheet_long_rest"), command=self.long_rest, style="Primary.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

        # Death Saves
        self.death_saves_frame = tk.Frame(combat_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=6)
        self.death_saves_frame.pack(fill=tk.X, pady=(0, 6))
        
        tk.Label(self.death_saves_frame, text=_t("sheet_death_saves"), font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(anchor="w")
        
        self.ds_succ_vars = [tk.BooleanVar() for _ in range(3)]
        self.ds_fail_vars = [tk.BooleanVar() for _ in range(3)]
        
        ds_subframe = tk.Frame(self.death_saves_frame, bg=SURFACE_COLOR_ALT)
        ds_subframe.pack(pady=4)
        
        tk.Label(ds_subframe, text=f"{_t('sheet_successes')[:4]}:", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_GREEN).grid(row=0, column=0, sticky="e", padx=(0, 2))
        for i in range(3):
            cb = ttk.Checkbutton(ds_subframe, variable=self.ds_succ_vars[i], state=tk.DISABLED)
            cb.grid(row=0, column=i+1, padx=1)
            
        tk.Label(ds_subframe, text=f" {_t('sheet_failures')[:4]}:", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_RED).grid(row=0, column=4, sticky="e", padx=(4, 2))
        for i in range(3):
            cb = ttk.Checkbutton(ds_subframe, variable=self.ds_fail_vars[i], state=tk.DISABLED)
            cb.grid(row=0, column=i+5, padx=1)
            
        self.ds_roll_btn = ttk.Button(self.death_saves_frame, text=f"🎲 {_t('sheet_death_saves')}", command=self.roll_death_save, style="Gold.TButton")
        self.ds_roll_btn.pack(fill=tk.X, pady=(4, 0))
        self.hp_cur_var.trace_add("write", lambda *args: self.update_death_saves_ui())
        
        death_label_container = tk.Frame(combat_frame, bg=SURFACE_COLOR)
        death_label_container.pack(fill=tk.X, pady=4)
        self.death_label = tk.Label(death_label_container, text=_t("sheet_you_are_dead"), fg=ACCENT_RED, bg=SURFACE_COLOR, font=("Georgia", 16, "bold"))
        self.death_label.grid(row=0, column=0, padx=10, pady=5)
        self.death_label.grid_remove()

        # Tab Notebook (Destra per note/inventario/incantesimi)
        tabs_frame = ttk.Frame(body_frame)
        tabs_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(tabs_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.text_widgets = {}
        tabs_def = [
            (_t("sheet_tab_weapons"), "weapons"),
            (_t("sheet_tab_inventory"), "inventory_grid"),
            (_t("sheet_tab_features"), "features"),
            (_t("sheet_tab_spellbook"), "spellbook"),
            (_t("sheet_tab_journal"), "journal_notes"),
            (_t("sheet_tab_quick_notes"), "notes")
        ]
        for tab_name, attr in tabs_def:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=tab_name)
            
            if attr == "weapons":
                self.create_weapons_tab(frame)
            elif attr == "inventory_grid":
                self.create_inventory_tab(frame)
            elif attr == "features":
                self.create_features_tab(frame)
            elif attr == "spellbook":
                self.build_spells_tab(frame)
            elif attr == "journal_notes":
                self.create_journal_tab(frame)
            else:
                txt = tk.Text(frame, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=self.default_font, wrap=tk.WORD)
                txt.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
                self.text_widgets[attr] = txt

        if "FOR" in self.attr_vars:
            self.attr_vars["FOR"].trace_add("write", lambda *args: self.calculate_total_weight())

        # Pulsanti (in fondo alla scheda)
        btn_frame = ttk.Frame(main_frame, padding=(0, 10))
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Button(btn_frame, text="📥 Esporta Scheda...", command=self.export_character_dialog).pack(side=tk.LEFT, padx=5)
        
        save_btn = ttk.Button(btn_frame, text=f"{_t('save')} (Ctrl+S)", command=self.save_character, style="Primary.TButton")
        save_btn.pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=_t("cancel"), command=self.destroy).pack(side=tk.RIGHT, padx=5)
        self.bind("<Control-s>", self.save_character)
        self.bind("<Control-S>", self.save_character)

    def create_features_tab(self, parent_frame):
        # 1. Box Risorse Speciali di Classe (Punti Ki, Furore, Ispirazione, ecc.)
        res_card = tk.Frame(parent_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=6)
        res_card.pack(fill=tk.X, padx=4, pady=(4, 6))
        
        hdr_row = tk.Frame(res_card, bg=SURFACE_COLOR_ALT)
        hdr_row.pack(fill=tk.X, pady=(0, 4))
        tk.Label(hdr_row, text="⚡ Risorse di Classe Speciali (Ki, Furore, Ispirazione, ecc.)", font=FONT_BOLD, fg=ACCENT_GOLD, bg=SURFACE_COLOR_ALT).pack(side=tk.LEFT)
        ttk.Button(hdr_row, text="+ Nuova Risorsa", command=self.add_custom_resource_dialog, style="Success.TButton").pack(side=tk.RIGHT)
        
        self.resources_container = tk.Frame(res_card, bg=SURFACE_COLOR_ALT)
        self.resources_container.pack(fill=tk.X, pady=2)
        self.refresh_custom_resources_ui()
        
        # 2. Box Privilegi e Tratti di Classe (Testo)
        txt_hdr = tk.Frame(parent_frame, bg=SURFACE_COLOR)
        txt_hdr.pack(fill=tk.X, padx=4, pady=(4, 2))
        tk.Label(txt_hdr, text="📜 Privilegi, Tratti Razziali e Capacità:", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w")
        
        txt = tk.Text(parent_frame, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=self.default_font, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        self.text_widgets["features"] = txt

    def refresh_custom_resources_ui(self):
        if not hasattr(self, "resources_container") or not self.resources_container.winfo_exists():
            return
        for w in self.resources_container.winfo_children():
            w.destroy()
        
        resources = getattr(self.character, "custom_resources", [])
        if not resources:
            tk.Label(self.resources_container, text="Nessuna risorsa speciale registrata. Clicca '+ Nuova Risorsa' per tracciare Ki, Furore, Ispirazione Bardica, ecc.",
                     font=FONT_SMALL, fg=TEXT_MUTED, bg=SURFACE_COLOR_ALT).pack(anchor="w", pady=4)
            return
            
        for idx, res in enumerate(resources):
            r_name = res.get("name", "Risorsa")
            cur = res.get("current", 0)
            mx = res.get("max", 0)
            rst = res.get("reset_on", "long")
            rst_lbl = "Riposo Breve" if rst == "short" else "Riposo Lungo"
            
            row = tk.Frame(self.resources_container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=3)
            row.pack(fill=tk.X, pady=2)
            
            tk.Label(row, text=f"★ {r_name}", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR, width=24, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=f"[{rst_lbl}]", font=FONT_SMALL, fg=TEXT_MUTED, bg=SURFACE_COLOR, width=14, anchor="w").pack(side=tk.LEFT)
            
            val_lbl = tk.Label(row, text=f"{cur} / {mx}", font=FONT_BOLD, fg=ACCENT_GOLD, bg=SURFACE_COLOR, width=8, anchor="center")
            
            def make_adjust(i=idx, delta=1, v_lbl=val_lbl):
                def _cmd():
                    res_obj = self.character.custom_resources[i]
                    res_obj["current"] = max(0, min(res_obj.get("max", 0), res_obj.get("current", 0) + delta))
                    v_lbl.config(text=f"{res_obj['current']} / {res_obj.get('max', 0)}")
                    self.manager.save_characters()
                return _cmd

            def make_delete(i=idx):
                def _del():
                    if messagebox.askyesno("Elimina Risorsa", f"Vuoi eliminare la risorsa '{self.character.custom_resources[i].get('name')}'?"):
                        self.character.custom_resources.pop(i)
                        self.manager.save_characters()
                        self.refresh_custom_resources_ui()
                return _del

            ttk.Button(row, text="-", width=2, command=make_adjust(idx, -1)).pack(side=tk.LEFT, padx=1)
            val_lbl.pack(side=tk.LEFT, padx=2)
            ttk.Button(row, text="+", width=2, command=make_adjust(idx, 1)).pack(side=tk.LEFT, padx=1)
            ttk.Button(row, text="🗑", width=2, command=make_delete(idx)).pack(side=tk.RIGHT, padx=2)

    def add_custom_resource_dialog(self):
        name = simpledialog.askstring("Nuova Risorsa di Classe", "Nome risorsa (es. Punti Ki, Furore, Ispirazione Bardica):", parent=self)
        if not name or not name.strip():
            return
        mx = simpledialog.askinteger("Usi Massimi", "Numero massimo di utilizzi:", initialvalue=3, minvalue=1, maxvalue=999, parent=self)
        if not mx:
            return
        is_short = messagebox.askyesno("Ricarica Risorsa", "Questa risorsa si ricarica con un Riposo Breve?\n\n(Sì = Riposo Breve, No = Riposo Lungo)", parent=self)
        reset_on = "short" if is_short else "long"
        
        if not hasattr(self.character, "custom_resources") or not isinstance(self.character.custom_resources, list):
            self.character.custom_resources = []
            
        self.character.custom_resources.append({
            "name": name.strip(),
            "current": mx,
            "max": mx,
            "reset_on": reset_on
        })
        self.manager.save_characters()
        self.refresh_custom_resources_ui()

    def export_character_dialog(self):
        CharacterSheetUI.open_export_character_dialog(self, self.character)

    @staticmethod
    def open_export_character_dialog(parent, character):
        from tkinter import filedialog
        from client.pdf_sheet_generator import generate_character_pdf
        import re
        import json

        dialog = tk.Toplevel(parent)
        dialog.title("Esporta Scheda Personaggio")
        dialog.minsize(460, 280)
        dialog.resizable(False, False)
        dialog.transient(parent)
        apply_modern_window_style(dialog)

        container = tk.Frame(dialog, bg=SURFACE_COLOR, padx=20, pady=18)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            container,
            text="Esportazione Personaggio",
            font=FONT_HEADER,
            bg=SURFACE_COLOR,
            fg=ACCENT_GOLD
        ).pack(anchor="w", pady=(0, 4))

        tk.Label(
            container,
            text="Scegli il formato desiderato per l'esportazione:",
            font=FONT_MAIN,
            bg=SURFACE_COLOR,
            fg=TEXT_MUTED
        ).pack(anchor="w", pady=(0, 15))

        char_data = character.to_dict() if hasattr(character, "to_dict") else character
        char_name = character.name if hasattr(character, "name") else char_data.get("name", "personaggio")
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', char_name or "personaggio")

        def export_pdf():
            template_path = filedialog.askopenfilename(
                parent=dialog,
                title="Seleziona il modello PDF vuoto (dnd_blankcharactersheet_it.pdf)",
                filetypes=[("Modello PDF (*.pdf)", "*.pdf"), ("Tutti i file", "*.*")]
            )
            if not template_path:
                return

            file_path = filedialog.asksaveasfilename(
                parent=dialog,
                title="Salva Scheda Ufficiale D&D 5e (PDF)",
                initialfile=f"{safe_name}_scheda.pdf",
                defaultextension=".pdf",
                filetypes=[("Documento PDF", "*.pdf")]
            )
            if not file_path:
                return
            dialog.destroy()
            try:
                generate_character_pdf(char_data, file_path, template_path=template_path)
                messagebox.showinfo(
                    "Esportazione Completata",
                    f"Scheda PDF ufficiale generata con successo in:\n{file_path}\n\n"
                    "Il documento a 3 pagine è pronto per la visualizzazione e la stampa!",
                    parent=parent
                )
            except Exception as e:
                messagebox.showerror(
                    "Errore Esportazione PDF",
                    f"Si è verificato un errore durante la generazione della scheda PDF:\n{e}",
                    parent=parent
                )

        def export_json():
            file_path = filedialog.asksaveasfilename(
                parent=dialog,
                title="Esporta Dati Personaggio (JSON)",
                initialfile=f"{safe_name}.json",
                defaultextension=".json",
                filetypes=[("File JSON", "*.json")]
            )
            if not file_path:
                return
            dialog.destroy()
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(char_data, f, indent=2, ensure_ascii=False)
                messagebox.showinfo(
                    "Esportazione Completata",
                    f"Dati personaggio salvati con successo in:\n{file_path}",
                    parent=parent
                )
            except Exception as e:
                messagebox.showerror(
                    "Errore Salvataggio JSON",
                    f"Si è verificato un errore durante il salvataggio dei dati JSON:\n{e}",
                    parent=parent
                )

        # Card Opzione PDF
        pdf_card = tk.Frame(container, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        pdf_card.pack(fill=tk.X, pady=(0, 10))

        pdf_top = tk.Frame(pdf_card, bg=SURFACE_COLOR_ALT)
        pdf_top.pack(fill=tk.X)

        tk.Label(pdf_top, text="📄 Scheda Ufficiale D&D 5e (PDF)", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).pack(side=tk.LEFT)
        btn_pdf = ttk.Button(pdf_top, text="Esporta PDF", style="Primary.TButton", command=export_pdf)
        btn_pdf.pack(side=tk.RIGHT)

        tk.Label(
            pdf_card,
            text="Seleziona il modello PDF vuoto (es. dnd_blankcharactersheet_it.pdf) per compilare automaticamente la scheda a 3 pagine.",
            font=FONT_SMALL,
            bg=SURFACE_COLOR_ALT,
            fg=TEXT_MUTED,
            wraplength=400,
            justify="left"
        ).pack(anchor="w", pady=(3, 0))

        # Card Opzione JSON
        json_card = tk.Frame(container, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        json_card.pack(fill=tk.X, pady=(0, 14))

        json_top = tk.Frame(json_card, bg=SURFACE_COLOR_ALT)
        json_top.pack(fill=tk.X)

        tk.Label(json_top, text="💾 File Dati Personaggio (JSON)", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).pack(side=tk.LEFT)
        btn_json = ttk.Button(json_top, text="Esporta JSON", command=export_json)
        btn_json.pack(side=tk.RIGHT)

        tk.Label(
            json_card,
            text="Salva i dati grezzi del personaggio per backup, modifiche manuali o re-importazione.",
            font=FONT_SMALL,
            bg=SURFACE_COLOR_ALT,
            fg=TEXT_MUTED,
            wraplength=400,
            justify="left"
        ).pack(anchor="w", pady=(3, 0))

        # Barra inferiore con tasto Annulla
        bottom_frame = tk.Frame(container, bg=SURFACE_COLOR)
        bottom_frame.pack(fill=tk.X)
        ttk.Button(bottom_frame, text="Annulla", command=dialog.destroy).pack(side=tk.RIGHT)

        dialog.grab_set()


    @staticmethod
    def _generate_character_html(data):
        if hasattr(data, "to_dict"):
            data = data.to_dict()
        name = data.get("name", "Eroe")
        char_cls = data.get("char_class", "")
        race = data.get("race", "")
        lvl = data.get("level", 1)
        hp = data.get("hp_current", 10)
        hp_max = data.get("hp_max", 10)
        ac = data.get("ac", 10)
        speed = data.get("speed", 30)
        attrs = data.get("attributes", {})
        
        attr_html = ""
        for a in ["FOR", "DES", "COS", "INT", "SAG", "CAR"]:
            val = attrs.get(a, 10)
            mod = (val - 10) // 2
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            attr_html += f"""
            <div style="background:#262930; border:1px solid #3c4048; border-radius:6px; padding:10px; text-align:center; min-width:80px;">
                <div style="font-size:12px; font-weight:bold; color:#f59e0b;">{a}</div>
                <div style="font-size:24px; font-weight:bold; color:#fff;">{val}</div>
                <div style="font-size:14px; font-weight:bold; color:#10b981;">{mod_str}</div>
            </div>
            """
            
        res_html = ""
        for r in data.get("custom_resources", []):
            res_html += f"<li><strong>{r.get('name')}</strong>: {r.get('current')}/{r.get('max')} (Reset: {r.get('reset_on')})</li>"
        if not res_html: res_html = "<li>Nessuna risorsa registrata</li>"
        
        weap_html = ""
        for w in data.get("weapons", []):
            weap_html += f"<tr><td>{w.get('name')}</td><td>{w.get('bonus', 0):+d}</td><td>{w.get('damage_dice', '1d6')} {w.get('damage_type', '')}</td></tr>"
            
        spells_html = ""
        for s in data.get("spellbook", []):
            spells_html += f"<li><strong>Lv {s.get('level', 0)} - {s.get('name')}</strong> ({s.get('time', '-')}, {s.get('range', '-')})</li>"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Scheda: {name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background:#121316; color:#e0e0e0; margin:30px; }}
        .header {{ border-bottom: 2px solid #f59e0b; padding-bottom: 12px; margin-bottom: 20px; }}
        h1 {{ color:#f59e0b; margin:0 0 5px 0; }}
        .badge {{ display:inline-block; background:#1f2937; border:1px solid #374151; border-radius:4px; padding:4px 10px; margin-right:8px; font-size:14px; }}
        .stats-grid {{ display:flex; gap:12px; margin:20px 0; flex-wrap:wrap; }}
        .card {{ background:#1a1c23; border:1px solid #2d3748; border-radius:8px; padding:15px; margin-bottom:20px; }}
        table {{ width:100%; border-collapse:collapse; }}
        th, td {{ border:1px solid #374151; padding:8px; text-align:left; }}
        th {{ background:#2d3748; color:#f59e0b; }}
        @media print {{ body {{ background:#fff; color:#000; }} .card {{ border:1px solid #ccc; background:#fff; }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{name}</h1>
        <div>
            <span class="badge">Razza: {race}</span>
            <span class="badge">Classe: {char_cls} Lv {lvl}</span>
            <span class="badge">🛡️ CA: {ac}</span>
            <span class="badge">❤️ PV: {hp} / {hp_max}</span>
            <span class="badge">👟 Velocità: {speed}</span>
        </div>
    </div>
    
    <h2>Caratteristiche Base</h2>
    <div class="stats-grid">{attr_html}</div>
    
    <div class="card">
        <h3>⚡ Risorse di Classe Speciali</h3>
        <ul>{res_html}</ul>
    </div>
    
    <div class="card">
        <h3>⚔️ Armi e Attacchi</h3>
        <table>
            <tr><th>Arma</th><th>Bonus Txc</th><th>Danno</th></tr>
            {weap_html}
        </table>
    </div>
    
    <div class="card">
        <h3>📖 Grimorio & Incantesimi</h3>
        <ul>{spells_html}</ul>
    </div>
</body>
</html>
"""

    def create_inventory_tab(self, parent_frame):
        # 1. Borsa delle Monete (Currency Cards)
        currency_box = tk.Frame(parent_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=6)
        currency_box.pack(fill=tk.X, padx=6, pady=(6, 4))
        
        c_hdr = tk.Frame(currency_box, bg=SURFACE_COLOR_ALT)
        c_hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(c_hdr, text=f"💰 {_t('sheet_currency')}", font=FONT_BOLD, fg=ACCENT_GOLD, bg=SURFACE_COLOR_ALT).pack(side=tk.LEFT)
        
        self.currency_total_lbl = tk.Label(c_hdr, text=f"{_t('sheet_currency_total')}: ≈ 0.00 MO", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR_ALT)
        self.currency_total_lbl.pack(side=tk.RIGHT)
        ToolTip(self.currency_total_lbl, "Valore totale stimato in Monete d'Oro (1 MO = 10 MA = 100 MR, 1 MP = 10 MO, 1 ME = 0.5 MO)")

        cards_row = tk.Frame(currency_box, bg=SURFACE_COLOR_ALT)
        cards_row.pack(fill=tk.X, pady=2)
        
        COIN_CONFIG = [
            ("MR", "coin_cp_title", "coin_cp_sub", "tooltip_coin_cp", "#C87D55", "#241E1A"),
            ("MA", "coin_sp_title", "coin_sp_sub", "tooltip_coin_sp", "#CBD5E1", "#1E242B"),
            ("ME", "coin_ep_title", "coin_ep_sub", "tooltip_coin_ep", "#38BDF8", "#1A232E"),
            ("MO", "coin_gp_title", "coin_gp_sub", "tooltip_coin_gp", "#F1C40F", "#2B2615"),
            ("MP", "coin_pp_title", "coin_pp_sub", "tooltip_coin_pp", "#DDD6FE", "#231F33"),
        ]
        
        self.currency_vars = {}
        for coin, title_k, sub_k, tip_k, color, bg_tint in COIN_CONFIG:
            card = tk.Frame(cards_row, bg=bg_tint, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=4)
            card.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=3)
            
            lbl_title = tk.Label(card, text=_t(title_k), font=("Segoe UI", 9, "bold"), fg=color, bg=bg_tint)
            lbl_title.pack(side=tk.TOP, pady=(1, 2))
            
            var = tk.IntVar(value=0)
            self.currency_vars[coin] = var
            var.trace_add("write", lambda *args: self.update_currency_total())
            
            entry = ttk.Entry(card, textvariable=var, width=6, justify="center")
            entry.pack(side=tk.TOP, pady=2)
            
            lbl_sub = tk.Label(card, text=_t(sub_k), font=("Segoe UI", 7), fg=TEXT_MUTED, bg=bg_tint)
            lbl_sub.pack(side=tk.TOP, pady=(1, 1))
            
            ToolTip(card, _t(tip_k))
            ToolTip(lbl_title, _t(tip_k))
            ToolTip(entry, _t(tip_k))

        if self.is_connected:
            btn_req_currency = ttk.Button(currency_box, text=_t("btn_request_currency"), command=self.open_request_currency_dialog, style="Gold.TButton")
            btn_req_currency.pack(fill=tk.X, pady=(4, 2))

        # 2. Toolbar & Status Bar (Sintonia)
        inv_bar = tk.Frame(parent_frame, bg=BG_COLOR)
        inv_bar.pack(fill=tk.X, padx=6, pady=(4, 2))
        
        tk.Label(inv_bar, text=f"🎒 {_t('sheet_tab_inventory')} (25 Slot)", font=FONT_BOLD, fg=ACCENT_GOLD, bg=BG_COLOR).pack(side=tk.LEFT)
        
        self.attunement_label = tk.Label(inv_bar, text=_t("sheet_attunement_count", count=0), font=FONT_BOLD, fg=ACCENT_BLUE, bg=BG_COLOR)
        self.attunement_label.pack(side=tk.RIGHT, padx=4)
        ToolTip(self.attunement_label, "Oggetti Magici Sintonizzati (Regola 5e: Massimo 3 oggetti attivi contemporaneamente)")

        # 3. Lista Griglia 25 Slot (Canvas Dark con auto-stretch e zero bordi bianchi)
        list_frame = tk.Frame(parent_frame, bg=BG_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)
        
        canvas = tk.Canvas(list_frame, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_canvas_resize(e):
            canvas.itemconfig(canvas_window, width=e.width)
        canvas.bind("<Configure>", _on_canvas_resize)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                pass
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        
        # Intestazione Colonne
        hdr_frame = tk.Frame(scrollable_frame, bg=SURFACE_COLOR_ALT, padx=4, pady=3)
        hdr_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
        
        tk.Label(hdr_frame, text="#", font=FONT_BOLD, fg=TEXT_MUTED, bg=SURFACE_COLOR_ALT, width=3).pack(side=tk.LEFT)
        tk.Label(hdr_frame, text=_t("sheet_item"), font=FONT_BOLD, fg=TEXT_MUTED, bg=SURFACE_COLOR_ALT).pack(side=tk.LEFT, padx=6, expand=True, fill=tk.X)
        tk.Label(hdr_frame, text=_t("sheet_weight_col"), font=FONT_BOLD, fg=TEXT_MUTED, bg=SURFACE_COLOR_ALT, width=10).pack(side=tk.RIGHT, padx=4)
        tk.Label(hdr_frame, text="🔮 " + _t("sheet_attunement"), font=FONT_BOLD, fg=TEXT_MUTED, bg=SURFACE_COLOR_ALT, width=8).pack(side=tk.RIGHT, padx=4)

        self.inventory_buttons = []
        self.weight_vars = []
        self.attuned_vars = []
        
        for i in range(25):
            row_bg = SURFACE_COLOR if (i % 2 == 0) else SURFACE_COLOR_ALT
            row_frame = tk.Frame(scrollable_frame, bg=row_bg, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=2)
            row_frame.pack(fill=tk.X, padx=2, pady=1)
            
            # Indice slot #i+1
            lbl_idx = tk.Label(row_frame, text=f"#{i+1:02d}", font=FONT_SMALL, fg=TEXT_MUTED, bg=row_bg, width=3)
            lbl_idx.pack(side=tk.LEFT, padx=(2, 4))
            
            # Bottone Oggetto
            btn = ttk.Button(row_frame, text=_t("sheet_empty_slot_desc"), command=lambda idx=i: self.on_inventory_click(idx), style="Slot.TButton")
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
            self.inventory_buttons.append(btn)
            
            # Peso
            w_frame = tk.Frame(row_frame, bg=row_bg)
            w_frame.pack(side=tk.RIGHT, padx=4)
            w_var = tk.DoubleVar(value=0.0)
            w_var.trace_add("write", lambda *args: self.calculate_total_weight())
            w_entry = ttk.Entry(w_frame, textvariable=w_var, width=5, justify="center")
            w_entry.pack(side=tk.LEFT)
            tk.Label(w_frame, text="lbs", font=FONT_SMALL, fg=TEXT_MUTED, bg=row_bg).pack(side=tk.LEFT, padx=1)
            self.weight_vars.append(w_var)
            
            # Sintonia
            a_frame = tk.Frame(row_frame, bg=row_bg)
            a_frame.pack(side=tk.RIGHT, padx=6)
            a_var = tk.BooleanVar(value=False)
            a_var.trace_add("write", lambda *args, idx=i: self.check_attunement(idx))
            cb = ttk.Checkbutton(a_frame, variable=a_var)
            cb.pack(side=tk.LEFT)
            self.attuned_vars.append(a_var)
            ToolTip(cb, "Sintonizza questo oggetto magico (Max 3 contemporaneamente)")

        # 4. Barra Inferiore (Peso, Capacità di Carico e Pulsanti)
        bottom_frame = tk.Frame(parent_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=6)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=6, pady=4)
        
        weight_row = tk.Frame(bottom_frame, bg=SURFACE_COLOR_ALT)
        weight_row.pack(fill=tk.X, pady=(0, 4))
        
        self.weight_label = tk.Label(weight_row, text=_t("sheet_total_weight", current="0.0", max="150"), font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR_ALT)
        self.weight_label.pack(side=tk.LEFT)
        
        self.weight_bar = ttk.Progressbar(weight_row, length=180, mode='determinate')
        self.weight_bar.pack(side=tk.RIGHT, padx=4)
        
        btn_bar = tk.Frame(bottom_frame, bg=SURFACE_COLOR_ALT)
        btn_bar.pack(fill=tk.X, pady=(4, 0))
        
        compendium_btn = ttk.Button(btn_bar, text=_t("sheet_search_compendium"), command=self.open_inventory_compendium)
        compendium_btn.pack(side=tk.LEFT, padx=2)
        
        custom_btn = ttk.Button(btn_bar, text=_t("sheet_add_custom_item"), command=self.open_custom_item_dialog)
        custom_btn.pack(side=tk.LEFT, padx=4)
        
        btn_give_gold = ttk.Button(btn_bar, text=_t("sheet_give_gold_btn"), command=self.on_give_gold_click, style="Gold.TButton")
        btn_give_gold.pack(side=tk.RIGHT, padx=2)

    def update_currency_total(self, *args):
        if not hasattr(self, "currency_vars") or not hasattr(self, "currency_total_lbl"):
            return
        try:
            mr = self.currency_vars.get("MR", tk.IntVar(value=0)).get()
            ma = self.currency_vars.get("MA", tk.IntVar(value=0)).get()
            me = self.currency_vars.get("ME", tk.IntVar(value=0)).get()
            mo = self.currency_vars.get("MO", tk.IntVar(value=0)).get()
            mp = self.currency_vars.get("MP", tk.IntVar(value=0)).get()
            total_gp = mo + (mp * 10.0) + (me * 0.5) + (ma * 0.1) + (mr * 0.01)
            is_it = (get_language() == "it")
            unit = "MO" if is_it else "gp"
            self.currency_total_lbl.config(
                text=f"{_t('sheet_currency_total')}: ≈ {total_gp:.2f} {unit}"
            )
        except (ValueError, tk.TclError, KeyError):
            pass

    def open_request_currency_dialog(self):
        if not self.is_connected:
            return
        win = tk.Toplevel(self)
        win.transient(self)
        win.grab_set()
        apply_modern_window_style(win)
        win.title(_t("title_request_currency"))
        win.minsize(380, 320)
        
        body = tk.Frame(win, bg=SURFACE_COLOR, padx=16, pady=14)
        body.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(body, text=f"🤝 {_t('title_request_currency')}", font=FONT_TITLE, fg=ACCENT_GOLD, bg=SURFACE_COLOR).pack(anchor="w", pady=(0, 10))
        
        tk.Label(body, text=_t("lbl_request_coin"), font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w", pady=(2, 1))
        coin_opts = ["MO (Oro / Gold)", "MA (Argento / Silver)", "MR (Rame / Copper)", "ME (Electrum)", "MP (Platino / Platinum)"]
        coin_combo = ttk.Combobox(body, values=coin_opts, state="readonly")
        coin_combo.set(coin_opts[0])
        coin_combo.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(body, text=_t("lbl_request_amount"), font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w", pady=(2, 1))
        amount_var = tk.IntVar(value=10)
        amt_entry = ttk.Entry(body, textvariable=amount_var, width=10, justify="center")
        amt_entry.pack(anchor="w", pady=(0, 8))
        
        tk.Label(body, text=_t("lbl_request_reason"), font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w", pady=(2, 1))
        reason_text = tk.Text(body, height=3, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_MAIN, wrap=tk.WORD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        reason_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        def submit_request():
            try:
                amt = int(amount_var.get())
            except (ValueError, tk.TclError):
                amt = 0
            if amt <= 0:
                messagebox.showwarning("Quantità Non Valida", "Inserisci una quantità positiva di monete.", parent=win)
                return
            
            sel = coin_combo.get()
            coin_code = "MO"
            if "MA" in sel: coin_code = "MA"
            elif "MR" in sel: coin_code = "MR"
            elif "ME" in sel: coin_code = "ME"
            elif "MP" in sel: coin_code = "MP"
            
            reason_val = reason_text.get("1.0", tk.END).strip()
            
            if self.request_currency_callback:
                self.request_currency_callback(coin_code, amt, reason_val)
            
            win.destroy()
            messagebox.showinfo("Richiesta Inviata", _t("msg_request_currency_sent", amount=amt, coin=coin_code), parent=self)
            
        btn_box = tk.Frame(body, bg=SURFACE_COLOR)
        btn_box.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_box, text="Invia Richiesta al Master", command=submit_request, style="Gold.TButton").pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_box, text="Annulla", command=win.destroy).pack(side=tk.RIGHT, padx=4)

    def calculate_total_weight(self):
        if not hasattr(self, 'weight_vars') or not hasattr(self, 'weight_label'):
            return
        total = 0.0
        for i in range(25):
            if i < len(self.character.inventory_grid):
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
        
        if hasattr(self, 'weight_bar'):
            self.weight_bar['maximum'] = max(1.0, max_weight)
            self.weight_bar['value'] = min(max_weight, total)
        
        if total > max_weight:
            self.weight_label.config(
                text=f"{_t('sheet_total_weight', current=f'{total:.1f}', max=max_weight)} {_t('sheet_encumbered')}",
                fg=ACCENT_RED
            )
        else:
            self.weight_label.config(
                text=_t("sheet_total_weight", current=f"{total:.1f}", max=max_weight),
                fg=TEXT_COLOR
            )

    def check_attunement(self, changed_idx=None):
        if not hasattr(self, 'attuned_vars'): return
        attuned_count = sum(1 for var in self.attuned_vars if var.get())
        if hasattr(self, 'attunement_label'):
            color = ACCENT_RED if attuned_count > 3 else (ACCENT_GOLD if attuned_count == 3 else ACCENT_BLUE)
            self.attunement_label.config(
                text=_t("sheet_attunement_count", count=attuned_count),
                fg=color
            )
        if attuned_count > 3 and changed_idx is not None:
            messagebox.showwarning("Sintonia", "Non puoi sintonizzarti con più di 3 oggetti contemporaneamente!")
            self.attuned_vars[changed_idx].set(False)

    def build_spells_tab(self, parent_frame):
        slots_frame = ttk.LabelFrame(parent_frame, text=_t("sheet_spell_slots_header"))
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
        
        base_lvl = int(spell.get('level', 0))
        upcast_var = tk.IntVar(value=max(1, base_lvl) if base_lvl > 0 else 0)
        
        if base_lvl > 0:
            upcast_row = tk.Frame(win, bg="#1e1e1e")
            upcast_row.pack(fill=tk.X, padx=10, pady=(0, 6))
            tk.Label(upcast_row, text="⚡ Lancia a Livello (Upcasting):", font=FONT_BOLD, fg=ACCENT_GOLD, bg="#1e1e1e").pack(side=tk.LEFT, padx=(0, 6))
            
            levels_available = []
            for l in range(base_lvl, 10):
                l_str = str(l)
                cur_slots = 0
                if l_str in self.slot_vars:
                    cur_slots = self.slot_vars[l_str]["current"].get()
                levels_available.append(f"Livello {l} ({cur_slots} slot rimasti)")
                
            upcast_combo = ttk.Combobox(upcast_row, values=levels_available, state="readonly", width=26)
            upcast_combo.current(0)
            upcast_combo.pack(side=tk.LEFT)
            
            def on_upcast_change(e):
                sel_idx = upcast_combo.current()
                upcast_var.set(base_lvl + sel_idx)
            upcast_combo.bind("<<ComboboxSelected>>", on_upcast_change)

        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, pady=10)
        
        def do_cast():
            lvl = int(spell.get('level', 0))
            cast_level = lvl
            if lvl > 0:
                cast_level = upcast_var.get()
                lvl_str = str(cast_level)
                if lvl_str in self.slot_vars:
                    massimi_var = self.slot_vars[lvl_str]["max"]
                    usati_var = self.slot_vars[lvl_str]["current"]
                    if usati_var.get() > 0:
                        usati_var.set(usati_var.get() - 1)
                        if not hasattr(self.character, "spell_slots"):
                            self.character.spell_slots = {str(i): {"max": 0, "current": 0} for i in range(1, 10)}
                        self.character.spell_slots[lvl_str]["current"] = usati_var.get()
                        self.character.spell_slots[lvl_str]["max"] = massimi_var.get()
                        self.manager.update_character(self.character)
                    else:
                        if not messagebox.askyesno("Slot Esauriti", f"Non hai piu' slot di livello {lvl_str}. Vuoi lanciarlo lo stesso?", parent=win):
                            return
            
            if self.roll_callback:
                upcast_info = f" (Potenziato al Livello {cast_level}!)" if cast_level > lvl else ""
                chat_msg = f"{self.character.name} lancia {spell.get('name', '')}{upcast_info}!"
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
        query = simpledialog.askstring("Cerca Incantesimo", "Nome incantesimo (in italiano o inglese, es. Fireball, Palla di Fuoco, Scudo):")
        if not query: return
        query_clean = query.strip().lower()
        
        # 1. Ricerca locale offline nei manuali indicizzati (PHB 2024, XGtE, TCoE)
        try:
            from common.manuals_manager import ManualsManager
            mgr = ManualsManager()
            spell_hits = [r for r in mgr.search(query_clean, category_filter="Incantesimi")]
            if not spell_hits:
                spell_hits = [r for r in mgr.search(query_clean) if r.get("category") == "Incantesimi" or "spell" in r.get("title", "").lower() or r.get("manual") in ["PHB", "XGtE", "TCoE"]]
            
            if spell_hits:
                top = spell_hits[0]
                ref = top.get("page_ref", "PHB 2024")
                title = top.get("title", query.title())
                summary = top.get("summary", "")
                content = top.get("content", "")
                
                # Deduci livello incantesimo
                lvl = 1
                lvl_m = re.search(r'(\d+)[°\^stndrdth]+\s+level|level\s+(\d+)|livello\s+(\d+)', content, re.IGNORECASE)
                if lvl_m:
                    lvl_str = lvl_m.group(1) or lvl_m.group(2) or lvl_m.group(3)
                    lvl = int(lvl_str)
                elif "cantrip" in content.lower() or "trucchetto" in content.lower():
                    lvl = 0
                
                if messagebox.askyesno("Incantesimo Trovato nel Manuale", f"Trovato in {ref}:\n\n★ {title}\nLivello stimato: {lvl}\n\n{summary}\n\nAggiungere al Grimorio?"):
                    self._add_fetched_spell(title, lvl, "1 Azione", "Vedi manuale", content)
                    return
        except Exception as e:
            print("[GRIMORIO] Errore ricerca manuale offline:", e)

        # 2. Fallback online su dnd5eapi.co
        query_safe = urllib.parse.quote(query_clean)
        
        def fetch_spell():
            try:
                url = f"https://www.dnd5eapi.co/api/spells/?name={query_safe}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3.0) as response:
                    data = json.loads(response.read().decode())
                
                if data.get("count", 0) > 0:
                    spell_url = data["results"][0]["url"]
                    if not spell_url.startswith("http"):
                        spell_url = "https://www.dnd5eapi.co" + spell_url
                    
                    req2 = urllib.request.Request(spell_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req2, timeout=3.0) as response2:
                        spell_data = json.loads(response2.read().decode())
                        
                    name = spell_data.get("name", "")
                    level = spell_data.get("level", 0)
                    time = spell_data.get("casting_time", "")
                    rng = spell_data.get("range", "")
                    desc_list = spell_data.get("desc", [])
                    desc = "\n".join(desc_list) if isinstance(desc_list, list) else str(desc_list)
                    
                    self.after(0, lambda: self._add_fetched_spell(name, level, time, rng, desc))
                else:
                    self.after(0, lambda: messagebox.showinfo("Nessun risultato", f"Incantesimo '{query}' non trovato nei manuali o online."))
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
            total_prof = sum(self.character.skills.values()) if self.character.skills else 0
            if total_prof == 0 and getattr(self.character, "char_class", ""):
                from common.starter_equipment import CLASS_DEFAULT_SKILLS
                char_class = self.character.char_class
                if char_class in CLASS_DEFAULT_SKILLS:
                    for sk in CLASS_DEFAULT_SKILLS[char_class]:
                        if sk in self.character.skills:
                            self.character.skills[sk] = 2 if char_class in ["Ladro", "Rogue"] and sk in ["Furtività", "Prestidigitazione"] else 1
            for k, v in self.character.skills.items():
                if k in self.skill_vars:
                    self.skill_vars[k].set(v)
            
        self.hp_cur_var.set(self.character.hp_current)
        self.hp_max_var.set(self.character.hp_max)
        self.ac_var.set(self.character.ac)
        self.init_var.set(self.character.initiative)
        spd = getattr(self.character, "speed", 30)
        try:
            u = getattr(self.character, "speed_unit", None) or ("m" if float(spd) <= 18 else "ft")
        except (ValueError, TypeError):
            u = "ft"
        self.speed_var.set(str(spd))
        if hasattr(self, "speed_unit_var"):
            self.speed_unit_var.set(u)
            self._last_speed_unit = u
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
            self.initial_currency = dict(self.character.currency)
        else:
            self.initial_currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
                
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
        self.refresh_weapons_list()
        self.update_inspiration_ui()
        self.update_exp_ui()
        self.update_skill_modifiers()

    def update_skill_modifiers(self):
        """Calcola e aggiorna dinamicamente i bonus calcolati (+X / -X) per tutte le abilità."""
        level = 1
        try:
            level = int(self.level_var.get())
        except (ValueError, AttributeError, tk.TclError):
            if hasattr(self, "character") and getattr(self.character, "level", None):
                level = self.character.level
        level = max(1, level)
        prof_bonus = ((level - 1) // 4) + 2

        for skill, stat in self.skill_map.items():
            try:
                stat_val = int(self.attr_vars[stat].get())
            except (KeyError, ValueError, tk.TclError):
                stat_val = 10
            stat_mod = (stat_val - 10) // 2

            prof_level = 0
            if skill in self.skill_vars:
                try:
                    prof_level = int(self.skill_vars[skill].get())
                except (ValueError, tk.TclError):
                    prof_level = 0

            total_mod = stat_mod + (prof_bonus * prof_level)
            mod_str = f"+{total_mod}" if total_mod >= 0 else str(total_mod)

            lbl = self.skill_mod_labels.get(skill)
            if lbl:
                fg_color = TEXT_COLOR
                if prof_level == 2:
                    fg_color = ACCENT_GREEN
                elif prof_level == 1:
                    fg_color = ACCENT_GOLD
                elif total_mod < 0:
                    fg_color = ACCENT_RED
                lbl.config(text=mod_str, fg=fg_color)

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
                name = item.get("name", _t("sheet_item"))
                qty = item.get("qty", 1)
                icon = get_item_icon(item)
                item_type = item.get("type", "")
                type_str = f" [{item_type}]" if item_type else ""
                short_name = name[:20] + ".." if len(name) > 20 else name
                btn.config(text=f"{icon} {short_name} (x{qty}){type_str}", style="SlotFilled.TButton")
                if hasattr(self, 'weight_vars') and i < len(self.weight_vars):
                    self.weight_vars[i].set(item.get("weight", 0.0))
                if hasattr(self, 'attuned_vars') and i < len(self.attuned_vars):
                    self.attuned_vars[i].set(item.get("attuned", False))
                desc = item.get("desc", "")
                weight = item.get("weight", 0.0)
                tip_text = f"{name} (x{qty})\nTipo: {item_type}\nPeso: {weight} lbs\n\n{desc}" if desc else f"{name} (x{qty})\nTipo: {item_type}\nPeso: {weight} lbs"
                ToolTip(btn, tip_text)
            else:
                btn.config(text=f"➕ {_t('sheet_empty_slot_desc')}", style="Slot.TButton")
                ToolTip(btn, _t("sheet_empty_slot_desc"))
                if hasattr(self, 'weight_vars') and i < len(self.weight_vars):
                    self.weight_vars[i].set(0.0)
                if hasattr(self, 'attuned_vars') and i < len(self.attuned_vars):
                    self.attuned_vars[i].set(False)
        if hasattr(self, 'check_attunement'):
            self.check_attunement()
        if hasattr(self, 'calculate_total_weight'):
            self.calculate_total_weight()
        if hasattr(self, 'update_currency_total'):
            self.update_currency_total()

    def on_inventory_click(self, idx):
        item = self.character.inventory_grid[idx]
        if not item:
            self.prompt_add_item_dialog(idx)
            return
        self.open_item_details_dialog(idx, item)

    def prompt_add_item_dialog(self, idx):
        win = tk.Toplevel(self)
        win.transient(self)
        win.grab_set()
        apply_modern_window_style(win)
        win.title(f"Aggiungi Oggetto - Slot #{idx+1}")
        win.minsize(360, 220)
        
        container = tk.Frame(win, bg=SURFACE_COLOR, padx=16, pady=16)
        container.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(container, text=f"Slot #{idx+1} Vuoto", font=FONT_TITLE, fg=ACCENT_GOLD, bg=SURFACE_COLOR).pack(pady=(0, 10))
        tk.Label(container, text="Scegli come aggiungere l'oggetto allo zaino:", font=FONT_MAIN, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(pady=(0, 14))
        
        btn_frame = tk.Frame(container, bg=SURFACE_COLOR)
        btn_frame.pack(fill=tk.X, pady=6)
        
        def from_comp():
            win.destroy()
            self.open_inventory_compendium_for_slot(idx)
            
        def from_custom():
            win.destroy()
            self.open_custom_item_dialog(idx)
            
        ttk.Button(btn_frame, text="📚 Cerca nel Compendio 5e", command=from_comp, style="Gold.TButton").pack(fill=tk.X, pady=4)
        ttk.Button(btn_frame, text="✏️ Crea Oggetto Personalizzato", command=from_custom).pack(fill=tk.X, pady=4)
        ttk.Button(btn_frame, text="Annulla", command=win.destroy).pack(fill=tk.X, pady=4)

    def open_custom_item_dialog(self, target_idx=None):
        if target_idx is None:
            for i, it in enumerate(self.character.inventory_grid):
                if not it:
                    target_idx = i
                    break
        if target_idx is None:
            messagebox.showerror("Zaino Pieno", "Non c'è spazio libero nello zaino per un nuovo oggetto!")
            return
            
        win = tk.Toplevel(self)
        win.transient(self)
        win.grab_set()
        apply_modern_window_style(win)
        win.title(f"Nuovo Oggetto - Slot #{target_idx+1}")
        win.minsize(420, 440)
        
        body = tk.Frame(win, bg=SURFACE_COLOR, padx=14, pady=12)
        body.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(body, text=f"✨ Nuovo Oggetto (Slot #{target_idx+1})", font=FONT_TITLE, fg=ACCENT_GOLD, bg=SURFACE_COLOR).pack(anchor="w", pady=(0, 8))
        
        tk.Label(body, text="Nome Oggetto:", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w", pady=(2, 1))
        name_entry = ttk.Entry(body, width=35)
        name_entry.pack(fill=tk.X, pady=(0, 6))
        name_entry.focus_set()
        
        tk.Label(body, text="Tipo / Categoria:", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w", pady=(2, 1))
        type_combo = ttk.Combobox(body, values=["Arma", "Armatura", "Scudo", "Pozione", "Pergamena", "Attrezzi", "Equipaggiamento", "Altro"], state="normal")
        type_combo.set("Equipaggiamento")
        type_combo.pack(fill=tk.X, pady=(0, 6))
        
        qp_frame = tk.Frame(body, bg=SURFACE_COLOR)
        qp_frame.pack(fill=tk.X, pady=4)
        
        tk.Label(qp_frame, text="Quantità:", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(side=tk.LEFT, padx=(0, 4))
        qty_var = tk.IntVar(value=1)
        ttk.Entry(qp_frame, textvariable=qty_var, width=5, justify="center").pack(side=tk.LEFT, padx=(0, 16))
        
        tk.Label(qp_frame, text="Peso Unitario (lbs):", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(side=tk.LEFT, padx=(0, 4))
        weight_var = tk.DoubleVar(value=1.0)
        ttk.Entry(qp_frame, textvariable=weight_var, width=6, justify="center").pack(side=tk.LEFT)
        
        attune_var = tk.BooleanVar(value=False)
        cb_attune = ttk.Checkbutton(body, text="Richiede Sintonia Magica 🔮", variable=attune_var)
        cb_attune.pack(anchor="w", pady=4)
        
        tk.Label(body, text="Descrizione / Proprietà:", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w", pady=(4, 1))
        desc_text = tk.Text(body, height=5, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_MAIN, wrap=tk.WORD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        def save_custom():
            nm = name_entry.get().strip()
            if not nm:
                messagebox.showwarning("Nome Mancante", "Inserisci il nome dell'oggetto.", parent=win)
                return
            entry = {
                "name": nm,
                "type": type_combo.get().strip() or "Equipaggiamento",
                "qty": max(1, qty_var.get()),
                "weight": max(0.0, weight_var.get()),
                "attuned": attune_var.get(),
                "desc": desc_text.get("1.0", tk.END).strip()
            }
            if self.is_connected and self.request_item_callback:
                self.request_item_callback(entry, target_idx)
                win.destroy()
                messagebox.showinfo("Richiesta Inviata", _t("msg_item_approval_sent", item=nm), parent=self)
                return

            self.character.inventory_grid[target_idx] = entry
            self.manager.update_character(self.character)
            if hasattr(self.manager, 'save_characters'):
                self.manager.save_characters()
            self.refresh_inventory_grid()
            win.destroy()
            messagebox.showinfo("Oggetto Creato", f"'{nm}' aggiunto allo slot #{target_idx+1}!")
            
        btn_box = tk.Frame(body, bg=SURFACE_COLOR)
        btn_box.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_box, text="💾 Salva nello Zaino", command=save_custom, style="Gold.TButton").pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_box, text="Annulla", command=win.destroy).pack(side=tk.RIGHT, padx=4)

    def open_item_details_dialog(self, idx, item):
        win = tk.Toplevel(self)
        win.transient(self)
        win.grab_set()
        apply_modern_window_style(win)
        win.title(f"Dettagli Oggetto - Slot #{idx+1}")
        win.minsize(420, 460)
        
        body = tk.Frame(win, bg=SURFACE_COLOR, padx=14, pady=12)
        body.pack(fill=tk.BOTH, expand=True)
        
        icon = get_item_icon(item)
        name = item.get("name", _t("sheet_item"))
        
        hdr = tk.Frame(body, bg=SURFACE_COLOR)
        hdr.pack(fill=tk.X, pady=(0, 8))
        tk.Label(hdr, text=f"{icon} {name}", font=FONT_TITLE, fg=ACCENT_GOLD, bg=SURFACE_COLOR).pack(side=tk.LEFT)
        
        tk.Label(body, text="Nome:", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w", pady=(2, 1))
        name_entry = ttk.Entry(body)
        name_entry.insert(0, name)
        name_entry.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(body, text="Tipo / Categoria:", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w", pady=(2, 1))
        type_combo = ttk.Combobox(body, values=["Arma", "Armatura", "Scudo", "Pozione", "Pergamena", "Attrezzi", "Equipaggiamento", "Altro"])
        type_combo.set(item.get("type", "Equipaggiamento"))
        type_combo.pack(fill=tk.X, pady=(0, 4))
        
        qp_frame = tk.Frame(body, bg=SURFACE_COLOR)
        qp_frame.pack(fill=tk.X, pady=4)
        
        tk.Label(qp_frame, text="Quantità:", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(side=tk.LEFT, padx=(0, 4))
        qty_var = tk.IntVar(value=item.get("qty", 1))
        ttk.Button(qp_frame, text="-", width=2, command=lambda: qty_var.set(max(1, qty_var.get() - 1))).pack(side=tk.LEFT)
        ttk.Entry(qp_frame, textvariable=qty_var, width=4, justify="center").pack(side=tk.LEFT, padx=2)
        ttk.Button(qp_frame, text="+", width=2, command=lambda: qty_var.set(qty_var.get() + 1)).pack(side=tk.LEFT, padx=(0, 14))
        
        tk.Label(qp_frame, text="Peso Unitario (lbs):", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(side=tk.LEFT, padx=(0, 4))
        w_var = tk.DoubleVar(value=item.get("weight", 0.0))
        ttk.Entry(qp_frame, textvariable=w_var, width=5, justify="center").pack(side=tk.LEFT)
        
        attune_var = tk.BooleanVar(value=item.get("attuned", False))
        cb_attune = ttk.Checkbutton(body, text="Oggetto Sintonizzato 🔮", variable=attune_var)
        cb_attune.pack(anchor="w", pady=4)
        
        tk.Label(body, text="Descrizione / Proprietà:", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w", pady=(4, 1))
        desc_text = tk.Text(body, height=5, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_MAIN, wrap=tk.WORD, highlightbackground=BORDER_COLOR, highlightthickness=1)
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        desc_text.insert("1.0", item.get("desc", ""))
        
        btn_frame = tk.Frame(body, bg=SURFACE_COLOR)
        btn_frame.pack(fill=tk.X, pady=4)
        
        def save_item():
            item["name"] = name_entry.get().strip() or name
            item["type"] = type_combo.get().strip() or "Equipaggiamento"
            item["qty"] = max(1, qty_var.get())
            item["weight"] = max(0.0, w_var.get())
            item["attuned"] = attune_var.get()
            item["desc"] = desc_text.get("1.0", tk.END).strip()
            self.refresh_inventory_grid()
            self.manager.update_character(self.character)
            if hasattr(self.manager, 'save_characters'):
                self.manager.save_characters()
            win.destroy()
            
        def discard():
            if messagebox.askyesno("Conferma Scarto", _t("sheet_discard_confirm"), parent=win):
                self.character.inventory_grid[idx] = None
                self.refresh_inventory_grid()
                self.manager.update_character(self.character)
                if hasattr(self.manager, 'save_characters'):
                    self.manager.save_characters()
                win.destroy()
                
        def trade():
            if not hasattr(self, 'players_list_callback') or not hasattr(self, 'trade_callback'):
                messagebox.showinfo("Offline", "Funzione non disponibile offline.", parent=win)
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
                self.manager.update_character(self.character)
                if hasattr(self.manager, 'save_characters'):
                    self.manager.save_characters()
                win.destroy()
            elif target:
                messagebox.showerror("Errore", "Giocatore non trovato.", parent=win)
                
        ttk.Button(btn_frame, text="💾 Salva", command=save_item, style="Gold.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🤝 Dona", command=trade).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🗑️ Scarta", command=discard, style="Danger.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Chiudi", command=win.destroy).pack(side=tk.RIGHT, padx=3)

    def open_inventory_compendium_for_slot(self, slot_idx):
        from server.compendium_ui import CompendiumDialog
        def on_import(item_data, category):
            self.import_from_compendium_to_slot(item_data, category, slot_idx)
        CompendiumDialog(self.master, on_import_callback=on_import, is_dm=False)

    def import_from_compendium_to_slot(self, item_data, category, target_idx=None):
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
            messagebox.showinfo("Importato", f"{item_data.get('name')} importato come Incantesimo!")
            return

        if target_idx is None:
            for i, it in enumerate(self.character.inventory_grid):
                if not it:
                    target_idx = i
                    break
        if target_idx is None:
            messagebox.showerror("Zaino Pieno", "Non c'è spazio nello zaino!")
            return
            
        desc = item_data.get("desc", "")
        if isinstance(desc, list):
            desc = "\n".join(desc)
            
        weight = 0.0
        try:
            weight = float(item_data.get("weight", 0.0) or 0.0)
        except (ValueError, TypeError):
            weight = 0.0
            
        entry = {
            "name": item_data.get("name"),
            "type": category,
            "qty": 1,
            "weight": weight,
            "attuned": False,
            "desc": desc
        }
        if self.is_connected and self.request_item_callback:
            self.request_item_callback(entry, target_idx)
            messagebox.showinfo("Richiesta Inviata", _t("msg_item_approval_sent", item=item_data.get('name')), parent=self)
            return

        self.character.inventory_grid[target_idx] = entry
        self.manager.update_character(self.character)
        if hasattr(self.manager, 'save_characters'):
            self.manager.save_characters()
        self.refresh_inventory_grid()
        messagebox.showinfo("Importato", f"'{item_data.get('name')}' importato nello slot #{target_idx+1}!")

    def open_inventory_compendium(self):
        from server.compendium_ui import CompendiumDialog
        CompendiumDialog(self.master, on_import_callback=self.import_from_compendium, is_dm=False)

    def import_from_compendium(self, item_data, category):
        return self.import_from_compendium_to_slot(item_data, category, None)

    def _adjust_hp_quick(self, delta: int):
        try:
            cur = int(self.hp_cur_var.get())
            mx = max(1, int(self.hp_max_var.get()))
            new_hp = max(0, min(mx, cur + delta))
            self.hp_cur_var.set(new_hp)
        except (ValueError, tk.TclError):
            pass

    def save_character(self, event=None):
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
            spd_raw = float(str(self.speed_var.get()).replace(",", "."))
            self.character.speed = int(spd_raw) if spd_raw == int(spd_raw) else round(spd_raw, 1)
            if hasattr(self, "speed_unit_var"):
                self.character.speed_unit = self.speed_unit_var.get()
                set_distance_unit(self.character.speed_unit)
            
            for attr, txt in self.text_widgets.items():
                val = txt.get("1.0", tk.END).strip()
                setattr(self.character, attr, val)
                
            if not hasattr(self.character, "currency"):
                self.character.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
            currency_blocked = False
            for coin, var in self.currency_vars.items():
                try:
                    val = var.get()
                    if self.is_connected and hasattr(self, "initial_currency"):
                        init_val = self.initial_currency.get(coin, 0)
                        if val > init_val:
                            val = init_val
                            var.set(init_val)
                            currency_blocked = True
                    self.character.currency[coin] = val
                except tk.TclError:
                    pass
            if currency_blocked:
                messagebox.showwarning("Valuta Bloccata", _t("msg_currency_locked_online"), parent=self)
                
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

    def _on_speed_unit_changed(self, event=None):
        new_u = self.speed_unit_var.get()
        old_u = getattr(self, "_last_speed_unit", new_u)
        if new_u != old_u:
            try:
                cur_val = float(str(self.speed_var.get()).replace(",", "."))
                converted = convert_speed_value(cur_val, old_u, new_u)
                self.speed_var.set(str(converted))
            except (ValueError, TypeError):
                self.speed_var.set("9" if new_u == "m" else "30")
            self._last_speed_unit = new_u
            self.character.speed_unit = new_u
            set_distance_unit(new_u)

    def roll_stat(self, stat_name, stat_val):
        if not self.roll_callback: return
        try:
            val = int(stat_val)
            mod = (val - 10) // 2
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            
            formula = f"1d20{mod_str}"
            adv_state = self.adv_dis_var.get()
            if adv_state in ("Vantaggio", _t("adv_advantage")):
                formula += " adv"
            elif adv_state in ("Svantaggio", _t("adv_disadvantage")):
                formula += " dis"
                
            self.adv_dis_var.set(_t("adv_normal"))
            self.roll_callback(formula, f"Check {stat_name}")
        except (ValueError, tk.TclError):
            pass

    def roll_skill(self, skill_name, stat_name):
        if not self.roll_callback: return
        try:
            stat_val = int(self.attr_vars[stat_name].get())
            stat_mod = (stat_val - 10) // 2
            
            prof_level = self.skill_vars[skill_name].get()
            level = 1
            try:
                level = int(self.level_var.get())
            except (ValueError, AttributeError, tk.TclError):
                level = getattr(self.character, "level", 1) or 1
            prof_bonus = getattr(self.character, "proficiency_bonus", ((max(1, level) - 1) // 4) + 2)
            
            total_mod = stat_mod + (prof_bonus * prof_level)
            mod_str = f"+{total_mod}" if total_mod >= 0 else str(total_mod)
            
            formula = f"1d20{mod_str}"
            adv_state = self.adv_dis_var.get()
            if adv_state in ("Vantaggio", _t("adv_advantage")):
                formula += " adv"
            elif adv_state in ("Svantaggio", _t("adv_disadvantage")):
                formula += " dis"
                
            self.adv_dis_var.set(_t("adv_normal"))
            self.roll_callback(formula, f"Check {skill_name}")
        except (ValueError, tk.TclError):
            pass

    def roll_initiative(self):
        if not self.roll_callback: return
        try:
            des_val = int(self.attr_vars["DES"].get())
            mod = (des_val - 10) // 2
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            
            formula = f"1d20{mod_str}"
            adv_state = self.adv_dis_var.get()
            if adv_state in ("Vantaggio", _t("adv_advantage")):
                formula += " adv"
            elif adv_state in ("Svantaggio", _t("adv_disadvantage")):
                formula += " dis"

            self.adv_dis_var.set(_t("adv_normal"))
            self.roll_callback(formula, "Iniziativa")
        except (ValueError, tk.TclError):
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
        
        healed = self.character.short_rest(spend)
        self.hp_cur_var.set(self.character.hp_current)
        self.manager.update_character(self.character)
        if hasattr(self, "on_save_callback") and self.on_save_callback:
            try: self.on_save_callback(self.character)
            except Exception: pass
        messagebox.showinfo("Riposo Breve", f"Hai speso {spend} Dadi Vita e recuperato {healed} HP! Privilegi di classe ricaricati.")

    def long_rest(self):
        if hasattr(self, 'long_rest_callback') and self.long_rest_callback:
            self.long_rest_callback()
        else:
            if messagebox.askyesno("Riposo Lungo", "Effettuare un riposo lungo?"):
                self.character.long_rest()
                self.load_data()
                self.manager.update_character(self.character)
                if hasattr(self, "on_save_callback") and self.on_save_callback:
                    try: self.on_save_callback(self.character)
                    except Exception: pass
                messagebox.showinfo("Riposo Lungo", "Hai effettuato un riposo lungo! HP, Dadi Vita, Tiri contro la Morte e Slot Incantesimo sono stati recuperati.")

    def roll_death_save(self):
        import random
        roll = random.randint(1, 20)
        if not hasattr(self.character, "death_saves"):
            self.character.death_saves = {"successes": 0, "failures": 0}
            
        succ = self.character.death_saves.get("successes", 0)
        fail = self.character.death_saves.get("failures", 0)
        conds = getattr(self.character, "conditions", [])
        
        flavor = ""
        if roll == 1:
            fail += 2
            flavor = "💀 FALLIMENTO CRITICO (1 Naturale)! (2 fallimenti)"
        elif roll <= 9:
            fail += 1
            flavor = "❌ Fallimento."
        elif roll <= 19:
            succ += 1
            flavor = "✅ Successo."
        elif roll == 20:
            self.character.hp_current = 1
            self.hp_cur_var.set(1)
            succ = 0
            fail = 0
            if "Incosciente" in conds:
                conds.remove("Incosciente")
            flavor = "🌟 SUCCESSO CRITICO (20 Naturale)! Ti risvegli con 1 HP."

        if roll != 20:
            succ = min(3, succ)
            fail = min(3, fail)
            if fail >= 3:
                if "Morto" not in conds:
                    conds.append("Morto")
                flavor += " 💀 Sei MORTO!"
            elif succ >= 3:
                if "Stabilizzato" not in conds:
                    conds.append("Stabilizzato")
                flavor += " 🩹 Ti sei STABILIZZATO!"

        self.character.conditions = conds
        self.character.death_saves["successes"] = succ
        self.character.death_saves["failures"] = fail
        self.update_death_saves_ui()
        self.manager.update_character(self.character)
        if hasattr(self, "on_save_callback") and self.on_save_callback:
            try: self.on_save_callback(self.character)
            except Exception: pass
            
        if self.roll_callback:
            chat_msg = f"💀 Tiro contro la Morte di {self.character.name}: [d20: {roll}] -> {flavor} (Successi: {succ}/3 | Fallimenti: {fail}/3)"
            self.roll_callback("0d0", chat_msg)

        msg = f"Tiro 1d20: {roll}. {flavor}\n(Successi: {succ}/3 | Fallimenti: {fail}/3)"
        messagebox.showinfo("Tiro contro la Morte", msg, parent=self)

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
            self.death_saves_frame.pack(fill=tk.X, pady=(0, 6))
        else:
            self.death_saves_frame.pack_forget()
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



    def update_inspiration_ui(self):
        if not hasattr(self, 'btn_inspiration'): return
        has_insp = getattr(self.character, "has_inspiration", False)
        if has_insp:
            self.btn_inspiration.config(text="⭐ ISPIRAZIONE ATTIVA (Clicca per Usare)", bg=ACCENT_GOLD, fg=TEXT_DARK)
        else:
            self.btn_inspiration.config(text="☆ Nessuna Ispirazione (Assegnata dal DM)", bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED)

    def set_inspiration(self, val: bool):
        self.character.has_inspiration = val
        self.update_inspiration_ui()

    def on_inspiration_clicked(self):
        has_insp = getattr(self.character, "has_inspiration", False)
        if has_insp:
            if messagebox.askyesno("Consuma Ispirazione", "Vuoi consumare l'Ispirazione per impostare VANTAGGIO al tuo prossimo tiro?"):
                self.character.has_inspiration = False
                self.adv_dis_var.set("Vantaggio")
                self.update_inspiration_ui()
                self.manager.save_characters()
                if self.roll_callback:
                    self.roll_callback("0d0", f"⭐ {self.character.name} consuma la propria Ispirazione per ottenere Vantaggio!")
        else:
            messagebox.showinfo("Ispirazione 5e", "L'Ispirazione è un dono conferito dal Dungeon Master per idee brillanti, eroismo o eccellente interpretazione di ruolo!\n\nIl DM può assegnartela dal menu contestuale del tuo token.")

    def create_weapons_tab(self, parent_frame):
        bar = tk.Frame(parent_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=6)
        bar.pack(fill=tk.X, pady=(0, 6))
        
        tk.Label(bar, text="⚔️ Armi & Attacchi Rapidi 5e", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        ttk.Button(bar, text="+ Aggiungi Arma", command=self.open_add_weapon_dialog, style="Gold.TButton").pack(side=tk.RIGHT)
        
        canvas = tk.Canvas(parent_frame, bg=BG_COLOR, highlightthickness=0)
        sb = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.weapons_cards_frame = tk.Frame(canvas, bg=BG_COLOR)
        
        self.weapons_cards_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.weapons_cards_frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.refresh_weapons_list()

    def refresh_weapons_list(self):
        if not hasattr(self, 'weapons_cards_frame'): return
        for child in self.weapons_cards_frame.winfo_children():
            child.destroy()
            
        weapons = getattr(self.character, "weapons", [])
        if not weapons:
            empty_lbl = tk.Label(self.weapons_cards_frame, text="Nessuna arma equipaggiata.\nClicca '+ Aggiungi Arma' per registrare un'arma o attacco!", font=FONT_MAIN, bg=BG_COLOR, fg=TEXT_MUTED, pady=25)
            empty_lbl.pack(fill=tk.X)
            return
            
        for i, w in enumerate(weapons):
            card = tk.Frame(self.weapons_cards_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=8)
            card.pack(fill=tk.X, pady=4, padx=4)
            
            stat_key = w.get("ability", "FOR")
            stat_val = self.character.attributes.get(stat_key, 10)
            mod = (stat_val - 10) // 2
            prof_bonus = getattr(self.character, "proficiency_bonus", 2) if w.get("proficient", True) else 0
            w_bonus = w.get("bonus", 0)
            total_txc = mod + prof_bonus + w_bonus
            txc_str = f"+{total_txc}" if total_txc >= 0 else str(total_txc)
            
            dmg_mod = mod + w_bonus
            dmg_mod_str = f"+{dmg_mod}" if dmg_mod > 0 else (str(dmg_mod) if dmg_mod < 0 else "")
            dice = w.get("damage_dice", "1d8")
            dmg_formula = f"{dice}{dmg_mod_str}"
            dmg_str = f"{dmg_formula} {w.get('damage_type', '')}"
            
            r1 = tk.Frame(card, bg=SURFACE_COLOR)
            r1.pack(fill=tk.X)
            name_lbl = tk.Label(r1, text=w.get("name", "Arma"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD)
            name_lbl.pack(side=tk.LEFT)
            type_lbl = tk.Label(r1, text=f"• {w.get('type', '')}", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
            type_lbl.pack(side=tk.LEFT, padx=6)
            
            prof_badge = "Competente" if w.get("proficient", True) else "Non Comp."
            r2 = tk.Frame(card, bg=SURFACE_COLOR)
            r2.pack(fill=tk.X, pady=(2, 4))
            tk.Label(r2, text=f"Modificatore: {stat_key} ({mod:+d}) | {prof_badge} (+{prof_bonus}) | Magico: +{w_bonus}", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
            
            r3 = tk.Frame(card, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=4)
            r3.pack(fill=tk.X, pady=(2, 6))
            tk.Label(r3, text=f"TxC: {txc_str}", font=("Georgia", 11, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(side=tk.LEFT, padx=(0, 15))
            tk.Label(r3, text=f"Danno: {dmg_str}", font=("Georgia", 11, "bold"), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).pack(side=tk.LEFT)
            
            r4 = tk.Frame(card, bg=SURFACE_COLOR)
            r4.pack(fill=tk.X)
            
            if getattr(self, "attack_callback", None):
                btn_target = ttk.Button(r4, text=f"🎯 Bersaglio ({txc_str})", command=lambda weapon=w, txc=total_txc, dmg=dmg_formula: self.execute_targeted_attack(weapon, txc, dmg), style="Gold.TButton")
                btn_target.pack(side=tk.LEFT, padx=(0, 4))
                btn_attack = ttk.Button(r4, text="🎲 Tira TxC", command=lambda weapon=w, txc=total_txc: self.execute_weapon_attack(weapon, txc), style="Primary.TButton")
                btn_attack.pack(side=tk.LEFT, padx=(0, 4))
            else:
                btn_attack = ttk.Button(r4, text=f"🎯 Colpisci ({txc_str})", command=lambda weapon=w, txc=total_txc: self.execute_weapon_attack(weapon, txc), style="Gold.TButton")
                btn_attack.pack(side=tk.LEFT, padx=(0, 4))
            
            btn_damage = ttk.Button(r4, text="💥 Danno", command=lambda weapon=w, dmod=dmg_mod: self.execute_weapon_damage(weapon, dmod), style="Primary.TButton")
            btn_damage.pack(side=tk.LEFT, padx=(0, 4))
            
            btn_del = ttk.Button(r4, text="🗑️", width=3, command=lambda idx=i: self.remove_weapon(idx))
            btn_del.pack(side=tk.RIGHT)

            btn_edit = ttk.Button(r4, text="✏️", width=3, command=lambda weapon=w, idx=i: self.open_edit_weapon_dialog(weapon, idx))
            btn_edit.pack(side=tk.RIGHT, padx=(0, 4))

    def execute_targeted_attack(self, weapon, total_txc, dmg_str):
        if getattr(self, "attack_callback", None):
            w_name = weapon.get("name", "Arma")
            d_type = weapon.get("damage_type", "Tagliente")
            self.attack_callback(w_name, total_txc, dmg_str, d_type)
        else:
            self.execute_weapon_attack(weapon, total_txc)

    def open_add_weapon_dialog(self):
        def _on_save(w_data):
            if not hasattr(self.character, "weapons"): self.character.weapons = []
            self.character.weapons.append(w_data)
            self.manager.save_characters()
            self.refresh_weapons_list()
        WeaponDialog(self, on_save_callback=_on_save)

    def open_edit_weapon_dialog(self, weapon, idx):
        def _on_save(w_data):
            self.character.weapons[idx] = w_data
            self.manager.save_characters()
            self.refresh_weapons_list()
        WeaponDialog(self, weapon_data=weapon, on_save_callback=_on_save)

    def remove_weapon(self, idx):
        if idx < len(self.character.weapons):
            w_name = self.character.weapons[idx].get("name", "Arma")
            if messagebox.askyesno("Rimuovi Arma", f"Rimuovere l'arma '{w_name}'?"):
                self.character.weapons.pop(idx)
                self.manager.save_characters()
                self.refresh_weapons_list()

    def execute_weapon_attack(self, weapon, total_txc):
        import random
        if getattr(self.character, "has_inspiration", False):
            if messagebox.askyesno("Usa Ispirazione", "Possiedi l'Ispirazione! Vuoi spenderla per ottenere VANTAGGIO a questo attacco?"):
                self.character.has_inspiration = False
                self.update_inspiration_ui()
                self.adv_dis_var.set(_t("adv_advantage"))
                self.manager.save_characters()
                
        adv_state = self.adv_dis_var.get()
        r1 = random.randint(1, 20)
        r2 = random.randint(1, 20)
        
        if adv_state in ("Vantaggio", _t("adv_advantage")):
            base_roll = max(r1, r2)
            rolls_str = f"max({r1}, {r2})"
        elif adv_state in ("Svantaggio", _t("adv_disadvantage")):
            base_roll = min(r1, r2)
            rolls_str = f"min({r1}, {r2})"
        else:
            base_roll = r1
            rolls_str = str(r1)
            
        total = base_roll + total_txc
        txc_sign = f"+{total_txc}" if total_txc >= 0 else str(total_txc)
        w_name = weapon.get("name", "Arma")
        
        is_crit = (base_roll == 20)
        is_fail = (base_roll == 1)
        weapon["_last_crit"] = is_crit
        
        adv_text = f" ({adv_state})" if adv_state not in ("Normale", _t("adv_normal"), "") else ""
        
        if is_crit:
            msg = f"⚔️ {self.character.name} attacca con {w_name}{adv_text}: [d20: {rolls_str}] {txc_sign} = {total} 🌟 COLPO CRITICO (20 Naturale)!"
            messagebox.showinfo("COLPO CRITICO!", f"🌟 COLPO CRITICO!\nUn 20 Naturale con {w_name}!\nIl prossimo tiro dei danni raddoppierà automaticamente i dadi!")
        elif is_fail:
            msg = f"⚔️ {self.character.name} attacca con {w_name}{adv_text}: [d20: {rolls_str}] {txc_sign} = {total} 💀 FALLIMENTO CRITICO (1 Naturale)! Mancato automatico!"
            messagebox.showwarning("FALLIMENTO CRITICO!", f"💀 FALLIMENTO CRITICO!\nUn 1 Naturale con {w_name}: l'attacco manca automaticamente il bersaglio!")
        else:
            msg = f"⚔️ {self.character.name} attacca con {w_name}{adv_text}: [d20: {rolls_str}] {txc_sign} = {total}"
            
        self.adv_dis_var.set(_t("adv_normal"))
        if self.roll_callback:
            self.roll_callback("0d0", msg)
        else:
            messagebox.showinfo("Attacco Eseguito", msg)

    def execute_weapon_damage(self, weapon, dmg_mod):
        import random, re
        dice_expr = weapon.get("damage_dice", "1d8")
        is_crit = weapon.pop("_last_crit", False)
        
        m = re.match(r"(\d+)d(\d+)", dice_expr)
        if m:
            num_dice = int(m.group(1))
            die_sides = int(m.group(2))
        else:
            num_dice = 1
            die_sides = 8
            
        if is_crit:
            num_dice *= 2
            
        rolls = [random.randint(1, die_sides) for _ in range(num_dice)]
        dice_sum = sum(rolls)
        total = max(0, dice_sum + dmg_mod)
        
        w_name = weapon.get("name", "Arma")
        dmg_type = weapon.get("damage_type", "")
        crit_text = " ⭐ CRITICO (Dadi Raddoppiati!)" if is_crit else ""
        mod_sign = f"+{dmg_mod}" if dmg_mod >= 0 else str(dmg_mod)
        
        msg = f"💥 Danni {w_name}{crit_text}: [{'+'.join(map(str, rolls))}] {mod_sign} = {total} danni {dmg_type} ({num_dice}d{die_sides}{mod_sign})"
        if self.roll_callback:
            self.roll_callback("0d0", msg)
        else:
            messagebox.showinfo("Danni", msg)

    def create_journal_tab(self, parent_frame):
        header = tk.Frame(parent_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=6)
        header.pack(fill=tk.X, pady=(0, 6))
        tk.Label(header, text="📜 Diario di Bordo & Note Personali", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        tk.Label(header, text="Appunti di sessione, indizi, nomi e segreti del personaggio", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=10)
        
        txt = tk.Text(parent_frame, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=self.default_font, wrap=tk.WORD,
                      highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=8)
        txt.pack(fill=tk.BOTH, expand=True)
        self.text_widgets["journal_notes"] = txt

    def on_give_gold_click(self):
        if not getattr(self, "give_gold_callback", None) or not getattr(self, "players_list_callback", None):
            messagebox.showinfo("Offline", "Disponibile solo quando connesso a una sessione multiplayer.")
            return
        players = self.players_list_callback()
        if not players:
            messagebox.showinfo("Nessuno", "Nessun altro giocatore connesso.")
            return
        target = simpledialog.askstring("Dona Oro", f"A chi vuoi consegnare le Monete d'Oro?\nGiocatori online: {', '.join(players)}", parent=self)
        if not target or target not in players:
            if target: messagebox.showerror("Errore", "Giocatore non valido.", parent=self)
            return
            
        cur_gold = self.currency_vars.get("MO").get() if "MO" in self.currency_vars else 0
        amount = simpledialog.askinteger("Quantità Oro", f"Quante Monete d'Oro (MO) vuoi donare a {target}?\n(Possiedi: {cur_gold} MO)", minvalue=1, maxvalue=max(1, cur_gold), parent=self)
        if not amount: return
        
        self.give_gold_callback(target, amount)
        self.currency_vars["MO"].set(max(0, cur_gold - amount))


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



class WeaponDialog(tk.Toplevel):
    """Finestra di dialogo moderna per aggiungere o modificare armi del personaggio."""
    def __init__(self, parent, weapon_data=None, on_save_callback=None):
        super().__init__(parent)
        self.weapon_data = weapon_data or {}
        self.on_save_callback = on_save_callback
        is_edit = bool(weapon_data)
        self.title("Modifica Arma" if is_edit else "Nuova Arma da Combattimento")
        self.minsize(420, 440)
        self.transient(parent)
        self.grab_set()
        apply_modern_window_style(self)
        self.configure(bg=BG_COLOR)
        
        container = tk.Frame(self, bg=BG_COLOR, padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(container, text="⚔️ Scheda Arma 5e", font=("Georgia", 14, "bold"), bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 10))
        
        form = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        form.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tk.Label(form, text="Nome Arma:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=0, column=0, sticky="w", pady=4)
        self.name_var = tk.StringVar(value=self.weapon_data.get("name", "Spada Lunga"))
        ttk.Entry(form, textvariable=self.name_var, width=22).grid(row=0, column=1, sticky="ew", pady=4, padx=6)
        
        tk.Label(form, text="Tipo / Proprietà:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=1, column=0, sticky="w", pady=4)
        self.type_var = tk.StringVar(value=self.weapon_data.get("type", "Mischia (Versatile 1d10)"))
        type_combo = ttk.Combobox(form, textvariable=self.type_var, values=[
            "Mischia", "Mischia (Accurata)", "Mischia (Versatile 1d10)", "Mischia (Pesante, Due Mani)",
            "Distanza (Munizioni)", "Distanza (80/320 ft)", "Lancio (Veloce)", "Senz'Armi"
        ], width=20)
        type_combo.grid(row=1, column=1, sticky="ew", pady=4, padx=6)
        
        tk.Label(form, text="Attributo (TxC & Danni):", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=2, column=0, sticky="w", pady=4)
        self.ability_var = tk.StringVar(value=self.weapon_data.get("ability", "FOR"))
        ttk.Combobox(form, textvariable=self.ability_var, values=["FOR", "DES", "INT", "SAG", "CAR", "COS"], state="readonly", width=8).grid(row=2, column=1, sticky="w", pady=4, padx=6)
        
        tk.Label(form, text="Dado Danno:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=3, column=0, sticky="w", pady=4)
        self.dice_var = tk.StringVar(value=self.weapon_data.get("damage_dice", "1d8"))
        ttk.Combobox(form, textvariable=self.dice_var, values=["1d4", "1d6", "1d8", "1d10", "1d12", "2d6", "2d4", "1d20"], width=8).grid(row=3, column=1, sticky="w", pady=4, padx=6)
        
        tk.Label(form, text="Tipo di Danno:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=4, column=0, sticky="w", pady=4)
        self.dmg_type_var = tk.StringVar(value=self.weapon_data.get("damage_type", "Tagliente"))
        ttk.Combobox(form, textvariable=self.dmg_type_var, values=[
            "Tagliente", "Perforante", "Contundente", "Fuoco", "Freddo", "Fulmine", "Acido", "Radioso", "Necrotico", "Forza", "Veleno", "Psichico"
        ], width=14).grid(row=4, column=1, sticky="w", pady=4, padx=6)
        
        tk.Label(form, text="Bonus Magico (+X):", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=5, column=0, sticky="w", pady=4)
        self.bonus_var = tk.IntVar(value=self.weapon_data.get("bonus", 0))
        ttk.Spinbox(form, from_=-5, to=10, textvariable=self.bonus_var, width=5).grid(row=5, column=1, sticky="w", pady=4, padx=6)
        
        self.prof_var = tk.BooleanVar(value=self.weapon_data.get("proficient", True))
        ttk.Checkbutton(form, text="Competente nell'Arma (+ Competenza al TxC)", variable=self.prof_var).grid(row=6, column=0, columnspan=2, sticky="w", pady=8)
        
        btns = tk.Frame(container, bg=BG_COLOR)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Salva Arma", command=self.save, style="Primary.TButton").pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btns, text="Annulla", command=self.destroy).pack(side=tk.RIGHT)

    def save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Nome Mancante", "Inserisci il nome dell'arma.", parent=self)
            return
            
        data = {
            "name": name,
            "type": self.type_var.get().strip(),
            "ability": self.ability_var.get().strip(),
            "damage_dice": self.dice_var.get().strip(),
            "damage_type": self.dmg_type_var.get().strip(),
            "bonus": int(self.bonus_var.get()),
            "proficient": bool(self.prof_var.get())
        }
        if self.on_save_callback:
            self.on_save_callback(data)
        self.destroy()

open_export_character_dialog = CharacterSheetUI.open_export_character_dialog

