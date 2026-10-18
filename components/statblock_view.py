# components/statblock_view.py
"""
Componente UI Dark Fantasy per la visualizzazione dello Statblock autentico 5e.
Supporta rendering avanzato per:
- Mostri e PNG (Badge CA/HP/Velocità/CR, Tabella Caratteristiche, Tratti, Azioni con TpC/Danno)
- Oggetti Magici ed Equipaggiamento (Rarità colorata, Sintonizzazione, Proprietà, Descrizione)
- Incantesimi (Livello, Scuola, Tempo di Lancio, Componenti, Gittata, Durata)
- Regole generali ed elementi di compendio
"""

import tkinter as tk
from tkinter import ttk
import re
from typing import Dict, Any, Optional, Callable

from common.theme import (
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT,
    BORDER_COLOR, BORDER_GOLD, ACCENT_GOLD, ACCENT_GOLD_LIGHT,
    ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE, ACCENT_PURPLE,
    TEXT_COLOR, TEXT_MUTED, TEXT_GOLD,
    FONT_TITLE, FONT_HEADER, FONT_MAIN, FONT_BOLD, FONT_SMALL
)
from common.srd_offline import (
    normalize_ac_value,
    normalize_speed_value,
)

# Mappatura colori per la rarità degli oggetti D&D 5e
RARITY_COLORS = {
    "common": "#9CA3AF",        # Grigio
    "comune": "#9CA3AF",
    "uncommon": "#10B981",      # Verde smeraldo
    "non comune": "#10B981",
    "rare": "#3B82F6",          # Blu arcano
    "raro": "#3B82F6",
    "very rare": "#8B5CF6",     # Viola ametista
    "molto raro": "#8B5CF6",
    "legendary": "#F59E0B",     # Oro brillante
    "leggendario": "#F59E0B",
    "artifact": "#EF4444",      # Rosso artefatto
    "artefatto": "#EF4444"
}


