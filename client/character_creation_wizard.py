import tkinter as tk
from common.messagebox import messagebox
from tkinter import ttk
import random
from typing import Dict, Any, List

from .character_manager import Character
from common.theme import (
    apply_modern_window_style,
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

# CLASSES importato da common.classes_data

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]
ATTRIBUTES = ["FOR", "DES", "COS", "INT", "SAG", "CAR"]
ALL_SKILLS_5E = [
    "Acrobazia", "Addestrare Animali", "Arcano", "Atletica", "Furtività",
    "Indagare", "Inganno", "Intimidire", "Intrattenere", "Intuizione",
    "Medicina", "Natura", "Percezione", "Persuasione", "Prestidigitazione",
    "Religione", "Sopravvivenza", "Storia"
]


class CharacterCreationWizard(tk.Toplevel):
    def __init__(self, master, manager, on_complete_callback):
        super().__init__(master)
        self.title("Creazione Guidata Personaggio & Background (D&D 5e)")
        self.minsize(700, 720)
        self.geometry("760x780")
        apply_modern_window_style(self)
        self.transient(master)
        self.grab_set()
        
        self.manager = manager
        self.on_complete_callback = on_complete_callback
        self.default_font = ("Georgia", 11)
        
        # Dati in costruzione
        self.char_data: Dict[str, Any] = {
            "race": "Umano",
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
        
        self.container = ttk.Frame(self, padding=16)
        self.container.pack(fill=tk.BOTH, expand=True)
        
        self.btn_frame = ttk.Frame(self, style="Surface.TFrame", padding=10)
        self.btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.prev_btn = ttk.Button(self.btn_frame, text="< Indietro", command=self.prev_step)
        self.prev_btn.pack(side=tk.LEFT)
        
        self.step_indicator_lbl = ttk.Label(self.btn_frame, text="", style="Muted.TLabel")
        self.step_indicator_lbl.pack(side=tk.LEFT, padx=20)

        self.next_btn = ttk.Button(self.btn_frame, text="Avanti >", command=self.next_step, style="Primary.TButton")
        self.next_btn.pack(side=tk.RIGHT)
        
        self.show_step()

    def clear_container(self):
        try:
            self.unbind_all("<MouseWheel>")
        except Exception:
            pass
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_step(self):
        self.clear_container()
        step_idx = self.current_step
        self.step_indicator_lbl.config(text=f"Passo {step_idx + 1} di {len(self.steps)}")

        # I passi 1, 3 e 4 hanno molti elementi o descrizioni ricche: usiamo una Canvas scorrevole fluida
        if step_idx in (1, 3, 4):
            canvas = tk.Canvas(self.container, highlightthickness=0, borderwidth=0)
            scrollbar = ttk.Scrollbar(self.container, orient="vertical", command=canvas.yview)
            scroll_frame = ttk.Frame(canvas)
            scroll_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
            
            def _on_canvas_configure(event):
                canvas.itemconfig(canvas_window, width=event.width)
            canvas.bind("<Configure>", _on_canvas_configure)
            
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

    def prev_step(self):
        if self.current_step > 0:
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
                for k in ATTRIBUTES:
                    self.char_data["attributes"][k] = self.attr_vars[k].get()

        # Salvataggio Passo 4: Background & Competenze
        if self.current_step == 3:
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
            if hasattr(self, "custom_skill1_var") and self.char_data["background"] == "Personalizzato":
                self.char_data["background_skills"] = [self.custom_skill1_var.get(), self.custom_skill2_var.get()]

        # Validazione & Creazione Passo 5: Dettagli Finali & Narrativa
        if self.current_step == 4:
            if hasattr(self, "name_var"):
                name = self.name_var.get().strip()
                if not name:
                    messagebox.showerror("Errore", "Il nome del personaggio è obbligatorio.")
                    return
                self.char_data["name"] = name
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
                self.char_data["backstory"] = self.backstory_text.get("1.0", tk.END).strip()
            
            self.finish_creation()
            return

        self.current_step += 1
        self.show_step()

    # -------------------------------------------------------------------------
    # PASSO 1: RAZZA
    # -------------------------------------------------------------------------
    def build_step_race(self, parent=None):
        parent = parent or self.container
        ttk.Label(parent, text="Passo 1: Scegli la Razza", style="Title.TLabel").pack(pady=(0, 10))
        
        self.race_var = tk.StringVar(value=self.char_data["race"])
        desc_label = ttk.Label(parent, text="", wraplength=520, justify=tk.LEFT)
        
        def update_desc(*args):
            r = self.race_var.get()
            self.char_data["race"] = r
            if r in RACES:
                desc_label.config(text=RACES[r]["desc"])
            
        self.race_var.trace_add("write", update_desc)
        
        cb = ttk.Combobox(parent, textvariable=self.race_var, values=list(RACES.keys()), state="readonly", font=self.default_font, width=22)
        cb.pack(pady=10)
            
        desc_label.pack(pady=15, fill=tk.X)
        update_desc()

    # -------------------------------------------------------------------------
    # PASSO 2: CLASSE
    # -------------------------------------------------------------------------
    def open_classes_comparison_dialog(self):
        """Apre una finestra modale con la tabella comparativa di tutte le 12 classi 5e."""
        top = tk.Toplevel(self)
        top.title("Tabella Comparativa delle 12 Classi (D&D 5e)")
        top.geometry("860x520")
        top.minsize(750, 400)
        apply_modern_window_style(top)
        top.transient(self)
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
                    var.set(pick if isinstance(pick, str) else pick.get("title", ""))
            
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
        
        def compose_story():
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
                trinket=self.trinket_var.get()
            )
            self.backstory_text.delete("1.0", tk.END)
            self.backstory_text.insert(tk.END, story)

        btn_compose = ttk.Button(story_top, text="✨ Componi la mia Storia (Automatico)", command=compose_story, style="Gold.TButton")
        btn_compose.pack(side=tk.RIGHT)

        self.backstory_text = tk.Text(story_card, height=6, wrap=tk.WORD, font=self.default_font)
        self.backstory_text.pack(fill=tk.BOTH, expand=True, pady=(2, 6))
        
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
        
        # Calcolo attributi = array + bonus razza
        race_info = RACES.get(c.race, RACES["Umano"])
        for attr in ATTRIBUTES:
            base = self.char_data["attributes"][attr]
            bonus = race_info["bonuses"].get(attr, 0)
            c.attributes[attr] = base + bonus
            
        def get_mod(val):
            return (val - 10) // 2

        con_mod = get_mod(c.attributes["COS"])
        dex_mod = get_mod(c.attributes["DES"])
        
        # Calcolo HP
        class_info = CLASSES.get(c.char_class, CLASSES["Guerriero"])
        c.hp_max = class_info["hd"] + con_mod
        c.hp_current = c.hp_max
        
        # Calcolo AC base (10 + Dex)
        c.ac = 10 + dex_mod
        c.initiative = dex_mod
        c.speed = race_info.get("speed", 30)
        
        # Equipaggiamento iniziale di classe (armi, armature, scudi) e incantesimi
        from common.starter_equipment import apply_class_and_race_starter_kit
        apply_class_and_race_starter_kit(c)
        
        # Aggiungi oro iniziale del background
        bg_gold = int(self.char_data.get("background_gold", 10))
        if hasattr(c, "currency") and isinstance(c.currency, dict):
            c.currency["MO"] = c.currency.get("MO", 0) + bg_gold

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

        # Competenze nelle abilità conferite dal background
        bg_skills = self.char_data.get("background_skills", [])
        for sk in bg_skills:
            if hasattr(c, "skills") and isinstance(c.skills, dict):
                if sk in c.skills and c.skills[sk] == 0:
                    c.skills[sk] = 1

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

        # Async fetch for Level 1 features (prima offline SRD istantaneo, poi fallback online se necessario)
        def _fetch_level_1():
            try:
                from common.srd_offline import get_class_level_features_offline
                off_data = get_class_level_features_offline(c.char_class, 1)
                if off_data and off_data.get("features"):
                    c.features += "\n\n--- Privilegi di Livello 1 ---\n" + "\n".join(f"- {ft}" for ft in off_data["features"])
                    if off_data.get("spell_slots"):
                        for lvl_str, cnt in off_data["spell_slots"].items():
                            c.spell_slots[lvl_str] = [0, cnt]
                else:
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
                                    c.spell_slots[str(i)] = [0, sc[key]]
            except Exception:
                pass
            
            try:
                self.master.after(0, self._on_creation_done, c)
            except RuntimeError:
                try:
                    self._on_creation_done(c)
                except Exception:
                    pass
            
        import threading
        threading.Thread(target=_fetch_level_1, daemon=True).start()

    def _on_creation_done(self, c):
        self.manager.add_character(c)
        try:
            messagebox.showinfo("Successo", f"Personaggio '{c.name}' creato con successo!", parent=self)
        except Exception:
            pass
        if self.on_complete_callback:
            try:
                self.on_complete_callback(c)
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass
