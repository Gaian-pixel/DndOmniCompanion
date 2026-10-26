import tkinter as tk
import re
import threading
import urllib.request
import urllib.parse
import json
from common.messagebox import messagebox
from tkinter import ttk, simpledialog, scrolledtext
from common.theme import (
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, BORDER_COLOR,
    TEXT_COLOR, TEXT_MUTED, TEXT_DARK,
    ACCENT_GOLD, ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE,
    FONT_MAIN, FONT_TITLE, FONT_HEADER, FONT_BOLD, FONT_SMALL,
    apply_modern_window_style
)
from common.i18n import (
    _t, get_language, translate_ability, translate_skill,
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

SRD_SUBCLASSES = {
    "barbaro": ["Cammino del Berserker", "Cammino del Combattente Totemico", "Cammino dello Zelota"],
    "barbarian": ["Path of the Berserker", "Path of the Totem Warrior", "Path of the Zealot"],
    "bardo": ["Collegio della Sapienza", "Collegio del Valore", "Collegio delle Spade"],
    "bard": ["College of Lore", "College of Valor", "College of Swords"],
    "chierico": ["Dominio della Vita", "Dominio della Luce", "Dominio della Guerra", "Dominio dell'Inganno", "Dominio della Tempesta"],
    "cleric": ["Life Domain", "Light Domain", "War Domain", "Trickery Domain", "Tempest Domain"],
    "druido": ["Circolo della Terra", "Circolo della Luna", "Circolo delle Spore"],
    "druid": ["Circle of the Land", "Circle of the Moon", "Circle of Spores"],
    "guerriero": ["Campione", "Maestro di Battaglia", "Cavaliere Mistico", "Arciere Arcano"],
    "fighter": ["Champion", "Battle Master", "Eldritch Knight", "Arcane Archer"],
    "monaco": ["Via della Mano Aperta", "Via dell'Ombra", "Via dei Quattro Elementi", "Via del Kensei"],
    "monk": ["Way of the Open Hand", "Way of Shadow", "Way of the Four Elements", "Way of the Kensei"],
    "paladino": ["Giuramento di Devozione", "Giuramento degli Antichi", "Giuramento di Vendetta", "Giuramento di Conquista"],
    "paladin": ["Oath of Devotion", "Oath of the Ancients", "Oath of Vengeance", "Oath of Conquest"],
    "ranger": ["Cacciatore", "Signore delle Bestie", "Giramondo dell'Orizzonte"],
    "ladro": ["Assassino", "Furfante", "Mistico Mistificatore", "Spadaccino"],
    "rogue": ["Assassin", "Thief", "Arcane Trickster", "Swashbuckler"],
    "stregone": ["Stirpe Draconica", "Magia Selvaggia", "Anima Favorevole"],
    "sorcerer": ["Draconic Bloodline", "Wild Magic", "Divine Soul"],
    "warlock": ["Il Signore Immondo", "Il Grande Antico", "La Fatata", "La Lama del Patto"],
    "mago": ["Scuola di Invocazione", "Scuola di Abiurazione", "Scuola di Divinazione", "Scuola di Necromanzia", "Scuola di Trasmutazione", "Scuola di Illusione", "Scuola di Incantamento", "Scuola di Evocazione"],
    "wizard": ["School of Evocation", "School of Abjuration", "School of Divination", "School of Necromancy", "School of Transmutation", "School of Illusion", "School of Enchantment", "School of Conjuration"]
}


def configure_markdown_tags(text_widget):
    """Configura i tag grafici per il rendering Markdown ricco e dark fantasy."""
    text_widget.tag_configure("h1", font=("Segoe UI", 13, "bold"), foreground=ACCENT_GOLD, spacing1=8, spacing3=4)
    text_widget.tag_configure("h2", font=("Segoe UI", 11, "bold"), foreground=ACCENT_GOLD, spacing1=6, spacing3=3)
    text_widget.tag_configure("h3", font=("Segoe UI", 10, "bold"), foreground="#F1C40F", spacing1=5, spacing3=2)
    text_widget.tag_configure("h4", font=("Segoe UI", 9, "bold"), foreground="#5DADE2", spacing1=4, spacing3=2)
    text_widget.tag_configure("bold", font=("Segoe UI", 9, "bold"), foreground="#FFFFFF")
    text_widget.tag_configure("italic", font=("Segoe UI", 9, "italic"), foreground="#D0D0D0")
    text_widget.tag_configure("bullet_symbol", font=("Segoe UI", 9, "bold"), foreground=ACCENT_GOLD, lmargin1=16, lmargin2=28)
    text_widget.tag_configure("bullet_line", font=("Segoe UI", 9), foreground=TEXT_COLOR, lmargin1=16, lmargin2=28, spacing1=2, spacing3=2)
    text_widget.tag_configure("normal", font=("Segoe UI", 9), foreground=TEXT_COLOR, spacing1=2, spacing3=2)
    text_widget.tag_configure("quote", font=("Segoe UI", 9, "italic"), foreground=TEXT_MUTED, lmargin1=20, lmargin2=20, spacing1=2, spacing3=2)

def render_markdown_to_widget(text_widget, markdown_text: str):
    """Parsa e inserisce testo formattato Markdown in uno ScrolledText/Text."""
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)
    if not markdown_text:
        text_widget.config(state="disabled")
        return

    def _insert_inline(txt, base_tags=("normal",)):
        tokens = re.split(r'(\*\*.*?\*\*|\*.*?\*)', txt)
        for tok in tokens:
            if not tok: continue
            if tok.startswith("**") and tok.endswith("**") and len(tok) >= 4:
                text_widget.insert(tk.END, tok[2:-2], ("bold",) + base_tags)
            elif tok.startswith("*") and tok.endswith("*") and len(tok) >= 2:
                text_widget.insert(tk.END, tok[1:-1], ("italic",) + base_tags)
            else:
                text_widget.insert(tk.END, tok, base_tags)

    lines = markdown_text.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            text_widget.insert(tk.END, "\n", ("normal",))
            continue
        if stripped.startswith("#### "):
            text_widget.insert(tk.END, stripped[5:] + "\n", ("h4",))
        elif stripped.startswith("### "):
            text_widget.insert(tk.END, stripped[4:] + "\n", ("h3",))
        elif stripped.startswith("## "):
            text_widget.insert(tk.END, stripped[3:] + "\n", ("h2",))
        elif stripped.startswith("# "):
            text_widget.insert(tk.END, stripped[2:] + "\n", ("h1",))
        elif stripped.startswith("> "):
            text_widget.insert(tk.END, stripped[2:] + "\n", ("quote",))
        elif stripped.startswith("• ") or stripped.startswith("- "):
            bullet_body = stripped[2:]
            text_widget.insert(tk.END, "  • ", ("bullet_symbol",))
            _insert_inline(bullet_body, base_tags=("bullet_line",))
            text_widget.insert(tk.END, "\n", ("bullet_line",))
        else:
            _insert_inline(line, base_tags=("normal",))
            text_widget.insert(tk.END, "\n", ("normal",))

    text_widget.config(state="disabled")

def parse_features_text(raw_text: str):
    """Estrae categorie e tratti strutturati da un testo libero con sezioni standard D&D."""
    if not raw_text or not raw_text.strip():
        return []
    items = []
    current_cat = "Altro"
    current_title = ""
    current_body = []
    
    for line in raw_text.splitlines():
        s = line.strip()
        if not s:
            if current_body:
                current_body.append("")
            continue
        s_lower = s.lower()
        if s_lower.startswith("tratti razziali") or "tratti razziali:" in s_lower:
            if current_title:
                items.append({"name": current_title, "category": current_cat, "desc": "\n".join(current_body).strip()})
                current_body = []
            current_cat = "Tratto Razziale"
            current_title = "Tratti Razziali"
        elif s_lower.startswith("tratti classe") or "tratti classe:" in s_lower:
            if current_title:
                items.append({"name": current_title, "category": current_cat, "desc": "\n".join(current_body).strip()})
                current_body = []
            current_cat = "Privilegio di Classe"
            current_title = "Tratti di Classe Base"
        elif "privilegio di background" in s_lower or s_lower.startswith("background:"):
            if current_title:
                items.append({"name": current_title, "category": current_cat, "desc": "\n".join(current_body).strip()})
                current_body = []
            current_cat = "Tratto di Background"
            m = re.search(r'\((.*?)\)', s)
            current_title = f"Background: {m.group(1)}" if m else "Privilegio di Background"
        elif s.startswith("---") and "---" in s[3:]:
            if current_title:
                items.append({"name": current_title, "category": current_cat, "desc": "\n".join(current_body).strip()})
                current_body = []
            current_cat = "Privilegio di Classe"
            clean_hdr = s.replace("-", "").strip()
            current_title = clean_hdr or "Privilegi di Livello"
        elif s.startswith("- ") and current_cat == "Privilegio di Classe" and "livello" in current_title.lower():
            ft_name = s[2:].strip()
            items.append({"name": ft_name, "category": "Privilegio di Classe", "desc": f"Privilegio di classe: {ft_name}"})
        elif s.startswith("=== ") and s.endswith(" ==="):
            if current_title:
                items.append({"name": current_title, "category": current_cat, "desc": "\n".join(current_body).strip()})
                current_body = []
            clean_cat = s[4:-4].strip().title()
            current_cat = clean_cat
            current_title = ""
        elif s.startswith("★ "):
            if current_title:
                items.append({"name": current_title, "category": current_cat, "desc": "\n".join(current_body).strip()})
                current_body = []
            current_title = s[2:].strip()
        else:
            if not current_title:
                current_title = s[:30]
            current_body.append(line)
            
    if current_title and current_body:
        items.append({"name": current_title, "category": current_cat, "desc": "\n".join(current_body).strip()})
        
    return items

def serialize_features_list(features_list):
    """Rigenera il testo leggibile di features mantenendo la compatibilità con export e schede."""
    if not features_list:
        return ""
    grouped = {}
    for feat in features_list:
        cat = feat.get("category", "Altro")
        grouped.setdefault(cat, []).append(feat)
        
    lines = []
    order = ["Tratto Razziale", "Privilegio di Classe", "Tratto di Background", "Talento", "Altro"]
    
    for cat in order:
        items = grouped.get(cat, [])
        if not items: continue
        if cat == "Tratto Razziale":
            lines.append("=== TRATTI RAZZIALI ===")
        elif cat == "Privilegio di Classe":
            lines.append("=== PRIVILEGI DI CLASSE ===")
        elif cat == "Tratto di Background":
            lines.append("=== TRATTI DI BACKGROUND ===")
        elif cat == "Talento":
            lines.append("=== TALENTI & DONI ===")
        else:
            lines.append("=== ALTRI TRATTI E CAPACITÀ ===")
            
        for item in items:
            name = item.get("name", "Tratto")
            desc = item.get("desc", "").strip()
            lines.append(f"★ {name}")
            if desc:
                lines.append(desc)
            lines.append("")
            
    for cat, items in grouped.items():
        if cat not in order and items:
            lines.append(f"=== {cat.upper()} ===")
            for item in items:
                lines.append(f"★ {item.get('name', 'Tratto')}")
                if item.get("desc"): lines.append(item.get("desc").strip())
                lines.append("")
                
    return "\n".join(lines).strip()


class FeatureEditorDialog(tk.Toplevel):
    def __init__(self, parent, item=None, on_save_callback=None):
        super().__init__(parent)
        self.item = item or {}
        self.on_save_callback = on_save_callback
        is_edit = bool(item)
        self.title("Modifica Tratto / Privilegio" if is_edit else "Nuovo Tratto o Privilegio")
        self.geometry("520x460")
        self.minsize(440, 380)
        self.transient(parent)
        self.grab_set()
        apply_modern_window_style(self)
        
        body = ttk.Frame(self, padding="14")
        body.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(body, text="★ Modifica Tratto o Privilegio" if is_edit else "★ Aggiungi Tratto o Privilegio", font=FONT_BOLD).pack(anchor="w", pady=(0, 10))
        
        ttk.Label(body, text="Nome:", style="Muted.TLabel").pack(anchor="w", pady=(2, 1))
        self.name_var = tk.StringVar(value=self.item.get("name", ""))
        self.name_entry = ttk.Entry(body, textvariable=self.name_var)
        self.name_entry.pack(fill=tk.X, pady=(0, 8))
        self.name_entry.focus_set()
        
        ttk.Label(body, text="Categoria:", style="Muted.TLabel").pack(anchor="w", pady=(2, 1))
        self.cat_var = tk.StringVar(value=self.item.get("category", "Privilegio di Classe"))
        cats = ["Privilegio di Classe", "Tratto Razziale", "Tratto di Background", "Talento", "Altro"]
        self.cat_combo = ttk.Combobox(body, textvariable=self.cat_var, values=cats, state="readonly")
        self.cat_combo.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(body, text="Descrizione & Dettagli:", style="Muted.TLabel").pack(anchor="w", pady=(2, 1))
        self.desc_text = scrolledtext.ScrolledText(body, wrap=tk.WORD, font=FONT_MAIN, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, padx=6, pady=6)
        self.desc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        self.desc_text.insert("1.0", self.item.get("desc", ""))
        
        btn_box = ttk.Frame(body)
        btn_box.pack(fill=tk.X)
        
        def save_and_close():
            nm = self.name_var.get().strip()
            if not nm:
                messagebox.showwarning("Nome Mancante", "Inserisci un nome per il tratto o privilegio.", parent=self)
                return
            cat = self.cat_var.get().strip() or "Altro"
            desc = self.desc_text.get("1.0", tk.END).strip()
            result = {"name": nm, "category": cat, "desc": desc}
            if self.on_save_callback:
                self.on_save_callback(result)
            self.destroy()
            
        ttk.Button(btn_box, text="💾 Salva", command=save_and_close, style="Success.TButton").pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_box, text="Annulla", command=self.destroy).pack(side=tk.RIGHT, padx=4)