class StatblockCardView(ttk.Frame):
    """
    Card Statblock Dark Fantasy 5e con scrollbar integrata.
    Si aggiorna all'istante alla selezione di un elemento.
    """

    def __init__(self, parent, on_primary_action: Optional[Callable[[Dict[str, Any], str], None]] = None, action_label: str = "Importa nella Sessione"):
        super().__init__(parent)
        self.on_primary_action = on_primary_action
        self.action_label = action_label
        self.current_data = None
        self.current_category = "Mostri"

        self._setup_layout()
        self.show_placeholder()

    def _setup_layout(self):
        # Canvas scorrevole per ospitare schede di qualsiasi altezza
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_content = tk.Frame(self.canvas, bg=BG_COLOR)

        self.scroll_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        # Mousewheel binding universale
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _on_mousewheel(self, event):
        # Solo se il cursore è sopra il nostro widget o figli
        try:
            widget_under_mouse = self.winfo_containing(event.x_root, event.y_root)
            if widget_under_mouse and (widget_under_mouse == self.canvas or str(widget_under_mouse).startswith(str(self))):
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def _clear_content(self):
        for child in self.scroll_content.winfo_children():
            child.destroy()
        self.canvas.yview_moveto(0.0)

    def show_placeholder(self, message: str = "Seleziona un elemento dalla lista per visualizzare lo Statblock completo."):
        self._clear_content()
        p_frame = tk.Frame(self.scroll_content, bg=BG_COLOR, padx=20, pady=60)
        p_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(p_frame, text="📜", font=("Segoe UI", 36), bg=BG_COLOR, fg=BORDER_GOLD).pack(pady=(0, 10))
        tk.Label(p_frame, text="Compendio D&D 5e", font=FONT_TITLE, bg=BG_COLOR, fg=ACCENT_GOLD).pack(pady=(0, 6))
        tk.Label(p_frame, text=message, font=FONT_MAIN, bg=BG_COLOR, fg=TEXT_MUTED, wraplength=420, justify="center").pack()

    def show_loading(self, item_name: str = "Elemento"):
        self._clear_content()
        p_frame = tk.Frame(self.scroll_content, bg=BG_COLOR, padx=20, pady=60)
        p_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(p_frame, text="⏳", font=("Segoe UI", 30), bg=BG_COLOR, fg=ACCENT_GOLD_LIGHT).pack(pady=(0, 8))
        tk.Label(p_frame, text=f"Recupero dettagli di '{item_name}'...", font=FONT_HEADER, bg=BG_COLOR, fg=TEXT_COLOR).pack()

    # -------------------------------------------------------------------------
    # STATBLOCK MOSTRI / PNG
    # -------------------------------------------------------------------------
    def show_monster(self, mdata: Dict[str, Any], raw_item: Optional[Dict[str, Any]] = None):
        self._clear_content()
        self.current_data = mdata
        self.current_category = "Mostri"

        container = tk.Frame(self.scroll_content, bg=SURFACE_COLOR, highlightbackground=BORDER_GOLD, highlightthickness=1.5, padx=14, pady=12)
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        name = mdata.get("name", "Creatura")
        size = mdata.get("size", "Media")
        m_type = mdata.get("type", "mostro")
        align = mdata.get("alignment", "qualsiasi allineamento")
        cr = str(mdata.get("challenge_rating", mdata.get("cr", "1")))

        # 1. Header con pulsante d'azione rapido
        top_row = tk.Frame(container, bg=SURFACE_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 4))

        title_box = tk.Frame(top_row, bg=SURFACE_COLOR)
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(title_box, text=f"🐉 {name}", font=FONT_TITLE, bg=SURFACE_COLOR, fg=ACCENT_GOLD_LIGHT, anchor="w").pack(anchor="w")
        tk.Label(title_box, text=f"{size} {m_type}, {align}", font=("Segoe UI", 9, "italic"), bg=SURFACE_COLOR, fg=TEXT_MUTED, anchor="w").pack(anchor="w")

        if self.on_primary_action:
            btn_act = ttk.Button(
                top_row,
                text=f"⚔️ {self.action_label}",
                command=lambda: self.on_primary_action(mdata, "Mostri"),
                style="Gold.TButton"
            )
            btn_act.pack(side=tk.RIGHT, padx=(6, 0))

        # Divisore dorato
        self._add_divider(container)

        # 2. Badge Vitali (CA, HP, Velocità, CR)
        hp = mdata.get("hit_points", mdata.get("hp", 10))
        hp_formula = mdata.get("hit_dice") or mdata.get("hit_points_roll") or ""
        hp_str = f"{hp} ({hp_formula})" if hp_formula else str(hp)

        ac = normalize_ac_value(mdata.get("armor_class", mdata.get("ac", 10)))
        raw_speed = mdata.get("speed", 30)
        speed_val, speed_disp, speed_unit = normalize_speed_value(raw_speed)

        badges_row = tk.Frame(container, bg=SURFACE_COLOR)
        badges_row.pack(fill=tk.X, pady=(4, 6))

        self._create_stat_badge(badges_row, "🛡️ CA", str(ac), ACCENT_BLUE)
        self._create_stat_badge(badges_row, "❤️ Punti Ferita", hp_str, ACCENT_RED)
        self._create_stat_badge(badges_row, "👟 Velocità", speed_disp, ACCENT_GREEN)
        self._create_stat_badge(badges_row, "🏆 Grado Sfida", f"CR {cr}", ACCENT_GOLD)

        self._add_divider(container)

        # 3. Ability Scores Table (FOR, DES, COS, INT, SAG, CAR)
        from common.srd_offline import extract_and_normalize_attributes
        attrs = mdata.get("attributes") or extract_and_normalize_attributes(mdata, name)

        attr_frame = tk.Frame(container, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=6)
        attr_frame.pack(fill=tk.X, pady=(2, 8))

        stat_order = [("FOR", "FOR"), ("DES", "DES"), ("COS", "COS"), ("INT", "INT"), ("SAG", "SAG"), ("CAR", "CAR")]
        for idx, (code, label) in enumerate(stat_order):
            col = tk.Frame(attr_frame, bg=SURFACE_COLOR_ALT)
            col.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=3)
            val = attrs.get(code, 10)
            mod = (val - 10) // 2
            mod_str = f"+{mod}" if mod >= 0 else str(mod)

            tk.Label(col, text=label, font=("Segoe UI", 8, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack()
            tk.Label(col, text=f"{val}", font=("Segoe UI", 11, "bold"), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).pack()
            tk.Label(col, text=f"({mod_str})", font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED).pack()

        # 4. Tratti Ausiliari (Sensi, Linguaggi, TS, Resistenze)
        aux_lines = []
        if mdata.get("saving_throws"):
            aux_lines.append(f"🛡️ Tiri Salvezza: {mdata.get('saving_throws')}")
        if mdata.get("damage_vulnerabilities"):
            aux_lines.append(f"💔 Vulnerabilità: {mdata.get('damage_vulnerabilities')}")
        if mdata.get("damage_resistances"):
            aux_lines.append(f"🛡️ Resistenze: {mdata.get('damage_resistances')}")
        if mdata.get("damage_immunities"):
            aux_lines.append(f"✨ Immunità ai Danni: {mdata.get('damage_immunities')}")
        if mdata.get("condition_immunities"):
            aux_lines.append(f"⚡ Immunità a Condizioni: {mdata.get('condition_immunities')}")
        if mdata.get("senses"):
            aux_lines.append(f"👁️ Sensi: {mdata.get('senses')}")
        if mdata.get("languages"):
            aux_lines.append(f"🗣️ Linguaggi: {mdata.get('languages')}")

        if aux_lines:
            aux_box = tk.Frame(container, bg=SURFACE_COLOR)
            aux_box.pack(fill=tk.X, pady=(2, 6))
            for line in aux_lines:
                tk.Label(aux_box, text=line, font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED, anchor="w", justify="left").pack(anchor="w")

        # 5. Abilità Speciali & Tratti
        traits = mdata.get("special_abilities") or mdata.get("features") or []
        if traits:
            self._add_section_header(container, "TRATTI & CAPACITÀ SPECIALI")
            for t in traits:
                t_name = t.get("name", "Tratto") if isinstance(t, dict) else str(t).split(":")[0]
                t_desc = t.get("desc", "") if isinstance(t, dict) else str(t)
                self._add_feature_block(container, t_name, t_desc)

        # 6. Azioni & Attacchi
        actions = mdata.get("actions") or []
        if actions:
            self._add_section_header(container, "AZIONI & ATTACCHI")
            for act in actions:
                a_name = act.get("name", "Attacco") if isinstance(act, dict) else str(act).split(":")[0]
                a_desc = act.get("desc", "") if isinstance(act, dict) else str(act)
                self._add_action_block(container, a_name, a_desc, act)

        # 7. Azioni Leggendarie
        leg_actions = mdata.get("legendary_actions") or []
        if leg_actions:
            self._add_section_header(container, "AZIONI LEGGENDARIE")
            for leg in leg_actions:
                l_name = leg.get("name", "Azione Leggendaria") if isinstance(leg, dict) else str(leg).split(":")[0]
                l_desc = leg.get("desc", "") if isinstance(leg, dict) else str(leg)
                self._add_feature_block(container, l_name, l_desc)

    # -------------------------------------------------------------------------
    # STATBLOCK OGGETTI MAGICI ED EQUIPAGGIAMENTO
    # -------------------------------------------------------------------------
    def show_magic_item(self, item_data: Dict[str, Any]):
        self._clear_content()
        self.current_data = item_data
        self.current_category = "Oggetti"

        container = tk.Frame(self.scroll_content, bg=SURFACE_COLOR, highlightbackground=BORDER_GOLD, highlightthickness=1.5, padx=14, pady=12)
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        name = item_data.get("name", "Oggetto")
        rarity_raw = str(item_data.get("rarity", "Comune")).lower()
        i_type = item_data.get("type") or item_data.get("equipment_category", {}).get("name") if isinstance(item_data.get("equipment_category"), dict) else item_data.get("equipment_category", "Oggetto")

        rarity_color = RARITY_COLORS.get(rarity_raw, "#9CA3AF")
        rarity_label = rarity_raw.capitalize()

        # Top row
        top_row = tk.Frame(container, bg=SURFACE_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 4))

        title_box = tk.Frame(top_row, bg=SURFACE_COLOR)
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        icon = "🔮" if "wondrous" in str(i_type).lower() or "mag" in str(i_type).lower() else ("⚔️" if "weapon" in str(i_type).lower() else ("🛡️" if "armor" in str(i_type).lower() else "🎒"))
        tk.Label(title_box, text=f"{icon} {name}", font=FONT_TITLE, bg=SURFACE_COLOR, fg=ACCENT_GOLD_LIGHT, anchor="w").pack(anchor="w")
        tk.Label(title_box, text=f"{i_type}", font=("Segoe UI", 9, "italic"), bg=SURFACE_COLOR, fg=TEXT_MUTED, anchor="w").pack(anchor="w")

        if self.on_primary_action:
            btn_act = ttk.Button(
                top_row,
                text=f"🎁 {self.action_label}",
                command=lambda: self.on_primary_action(item_data, "Oggetti"),
                style="Gold.TButton"
            )
            btn_act.pack(side=tk.RIGHT, padx=(6, 0))

        self._add_divider(container)

        # Badges row
        b_row = tk.Frame(container, bg=SURFACE_COLOR)
        b_row.pack(fill=tk.X, pady=(4, 8))

        self._create_stat_badge(b_row, "Rarità", rarity_label, rarity_color)

        requires_attunement = "attunement" in str(item_data.get("desc", "")).lower() or item_data.get("requires_attunement", False)
        if requires_attunement:
            self._create_stat_badge(b_row, "Sintonizzazione", "✨ Richiesta", ACCENT_PURPLE)

        cost = item_data.get("cost")
        if cost:
            cost_str = f"{cost.get('quantity', 0)} {cost.get('unit', 'mo')}" if isinstance(cost, dict) else str(cost)
            self._create_stat_badge(b_row, "Valore / Costo", cost_str, ACCENT_GOLD)

        weight = item_data.get("weight")
        if weight:
            self._create_stat_badge(b_row, "Peso", f"{weight} lbs", TEXT_MUTED)

        self._add_divider(container)

        # Descrizione & Proprietà
        desc = item_data.get("desc", "")
        if isinstance(desc, list):
            desc = "\n\n".join(desc)
        elif not desc and "description" in item_data:
            desc = item_data.get("description", "")

        txt_frame = tk.Frame(container, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=10)
        txt_frame.pack(fill=tk.BOTH, expand=True, pady=6)

        tk.Label(txt_frame, text=desc, font=FONT_MAIN, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, justify="left", wraplength=480, anchor="w").pack(anchor="w")

    # -------------------------------------------------------------------------
    # STATBLOCK INCANTESIMI
    # -------------------------------------------------------------------------
    def show_spell(self, sdata: Dict[str, Any]):
        self._clear_content()
        self.current_data = sdata
        self.current_category = "Incantesimi"

        container = tk.Frame(self.scroll_content, bg=SURFACE_COLOR, highlightbackground=BORDER_GOLD, highlightthickness=1.5, padx=14, pady=12)
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        name = sdata.get("name", "Incantesimo")
        lvl = sdata.get("level", 0)
        lvl_str = "Trucchetto" if lvl == 0 or str(lvl).lower() == "cantrip" else f"Livello {lvl}"
        school = sdata.get("school", {}).get("name") if isinstance(sdata.get("school"), dict) else sdata.get("school", "")

        top_row = tk.Frame(container, bg=SURFACE_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 4))

        title_box = tk.Frame(top_row, bg=SURFACE_COLOR)
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(title_box, text=f"✨ {name}", font=FONT_TITLE, bg=SURFACE_COLOR, fg=ACCENT_GOLD_LIGHT, anchor="w").pack(anchor="w")
        tk.Label(title_box, text=f"{lvl_str} • {school}", font=("Segoe UI", 9, "italic"), bg=SURFACE_COLOR, fg=TEXT_MUTED, anchor="w").pack(anchor="w")

        if self.on_primary_action:
            btn_act = ttk.Button(
                top_row,
                text=f"📖 {self.action_label}",
                command=lambda: self.on_primary_action(sdata, "Incantesimi"),
                style="Gold.TButton"
            )
            btn_act.pack(side=tk.RIGHT, padx=(6, 0))

        self._add_divider(container)

        # Badges row
        b_row = tk.Frame(container, bg=SURFACE_COLOR)
        b_row.pack(fill=tk.X, pady=(4, 8))

        self._create_stat_badge(b_row, "⏱️ Tempo di Lancio", str(sdata.get("casting_time", "1 Azione")), ACCENT_BLUE)
        self._create_stat_badge(b_row, "📏 Gittata", str(sdata.get("range", "A contatto")), ACCENT_GREEN)
        self._create_stat_badge(b_row, "📜 Componenti", str(sdata.get("components", "V, S")), ACCENT_GOLD)
        self._create_stat_badge(b_row, "⏳ Durata", str(sdata.get("duration", "Istantanea")), ACCENT_PURPLE)

        self._add_divider(container)

        # Descrizione
        desc = sdata.get("desc", "")
        if isinstance(desc, list):
            desc = "\n\n".join(desc)

        txt_frame = tk.Frame(container, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=10)
        txt_frame.pack(fill=tk.BOTH, expand=True, pady=6)

        tk.Label(txt_frame, text=desc, font=FONT_MAIN, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, justify="left", wraplength=480, anchor="w").pack(anchor="w")

        higher = sdata.get("higher_level")
        if higher:
            higher_str = "\n".join(higher) if isinstance(higher, list) else str(higher)
            h_frame = tk.Frame(container, bg=SURFACE_COLOR, pady=6)
            h_frame.pack(fill=tk.X)
            tk.Label(h_frame, text="✨ Ai Livelli Superiori:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
            tk.Label(h_frame, text=higher_str, font=FONT_MAIN, bg=SURFACE_COLOR, fg=TEXT_MUTED, justify="left", wraplength=480).pack(anchor="w")

    # -------------------------------------------------------------------------
    # GENERIC / FALLBACK
    # -------------------------------------------------------------------------
    def show_generic(self, title: str, data_dict: Dict[str, Any]):
        self._clear_content()
        self.current_data = data_dict

        container = tk.Frame(self.scroll_content, bg=SURFACE_COLOR, highlightbackground=BORDER_GOLD, highlightthickness=1.5, padx=14, pady=12)
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        top_row = tk.Frame(container, bg=SURFACE_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 4))

        tk.Label(top_row, text=f"📖 {title}", font=FONT_TITLE, bg=SURFACE_COLOR, fg=ACCENT_GOLD_LIGHT, anchor="w").pack(side=tk.LEFT)

        if self.on_primary_action:
            btn_act = ttk.Button(
                top_row,
                text=f"➕ {self.action_label}",
                command=lambda: self.on_primary_action(data_dict, "Generico"),
                style="Gold.TButton"
            )
            btn_act.pack(side=tk.RIGHT)

        self._add_divider(container)

        txt_frame = tk.Frame(container, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=10)
        txt_frame.pack(fill=tk.BOTH, expand=True, pady=6)

        lines = []
        if "desc" in data_dict:
            d = data_dict["desc"]
            lines.append("\n\n".join(d) if isinstance(d, list) else str(d))
            lines.append("\n" + "─" * 40 + "\n")

        for k, v in data_dict.items():
            if k not in ["name", "desc", "url", "index"]:
                if isinstance(v, (str, int, float, bool)):
                    lines.append(f"{k.capitalize()}: {v}")
                elif isinstance(v, list) and v and isinstance(v[0], dict) and "name" in v[0]:
                    lines.append(f"{k.capitalize()}: {', '.join(x.get('name', '') for x in v)}")

        content_str = "\n".join(lines) if lines else "Nessun dettaglio aggiuntivo disponibile."
        tk.Label(txt_frame, text=content_str, font=FONT_MAIN, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, justify="left", wraplength=480, anchor="w").pack(anchor="w")

    # -------------------------------------------------------------------------
    # HELPERS VISIVI
    # -------------------------------------------------------------------------
    def _add_divider(self, parent):
        sep = tk.Frame(parent, height=2, bg=BORDER_GOLD)
        sep.pack(fill=tk.X, pady=6)

    def _create_stat_badge(self, parent, label: str, value: str, accent_color: str):
        badge = tk.Frame(parent, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=4)
        badge.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=3)

        tk.Label(badge, text=label, font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED).pack()
        tk.Label(badge, text=value, font=("Segoe UI", 10, "bold"), bg=SURFACE_COLOR_ALT, fg=accent_color).pack()

    def _add_section_header(self, parent, title: str):
        h_frame = tk.Frame(parent, bg=SURFACE_COLOR)
        h_frame.pack(fill=tk.X, pady=(8, 4))
        tk.Label(h_frame, text=title, font=("Georgia", 10, "bold"), bg=SURFACE_COLOR, fg=ACCENT_RED).pack(anchor="w")
        sep = tk.Frame(h_frame, height=1, bg=ACCENT_RED)
        sep.pack(fill=tk.X, pady=(2, 4))

    def _add_feature_block(self, parent, name: str, desc: str):
        box = tk.Frame(parent, bg=SURFACE_COLOR, pady=2)
        box.pack(fill=tk.X)
        header = tk.Label(box, text=f"• {name}.", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR, fg=ACCENT_GOLD_LIGHT, anchor="w")
        header.pack(anchor="w")
        body = tk.Label(box, text=desc, font=FONT_MAIN, bg=SURFACE_COLOR, fg=TEXT_COLOR, justify="left", wraplength=480, anchor="w")
        body.pack(anchor="w", padx=(10, 0))

    def _add_action_block(self, parent, name: str, desc: str, act_dict: Optional[Dict[str, Any]] = None):
        box = tk.Frame(parent, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=5)
        box.pack(fill=tk.X, pady=3)

        # Riga Titolo Azione & Tag di Combattimento
        top = tk.Frame(box, bg=SURFACE_COLOR_ALT)
        top.pack(fill=tk.X)

        tk.Label(top, text=f"⚔️ {name}", font=("Segoe UI", 10, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD_LIGHT).pack(side=tk.LEFT)

        tags = []
        if isinstance(act_dict, dict):
            if act_dict.get("attack_bonus"):
                tags.append(f"🎯 TxC: +{act_dict.get('attack_bonus')}")
            m_hit = re.search(r'Hit:\s*([0-9]+\s*\([^)]+\))', desc)
            if m_hit:
                tags.append(f"💥 Danno: {m_hit.group(1)}")
            elif act_dict.get("damage_dice"):
                tags.append(f"💥 Danno: {act_dict.get('damage_dice')}")
        if tags:
            tk.Label(top, text="  •  ".join(tags), font=("Segoe UI", 8, "bold"), bg=SURFACE_COLOR_ALT, fg=TEXT_GOLD).pack(side=tk.RIGHT)

        tk.Label(box, text=desc, font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, justify="left", wraplength=470, anchor="w").pack(anchor="w", pady=(3, 0))

