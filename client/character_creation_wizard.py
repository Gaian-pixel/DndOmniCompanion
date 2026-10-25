import tkinter as tk
from common.messagebox import messagebox
from tkinter import ttk
import random
from typing import Dict, Any, List

from .character_manager import Character
from common.theme import (
    apply_modern_window_style,
    BG_COLOR,
    ACCENT_GOLD,
    ACCENT_GOLD_LIGHT,
    SURFACE_COLOR,
    SURFACE_COLOR_ALT,
    TEXT_COLOR,
    TEXT_MUTED,
    BORDER_COLOR,
    FONT_TITLE,
    FONT_HEADER,
    FONT_BOLD,
    FONT_MAIN,
    FONT_SMALL,
    FONT_BADGE
)
from common.classes_data import CLASSES, get_class_info, get_class_names, CLASS_CATEGORIES, get_classes_by_category
from common.races_data import RACES, get_race_info, get_race_names
from common.backgrounds_data import (
    BACKGROUNDS,
    PERSONAL_QUESTS,
    CHARACTER_SECRETS,
    PARTY_TIES,
    TRINKETS,
    ALIGNMENT_NONE,
    ALIGNMENTS,
    generate_backstory
)

# RACES importato da common.races_data

# CLASSES importato da common.classes_data

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]
ATTRIBUTES = ["FOR", "DES", "COS", "INT", "SAG", "CAR"]
ALL_SKILLS_5E = [
    "Acrobazia", "Addestrare Animali", "Arcano", "Atletica", "Furtività",
    "Indagare", "Inganno", "Intimidire", "Intrattenere", "Intuizione",
    "Medicina", "Natura", "Percezione", "Persuasione", "Prestidigitazione",
    "Religione", "Sopravvivenza", "Storia"
]


