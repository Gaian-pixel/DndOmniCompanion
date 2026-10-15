import tkinter as tk
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
from common.i18n import _t, get_language, translate_condition, translate_ability, translate_skill


class CharacterSheetUI(tk.Toplevel):
    def __init__(self, master, character, manager, on_save_callback=None, roll_callback=None, trade_callback=None, give_gold_callback=None, players_list_callback=None, attack_callback=None, long_rest_callback=None, custom_spell_request_callback=None, is_connected=False):
        super().__init__(master)
        self.title(f"{_t('sheet_title')} - {character.name}")
        self.minsize(600, 700)
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
        self.is_connected = is_connected
        self.default_font = ("Georgia", 10)
        
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
                return _update
            var.trace_add("write", make_mod_updater())

        # Abilità
        skills_frame = tk.Frame(body_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=6)
        skills_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        tk.Label(skills_frame, text=_t("sheet_skills"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(pady=(2, 6))
        
        self.skill_vars = {}
        self.skill_map = {
            "Acrobazia": "DES", "Addestrare Animali": "SAG", "Arcano": "INT", "Atletica": "FOR",
            "Furtività": "DES", "Indagare": "INT", "Inganno": "CAR", "Intimidire": "CAR",
            "Intrattenere": "CAR", "Intuizione": "SAG", "Medicina": "SAG", "Natura": "INT",
            "Percezione": "SAG", "Persuasione": "CAR", "Prestidigitazione": "DES",
            "Religione": "INT", "Sopravvivenza": "SAG", "Storia": "INT"
        }
        
        skills_canvas = tk.Canvas(skills_frame, width=220, bg=SURFACE_COLOR, highlightthickness=0)
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
        
        for i, (skill, stat) in enumerate(self.skill_map.items()):
            skill_text = translate_skill(skill)
            stat_text = translate_ability(stat)
            tk.Label(skills_inner_frame, text=f"{skill_text} ({stat_text})", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_COLOR).grid(row=i, column=0, sticky="w", pady=2)
            var = tk.IntVar()
            self.skill_vars[skill] = var
            combo = ttk.Combobox(skills_inner_frame, textvariable=var, values=[0, 1, 2], width=2, state="readonly")
            combo.grid(row=i, column=1, padx=4)
            ttk.Button(skills_inner_frame, text="🎲", width=2, command=lambda s=skill, st=stat: self.roll_skill(s, st)).grid(row=i, column=2, padx=2)

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
        self.speed_var = tk.IntVar(value=30)
        ttk.Entry(speed_box, textvariable=self.speed_var, width=3, justify="center").pack(pady=2)

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
        ttk.Entry(hp_inputs, textvariable=self.hp_max_var, width=4, justify="center").pack(side=tk.LEFT)
        
        # Health bar fill
        self.sheet_hp_bg = tk.Frame(hp_card, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, height=10)
        self.sheet_hp_bg.pack(fill=tk.X, pady=(2, 2))
        self.sheet_hp_fill = tk.Frame(self.sheet_hp_bg, bg=ACCENT_GREEN, height=8)
        self.sheet_hp_fill.place(x=0, y=0, width=0, relheight=1.0)
        
        def update_sheet_hp_bar(*args):
            try:
                cur = int(self.hp_cur_var.get())
                mx = max(1, int(self.hp_max_var.get()))
                ratio = max(0.0, min(1.0, cur / mx))
                color = ACCENT_GREEN if ratio > 0.5 else ("#F59F00" if ratio > 0.25 else ACCENT_RED)
                self.sheet_hp_fill.config(bg=color)
                w = self.sheet_hp_bg.winfo_width()
                if w <= 10: w = 180
                self.sheet_hp_fill.place(x=0, y=0, width=max(0, int(w * ratio)), relheight=1.0)
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
        ttk.Button(btn_frame, text=_t("save"), command=self.save_character, style="Primary.TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=_t("cancel"), command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def create_inventory_tab(self, parent_frame):
        currency_frame = ttk.LabelFrame(parent_frame, text=_t("sheet_currency"))
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
        
        ttk.Label(scrollable_frame, text=_t("sheet_item"), font=("Georgia", 9, "bold")).grid(row=0, column=0, padx=5, pady=2)
        ttk.Label(scrollable_frame, text=_t("sheet_weight_col"), font=("Georgia", 9, "bold")).grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(scrollable_frame, text=_t("sheet_attunement"), font=("Georgia", 9, "bold")).grid(row=0, column=2, padx=5, pady=2)
        
        self.inventory_buttons = []
        self.weight_vars = []
        self.attuned_vars = []
        
        for i in range(25):
            btn = ttk.Button(scrollable_frame, text=_t("sheet_empty_slot"), width=20, command=lambda idx=i: self.on_inventory_click(idx))
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
        
        self.weight_label = ttk.Label(bottom_frame, text=_t("sheet_total_weight", current="0.0", max="150"), font=("Georgia", 10, "bold"))
        self.weight_label.pack(pady=5)
        
        compendium_btn = ttk.Button(bottom_frame, text=_t("sheet_search_compendium"), command=self.open_inventory_compendium)
        compendium_btn.pack(side=tk.LEFT, padx=4, pady=5)
        
        btn_give_gold = ttk.Button(bottom_frame, text=_t("sheet_give_gold_btn"), command=self.on_give_gold_click, style="Gold.TButton")
        btn_give_gold.pack(side=tk.RIGHT, padx=4, pady=5)

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
            self.weight_label.config(
                text=f"{_t('sheet_total_weight', current=f'{total:.1f}', max=max_weight)} {_t('sheet_encumbered')}",
                foreground="red"
            )
        else:
            self.weight_label.config(
                text=_t("sheet_total_weight", current=f"{total:.1f}", max=max_weight),
                foreground=TEXT_COLOR
            )

    def check_attunement(self, changed_idx):
        if not hasattr(self, 'attuned_vars'): return
        attuned_count = sum(1 for var in self.attuned_vars if var.get())
        if attuned_count > 3:
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
        self.refresh_weapons_list()
        self.update_inspiration_ui()
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
                name = item.get("name", _t("sheet_item"))
                qty = item.get("qty", 1)
                short_name = name[:15] + ".." if len(name) > 15 else name
                btn.config(text=f"{short_name} (x{qty})", style="SlotFilled.TButton")
                if hasattr(self, 'weight_vars'):
                    self.weight_vars[i].set(item.get("weight", 0.0))
                if hasattr(self, 'attuned_vars'):
                    self.attuned_vars[i].set(item.get("attuned", False))
            else:
                btn.config(text=_t("sheet_empty_slot"), style="Slot.TButton")
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
        
        healed = self.character.short_rest(spend)
        self.hp_cur_var.set(self.character.hp_current)
        self.manager.update_character(self.character)
        if hasattr(self, "on_save_callback") and self.on_save_callback:
            try: self.on_save_callback()
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
                    try: self.on_save_callback()
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
            flavor = "💥 Fallimento critico! (2 fallimenti)"
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
            flavor = "🌟 Critico naturale (20)! Ti risvegli con 1 HP."

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
            try: self.on_save_callback()
            except Exception: pass
            
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
            dmg_str = f"{dice}{dmg_mod_str} {w.get('damage_type', '')}"
            
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
                btn_target = ttk.Button(r4, text=f"🎯 Bersaglio ({txc_str})", command=lambda weapon=w, txc=total_txc, dmg=dmg_str: self.execute_targeted_attack(weapon, txc, dmg), style="Gold.TButton")
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
                self.adv_dis_var.set("Vantaggio")
                self.manager.save_characters()
                
        adv_state = self.adv_dis_var.get()
        r1 = random.randint(1, 20)
        r2 = random.randint(1, 20)
        
        if adv_state == "Vantaggio":
            base_roll = max(r1, r2)
            rolls_str = f"max({r1}, {r2})"
        elif adv_state == "Svantaggio":
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
        
        adv_text = f" ({adv_state})" if adv_state != "Normale" else ""
        
        if is_crit:
            msg = f"⚔️ {self.character.name} attacca con {w_name}{adv_text}: [d20: {rolls_str}] {txc_sign} = {total} ⭐ COLPO CRITICO (20)!"
            messagebox.showinfo("COLPO CRITICO!", f"⭐ COLPO CRITICO!\nUn naturale 20 con {w_name}!\nIl prossimo tiro dei danni raddoppierà automaticamente i dadi!")
        elif is_fail:
            msg = f"⚔️ {self.character.name} attacca con {w_name}{adv_text}: [d20: {rolls_str}] {txc_sign} = {total} 💥 FALLIMENTO CRITICO (1)!"
        else:
            msg = f"⚔️ {self.character.name} attacca con {w_name}{adv_text}: [d20: {rolls_str}] {txc_sign} = {total}"
            
        self.adv_dis_var.set("Normale")
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