class CharacterSheetFrame(ttk.Frame):
    def __init__(self, master, character, manager, on_save_callback=None, roll_callback=None, trade_callback=None, give_gold_callback=None, players_list_callback=None, attack_callback=None, long_rest_callback=None, custom_spell_request_callback=None, request_currency_callback=None, request_item_callback=None, is_connected=False, request_journal_approval_callback=None, on_close_callback=None, on_detach_callback=None, on_dock_callback=None, is_overlay=False, network=None, **kwargs):
        super().__init__(master, **kwargs)
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
        self.network = network
        self.default_font = ("Georgia", 10)
        self.initial_currency = {}
        self.request_journal_approval_callback = request_journal_approval_callback
        self._suppress_weight_sync = True
        self._initial_text_fields = {}
        self._initial_state_snapshot = None
        self._markdown_widgets = {}
        self.current_container_filter = "all"
        self.inventory_row_frames = []
        self.container_quick_buttons = []
        self.spend_buttons = []
        self.container_filter_btns = {}
        self.on_close_callback = on_close_callback
        self.on_detach_callback = on_detach_callback
        self.on_dock_callback = on_dock_callback
        self.is_overlay = is_overlay
        
        self.setup_ui()
        self.load_data()

    def _capture_initial_state(self):
        import copy
        self._initial_state_snapshot = {
            "name": getattr(self.character, "name", ""),
            "campaign": getattr(self.character, "campaign", ""),
            "char_class": getattr(self.character, "char_class", ""),
            "level": getattr(self.character, "level", 1),
            "race": getattr(self.character, "race", ""),
            "subclass": getattr(self.character, "subclass", ""),
            "background": getattr(self.character, "background", ""),
            "alignment": getattr(self.character, "alignment", ""),
            "attributes": copy.deepcopy(getattr(self.character, "attributes", {})),
            "skills": copy.deepcopy(getattr(self.character, "skills", {})),
            "hp_current": getattr(self.character, "hp_current", 10),
            "hp_max": getattr(self.character, "hp_max", 10),
            "ac": getattr(self.character, "ac", 10),
            "initiative": getattr(self.character, "initiative", 0),
            "speed": getattr(self.character, "speed", 30),
            "speed_unit": getattr(self.character, "speed_unit", "ft"),
            "currency": copy.deepcopy(getattr(self.character, "currency", {})),
            "spell_slots": copy.deepcopy(getattr(self.character, "spell_slots", {})),
        }

    def cancel_sheet(self):
        import copy
        if self._initial_state_snapshot and hasattr(self, "character") and self.character:
            for k, v in self._initial_state_snapshot.items():
                setattr(self.character, k, copy.deepcopy(v))
        self.close_sheet()

    def close_sheet(self):
        if self.on_close_callback:
            self.on_close_callback()
        else:
            self.destroy()

    def setup_ui(self):
        # Banner di controllo overlay/docking se overlay o con callback
        if self.is_overlay or self.on_detach_callback or self.on_dock_callback:
            overlay_header = tk.Frame(self, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=5)
            overlay_header.pack(fill=tk.X, padx=10, pady=(6, 2))

            tk.Label(
                overlay_header,
                text=f"📜 {_t('sheet_title')} • {self.character.name} (Livello {self.character.level} {self.character.char_class})",
                font=FONT_BOLD,
                bg=SURFACE_COLOR,
                fg=ACCENT_GOLD
            ).pack(side=tk.LEFT)

            if self.on_close_callback:
                btn_close = ttk.Button(overlay_header, text="✕ Chiudi (Esc)", command=self.cancel_sheet, style="Danger.TButton")
                btn_close.pack(side=tk.RIGHT, padx=(4, 0))
                ToolTip(btn_close, "Chiudi la vista scheda e torna alla mappa (Esc)")

            if self.on_detach_callback:
                btn_detach = ttk.Button(overlay_header, text="◱ Stacca Finestra", command=self.on_detach_callback, style="Tool.TButton")
                btn_detach.pack(side=tk.RIGHT, padx=(4, 0))
                ToolTip(btn_detach, "Apri la scheda in una finestra separata indipendente")

            if self.on_dock_callback:
                btn_dock = ttk.Button(overlay_header, text="◰ Riaggancia alla Mappa", command=self.on_dock_callback, style="Gold.TButton")
                btn_dock.pack(side=tk.RIGHT, padx=(4, 0))
                ToolTip(btn_dock, "Riaggancia la scheda all'interno della finestra principale del VTT")

            btn_quick_save = ttk.Button(overlay_header, text="💾 Salva (Ctrl+S)", command=self.save_character, style="Success.TButton")
            btn_quick_save.pack(side=tk.RIGHT, padx=(4, 0))
            ToolTip(btn_quick_save, "Salva le modifiche e chiudi la vista (Ctrl+S)")

        main_frame = ttk.Frame(self, padding=8)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Intestazione (Dark Fantasy Card Responsiva)
        header_frame = tk.Frame(main_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=8)
        header_frame.pack(fill=tk.X, pady=(0, 8))
        header_frame.columnconfigure(2, weight=1)
        header_frame.columnconfigure(4, weight=1)
        header_frame.columnconfigure(7, weight=1)

        # Riquadro Avatar / Token Personaggio
        avatar_frame = tk.Frame(header_frame, bg=SURFACE_COLOR)
        avatar_frame.grid(row=0, column=0, rowspan=4, padx=(0, 12), sticky="n")

        self.avatar_canvas = tk.Canvas(avatar_frame, width=64, height=64, bg="#181A20", highlightthickness=0, cursor="hand2")
        self.avatar_canvas.pack(pady=(0, 2))
        self.avatar_canvas.bind("<Button-1>", lambda e: self._on_avatar_clicked())
        self.avatar_canvas.bind("<Button-3>", self._on_avatar_right_click)
        ToolTip(self.avatar_canvas, "Clicca per caricare o modificare l'immagine del token sulla mappa")

        self.btn_edit_avatar = tk.Button(
            avatar_frame, text="📷 Token", font=("Segoe UI", 8),
            bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, activebackground=SURFACE_COLOR,
            relief=tk.FLAT, bd=0, padx=4, pady=1, command=self._on_avatar_clicked
        )
        self.btn_edit_avatar.pack()

        tk.Label(header_frame, text=_t("sheet_name"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).grid(row=0, column=1, sticky="e", padx=(0, 4))
        self.name_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.name_var, width=16).grid(row=0, column=2, padx=4, pady=3, sticky="ew")

        tk.Label(header_frame, text=_t("sheet_campaign"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=0, column=3, sticky="e", padx=(8, 4))
        self.campaign_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.campaign_var, width=14).grid(row=0, column=4, padx=4, pady=3, sticky="ew")

        self.levelup_btn = ttk.Button(header_frame, text=_t("sheet_levelup_btn"), command=self.level_up, style="Gold.TButton")
        self.levelup_btn.grid(row=0, column=5, columnspan=3, padx=(10, 0), pady=3, sticky="ew")

        tk.Label(header_frame, text=_t("sheet_class"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=1, column=1, sticky="e", padx=(0, 4))
        self.class_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.class_var, width=16).grid(row=1, column=2, padx=4, pady=3, sticky="ew")

        tk.Label(header_frame, text=_t("sheet_level"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=1, column=3, sticky="e", padx=(8, 4))
        self.level_var = tk.IntVar()
        self.level_var.trace_add("write", lambda *args: self.update_skill_modifiers() if hasattr(self, "update_skill_modifiers") else None)
        ttk.Entry(header_frame, textvariable=self.level_var, width=4, state="readonly", justify="center").grid(row=1, column=4, padx=4, pady=3, sticky="w")
        
        tk.Label(header_frame, text=_t("sheet_exp"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=1, column=5, sticky="e", padx=(8, 4))
        self.exp_label = tk.Label(header_frame, text="0 / 300", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_COLOR)
        self.exp_label.grid(row=1, column=6, padx=4, pady=3, sticky="w")
        self.exp_progress = ttk.Progressbar(header_frame, length=90, mode='determinate')
        self.exp_progress.grid(row=1, column=7, padx=4, pady=3, sticky="w")

        tk.Label(header_frame, text=_t("sheet_race"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=2, column=1, sticky="e", padx=(0, 4))
        self.race_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.race_var, width=16).grid(row=2, column=2, padx=4, pady=3, sticky="ew")

        tk.Label(header_frame, text="Sottoclasse:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=2, column=3, sticky="e", padx=(8, 4))
        self.subclass_var = tk.StringVar()
        self.subclass_combo = ttk.Combobox(header_frame, textvariable=self.subclass_var, width=14)
        self.subclass_combo.grid(row=2, column=4, padx=4, pady=3, sticky="ew")
        ToolTip(self.subclass_combo, "Sottoclasse / Archetipo D&D 5e (Seleziona dalla lista SRD o digita il tuo archetipo)")

        self.btn_inspiration = tk.Button(
            header_frame, text=_t("insp_none"), font=("Segoe UI", 9, "bold"),
            bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, activebackground=SURFACE_COLOR,
            relief=tk.FLAT, bd=0, padx=8, pady=2, command=self.on_inspiration_clicked
        )
        self.btn_inspiration.grid(row=2, column=5, columnspan=3, padx=(8, 0), pady=3, sticky="ew")

        tk.Label(header_frame, text="Background:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=3, column=1, sticky="e", padx=(0, 4))
        self.background_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.background_var, width=16).grid(row=3, column=2, padx=4, pady=3, sticky="ew")

        tk.Label(header_frame, text="Allineamento:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).grid(row=3, column=3, sticky="e", padx=(8, 4))
        self.alignment_var = tk.StringVar()
        ttk.Entry(header_frame, textvariable=self.alignment_var, width=14).grid(row=3, column=4, padx=4, pady=3, sticky="ew")

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
        self.hp_cur_entry = ttk.Entry(hp_inputs, textvariable=self.hp_cur_var, width=4, justify="center")
        if self.is_connected:
            self.hp_cur_entry.configure(state="readonly")
            ToolTip(self.hp_cur_entry, lambda: _t("msg_hp_cur_locked_online"))
        self.hp_cur_entry.pack(side=tk.LEFT)
        tk.Label(hp_inputs, text="/", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=3)
        self.hp_max_var = tk.IntVar()
        self.hp_max_entry = ttk.Entry(hp_inputs, textvariable=self.hp_max_var, width=4, justify="center")
        if self.is_connected:
            self.hp_max_entry.configure(state="readonly")
            ToolTip(self.hp_max_entry, lambda: _t("msg_hp_max_locked_online"))
        self.hp_max_entry.pack(side=tk.LEFT)
        
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
            elif attr == "notes":
                self.create_notes_tab(frame)
            else:
                txt = tk.Text(frame, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=self.default_font, wrap=tk.WORD)
                txt.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
                self.text_widgets[attr] = txt

        if "FOR" in self.attr_vars:
            self.attr_vars["FOR"].trace_add("write", lambda *args: self.calculate_total_weight())

        # Barra Azioni Inferiore Strutturata
        btn_frame = tk.Frame(main_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=6)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))
        
        ttk.Button(btn_frame, text="📥 Esporta PDF / JSON...", command=self.export_character_dialog, style="Info.TButton").pack(side=tk.LEFT)
        
        save_btn = ttk.Button(btn_frame, text=f"💾 {_t('save')} (Ctrl+S)", command=self.save_character, style="Gold.TButton")
        save_btn.pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_frame, text=f"✕ {_t('cancel')}", command=self.cancel_sheet, style="Dark.TButton").pack(side=tk.RIGHT)
        self.bind("<Control-s>", self.save_character)
        self.bind("<Control-S>", self.save_character)
        try:
            top_win = self.winfo_toplevel()
            def _on_ctrl_s(event=None):
                if self.winfo_exists() and self.winfo_viewable():
                    self.save_character()
            top_win.bind("<Control-s>", _on_ctrl_s, add="+")
            top_win.bind("<Control-S>", _on_ctrl_s, add="+")
        except Exception:
            pass

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
        
        # 2. Box Privilegi e Tratti di Classe (Strutturato con Categorie e Preview)
        ft_card = tk.Frame(parent_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=6)
        ft_card.pack(fill=tk.BOTH, expand=True, padx=4, pady=(2, 4))
        
        ft_toolbar = tk.Frame(ft_card, bg=SURFACE_COLOR)
        ft_toolbar.pack(fill=tk.X, pady=(0, 6))
        
        tk.Label(ft_toolbar, text="📜 Privilegi di Classe, Tratti Razziali e Talenti", font=FONT_BOLD, fg=ACCENT_GOLD, bg=SURFACE_COLOR).pack(side=tk.LEFT)
        
        btn_box = tk.Frame(ft_toolbar, bg=SURFACE_COLOR)
        btn_box.pack(side=tk.RIGHT)
        
        if self.is_connected:
            self.btn_prop_features = ttk.Button(btn_box, text="📤 Proponi al Master", command=self.propose_features_approval, style="Gold.TButton")
            self.btn_prop_features.pack(side=tk.RIGHT, padx=3)
            
        self.btn_view_features = ttk.Button(btn_box, text="👁️ Vista Testo", command=self.toggle_features_view_mode)
        self.btn_view_features.pack(side=tk.RIGHT, padx=3)
        
        self.btn_del_feature = ttk.Button(btn_box, text="🗑️ Elimina", command=self.delete_selected_feature, style="Danger.TButton")
        self.btn_del_feature.pack(side=tk.RIGHT, padx=3)
        
        self.btn_edit_feature = ttk.Button(btn_box, text="✏️ Modifica", command=self.open_edit_feature_dialog)
        self.btn_edit_feature.pack(side=tk.RIGHT, padx=3)
        
        self.btn_add_feature = ttk.Button(btn_box, text="➕ Aggiungi Tratto", command=self.open_add_feature_dialog, style="Success.TButton")
        self.btn_add_feature.pack(side=tk.RIGHT, padx=3)
        
        self.features_main_container = tk.Frame(ft_card, bg=SURFACE_COLOR)
        self.features_main_container.pack(fill=tk.BOTH, expand=True)
        
        # 2a. Vista Strutturata (Treeview a sinistra, Dettaglio a destra)
        self.features_paned = ttk.PanedWindow(self.features_main_container, orient=tk.HORIZONTAL)
        self.features_paned.pack(fill=tk.BOTH, expand=True)
        
        tree_frame = ttk.Frame(self.features_paned, padding=2)
        self.features_paned.add(tree_frame, weight=1)
        
        self.features_tree = ttk.Treeview(tree_frame, selectmode="browse", show="tree")
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.features_tree.yview)
        self.features_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.features_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.features_tree.bind("<<TreeviewSelect>>", self._on_feature_tree_selected)
        
        detail_frame = tk.Frame(self.features_paned, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=8)
        self.features_paned.add(detail_frame, weight=2)
        
        self.feat_detail_title = tk.Label(detail_frame, text="Seleziona un tratto o privilegio", font=("Segoe UI", 11, "bold"), fg=ACCENT_GOLD, bg=SURFACE_COLOR_ALT, anchor="w")
        self.feat_detail_title.pack(fill=tk.X, pady=(0, 2))
        
        self.feat_detail_badge = tk.Label(detail_frame, text="", font=FONT_SMALL, fg="#5DADE2", bg=SURFACE_COLOR_ALT, anchor="w")
        self.feat_detail_badge.pack(fill=tk.X, pady=(0, 6))
        
        self.feat_detail_desc = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD, font=FONT_MAIN, bg=SURFACE_COLOR, fg=TEXT_COLOR, padx=6, pady=6)
        self.feat_detail_desc.pack(fill=tk.BOTH, expand=True)
        configure_markdown_tags(self.feat_detail_desc)
        self.feat_detail_desc.config(state="disabled")
        
        # 2b. Vista Testo Libero
        self.features_text_frame = tk.Frame(self.features_main_container, bg=SURFACE_COLOR)
        txt = tk.Text(self.features_text_frame, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=self.default_font, wrap=tk.WORD, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=6)
        txt.pack(fill=tk.BOTH, expand=True)
        self.text_widgets["features"] = txt
        
        self._features_view_mode = "structured"

    def refresh_features_ui(self):
        if not hasattr(self, 'features_tree') or not self.features_tree.winfo_exists():
            return
            
        for it in self.features_tree.get_children():
            self.features_tree.delete(it)
            
        flist = getattr(self.character, "features_list", None)
        if flist is None:
            raw_f = getattr(self.character, "features", "")
            flist = parse_features_text(raw_f)
            self.character.features_list = flist
            
        cat_labels = {
            "Privilegio di Classe": "🛡️ Privilegi di Classe",
            "Tratto Razziale": "🧬 Tratti Razziali",
            "Tratto di Background": "📜 Tratti di Background",
            "Talento": "⚡ Talenti & Doni",
            "Altro": "🔮 Altri Tratti e Capacità"
        }
        
        cat_nodes = {}
        for cat_key, cat_label in cat_labels.items():
            cat_nodes[cat_key] = self.features_tree.insert("", tk.END, text=cat_label, open=True)
            
        for idx, feat in enumerate(flist):
            nm = feat.get("name", "Tratto")
            cat = feat.get("category", "Altro")
            parent_node = cat_nodes.get(cat, cat_nodes["Altro"])
            self.features_tree.insert(parent_node, tk.END, iid=f"feat_{idx}", text=f"  ★ {nm}")
            
        serialized = serialize_features_list(flist)
        self.character.features = serialized
        if "features" in self.text_widgets:
            txt = self.text_widgets["features"]
            txt.config(state="normal")
            txt.delete("1.0", tk.END)
            txt.insert("1.0", serialized)

    def _on_feature_tree_selected(self, event=None):
        sel = self.features_tree.selection()
        if not sel: return
        node_id = sel[0]
        if not node_id.startswith("feat_"):
            return
        idx = int(node_id.replace("feat_", ""))
        flist = getattr(self.character, "features_list", [])
        if 0 <= idx < len(flist):
            feat = flist[idx]
            nm = feat.get("name", "")
            cat = feat.get("category", "")
            desc = feat.get("desc", "")
            
            self.feat_detail_title.config(text=f"★ {nm}")
            self.feat_detail_badge.config(text=f"[{cat}]")
            render_markdown_to_widget(self.feat_detail_desc, desc)

    def open_add_feature_dialog(self):
        def _on_save(new_item):
            if not hasattr(self.character, "features_list") or not isinstance(self.character.features_list, list):
                self.character.features_list = []
            self.character.features_list.append(new_item)
            self.refresh_features_ui()
            self.manager.save_characters()
            if self.is_connected and self.request_journal_approval_callback:
                if messagebox.askyesno("Approvazione Master", f"Hai aggiunto '{new_item.get('name')}'.\n\nVuoi inviare la richiesta di approvazione al Dungeon Master?", parent=self):
                    self.request_journal_approval_callback("features", self.character.features, f"Aggiunto {new_item.get('name')}")
        FeatureEditorDialog(self, on_save_callback=_on_save)

    def open_edit_feature_dialog(self):
        sel = self.features_tree.selection()
        if not sel or not sel[0].startswith("feat_"):
            messagebox.showinfo("Seleziona", "Seleziona prima un tratto dall'elenco a sinistra da modificare.", parent=self)
            return
        idx = int(sel[0].replace("feat_", ""))
        flist = getattr(self.character, "features_list", [])
        if 0 <= idx < len(flist):
            def _on_save(updated_item):
                flist[idx] = updated_item
                self.refresh_features_ui()
                self.manager.save_characters()
                if self.is_connected and self.request_journal_approval_callback:
                    if messagebox.askyesno("Approvazione Master", f"Hai modificato '{updated_item.get('name')}'.\n\nVuoi inviare la richiesta di approvazione al Master?", parent=self):
                        self.request_journal_approval_callback("features", self.character.features, f"Modificato {updated_item.get('name')}")
            FeatureEditorDialog(self, item=flist[idx], on_save_callback=_on_save)

    def delete_selected_feature(self):
        sel = self.features_tree.selection()
        if not sel or not sel[0].startswith("feat_"):
            messagebox.showinfo("Seleziona", "Seleziona prima un tratto dall'elenco a sinistra da eliminare.", parent=self)
            return
        idx = int(sel[0].replace("feat_", ""))
        flist = getattr(self.character, "features_list", [])
        if 0 <= idx < len(flist):
            nm = flist[idx].get("name", "questo tratto")
            if messagebox.askyesno("Elimina", f"Sei sicuro di voler eliminare '{nm}'?", parent=self):
                flist.pop(idx)
                self.refresh_features_ui()
                self.manager.save_characters()
                if self.is_connected and self.request_journal_approval_callback:
                    if messagebox.askyesno("Approvazione Master", f"Hai rimosso '{nm}'.\n\nVuoi notificare il Dungeon Master?", parent=self):
                        self.request_journal_approval_callback("features", self.character.features, f"Rimosso {nm}")

    def toggle_features_view_mode(self):
        if self._features_view_mode == "structured":
            self.features_paned.pack_forget()
            self.features_text_frame.pack(fill=tk.BOTH, expand=True)
            self._features_view_mode = "text"
            self.btn_view_features.config(text="👁️ Vista Categorie")
            self.btn_add_feature.pack_forget()
            self.btn_edit_feature.pack_forget()
            self.btn_del_feature.pack_forget()
        else:
            raw_text = self.text_widgets["features"].get("1.0", tk.END).strip()
            self.character.features_list = parse_features_text(raw_text)
            self.features_text_frame.pack_forget()
            self.features_paned.pack(fill=tk.BOTH, expand=True)
            self._features_view_mode = "structured"
            self.btn_view_features.config(text="👁️ Vista Testo")
            self.btn_add_feature.pack(side=tk.RIGHT, padx=3)
            self.btn_edit_feature.pack(side=tk.RIGHT, padx=3)
            self.btn_del_feature.pack(side=tk.RIGHT, padx=3)
            self.refresh_features_ui()

    def propose_features_approval(self):
        if not self.is_connected:
            messagebox.showinfo("Offline", "Questa funzione è attiva solo durante una sessione di gioco connessa al Master.", parent=self)
            return
        if self._features_view_mode == "text":
            content = self.text_widgets["features"].get("1.0", tk.END).strip()
        else:
            content = serialize_features_list(getattr(self.character, "features_list", []))
            
        if self.request_journal_approval_callback:
            sent = self.request_journal_approval_callback("features", content, "Aggiornamento Privilegi e Tratti")
            if sent:
                messagebox.showinfo("Richiesta Inviata", "La proposta di aggiornamento per 'Privilegi & Tratti' è stata inviata al Master.\nRiceverai una notifica quando il Master la approverà.", parent=self)

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

        # 2. Toolbar & Status Bar (Zaino & Sintonia)
        inv_bar = tk.Frame(parent_frame, bg=BG_COLOR)
        inv_bar.pack(fill=tk.X, padx=6, pady=(4, 2))
        
        tk.Label(inv_bar, text=f"🎒 {_t('sheet_tab_inventory')} (25 Slot)", font=FONT_BOLD, fg=ACCENT_GOLD, bg=BG_COLOR).pack(side=tk.LEFT)
        
        self.btn_drop_backpack = ttk.Button(inv_bar, text=_t("btn_drop_backpack"), command=self.toggle_drop_backpack, style="Slot.TButton")
        self.btn_drop_backpack.pack(side=tk.LEFT, padx=(8, 4))
        ToolTip(self.btn_drop_backpack, "Sfila lo zaino e lascialo a terra come Interazione con Oggetto Gratuita (PHB p. 190). Esclude il peso dello zaino dal carico trasportato.")
        
        self.lbl_backpack_status = tk.Label(inv_bar, text=_t("status_backpack_worn"), font=FONT_SMALL, fg=ACCENT_GREEN, bg=BG_COLOR)
        self.lbl_backpack_status.pack(side=tk.LEFT, padx=4)
        
        self.attunement_label = tk.Label(inv_bar, text=_t("sheet_attunement_count", count=0), font=FONT_BOLD, fg=ACCENT_BLUE, bg=BG_COLOR)
        self.attunement_label.pack(side=tk.RIGHT, padx=4)
        ToolTip(self.attunement_label, "Oggetti Magici Sintonizzati (Regola 5e: Massimo 3 oggetti attivi contemporaneamente)")

        self.lbl_attunement_status = tk.Label(inv_bar, text="", font=FONT_SMALL, fg=ACCENT_GOLD, bg=BG_COLOR)
        self.lbl_attunement_status.pack(side=tk.RIGHT, padx=6)

        # 2b. Barra Filtro e Gestione Contenitori (Zaino, Addosso, Borsa Conservante, ecc.)
        self.container_filter_bar = tk.Frame(parent_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=4)
        self.container_filter_bar.pack(fill=tk.X, padx=6, pady=(2, 4))
        
        c_filter_top = tk.Frame(self.container_filter_bar, bg=SURFACE_COLOR_ALT)
        c_filter_top.pack(fill=tk.X, pady=(0, 2))
        
        tk.Label(c_filter_top, text="Contenitore:", font=FONT_SMALL, fg=TEXT_MUTED, bg=SURFACE_COLOR_ALT).pack(side=tk.LEFT, padx=(2, 6))
        
        self.container_filter_btns = {}
        filters_def = [
            ("all", "📦 Tutti"),
            ("backpack", "🎒 Zaino"),
            ("equipped", "⚔️ Addosso"),
            ("bag_of_holding", "🔮 Borsa"),
            ("haversack", "✨ Zaino Pratico"),
            ("mount", "🐴 Cavalcatura"),
        ]
        for f_key, f_label in filters_def:
            b = ttk.Button(c_filter_top, text=f_label, command=lambda k=f_key: self.set_container_filter(k), style="Slot.TButton")
            b.pack(side=tk.LEFT, padx=2)
            self.container_filter_btns[f_key] = b
            
        self.container_info_lbl = tk.Label(self.container_filter_bar, text="", font=FONT_SMALL, fg=ACCENT_GOLD, bg=SURFACE_COLOR_ALT)
        self.container_info_lbl.pack(anchor="w", padx=2, pady=(2, 0))

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
        tk.Label(hdr_frame, text="Cont.", font=FONT_BOLD, fg=TEXT_MUTED, bg=SURFACE_COLOR_ALT, width=4).pack(side=tk.LEFT, padx=(2, 2))
        tk.Label(hdr_frame, text=_t("sheet_item"), font=FONT_BOLD, fg=TEXT_MUTED, bg=SURFACE_COLOR_ALT).pack(side=tk.LEFT, padx=6, expand=True, fill=tk.X)
        tk.Label(hdr_frame, text="🔮 " + _t("sheet_attunement"), font=FONT_BOLD, fg=TEXT_MUTED, bg=SURFACE_COLOR_ALT, width=8).pack(side=tk.RIGHT, padx=4)
        tk.Label(hdr_frame, text=_t("sheet_weight_col"), font=FONT_BOLD, fg=TEXT_MUTED, bg=SURFACE_COLOR_ALT, width=10).pack(side=tk.RIGHT, padx=4)
        tk.Label(hdr_frame, text="Spendi", font=FONT_BOLD, fg=TEXT_MUTED, bg=SURFACE_COLOR_ALT, width=5).pack(side=tk.RIGHT, padx=4)

        self.inventory_row_frames = []
        self.inventory_buttons = []
        self.container_quick_buttons = []
        self.spend_buttons = []
        self.weight_vars = []
        self.attuned_vars = []
        
        for i in range(25):
            row_bg = SURFACE_COLOR if (i % 2 == 0) else SURFACE_COLOR_ALT
            row_frame = tk.Frame(scrollable_frame, bg=row_bg, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=2)
            row_frame.pack(fill=tk.X, padx=2, pady=1)
            self.inventory_row_frames.append(row_frame)
            
            # Indice slot #i+1
            lbl_idx = tk.Label(row_frame, text=f"#{i+1:02d}", font=FONT_SMALL, fg=TEXT_MUTED, bg=row_bg, width=3)
            lbl_idx.pack(side=tk.LEFT, padx=(2, 2))
            
            # Bottone Rapido Contenitore (Collocazione)
            btn_c = tk.Button(row_frame, text="🎒", font=("Segoe UI Emoji", 10), relief=tk.FLAT, bd=0, bg=row_bg, fg=TEXT_COLOR, activebackground=BORDER_COLOR, width=3)
            btn_c.pack(side=tk.LEFT, padx=(0, 2))
            btn_c.config(command=lambda idx=i, b=btn_c: self.open_quick_container_picker(idx, b))
            ToolTip(btn_c, "Sposta rapidamente questo oggetto in un altro contenitore (Zaino, Addosso, Borsa Conservante, ecc.)")
            self.container_quick_buttons.append(btn_c)
            
            # Bottone Oggetto
            btn = ttk.Button(row_frame, text=_t("sheet_empty_slot_desc"), command=lambda idx=i: self.on_inventory_click(idx), style="Slot.TButton")
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
            btn.bind("<Button-3>", lambda e, idx=i: self.show_container_context_menu(e, idx))
            row_frame.bind("<Button-3>", lambda e, idx=i: self.show_container_context_menu(e, idx))
            self.inventory_buttons.append(btn)
            
            # Bottone Rapido Spendi / Consuma / Spacchetta
            btn_spend = ttk.Button(row_frame, text="-1", width=4, style="Small.TButton", command=lambda idx=i: self.on_quick_spend_or_open_click(idx))
            btn_spend.pack(side=tk.RIGHT, padx=2)
            self.spend_buttons.append(btn_spend)
            
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
            a_frame.pack(side=tk.RIGHT, padx=4)
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

        self.weight_details_lbl = tk.Label(bottom_frame, text="", font=FONT_SMALL, fg=TEXT_MUTED, bg=SURFACE_COLOR_ALT)
        self.weight_details_lbl.pack(fill=tk.X, pady=(1, 2))
        
        btn_bar = tk.Frame(bottom_frame, bg=SURFACE_COLOR_ALT)
        btn_bar.pack(fill=tk.X, pady=(2, 0))
        
        comp_btn_txt = _t("sheet_search_compendium") if self.is_connected else f"{_t('sheet_search_compendium')} 🔒"
        compendium_btn = ttk.Button(btn_bar, text=comp_btn_txt, command=self.open_inventory_compendium)
        compendium_btn.pack(side=tk.LEFT, padx=2)
        comp_tip = "Cerca un oggetto nel compendio e invia richiesta al DM" if self.is_connected else "L'aggiunta di oggetti richiede l'approvazione del Master in sessione"
        ToolTip(compendium_btn, comp_tip)
        
        custom_btn_txt = _t("sheet_add_custom_item") if self.is_connected else f"{_t('sheet_add_custom_item')} 🔒"
        custom_btn = ttk.Button(btn_bar, text=custom_btn_txt, command=self.open_custom_item_dialog)
        custom_btn.pack(side=tk.LEFT, padx=4)
        custom_tip = "Crea un oggetto personalizzato e invia richiesta al DM" if self.is_connected else "L'aggiunta di oggetti richiede l'approvazione del Master in sessione"
        ToolTip(custom_btn, custom_tip)
        
        btn_give_gold = ttk.Button(btn_bar, text=_t("sheet_give_gold_btn"), command=self.on_give_gold_click, style="Gold.TButton")
        btn_give_gold.pack(side=tk.RIGHT, padx=2)

    def sync_inventory_coins_to_currency(self):
        """
        Rileva le monete presenti come oggetti nella griglia inventario (es. kit iniziali,
        monete d'oro, sacche di monete) e garantisce che vengano riportate
        nella tabella superiore delle valute (character.currency / MR, MA, ME, MO, MP).
        """
        if not hasattr(self.character, "currency") or not isinstance(self.character.currency, dict):
            self.character.currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
            
        for k in ["MR", "MA", "ME", "MO", "MP"]:
            if k not in self.character.currency:
                self.character.currency[k] = 0

        grid = getattr(self.character, "inventory_grid", [])
        if not isinstance(grid, list):
            return

        inv_coins = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
        has_coin_items = False
        
        for it in grid:
            if not it or not isinstance(it, dict):
                continue
            if it.get("_coins_synced"):
                continue
            nm = it.get("name", "").strip().lower()
            itype = str(it.get("type", "")).strip().lower()
            desc = str(it.get("desc", "")).strip().lower()
            
            is_coin = (
                (itype in ["valuta", "currency", "moneta", "monete"])
                or ("monet" in nm)
                or ("borsello" in nm)
                or ("borsa di monete" in nm)
                or ("borsa con monete" in nm)
            )
            if not is_coin:
                continue
                
            full_text = f"{nm} {desc}"
            has_coin_items = True
            
            # 1. Ricerca quantitativi espliciti menzionati nel testo (es. "50 MA e 5 MP")
            found_any_explicit = False
            for c_code, pat in [
                ("MP", r"(\d+)\s*(?:mp|pp|monete d'platino|platino)"),
                ("ME", r"(\d+)\s*(?:me|ep|monete d'electrum|electrum|electro)"),
                ("MA", r"(\d+)\s*(?:ma|sp|monete d'argento|argento)"),
                ("MR", r"(\d+)\s*(?:mr|cp|monete di rame|rame)"),
                ("MO", r"(\d+)\s*(?:mo|gp|monete d'oro|oro)")
            ]:
                m = re.search(pat, full_text, re.IGNORECASE)
                if m:
                    inv_coins[c_code] += int(m.group(1))
                    found_any_explicit = True
                    
            # 2. Se non ci sono pattern espliciti, usa la quantita dell'oggetto e deduci il tipo di moneta
            if not found_any_explicit:
                qty = it.get("qty", 1)
                coin_type = "MO"
                if re.search(r"\b(?:platino|pp)\b", full_text, re.IGNORECASE) or re.search(r"\bmp\b", nm, re.IGNORECASE):
                    coin_type = "MP"
                elif re.search(r"\b(?:electrum|electro|ep)\b", full_text, re.IGNORECASE) or re.search(r"\bme\b", nm, re.IGNORECASE):
                    coin_type = "ME"
                elif re.search(r"\b(?:argento|sp)\b", full_text, re.IGNORECASE) or re.search(r"\bma\b", nm, re.IGNORECASE):
                    coin_type = "MA"
                elif re.search(r"\b(?:rame|cp)\b", full_text, re.IGNORECASE) or re.search(r"\bmr\b", nm, re.IGNORECASE):
                    coin_type = "MR"
                inv_coins[coin_type] += qty
            it["_coins_synced"] = True

        if has_coin_items:
            for c_code, c_amount in inv_coins.items():
                if c_amount > 0 and self.character.currency.get(c_code, 0) < c_amount:
                    self.character.currency[c_code] = c_amount
                    if hasattr(self, "currency_vars") and c_code in self.currency_vars:
                        self.currency_vars[c_code].set(self.character.currency[c_code])
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
        if getattr(self, '_suppress_weight_sync', False):
            return
            
        from common.starter_equipment import lookup_standard_weight
        # Sincronizza i pesi inseriti nella UI sugli oggetti
        for i in range(25):
            if i < len(self.character.inventory_grid):
                item = self.character.inventory_grid[i]
                if item and i < len(self.weight_vars):
                    try:
                        w_val = float(self.weight_vars[i].get())
                        if w_val > 0:
                            item["weight"] = w_val
                        elif not item.get("weight") or float(item.get("weight", 0)) == 0:
                            std_w = lookup_standard_weight(item.get("name", ""))
                            if std_w > 0:
                                item["weight"] = std_w
                                self.weight_vars[i].set(std_w)
                    except (tk.TclError, ValueError):
                        pass

        # Sincronizza le monete per il calcolo del peso
        if hasattr(self, "currency_vars"):
            for coin, var in self.currency_vars.items():
                try:
                    self.character.currency[coin] = int(var.get())
                except (tk.TclError, ValueError):
                    pass

        # Sincronizza FOR se modificata nei campi di testo
        if hasattr(self, "attr_vars") and "FOR" in self.attr_vars:
            try:
                self.character.attributes["FOR"] = int(self.attr_vars["FOR"].get())
            except (tk.TclError, ValueError):
                pass

        enc = self.character.get_encumbrance_status()
        total = enc["carried_weight"]
        max_weight = enc["limit_max"]
        tier = enc["tier"]

        if hasattr(self, 'weight_bar'):
            self.weight_bar['maximum'] = max(1.0, max_weight)
            self.weight_bar['value'] = min(max_weight, total)

        enc_text = {
            "normal": _t("enc_normal"),
            "encumbered": _t("enc_encumbered"),
            "heavily_encumbered": _t("enc_heavily_encumbered"),
            "overloaded": _t("enc_overloaded")
        }.get(tier, _t("enc_normal"))

        self.weight_label.config(
            text=f"{_t('sheet_total_weight', current=f'{total:.1f}', max=f'{max_weight:.1f}')}  [{enc_text}]",
            fg=enc["color"]
        )

        if hasattr(self, 'weight_details_lbl'):
            details = []
            coin_count = sum(self.character.currency.values()) if hasattr(self.character, "currency") else 0
            coin_lbs = round(coin_count / 50.0, 1)
            if coin_lbs > 0:
                details.append(_t("lbl_coins_weight", weight=f"{coin_lbs:.1f}"))
            
            if enc.get("backpack_dropped"):
                details.append(_t("lbl_backpack_ground_weight", weight=f"{enc['backpack_weight']:.1f}"))
                
            if enc.get("boh_weight", 0) > 0:
                details.append(_t("lbl_boh_capacity", cur=f"{enc['boh_weight']:.1f}"))
                
            if enc.get("haversack_weight", 0) > 0:
                details.append(_t("lbl_haversack_capacity", cur=f"{enc['haversack_weight']:.1f}"))
                
            if enc.get("mount_weight", 0) > 0:
                details.append(_t("lbl_mount_capacity", cur=f"{enc['mount_weight']:.1f}"))

            self.weight_details_lbl.config(
                text=" • ".join(details) if details else ""
            )

        if hasattr(self, 'btn_drop_backpack') and hasattr(self, 'lbl_backpack_status'):
            if enc.get("backpack_dropped"):
                self.btn_drop_backpack.config(text=_t("btn_pickup_backpack"), style="Gold.TButton")
                self.lbl_backpack_status.config(text=_t("status_backpack_ground"), fg="#F59E0B")
            else:
                self.btn_drop_backpack.config(text=_t("btn_drop_backpack"), style="Slot.TButton")
                self.lbl_backpack_status.config(text=_t("status_backpack_worn"), fg=ACCENT_GREEN)

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
            return

        if hasattr(self.character, "inventory_grid"):
            for i, var in enumerate(self.attuned_vars):
                if i < len(self.character.inventory_grid) and isinstance(self.character.inventory_grid[i], dict):
                    self.character.inventory_grid[i]["attuned"] = var.get()

        if hasattr(self.character, "get_attunement_bonuses") and hasattr(self, "lbl_attunement_status"):
            b = self.character.get_attunement_bonuses()
            parts = []
            if b.get("bonus_ac", 0) > 0: parts.append(f"+{b['bonus_ac']} CA")
            if b.get("bonus_saves", 0) > 0: parts.append(f"+{b['bonus_saves']} TS")
            for s, v in b.get("set_stats", {}).items(): parts.append(f"{s}={v}")
            if parts:
                self.lbl_attunement_status.config(text=f"🔮 Bonus: {', '.join(parts)}")
            else:
                self.lbl_attunement_status.config(text="")

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
        add_spell_txt = "+ Richiedi Incantesimo" if self.is_connected else "+ Nuovo Incantesimo 🔒"
        btn_new_spell = ttk.Button(btn_frame, text=add_spell_txt, command=self.add_spell)
        btn_new_spell.pack(side=tk.LEFT, padx=5)
        add_spell_tip = "Crea un incantesimo custom e invialo al Master per approvazione" if self.is_connected else "L'aggiunta di incantesimi richiede l'approvazione del Master in sessione"
        ToolTip(btn_new_spell, add_spell_tip)
        srd_btn_txt = "📜 Richiedi Incantesimo (SRD)" if self.is_connected else "📜 Cerca Incantesimo (SRD)"
        srd_btn = ttk.Button(btn_frame, text=srd_btn_txt, command=self.search_spell_srd)
        srd_btn.pack(side=tk.LEFT, padx=5)
        tip_msg = "Cerca un incantesimo da SRD/Manuali e invialo al DM per approvazione" if self.is_connected else "Cerca e aggiungi un incantesimo dall'SRD o dai manuali al Grimorio"
        ToolTip(srd_btn, tip_msg)
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
        if not self.is_connected:
            messagebox.showwarning(
                "Azione Non Consentita",
                "Non puoi aggiungere incantesimi al Grimorio in modalità offline.\n\n"
                "L'apprendimento e l'aggiunta di nuovi incantesimi richiede sempre l'approvazione del Dungeon Master durante una sessione di gioco.",
                parent=self
            )
            return
        SpellEditorDialog(self)

    def remove_spell(self):
        sel = self.spell_tree.selection()
        if not sel: return
        idx = int(sel[0])
        sp = self.character.spellbook[idx]
        s_name = sp.get("name", "questo incantesimo")
        
        if not self.is_connected:
            messagebox.showwarning(
                "Azione Non Consentita",
                f"Non puoi rimuovere '{s_name}' dal Grimorio in modalità offline.\n\n"
                "La rimozione di incantesimi richiede sempre l'approvazione del Dungeon Master durante una sessione di gioco.",
                parent=self
            )
            return
            
        if not getattr(self, "custom_spell_request_callback", None):
            messagebox.showwarning("Non Consentito", "In sessione multiplayer la rimozione di incantesimi richiede l'approvazione del Master.", parent=self)
            return
            
        if messagebox.askyesno(
            "Richiesta Rimozione al Master",
            f"Vuoi inviare la richiesta di rimozione per l'incantesimo '{s_name}' al Dungeon Master per approvazione?",
            parent=self
        ):
            sent = self.custom_spell_request_callback({"name": s_name, "level": sp.get("level", 0), "action": "remove"})
            if sent:
                messagebox.showinfo(
                    "Richiesta Inviata",
                    f"Richiesta di rimozione per '{s_name}' inviata al Master!\nL'incantesimo verrà rimosso dal tuo Grimorio una volta approvato.",
                    parent=self
                )

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
            
            desc_text = (str(spell.get('desc', '')) + " " + str(spell.get('duration', ''))).lower()
            requires_conc = ("concentrazione" in desc_text or "concentration" in desc_text)
            conc_info = ""
            if requires_conc:
                if not hasattr(self.character, "conditions") or not isinstance(self.character.conditions, list):
                    self.character.conditions = []
                if "Concentrazione" in self.character.conditions:
                    conc_info = f" [⚡ La precedente Concentrazione di {self.character.name} si interrompe per mantenere {spell.get('name', '')}!]"
                else:
                    self.character.conditions.append("Concentrazione")
                    conc_info = " [🧠 Concentrazione Attiva]"
                self.manager.update_character(self.character)

            self.manager.update_character(self.character)
            if hasattr(self.manager, 'save_characters'):
                self.manager.save_characters()
            if hasattr(self, "on_save_callback") and self.on_save_callback:
                try: self.on_save_callback(self.character)
                except Exception: pass

            if self.roll_callback:
                upcast_info = f" (Potenziato al Livello {cast_level}!)" if cast_level > lvl else ""
                chat_msg = f"{self.character.name} lancia {spell.get('name', '')}{upcast_info}!{conc_info}"
                self.roll_callback("0d0", chat_msg)
            win.destroy()

            
        def do_attack():
            if not getattr(self, 'attack_callback', None): return
            hit_bonus_str = tk.simpledialog.askstring("Bonus Colpire", "Inserisci bonus per colpire (es. 5):", parent=win)
            if not hit_bonus_str: return
            try: hit_bonus = int(hit_bonus_str)
            except (ValueError, TypeError): hit_bonus = 0
            
            dmg_str = tk.simpledialog.askstring("Danno", "Inserisci formula danno (es. 1d8+3):", parent=win)
            if not dmg_str: return
            
            self.attack_callback(spell.get('name', ''), hit_bonus, dmg_str)
            win.destroy()

        ttk.Button(btn_frame, text="Lancia in Chat", command=do_cast).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Attacca Bersaglio", command=do_attack, style="Danger.TButton").pack(side=tk.LEFT, padx=10)

    def _handle_found_spell(self, name, level, time, rng, desc):
        spell_dict = {
            "name": name,
            "level": level,
            "time": time,
            "range": rng,
            "desc": desc
        }
        if self.is_connected:
            if not getattr(self, "custom_spell_request_callback", None):
                messagebox.showwarning("Non Consentito", "In sessione multiplayer non puoi aggiungere autonomamente incantesimi al Grimorio. Richiedi l'aggiunta al Master.", parent=self)
                return
            if messagebox.askyesno(
                "Richiesta Approvazione al Master",
                f"★ {name} (Livello {level})\nTempo: {time} | Gittata: {rng}\n\n"
                f"⚠️ Sei connesso a una sessione multiplayer: non puoi aggiungere incantesimi direttamente al Grimorio senza il permesso del Master.\n\n"
                f"Vuoi inviare la richiesta di approvazione per questo incantesimo al Dungeon Master?",
                parent=self
            ):
                sent = self.custom_spell_request_callback(spell_dict)
                if sent:
                    messagebox.showinfo("Richiesta Inviata", f"Richiesta per l'incantesimo '{name}' inviata al Master!\nRiceverai una notifica quando il Master risponderà.", parent=self)
        else:
            messagebox.showwarning(
                "Azione Non Consentita",
                f"★ {name} (Livello {level})\n\n"
                f"Non puoi aggiungere incantesimi al Grimorio autonomamente, nemmeno in modalità offline.\n\n"
                f"L'acquisizione di nuovi incantesimi richiede sempre l'approvazione del Dungeon Master durante una sessione di gioco.",
                parent=self
            )

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
                    self._handle_found_spell(title, lvl, "1 Azione", "Vedi manuale", content)
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
                    
                    self.after(0, lambda: self._handle_found_spell(name, level, time, rng, desc))
                else:
                    from common.srd_offline import search_spells_offline
                    local_hits = search_spells_offline(query_clean)
                    if local_hits:
                        sp = local_hits[0]
                        self.after(0, lambda: self._handle_found_spell(sp["name"], sp["level"], sp["time"], sp["range"], sp["desc"]))
                    else:
                        self.after(0, lambda: messagebox.showinfo("Nessun risultato", f"Incantesimo '{query}' non trovato nei manuali, nell'SRD locale o online."))
            except Exception:
                # Fallback trasparente offline su srd_data/open5e_spells.json
                from common.srd_offline import search_spells_offline
                local_hits = search_spells_offline(query_clean)
                if local_hits:
                    sp = local_hits[0]
                    self.after(0, lambda: self._handle_found_spell(sp["name"], sp["level"], sp["time"], sp["range"], sp["desc"]))
                else:
                    self.after(0, lambda: messagebox.showinfo("Nessun risultato", f"Incantesimo '{query}' non trovato nei manuali o nell'SRD locale (offline)."))
                
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

    def update_subclass_suggestions(self):
        if not hasattr(self, 'subclass_combo'): return
        c_cls = (self.class_var.get() or "").lower().strip()
        found_options = []
        for k, v in SRD_SUBCLASSES.items():
            if k in c_cls or c_cls in k:
                found_options = v
                break
        self.subclass_combo['values'] = found_options


    def _on_avatar_clicked(self):
        from common.image_utils import open_avatar_file_dialog, render_avatar_on_canvas
        b64, path = open_avatar_file_dialog(parent=self)
        if b64:
            self.character.avatar_b64 = b64
            self.character.avatar_path = path
            render_avatar_on_canvas(self.avatar_canvas, b64, self.character.name, size=64)
            self.manager.update_character(self.character)
            if self.is_connected and self.on_save_callback:
                self.on_save_callback(self.character)

    def _on_avatar_right_click(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="📁 Scegli Nuova Immagine Token...", command=self._on_avatar_clicked)
        menu.add_command(label="❌ Rimuovi Immagine Token", command=self._remove_avatar)
        menu.tk_popup(event.x_root, event.y_root)

    def _remove_avatar(self):
        from common.image_utils import render_avatar_on_canvas
        self.character.avatar_b64 = ""
        self.character.avatar_path = ""
        render_avatar_on_canvas(self.avatar_canvas, "", self.character.name, size=64)
        self.manager.update_character(self.character)
        if self.is_connected and self.on_save_callback:
            self.on_save_callback(self.character)

    def load_data(self):
        from common.image_utils import render_avatar_on_canvas
        if hasattr(self, "avatar_canvas"):
            render_avatar_on_canvas(self.avatar_canvas, getattr(self.character, "avatar_b64", ""), self.character.name, size=64)
        self.name_var.set(self.character.name)
        self.campaign_var.set(self.character.campaign)
        self.class_var.set(self.character.char_class)
        self.level_var.set(self.character.level)
        self.race_var.set(self.character.race)
        if hasattr(self, 'subclass_var'):
            self.subclass_var.set(getattr(self.character, "subclass", ""))
            self.update_subclass_suggestions()
        if hasattr(self, 'background_var'):
            self.background_var.set(getattr(self.character, "background", ""))
        if hasattr(self, 'alignment_var'):
            self.alignment_var.set(getattr(self.character, "alignment", ""))
        if hasattr(self, 'class_var') and not getattr(self, '_class_var_traced', False):
            self.class_var.trace_add("write", lambda *args: self.update_subclass_suggestions())
            self._class_var_traced = True
        
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
        from common.srd_offline import normalize_ac_value, normalize_speed_value
        self.ac_var.set(normalize_ac_value(getattr(self.character, "ac", 10)))
        self.init_var.set(self.character.initiative)
        spd = getattr(self.character, "speed", 30)
        speed_val, speed_disp, u = normalize_speed_value(spd, default_unit=getattr(self.character, "speed_unit", None))
        self.speed_var.set(str(speed_val))
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
            val = getattr(self.character, attr, "")
            txt.insert("1.0", val)
            if attr in getattr(self, "_markdown_widgets", {}):
                bundle = self._markdown_widgets[attr]
                render_markdown_to_widget(bundle["preview"], val)
                if not val.strip():
                    bundle["preview"].pack_forget()
                    bundle["edit"].pack(fill=tk.BOTH, expand=True)
                    bundle["btn_toggle"].config(text="👁️ Vista Formattata (Markdown)")
                    bundle["mode"] = "edit"
                else:
                    bundle["edit"].pack_forget()
                    bundle["preview"].pack(fill=tk.BOTH, expand=True)
                    bundle["btn_toggle"].config(text="✏️ Modifica Testo")
                    bundle["mode"] = "preview"

        if hasattr(self, 'refresh_features_ui'):
            self.refresh_features_ui()
                
        # Sincronizza le monete presenti nell'inventario con la tabella superiore delle valute
        self.sync_inventory_coins_to_currency()

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
        self._suppress_weight_sync = False
        self.calculate_total_weight()
        self._initial_text_fields = {
            "journal_notes": getattr(self.character, "journal_notes", ""),
            "notes": getattr(self.character, "notes", ""),
            "features": getattr(self.character, "features", "")
        }
        self._capture_initial_state()

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

    def set_container_filter(self, container_key: str):
        self.current_container_filter = container_key
        self.refresh_inventory_grid()

    def refresh_inventory_grid(self):
        backpack_dropped = getattr(self.character, "backpack_dropped", False)
        from common.starter_equipment import lookup_standard_weight, get_pack_contents
        from client.character_manager import CONTAINERS
        
        # 1. Calcola statistiche per contenitore
        c_counts = {"all": 0, "backpack": 0, "equipped": 0, "bag_of_holding": 0, "haversack": 0, "mount": 0}
        c_weights = {"all": 0.0, "backpack": 0.0, "equipped": 0.0, "bag_of_holding": 0.0, "haversack": 0.0, "mount": 0}
        
        for item in self.character.inventory_grid:
            if not item or not isinstance(item, dict):
                continue
            c_key = item.get("container")
            if not c_key:
                itype = str(item.get("type", "")).strip().lower()
                c_key = "equipped" if itype in ("arma", "armatura", "scudo", "weapon", "armor", "shield") else "backpack"
            if c_key not in c_counts:
                c_key = "backpack"
            c_counts[c_key] += 1
            c_counts["all"] += 1
            
            try:
                w = float(item.get("weight", 0.0) or 0.0)
                q = int(item.get("qty", 1) or 1)
                c_weights[c_key] += round(w * q, 2)
                c_weights["all"] += round(w * q, 2)
            except (ValueError, TypeError):
                pass
                
        # 2. Aggiorna bottoni del filtro contenitori
        if hasattr(self, "container_filter_btns"):
            filter_labels = [
                ("all", f"📦 Tutti ({c_counts['all']}/25)"),
                ("backpack", f"🎒 Zaino ({c_counts['backpack']})"),
                ("equipped", f"⚔️ Addosso ({c_counts['equipped']})"),
                ("bag_of_holding", f"🔮 Borsa ({c_counts['bag_of_holding']})"),
                ("haversack", f"✨ Pratico ({c_counts['haversack']})"),
                ("mount", f"🐴 Cavalcatura ({c_counts['mount']})"),
            ]
            for f_key, f_lbl in filter_labels:
                btn_widget = self.container_filter_btns.get(f_key)
                if btn_widget and btn_widget.winfo_exists():
                    is_active = (f_key == getattr(self, "current_container_filter", "all"))
                    btn_widget.config(text=f_lbl, style="Gold.TButton" if is_active else "Slot.TButton")
                    
        # 3. Aggiorna stringa informativa del contenitore
        if hasattr(self, "container_info_lbl") and self.container_info_lbl.winfo_exists():
            active_f = getattr(self, "current_container_filter", "all")
            if active_f == "all":
                carried_w = self.character.get_carried_weight()
                self.container_info_lbl.config(
                    text=f"📦 Tutti gli Oggetti: {c_counts['all']}/25 slot occupati • Carico Trasportato: {carried_w} lbs"
                )
            elif active_f == "backpack":
                bp_state = "⚠️ A Terra (Escluso dal carico)" if backpack_dropped else "Indossato (Sul personaggio)"
                self.container_info_lbl.config(
                    text=f"🎒 Zaino: {c_counts['backpack']} oggetti • Peso interno: {c_weights['backpack']:.1f} lbs • Stato: {bp_state}"
                )
            elif active_f == "equipped":
                self.container_info_lbl.config(
                    text=f"⚔️ Addosso / Equipaggiato: {c_counts['equipped']} oggetti • Peso: {c_weights['equipped']:.1f} lbs (Grava sempre sul carico corporeo)"
                )
            elif active_f == "bag_of_holding":
                self.container_info_lbl.config(
                    text=f"🔮 Borsa Conservante: {c_counts['bag_of_holding']} oggetti • Peso interno: {c_weights['bag_of_holding']:.1f} / 500.0 lbs (Extradimensionale)"
                )
            elif active_f == "haversack":
                self.container_info_lbl.config(
                    text=f"✨ Zaino Pratico di Heward: {c_counts['haversack']} oggetti • Peso interno: {c_weights['haversack']:.1f} / 120.0 lbs (Extradimensionale)"
                )
            elif active_f == "mount":
                self.container_info_lbl.config(
                    text=f"🐴 Sacca da Sella / Cavalcatura: {c_counts['mount']} oggetti • Peso: {c_weights['mount']:.1f} lbs (Non grava sul PG)"
                )
                
        # 4. Aggiorna ciascuna riga dello slot
        active_filter = getattr(self, "current_container_filter", "all")
        for i, item in enumerate(self.character.inventory_grid):
            btn = self.inventory_buttons[i]
            btn_c = self.container_quick_buttons[i] if i < len(self.container_quick_buttons) else None
            btn_sp = self.spend_buttons[i] if i < len(self.spend_buttons) else None
            row_frame = self.inventory_row_frames[i] if i < len(self.inventory_row_frames) else None
            
            # Filtro visibilità riga
            item_c = "backpack"
            if item:
                item_c = item.get("container")
                if not item_c:
                    itype = str(item.get("type", "")).strip().lower()
                    item_c = "equipped" if itype in ("arma", "armatura", "scudo", "weapon", "armor", "shield") else "backpack"
            
            if item:
                name = item.get("name", _t("sheet_item"))
                item_w = item.get("weight", 0.0)
                try:
                    item_w = float(item_w)
                except (ValueError, TypeError):
                    item_w = 0.0
                if item_w <= 0.0:
                    std_w = lookup_standard_weight(name)
                    if std_w > 0:
                        item["weight"] = std_w
                        item_w = std_w
                if hasattr(self, 'weight_vars') and i < len(self.weight_vars):
                    self.weight_vars[i].set(item.get("weight", item_w))
                if hasattr(self, 'attuned_vars') and i < len(self.attuned_vars):
                    self.attuned_vars[i].set(item.get("attuned", False))
            else:
                if hasattr(self, 'weight_vars') and i < len(self.weight_vars):
                    self.weight_vars[i].set(0.0)
                if hasattr(self, 'attuned_vars') and i < len(self.attuned_vars):
                    self.attuned_vars[i].set(False)

            should_show = (active_filter == "all") or (item and item_c == active_filter)
            if row_frame:
                if should_show:
                    row_frame.pack(fill=tk.X, padx=2, pady=1)
                else:
                    row_frame.pack_forget()
                    continue

            if item:
                qty = item.get("qty", 1)
                icon = get_item_icon(item)
                item_type = item.get("type", "")
                type_str = f" [{item_type}]" if item_type else ""
                
                c_info = CONTAINERS.get(item_c, CONTAINERS["backpack"])
                c_icon = c_info.get("icon", "🎒")
                c_name = c_info.get("name_it" if get_language() == "it" else "name_en", "Zaino")
                
                is_on_ground = (item_c == "backpack" and backpack_dropped)
                ground_tag = " [A Terra]" if is_on_ground else ""
                
                short_name = name[:18] + ".." if len(name) > 18 else name
                btn_style = "Slot.TButton" if is_on_ground else "SlotFilled.TButton"
                btn.config(text=f"{c_icon} {icon} {short_name} (x{qty}){type_str}{ground_tag}", style=btn_style)
                
                if btn_c:
                    btn_c.config(text=c_icon, state=tk.NORMAL)
                    ToolTip(btn_c, f"Collocato in: {c_icon} {c_name}\nClicca per spostare in un altro contenitore")
                    
                is_spendable = self.is_spendable_item(item)
                pack_items = get_pack_contents(name)
                if btn_sp:
                    if is_spendable:
                        btn_sp.config(text="-1", state=tk.NORMAL)
                        ToolTip(btn_sp, f"Spendi / Consuma 1x {name} (Rimanenti: {qty})\nClicca per spendere")
                    elif pack_items:
                        btn_sp.config(text="📦", state=tk.NORMAL)
                        ToolTip(btn_sp, f"Spacchetta '{name}' estraendo i contenuti ({len(pack_items)} oggetti)")
                    else:
                        btn_sp.config(text="", state=tk.DISABLED)
                
                if hasattr(self, 'weight_vars') and i < len(self.weight_vars):
                    self.weight_vars[i].set(item.get("weight", item_w if "item_w" in locals() else 0.0))
                if hasattr(self, 'attuned_vars') and i < len(self.attuned_vars):
                    self.attuned_vars[i].set(item.get("attuned", False))
                desc = item.get("desc", "")
                weight = item.get("weight", 0.0)
                ground_status = "\n⚠️ QUESTO OGGETTO È A TERRA CON LO ZAINO!" if is_on_ground else ""
                spend_status = f"\n🏹 Oggetto Spendibile: clicca '[-1]' per consumare 1 unità." if is_spendable else ""
                pack_status = f"\n📦 Pacchetto Apribile: clicca '[📦]' per estrarre gli oggetti." if pack_items else ""
                tip_text = f"{name} (x{qty})\nCollocazione: {c_icon} {c_name}\nTipo: {item_type}\nPeso: {weight} lbs{ground_status}{spend_status}{pack_status}\n\n{desc}" if desc else f"{name} (x{qty})\nCollocazione: {c_icon} {c_name}\nTipo: {item_type}\nPeso: {weight} lbs{ground_status}{spend_status}{pack_status}"
                ToolTip(btn, tip_text)
            else:
                btn.config(text=f"➕ {_t('sheet_empty_slot_desc')}", style="Slot.TButton")
                empty_tip = _t("sheet_empty_slot_desc") if self.is_connected else "Slot Vuoto (L'assegnazione di oggetti richiede l'approvazione del Master in sessione)"
                ToolTip(btn, empty_tip)
                if btn_c:
                    btn_c.config(text="➕", state=tk.DISABLED)
                if btn_sp:
                    btn_sp.config(text="", state=tk.DISABLED)
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

    def is_spendable_item(self, item: dict) -> bool:
        """Determina se un oggetto è spendibile/consumabile (frecce, dardi, pozioni, razioni, torce, ecc.)."""
        if not item or not isinstance(item, dict):
            return False
        qty = item.get("qty", 1)
        try:
            qty = int(qty)
        except (ValueError, TypeError):
            qty = 1
        if qty <= 0:
            return False
        itype = str(item.get("type", "")).strip().lower()
        iname = str(item.get("name", "")).strip().lower()
        idesc = str(item.get("desc", "")).strip().lower()
        
        if any(k in itype for k in ["munizion", "ammunition", "ammo", "consumab", "pozion", "potion", "pergamena", "scroll"]):
            return True
        if any(k in iname or k in idesc for k in [
            "frecc", "arrow", "dard", "bolt", "proiettil", "bullet",
            "pozione", "potion", "elisir", "fiala", "vial", "razion", "ration",
            "torcia", "torce", "torch", "boccetta", "olio", "oil", "antidoto",
            "erba", "benda", "bende", "kit medic", "healer's kit", "candela", "candele"
        ]):
            return True
        if qty > 1 and itype not in ["arma", "armatura", "scudo", "weapon", "armor", "shield"]:
            return True
        return False

    def on_quick_spend_or_open_click(self, slot_idx: int):
        if slot_idx < 0 or slot_idx >= len(self.character.inventory_grid):
            return
        item = self.character.inventory_grid[slot_idx]
        if not item or not isinstance(item, dict):
            return
        from common.starter_equipment import get_pack_contents
        if get_pack_contents(item.get("name", "")):
            self.unpack_starter_pack(slot_idx)
        elif self.is_spendable_item(item):
            self.spend_consumable(slot_idx, 1)

    def spend_consumable(self, slot_idx: int, amount: int = 1):
        if slot_idx < 0 or slot_idx >= len(self.character.inventory_grid):
            return
        item = self.character.inventory_grid[slot_idx]
        if not item or not isinstance(item, dict):
            return
            
        it_name = item.get("name", "Oggetto")
        try:
            current_qty = int(item.get("qty", 1))
        except (ValueError, TypeError):
            current_qty = 1
            
        if current_qty < amount:
            messagebox.showwarning("Quantità Insufficiente", f"Non hai abbastanza {it_name} (Disponibili: {current_qty}, Richiesti: {amount}).", parent=self)
            return
            
        heal_msg = ""
        iname_lower = it_name.lower()
        if "pozione" in iname_lower or "potion" in iname_lower:
            import random
            heal_roll = 0
            pot_tier = ""
            if any(k in iname_lower for k in ["suprema", "supreme"]):
                heal_roll = sum(random.randint(1, 4) for _ in range(10)) + 20
                pot_tier = "Suprema (10d4+20)"
            elif any(k in iname_lower for k in ["superiore", "superior"]):
                heal_roll = sum(random.randint(1, 4) for _ in range(8)) + 8
                pot_tier = "Superiore (8d4+8)"
            elif any(k in iname_lower for k in ["maggiore", "greater"]):
                heal_roll = sum(random.randint(1, 4) for _ in range(4)) + 4
                pot_tier = "Maggiore (4d4+4)"
            elif any(k in iname_lower for k in ["guarigione", "healing", "cura"]):
                heal_roll = sum(random.randint(1, 4) for _ in range(2)) + 2
                pot_tier = "Comune (2d4+2)"
            if heal_roll > 0:
                old_hp = self.character.hp_current
                self.character.hp_current = min(self.character.hp_max, self.character.hp_current + heal_roll)
                if hasattr(self, "hp_cur_var"):
                    self.hp_cur_var.set(self.character.hp_current)
                if hasattr(self, "hp_cur_entry") and self.hp_cur_entry.winfo_exists():
                    self.hp_cur_entry.delete(0, tk.END)
                    self.hp_cur_entry.insert(0, str(self.character.hp_current))
                if hasattr(self, "update_hp_bar"):
                    self.update_hp_bar()
                heal_msg = f"\n🧪 Hai bevuto la Pozione di Guarigione {pot_tier} e recuperato +{heal_roll} PF (ora {self.character.hp_current}/{self.character.hp_max})!"

        new_qty = current_qty - amount
        if new_qty > 0:
            item["qty"] = new_qty
            status_text = f"Hai consumato {amount}x {it_name}. Rimanenti: {new_qty}.{heal_msg}"
        else:
            ans = messagebox.askyesno(
                "Oggetto Esaurito",
                f"Hai consumato l'ultima unità di '{it_name}'!{heal_msg}\n\nVuoi liberare lo slot nell'inventario?",
                parent=self
            )
            if ans:
                self.character.inventory_grid[slot_idx] = None
                status_text = f"Hai consumato l'ultima unità di {it_name}. Slot liberato.{heal_msg}"
            else:
                item["qty"] = 0
                status_text = f"Hai consumato l'ultima unità di {it_name}. Rimanenti: 0 (Esaurito).{heal_msg}"

        self.manager.update_character(self.character)
        if hasattr(self.manager, 'save_characters'):
            self.manager.save_characters()
            
        self.refresh_inventory_grid()
        self.refresh_weapons_list()
        
        if self.is_connected and getattr(self, "network", None):
            from common.protocol import make_update_full_sheet_request, make_update_stats_request, make_chat_message
            self.network.send(make_update_stats_request(self.character.hp_current, self.character.hp_max, self.character.initiative, getattr(self.character, "conditions", [])))
            self.network.send(make_update_full_sheet_request(self.character.to_dict()))
            self.network.send(make_chat_message(f"[CONSUMO] {self.character.name} ha consumato {amount}x {it_name} (Rimanenti: {new_qty})"))
            
        if hasattr(self, "show_toast"):
            self.show_toast(status_text, title="Oggetto Consumato", toast_type="info")
        else:
            messagebox.showinfo("Oggetto Consumato", status_text, parent=self)

    def prompt_spend_custom_amount(self, slot_idx: int):
        if slot_idx < 0 or slot_idx >= len(self.character.inventory_grid):
            return
        item = self.character.inventory_grid[slot_idx]
        if not item: return
        it_name = item.get("name", "Oggetto")
        try:
            qty = int(item.get("qty", 1))
        except (ValueError, TypeError):
            qty = 1
        ans = simpledialog.askinteger(
            "Spendi Quantità",
            f"Quante unità di '{it_name}' vuoi spendere / consumare?\n(Disponibili: {qty})",
            parent=self,
            minvalue=1,
            maxvalue=max(1, qty),
            initialvalue=1
        )
        if ans:
            self.spend_consumable(slot_idx, ans)

    def unpack_starter_pack(self, slot_idx: int):
        if slot_idx < 0 or slot_idx >= len(self.character.inventory_grid):
            return
        item = self.character.inventory_grid[slot_idx]
        if not item or not isinstance(item, dict):
            return
        pack_name = item.get("name", "")
        from common.starter_equipment import get_pack_contents
        sub_items = get_pack_contents(pack_name)
        if not sub_items:
            messagebox.showinfo("Non è un Pacchetto", f"'{pack_name}' non è un pacchetto o kit apribile.", parent=self)
            return
            
        free_slots = [idx for idx, it in enumerate(self.character.inventory_grid) if it is None]
        slots_needed = len(sub_items) - 1
        if len(free_slots) < slots_needed:
            messagebox.showwarning(
                "Spazio Insufficiente",
                f"Per spacchettare '{pack_name}' servono {len(sub_items)} slot liberi nello zaino (attualmente ne hai {len(free_slots)+1}).\n\n"
                "Libera prima qualche slot per estrarre tutti gli oggetti individuali.",
                parent=self
            )
            return
            
        if not messagebox.askyesno(
            "Spacchetta Contenuto",
            f"Vuoi estrarre tutti gli oggetti da '{pack_name}' nello zaino?\n\nVerranno inseriti {len(sub_items)} oggetti individuali (torce, razioni, corda, ecc.) spendibili singolarmente.",
            parent=self
        ):
            return
            
        self.character.inventory_grid[slot_idx] = sub_items[0]
        curr_sub_idx = 1
        for free_idx in free_slots:
            if curr_sub_idx >= len(sub_items):
                break
            self.character.inventory_grid[free_idx] = sub_items[curr_sub_idx]
            curr_sub_idx += 1
            
        self.manager.update_character(self.character)
        if hasattr(self.manager, 'save_characters'):
            self.manager.save_characters()
            
        self.refresh_inventory_grid()
        self.refresh_weapons_list()
        
        if self.is_connected and getattr(self, "network", None):
            from common.protocol import make_update_full_sheet_request, make_chat_message
            self.network.send(make_update_full_sheet_request(self.character.to_dict()))
            self.network.send(make_chat_message(f"[INVENTARIO] {self.character.name} ha spacchettato '{pack_name}' estraendo i contenuti nello zaino."))
            
        messagebox.showinfo(
            "Contenuto Estratto",
            f"'{pack_name}' è stato spacchettato con successo!\nTutti gli oggetti (incluse torce e razioni) sono ora gestibili e spendibili direttamente nello zaino.",
            parent=self
        )

    def move_item_to_container(self, slot_idx: int, target_container: str):
        if slot_idx < 0 or slot_idx >= len(self.character.inventory_grid):
            return
        item = self.character.inventory_grid[slot_idx]
        if not item or not isinstance(item, dict):
            return
        from client.character_manager import CONTAINERS
        c_info = CONTAINERS.get(target_container, CONTAINERS.get("backpack", {}))
        c_name = c_info.get("name_it" if get_language() == "it" else "name_en", target_container)
        c_icon = c_info.get("icon", "📦")
        
        old_container = item.get("container", "backpack")
        if old_container == target_container:
            return
            
        item["container"] = target_container
        self.manager.update_character(self.character)
        if hasattr(self.manager, 'save_characters'):
            self.manager.save_characters()
            
        self.refresh_inventory_grid()
        
        if self.is_connected and getattr(self, "network", None):
            from common.protocol import make_update_full_sheet_request
            self.network.send(make_update_full_sheet_request(self.character.to_dict()))

    def open_quick_container_picker(self, slot_idx: int, button_widget: tk.Widget):
        if slot_idx < 0 or slot_idx >= len(self.character.inventory_grid):
            return
        item = self.character.inventory_grid[slot_idx]
        if not item or not isinstance(item, dict):
            return
            
        it_name = item.get("name", "Oggetto")
        curr_c = item.get("container", "backpack")
        from client.character_manager import CONTAINERS
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=f"📦 Collocazione: {it_name}", state="disabled")
        menu.add_separator()
        
        for c_id, c_data in CONTAINERS.items():
            c_icon = c_data.get("icon", "")
            c_name = c_data.get("name_it" if get_language() == "it" else "name_en", c_id)
            prefix = "✓ " if c_id == curr_c else "   "
            menu.add_command(
                label=f"{prefix}{c_icon} {c_name}",
                command=lambda c=c_id: self.move_item_to_container(slot_idx, c)
            )
            
        x = button_widget.winfo_rootx()
        y = button_widget.winfo_rooty() + button_widget.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def show_container_context_menu(self, event, slot_idx: int):
        if slot_idx < 0 or slot_idx >= len(self.character.inventory_grid):
            return
        item = self.character.inventory_grid[slot_idx]
        menu = tk.Menu(self, tearoff=0)
        
        if item and isinstance(item, dict):
            it_name = item.get("name", "Oggetto")
            curr_c = item.get("container", "backpack")
            from client.character_manager import CONTAINERS
            
            menu.add_command(label=f"📦 {it_name}", state="disabled")
            menu.add_separator()
            
            c_menu = tk.Menu(menu, tearoff=0)
            for c_id, c_data in CONTAINERS.items():
                c_icon = c_data.get("icon", "")
                c_name = c_data.get("name_it" if get_language() == "it" else "name_en", c_id)
                prefix = "✓ " if c_id == curr_c else "   "
                c_menu.add_command(
                    label=f"{prefix}{c_icon} {c_name}",
                    command=lambda c=c_id: self.move_item_to_container(slot_idx, c)
                )
            menu.add_cascade(label="Sposta in Contenitore...", menu=c_menu)
            
            if self.is_spendable_item(item):
                qty = item.get("qty", 1)
                menu.add_command(
                    label=f"🏹 Spendi / Usa 1 (Disponibili: {qty})",
                    command=lambda: self.spend_consumable(slot_idx, 1)
                )
                menu.add_command(
                    label="🔢 Spendi Quantità...",
                    command=lambda: self.prompt_spend_custom_amount(slot_idx)
                )
                
            from common.starter_equipment import get_pack_contents
            if get_pack_contents(item.get("name", "")):
                menu.add_command(
                    label="📦 Spacchetta / Estrai Contenuto nello Zaino",
                    command=lambda: self.unpack_starter_pack(slot_idx)
                )
                
            menu.add_separator()
            menu.add_command(label="✏️ Modifica Dettagli...", command=lambda: self.open_item_details_dialog(slot_idx, item))
            menu.add_command(label="🗑️ Richiedi Rimozione...", command=lambda: self.prompt_item_removal(slot_idx, item))
        else:
            menu.add_command(label=f"Slot #{slot_idx+1} Vuoto", state="disabled")
            if self.is_connected:
                menu.add_command(label="➕ Aggiungi Oggetto...", command=lambda: self.on_inventory_click(slot_idx))
                
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def prompt_item_removal(self, slot_idx: int, item: dict):
        if not self.is_connected:
            messagebox.showwarning(
                "Azione Non Consentita",
                "Non puoi rimuovere o scartare oggetti dall'inventario in modalità offline.\n\n"
                "La rimozione di oggetti richiede sempre l'approvazione del Dungeon Master durante una sessione di gioco.",
                parent=self
            )
            return
            
        it_name = item.get("name", "questo oggetto")
        if not getattr(self, "request_item_callback", None):
            messagebox.showwarning("Non Consentito", "In sessione multiplayer la rimozione di oggetti richiede l'approvazione del Master.", parent=self)
            return
            
        if messagebox.askyesno(
            "Richiesta Rimozione al Master",
            f"Vuoi inviare la richiesta di rimozione per '{it_name}' (Slot #{slot_idx+1}) al Dungeon Master per approvazione?",
            parent=self
        ):
            sent = self.request_item_callback({"name": it_name, "action": "remove", "type": item.get("type", "")}, slot_idx=slot_idx)
            if sent:
                messagebox.showinfo(
                    "Richiesta Inviata",
                    f"Richiesta di rimozione per '{it_name}' inviata al Master!\nL'oggetto verrà rimosso dallo zaino una volta approvato.",
                    parent=self
                )

    def on_inventory_click(self, idx):
        item = self.character.inventory_grid[idx]
        if not item:
            if not self.is_connected:
                messagebox.showwarning(
                    "Azione Non Consentita",
                    "Non puoi aggiungere oggetti all'inventario autonomamente in modalità offline.\n\n"
                    "L'assegnazione e l'aggiunta di nuovi oggetti possono avvenire esclusivamente con l'approvazione del Dungeon Master durante una sessione di gioco.",
                    parent=self
                )
                return
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
        if not self.is_connected:
            messagebox.showwarning(
                "Azione Non Consentita",
                "Non puoi creare o aggiungere oggetti all'inventario in modalità offline.\n\n"
                "La creazione di nuovi oggetti richiede l'approvazione del Dungeon Master durante una sessione di gioco connessa.",
                parent=self
            )
            return
        if target_idx is None:
            for i, it in enumerate(self.character.inventory_grid):
                if not it:
                    target_idx = i
                    break
        if target_idx is None:
            messagebox.showerror("Zaino Pieno", "Non c'è spazio libero nello zaino per un nuovo oggetto!", parent=self)
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
        type_combo.pack(fill=tk.X, pady=(0, 4))

        tk.Label(body, text=_t("lbl_container"), font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w", pady=(2, 1))
        container_opts = [
            ("backpack", _t("container_backpack")),
            ("equipped", _t("container_equipped")),
            ("bag_of_holding", _t("container_bag_of_holding")),
            ("haversack", _t("container_haversack")),
            ("mount", _t("container_mount")),
        ]
        container_combo = ttk.Combobox(body, values=[label for code, label in container_opts], state="readonly")
        container_combo.current(0)
        container_combo.pack(fill=tk.X, pady=(0, 6))

        def _update_container_by_type(event=None):
            st = str(type_combo.get() or "").strip().lower()
            if st in ("arma", "armatura", "scudo", "weapon", "armor", "shield"):
                container_combo.current(1)
            else:
                container_combo.current(0)
        type_combo.bind("<<ComboboxSelected>>", _update_container_by_type)
        _update_container_by_type()
        
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
            sel_c = container_combo.get()
            c_code = "backpack"
            for code, label in container_opts:
                if label == sel_c:
                    c_code = code
                    break
            entry = {
                "name": nm,
                "type": type_combo.get().strip() or "Equipaggiamento",
                "qty": max(1, qty_var.get()),
                "weight": max(0.0, weight_var.get()),
                "attuned": attune_var.get(),
                "desc": desc_text.get("1.0", tk.END).strip(),
                "container": c_code
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
        win.minsize(420, 480)
        
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
        name_entry.config(state="readonly")
        name_entry.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(body, text="Tipo / Categoria:", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w", pady=(2, 1))
        type_combo = ttk.Combobox(body, values=["Arma", "Armatura", "Scudo", "Pozione", "Pergamena", "Attrezzi", "Equipaggiamento", "Altro"], state="disabled")
        type_combo.set(item.get("type", "Equipaggiamento"))
        type_combo.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(body, text=_t("lbl_container"), font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(anchor="w", pady=(2, 1))
        current_container = item.get("container")
        if not current_container:
            itype = str(item.get("type", "")).strip().lower()
            current_container = "equipped" if itype in ("arma", "armatura", "scudo", "weapon", "armor", "shield") else "backpack"
            
        container_opts = [
            ("backpack", _t("container_backpack")),
            ("equipped", _t("container_equipped")),
            ("bag_of_holding", _t("container_bag_of_holding")),
            ("haversack", _t("container_haversack")),
            ("mount", _t("container_mount")),
        ]
        container_combo = ttk.Combobox(body, values=[label for code, label in container_opts], state="readonly")
        selected_idx = 0
        for opt_idx, (code, label) in enumerate(container_opts):
            if code == current_container:
                selected_idx = opt_idx
                break
        container_combo.current(selected_idx)
        container_combo.pack(fill=tk.X, pady=(0, 2))

        # Pulsanti rapidi cambio contenitore
        c_quick_frame = tk.Frame(body, bg=SURFACE_COLOR)
        c_quick_frame.pack(fill=tk.X, pady=(2, 6))
        tk.Label(c_quick_frame, text="Sposta rapido:", font=FONT_SMALL, fg=TEXT_MUTED, bg=SURFACE_COLOR).pack(side=tk.LEFT, padx=(0, 4))
        for opt_idx, (code, label) in enumerate(container_opts):
            c_icon = CONTAINERS.get(code, {}).get("icon", "📦")
            btn_cq = ttk.Button(
                c_quick_frame, text=c_icon, width=3,
                command=lambda oi=opt_idx: container_combo.current(oi)
            )
            btn_cq.pack(side=tk.LEFT, padx=1)
            ToolTip(btn_cq, f"Imposta collocazione: {label}")

        qp_frame = tk.Frame(body, bg=SURFACE_COLOR)
        qp_frame.pack(fill=tk.X, pady=4)
        
        tk.Label(qp_frame, text="Quantità:", font=FONT_BOLD, fg=TEXT_COLOR, bg=SURFACE_COLOR).pack(side=tk.LEFT, padx=(0, 4))
        initial_qty = max(1, int(item.get("qty", 1) or 1))
        qty_var = tk.IntVar(value=initial_qty)
        ttk.Button(qp_frame, text="-", width=2, command=lambda: qty_var.set(max(1, qty_var.get() - 1))).pack(side=tk.LEFT)
        ttk.Entry(qp_frame, textvariable=qty_var, width=4, justify="center", state="readonly").pack(side=tk.LEFT, padx=2)
        ttk.Button(qp_frame, text="+", width=2, command=lambda: qty_var.set(min(9999, qty_var.get() + 1))).pack(side=tk.LEFT, padx=(0, 14))
        
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
            if attune_var.get() and not item.get("attuned", False):
                current_attuned = sum(
                    1 for idx_i, it_i in enumerate(self.character.inventory_grid)
                    if it_i and idx_i != idx and it_i.get("attuned", False)
                )
                if current_attuned >= 3:
                    messagebox.showwarning("Limite Sintonia", "Non puoi sintonizzarti con più di 3 oggetti magici contemporaneamente!", parent=win)
                    return
            item["qty"] = max(1, qty_var.get())
            item["weight"] = max(0.0, w_var.get())
            item["attuned"] = attune_var.get()
            item["desc"] = desc_text.get("1.0", tk.END).strip()
            sel_c = container_combo.get()
            c_code = "backpack"
            for code, label in container_opts:
                if label == sel_c:
                    c_code = code
                    break
            item["container"] = c_code
            self.refresh_inventory_grid()
            self.manager.update_character(self.character)
            if hasattr(self.manager, 'save_characters'):
                self.manager.save_characters()
            win.destroy()
            
        def discard():
            if not self.is_connected:
                messagebox.showwarning(
                    "Azione Non Consentita",
                    "Non puoi rimuovere o scartare oggetti dall'inventario in modalità offline.\n\n"
                    "La rimozione di oggetti richiede sempre l'approvazione del Dungeon Master durante una sessione di gioco.",
                    parent=win
                )
                return
                
            it_name = item.get("name", "questo oggetto")
            if not getattr(self, "request_item_callback", None):
                messagebox.showwarning("Non Consentito", "In sessione multiplayer la rimozione di oggetti richiede l'approvazione del Master.", parent=win)
                return
                
            if messagebox.askyesno(
                "Richiesta Rimozione al Master",
                f"Vuoi inviare la richiesta di rimozione per '{it_name}' (Slot #{idx+1}) al Dungeon Master per approvazione?",
                parent=win
            ):
                sent = self.request_item_callback({"name": it_name, "action": "remove", "type": item.get("type", "")}, slot_idx=idx)
                if sent:
                    win.destroy()
                    messagebox.showinfo(
                        "Richiesta Inviata",
                        f"Richiesta di rimozione per '{it_name}' inviata al Master!\nL'oggetto verrà rimosso dallo zaino una volta approvato.",
                        parent=self
                    )
                
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
                item_qty = int(item.get("qty", 1) or 1)
                donate_qty = 1
                if item_qty > 1:
                    donate_qty = simpledialog.askinteger("Quantità", f"Quante unità di {item.get('name')} vuoi donare? (1-{item_qty}):", parent=win, minvalue=1, maxvalue=item_qty)
                    if not donate_qty:
                        return
                item_to_send = dict(item)
                item_to_send["qty"] = donate_qty
                if donate_qty >= item_qty:
                    self.character.inventory_grid[idx] = None
                else:
                    item["qty"] = item_qty - donate_qty
                self.refresh_inventory_grid()
                self.manager.update_character(self.character)
                if hasattr(self.manager, 'save_characters'):
                    self.manager.save_characters()
                self.trade_callback(item_to_send, target)
                win.destroy()
            elif target:
                messagebox.showerror("Errore", "Giocatore non trovato.", parent=win)
                
        if self.is_spendable_item(item):
            def _use_one():
                win.destroy()
                self.spend_consumable(idx, 1)
            ttk.Button(btn_frame, text="🏹 Spendi 1", command=_use_one, style="Gold.TButton").pack(side=tk.LEFT, padx=2)
            
            def _spend_custom():
                win.destroy()
                self.prompt_spend_custom_amount(idx)
            ttk.Button(btn_frame, text="🔢 Spendi...", command=_spend_custom).pack(side=tk.LEFT, padx=2)
            
        from common.starter_equipment import get_pack_contents
        if get_pack_contents(item.get("name", "")):
            def _unpack():
                win.destroy()
                self.unpack_starter_pack(idx)
            ttk.Button(btn_frame, text="📦 Spacchetta", command=_unpack, style="Gold.TButton").pack(side=tk.LEFT, padx=2)

        ttk.Button(btn_frame, text="💾 Salva", command=save_item, style="Gold.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🤝 Dona", command=trade).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🗑️ Scarta", command=discard, style="Danger.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Chiudi", command=win.destroy).pack(side=tk.RIGHT, padx=3)

    def open_inventory_compendium_for_slot(self, slot_idx):
        if not self.is_connected:
            messagebox.showwarning(
                "Azione Non Consentita",
                "Non puoi aggiungere oggetti all'inventario dal Compendio in modalità offline.\n\n"
                "L'importazione di oggetti richiede l'approvazione del Dungeon Master durante una sessione di gioco connessa.",
                parent=self
            )
            return
        from server.compendium_ui import CompendiumDialog
        def on_import(item_data, category):
            self.import_from_compendium_to_slot(item_data, category, slot_idx)
        CompendiumDialog(self.master, on_import_callback=on_import, is_dm=False)

    def import_from_compendium_to_slot(self, item_data, category, target_idx=None):
        if not self.is_connected:
            messagebox.showwarning(
                "Azione Non Consentita",
                "Non puoi aggiungere oggetti o incantesimi alla scheda senza l'approvazione del Dungeon Master durante una sessione di gioco.",
                parent=self
            )
            return
        if category == "Incantesimi":
            desc = item_data.get("desc", "")
            if isinstance(desc, list):
                desc = "\n".join(desc)
            spell_dict = {
                "name": item_data.get("name", ""),
                "level": item_data.get("level", 0),
                "time": item_data.get("casting_time", ""),
                "range": item_data.get("range", ""),
                "desc": desc
            }
            if self.custom_spell_request_callback:
                if messagebox.askyesno(
                    "Richiesta Approvazione al Master",
                    f"Incantesimo selezionato: ★ {spell_dict['name']} (Livello {spell_dict['level']})\n\n"
                    f"Vuoi inviare la richiesta di approvazione per questo incantesimo al Dungeon Master?",
                    parent=self
                ):
                    sent = self.custom_spell_request_callback(spell_dict)
                    if sent:
                        messagebox.showinfo("Richiesta Inviata", f"Richiesta per '{spell_dict['name']}' inviata al Master!\nRiceverai una notifica quando il Master risponderà.", parent=self)
            else:
                messagebox.showwarning("Non Connesso", "Devi essere connesso al server per richiedere l'approvazione di un incantesimo.", parent=self)
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
            
        cat_lower = str(category).lower()
        default_c = "equipped" if any(k in cat_lower for k in ["arma", "armatura", "scudo", "weapon", "armor", "shield"]) else "backpack"
        entry = {
            "name": item_data.get("name"),
            "type": category,
            "qty": 1,
            "weight": weight,
            "attuned": False,
            "desc": desc,
            "container": default_c
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

    def toggle_drop_backpack(self):
        new_state = self.character.toggle_drop_backpack()
        self.manager.update_character(self.character)
        if hasattr(self.manager, 'save_characters'):
            self.manager.save_characters()
            
        self.refresh_inventory_grid()
        self.calculate_total_weight()
        
        char_name = getattr(self.character, "name", "Eroe")
        if new_state:
            chat_msg = _t("msg_backpack_dropped", name=char_name)
        else:
            chat_msg = _t("msg_backpack_picked_up", name=char_name)
            
        if hasattr(self, 'roll_callback') and self.roll_callback:
            try:
                self.roll_callback("0d0", chat_msg)
            except Exception:
                pass
                
        if hasattr(self, 'on_save_callback') and self.on_save_callback:
            try:
                self.on_save_callback(self.character)
            except Exception:
                pass

    def open_inventory_compendium(self):
        if not self.is_connected:
            messagebox.showwarning(
                "Azione Non Consentita",
                "Non puoi aggiungere oggetti all'inventario dal Compendio in modalità offline.\n\n"
                "L'importazione di oggetti richiede l'approvazione del Dungeon Master durante una sessione di gioco connessa.",
                parent=self
            )
            return
        from server.compendium_ui import CompendiumDialog
        CompendiumDialog(self.master, on_import_callback=self.import_from_compendium, is_dm=False)

    def import_from_compendium(self, item_data, category):
        return self.import_from_compendium_to_slot(item_data, category, None)

    def _adjust_hp_quick(self, delta: int):
        if self.is_connected:
            return
        try:
            cur = int(self.hp_cur_var.get())
            mx = max(1, int(self.hp_max_var.get()))
            new_hp = max(0, min(mx, cur + delta))
            self.hp_cur_var.set(new_hp)
        except (ValueError, tk.TclError):
            pass

    def save_character(self, event=None, close_after=True):
        try:
            self.character.name = self.name_var.get()
            self.character.campaign = self.campaign_var.get()
            self.character.char_class = self.class_var.get()
            self.character.level = self.level_var.get()
            self.character.race = self.race_var.get()
            if hasattr(self, "subclass_var"):
                self.character.subclass = self.subclass_var.get().strip()
            if hasattr(self, "background_var"):
                self.character.background = self.background_var.get().strip()
            if hasattr(self, "alignment_var"):
                self.character.alignment = self.alignment_var.get().strip()
            
            for k, var in self.attr_vars.items():
                self.character.attributes[k] = var.get()
                
            if not hasattr(self.character, "skills"):
                self.character.skills = {}
            for k, var in self.skill_vars.items():
                try:
                    self.character.skills[k] = var.get()
                except tk.TclError:
                    self.character.skills[k] = 0
                
            if not self.is_connected:
                self.character.hp_current = self.hp_cur_var.get()
                self.character.hp_max = self.hp_max_var.get()
            self.character.ac = self.ac_var.get()
            self.character.initiative = self.init_var.get()
            spd_raw = float(str(self.speed_var.get()).replace(",", "."))
            self.character.speed = int(spd_raw) if spd_raw == int(spd_raw) else round(spd_raw, 1)
            if hasattr(self, "speed_unit_var"):
                self.character.speed_unit = self.speed_unit_var.get()
                set_distance_unit(self.character.speed_unit)
            
            if self.is_connected:
                approval_fields = [
                    ("journal_notes", "Biografia & Diario"),
                    ("notes", "Appunti di Sessione"),
                    ("features", "Tratti & Privilegi")
                ]
                for attr_key, disp_name in approval_fields:
                    if attr_key in self.text_widgets:
                        new_val = self.text_widgets[attr_key].get("1.0", tk.END).strip()
                        initial_val = self._initial_text_fields.get(attr_key, getattr(self.character, attr_key, "")).strip()
                        if new_val != initial_val:
                            if messagebox.askyesno(
                                "Richiesta Approvazione al Master",
                                f"Hai modificato la sezione '{disp_name}'.\n\n"
                                f"Sei in sessione multiplayer: per applicare queste modifiche è richiesta l'approvazione del Dungeon Master.\n\n"
                                f"Vuoi inviare la richiesta di approvazione al Master ora?",
                                parent=self
                            ):
                                if self.request_journal_approval_callback:
                                    self.request_journal_approval_callback(attr_key, new_val, title=f"Aggiornamento {disp_name}")
                            setattr(self.character, attr_key, initial_val)
                    elif attr_key == "features" and hasattr(self.character, "features_list"):
                        serialized = serialize_features_list(self.character.features_list)
                        initial_val = self._initial_text_fields.get("features", getattr(self.character, "features", "")).strip()
                        if serialized != initial_val:
                            if messagebox.askyesno(
                                "Richiesta Approvazione al Master",
                                f"Hai modificato i Tratti & Privilegi del personaggio.\n\n"
                                f"Sei in sessione multiplayer: per applicare queste modifiche è richiesta l'approvazione del Dungeon Master.\n\n"
                                f"Vuoi inviare la richiesta di approvazione al Master ora?",
                                parent=self
                            ):
                                if self.request_journal_approval_callback:
                                    self.request_journal_approval_callback("features", serialized, title="Aggiornamento Tratti & Privilegi")
                            setattr(self.character, "features", initial_val)
            else:
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
            self._capture_initial_state()
            
            if self.on_save_callback:
                self.on_save_callback(self.character)
                
            if close_after:
                self.close_sheet()
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
            prof_bonus = ((max(1, int(level)) - 1) // 4) + 2
            
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
        win = tk.Toplevel(self)
        win.transient(self)
        win.grab_set()
        apply_modern_window_style(win)
        win.title("❤️ Riposo Breve - Spesa Dadi Vita 5e")
        win.minsize(440, 480)

        container = tk.Frame(win, bg=BG_COLOR, padx=16, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text="❤️ Riposo Breve (Short Rest D&D 5e)", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
        tk.Label(container, text="Spendi Dadi Vita per recuperare PF e ripristinare i privilegi di classe.", font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 10))

        # Status frame
        st_frame = tk.Frame(container, bg=SURFACE_COLOR, padx=12, pady=10, highlightbackground=BORDER_COLOR, highlightthickness=1)
        st_frame.pack(fill=tk.X, pady=(0, 10))

        lbl_hp = tk.Label(st_frame, text=f"Punti Ferita: {self.character.hp_current} / {self.character.hp_max}", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR)
        lbl_hp.pack(anchor="w")

        # HP Bar
        bar_bg = tk.Frame(st_frame, bg="#111827", height=12)
        bar_bg.pack(fill=tk.X, pady=(4, 8))
        ratio = max(0.0, min(1.0, self.character.hp_current / max(1, self.character.hp_max)))
        bar_fill = tk.Frame(bar_bg, bg=ACCENT_GREEN if ratio > 0.5 else ("#F59E0B" if ratio > 0.25 else ACCENT_RED), height=12)
        bar_fill.place(x=0, y=0, relwidth=ratio, relheight=1.0)

        cos_mod = (int(self.character.attributes.get("COS", 10)) - 10) // 2
        cos_str = f"+{cos_mod}" if cos_mod >= 0 else str(cos_mod)
        lbl_hd = tk.Label(st_frame, text=f"🎲 Dadi Vita: {self.character.hit_dice_current} / {self.character.hit_dice_total} ({self.character.hit_dice_type})  |  COS: {cos_str}", font=FONT_SMALL, bg=SURFACE_COLOR, fg=ACCENT_GOLD)
        lbl_hd.pack(anchor="w")

        # Roll Log
        tk.Label(container, text="Registro Tiri del Riposo:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(4, 2))
        log_box = tk.Text(container, height=8, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=("Consolas", 9), relief=tk.FLAT, padx=8, pady=6)
        log_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        log_box.insert(tk.END, "Inizio riposo breve. Clicca su 'Tira 1 Dado Vita' per curarti.\n")
        log_box.config(state=tk.DISABLED)

        spent_dice = []

        def update_dialog_ui():
            lbl_hp.config(text=f"Punti Ferita: {self.character.hp_current} / {self.character.hp_max}")
            r = max(0.0, min(1.0, self.character.hp_current / max(1, self.character.hp_max)))
            c = ACCENT_GREEN if r > 0.5 else ("#F59E0B" if r > 0.25 else ACCENT_RED)
            bar_fill.config(bg=c)
            bar_fill.place(x=0, y=0, relwidth=r, relheight=1.0)
            lbl_hd.config(text=f"🎲 Dadi Vita: {self.character.hit_dice_current} / {self.character.hit_dice_total} ({self.character.hit_dice_type})  |  COS: {cos_str}")
            self.hp_cur_var.set(self.character.hp_current)
            if self.character.hit_dice_current <= 0 or self.character.hp_current >= self.character.hp_max:
                btn_roll_one.config(state=tk.DISABLED)
                btn_roll_all.config(state=tk.DISABLED)

        def log_msg(msg_text):
            log_box.config(state=tk.NORMAL)
            log_box.insert(tk.END, msg_text + "\n")
            log_box.see(tk.END)
            log_box.config(state=tk.DISABLED)

        def roll_one():
            if self.character.hit_dice_current <= 0:
                messagebox.showinfo("Dadi Esauriti", "Non hai più Dadi Vita da spendere.", parent=win)
                return
            if self.character.hp_current >= self.character.hp_max:
                messagebox.showinfo("PF al Massimo", "I tuoi Punti Ferita sono già al massimo!", parent=win)
                return
            res = self.character.spend_hit_die_single()
            if res.get("success"):
                spent_dice.append(res)
                log_msg(f"• Tiro {len(spent_dice)}: {res['die']} ({res['roll']}) {cos_str} COS = +{res['healed']} PF (PF: {res['hp_current']}/{res['hp_max']})")
                update_dialog_ui()

        def roll_all():
            while self.character.hit_dice_current > 0 and self.character.hp_current < self.character.hp_max:
                res = self.character.spend_hit_die_single()
                if res.get("success"):
                    spent_dice.append(res)
                    log_msg(f"• Tiro {len(spent_dice)}: {res['die']} ({res['roll']}) {cos_str} COS = +{res['healed']} PF (PF: {res['hp_current']}/{res['hp_max']})")
            update_dialog_ui()

        def finish_rest():
            if not hasattr(self.character, "class_resources") or not isinstance(self.character.class_resources, dict):
                self.character.class_resources = {}
            self.character.class_resources["second_wind"] = True
            self.character.class_resources["action_surge"] = True
            for res in getattr(self.character, "custom_resources", []):
                if isinstance(res, dict) and res.get("reset_on") == "short":
                    res["current"] = res.get("max", 0)
            c_class = str(getattr(self.character, "char_class", "")).strip().lower()
            if "warlock" in c_class:
                for lvl, slot in getattr(self.character, "spell_slots", {}).items():
                    if isinstance(slot, dict) and "current" in slot:
                        slot["current"] = slot.get("max", 0)
                        if hasattr(self, "slot_vars") and str(lvl) in self.slot_vars:
                            v = self.slot_vars[str(lvl)]
                            if isinstance(v, dict) and "current" in v:
                                v["current"].set(slot["current"])
                            elif hasattr(v, "set"):
                                v.set(slot["current"])
            
            self.manager.update_character(self.character)
            if hasattr(self, "on_save_callback") and self.on_save_callback:
                try: self.on_save_callback(self.character)
                except Exception: pass
                
            tot_healed = sum(d.get("healed", 0) for d in spent_dice)
            if self.roll_callback:
                chat_msg = f"[RIPOSO BREVE] {self.character.name} conclude il riposo breve. Dadi spesi: {len(spent_dice)}. PF recuperati: +{tot_healed} (PF attuali: {self.character.hp_current}/{self.character.hp_max}, Dadi rimasti: {self.character.hit_dice_current}/{self.character.hit_dice_total})."
                self.roll_callback("0d0", chat_msg)
            win.destroy()

        btn_row = tk.Frame(container, bg=BG_COLOR)
        btn_row.pack(fill=tk.X, pady=(4, 0))

        btn_roll_one = ttk.Button(btn_row, text="🎲 Tira 1 Dado Vita", command=roll_one, style="Gold.TButton")
        btn_roll_one.pack(side=tk.LEFT, padx=(0, 6))

        btn_roll_all = ttk.Button(btn_row, text="⚡ Spendi Tutti", command=roll_all)
        btn_roll_all.pack(side=tk.LEFT, padx=(0, 6))

        btn_finish = ttk.Button(btn_row, text="✅ Concludi Riposo", command=finish_rest)
        btn_finish.pack(side=tk.RIGHT)
        win.protocol("WM_DELETE_WINDOW", finish_rest)


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
        if hasattr(self, "on_save_callback") and self.on_save_callback:
            try: self.on_save_callback(self.character)
            except Exception: pass
        if self.is_connected and getattr(self, "network", None):
            from common.protocol import make_update_stats_request, make_update_full_sheet_request, make_chat_message
            self.network.send(make_update_stats_request(self.character.hp_current, self.character.hp_max, self.character.initiative, getattr(self.character, "conditions", [])))
            self.network.send(make_update_full_sheet_request(self.character.to_dict()))
            self.network.send(make_chat_message(f"🎉 [PROGRESSIONE] {self.character.name} è salito al Livello {self.character.level}! (PF Max: {self.character.hp_max})"))



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
        add_w_txt = "+ Richiedi Arma" if self.is_connected else "+ Aggiungi Arma 🔒"
        btn_add_w = ttk.Button(bar, text=add_w_txt, command=self.open_add_weapon_dialog, style="Gold.TButton")
        btn_add_w.pack(side=tk.RIGHT)
        ToolTip(btn_add_w, "Invia richiesta al Master per una nuova arma" if self.is_connected else "L'aggiunta di armi richiede l'approvazione del Master in sessione")
        
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
            prop_str = str(w.get("properties", "")).lower()
            name_str = str(w.get("name", "")).lower()
            is_finesse = "accurat" in prop_str or "finesse" in prop_str or any(fn in name_str for fn in ["stocco", "rapier", "pugnale", "dagger", "scimitarra", "scimitar", "frusta", "whip"])
            if is_finesse and stat_key in ("FOR", "DES"):
                for_val = self.character.attributes.get("FOR", 10)
                des_val = self.character.attributes.get("DES", 10)
                stat_key = "DES" if des_val >= for_val else "FOR"
            stat_val = self.character.attributes.get(stat_key, 10)
            mod = (stat_val - 10) // 2
            char_lvl = getattr(self.character, "level", 1) or 1
            calc_pb = ((max(1, int(char_lvl)) - 1) // 4) + 2
            prof_bonus = calc_pb if w.get("proficient", True) else 0
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
            
            ammo_item, ammo_idx = self.character.find_ammunition(w.get("name", ""))
            if ammo_item:
                ammo_lbl = tk.Label(r3, text=f"🏹 Munizioni: {ammo_item.get('qty', 0)}x {ammo_item.get('name')}", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD)
                ammo_lbl.pack(side=tk.RIGHT, padx=4)
            
            r4 = tk.Frame(card, bg=SURFACE_COLOR)
            r4.pack(fill=tk.X)
            
            if ammo_item:
                btn_ammo = ttk.Button(r4, text=f"🏹 -1 {ammo_item.get('name')}", command=lambda a_idx=ammo_idx: self.spend_consumable(a_idx, 1), style="Gold.TButton")
                btn_ammo.pack(side=tk.LEFT, padx=(0, 4))
            
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
        if not self.is_connected:
            messagebox.showwarning(
                "Azione Non Consentita",
                "Non puoi aggiungere armi alla scheda autonomamente in modalità offline.\n\n"
                "L'assegnazione di nuove armi richiede l'approvazione del Dungeon Master durante una sessione di gioco.",
                parent=self
            )
            return
        def _on_save(w_data):
            if getattr(self, "request_item_callback", None):
                self.request_item_callback(w_data)
                messagebox.showinfo("Richiesta Inviata", f"Richiesta di aggiunta per l'arma '{w_data.get('name')}' inviata al Master per approvazione!", parent=self)
            else:
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
        if idx >= len(self.character.weapons):
            return
        w_name = self.character.weapons[idx].get("name", "Arma")
        if not self.is_connected:
            messagebox.showwarning(
                "Azione Non Consentita",
                f"Non puoi rimuovere '{w_name}' dalla scheda in modalità offline.\n\n"
                "La rimozione di armi ed equipaggiamento richiede sempre l'approvazione del Dungeon Master durante una sessione di gioco.",
                parent=self
            )
            return
            
        if not getattr(self, "request_item_callback", None):
            messagebox.showwarning("Non Consentito", "In sessione multiplayer la rimozione di armi richiede l'approvazione del Master.", parent=self)
            return
            
        if messagebox.askyesno("Richiesta Rimozione al Master", f"Vuoi inviare la richiesta di rimozione per l'arma '{w_name}' al Dungeon Master?", parent=self):
            sent = self.request_item_callback({"name": w_name, "action": "remove", "type": "Arma"})
            if sent:
                messagebox.showinfo("Richiesta Inviata", f"Richiesta di rimozione per '{w_name}' inviata al Master!", parent=self)

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
        
        ammo_item, ammo_idx = self.character.find_ammunition(weapon.get("name", ""), include_empty=True)
        ammo_note = ""
        if ammo_item:
            a_name = ammo_item.get("name", "Munizione")
            try:
                a_qty = int(ammo_item.get("qty", 1))
            except (ValueError, TypeError):
                a_qty = 1
            if a_qty > 0:
                ammo_item["qty"] = a_qty - 1
                ammo_note = f"\n🏹 Consumata 1x {a_name} (Rimanenti nello zaino: {ammo_item['qty']})."
                self.manager.save_characters()
                self.refresh_inventory_grid()
                self.refresh_weapons_list()
                if self.is_connected and getattr(self, "network", None):
                    from common.protocol import make_update_full_sheet_request, make_chat_message
                    self.network.send(make_update_full_sheet_request(self.character.to_dict()))
                    self.network.send(make_chat_message(f"[MUNIZIONI] {self.character.name} ha consumato 1x {a_name} per l'attacco (Rimanenti: {ammo_item['qty']})."))
            else:
                messagebox.showwarning("Munizioni Esaurite", f"⚠️ Non hai più {a_name} nello zaino per attaccare con {w_name}!", parent=self)
                return

        adv_text = f" ({adv_state})" if adv_state not in ("Normale", _t("adv_normal"), "") else ""
        
        if is_crit:
            msg = f"⚔️ {self.character.name} attacca con {w_name}{adv_text}: [d20: {rolls_str}] {txc_sign} = {total} 🌟 COLPO CRITICO (20 Naturale)!"
            messagebox.showinfo("COLPO CRITICO!", f"🌟 COLPO CRITICO!\nUn 20 Naturale con {w_name}!\nIl prossimo tiro dei danni raddoppierà automaticamente i dadi!")
        elif is_fail:
            msg = f"⚔️ {self.character.name} attacca con {w_name}{adv_text}: [d20: {rolls_str}] {txc_sign} = {total} 💀 FALLIMENTO CRITICO (1 Naturale)! Mancato automatico!"
            messagebox.showwarning("FALLIMENTO CRITICO!", f"💀 FALLIMENTO CRITICO!\nUn 1 Naturale con {w_name}: l'attacco manca automaticamente il bersaglio!")
        else:
            msg = f"⚔️ {self.character.name} attacca con {w_name}{adv_text}: [d20: {rolls_str}] {txc_sign} = {total}"
            
        msg += ammo_note
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

    def create_markdown_journal_tab(self, parent_frame, field_name, title, subtitle):
        hdr = tk.Frame(parent_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=6)
        hdr.pack(fill=tk.X, pady=(0, 4))
        
        left_box = tk.Frame(hdr, bg=SURFACE_COLOR)
        left_box.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(left_box, text=title, font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
        tk.Label(left_box, text=subtitle, font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w")
        
        btn_box = tk.Frame(hdr, bg=SURFACE_COLOR)
        btn_box.pack(side=tk.RIGHT)
        
        if self.is_connected:
            badge = tk.Label(btn_box, text="🔒 Approvazione DM Attiva", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD, padx=6, pady=2)
            badge.pack(side=tk.LEFT, padx=4)
            
            btn_prop = ttk.Button(btn_box, text="📤 Proponi al Master", command=lambda f=field_name, t=title: self.propose_text_field_approval(f, t), style="Gold.TButton")
            btn_prop.pack(side=tk.LEFT, padx=3)
        else:
            btn_save = ttk.Button(btn_box, text="💾 Salva Modifiche", command=lambda f=field_name: self.save_text_field_offline(f), style="Success.TButton")
            btn_save.pack(side=tk.LEFT, padx=3)
            
        btn_toggle = ttk.Button(btn_box, text="✏️ Modifica Testo")
        btn_toggle.pack(side=tk.LEFT, padx=3)

        if field_name == "journal_notes":
            btn_gen = ttk.Button(btn_box, text="✨ Genera Storia", command=self._generate_character_backstory, style="Gold.TButton")
            btn_gen.pack(side=tk.LEFT, padx=3)
        
        body_container = tk.Frame(parent_frame, bg=SURFACE_COLOR)
        body_container.pack(fill=tk.BOTH, expand=True)
        
        preview_box = scrolledtext.ScrolledText(body_container, wrap=tk.WORD, font=FONT_MAIN, bg=SURFACE_COLOR, fg=TEXT_COLOR, padx=8, pady=8, highlightbackground=BORDER_COLOR, highlightthickness=1)
        configure_markdown_tags(preview_box)
        preview_box.config(state="disabled")
        
        edit_box = scrolledtext.ScrolledText(body_container, wrap=tk.WORD, font=FONT_MAIN, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, padx=8, pady=8, highlightbackground=BORDER_COLOR, highlightthickness=1)
        
        self.text_widgets[field_name] = edit_box
        
        widgets_bundle = {
            "preview": preview_box,
            "edit": edit_box,
            "btn_toggle": btn_toggle,
            "mode": "preview"
        }
        self._markdown_widgets[field_name] = widgets_bundle
        
        def _toggle_mode():
            cur_mode = widgets_bundle["mode"]
            if cur_mode == "preview":
                preview_box.pack_forget()
                edit_box.pack(fill=tk.BOTH, expand=True)
                btn_toggle.config(text="👁️ Vista Formattata (Markdown)")
                widgets_bundle["mode"] = "edit"
                edit_box.focus_set()
            else:
                content = edit_box.get("1.0", tk.END).strip()
                render_markdown_to_widget(preview_box, content)
                edit_box.pack_forget()
                preview_box.pack(fill=tk.BOTH, expand=True)
                btn_toggle.config(text="✏️ Modifica Testo")
                widgets_bundle["mode"] = "preview"
                
        btn_toggle.config(command=_toggle_mode)
        preview_box.pack(fill=tk.BOTH, expand=True)

    def create_journal_tab(self, parent_frame):
        self.create_markdown_journal_tab(
            parent_frame, 
            field_name="journal_notes",
            title="📖 Biografia & Diario del Personaggio",
            subtitle="Storia, legami, ideali, segreti e cronaca di viaggio (supporta Markdown #, ##, **, *, •)"
        )

    def _generate_character_backstory(self):
        from common.backgrounds_data import generate_backstory
        edit_box = self.text_widgets.get("journal_notes")
        if not edit_box:
            return
        cur_content = edit_box.get("1.0", tk.END).strip()
        if cur_content:
            if not messagebox.askyesno("Conferma Generazione Storia", "Il diario contiene già del testo. Vuoi comporre e inserire la biografia narrativa ufficiale D&D 5e basata su razza, classe, background e tratti del tuo eroe?", parent=self):
                return
        story = generate_backstory(
            name=self.character.name,
            race=getattr(self.character, "race", "Umano"),
            char_class=getattr(self.character, "char_class", "Guerriero"),
            background=getattr(self.character, "background", "Accolito"),
            origin_place=getattr(self.character, "origin_place", "Terre d'Origine"),
            trait=getattr(self.character, "personality_trait", ""),
            ideal=getattr(self.character, "ideal", ""),
            bond=getattr(self.character, "bond", ""),
            flaw=getattr(self.character, "flaw", ""),
            quest=getattr(self.character, "personal_quest", ""),
            secret=getattr(self.character, "secret", ""),
            party_tie=getattr(self.character, "party_tie", ""),
            trinket=getattr(self.character, "trinket", ""),
            include_headers=True
        )
        edit_box.delete("1.0", tk.END)
        edit_box.insert("1.0", story)
        self.save_text_field_offline("journal_notes")
        messagebox.showinfo("Storia Creata", "Biografia narrativa generata con successo e salvata nel Diario del Personaggio!", parent=self)

    def create_notes_tab(self, parent_frame):
        self.create_markdown_journal_tab(
            parent_frame, 
            field_name="notes",
            title="📝 Appunti di Sessione & Note Rapide",
            subtitle="Indizi, promesse, PNG incontrati, mappe e appunti tattici (supporta Markdown #, ##, **, *)"
        )

    def propose_text_field_approval(self, field_name, field_title):
        if not self.is_connected:
            messagebox.showinfo("Offline", "Questa funzione è disponibile solo se connesso a una sessione multiplayer con il Master.", parent=self)
            return
        if field_name not in self.text_widgets:
            return
        content = self.text_widgets[field_name].get("1.0", tk.END).strip()
        init_val = self._initial_text_fields.get(field_name, getattr(self.character, field_name, "")).strip()
        if content == init_val:
            messagebox.showinfo("Nessuna Modifica", "Non hai apportato alcuna modifica rispetto alla versione attuale salvata.", parent=self)
            return
        if self.request_journal_approval_callback:
            sent = self.request_journal_approval_callback(field_name, content, f"Modifica {field_title}")
            if sent:
                messagebox.showinfo("Richiesta Inviata", f"Le modifiche a '{field_title}' sono state inviate al Master per approvazione!\nRiceverai una notifica quando il Master le approverà.", parent=self)

    def save_text_field_offline(self, field_name):
        if field_name not in self.text_widgets:
            return
        content = self.text_widgets[field_name].get("1.0", tk.END).strip()
        setattr(self.character, field_name, content)
        self.manager.save_characters()
        bundle = self._markdown_widgets.get(field_name)
        if bundle:
            render_markdown_to_widget(bundle["preview"], content)
        messagebox.showinfo("Salvataggio", "Modifiche salvate con successo nella scheda del personaggio!", parent=self)

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


class CharacterSheetUI(tk.Toplevel):
    """
    Finestra modale / fluttuante per la Scheda Personaggio (retrocompatibile al 100%).
    Incapsula CharacterSheetFrame delegando attributi e metodi, supportando al contempo
    il riaggancio alla finestra principale (on_dock_callback).
    """
    def __init__(
        self, 
        master, 
        character, 
        manager, 
        on_save_callback=None, 
        roll_callback=None, 
        trade_callback=None, 
        give_gold_callback=None, 
        players_list_callback=None, 
        attack_callback=None, 
        long_rest_callback=None, 
        custom_spell_request_callback=None, 
        request_currency_callback=None, 
        request_item_callback=None, 
        is_connected=False, 
        request_journal_approval_callback=None,
        on_dock_callback=None,
        network=None
    ):
        super().__init__(master)
        self.title(f"{_t('sheet_title')} - {character.name}")
        self.minsize(700, 700)
        apply_modern_window_style(self)
        self.on_dock_callback = on_dock_callback
        self.network = network

        self._sheet_frame_internal = CharacterSheetFrame(
            self,
            character=character,
            manager=manager,
            on_save_callback=on_save_callback,
            roll_callback=roll_callback,
            trade_callback=trade_callback,
            give_gold_callback=give_gold_callback,
            players_list_callback=players_list_callback,
            attack_callback=attack_callback,
            long_rest_callback=long_rest_callback,
            custom_spell_request_callback=custom_spell_request_callback,
            request_currency_callback=request_currency_callback,
            request_item_callback=request_item_callback,
            is_connected=is_connected,
            request_journal_approval_callback=request_journal_approval_callback,
            on_close_callback=self.destroy,
            on_dock_callback=self._handle_dock if on_dock_callback else None,
            is_overlay=False,
            network=network
        )
        self._sheet_frame_internal.pack(fill=tk.BOTH, expand=True)

    def _handle_dock(self):
        if hasattr(self, "_sheet_frame_internal") and self._sheet_frame_internal.winfo_exists():
            self._sheet_frame_internal.save_character(close_after=False)
        cb = self.on_dock_callback
        self.destroy()
        if cb:
            cb()

    @property
    def sheet_frame(self):
        return self._sheet_frame_internal

    def destroy(self):
        try:
            super().destroy()
        except (tk.TclError, Exception):
            pass

    def __getattr__(self, name):
        if name in ("_tclCommands", "_w", "_name", "tk", "master", "children"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        if "_sheet_frame_internal" in self.__dict__ and hasattr(self.__dict__["_sheet_frame_internal"], name):
            return getattr(self.__dict__["_sheet_frame_internal"], name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name in ("_sheet_frame_internal", "on_dock_callback") or "_sheet_frame_internal" not in self.__dict__:
            super().__setattr__(name, value)
        elif hasattr(self.__dict__["_sheet_frame_internal"], name):
            setattr(self.__dict__["_sheet_frame_internal"], name, value)
        else:
            super().__setattr__(name, value)


CharacterSheetUI.open_export_character_dialog = CharacterSheetFrame.open_export_character_dialog
CharacterSheetUI._generate_character_html = CharacterSheetFrame._generate_character_html


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