class CharacterCreationWizardFrame(ttk.Frame):
    def __init__(self, master, manager, on_complete_callback, on_close_callback=None, is_embedded=False, **kwargs):
        super().__init__(master, **kwargs)
        self.manager = manager
        self.on_complete_callback = on_complete_callback
        self.on_close_callback = on_close_callback
        self.is_embedded = is_embedded
        self.default_font = ("Georgia", 11)
        
        # Dati in costruzione
        self.char_data: Dict[str, Any] = {
            "race": "Umano",
            "subrace": "",
            "half_elf_bonuses": ["DES", "COS"],
            "char_class": "Guerriero",
            "attributes": {"FOR": 15, "DES": 14, "COS": 13, "INT": 12, "SAG": 10, "CAR": 8},
            "name": "",
            "campaign": "",
            "origin_place": "",
            "background": "Accolito",
            "background_skills": ["Intuizione", "Religione"],
            "background_feature_name": "Rifugio del Fedele",
            "background_feature_desc": "Tu e i tuoi compagni potete ricevere cure e ospitalità gratuita presso i templi e santuari della tua fede.",
            "background_gold": 15,
            "alignment": "",
            "personality_trait": "",
            "ideal": "",
            "bond": "",
            "flaw": "",
            "personal_quest": "",
            "secret": "",
            "party_tie": "",
            "trinket": "",
            "backstory": "",
            "avatar_b64": "",
            "avatar_path": ""
        }
        
        self.current_step = 0
        self.steps = [
            self.build_step_race,
            self.build_step_class,
            self.build_step_attributes,
            self.build_step_background,
            self.build_step_narrative
        ]
        
        # Barra Superiore Stepper Visuale (5 Passi Guidati)
        self.stepper_bar = tk.Frame(self, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=8)
        self.stepper_bar.pack(fill=tk.X, side=tk.TOP, padx=12, pady=(10, 0))

        if self.on_close_callback:
            self.cancel_btn = ttk.Button(self.stepper_bar, text="← Menu", command=self.close_wizard, style="Dark.TButton")
            self.cancel_btn.pack(side=tk.LEFT, padx=(0, 10))
            tk.Frame(self.stepper_bar, bg=BORDER_COLOR, width=1).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=2)

        self.step_pills_frame = tk.Frame(self.stepper_bar, bg=SURFACE_COLOR)
        self.step_pills_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.step_pill_labels = []
        step_titles = ["① Razza", "② Classe", "③ Caratteristiche", "④ Background", "⑤ Identità & Storia"]
        for idx, s_title in enumerate(step_titles):
            lbl = tk.Label(
                self.step_pills_frame,
                text=s_title,
                font=FONT_BADGE,
                bg=SURFACE_COLOR_ALT,
                fg=TEXT_MUTED,
                padx=8,
                pady=4,
                highlightbackground=BORDER_COLOR,
                highlightthickness=1
            )
            lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            self.step_pill_labels.append(lbl)

        self.container = ttk.Frame(self, padding=14)
        self.container.pack(fill=tk.BOTH, expand=True)
        
        self.btn_frame = tk.Frame(self, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=14, pady=8)
        self.btn_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=12, pady=(0, 10))
        
        self.prev_btn = ttk.Button(self.btn_frame, text="← Passo Precedente", command=self.prev_step, style="Dark.TButton")
        self.prev_btn.pack(side=tk.LEFT)
        
        self.step_indicator_lbl = tk.Label(self.btn_frame, text="", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD)
        self.step_indicator_lbl.pack(side=tk.LEFT, padx=20)

        self.next_btn = ttk.Button(self.btn_frame, text="Passo Successivo →", command=self.next_step, style="Gold.TButton")
        self.next_btn.pack(side=tk.RIGHT)
        
        self.show_step()

    def close_wizard(self):
        try:
            self.clear_container()
        except Exception:
            pass
        if self.on_close_callback:
            self.on_close_callback()
        else:
            self.destroy()

    def clear_container(self):
        try:
            self.unbind_all("<MouseWheel>")
        except Exception:
            pass
        if hasattr(self, "container") and self.container.winfo_exists():
            for widget in self.container.winfo_children():
                widget.destroy()

    def show_step(self):
        self.clear_container()
        step_idx = self.current_step
        self.step_indicator_lbl.config(text=f"Passo {step_idx + 1} di {len(self.steps)}")
        if hasattr(self, "step_pill_labels"):
            for i, pill in enumerate(self.step_pill_labels):
                if i < step_idx:
                    pill.config(bg="#132B1B", fg="#51CF66", highlightbackground="#2B8A3E")
                elif i == step_idx:
                    pill.config(bg=ACCENT_GOLD, fg="#121316", highlightbackground=ACCENT_GOLD)
                else:
                    pill.config(bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, highlightbackground=BORDER_COLOR)

        # I passi 1, 3 e 4 hanno molti elementi o descrizioni ricche: usiamo una Canvas scorrevole fluida
        if step_idx in (0, 1, 3, 4):
            canvas = tk.Canvas(self.container, bg=BG_COLOR, highlightthickness=0, borderwidth=0)
            scrollbar = ttk.Scrollbar(self.container, orient="vertical", command=canvas.yview)
            scroll_frame = ttk.Frame(canvas)
            canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

            def _sync_scroll_geometry(event=None):
                if not canvas.winfo_exists() or not scroll_frame.winfo_exists():
                    return
                c_w = canvas.winfo_width()
                c_h = canvas.winfo_height()
                req_h = scroll_frame.winfo_reqheight()
                if c_w > 1:
                    canvas.itemconfig(canvas_window, width=c_w, height=max(c_h, req_h))
                canvas.configure(scrollregion=canvas.bbox("all"))

            scroll_frame.bind("<Configure>", _sync_scroll_geometry)
            canvas.bind("<Configure>", _sync_scroll_geometry)
            
            def _on_mousewheel(event):
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            canvas.configure(yscrollcommand=scrollbar.set)
            
            self.scroll_canvas = canvas
            self.steps[step_idx](scroll_frame)
        else:
            self.scroll_canvas = None
            self.steps[step_idx](self.container)
        
        if self.current_step == 0:
            self.prev_btn.config(state=tk.DISABLED)
        else:
            self.prev_btn.config(state=tk.NORMAL)
            
        if self.current_step == len(self.steps) - 1:
            self.next_btn.config(text="Fine e Crea Personaggio")
        else:
            self.next_btn.config(text="Avanti >")

    def _save_current_step_data(self):
        if self.current_step == 2 and hasattr(self, "attr_vars"):
            for k in ATTRIBUTES:
                if k in self.attr_vars:
                    try:
                        self.char_data["attributes"][k] = int(self.attr_vars[k].get())
                    except (ValueError, tk.TclError):
                        pass
        elif self.current_step == 3:
            if hasattr(self, "bg_name_var"):
                self.char_data["background"] = self.bg_name_var.get().strip()
            if hasattr(self, "trait_var"):
                self.char_data["personality_trait"] = self.trait_var.get().strip()
            if hasattr(self, "ideal_var"):
                self.char_data["ideal"] = self.ideal_var.get().strip()
            if hasattr(self, "bond_var"):
                self.char_data["bond"] = self.bond_var.get().strip()
            if hasattr(self, "flaw_var"):
                self.char_data["flaw"] = self.flaw_var.get().strip()
            if hasattr(self, "custom_skill1_var") and self.char_data.get("background") == "Personalizzato":
                self.char_data["background_skills"] = [self.custom_skill1_var.get(), self.custom_skill2_var.get()]
        elif self.current_step == 4:
            if hasattr(self, "name_var"):
                self.char_data["name"] = self.name_var.get().strip()
            if hasattr(self, "camp_var"):
                self.char_data["campaign"] = self.camp_var.get().strip()
            if hasattr(self, "origin_var"):
                self.char_data["origin_place"] = self.origin_var.get().strip()
            if hasattr(self, "align_var"):
                raw_align = self.align_var.get().strip()
                if not raw_align or raw_align == ALIGNMENT_NONE or raw_align.startswith("Nessun"):
                    self.char_data["alignment"] = ""
                else:
                    self.char_data["alignment"] = raw_align.split(" ")[0].strip()
            if hasattr(self, "quest_var"):
                self.char_data["personal_quest"] = self.quest_var.get().strip()
            if hasattr(self, "secret_var"):
                self.char_data["secret"] = self.secret_var.get().strip()
            if hasattr(self, "party_tie_var"):
                self.char_data["party_tie"] = self.party_tie_var.get().strip()
            if hasattr(self, "trinket_var"):
                self.char_data["trinket"] = self.trinket_var.get().strip()
            if hasattr(self, "backstory_text"):
                try:
                    self.char_data["backstory"] = self.backstory_text.get("1.0", tk.END).strip()
                except tk.TclError:
                    pass

    def prev_step(self):
        if self.current_step > 0:
            self._save_current_step_data()
            self.current_step -= 1
            self.show_step()

    def next_step(self):
        # Validazione Passo 3: Caratteristiche
        if self.current_step == 2:
            if hasattr(self, "attr_vars"):
                vals = [var.get() for var in self.attr_vars.values()]
                if len(set(vals)) != len(STANDARD_ARRAY) or sorted(vals, reverse=True) != STANDARD_ARRAY:
                    messagebox.showerror("Errore", "Devi assegnare ogni valore della Array Standard (15,14,13,12,10,8) esattamente una volta.")
                    return
                self._save_current_step_data()

        # Salvataggio Passo 4: Background & Competenze
        if self.current_step == 3:
            self._save_current_step_data()

        # Validazione & Creazione Passo 5: Dettagli Finali & Narrativa
        if self.current_step == 4:
            self._save_current_step_data()
            if not self.char_data.get("name"):
                messagebox.showerror("Errore", "Il nome del personaggio è obbligatorio.")
                return
            self.finish_creation()
            return

        self.current_step += 1
        self.show_step()

    # -------------------------------------------------------------------------
    # PASSO 1: RAZZA
    # -------------------------------------------------------------------------
    def open_races_comparison_dialog(self):
        """Apre una finestra modale con il compendio comparativo avanzato Master-Detail di tutte le 9 razze 5e."""
        parent_win = self.winfo_toplevel()
        top = tk.Toplevel(parent_win)
        top.title("Compendio & Confronto Comparativo Razze (D&D 5e)")
        top.geometry("1060x650")
        top.minsize(920, 520)
        apply_modern_window_style(top)
        top.transient(parent_win)
        top.grab_set()

        # Header Frame
        header_frame = ttk.Frame(top, padding=(14, 10, 14, 6))
        header_frame.pack(fill=tk.X)
        ttk.Label(header_frame, text="📊 Compendio e Confronto Comparativo delle Razze (D&D 5e)", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header_frame,
            text="Filtra e confronta le 9 razze canoniche: bonus, resistenze e sinergie. Clicca su una riga per l'anteprima istantanea a destra o fai doppio clic per selezionare.",
            style="Muted.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        # Search & Filter Frame
        filter_bar = ttk.Frame(top, padding=(14, 2, 14, 8))
        filter_bar.pack(fill=tk.X)

        ttk.Label(filter_bar, text="🔍 Cerca:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD).pack(side=tk.LEFT, padx=(0, 6))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_bar, textvariable=search_var, width=22)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))

        filter_category_var = tk.StringVar(value="Tutte")

        filter_chips = [
            ("Tutte (9)", "Tutte"),
            ("🛡️ Resistenze", "Resistenze"),
            ("👁️ Scurovisione", "Scurovisione"),
            ("🏃 Taglia Piccola", "Piccola"),
            ("⚔️ Mischia / Forza", "Mischia"),
            ("✨ Magiche / Carisma", "Magiche"),
        ]

        def _set_cat_filter(cat_val):
            filter_category_var.set(cat_val)
            _refresh_table()

        chips_frame = ttk.Frame(filter_bar)
        chips_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        chip_buttons = {}
        for chip_label, chip_val in filter_chips:
            b = ttk.Button(
                chips_frame,
                text=chip_label,
                style="Primary.TButton" if chip_val == "Tutte" else "Dark.TButton",
                command=lambda cv=chip_val: _set_cat_filter(cv)
            )
            b.pack(side=tk.LEFT, padx=3)
            chip_buttons[chip_val] = b

        # Master-Detail PanedWindow
        main_paned = ttk.PanedWindow(top, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 6))

        # Left: Table Frame (~60%)
        table_frame = ttk.Frame(main_paned, style="Surface.TFrame")
        main_paned.add(table_frame, weight=3)

        # Right: Preview Detail Frame (~40%)
        preview_container = ttk.Frame(main_paned, style="Card.TFrame", padding=1)
        main_paned.add(preview_container, weight=2)

        # Table Treeview
        columns = ("razza", "bonus", "tratti", "resistenze", "taglia_vel", "classi")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        tree.heading("razza", text="Razza")
        tree.heading("bonus", text="Bonus Caratteristiche")
        tree.heading("tratti", text="Tratti Razziali Chiave")
        tree.heading("resistenze", text="Resistenze & Difese")
        tree.heading("taglia_vel", text="Taglia / Vel.")
        tree.heading("classi", text="Classi Consigliate")

        tree.column("razza", width=105, anchor="w")
        tree.column("bonus", width=155, anchor="w")
        tree.column("tratti", width=180, anchor="w")
        tree.column("resistenze", width=160, anchor="w")
        tree.column("taglia_vel", width=85, anchor="center")
        tree.column("classi", width=150, anchor="w")

        v_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # Preview Scrollable Canvas setup
        preview_canvas = tk.Canvas(preview_container, bg=SURFACE_COLOR, highlightthickness=0)
        preview_scrollbar = ttk.Scrollbar(preview_container, orient="vertical", command=preview_canvas.yview)
        preview_inner = ttk.Frame(preview_canvas, style="Surface.TFrame", padding=12)

        preview_canvas.configure(yscrollcommand=preview_scrollbar.set)
        preview_canvas_window = preview_canvas.create_window((0, 0), window=preview_inner, anchor="nw")

        def _on_preview_config(event):
            preview_canvas.itemconfig(preview_canvas_window, width=event.width)
            preview_canvas.configure(scrollregion=preview_canvas.bbox("all"))

        def _on_inner_config(event):
            preview_canvas.configure(scrollregion=preview_canvas.bbox("all"))

        preview_canvas.bind("<Configure>", _on_preview_config)
        preview_inner.bind("<Configure>", _on_inner_config)

        def _on_mousewheel(event):
            try:
                preview_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        preview_canvas.bind("<MouseWheel>", _on_mousewheel)
        preview_inner.bind("<MouseWheel>", _on_mousewheel)

        preview_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        selected_race_name = [self.char_data.get("race", "Umano")]

        def _select_and_close():
            sel = tree.selection()
            chosen = sel[0] if sel else selected_race_name[0]
            if chosen:
                if hasattr(self, "race_var"):
                    self.race_var.set(chosen)
            top.destroy()

        def _render_preview(r_name):
            selected_race_name[0] = r_name
            for widget in preview_inner.winfo_children():
                widget.destroy()

            r_info = RACES.get(r_name, RACES["Umano"])

            # Race Header
            hdr = ttk.Frame(preview_inner, style="Surface.TFrame")
            hdr.pack(fill=tk.X, pady=(0, 6))

            icon = r_info.get("icon", "🧬")
            ttk.Label(
                hdr,
                text=f"{icon} {r_name}",
                font=("Georgia", 16, "bold"),
                foreground=ACCENT_GOLD,
                style="Surface.TLabel"
            ).pack(anchor="w")

            ttk.Label(
                hdr,
                text=r_info.get("tagline", ""),
                font=("Segoe UI", 9, "italic"),
                foreground=TEXT_COLOR,
                wraplength=340,
                justify=tk.LEFT,
                style="Surface.TLabel"
            ).pack(anchor="w", pady=(3, 0))

            ttk.Separator(preview_inner, orient="horizontal").pack(fill=tk.X, pady=6)

            # Quick Specs Matrix
            specs_frame = ttk.Frame(preview_inner, style="Surface.TFrame")
            specs_frame.pack(fill=tk.X, pady=(0, 6))

            def _add_spec(parent, icon_char, label, value, val_color=TEXT_COLOR):
                f = ttk.Frame(parent, style="Surface.TFrame")
                f.pack(fill=tk.X, pady=1)
                ttk.Label(f, text=f"{icon_char} {label}:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT)
                ttk.Label(f, text=f" {value}", font=("Segoe UI", 9), foreground=val_color, wraplength=250, justify=tk.LEFT, style="Surface.TLabel").pack(side=tk.LEFT, fill=tk.X, expand=True)

            _add_spec(specs_frame, "⚡", "Bonus Caratteristiche", r_info.get("bonuses_display", ""), "#51CF66")
            _add_spec(specs_frame, "🏃", "Velocità & Taglia", f"{r_info.get('speed', 30)} ft  •  {r_info.get('size', 'Media')}")
            _add_spec(specs_frame, "👁️", "Sensi & Visione", r_info.get("vision", "Normale"))
            _add_spec(specs_frame, "🗣️", "Linguaggi", r_info.get("languages", "Comune"))
            _add_spec(specs_frame, "⏳", "Longevità Tipica", r_info.get("lifespan", ""))

            # Resistenze & Difese Highlight Box
            res_val = r_info.get("resistances", "Nessuna")
            res_box = ttk.LabelFrame(preview_inner, text="🛡️ Resistenze, Immunità & Difese", padding=(8, 6))
            res_box.pack(fill=tk.X, pady=6)
            ttk.Label(
                res_box,
                text=res_val,
                font=("Segoe UI", 9, "bold" if res_val != "Nessuna" else "normal"),
                foreground="#4DABF7" if res_val != "Nessuna" else TEXT_MUTED,
                wraplength=330,
                justify=tk.LEFT,
                style="Surface.TLabel"
            ).pack(anchor="w")

            # Sinergie & Classi Ideali Box
            syn_box = ttk.LabelFrame(preview_inner, text="⭐ Sinergie & Classi Ideali", padding=(8, 6))
            syn_box.pack(fill=tk.X, pady=6)
            best_cls = r_info.get("best_classes", "")
            if best_cls:
                ttk.Label(
                    syn_box,
                    text=f"🎯 Ottimale per: {best_cls}",
                    font=("Segoe UI", 9, "bold"),
                    foreground=ACCENT_GOLD_LIGHT,
                    wraplength=330,
                    justify=tk.LEFT,
                    style="Surface.TLabel"
                ).pack(anchor="w", pady=(0, 3))
            ttk.Label(
                syn_box,
                text=r_info.get("synergies", ""),
                font=("Segoe UI", 9),
                foreground=TEXT_COLOR,
                wraplength=330,
                justify=tk.LEFT,
                style="Surface.TLabel"
            ).pack(anchor="w")

            # Tratti Razziali Completi
            traits = r_info.get("traits", [])
            if traits:
                traits_box = ttk.LabelFrame(preview_inner, text=f"🧬 Tratti Razziali ({len(traits)})", padding=(8, 6))
                traits_box.pack(fill=tk.X, pady=6)
                for t_name, t_desc in traits:
                    t_frame = ttk.Frame(traits_box, style="Surface.TFrame")
                    t_frame.pack(fill=tk.X, pady=(2, 4))
                    ttk.Label(
                        t_frame,
                        text=f"• {t_name}",
                        font=("Segoe UI", 9, "bold"),
                        foreground=ACCENT_GOLD,
                        style="Surface.TLabel"
                    ).pack(anchor="w")
                    ttk.Label(
                        t_frame,
                        text=t_desc,
                        font=("Segoe UI", 8),
                        foreground=TEXT_COLOR,
                        wraplength=325,
                        justify=tk.LEFT,
                        style="Surface.TLabel"
                    ).pack(anchor="w", padx=(10, 0))

            # Sottorazze & Varianti
            subraces = r_info.get("subraces_preview", [])
            if subraces:
                sub_box = ttk.LabelFrame(preview_inner, text=f"🌿 Sottorazze & Varianti ({len(subraces)})", padding=(8, 6))
                sub_box.pack(fill=tk.X, pady=6)
                for sub in subraces:
                    ttk.Label(
                        sub_box,
                        text=f"• {sub}",
                        font=("Segoe UI", 8),
                        foreground=TEXT_MUTED,
                        wraplength=325,
                        justify=tk.LEFT,
                        style="Surface.TLabel"
                    ).pack(anchor="w", pady=1)

            # Action button in preview card
            ttk.Button(
                preview_inner,
                text=f"✓ Scegli {r_name}",
                style="Primary.TButton",
                command=_select_and_close
            ).pack(fill=tk.X, pady=(10, 4))

        def _refresh_table(*args):
            cat = filter_category_var.get()
            query = search_var.get().strip().lower()

            for chip_val, btn in chip_buttons.items():
                if chip_val == cat:
                    btn.configure(style="Primary.TButton")
                else:
                    btn.configure(style="Dark.TButton")

            # Clear current items
            for item in tree.get_children():
                tree.delete(item)

            filtered_races = []
            for r_name, r_info in RACES.items():
                tags = r_info.get("category_tags", [])
                res = r_info.get("resistances", "")
                size = r_info.get("size", "")
                vision = r_info.get("vision", "")
                bonuses = r_info.get("bonuses", {})

                # Category match
                if cat == "Resistenze":
                    if not (any(t in ["Resistenze", "Immunità/Difese"] for t in tags) or "Resistenza" in res or "Immunità" in res or "Vantaggio" in res):
                        continue
                elif cat == "Scurovisione":
                    if "Scurovisione" not in vision:
                        continue
                elif cat == "Piccola":
                    if "Piccola" not in size:
                        continue
                elif cat == "Mischia":
                    if not (any(t in ["Mischia/Forza", "Destrezza"] for t in tags) or "FOR" in bonuses or "COS" in bonuses):
                        continue
                elif cat == "Magiche":
                    if not (any(t in ["Magia Innata", "Carisma/Versatilità"] for t in tags) or any(k in bonuses for k in ["INT", "CAR", "SAG"])):
                        continue

                # Query match
                if query:
                    haystack = (
                        f"{r_name} {r_info.get('bonuses_display', '')} {r_info.get('key_traits_summary', '')} "
                        f"{r_info.get('resistances', '')} {r_info.get('best_classes', '')} {r_info.get('synergies', '')} "
                        f"{r_info.get('tagline', '')} {r_info.get('size', '')} {r_info.get('languages', '')}"
                    ).lower()
                    if query not in haystack:
                        continue

                filtered_races.append((r_name, r_info))

            for r_name, r_info in filtered_races:
                icon = r_info.get("icon", "")
                disp_name = f"{icon} {r_name}" if icon else r_name
                size_short = r_info.get("size", "Media").split()[0]
                speed_str = f"{r_info.get('speed', 30)} ft"
                taglia_vel = f"{size_short} | {speed_str}"
                tree.insert(
                    "",
                    tk.END,
                    iid=r_name,
                    values=(
                        disp_name,
                        r_info.get("bonuses_display", ""),
                        r_info.get("key_traits_summary", ""),
                        r_info.get("resistances", ""),
                        taglia_vel,
                        r_info.get("best_classes", "")
                    )
                )

            # Auto-select row if matches current or first
            current_target = selected_race_name[0]
            if current_target in tree.get_children():
                tree.selection_set(current_target)
                tree.focus(current_target)
                tree.see(current_target)
                _render_preview(current_target)
            elif tree.get_children():
                first = tree.get_children()[0]
                tree.selection_set(first)
                tree.focus(first)
                tree.see(first)
                _render_preview(first)

        def _on_tree_select(event=None):
            sel = tree.selection()
            if sel:
                chosen = sel[0]
                _render_preview(chosen)

        tree.bind("<<TreeviewSelect>>", _on_tree_select)
        tree.bind("<Double-1>", lambda e: _select_and_close())
        search_var.trace_add("write", _refresh_table)

        # Initial population
        _refresh_table()

        # Bottom Bar
        btn_bar = ttk.Frame(top, style="Surface.TFrame", padding=(14, 10))
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="Annulla", command=top.destroy, style="Dark.TButton").pack(side=tk.LEFT)
        ttk.Label(
            btn_bar,
            text="💡 Suggerimento: Seleziona una razza per visualizzarne i dettagli o premi 'Scegli Questa Razza'.",
            style="Muted.TLabel"
        ).pack(side=tk.LEFT, padx=16)
        ttk.Button(btn_bar, text="✓ Scegli Questa Razza", command=_select_and_close, style="Primary.TButton").pack(side=tk.RIGHT)

    def build_step_race(self, parent=None):
        parent = parent or self.container
        
        # Header descrittivo
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 6))
        
        ttk.Label(header_frame, text="Passo 1: Scegli la Razza", style="Title.TLabel").pack(anchor="center")
        ttk.Label(
            header_frame,
            text="La razza definisce la tua discendenza biologica e culturale, i bonus alle caratteristiche, la taglia, la velocità e i talenti innati.",
            style="Muted.TLabel",
            justify=tk.CENTER,
            wraplength=640
        ).pack(anchor="center", pady=(2, 0))

        # Barra di selezione razza con pulsanti rapido precedente/successivo e tabella comparativa
        sel_frame = ttk.Frame(parent, style="Surface.TFrame", padding=(10, 8))
        sel_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(sel_frame, text="🧬 Razza:", font=("Segoe UI", 11, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT, padx=(5, 10))
        
        race_list = list(RACES.keys())
        current_race = self.char_data.get("race", "Umano")
        if current_race not in race_list:
            current_race = race_list[0]
            
        self.race_var = tk.StringVar(value=current_race)
        
        def _prev_race():
            r = self.race_var.get()
            idx = race_list.index(r) if r in race_list else 0
            self.race_var.set(race_list[(idx - 1) % len(race_list)])
            
        def _next_race():
            r = self.race_var.get()
            idx = race_list.index(r) if r in race_list else 0
            self.race_var.set(race_list[(idx + 1) % len(race_list)])

        btn_prev = ttk.Button(sel_frame, text="◀ Prec.", width=8, command=_prev_race, style="Dark.TButton")
        btn_prev.pack(side=tk.LEFT, padx=3)
        
        cb = ttk.Combobox(sel_frame, textvariable=self.race_var, values=race_list, state="readonly", font=("Georgia", 11, "bold"), width=16)
        cb.pack(side=tk.LEFT, padx=6)
        
        btn_next = ttk.Button(sel_frame, text="Succ. ▶", width=8, command=_next_race, style="Dark.TButton")
        btn_next.pack(side=tk.LEFT, padx=3)
        
        btn_compare = ttk.Button(sel_frame, text="📊 Tabella Comparativa", command=self.open_races_comparison_dialog, style="Gold.TButton")
        btn_compare.pack(side=tk.RIGHT, padx=5)

        size_badge_lbl = ttk.Label(sel_frame, text="", style="BadgeBlue.TLabel")
        size_badge_lbl.pack(side=tk.RIGHT, padx=8)

        # Barra Opzioni Sottorazza / Bonus Mezzelfo
        sub_sel_frame = ttk.Frame(parent, style="Surface.TFrame", padding=(10, 6))
        self.subrace_var = tk.StringVar(value=self.char_data.get("subrace", ""))
        sub_lbl = ttk.Label(sub_sel_frame, text="🌿 Sottorazza:", font=("Segoe UI", 10, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel")
        sub_cb = ttk.Combobox(sub_sel_frame, textvariable=self.subrace_var, state="readonly", font=("Segoe UI", 10), width=24)

        he_stats = ["FOR", "DES", "COS", "INT", "SAG"]
        cur_he = self.char_data.get("half_elf_bonuses", ["DES", "COS"])
        if isinstance(cur_he, dict):
            cur_he = list(cur_he.keys())
        self.he_bon1_var = tk.StringVar(value=cur_he[0] if len(cur_he) > 0 else "DES")
        self.he_bon2_var = tk.StringVar(value=cur_he[1] if len(cur_he) > 1 else "COS")
        he_lbl = ttk.Label(sub_sel_frame, text="✨ Bonus +1 Mezzelfo (2 Caratteristiche):", font=("Segoe UI", 10, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel")
        he_cb1 = ttk.Combobox(sub_sel_frame, textvariable=self.he_bon1_var, values=he_stats, state="readonly", width=6)
        he_cb2 = ttk.Combobox(sub_sel_frame, textvariable=self.he_bon2_var, values=he_stats, state="readonly", width=6)

        def _on_subrace_or_he_change(*_a):
            self.char_data["subrace"] = self.subrace_var.get()
            b1 = self.he_bon1_var.get()
            b2 = self.he_bon2_var.get()
            if b1 == b2:
                for alt in he_stats:
                    if alt != b1:
                        b2 = alt
                        self.he_bon2_var.set(b2)
                        break
            self.char_data["half_elf_bonuses"] = [b1, b2]

        self.subrace_var.trace_add("write", _on_subrace_or_he_change)
        self.he_bon1_var.trace_add("write", _on_subrace_or_he_change)
        self.he_bon2_var.trace_add("write", _on_subrace_or_he_change)

        # Scheda Dettagli Razza (Card)
        card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Testata della card
        top_frame = ttk.Frame(card, style="Surface.TFrame")
        top_frame.pack(fill=tk.X, pady=(0, 6))
        
        name_lbl = ttk.Label(top_frame, text="", font=("Georgia", 16, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel")
        name_lbl.pack(anchor="w")
        
        tagline_lbl = ttk.Label(top_frame, text="", font=("Segoe UI", 10, "italic"), foreground=TEXT_COLOR, wraplength=640, justify=tk.LEFT, style="Surface.TLabel")
        tagline_lbl.pack(anchor="w", pady=(2, 6))
        
        ttk.Separator(card, orient="horizontal").pack(fill=tk.X, pady=6)
        
        # Griglia Quick Stats
        stats_frame = ttk.Frame(card, style="Surface.TFrame")
        stats_frame.pack(fill=tk.X, pady=(2, 8))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        
        # Cella 1: Bonus Caratteristiche
        cell_bon = ttk.Frame(stats_frame, style="Surface.TFrame")
        cell_bon.grid(row=0, column=0, sticky="w", padx=6, pady=3)
        ttk.Label(cell_bon, text="⚡ Bonus:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT)
        bon_val_lbl = ttk.Label(cell_bon, text="", font=("Segoe UI", 9, "bold"), foreground="#51CF66", style="Surface.TLabel")
        bon_val_lbl.pack(side=tk.LEFT, padx=4)
        
        # Cella 2: Velocità & Taglia
        cell_speed = ttk.Frame(stats_frame, style="Surface.TFrame")
        cell_speed.grid(row=0, column=1, sticky="w", padx=6, pady=3)
        ttk.Label(cell_speed, text="🏃 Velocità & Taglia:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT)
        speed_val_lbl = ttk.Label(cell_speed, text="", font=("Segoe UI", 9), style="Surface.TLabel")
        speed_val_lbl.pack(side=tk.LEFT, padx=4)
        
        # Cella 3: Sensi Speciali
        cell_vis = ttk.Frame(stats_frame, style="Surface.TFrame")
        cell_vis.grid(row=1, column=0, sticky="w", padx=6, pady=3)
        ttk.Label(cell_vis, text="👁️ Sensi:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT)
        vis_val_lbl = ttk.Label(cell_vis, text="", font=("Segoe UI", 9), style="Surface.TLabel")
        vis_val_lbl.pack(side=tk.LEFT, padx=4)
        
        # Cella 4: Linguaggi
        cell_lang = ttk.Frame(stats_frame, style="Surface.TFrame")
        cell_lang.grid(row=1, column=1, sticky="w", padx=6, pady=3)
        ttk.Label(cell_lang, text="🗣️ Linguaggi:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT)
        lang_val_lbl = ttk.Label(cell_lang, text="", font=("Segoe UI", 9), wraplength=300, justify=tk.LEFT, style="Surface.TLabel")
        lang_val_lbl.pack(side=tk.LEFT, padx=4)

        # Cella 5: Resistenze & Difese
        cell_res = ttk.Frame(stats_frame, style="Surface.TFrame")
        cell_res.grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=3)
        ttk.Label(cell_res, text="🛡️ Resistenze & Difese:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT)
        res_val_lbl = ttk.Label(cell_res, text="", font=("Segoe UI", 9, "bold"), foreground="#4DABF7", wraplength=480, justify=tk.LEFT, style="Surface.TLabel")
        res_val_lbl.pack(side=tk.LEFT, padx=4)

        ttk.Separator(card, orient="horizontal").pack(fill=tk.X, pady=6)

        # Sezione: Sinergie di Classe & Consigli
        synergy_box = ttk.Frame(card, style="Surface.TFrame", padding=(8, 6))
        synergy_box.pack(fill=tk.X, pady=(2, 6))
        ttk.Label(synergy_box, text="⭐ Sinergie di Classe Consigliate:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD_LIGHT, style="Surface.TLabel").pack(anchor="w")
        synergy_lbl = ttk.Label(synergy_box, text="", font=("Segoe UI", 9), wraplength=620, justify=tk.LEFT, style="Surface.TLabel")
        synergy_lbl.pack(anchor="w", padx=(10, 0), pady=(1, 2))

        ttk.Separator(card, orient="horizontal").pack(fill=tk.X, pady=6)
        
        # Sezione 1: Panoramica Narrativa
        ttk.Label(card, text="📖 Panoramica & Lore Narrativa", font=("Segoe UI", 10, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(anchor="w")
        overview_lbl = ttk.Label(card, text="", font=("Segoe UI", 9), wraplength=640, justify=tk.LEFT, style="Surface.TLabel")
        overview_lbl.pack(anchor="w", pady=(2, 8))
        
        ttk.Separator(card, orient="horizontal").pack(fill=tk.X, pady=6)
        
        # Sezione 2: Tratti Razziali Innati
        ttk.Label(card, text="🧬 Tratti Razziali Innati", font=("Segoe UI", 10, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(anchor="w")
        traits_container = ttk.Frame(card, style="Surface.TFrame")
        traits_container.pack(fill=tk.X, pady=(2, 8))
        
        ttk.Separator(card, orient="horizontal").pack(fill=tk.X, pady=6)
        
        # Sezione 3: Sottorazze & Varianti
        ttk.Label(card, text="🌿 Sottorazze e Varianti Famose", font=("Segoe UI", 10, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(anchor="w")
        subraces_lbl = ttk.Label(card, text="", font=("Segoe UI", 9), wraplength=640, justify=tk.LEFT, style="Surface.TLabel")
        subraces_lbl.pack(anchor="w", pady=(2, 6))

        # Sezione 4: Longevità
        lifespan_box = ttk.Frame(card, style="Surface.TFrame", padding=(8, 4))
        lifespan_box.pack(fill=tk.X, pady=(2, 4))
        ttk.Label(lifespan_box, text="⏳ Longevità & Maturità:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT)
        lifespan_lbl = ttk.Label(lifespan_box, text="", font=("Segoe UI", 9), style="Surface.TLabel")
        lifespan_lbl.pack(side=tk.LEFT, padx=6)
        
        def update_desc(*args):
            r = self.race_var.get()
            self.char_data["race"] = r
            if r in RACES:
                info = RACES[r]
                sub_dict = info.get("subraces", {})
                for w in sub_sel_frame.winfo_children():
                    w.pack_forget()
                if sub_dict:
                    sub_names = list(sub_dict.keys())
                    if self.subrace_var.get() not in sub_names:
                        self.subrace_var.set(sub_names[0])
                    sub_cb.config(values=sub_names)
                    sub_lbl.pack(side=tk.LEFT, padx=(5, 8))
                    sub_cb.pack(side=tk.LEFT, padx=4)
                    sub_sel_frame.pack(fill=tk.X, pady=(0, 8), before=card)
                elif r == "Mezzelfo":
                    self.subrace_var.set("")
                    he_lbl.pack(side=tk.LEFT, padx=(5, 8))
                    he_cb1.pack(side=tk.LEFT, padx=4)
                    he_cb2.pack(side=tk.LEFT, padx=4)
                    sub_sel_frame.pack(fill=tk.X, pady=(0, 8), before=card)
                else:
                    self.subrace_var.set("")
                    sub_sel_frame.pack_forget()
                name_lbl.config(text=f"Razza: {r}")
                size_badge_lbl.config(text=f"🏃 {info.get('speed', 30)} ft | {info.get('size', 'Media').split()[0]}")
                tagline_lbl.config(text=f'"{info.get("tagline", "")}"')
                bon_val_lbl.config(text=info.get("bonuses_display", ""))
                speed_val_lbl.config(text=f"{info.get('speed', 30)} ft ({round(info.get('speed', 30)*0.3)} m) | Taglia {info.get('size', 'Media').split()[0]}")
                vis_val_lbl.config(text=info.get("vision", "Normale"))
                lang_val_lbl.config(text=info.get("languages", "Comune"))
                res_val_lbl.config(text=info.get("resistances", "Nessuna"))
                best_cls = info.get("best_classes", "")
                best_prefix = f"🎯 Ottimale per: {best_cls}\n" if best_cls else ""
                synergy_lbl.config(text=f"{best_prefix}{info.get('synergies', '')}")
                overview_lbl.config(text=info.get("overview", ""))
                lifespan_lbl.config(text=info.get("lifespan", ""))
                
                subs = info.get("subraces_preview", [])
                subraces_lbl.config(text="\n".join(f"• {sub}" for sub in subs))
                
                # Rigenera blocchi tratti razziali
                for w in traits_container.winfo_children():
                    w.destroy()
                for t_name, t_desc in info.get("traits", []):
                    t_row = ttk.Frame(traits_container, style="Surface.TFrame")
                    t_row.pack(fill=tk.X, pady=2)
                    ttk.Label(t_row, text=f"• {t_name}:", font=("Segoe UI", 9, "bold"), foreground="#F59E0B", style="Surface.TLabel").pack(anchor="w")
                    ttk.Label(t_row, text=t_desc, font=("Segoe UI", 9), wraplength=630, justify=tk.LEFT, style="Surface.TLabel").pack(anchor="w", padx=(12, 0), pady=(1, 2))
                    
                if hasattr(self, "scroll_canvas") and self.scroll_canvas and self.scroll_canvas.winfo_exists():
                    try:
                        self.scroll_canvas.update_idletasks()
                        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))
                        self.scroll_canvas.yview_moveto(0.0)
                    except Exception:
                        pass

        self.race_var.trace_add("write", update_desc)
        update_desc()
    # -------------------------------------------------------------------------
    # PASSO 2: CLASSE
    # -------------------------------------------------------------------------
    def open_classes_comparison_dialog(self):
        """Apre una finestra modale con la tabella comparativa di tutte le 12 classi 5e."""
        parent_win = self.winfo_toplevel()
        top = tk.Toplevel(parent_win)
        top.title("Tabella Comparativa delle 12 Classi (D&D 5e)")
        top.geometry("860x520")
        top.minsize(750, 400)
        apply_modern_window_style(top)
        top.transient(parent_win)
        top.grab_set()

        header_frame = ttk.Frame(top, padding=(12, 10))
        header_frame.pack(fill=tk.X)
        ttk.Label(header_frame, text="📊 Confronto Rapido delle Classi", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header_frame,
            text="Confronta Dadi Vita, Ruolo Tattico, Caratteristiche Primarie e Complessità per scegliere l'eroe perfetto. Fai doppio clic su una riga per selezionarla.",
            style="Muted.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        # Tabella Treeview
        columns = ("classe", "categoria", "ruolo", "hd", "primaria", "tiri_salvezza", "complessita")
        tree = ttk.Treeview(top, columns=columns, show="headings", height=13)
        tree.heading("classe", text="Classe")
        tree.heading("categoria", text="Categoria")
        tree.heading("ruolo", text="Ruolo nel Party")
        tree.heading("hd", text="Dado Vita")
        tree.heading("primaria", text="Caratteristica Primaria")
        tree.heading("tiri_salvezza", text="Tiri Salvezza")
        tree.heading("complessita", text="Complessità")

        tree.column("classe", width=95, anchor="center")
        tree.column("categoria", width=90, anchor="center")
        tree.column("ruolo", width=220, anchor="w")
        tree.column("hd", width=75, anchor="center")
        tree.column("primaria", width=140, anchor="w")
        tree.column("tiri_salvezza", width=110, anchor="center")
        tree.column("complessita", width=110, anchor="w")

        for c_name, c_info in CLASSES.items():
            comp_short = c_info.get("complexity", "").split("(")[0].strip()
            tree.insert("", tk.END, iid=c_name, values=(
                c_name,
                c_info.get("category", "Marziale"),
                c_info.get("role", ""),
                f"d{c_info.get('hd', 8)}",
                c_info.get("primary_stat", ""),
                c_info.get("saving_throws", ""),
                comp_short
            ))

        scroll = ttk.Scrollbar(top, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        
        table_frame = ttk.Frame(top, padding=(12, 0))
        table_frame.pack(fill=tk.BOTH, expand=True)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def _select_and_close():
            sel = tree.selection()
            if sel:
                chosen = sel[0]
                if hasattr(self, "class_var"):
                    self.class_var.set(chosen)
                top.destroy()

        tree.bind("<Double-1>", lambda e: _select_and_close())

        btn_bar = ttk.Frame(top, style="Surface.TFrame", padding=(12, 10))
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Button(btn_bar, text="Annulla", command=top.destroy, style="Dark.TButton").pack(side=tk.LEFT)
        ttk.Button(btn_bar, text="✓ Scegli Questa Classe", command=_select_and_close, style="Primary.TButton").pack(side=tk.RIGHT)

    def build_step_class(self, parent=None):
        parent = parent or self.container
        
        # Header descrittivo
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 6))
        
        ttk.Label(header_frame, text="Passo 2: Scegli la Classe", style="Title.TLabel").pack(anchor="center")
        ttk.Label(
            header_frame,
            text="La classe definisce la vocazione, le abilità marziali o magiche, i privilegi speciali e il ruolo tattico del tuo avventuriero.",
            style="Muted.TLabel",
            justify=tk.CENTER,
            wraplength=640
        ).pack(anchor="center", pady=(2, 0))

        # Barra Filtri di Categoria & Confronto
        filter_bar = ttk.Frame(parent, style="Surface.TFrame", padding=(8, 5))
        filter_bar.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(filter_bar, text="Filtra:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT, padx=(5, 6))
        
        self.active_category_var = tk.StringVar(value="Tutte")
        cat_buttons = {}

        def _filter_classes(cat):
            self.active_category_var.set(cat)
            filtered_names = get_classes_by_category(cat)
            cb["values"] = filtered_names
            for c_name, btn in cat_buttons.items():
                if c_name == cat:
                    btn.configure(style="Primary.TButton")
                else:
                    btn.configure(style="Dark.TButton")
            # Se la classe corrente non è nel filtro, seleziona la prima
            if self.class_var.get() not in filtered_names and filtered_names:
                self.class_var.set(filtered_names[0])

        for cat in CLASS_CATEGORIES:
            btn = ttk.Button(
                filter_bar,
                text=cat,
                command=lambda c=cat: _filter_classes(c),
                style="Primary.TButton" if cat == "Tutte" else "Dark.TButton"
            )
            btn.pack(side=tk.LEFT, padx=3)
            cat_buttons[cat] = btn

        btn_compare = ttk.Button(filter_bar, text="📊 Tabella Comparativa", command=self.open_classes_comparison_dialog, style="Gold.TButton")
        btn_compare.pack(side=tk.RIGHT, padx=5)

        # Barra di selezione classe con pulsanti rapido precedente/successivo e badge ruolo
        sel_frame = ttk.Frame(parent, style="Surface.TFrame", padding=(10, 8))
        sel_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(sel_frame, text="⚔️ Classe:", font=("Segoe UI", 11, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT, padx=(5, 10))
        
        class_list = list(CLASSES.keys())
        current_class = self.char_data.get("char_class", "Guerriero")
        if current_class not in class_list:
            current_class = class_list[0]
            
        self.class_var = tk.StringVar(value=current_class)
        
        def _prev_class():
            c = self.class_var.get()
            cur_values = list(cb["values"]) if cb["values"] else class_list
            idx = cur_values.index(c) if c in cur_values else 0
            self.class_var.set(cur_values[(idx - 1) % len(cur_values)])
            
        def _next_class():
            c = self.class_var.get()
            cur_values = list(cb["values"]) if cb["values"] else class_list
            idx = cur_values.index(c) if c in cur_values else 0
            self.class_var.set(cur_values[(idx + 1) % len(cur_values)])

        btn_prev = ttk.Button(sel_frame, text="◀ Prec.", width=8, command=_prev_class, style="Dark.TButton")
        btn_prev.pack(side=tk.LEFT, padx=3)
        
        cb = ttk.Combobox(sel_frame, textvariable=self.class_var, values=class_list, state="readonly", font=("Georgia", 11, "bold"), width=16)
        cb.pack(side=tk.LEFT, padx=6)
        
        btn_next = ttk.Button(sel_frame, text="Succ. ▶", width=8, command=_next_class, style="Dark.TButton")
        btn_next.pack(side=tk.LEFT, padx=3)
        
        role_badge_lbl = ttk.Label(sel_frame, text="", style="BadgeBlue.TLabel")
        role_badge_lbl.pack(side=tk.RIGHT, padx=5)

        # Scheda Dettagli Classe (Card)
        card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Testata della card
        top_frame = ttk.Frame(card, style="Surface.TFrame")
        top_frame.pack(fill=tk.X, pady=(0, 6))
        
        title_row = ttk.Frame(top_frame, style="Surface.TFrame")
        title_row.pack(fill=tk.X)
        
        name_lbl = ttk.Label(title_row, text="", font=("Georgia", 16, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel")
        name_lbl.pack(side=tk.LEFT)
        
        complexity_lbl = ttk.Label(title_row, text="", style="Badge.TLabel")
        complexity_lbl.pack(side=tk.RIGHT)
        
        tagline_lbl = ttk.Label(top_frame, text="", font=("Segoe UI", 10, "italic"), foreground=TEXT_COLOR, wraplength=640, justify=tk.LEFT, style="Surface.TLabel")
        tagline_lbl.pack(anchor="w", pady=(3, 6))
        
        ttk.Separator(card, orient="horizontal").pack(fill=tk.X, pady=6)
        
        # Griglia Quick Stats / Pillole informative
        stats_frame = ttk.Frame(card, style="Surface.TFrame")
        stats_frame.pack(fill=tk.X, pady=(2, 8))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        
        # Cella 1: Dado Vita
        cell_hd = ttk.Frame(stats_frame, style="Surface.TFrame")
        cell_hd.grid(row=0, column=0, sticky="w", padx=6, pady=3)
        ttk.Label(cell_hd, text="🎲 Dado Vita:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT)
        hd_val_lbl = ttk.Label(cell_hd, text="", font=("Segoe UI", 9), style="Surface.TLabel")
        hd_val_lbl.pack(side=tk.LEFT, padx=4)
        
        # Cella 2: Caratteristica Primaria
        cell_prim = ttk.Frame(stats_frame, style="Surface.TFrame")
        cell_prim.grid(row=0, column=1, sticky="w", padx=6, pady=3)
        ttk.Label(cell_prim, text="⭐ Primaria:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT)
        prim_val_lbl = ttk.Label(cell_prim, text="", font=("Segoe UI", 9), style="Surface.TLabel")
        prim_val_lbl.pack(side=tk.LEFT, padx=4)
        
        # Cella 3: Tiri Salvezza
        cell_st = ttk.Frame(stats_frame, style="Surface.TFrame")
        cell_st.grid(row=1, column=0, sticky="w", padx=6, pady=3)
        ttk.Label(cell_st, text="🛡️ Tiri Salvezza:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT)
        st_val_lbl = ttk.Label(cell_st, text="", font=("Segoe UI", 9), style="Surface.TLabel")
        st_val_lbl.pack(side=tk.LEFT, padx=4)
        
        # Cella 4: Competenze
        cell_prof = ttk.Frame(stats_frame, style="Surface.TFrame")
        cell_prof.grid(row=1, column=1, sticky="w", padx=6, pady=3)
        ttk.Label(cell_prof, text="⚔️ Competenze:", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(side=tk.LEFT)
        prof_val_lbl = ttk.Label(cell_prof, text="", font=("Segoe UI", 9), wraplength=300, justify=tk.LEFT, style="Surface.TLabel")
        prof_val_lbl.pack(side=tk.LEFT, padx=4)

        ttk.Separator(card, orient="horizontal").pack(fill=tk.X, pady=6)

        # Sezione: Creazione Rapida & Priorità Caratteristiche (Quick Build)
        quick_build_box = ttk.Frame(card, style="Surface.TFrame", padding=(8, 6))
        quick_build_box.pack(fill=tk.X, pady=(2, 6))
        ttk.Label(quick_build_box, text="💡 Consiglio di Creazione Rapida (per il Passo 3):", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD_LIGHT, style="Surface.TLabel").pack(anchor="w")
        quick_build_lbl = ttk.Label(quick_build_box, text="", font=("Segoe UI", 9), wraplength=620, justify=tk.LEFT, style="Surface.TLabel")
        quick_build_lbl.pack(anchor="w", padx=(10, 0), pady=(1, 2))

        # Sezione: Dotazione & Equipaggiamento Iniziale (Starter Kit)
        gear_box = ttk.Frame(card, style="Surface.TFrame", padding=(8, 6))
        gear_box.pack(fill=tk.X, pady=(2, 6))
        ttk.Label(gear_box, text="🎒 Dotazione Iniziale di Classe (fornita all'inizio):", font=("Segoe UI", 9, "bold"), foreground="#51CF66", style="Surface.TLabel").pack(anchor="w")
        gear_lbl = ttk.Label(gear_box, text="", font=("Segoe UI", 9), wraplength=620, justify=tk.LEFT, style="Surface.TLabel")
        gear_lbl.pack(anchor="w", padx=(10, 0), pady=(1, 2))

        # Sezione opzionale: Magia & Incantesimi Iniziali
        magic_box = ttk.Frame(card, style="Surface.TFrame", padding=(8, 6))
        magic_box.pack(fill=tk.X, pady=(2, 6))
        magic_title_lbl = ttk.Label(magic_box, text="✨ Magia & Incantesimi Iniziali (Livello 1):", font=("Segoe UI", 9, "bold"), foreground="#4DABF7", style="Surface.TLabel")
        magic_title_lbl.pack(anchor="w")
        magic_lbl = ttk.Label(magic_box, text="", font=("Segoe UI", 9), wraplength=620, justify=tk.LEFT, style="Surface.TLabel")
        magic_lbl.pack(anchor="w", padx=(10, 0), pady=(1, 2))

        ttk.Separator(card, orient="horizontal").pack(fill=tk.X, pady=6)
        
        # Sezione 1: Panoramica Narrativa
        ttk.Label(card, text="📖 Panoramica & Identità Narrativa", font=("Segoe UI", 10, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(anchor="w")
        overview_lbl = ttk.Label(card, text="", font=("Segoe UI", 9), wraplength=640, justify=tk.LEFT, style="Surface.TLabel")
        overview_lbl.pack(anchor="w", pady=(2, 8))
        
        ttk.Separator(card, orient="horizontal").pack(fill=tk.X, pady=6)
        
        # Sezione 2: Privilegi di Livello 1
        ttk.Label(card, text="⚔️ Privilegi Chiave di Livello 1", font=("Segoe UI", 10, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(anchor="w")
        features_container = ttk.Frame(card, style="Surface.TFrame")
        features_container.pack(fill=tk.X, pady=(2, 8))
        
        ttk.Separator(card, orient="horizontal").pack(fill=tk.X, pady=6)
        
        # Sezione 3: Stile di Gioco & Tattica
        ttk.Label(card, text="🎯 Stile di Gioco & Ruolo nel Gruppo", font=("Segoe UI", 10, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(anchor="w")
        playstyle_lbl = ttk.Label(card, text="", font=("Segoe UI", 9), wraplength=640, justify=tk.LEFT, style="Surface.TLabel")
        playstyle_lbl.pack(anchor="w", pady=(2, 8))
        
        ttk.Separator(card, orient="horizontal").pack(fill=tk.X, pady=6)
        
        # Sezione 4: Archetipi Futuri
        ttk.Label(card, text="🔮 Archetipi e Sottoclassi Future", font=("Segoe UI", 10, "bold"), foreground=ACCENT_GOLD, style="Surface.TLabel").pack(anchor="w")
        subclasses_lbl = ttk.Label(card, text="", font=("Segoe UI", 9), wraplength=640, justify=tk.LEFT, style="Surface.TLabel")
        subclasses_lbl.pack(anchor="w", pady=(2, 4))
        
        def update_desc(*args):
            c = self.class_var.get()
            self.char_data["char_class"] = c
            if c in CLASSES:
                info = CLASSES[c]
                name_lbl.config(text=f"Classe: {c}")
                role_badge_lbl.config(text=info.get("role", ""))
                complexity_lbl.config(text=info.get("complexity", "").split("(")[0].strip())
                tagline_lbl.config(text=f'"{info.get("tagline", "")}"')
                hd_val_lbl.config(text=f"d{info['hd']} (PF al 1°: {info['hd']} + mod. COS)")
                prim_val_lbl.config(text=info.get("primary_stat", ""))
                st_val_lbl.config(text=info.get("saving_throws", ""))
                prof_val_lbl.config(text=f"{info.get('armor_prof', '')}; {info.get('weapon_prof', '')}")
                quick_build_lbl.config(text=info.get("quick_build", ""))
                gear_lbl.config(text=info.get("starter_gear", ""))
                
                # Box magia
                spells = info.get("starter_spells")
                if spells:
                    magic_box.pack(fill=tk.X, pady=(2, 6))
                    magic_lbl.config(text=spells)
                else:
                    magic_box.pack_forget()

                overview_lbl.config(text=info.get("overview", ""))
                playstyle_lbl.config(text=info.get("playstyle", ""))
                subclasses_lbl.config(text="\n".join(f"• {sub}" for sub in info.get("subclasses_preview", [])))
                
                # Rigenera blocchi privilegi di livello 1
                for w in features_container.winfo_children():
                    w.destroy()
                for feat_name, feat_desc in info.get("features_lvl1", []):
                    f_row = ttk.Frame(features_container, style="Surface.TFrame")
                    f_row.pack(fill=tk.X, pady=2)
                    ttk.Label(f_row, text=f"• {feat_name}:", font=("Segoe UI", 9, "bold"), foreground="#F59E0B", style="Surface.TLabel").pack(anchor="w")
                    ttk.Label(f_row, text=feat_desc, font=("Segoe UI", 9), wraplength=630, justify=tk.LEFT, style="Surface.TLabel").pack(anchor="w", padx=(12, 0), pady=(1, 2))
                    
                if hasattr(self, "scroll_canvas") and self.scroll_canvas and self.scroll_canvas.winfo_exists():
                    try:
                        self.scroll_canvas.update_idletasks()
                        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))
                        self.scroll_canvas.yview_moveto(0.0)
                    except Exception:
                        pass

        self.class_var.trace_add("write", update_desc)
        update_desc()
    # -------------------------------------------------------------------------
    # PASSO 3: CARATTERISTICHE (STANDARD ARRAY)
    # -------------------------------------------------------------------------
    def build_step_attributes(self, parent=None):
        parent = parent or self.container
        ttk.Label(parent, text="Passo 3: Caratteristiche (Standard Array)", style="Title.TLabel").pack(pady=(0, 10))
        ttk.Label(parent, text="Assegna i valori: 15, 14, 13, 12, 10, 8\nI valori si scambieranno automaticamente per non avere duplicati.", justify=tk.CENTER).pack(pady=(0, 15))
        
        self.attr_vars = {}
        self.old_attr_values = {}
        
        frame = ttk.Frame(parent)
        frame.pack()
        
        for i, attr in enumerate(ATTRIBUTES):
            val = self.char_data["attributes"].get(attr, STANDARD_ARRAY[i])
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
            ttk.Label(frame, text=attr, font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky="e", padx=8, pady=4)
            
            var = self.attr_vars[attr]
            var.trace_add("write", lambda name, index, mode, a=attr: on_var_change(a))
            
            cb = ttk.Combobox(frame, textvariable=var, values=STANDARD_ARRAY, state="readonly", width=6, justify="center")
            cb.grid(row=i, column=1, padx=8, pady=4)

    # -------------------------------------------------------------------------
    # PASSO 4: BACKGROUND & COMPETENZE
    # -------------------------------------------------------------------------
    def build_step_background(self, parent):
        ttk.Label(parent, text="Passo 4: Scegli il Background & le Competenze", style="Title.TLabel").pack(pady=(0, 4))
        ttk.Label(parent, text="Il tuo passato plasma le tue competenze nelle abilità, i privilegi sociali e l'indole morale.", style="Muted.TLabel").pack(pady=(0, 12))
        
        # 1. Selezione del Background
        top_bar = ttk.Frame(parent)
        top_bar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top_bar, text="Background 5e:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        
        cur_bg = self.char_data.get("background") or "Accolito"
        self.bg_name_var = tk.StringVar(value=cur_bg)
        bg_cb = ttk.Combobox(top_bar, textvariable=self.bg_name_var, values=list(BACKGROUNDS.keys()), state="readonly", width=25, font=self.default_font)
        bg_cb.pack(side=tk.LEFT, padx=4)
        
        # 2. Scheda Descrittiva del Background (Info, Privilegio, Abilità)
        card_bg = ttk.Frame(parent, style="Surface.TFrame", padding=12)
        card_bg.pack(fill=tk.X, pady=(0, 14))
        
        lbl_bg_desc = ttk.Label(card_bg, text="", wraplength=580, justify=tk.LEFT)
        lbl_bg_desc.pack(anchor="w", pady=(0, 8))
        
        skills_row = ttk.Frame(card_bg)
        skills_row.pack(fill=tk.X, pady=(2, 6))
        ttk.Label(skills_row, text="🎯 Competenze Abilità:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        lbl_skills = ttk.Label(skills_row, text="", style="Primary.TLabel")
        lbl_skills.pack(side=tk.LEFT)

        # Selettori abilità custom nel caso di background 'Personalizzato'
        self.custom_skills_frame = ttk.Frame(card_bg)
        self.custom_skill1_var = tk.StringVar(value="Intuizione")
        self.custom_skill2_var = tk.StringVar(value="Percezione")
        ttk.Label(self.custom_skills_frame, text="Scegli 2 Abilità:").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Combobox(self.custom_skills_frame, textvariable=self.custom_skill1_var, values=ALL_SKILLS_5E, state="readonly", width=14).pack(side=tk.LEFT, padx=3)
        ttk.Combobox(self.custom_skills_frame, textvariable=self.custom_skill2_var, values=ALL_SKILLS_5E, state="readonly", width=14).pack(side=tk.LEFT, padx=3)

        feat_box = ttk.Frame(card_bg)
        feat_box.pack(fill=tk.X, pady=(4, 6))
        lbl_feat_title = ttk.Label(feat_box, text="", font=("Segoe UI", 9, "bold"))
        lbl_feat_title.pack(anchor="w")
        lbl_feat_desc = ttk.Label(feat_box, text="", style="Muted.TLabel", wraplength=580, justify=tk.LEFT)
        lbl_feat_desc.pack(anchor="w", pady=(2, 0))

        lbl_equip = ttk.Label(card_bg, text="", style="Muted.TLabel", wraplength=580, justify=tk.LEFT)
        lbl_equip.pack(anchor="w", pady=(6, 0))

        # 3. Le 4 Colonne Ruolistiche 5e (Tratti, Ideali, Legami, Difetti)
        roleplay_header = ttk.Frame(parent)
        roleplay_header.pack(fill=tk.X, pady=(10, 6))
        ttk.Label(roleplay_header, text="🎭 Le 4 Colonne Ruolistiche (D&D 5e)", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        btn_roll_all = ttk.Button(roleplay_header, text="🎲 Tira Tutti i Tratti Casuali", command=lambda: self._roll_all_roleplay_traits(), style="Gold.TButton")
        btn_roll_all.pack(side=tk.RIGHT)

        rp_grid = ttk.Frame(parent)
        rp_grid.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        rp_grid.columnconfigure(0, weight=1)

        # Variabili ruolistiche
        self.trait_var = tk.StringVar(value=self.char_data.get("personality_trait", ""))
        self.ideal_var = tk.StringVar(value=self.char_data.get("ideal", ""))
        self.bond_var = tk.StringVar(value=self.char_data.get("bond", ""))
        self.flaw_var = tk.StringVar(value=self.char_data.get("flaw", ""))

        self.rp_combos = {}

        def make_rp_row(row_idx, title, var, rp_key):
            row_frame = ttk.Frame(rp_grid)
            row_frame.grid(row=row_idx, column=0, sticky="ew", pady=4)
            
            hdr_f = ttk.Frame(row_frame)
            hdr_f.pack(fill=tk.X)
            ttk.Label(hdr_f, text=title, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
            
            def do_roll():
                bg = BACKGROUNDS.get(self.bg_name_var.get(), BACKGROUNDS["Accolito"])
                pool = bg.get(rp_key, [])
                if pool:
                    var.set(random.choice(pool))
            
            btn_roll = ttk.Button(hdr_f, text="🎲", width=3, command=do_roll)
            btn_roll.pack(side=tk.RIGHT)

            cb = ttk.Combobox(row_frame, textvariable=var, state="normal")
            cb.pack(fill=tk.X, pady=(2, 4))
            self.rp_combos[rp_key] = cb

        make_rp_row(0, "Tratto Caratteriale (Abitudini & Modi di fare):", self.trait_var, "traits")
        make_rp_row(1, "Ideale (Principio etico o morale):", self.ideal_var, "ideals")
        make_rp_row(2, "Legame (La persona, luogo o memoria per cui moriresti):", self.bond_var, "bonds")
        make_rp_row(3, "Difetto (Vizio segreto, debolezza o fobia):", self.flaw_var, "flaws")

        def update_bg_info(*args):
            bg_name = self.bg_name_var.get()
            info = BACKGROUNDS.get(bg_name, BACKGROUNDS["Accolito"])
            
            self.char_data["background"] = bg_name
            self.char_data["background_feature_name"] = info["feature_name"]
            self.char_data["background_feature_desc"] = info["feature_desc"]
            self.char_data["background_gold"] = info.get("gold", 15)
            
            lbl_bg_desc.config(text=info["desc"])
            
            if bg_name == "Personalizzato":
                skills_row.pack_forget()
                self.custom_skills_frame.pack(fill=tk.X, pady=(2, 6))
                self.char_data["background_skills"] = [self.custom_skill1_var.get(), self.custom_skill2_var.get()]
            else:
                self.custom_skills_frame.pack_forget()
                skills_row.pack(fill=tk.X, pady=(2, 6))
                lbl_skills.config(text=", ".join(info["skills"]))
                self.char_data["background_skills"] = list(info["skills"])

            lbl_feat_title.config(text=f"📜 Privilegio: {info['feature_name']}")
            lbl_feat_desc.config(text=info["feature_desc"])
            lbl_equip.config(text=f"🎒 Equipaggiamento & Oro Iniziale: {info['equipment']}")

            # Aggiorna opzioni delle 4 colonne ruolistiche
            for key, cb in self.rp_combos.items():
                opts = info.get(key, [])
                cb["values"] = opts
                # Se il valore corrente è vuoto, pre-seleziona il primo
                current_v = cb.get()
                if not current_v and opts:
                    cb.set(opts[0])

        self.bg_name_var.trace_add("write", update_bg_info)
        update_bg_info()

    def _roll_all_roleplay_traits(self):
        bg = BACKGROUNDS.get(self.bg_name_var.get(), BACKGROUNDS["Accolito"])
        for key, var in [("traits", self.trait_var), ("ideals", self.ideal_var), ("bonds", self.bond_var), ("flaws", self.flaw_var)]:
            pool = bg.get(key, [])
            if pool:
                var.set(random.choice(pool))

    # -------------------------------------------------------------------------
    # PASSO 5: NARRATIVA, OBIETTIVI & DETTAGLI FINALI
    # -------------------------------------------------------------------------
    def build_step_narrative(self, parent):
        ttk.Label(parent, text="Passo 5: Narrativa, Obiettivi & Dettagli Finali", style="Title.TLabel").pack(pady=(0, 4))
        ttk.Label(parent, text="Definisci gli obiettivi della tua avventura, i tuoi segreti e componi la tua storia.", style="Muted.TLabel").pack(pady=(0, 10))

        # 1. Sezione Anagrafica Base (Nome, Campagna, Origine)
        ana_frame = ttk.Frame(parent)
        ana_frame.pack(fill=tk.X, pady=(0, 8))
        ana_frame.columnconfigure(1, weight=1)
        ana_frame.columnconfigure(3, weight=1)

        ttk.Label(ana_frame, text="Nome:*", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="e", padx=(0, 4), pady=4)
        self.name_var = tk.StringVar(value=self.char_data.get("name", ""))
        ttk.Entry(ana_frame, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=4)

        ttk.Label(ana_frame, text="Campagna:", font=("Segoe UI", 9)).grid(row=0, column=2, sticky="e", padx=(0, 4), pady=4)
        self.camp_var = tk.StringVar(value=self.char_data.get("campaign", ""))
        ttk.Entry(ana_frame, textvariable=self.camp_var).grid(row=0, column=3, sticky="ew", pady=4)

        ttk.Label(ana_frame, text="Origine / Città:", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="e", padx=(0, 4), pady=4)
        self.origin_var = tk.StringVar(value=self.char_data.get("origin_place", "Terre d'origine"))
        ttk.Entry(ana_frame, textvariable=self.origin_var).grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=4)

        ttk.Label(ana_frame, text="Allineamento:", font=("Segoe UI", 9)).grid(row=1, column=2, sticky="e", padx=(0, 4), pady=4)
        
        align_keys = list(ALIGNMENTS.keys())
        initial_align = ALIGNMENT_NONE
        cur_align = self.char_data.get("alignment", "")
        if cur_align:
            for k in align_keys:
                if k != ALIGNMENT_NONE and k.startswith(cur_align):
                    initial_align = k
                    break
        self.align_var = tk.StringVar(value=initial_align)
        align_cb = ttk.Combobox(ana_frame, textvariable=self.align_var, values=align_keys, state="readonly", width=18)
        align_cb.grid(row=1, column=3, sticky="ew", pady=4)

        # 1.1 Sezione Ritratto Personaggio & Token Mappa
        token_card = ttk.LabelFrame(parent, text="🖼️ Ritratto Personaggio & Token Mappa", padding=8)
        token_card.pack(fill=tk.X, pady=(0, 10))

        token_row = ttk.Frame(token_card)
        token_row.pack(fill=tk.X)

        self.token_canvas = tk.Canvas(token_row, width=64, height=64, bg="#181A20", highlightthickness=0)
        self.token_canvas.pack(side=tk.LEFT, padx=(0, 12))

        token_info = ttk.Frame(token_row)
        token_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(token_info, text="Aspetto del Personaggio & Token di Gioco:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Label(token_info, text="L'immagine scelta verrà ritagliata in forma circolare e utilizzata come token interattivo sulla mappa.", style="Muted.TLabel", wraplength=420, justify=tk.LEFT).pack(anchor="w", pady=(1, 4))

        token_btn_row = ttk.Frame(token_info)
        token_btn_row.pack(anchor="w", pady=(2, 0))

        self.token_status_lbl = ttk.Label(token_btn_row, text="Nessuna immagine impostata", style="Muted.TLabel")

        def _update_token_preview():
            cur_b64 = self.char_data.get("avatar_b64", "")
            cur_name = self.name_var.get() if hasattr(self, "name_var") else self.char_data.get("name", "")
            from common.image_utils import render_avatar_on_canvas
            render_avatar_on_canvas(self.token_canvas, cur_b64, cur_name, size=64)
            if cur_b64:
                path = self.char_data.get("avatar_path", "")
                fn = os.path.basename(path) if path else "Immagine caricata"
                self.token_status_lbl.config(text=f"✅ {fn}")
            else:
                self.token_status_lbl.config(text="Nessuna immagine (token con iniziali)")

        def _pick_image():
            from common.image_utils import open_avatar_file_dialog
            b64, path = open_avatar_file_dialog(parent=self)
            if b64:
                self.char_data["avatar_b64"] = b64
                self.char_data["avatar_path"] = path
                _update_token_preview()

        def _clear_image():
            self.char_data["avatar_b64"] = ""
            self.char_data["avatar_path"] = ""
            _update_token_preview()

        ttk.Button(token_btn_row, text="📁 Scegli Immagine...", command=_pick_image, style="Primary.TButton").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(token_btn_row, text="❌ Rimuovi", command=_clear_image).pack(side=tk.LEFT, padx=(0, 10))
        self.token_status_lbl.pack(side=tk.LEFT, padx=4)

        _update_token_preview()

        # Suggerimento Allineamento
        tip_frame = ttk.Frame(parent, style="Surface.TFrame", padding=8)
        tip_frame.pack(fill=tk.X, pady=(4, 10))
        tip_txt = (
            "💡 Allineamento Opzionale: In D&D 5e l'allineamento è solo una possibile bussola etica e una linea guida. "
            "Non definisce per forza il giocatore o il personaggio che sarai al tavolo: le tue scelte avranno sempre la precedenza."
        )
        ttk.Label(tip_frame, text=tip_txt, style="Muted.TLabel", wraplength=580, justify=tk.LEFT).pack(fill=tk.X)

        # 2. Ganci Narrativi e Dinamiche di Gruppo (Obiettivo, Segreto, Legame, Cimelio)
        narr_card = ttk.Frame(parent, style="Surface.TFrame", padding=10)
        narr_card.pack(fill=tk.X, pady=(0, 10))
        
        # Helper per creare righe con combobox e dado 🎲
        def make_narrative_picker(label_text, var, options_list, badge_text=""):
            row = ttk.Frame(narr_card)
            row.pack(fill=tk.X, pady=3)
            
            top_line = ttk.Frame(row)
            top_line.pack(fill=tk.X)
            
            ttk.Label(top_line, text=label_text, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
            if badge_text:
                ttk.Label(top_line, text=f" {badge_text}", style="Gold.TLabel").pack(side=tk.LEFT)
            
            def roll_val():
                if options_list:
                    pick = random.choice(options_list)
                    var.set(pick if isinstance(pick, str) else f"{pick.get('title', '')} — {pick.get('desc', '')}")
            
            ttk.Button(top_line, text="🎲", width=3, command=roll_val).pack(side=tk.RIGHT)

            raw_opts = [o if isinstance(o, str) else f"{o['title']} — {o['desc']}" for o in options_list]
            
            cb = ttk.Combobox(row, textvariable=var, values=raw_opts, state="normal")
            cb.pack(fill=tk.X, pady=(2, 4))
            return cb

        self.quest_var = tk.StringVar(value=self.char_data.get("personal_quest", f"{PERSONAL_QUESTS[0]['title']} — {PERSONAL_QUESTS[0]['desc']}"))
        make_narrative_picker("🎯 Obiettivo Personale / Gancio d'Avventura:", self.quest_var, PERSONAL_QUESTS)

        self.secret_var = tk.StringVar(value=self.char_data.get("secret", f"{CHARACTER_SECRETS[0]['title']} — {CHARACTER_SECRETS[0]['desc']}"))
        make_narrative_picker("🔒 Segreto del Personaggio (per il Master):", self.secret_var, CHARACTER_SECRETS, badge_text="[Visibile solo a te e al DM]")

        self.party_tie_var = tk.StringVar(value=self.char_data.get("party_tie", f"{PARTY_TIES[0]['title']} — {PARTY_TIES[0]['desc']}"))
        make_narrative_picker("🤝 Legame con il Gruppo (Party Tie):", self.party_tie_var, PARTY_TIES)

        self.trinket_var = tk.StringVar(value=self.char_data.get("trinket", TRINKETS[0]))
        make_narrative_picker("🗝️ Cimelio Personale (Trinket con significato affettivo):", self.trinket_var, TRINKETS)

        # 3. Generatore & Editor della Backstory
        story_card = ttk.Frame(parent)
        story_card.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        story_top = ttk.Frame(story_card)
        story_top.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(story_top, text="📖 Biografia & Storia dell'Eroe:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        
        def compose_story(variation=0):
            style_val = getattr(self, "story_style_var", None)
            style_str = style_val.get() if style_val else "heroic"
            party_tie_val = self.party_tie_var.get() if hasattr(self, "party_tie_var") else ""
            story = generate_backstory(
                name=self.name_var.get(),
                race=self.char_data.get("race", "Umano"),
                char_class=self.char_data.get("char_class", "Guerriero"),
                background=self.char_data.get("background", "Accolito"),
                origin_place=self.origin_var.get(),
                trait=self.trait_var.get() if hasattr(self, "trait_var") else "",
                ideal=self.ideal_var.get() if hasattr(self, "ideal_var") else "",
                bond=self.bond_var.get() if hasattr(self, "bond_var") else "",
                flaw=self.flaw_var.get() if hasattr(self, "flaw_var") else "",
                quest=self.quest_var.get(),
                secret=self.secret_var.get(),
                trinket=self.trinket_var.get(),
                party_tie=party_tie_val,
                narrative_style=style_str,
                include_headers=True,
                variation=variation
            )
            self.backstory_text.delete("1.0", tk.END)
            self.backstory_text.insert(tk.END, story)

        btn_compose = ttk.Button(story_top, text="✨ Componi Storia", command=compose_story, style="Gold.TButton")
        btn_compose.pack(side=tk.RIGHT, padx=2)

        def do_variation():
            var_num = random.randint(1, 9999)
            compose_story(variation=var_num)

        btn_var = ttk.Button(story_top, text="🎲 Variazione", command=do_variation, style="Dark.TButton")
        btn_var.pack(side=tk.RIGHT, padx=2)

        def do_clear():
            self.backstory_text.delete("1.0", tk.END)

        btn_clear = ttk.Button(story_top, text="🧹 Pulisci", command=do_clear, style="Dark.TButton")
        btn_clear.pack(side=tk.RIGHT, padx=2)

        style_frame = ttk.Frame(story_card)
        style_frame.pack(fill=tk.X, pady=(2, 4))
        ttk.Label(style_frame, text="🎨 Stile Narrativo:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.story_style_var = tk.StringVar(value="Eroico & Epico")
        style_cb = ttk.Combobox(
            style_frame,
            textvariable=self.story_style_var,
            values=["Eroico & Epico", "Dark Fantasy & Tormentato", "Misterioso & Arcano", "Picaresco & Avventuroso"],
            state="readonly",
            width=28
        )
        style_cb.pack(side=tk.LEFT, padx=4)
        style_cb.bind("<<ComboboxSelected>>", lambda e: compose_story())

        txt_frame = ttk.Frame(story_card)
        txt_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 6))

        scroll_y = ttk.Scrollbar(txt_frame, orient=tk.VERTICAL)
        self.backstory_text = tk.Text(txt_frame, height=10, wrap=tk.WORD, font=self.default_font, yscrollcommand=scroll_y.set)
        scroll_y.config(command=self.backstory_text.yview)
        self.backstory_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Se abbiamo già una backstory, la carichiamo, altrimenti componiamo una prima bozza evocativa
        existing_story = self.char_data.get("backstory", "").strip()
        if existing_story:
            self.backstory_text.insert(tk.END, existing_story)
        else:
            compose_story()

    # -------------------------------------------------------------------------
    # CONCLUSIONE E CREAZIONE FINALE
    # -------------------------------------------------------------------------
    def finish_creation(self):
        c = Character(name=self.char_data["name"], campaign=self.char_data["campaign"])
        c.race = self.char_data["race"]
        c.char_class = self.char_data["char_class"]
        c.background = self.char_data["background"]
        c.background_feature_name = self.char_data.get("background_feature_name", "")
        c.background_feature_desc = self.char_data.get("background_feature_desc", "")
        c.alignment = self.char_data.get("alignment", "")
        c.personality_trait = self.char_data.get("personality_trait", "")
        c.ideal = self.char_data.get("ideal", "")
        c.bond = self.char_data.get("bond", "")
        c.flaw = self.char_data.get("flaw", "")
        c.personal_quest = self.char_data.get("personal_quest", "")
        c.secret = self.char_data.get("secret", "")
        c.party_tie = self.char_data.get("party_tie", "")
        c.trinket = self.char_data.get("trinket", "")
        c.backstory = self.char_data.get("backstory", "")
        c.avatar_b64 = self.char_data.get("avatar_b64", "")
        c.avatar_path = self.char_data.get("avatar_path", "")
        c.level = 1
        
        # Calcolo attributi = array + bonus razza (+ eventuale sottorazza o scelta Mezzelfo)
        race_info = RACES.get(c.race, RACES["Umano"])
        effective_bonuses = dict(race_info.get("bonuses", {}))
        if c.race == "Mezzelfo" and isinstance(self.char_data.get("half_elf_bonuses"), dict):
            effective_bonuses = {"CAR": 2}
            for he_k, he_v in self.char_data["half_elf_bonuses"].items():
                if he_k != "CAR" and he_k in ATTRIBUTES:
                    effective_bonuses[he_k] = effective_bonuses.get(he_k, 0) + int(he_v)

        chosen_subrace = self.char_data.get("subrace", "")
        subraces_dict = race_info.get("subraces", {})
        subrace_info = subraces_dict.get(chosen_subrace, {}) if chosen_subrace else {}
        for sub_k, sub_v in subrace_info.get("bonuses", {}).items():
            if sub_k not in race_info.get("bonuses", {}):
                effective_bonuses[sub_k] = effective_bonuses.get(sub_k, 0) + int(sub_v)

        for attr in ATTRIBUTES:
            base = self.char_data["attributes"][attr]
            bonus = effective_bonuses.get(attr, 0)
            c.attributes[attr] = base + bonus
            
        def get_mod(val):
            return (val - 10) // 2

        con_mod = get_mod(c.attributes["COS"])
        dex_mod = get_mod(c.attributes["DES"])
        
        # Calcolo HP (incluso eventuale bonus sottorazza es. Nano delle Colline +1 PF)
        class_info = CLASSES.get(c.char_class, CLASSES["Guerriero"])
        hp_sub_bonus = int(subrace_info.get("hp_bonus", 0))
        c.hp_max = class_info["hd"] + con_mod + hp_sub_bonus
        c.hp_current = c.hp_max
        
        # Calcolo AC base (10 + Dex) e Velocità
        c.ac = 10 + dex_mod
        c.initiative = dex_mod
        c.speed = subrace_info.get("speed", race_info.get("speed", 30))
        
        # Equipaggiamento iniziale di classe (armi, armature, scudi) e incantesimi
        from common.starter_equipment import apply_class_and_race_starter_kit
        apply_class_and_race_starter_kit(c)
        
        # Aggiungi oro iniziale del background e allinea lo slot monete
        bg_gold = int(self.char_data.get("background_gold", 10))
        if hasattr(c, "currency") and isinstance(c.currency, dict):
            c.currency["MO"] = c.currency.get("MO", 0) + bg_gold
            for it in getattr(c, "inventory_grid", []):
                if isinstance(it, dict) and (it.get("type") == "Valuta" or "monet" in str(it.get("name", "")).lower()):
                    it["qty"] = c.currency["MO"]
                    it["desc"] = f"Monete iniziali ({c.currency['MO']} MO)."
                    it["_coins_synced"] = True
                    break

        # Aggiungi cimelio all'inventario
        if c.trinket:
            trinket_item = {
                "name": f"Cimelio: {c.trinket[:25]}...",
                "type": "Cimelio",
                "desc": c.trinket,
                "qty": 1,
                "weight": 0.5
            }
            if hasattr(c, "inventory") and isinstance(c.inventory, list):
                c.inventory.append(trinket_item)
            if hasattr(c, "inventory_grid") and isinstance(c.inventory_grid, list):
                for idx in range(len(c.inventory_grid)):
                    if c.inventory_grid[idx] is None:
                        c.inventory_grid[idx] = trinket_item
                        break

        # Competenze nelle abilità conferite dalla razza e dal background (con sostituzione automatica in caso di sovrapposizione PHB p. 125)
        extra_skills = list(race_info.get("racial_skills", [])) + list(self.char_data.get("background_skills", []))
        if hasattr(c, "skills") and isinstance(c.skills, dict):
            for sk in extra_skills:
                if sk in c.skills:
                    if c.skills[sk] == 0:
                        c.skills[sk] = 1
                    else:
                        for fallback_sk in ALL_SKILLS_5E:
                            if c.skills.get(fallback_sk, 0) == 0:
                                c.skills[fallback_sk] = 1
                                break

        # Privilegi del personaggio (Razza + Classe + Privilegio di Background)
        bg_feat_txt = ""
        if c.background_feature_name:
            bg_feat_txt = f"\n\nPrivilegio di Background ({c.background_feature_name}):\n{c.background_feature_desc}"
        
        c.features = f"Tratti razziali:\n{race_info['desc']}\n\nTratti classe:\n{class_info['desc']}{bg_feat_txt}"

        # Diario del Personaggio (Note ben formattate pronte nel tab 'Diario')
        notes_lines = []
        notes_lines.append(f"# Biografia & Origini di {c.name}")
        notes_lines.append(f"**Razza:** {c.race} | **Classe:** {c.char_class} | **Background:** {c.background}")
        if self.char_data.get("origin_place"):
            notes_lines.append(f"**Luogo d'Origine:** {self.char_data['origin_place']}")
        if c.alignment:
            notes_lines.append(f"**Allineamento:** {c.alignment}")
        notes_lines.append("")
        
        notes_lines.append("## 🎭 Spunti di Ruolo (D&D 5e)")
        if c.personality_trait:
            notes_lines.append(f"- **Tratto Caratteriale:** {c.personality_trait}")
        if c.ideal:
            notes_lines.append(f"- **Ideale:** {c.ideal}")
        if c.bond:
            notes_lines.append(f"- **Legame:** {c.bond}")
        if c.flaw:
            notes_lines.append(f"- **Difetto:** {c.flaw}")
        notes_lines.append("")

        notes_lines.append("## 🎯 Obiettivi & Segreti")
        if c.personal_quest:
            notes_lines.append(f"- **Obiettivo Personale:** {c.personal_quest}")
        if c.secret:
            notes_lines.append(f"- **Segreto (per il Master):** {c.secret}")
        if c.party_tie:
            notes_lines.append(f"- **Legame con il Gruppo:** {c.party_tie}")
        if c.trinket:
            notes_lines.append(f"- **Cimelio Personale:** {c.trinket}")
        notes_lines.append("")

        if c.backstory:
            notes_lines.append("## 📖 Storia dell'Eroe")
            notes_lines.append(c.backstory)
            notes_lines.append("")

        notes_lines.append("## 📝 Diario delle Sessioni")
        notes_lines.append("*Spazio per appunti, indizi, promesse e scoperte durante le sessioni di gioco.*")
        c.journal_notes = "\n".join(notes_lines)

        # Fetch for Level 1 features (prima offline SRD istantaneo sul main thread, poi eventuale fallback online)
        off_data = None
        try:
            from common.srd_offline import get_class_level_features_offline
            off_data = get_class_level_features_offline(c.char_class, 1)
        except Exception:
            off_data = None

        if off_data and off_data.get("features"):
            c.features += "\n\n--- Privilegi di Livello 1 ---\n" + "\n".join(f"- {ft}" for ft in off_data["features"])
            if off_data.get("spell_slots"):
                for lvl_str, cnt in off_data["spell_slots"].items():
                    c.spell_slots[str(lvl_str)] = {"max": cnt, "current": cnt}
            self._on_creation_done(c)
            return

        def _fetch_level_1_online():
            try:
                import urllib.request
                import json
                from .progression_ui import CLASS_MAP
                class_en = CLASS_MAP.get(c.char_class.lower())
                if class_en:
                    req = urllib.request.Request(
                        f"https://www.dnd5eapi.co/api/classes/{class_en}/levels/1",
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    with urllib.request.urlopen(req, timeout=1.5) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                    feats = [f["name"] for f in data.get("features", [])]
                    if feats:
                        c.features += "\n\n--- Privilegi di Livello 1 (API) ---\n" + "\n".join(f"- {ft}" for ft in feats)
                    sc = data.get("spellcasting")
                    if sc:
                        for i in range(1, 10):
                            key = f"spell_slots_level_{i}"
                            if key in sc:
                                c.spell_slots[str(i)] = {"max": sc[key], "current": sc[key]}
            except Exception:
                pass
            
            try:
                self.master.after(0, self._on_creation_done, c)
            except Exception:
                try:
                    self._on_creation_done(c)
                except Exception:
                    pass
            
        import threading
        threading.Thread(target=_fetch_level_1_online, daemon=True).start()

    def _on_creation_done(self, c):
        self.manager.add_character(c)
        try:
            messagebox.showinfo("Successo", f"Personaggio '{c.name}' creato con successo!", parent=self)
        except Exception:
            pass
        try:
            self.clear_container()
        except Exception:
            pass
        if self.on_complete_callback:
            try:
                self.on_complete_callback(c)
            except Exception:
                pass
        if not self.is_embedded or not self.on_complete_callback:
            try:
                self.close_wizard()
            except Exception:
                pass


class CharacterCreationWizard(tk.Toplevel):
    """
    Finestra modale per la creazione guidata del personaggio (retrocompatibile al 100%).
    Incapsula CharacterCreationWizardFrame delegando attributi e metodi.
    """
    def __init__(self, master, manager, on_complete_callback):
        super().__init__(master)
        self.title("Creazione Guidata Personaggio & Background (D&D 5e)")
        self.minsize(700, 720)
        self.geometry("760x780")
        apply_modern_window_style(self)
        self.transient(master)
        self.grab_set()

        self._frame_internal = CharacterCreationWizardFrame(
            self,
            manager=manager,
            on_complete_callback=on_complete_callback,
            on_close_callback=self.destroy,
            is_embedded=False
        )
        self._frame_internal.pack(fill=tk.BOTH, expand=True)

    def destroy(self):
        try:
            super().destroy()
        except (tk.TclError, Exception):
            pass

    def __getattr__(self, name):
        if name in ("_tclCommands", "_w", "_name", "tk", "master", "children"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        if "_frame_internal" in self.__dict__ and hasattr(self.__dict__["_frame_internal"], name):
            return getattr(self.__dict__["_frame_internal"], name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name in ("_frame_internal",) or "_frame_internal" not in self.__dict__:
            super().__setattr__(name, value)
        elif hasattr(self.__dict__["_frame_internal"], name):
            setattr(self.__dict__["_frame_internal"], name, value)
        else:
            super().__setattr__(name, value)
