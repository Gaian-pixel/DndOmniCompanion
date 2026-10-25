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
import random
from typing import Dict, Any, Optional, Callable, List

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
    get_bilingual_label,
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
    Card Statblock Dark Fantasy 5e con scrollbar integrata e dadi interattivi.
    Si aggiorna all'istante alla selezione di un elemento.
    """

    def __init__(
        self,
        parent,
        on_primary_action: Optional[Callable[[Dict[str, Any], str], None]] = None,
        action_label: str = "Importa nella Sessione",
        on_toggle_favorite: Optional[Callable[[Dict[str, Any], str], bool]] = None,
        is_favorite_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
        on_edit_custom: Optional[Callable[[Dict[str, Any], str], None]] = None,
        on_delete_custom: Optional[Callable[[Dict[str, Any], str], None]] = None,
    ):
        super().__init__(parent)
        self.on_primary_action = on_primary_action
        self.action_label = action_label
        self.on_toggle_favorite = on_toggle_favorite
        self.is_favorite_fn = is_favorite_fn
        self.on_edit_custom = on_edit_custom
        self.on_delete_custom = on_delete_custom
        self.current_data = None
        self.current_category = "Mostri"
        self.quantity_var = tk.IntVar(value=1)
        self.last_roll_result: Optional[Dict[str, Any]] = None

        self._setup_layout()
        self.show_placeholder()

    def _format_action_label(self, icon: str) -> str:
        raw = (self.action_label or "Importa").strip()
        cleaned = raw.lstrip("⚔️✨📜➕🎁📦• ").strip()
        return f"{icon} {cleaned}" if cleaned else f"{icon} {raw}"

    def _setup_layout(self):
        # Banner superiore per i risultati dei tiri di dado interattivi (nascosto finché non si tira)
        self.dice_banner = tk.Frame(
            self,
            bg=SURFACE_COLOR_ALT,
            highlightbackground=BORDER_GOLD,
            highlightthickness=1,
            padx=10,
            pady=5,
        )
        self.dice_banner_lbl = tk.Label(
            self.dice_banner,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg=SURFACE_COLOR_ALT,
            fg=ACCENT_GOLD_LIGHT,
            anchor="w",
        )
        self.dice_banner_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        btn_close_roll = tk.Button(
            self.dice_banner,
            text="✕",
            command=lambda: self.dice_banner.pack_forget(),
            bg=SURFACE_COLOR_ALT,
            fg=TEXT_MUTED,
            bd=0,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        )
        btn_close_roll.pack(side=tk.RIGHT)

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

    # -------------------------------------------------------------------------
    # MOTORE TIRI DI DADO INTERATTIVI NELLO STATBLOCK
    # -------------------------------------------------------------------------
    def roll_dice_formula(self, formula: str, label: str = "Tiro") -> Dict[str, Any]:
        """Esegue un tiro di dado (es. '2d6+3', '8d6', '1d20+5') e mostra il risultato nel banner."""
        clean = str(formula).replace(" ", "")
        m = re.search(r'(\d+)d(\d+)([+-]\d+)?', clean, re.IGNORECASE)
        if not m:
            return {"total": 0, "formula": formula, "rolls": [], "mod": 0}
        count = max(1, min(100, int(m.group(1))))
        sides = max(2, int(m.group(2)))
        mod = int(m.group(3)) if m.group(3) else 0
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + mod

        rolls_str = "+".join(str(r) for r in rolls)
        mod_str = f" {'+' if mod > 0 else '-'} {abs(mod)}" if mod != 0 else ""
        crit_note = ""
        fg_color = ACCENT_GOLD_LIGHT
        if count == 1 and sides == 20:
            if rolls[0] == 20:
                crit_note = " 🌟 CRITICO NATURALE (20)!"
                fg_color = ACCENT_GREEN
            elif rolls[0] == 1:
                crit_note = " 💀 FALLIMENTO CRITICO (1)!"
                fg_color = ACCENT_RED

        msg = f"🎲 {label}: {total}   [{count}d{sides}: ({rolls_str}){mod_str}]{crit_note}"
        self.last_roll_result = {
            "label": label,
            "formula": f"{count}d{sides}{f'{mod:+d}' if mod else ''}",
            "rolls": rolls,
            "mod": mod,
            "total": total,
            "text": msg,
        }
        try:
            self.dice_banner_lbl.config(text=msg, fg=fg_color)
            if not self.dice_banner.winfo_ismapped():
                self.dice_banner.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(6, 0), before=self.canvas)
        except Exception:
            pass
        return self.last_roll_result

    def _trigger_primary_action(self, data_dict: Dict[str, Any], category: str):
        if not self.on_primary_action:
            return
        try:
            qty = max(1, int(self.quantity_var.get()))
        except (ValueError, TypeError, tk.TclError):
            qty = 1
        data_dict["import_quantity"] = qty
        for _ in range(qty):
            self.on_primary_action(data_dict, category)

    def _build_header_controls(self, parent: tk.Widget, data_dict: Dict[str, Any], category: str, icon: str):
        """Costruisce la barra di controllo nell'header dello Statblock: Preferito, Edit/Delete Custom, Qtà e Importa."""
        ctrl_box = tk.Frame(parent, bg=SURFACE_COLOR)
        ctrl_box.pack(side=tk.RIGHT, padx=(6, 0))

        # 1. Pulsante Preferito (⭐)
        if self.on_toggle_favorite:
            is_fav = bool(self.is_favorite_fn(data_dict)) if self.is_favorite_fn else False
            fav_btn = tk.Button(
                ctrl_box,
                text="⭐" if is_fav else "☆",
                font=("Segoe UI", 11, "bold"),
                bg=SURFACE_COLOR_ALT,
                fg=ACCENT_GOLD if is_fav else TEXT_MUTED,
                activebackground=BORDER_GOLD,
                bd=1,
                relief=tk.SOLID,
                padx=6,
                pady=1,
                cursor="hand2",
            )
            def _toggle_fav():
                now_fav = self.on_toggle_favorite(data_dict, category)
                fav_btn.config(text="⭐" if now_fav else "☆", fg=ACCENT_GOLD if now_fav else TEXT_MUTED)
            fav_btn.config(command=_toggle_fav)
            fav_btn.pack(side=tk.LEFT, padx=(0, 4))

        # 2. Pulsanti Modifica / Elimina per voci [Custom]
        if data_dict.get("is_custom"):
            if self.on_edit_custom:
                ttk.Button(
                    ctrl_box,
                    text="✏️",
                    width=3,
                    command=lambda: self.on_edit_custom(data_dict, category),
                ).pack(side=tk.LEFT, padx=(0, 3))
            if self.on_delete_custom:
                ttk.Button(
                    ctrl_box,
                    text="🗑️",
                    width=3,
                    command=lambda: self.on_delete_custom(data_dict, category),
                    style="Danger.TButton",
                ).pack(side=tk.LEFT, padx=(0, 4))

        # 3. Selettore Quantità + Pulsante Primario d'Importazione/Spawn
        if self.on_primary_action:
            if category in ("Mostri", "Oggetti", "Equipaggiamento"):
                self.quantity_var.set(1)
                qty_lbl = tk.Label(ctrl_box, text="Qtà:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
                qty_lbl.pack(side=tk.LEFT, padx=(2, 2))
                qty_spin = ttk.Spinbox(
                    ctrl_box,
                    from_=1,
                    to=20,
                    textvariable=self.quantity_var,
                    width=3,
                    justify="center",
                )
                qty_spin.pack(side=tk.LEFT, padx=(0, 5))

            btn_act = ttk.Button(
                ctrl_box,
                text=self._format_action_label(icon),
                command=lambda: self._trigger_primary_action(data_dict, category),
                style="Gold.TButton",
            )
            btn_act.pack(side=tk.LEFT)

    def _add_quick_dice_bar(self, parent: tk.Widget, text_to_scan: str, source_name: str):
        """Estrae formule di dado (es. '8d6', '2d4 + 2') dal testo e crea pulsanti rapidi di lancio."""
        if not text_to_scan:
            return
        matches = re.findall(r'\b\d+d\d+(?:\s*[+-]\s*\d+)?\b', str(text_to_scan), re.IGNORECASE)
        unique_formulas: List[str] = []
        for m in matches:
            norm = m.replace(" ", "").lower()
            if norm not in unique_formulas:
                unique_formulas.append(norm)
        if not unique_formulas:
            return

        bar = tk.Frame(parent, bg=SURFACE_COLOR, pady=4)
        bar.pack(fill=tk.X)
        tk.Label(bar, text="🎲 Tiri Rapidi:", font=("Segoe UI", 8, "bold"), bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT, padx=(0, 6))
        for f_str in unique_formulas[:5]:
            btn = tk.Button(
                bar,
                text=f"🎲 {f_str}",
                font=("Segoe UI", 8, "bold"),
                bg=SURFACE_COLOR_ALT,
                fg=ACCENT_GOLD_LIGHT,
                activebackground=BORDER_GOLD,
                bd=1,
                relief=tk.SOLID,
                padx=6,
                pady=1,
                cursor="hand2",
                command=lambda fs=f_str: self.roll_dice_formula(fs, f"{source_name} ({fs})"),
            )
            btn.pack(side=tk.LEFT, padx=2)


    def _on_mousewheel(self, event):
        # Solo se il cursore è sopra il nostro widget o figli
        try:
            if not self.winfo_exists() or not self.canvas.winfo_exists():
                return
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

        name = mdata.get("name") or mdata.get("title", "Creatura")
        disp_name = get_bilingual_label(name, "Mostri")
        size = mdata.get("size", "Media")
        m_type = mdata.get("type", "mostro")
        align = mdata.get("alignment", "qualsiasi allineamento")
        cr = str(mdata.get("challenge_rating", mdata.get("cr", "1")))

        # 1. Header con pulsante d'azione rapido, quantità e preferiti
        top_row = tk.Frame(container, bg=SURFACE_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 4))

        title_box = tk.Frame(top_row, bg=SURFACE_COLOR)
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(title_box, text=f"🐉 {disp_name}", font=FONT_TITLE, bg=SURFACE_COLOR, fg=ACCENT_GOLD_LIGHT, anchor="w").pack(anchor="w")
        tk.Label(title_box, text=f"{size} {m_type}, {align}", font=("Segoe UI", 9, "italic"), bg=SURFACE_COLOR, fg=TEXT_MUTED, anchor="w").pack(anchor="w")

        self._build_header_controls(top_row, mdata, "Mostri", "⚔️")

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

        # 3. Ability Scores Table (FOR, DES, COS, INT, SAG, CAR) — cliccabili per tirare 1d20+mod
        from common.srd_offline import extract_and_normalize_attributes
        attrs = mdata.get("attributes") or extract_and_normalize_attributes(mdata, name)

        attr_frame = tk.Frame(container, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=6)
        attr_frame.pack(fill=tk.X, pady=(2, 8))

        stat_order = [("FOR", "FOR"), ("DES", "DES"), ("COS", "COS"), ("INT", "INT"), ("SAG", "SAG"), ("CAR", "CAR")]
        for idx, (code, label) in enumerate(stat_order):
            col = tk.Frame(attr_frame, bg=SURFACE_COLOR_ALT, cursor="hand2")
            col.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=3)
            val = attrs.get(code, 10)
            mod = (val - 10) // 2
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            formula_stat = f"1d20{mod:+d}" if mod != 0 else "1d20"

            l1 = tk.Label(col, text=f"🎲 {label}", font=("Segoe UI", 8, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD, cursor="hand2")
            l1.pack()
            l2 = tk.Label(col, text=f"{val}", font=("Segoe UI", 11, "bold"), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, cursor="hand2")
            l2.pack()
            l3 = tk.Label(col, text=f"({mod_str})", font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, cursor="hand2")
            l3.pack()

            for w in (col, l1, l2, l3):
                w.bind(
                    "<Button-1>",
                    lambda e, fs=formula_stat, sc=label, mn=name: self.roll_dice_formula(fs, f"{mn} • Prova {sc}"),
                )

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

        # 8. Descrizione testuale custom (se presente)
        if mdata.get("desc") and not actions and not traits:
            self._add_section_header(container, "DESCRIZIONE & NOTE")
            tk.Label(container, text=str(mdata.get("desc")), font=FONT_MAIN, bg=SURFACE_COLOR, fg=TEXT_COLOR, justify="left", wraplength=480, anchor="w").pack(anchor="w")
            self._add_quick_dice_bar(container, str(mdata.get("desc")), name)

    # -------------------------------------------------------------------------
    # STATBLOCK OGGETTI MAGICI ED EQUIPAGGIAMENTO
    # -------------------------------------------------------------------------
    def show_magic_item(self, item_data: Dict[str, Any]):
        self._clear_content()
        self.current_data = item_data
        self.current_category = "Oggetti"

        container = tk.Frame(self.scroll_content, bg=SURFACE_COLOR, highlightbackground=BORDER_GOLD, highlightthickness=1.5, padx=14, pady=12)
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        name = item_data.get("name") or item_data.get("title", "Oggetto")
        disp_name = get_bilingual_label(name, "Oggetti")
        rarity_raw = str(item_data.get("rarity", "Comune")).lower()
        i_type = item_data.get("type") or item_data.get("equipment_category", {}).get("name") if isinstance(item_data.get("equipment_category"), dict) else item_data.get("equipment_category", "Oggetto")

        rarity_color = RARITY_COLORS.get(rarity_raw, "#9CA3AF")
        rarity_label = rarity_raw.capitalize()

        # Top row
        top_row = tk.Frame(container, bg=SURFACE_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 4))

        title_box = tk.Frame(top_row, bg=SURFACE_COLOR)
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        icon = "🔮" if "wondrous" in str(i_type).lower() or "mag" in str(i_type).lower() else ("⚔️" if "weapon" in str(i_type).lower() or "arma" in str(i_type).lower() else ("🛡️" if "armor" in str(i_type).lower() or "armatura" in str(i_type).lower() else "🎒"))
        tk.Label(title_box, text=f"{icon} {disp_name}", font=FONT_TITLE, bg=SURFACE_COLOR, fg=ACCENT_GOLD_LIGHT, anchor="w").pack(anchor="w")
        tk.Label(title_box, text=f"{i_type}", font=("Segoe UI", 9, "italic"), bg=SURFACE_COLOR, fg=TEXT_MUTED, anchor="w").pack(anchor="w")

        self._build_header_controls(top_row, item_data, "Oggetti", "🎁")

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

        dmg_info = item_data.get("damage")
        if isinstance(dmg_info, dict) and dmg_info.get("damage_dice"):
            d_type = dmg_info.get("damage_type", {}).get("name", "") if isinstance(dmg_info.get("damage_type"), dict) else ""
            self._create_stat_badge(b_row, "Danno", f"{dmg_info['damage_dice']} {d_type}".strip(), ACCENT_RED)

        self._add_divider(container)

        # Descrizione & Proprietà
        desc = item_data.get("desc", "")
        if isinstance(desc, list):
            desc = "\n\n".join(desc)
        elif not desc and "description" in item_data:
            desc = item_data.get("description", "")

        # Barra tiri rapidi per eventuali dadi nell'oggetto (es. Pozioni 2d4+2, Armi 1d8, Bacchette 8d6)
        scan_txt = str(desc)
        if isinstance(dmg_info, dict) and dmg_info.get("damage_dice"):
            scan_txt = f"{dmg_info['damage_dice']} " + scan_txt
        self._add_quick_dice_bar(container, scan_txt, name)

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

        name = sdata.get("name") or sdata.get("title", "Incantesimo")
        disp_name = get_bilingual_label(name, "Incantesimi")
        lvl = sdata.get("level", 0)
        lvl_str = "Trucchetto" if lvl == 0 or str(lvl).lower() == "cantrip" else f"Livello {lvl}"
        school = sdata.get("school", {}).get("name") if isinstance(sdata.get("school"), dict) else sdata.get("school", "")

        top_row = tk.Frame(container, bg=SURFACE_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 4))

        title_box = tk.Frame(top_row, bg=SURFACE_COLOR)
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(title_box, text=f"✨ {disp_name}", font=FONT_TITLE, bg=SURFACE_COLOR, fg=ACCENT_GOLD_LIGHT, anchor="w").pack(anchor="w")
        tk.Label(title_box, text=f"{lvl_str} • {school}", font=("Segoe UI", 9, "italic"), bg=SURFACE_COLOR, fg=TEXT_MUTED, anchor="w").pack(anchor="w")

        self._build_header_controls(top_row, sdata, "Incantesimi", "📖")

        self._add_divider(container)

        # Badges row
        b_row = tk.Frame(container, bg=SURFACE_COLOR)
        b_row.pack(fill=tk.X, pady=(4, 8))

        self._create_stat_badge(b_row, "⏱️ Tempo di Lancio", str(sdata.get("casting_time") or sdata.get("time") or "1 Azione"), ACCENT_BLUE)
        self._create_stat_badge(b_row, "📏 Gittata", str(sdata.get("range", "A contatto")), ACCENT_GREEN)
        self._create_stat_badge(b_row, "📜 Componenti", str(sdata.get("components", "V, S")), ACCENT_GOLD)
        self._create_stat_badge(b_row, "⏳ Durata", str(sdata.get("duration", "Istantanea")), ACCENT_PURPLE)

        self._add_divider(container)

        # Descrizione
        desc = sdata.get("desc", "")
        if isinstance(desc, list):
            desc = "\n\n".join(desc)

        self._add_quick_dice_bar(container, str(desc), name)

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
        real_title = title or data_dict.get("name") or data_dict.get("title", "Dettagli")

        container = tk.Frame(self.scroll_content, bg=SURFACE_COLOR, highlightbackground=BORDER_GOLD, highlightthickness=1.5, padx=14, pady=12)
        container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        top_row = tk.Frame(container, bg=SURFACE_COLOR)
        top_row.pack(fill=tk.X, pady=(0, 4))

        title_box = tk.Frame(top_row, bg=SURFACE_COLOR)
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(title_box, text=f"📖 {real_title}", font=FONT_TITLE, bg=SURFACE_COLOR, fg=ACCENT_GOLD_LIGHT, anchor="w").pack(anchor="w")

        manual_name = data_dict.get("manual_name")
        page_ref = data_dict.get("page_ref")
        cat_badge = data_dict.get("category")
        meta_parts = []
        if manual_name:
            meta_parts.append(str(manual_name))
        if page_ref:
            meta_parts.append(str(page_ref))
        if cat_badge:
            meta_parts.append(f"[{cat_badge}]")
        if meta_parts:
            tk.Label(title_box, text=" • ".join(meta_parts), font=("Segoe UI", 9, "italic"), bg=SURFACE_COLOR, fg=ACCENT_GOLD, anchor="w").pack(anchor="w")

        self._build_header_controls(top_row, data_dict, cat_badge or "Generico", "➕")

        self._add_divider(container)

        txt_frame = tk.Frame(container, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=10)
        txt_frame.pack(fill=tk.BOTH, expand=True, pady=6)

        if data_dict.get("content"):
            content_str = data_dict.get("content")
        else:
            lines = []
            if "desc" in data_dict:
                d = data_dict["desc"]
                lines.append("\n\n".join(d) if isinstance(d, list) else str(d))
                lines.append("\n" + "─" * 40 + "\n")

            for k, v in data_dict.items():
                if k not in ["name", "title", "desc", "content", "url", "index", "keywords", "monster_data", "id", "pdf_filename", "pdf_page"]:
                    if isinstance(v, (str, int, float, bool)):
                        lines.append(f"{k.capitalize()}: {v}")
                    elif isinstance(v, list) and v and isinstance(v[0], dict) and "name" in v[0]:
                        lines.append(f"{k.capitalize()}: {', '.join(x.get('name', '') for x in v)}")

            content_str = "\n".join(lines) if lines else "Nessun dettaglio aggiuntivo disponibile."

        self._add_quick_dice_bar(container, content_str, real_title)
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

        # Riga Titolo Azione & Bottoni Interattivi di Combattimento
        top = tk.Frame(box, bg=SURFACE_COLOR_ALT)
        top.pack(fill=tk.X)

        tk.Label(top, text=f"⚔️ {name}", font=("Segoe UI", 10, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD_LIGHT).pack(side=tk.LEFT)

        atk_bonus = None
        dmg_formula = None
        if isinstance(act_dict, dict):
            if act_dict.get("attack_bonus") is not None:
                atk_bonus = act_dict.get("attack_bonus")
            if act_dict.get("damage_dice"):
                dmg_formula = str(act_dict.get("damage_dice")).strip()
                if act_dict.get("damage_bonus"):
                    db = int(act_dict.get("damage_bonus"))
                    dmg_formula = f"{dmg_formula}{db:+d}"

        if atk_bonus is None:
            m_atk = re.search(r'([+-]\d+)\s*(?:to hit|a colpire)', desc, re.IGNORECASE)
            if m_atk:
                atk_bonus = int(m_atk.group(1))

        if not dmg_formula:
            m_dmg = re.search(r'\((\d+d\d+(?:\s*[+-]\s*\d+)?)\)', desc)
            if not m_dmg:
                m_dmg = re.search(r'\b(\d+d\d+(?:\s*[+-]\s*\d+)?)\b', desc)
            if m_dmg:
                dmg_formula = m_dmg.group(1).replace(" ", "")

        btn_bar = tk.Frame(top, bg=SURFACE_COLOR_ALT)
        btn_bar.pack(side=tk.RIGHT)

        if atk_bonus is not None:
            try:
                b_int = int(atk_bonus)
                atk_str = f"+{b_int}" if b_int >= 0 else str(b_int)
                f_atk = f"1d20{b_int:+d}" if b_int != 0 else "1d20"
                tk.Button(
                    btn_bar,
                    text=f"🎯 TxC {atk_str}",
                    font=("Segoe UI", 8, "bold"),
                    bg=SURFACE_COLOR,
                    fg=ACCENT_GOLD,
                    activebackground=BORDER_GOLD,
                    bd=1,
                    relief=tk.SOLID,
                    padx=5,
                    pady=1,
                    cursor="hand2",
                    command=lambda fa=f_atk, an=name: self.roll_dice_formula(fa, f"{an} • Tiro per Colpire"),
                ).pack(side=tk.LEFT, padx=(0, 4))
            except (ValueError, TypeError):
                pass

        if dmg_formula:
            tk.Button(
                btn_bar,
                text=f"💥 Danno {dmg_formula}",
                font=("Segoe UI", 8, "bold"),
                bg=SURFACE_COLOR,
                fg=ACCENT_RED,
                activebackground=BORDER_GOLD,
                bd=1,
                relief=tk.SOLID,
                padx=5,
                pady=1,
                cursor="hand2",
                command=lambda fd=dmg_formula, an=name: self.roll_dice_formula(fd, f"{an} • Danno"),
            ).pack(side=tk.LEFT)

        tk.Label(box, text=desc, font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, justify="left", wraplength=470, anchor="w").pack(anchor="w", pady=(3, 0))


