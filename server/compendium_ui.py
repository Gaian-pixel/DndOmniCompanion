# server/compendium_ui.py
"""
Modulo UI per la consultazione e l'importazione rapida di risorse 5e SRD e Manuali PDF.
Implementa una Split View (Master-Detail) con:
- Lista elementi filtrabile per Categoria, Ricerca, Grado di Sfida (CR), Tipo creatura e Rarità.
- Statblock Card 5e Dark Fantasy interattiva in tempo reale.
- Supporto a compendi online (dnd5eapi), compendi offline (Open5e, Creature Codex, Tome of Beasts)
  e importazione/consultazione diretta dai manuali PDF (PHB, DMG, MM, TCoE, XGtE e custom).
"""

import tkinter as tk
from tkinter import ttk, filedialog
import urllib.request
import json
import threading
import os
import shutil
import re
from typing import Optional, Callable, Dict, Any, List, Tuple

from common.messagebox import messagebox
from common.theme import (
    apply_modern_window_style, SURFACE_COLOR, SURFACE_COLOR_ALT, BORDER_COLOR, TEXT_COLOR, TEXT_MUTED,
    FONT_MAIN, FONT_BOLD, FONT_SMALL, FONT_HEADER, BG_COLOR, ACCENT_GOLD
)
from server.compendium_manager import CompendiumManager
from components.statblock_view import StatblockCardView
from common.srd_offline import (
    match_monster_cr,
    match_monster_type,
    match_item_rarity,
    match_item_type,
    match_spell_level,
    match_spell_school,
    get_monster_offline,
    get_all_monsters_offline,
    get_all_spells_offline,
    get_all_magic_items_offline,
    get_all_equipment_offline,
    get_all_rules_offline,
    get_all_classes_offline,
    get_all_traits_offline,
    get_bilingual_label,
    match_bilingual_search,
    parse_cr_to_float,
)
from common.pdf_manuals_indexer import PDFManualsIndexer, PDF_DIR


class CompendiumTreeList(ttk.Treeview):
    """
    Tabella multi-colonna ordinabile (Nome, Dettaglio, Tipo/Scuola, Fonte)
    che mantiene il 100% di retrocompatibilità con l'API di tk.Listbox
    (delete, insert, curselection, selection_set, selection_clear, get, size).
    """

    def __init__(self, master, on_sort_column: Optional[Callable[[str], None]] = None, **kwargs):
        # Filtra argomenti specifici di tk.Listbox non accettati da ttk.Treeview
        for k in ("font", "selectbackground", "selectforeground", "activestyle", "width"):
            kwargs.pop(k, None)
        height = kwargs.pop("height", 16)
        super().__init__(
            master,
            columns=("name", "detail", "type", "source"),
            show="headings",
            selectmode="browse",
            height=height,
            **kwargs,
        )
        self._row_labels: List[str] = []
        self._on_sort_column = on_sort_column

        self.heading("name", text="Nome (IT/EN)", anchor="w", command=lambda: self._trigger_sort("name"))
        self.heading("detail", text="CR / Liv / Rar", anchor="center", command=lambda: self._trigger_sort("detail"))
        self.heading("type", text="Tipo / Scuola", anchor="w", command=lambda: self._trigger_sort("type"))
        self.heading("source", text="Fonte", anchor="center", command=lambda: self._trigger_sort("source"))

        self.column("name", width=185, minwidth=120, anchor="w", stretch=True)
        self.column("detail", width=80, minwidth=55, anchor="center", stretch=False)
        self.column("type", width=95, minwidth=65, anchor="w", stretch=False)
        self.column("source", width=62, minwidth=45, anchor="center", stretch=False)

    def _trigger_sort(self, col: str):
        if self._on_sort_column:
            self._on_sort_column(col)

    def update_sort_indicator(self, active_col: Optional[str], desc: bool):
        titles = {
            "name": "Nome (IT/EN)",
            "detail": "CR / Liv / Rar",
            "type": "Tipo / Scuola",
            "source": "Fonte",
        }
        arrow = " ▼" if desc else " ▲"
        for col, base_t in titles.items():
            self.heading(col, text=f"{base_t}{arrow}" if col == active_col else base_t)

    # --- Metodi compatibili con tk.Listbox ---
    def delete(self, first=0, last=None):
        if first == 0 and (last == tk.END or last == "end" or last is None):
            self._row_labels.clear()
            children = self.get_children()
            if children:
                super().delete(*children)
        else:
            try:
                super().delete(str(first))
            except Exception:
                pass

    def insert(self, index, text: str, values: Optional[Tuple[str, str, str, str]] = None, tags: Tuple[str, ...] = ()):
        iid = str(len(self._row_labels))
        self._row_labels.append(str(text))
        row_vals = values if values is not None else (str(text), "", "", "")
        super().insert("", tk.END, iid=iid, values=row_vals, tags=tags)
        return iid

    def curselection(self) -> Tuple[int, ...]:
        sel = super().selection()
        return tuple(int(s) if str(s).isdigit() else s for s in sel)

    def selection_clear(self, first=0, last=None):
        sel = super().selection()
        if sel:
            super().selection_remove(*sel)

    def selection_set(self, *items):
        children = set(self.get_children())
        valid = [str(x) for x in items if str(x) in children]
        if valid:
            super().selection_set(valid)

    def get(self, first, last=None) -> str:
        try:
            idx = int(first)
            if 0 <= idx < len(self._row_labels):
                return self._row_labels[idx]
        except (ValueError, TypeError):
            pass
        return ""

    def size(self) -> int:
        return len(self._row_labels)

    def bind(self, sequence=None, func=None, add=None):
        if sequence == "<<ListboxSelect>>":
            return super().bind("<<TreeviewSelect>>", func, add=add)
        return super().bind(sequence, func, add=add)



class CompendiumDialog(tk.Toplevel):
    """Finestra Compendio 5e con Split View, Tabella Ordinabile, Ricerca Bilingue/Globale e Statblock Interattivo."""

    GLOBAL_CATEGORY = "🌐 Tutte le Categorie (Ricerca Globale)"
    FAVORITES_CATEGORY = "⭐ Preferiti"
    RECENT_CATEGORY = "🕒 Consultati di Recente"

    def __init__(self, master, on_import_callback: Optional[Callable] = None, is_dm: bool = True, initial_category: Optional[str] = None, action_label: Optional[str] = None, monsters_only: bool = False, allowed_categories: Optional[List[str]] = None):
        super().__init__(master)
        self.on_import_callback = on_import_callback
        self.is_dm = is_dm
        self.initial_category = initial_category
        self.action_label = action_label
        self.monsters_only = monsters_only
        self.allowed_categories = allowed_categories

        if self.monsters_only:
            self.title("Compendio Avversari 5e SRD & Manuali PDF • Mostri e PNG")
        else:
            self.title("Compendio 5e SRD & Manuali PDF • Consultazione & Importazione")
        self.minsize(1060, 700)
        self.geometry("1160x760")
        self.transient(master)
        apply_modern_window_style(self)

        self.base_url = "https://www.dnd5eapi.co/api"
        self.current_items: List[Dict[str, Any]] = []
        self.displayed_items: List[Dict[str, Any]] = []
        self.compendium_manager = CompendiumManager()
        self.pdf_indexer = PDFManualsIndexer()

        # Stato ordinamento colonne tabella
        self.sort_col: Optional[str] = None
        self.sort_desc: bool = False

        # Cache dettagli recuperati per evitare refetch ripetuti
        self._item_details_cache: Dict[str, Dict[str, Any]] = {}

        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "srd_data")
        self.offline_compendiums: Dict[str, str] = {}

        self.setup_ui()
        self.fetch_list()

    def _build_category_list(self) -> List[str]:
        if getattr(self, "monsters_only", False):
            # In modalità creazione incontro: solo categorie pertinenti a Mostri e NPC
            categories = [
                "Mostri",
                "PNG",
                self.FAVORITES_CATEGORY,
                self.RECENT_CATEGORY,
            ]

            try:
                from server.srd_downloader import DOWNLOADABLE_COMPENDIUMS
                for comp in DOWNLOADABLE_COMPENDIUMS:
                    path = os.path.join(self.data_dir, comp["filename"])
                    if os.path.exists(path):
                        ctype = str(comp.get("type", "")).lower()
                        cname = str(comp.get("name", "")).lower()
                        if ctype == "mostri" or any(k in cname for k in ["mostr", "creature", "beast", "tome of beasts", "npc", "png"]):
                            name = f"[OFFLINE] {comp['name']}"
                            categories.append(name)
                            self.offline_compendiums[name] = path
            except ImportError:
                pass

            pdf_cats = [
                "📖 [PDF] Monster Manual (Mostri)",
                "📖 [PDF] Mostri & PNG dai Manuali",
            ]

            try:
                for f in self.pdf_indexer.get_pdf_files():
                    fn_clean = os.path.splitext(f)[0].replace("_", " ")
                    custom_cat = f"📖 [PDF] {fn_clean}"
                    low = custom_cat.lower()
                    if any(known in low for known in ["monster manual", "players handbook", "player's handbook", "dungeon master", "tasha", "xanathar"]):
                        continue
                    if any(k in low for k in ["mostr", "monster", "creatur", "bestiar", "npc", "png"]):
                        if custom_cat not in pdf_cats:
                            pdf_cats.append(custom_cat)
            except Exception:
                pass

            all_cats = categories + pdf_cats
            if getattr(self, "allowed_categories", None):
                allowed_low = [a.lower() for a in self.allowed_categories]
                all_cats = [c for c in all_cats if any(a in c.lower() for a in allowed_low)]
            return all_cats or ["Mostri"]

        base_cats = ["Incantesimi", "Regole", "Classi", "Tratti", "Equipaggiamento", "Armi", "Pozioni", "Oggetti Magici"]
        if self.is_dm:
            base_cats = ["Mostri", "PNG"] + base_cats

        categories = [
            self.GLOBAL_CATEGORY,
            self.FAVORITES_CATEGORY,
            self.RECENT_CATEGORY,
        ] + base_cats

        # Rileva compendi offline scaricati
        try:
            from server.srd_downloader import DOWNLOADABLE_COMPENDIUMS
            for comp in DOWNLOADABLE_COMPENDIUMS:
                path = os.path.join(self.data_dir, comp["filename"])
                if os.path.exists(path):
                    name = f"[OFFLINE] {comp['name']}"
                    categories.append(name)
                    self.offline_compendiums[name] = path
        except ImportError:
            pass

        # Categorie PDF Manuali
        pdf_cats = [
            "📖 [PDF] Tutti i Manuali (Indice Completo)",
            "📖 [PDF] Monster Manual (Mostri)",
            "📖 [PDF] Player's Handbook (PHB 2024)",
            "📖 [PDF] Dungeon Master's Guide (DMG 2024)",
            "📖 [PDF] Tasha's Cauldron of Everything",
            "📖 [PDF] Xanathar's Guide to Everything",
            "📖 [PDF] Mostri & PNG dai Manuali",
            "📖 [PDF] Incantesimi dai Manuali",
            "📖 [PDF] Equipaggiamento & Tesori",
            "📖 [PDF] Regole & Meccaniche DM",
        ]

        # Includi eventuali altri PDF personalizzati presenti in manuals_pdf/
        try:
            for f in self.pdf_indexer.get_pdf_files():
                fn_clean = os.path.splitext(f)[0].replace("_", " ")
                custom_cat = f"📖 [PDF] {fn_clean}"
                if not any(known in custom_cat.lower() for known in ["monster manual", "players handbook", "player's handbook", "dungeon master", "tasha", "xanathar"]):
                    if custom_cat not in pdf_cats:
                        pdf_cats.append(custom_cat)
        except Exception:
            pass

        all_cats = categories + pdf_cats
        if getattr(self, "allowed_categories", None):
            allowed_low = [a.lower() for a in self.allowed_categories]
            all_cats = [c for c in all_cats if any(a in c.lower() for a in allowed_low)]
        return all_cats

    def _switch_quick_category(self, target_cat: str):
        values = list(self.category_cb["values"])
        if target_cat in values:
            self.category_var.set(target_cat)
            self._on_category_changed()

    def setup_ui(self):
        # Master-Detail PanedWindow
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # -------------------------------------------------------------
        # PANNELLO SINISTRO (Tabella Multi-Colonna, Ricerca & Filtri)
        # -------------------------------------------------------------
        left_panel = ttk.Frame(self.paned, padding="8")
        self.paned.add(left_panel, weight=0)

        # 1. Categoria + Pulsanti Rapidi (Globale, Preferiti, Recenti)
        cat_frame = ttk.Frame(left_panel)
        cat_frame.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(cat_frame, text="Categoria:", font=FONT_BOLD).pack(side=tk.LEFT, padx=(0, 4))
        self.category_var = tk.StringVar()

        categories = self._build_category_list()
        self.category_cb = ttk.Combobox(cat_frame, textvariable=self.category_var, values=categories, state="readonly", width=32)
        self.category_cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.category_cb.bind("<<ComboboxSelected>>", self._on_category_changed)

        if self.initial_category:
            matched = None
            for c in categories:
                if c.lower() == self.initial_category.lower() or self.initial_category.lower() in c.lower():
                    matched = c
                    break
            self.category_var.set(matched or categories[0])
        elif getattr(self, "monsters_only", False) or self.is_dm:
            self.category_var.set("Mostri")
        else:
            self.category_var.set("Incantesimi")

        # Barra scorciatoie rapide (Ricerca Globale, Preferiti, Recenti)
        quick_nav = ttk.Frame(left_panel)
        quick_nav.pack(fill=tk.X, pady=(0, 6))
        if not getattr(self, "monsters_only", False):
            ttk.Button(
                quick_nav,
                text="🌐 Tutto il Compendio",
                command=lambda: self._switch_quick_category(self.GLOBAL_CATEGORY),
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        ttk.Button(
            quick_nav,
            text="⭐ Preferiti",
            command=lambda: self._switch_quick_category(self.FAVORITES_CATEGORY),
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        ttk.Button(
            quick_nav,
            text="🕒 Recenti",
            command=lambda: self._switch_quick_category(self.RECENT_CATEGORY),
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 2. Contenitore Filtri Rapidi Contestuali
        self.filter_frame = ttk.LabelFrame(left_panel, text="Filtri Rapidi", padding="6")
        self.filter_frame.pack(fill=tk.X, pady=(0, 6))

        # Variabili filtri
        self.cr_filter_var = tk.StringVar(value="Tutti i CR")
        self.type_filter_var = tk.StringVar(value="Tutti i Tipi")
        self.rarity_filter_var = tk.StringVar(value="Tutte le Rarità")
        self.item_type_filter_var = tk.StringVar(value="Tutti i Tipi")
        self.spell_level_filter_var = tk.StringVar(value="Tutti i Livelli")
        self.spell_school_filter_var = tk.StringVar(value="Tutte le Scuole")

        self.filter_widgets = []
        self._update_filter_bar()

        # 3. Casella di ricerca bilingue (IT / EN) con pulsante pulizia
        search_frame = ttk.Frame(left_panel)
        search_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(search_frame, text="🔍 Cerca (IT/EN):", font=FONT_BOLD).pack(side=tk.LEFT, padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.update_listbox())
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            search_frame,
            text="✕",
            width=3,
            command=lambda: self.search_var.set(""),
        ).pack(side=tk.LEFT, padx=(3, 0))

        # 4. Tabella Multi-Colonna Ordinabile (CompendiumTreeList con API compatibile Listbox)
        list_container = ttk.Frame(left_panel)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.list_scroll = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        self.listbox = CompendiumTreeList(
            list_container,
            on_sort_column=self._on_sort_column,
            yscrollcommand=self.list_scroll.set,
            height=16,
        )
        self.list_scroll.config(command=self.listbox.yview)

        self.list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.listbox.bind("<<ListboxSelect>>", self._on_item_selected)
        self.listbox.bind("<Double-Button-1>", lambda e: self.import_selected())

        # 5. Status bar sinistra
        self.status_var = tk.StringVar(value="Pronto.")
        ttk.Label(left_panel, textvariable=self.status_var, font=FONT_SMALL, foreground=TEXT_MUTED).pack(fill=tk.X, pady=(0, 4))

        # 6. Bottoni inferiori su 2 righe ordinate (nessun taglio orizzontale)
        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(fill=tk.X)

        row_tools = ttk.Frame(btn_frame)
        row_tools.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(row_tools, text="📂 Importa PDF...", command=self.import_pdf_manual).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        ttk.Button(row_tools, text="🔄 Reindicizza PDF", command=self.reindex_pdf_manuals).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        ttk.Button(row_tools, text="🌐 Scarica SRD", command=self.open_downloader).pack(side=tk.LEFT, fill=tk.X, expand=True)

        row_actions = ttk.Frame(btn_frame)
        row_actions.pack(fill=tk.X)
        if self.is_dm:
            ttk.Button(row_actions, text="➕ Nuovo Custom", command=self.create_custom_item).pack(side=tk.LEFT, padx=(0, 3))
            ttk.Button(row_actions, text="✏️ Modifica", command=self.edit_selected_custom_item).pack(side=tk.LEFT, padx=(0, 3))
            ttk.Button(row_actions, text="🗑️ Elimina", command=self.delete_selected_custom_item, style="Danger.TButton").pack(side=tk.LEFT, padx=(0, 3))
        if self.on_import_callback:
            import_btn_label = self.action_label or "➕ Importa Selezionato"
            ttk.Button(row_actions, text=import_btn_label, command=self.import_selected, style="Gold.TButton").pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # -------------------------------------------------------------
        # PANNELLO DESTRO (Statblock Card 5e Interattivo)
        # -------------------------------------------------------------
        right_panel = ttk.Frame(self.paned)
        self.paned.add(right_panel, weight=1)

        action_txt = self.action_label or ("Schiera sulla Mappa" if self.is_dm else "Aggiungi al Personaggio")
        self.statblock_view = StatblockCardView(
            right_panel,
            on_primary_action=self._on_statblock_action,
            action_label=action_txt,
            on_toggle_favorite=self._on_toggle_favorite,
            is_favorite_fn=self.compendium_manager.is_favorite,
            on_edit_custom=self.edit_custom_item,
            on_delete_custom=self.delete_custom_item,
        )
        self.statblock_view.pack(fill=tk.BOTH, expand=True)

    # -------------------------------------------------------------------------
    # GESTIONE FILTRI RAPIDI & ORDINAMENTO COLONNE
    # -------------------------------------------------------------------------
    def _on_sort_column(self, col: str):
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col
            self.sort_desc = False
        self.listbox.update_sort_indicator(self.sort_col, self.sort_desc)
        self.update_listbox()

    def _on_toggle_favorite(self, item_data: Dict[str, Any], category: str) -> bool:
        now_fav = self.compendium_manager.toggle_favorite(item_data, category or self.category_var.get())
        if self.category_var.get() == self.FAVORITES_CATEGORY:
            self.fetch_list()
        return now_fav

    def _on_category_changed(self, event=None):
        self._update_filter_bar()
        self.fetch_list()

    def _update_filter_bar(self):
        for w in self.filter_widgets:
            w.destroy()
        self.filter_widgets.clear()

        cat = self.category_var.get()
        is_monster_cat = "mostri" in cat.lower() or "png" in cat.lower() or "npc" in cat.lower() or "creature" in cat.lower() or "tome of beasts" in cat.lower() or "monster manual" in cat.lower()
        is_item_cat = any(k in cat.lower() for k in ["oggetti", "equipaggiamento", "armi", "pozioni", "magic-item", "tesor"])
        is_spell_cat = "incantesimi" in cat.lower() or "spell" in cat.lower()

        if is_monster_cat:
            r1 = ttk.Frame(self.filter_frame)
            r1.pack(fill=tk.X, pady=2)
            self.filter_widgets.append(r1)

            ttk.Label(r1, text="CR:", font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 2))
            cr_vals = ["Tutti i CR", "CR 0 - 1/2", "CR 1 - 4", "CR 5 - 9", "CR 10 - 14", "CR 15 - 19", "CR 20+"]
            cb_cr = ttk.Combobox(r1, textvariable=self.cr_filter_var, values=cr_vals, state="readonly", width=12)
            cb_cr.pack(side=tk.LEFT, padx=(0, 6))
            cb_cr.bind("<<ComboboxSelected>>", lambda e: self.update_listbox())

            ttk.Label(r1, text="Tipo:", font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 2))
            type_vals = [
                "Tutti i Tipi", "Aberrazione", "Bestia", "Celestiale", "Costrutto", "Drago",
                "Elementale", "Fata", "Gigante", "Immondo", "Melma", "Mostruosità", "Non Morto", "Pianta", "Umanoide"
            ]
            cb_type = ttk.Combobox(r1, textvariable=self.type_filter_var, values=type_vals, state="readonly", width=14)
            cb_type.pack(side=tk.LEFT, fill=tk.X, expand=True)
            cb_type.bind("<<ComboboxSelected>>", lambda e: self.update_listbox())

        elif is_item_cat:
            r1 = ttk.Frame(self.filter_frame)
            r1.pack(fill=tk.X, pady=2)
            self.filter_widgets.append(r1)

            ttk.Label(r1, text="Rarità:", font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 2))
            rar_vals = ["Tutte le Rarità", "Comune", "Non Comune", "Raro", "Molto Raro", "Leggendario", "Artefatto"]
            cb_rar = ttk.Combobox(r1, textvariable=self.rarity_filter_var, values=rar_vals, state="readonly", width=13)
            cb_rar.pack(side=tk.LEFT, padx=(0, 6))
            cb_rar.bind("<<ComboboxSelected>>", lambda e: self.update_listbox())

            ttk.Label(r1, text="Tipo:", font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 2))
            item_types = ["Tutti i Tipi", "Arma", "Armatura", "Pozione", "Pergamena", "Bacchetta", "Anello", "Meraviglioso"]
            cb_it = ttk.Combobox(r1, textvariable=self.item_type_filter_var, values=item_types, state="readonly", width=13)
            cb_it.pack(side=tk.LEFT, fill=tk.X, expand=True)
            cb_it.bind("<<ComboboxSelected>>", lambda e: self.update_listbox())

        elif is_spell_cat:
            r1 = ttk.Frame(self.filter_frame)
            r1.pack(fill=tk.X, pady=2)
            self.filter_widgets.append(r1)

            ttk.Label(r1, text="Livello:", font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 2))
            lvl_vals = ["Tutti i Livelli", "Trucchetto (Liv 0)", "Livello 1", "Livello 2", "Livello 3", "Livello 4", "Livello 5", "Livello 6", "Livello 7", "Livello 8", "Livello 9"]
            cb_lvl = ttk.Combobox(r1, textvariable=self.spell_level_filter_var, values=lvl_vals, state="readonly", width=14)
            cb_lvl.pack(side=tk.LEFT, padx=(0, 6))
            cb_lvl.bind("<<ComboboxSelected>>", lambda e: self.update_listbox())

            ttk.Label(r1, text="Scuola:", font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 2))
            school_vals = ["Tutte le Scuole", "Abiurazione", "Ammaliamento", "Divinazione", "Evocazione", "Illusione", "Invocazione", "Necromanzia", "Trasmutazione"]
            cb_sch = ttk.Combobox(r1, textvariable=self.spell_school_filter_var, values=school_vals, state="readonly", width=14)
            cb_sch.pack(side=tk.LEFT, fill=tk.X, expand=True)
            cb_sch.bind("<<ComboboxSelected>>", lambda e: self.update_listbox())

        else:
            r1 = ttk.Frame(self.filter_frame)
            r1.pack(fill=tk.X, pady=2)
            self.filter_widgets.append(r1)
            ttk.Label(
                r1,
                text="💡 Clicca sulle intestazioni della tabella per ordinare per Nome, CR/Livello o Fonte.",
                font=FONT_SMALL,
                foreground=TEXT_MUTED,
            ).pack(side=tk.LEFT)

    # -------------------------------------------------------------------------
    # CARICAMENTO DATI OFFLINE-FIRST & IBRIDO (0ms + PDF + CUSTOM)
    # -------------------------------------------------------------------------
    def _load_offline_category_items(self, cat: str) -> Optional[List[Dict[str, Any]]]:
        """Carica istantaneamente in 0ms i dati locali completi per la categoria richiesta."""
        if cat == self.FAVORITES_CATEGORY:
            return self.compendium_manager.get_favorites(monsters_only=getattr(self, "monsters_only", False))
        if cat == self.RECENT_CATEGORY:
            return self.compendium_manager.get_recent(monsters_only=getattr(self, "monsters_only", False))
        if cat == self.GLOBAL_CATEGORY:
            merged: List[Dict[str, Any]] = []
            if self.is_dm:
                for m in get_all_monsters_offline():
                    mc = dict(m)
                    mc.setdefault("category", "Mostri")
                    merged.append(mc)
            for s in get_all_spells_offline():
                sc = dict(s)
                sc.setdefault("category", "Incantesimi")
                merged.append(sc)
            for eq in get_all_equipment_offline("Equipaggiamento"):
                ec = dict(eq)
                ec.setdefault("category", "Equipaggiamento")
                merged.append(ec)
            for r in get_all_rules_offline():
                merged.append(r)
            for cl in get_all_classes_offline():
                merged.append(cl)
            return merged

        if cat == "Mostri":
            items = get_all_monsters_offline()
            return items if items else None
        if cat == "Incantesimi":
            items = get_all_spells_offline()
            return items if items else None
        if cat == "Oggetti Magici":
            items = get_all_magic_items_offline()
            return items if items else None
        if cat in ("Equipaggiamento", "Armi", "Pozioni"):
            items = get_all_equipment_offline(cat)
            return items if items else None
        if cat == "Regole":
            return get_all_rules_offline()
        if cat == "Classi":
            return get_all_classes_offline()
        if cat == "Tratti":
            return get_all_traits_offline()
        return None

    def fetch_list(self):
        cat = self.category_var.get()

        # 1. Categorie Manuali PDF
        if "[PDF]" in cat:
            self.status_var.set("Caricamento voci dai manuali PDF...")
            self.listbox.delete(0, tk.END)
            self.current_items = []

            def do_load_pdf():
                try:
                    all_entries = self.pdf_indexer.get_all_entries()
                    filtered = []
                    cat_lower = cat.lower()

                    for entry in all_entries:
                        m_code = entry.get("manual", "").upper()
                        m_name = entry.get("manual_name", "").lower()
                        e_cat = entry.get("category", "")

                        if "tutti i manuali" in cat_lower:
                            filtered.append(entry)
                        elif "monster manual" in cat_lower:
                            if m_code == "MM" or "monster manual" in m_name or e_cat == "Mostri & PNG":
                                filtered.append(entry)
                        elif "player's handbook" in cat_lower or "phb" in cat_lower:
                            if m_code == "PHB" or "player" in m_name:
                                filtered.append(entry)
                        elif "dungeon master" in cat_lower or "dmg" in cat_lower:
                            if m_code == "DMG" or "dungeon master" in m_name:
                                filtered.append(entry)
                        elif "tasha" in cat_lower:
                            if m_code == "TCOE" or "tasha" in m_name:
                                filtered.append(entry)
                        elif "xanathar" in cat_lower:
                            if m_code == "XGTE" or "xanathar" in m_name:
                                filtered.append(entry)
                        elif "mostri & png" in cat_lower:
                            if e_cat == "Mostri & PNG" or "monster_data" in entry:
                                filtered.append(entry)
                        elif "incantesimi" in cat_lower:
                            if e_cat == "Incantesimi":
                                filtered.append(entry)
                        elif "equipaggiamento" in cat_lower:
                            if e_cat == "Equipaggiamento & Tesori":
                                filtered.append(entry)
                        elif "regole" in cat_lower:
                            if e_cat in ["Regole Generali", "Combattimento & Azioni", "Condizioni & Stati", "Pericoli & Ambiente", "Guida del DM & Strumenti", "Avventura & Viaggio"]:
                                filtered.append(entry)
                        else:
                            clean_cat_name = cat.replace("📖 [PDF] ", "").lower()
                            if clean_cat_name in m_name or clean_cat_name in entry.get("pdf_filename", "").lower():
                                filtered.append(entry)

                    for e in filtered:
                        if "name" not in e:
                            e["name"] = e.get("title", "Voce Manuale")
                        e["is_pdf"] = True

                    self.current_items = filtered
                    self.after(0, self.update_listbox)
                    self.after(0, lambda: self.status_var.set(f"Manuali PDF: {len(self.current_items)} voci trovate."))
                except Exception as e:
                    self.after(0, lambda err=e: messagebox.showerror("Errore PDF", str(err)))

            threading.Thread(target=do_load_pdf, daemon=True).start()
            return

        # 2. Categoria PNG (Custom e SRD Umanoidi - Caricamento rapido)
        if cat == "PNG":
            self.status_var.set("Caricamento PNG (Custom & SRD)...")
            self.listbox.delete(0, tk.END)
            custom_pngs = self.compendium_manager.get_items("PNG")
            srd_pngs = []
            try:
                all_m = get_all_monsters_offline()
                npc_keywords = [
                    "guard", "guardia", "mage", "mago", "priest", "sacerdote", "cultist", "cultista",
                    "bandit", "bandito", "knight", "cavaliere", "veteran", "veterano", "spy", "spia",
                    "assassin", "assassino", "commoner", "popolano", "noble", "nobile", "thug",
                    "berserker", "druid", "druido", "gladiator", "gladiatore", "archmage", "arcimago",
                    "acolyte", "accolito", "captain", "capitano", "scout", "esploratore", "tribal warrior"
                ]
                for m in all_m:
                    m_type = str(m.get("type", "")).lower()
                    m_name = str(m.get("name", "")).lower()
                    if "humanoid" in m_type or "umanoide" in m_type or any(k in m_name for k in npc_keywords):
                        m_copy = dict(m)
                        m_copy["is_npc"] = True
                        srd_pngs.append(m_copy)
            except Exception:
                pass
            self.current_items = custom_pngs + srd_pngs
            self.update_listbox()
            self.status_var.set(f"Trovati {len(self.current_items)} PNG (Custom & SRD).")
            return

        # 3. Compendi Offline scaricati
        if hasattr(self, 'offline_compendiums') and cat in self.offline_compendiums:
            self.status_var.set("Caricamento compendio offline...")
            def do_load():
                try:
                    with open(self.offline_compendiums[cat], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self.current_items = data if isinstance(data, list) else list(data.values())
                    self.after(0, self.update_listbox)
                    self.after(0, lambda: self.status_var.set(f"Trovati {len(self.current_items)} elementi."))
                except Exception as e:
                    self.after(0, lambda err=e: messagebox.showerror("Errore", str(err)))
            threading.Thread(target=do_load, daemon=True).start()
            return

        # 4. Motore Offline-First Ibrido (0ms e filtri CR/Livello/Rarità sempre attivi)
        offline_items = self._load_offline_category_items(cat)
        if offline_items is not None:
            self.current_items = offline_items
            self.update_listbox()
            self.status_var.set(f"Compendio pronto ({len(self.displayed_items)} elementi visualizzati).")
            return

        # 5. Fallback Endpoints API Online se un catalogo locale fosse assente
        endpoints = {
            "Mostri": "/monsters",
            "Equipaggiamento": "/equipment",
            "Oggetti Magici": "/magic-items",
            "Incantesimi": "/spells",
            "Regole": "/rule-sections",
            "Classi": "/classes",
            "Tratti": "/features",
            "Armi": "/equipment-categories/weapon",
            "Pozioni": "/equipment-categories/potion"
        }
        endpoint = endpoints.get(cat, "/spells")

        self.status_var.set("Caricamento in corso...")
        self.listbox.delete(0, tk.END)
        self.current_items = []

        def do_fetch():
            try:
                req = urllib.request.Request(self.base_url + endpoint, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=4.0) as response:
                    data = json.loads(response.read().decode('utf-8'))
                self.current_items = data.get("results", data.get("equipment", []))
                try:
                    self.after(0, self.update_listbox)
                    self.after(0, lambda: self.status_var.set(f"Trovati {len(self.current_items)} elementi."))
                except RuntimeError:
                    pass
            except Exception as e:
                self._fallback_local_srd(cat, str(e))

        threading.Thread(target=do_fetch, daemon=True).start()

    def _fallback_local_srd(self, cat: str, err_msg: str):
        try:
            from common.srd_offline import SRD_DIR
            fn = None
            if cat == "Mostri":
                fn = "open5e_monsters.json"
            elif cat in ("Oggetti Magici", "Equipaggiamento", "Armi", "Pozioni"):
                fn = "open5e_magicitems.json"
            elif cat == "Incantesimi":
                fn = "open5e_spells.json"

            if fn:
                p = os.path.join(SRD_DIR, fn)
                if os.path.exists(p):
                    with open(p, 'r', encoding='utf-8') as f:
                        self.current_items = json.load(f)
                    self.after(0, self.update_listbox)
                    self.after(0, lambda: self.status_var.set(f"SRD Offline: {len(self.current_items)} elementi."))
                    return
        except Exception:
            pass
        self.after(0, lambda: self.status_var.set("Errore nel caricamento online."))

    def _extract_row_columns(self, item: Dict[str, Any], cat: str) -> Tuple[str, str, str, str, float]:
        """
        Estrae le 4 colonne della tabella (Nome, Dettaglio, Tipo/Scuola, Fonte)
        e il valore numerico di ordinamento per la colonna Dettaglio.
        """
        raw_name = str(item.get("name") or item.get("title") or "Elemento")
        item_cat = str(item.get("category") or cat).lower()

        is_m = "mostr" in item_cat or "png" in item_cat or "npc" in item_cat or "creatur" in item_cat or "monster_data" in item or "challenge_rating" in item or "hit_points" in item
        is_s = "incantesim" in item_cat or "spell" in item_cat or "school" in item
        is_i = any(k in item_cat for k in ["oggett", "equipaggiamento", "armi", "pozion", "tesor"]) or "rarity" in item

        disp_name = get_bilingual_label(raw_name, item_cat)
        if self.compendium_manager.is_favorite(item):
            disp_name = f"⭐ {disp_name}"

        detail_str = ""
        type_str = ""
        sort_val = 0.0

        if is_m:
            mdata = item.get("monster_data") if isinstance(item.get("monster_data"), dict) else item
            cr = mdata.get("challenge_rating", mdata.get("cr"))
            if cr is not None and str(cr) != "":
                detail_str = f"CR {cr}"
                sort_val = parse_cr_to_float(cr)
            mtype = mdata.get("type", "")
            type_str = str(mtype).capitalize() if mtype else "Creatura"
        elif is_s:
            lvl = item.get("level_int", item.get("level"))
            if lvl is not None:
                if str(lvl).lower() in ("0", "cantrip", "trucchetto"):
                    detail_str = "Trucchetto"
                    sort_val = 0.0
                else:
                    m_l = re.search(r'\d+', str(lvl))
                    lv_num = int(m_l.group(0)) if m_l else 1
                    detail_str = f"Liv. {lv_num}"
                    sort_val = float(lv_num)
            sch = item.get("school")
            if isinstance(sch, dict):
                sch = sch.get("name", "")
            type_str = str(sch).capitalize() if sch else "Incantesimo"
        elif is_i:
            rar = str(item.get("rarity", "Comune")).capitalize()
            detail_str = rar
            rar_ranks = {"common": 1, "comune": 1, "uncommon": 2, "non comune": 2, "rare": 3, "raro": 3, "very rare": 4, "molto raro": 4, "legendary": 5, "leggendario": 5, "artifact": 6, "artefatto": 6}
            sort_val = float(rar_ranks.get(rar.lower(), 1))
            itype = item.get("type") or (item.get("equipment_category", {}).get("name") if isinstance(item.get("equipment_category"), dict) else item.get("equipment_category", "Oggetto"))
            type_str = str(itype)
        else:
            detail_str = str(item.get("page_ref") or item.get("category") or "")
            type_str = str(item.get("type") or item.get("category") or "Regola")

        if item.get("is_custom"):
            source_str = "Custom"
        elif item.get("is_pdf") or item.get("manual"):
            source_str = str(item.get("manual", "PDF"))
        else:
            src_raw = str(item.get("source") or item.get("document__slug") or "SRD 5e")
            if "open5e" in src_raw.lower() or "wotc" in src_raw.lower():
                source_str = "SRD 5e"
            elif "tob" in src_raw.lower():
                source_str = "ToB"
            elif "cc" in src_raw.lower():
                source_str = "CC"
            else:
                source_str = src_raw[:10]

        return disp_name, detail_str, type_str, source_str, sort_val

    def update_listbox(self):
        self.listbox.delete(0, tk.END)
        self.displayed_items = []
        search_text = self.search_var.get().lower().strip()
        cat = self.category_var.get()

        is_monster_cat = "mostri" in cat.lower() or "png" in cat.lower() or "npc" in cat.lower() or "creature" in cat.lower() or "tome of beasts" in cat.lower() or "monster manual" in cat.lower()
        is_item_cat = any(k in cat.lower() for k in ["oggetti", "equipaggiamento", "armi", "pozioni", "magic-item", "tesor"])
        is_spell_cat = "incantesimi" in cat.lower() or "spell" in cat.lower()

        cr_filter = self.cr_filter_var.get()
        type_filter = self.type_filter_var.get()
        rarity_filter = self.rarity_filter_var.get()
        item_type_filter = self.item_type_filter_var.get()
        spell_lvl_filter = self.spell_level_filter_var.get()
        spell_school_filter = self.spell_school_filter_var.get()

        rows_to_render = []

        # 1. Custom items (evitando duplicati se già caricati in PNG / Global)
        seen_custom_names = set()
        if cat == self.GLOBAL_CATEGORY:
            custom_items = []
            for c_k, c_list in self.compendium_manager.data.items():
                if not self.is_dm and c_k in ("Mostri", "PNG"):
                    continue
                custom_items.extend(c_list)
        elif cat in (self.FAVORITES_CATEGORY, self.RECENT_CATEGORY, "PNG"):
            custom_items = []
        else:
            custom_items = self.compendium_manager.get_items(cat)

        for item in custom_items:
            name = item.get("name") or item.get("title", "")
            if not name:
                continue
            if search_text and not match_bilingual_search(item, search_text, cat):
                continue
            seen_custom_names.add(name.strip().lower())
            disp_name, detail_str, type_str, source_str, sort_val = self._extract_row_columns(item, cat)
            legacy_tag = f"[Custom] {name}"
            rows_to_render.append((legacy_tag, (f"[Custom] {disp_name}", detail_str, type_str, source_str), sort_val, item))

        # 2. Elementi correnti (SRD Offline, PDF Manuals, Preferiti, Recenti)
        for item in self.current_items:
            name = item.get("name") or item.get("title", "")
            if not name:
                continue
            if item.get("is_custom") and name.strip().lower() in seen_custom_names:
                continue

            # Ricerca bilingue (IT <-> EN), keywords, tipo, scuola e summary
            if search_text and not match_bilingual_search(item, search_text, cat):
                continue

            # Filtri mostro
            if is_monster_cat or "monster_data" in item:
                mdata = item.get("monster_data") or item
                m_cr = mdata.get("challenge_rating", mdata.get("cr"))
                if m_cr is not None and not match_monster_cr(m_cr, cr_filter):
                    continue
                m_type = mdata.get("type")
                if m_type is not None and not match_monster_type(m_type, type_filter):
                    continue

            # Filtri oggetto
            elif is_item_cat:
                i_rar = item.get("rarity")
                if i_rar is not None and not match_item_rarity(i_rar, rarity_filter):
                    continue
                i_type = item.get("type") or item.get("equipment_category")
                if i_type is not None and not match_item_type(i_type, item_type_filter):
                    continue

            # Filtri incantesimo
            elif is_spell_cat:
                s_lvl = item.get("level_int", item.get("level"))
                if s_lvl is not None and not match_spell_level(s_lvl, spell_lvl_filter):
                    continue
                s_sch = item.get("school")
                if s_sch is not None and not match_spell_school(s_sch, spell_school_filter):
                    continue

            disp_name, detail_str, type_str, source_str, sort_val = self._extract_row_columns(item, cat)
            if item.get("is_custom"):
                legacy_tag = f"[Custom] {name}"
                disp_col = f"[Custom] {disp_name}"
            elif item.get("is_pdf") or item.get("manual"):
                m_code = item.get("manual", "PDF")
                legacy_tag = f"[{m_code}] {name}"
                disp_col = disp_name
            elif is_monster_cat and "challenge_rating" in item:
                legacy_tag = f"[{item['challenge_rating']}] {name}"
                disp_col = disp_name
            elif is_item_cat and "rarity" in item:
                legacy_tag = f"• {name} ({item['rarity']})"
                disp_col = disp_name
            else:
                legacy_tag = name
                disp_col = disp_name

            rows_to_render.append((legacy_tag, (disp_col, detail_str, type_str, source_str), sort_val, item))

        # 3. Ordinamento per colonna (se attivo)
        if self.sort_col:
            col_idx_map = {"name": 0, "detail": 1, "type": 2, "source": 3}
            c_idx = col_idx_map.get(self.sort_col, 0)
            if self.sort_col == "detail":
                rows_to_render.sort(key=lambda r: (r[2], r[1][0].lower()), reverse=self.sort_desc)
            else:
                rows_to_render.sort(key=lambda r: r[1][c_idx].lower(), reverse=self.sort_desc)

        for legacy_tag, col_vals, _sval, item in rows_to_render:
            self.listbox.insert(tk.END, legacy_tag, values=col_vals)
            self.displayed_items.append(item)

        self.status_var.set(f"Elementi visualizzati: {len(self.displayed_items)}")


    # -------------------------------------------------------------------------
    # DETTAGLI E STATBLOCK
    # -------------------------------------------------------------------------
    def get_selected_item(self) -> Optional[Dict[str, Any]]:
        if hasattr(self.listbox, "curselection"):
            sel = self.listbox.curselection()
        elif hasattr(self.listbox, "selection"):
            sel = self.listbox.selection()
        else:
            return None
        if not sel:
            return None

        try:
            idx = int(sel[0])
            if hasattr(self, "displayed_items") and 0 <= idx < len(self.displayed_items):
                return self.displayed_items[idx]
        except (ValueError, TypeError, IndexError):
            pass

        selected_text = self.listbox.get(sel[0])

        if selected_text.startswith("[Custom] "):
            real_name = selected_text.replace("[Custom] ", "", 1)
            cat = self.category_var.get()
            for item in self.compendium_manager.get_items(cat):
                if (item.get("name") or item.get("title")) == real_name:
                    return item
            return None

        # Rimuove prefissi tag come '[CR]', '[MM]', '[PHB]' o '•'
        clean_name = selected_text
        if clean_name.startswith("[") and "]" in clean_name:
            clean_name = clean_name.split("]", 1)[1].strip()
        elif clean_name.startswith("• "):
            clean_name = clean_name.replace("• ", "", 1).split(" (")[0].strip()

        for item in self.current_items:
            item_name = item.get("name") or item.get("title", "")
            if item_name == clean_name:
                return item
        return None

    def _on_item_selected(self, event=None):
        item = self.get_selected_item()
        if not item:
            return

        cat = self.category_var.get()
        item_cat = (item.get("category") or cat).lower()

        # Registra automaticamente nella cronologia 'Consultati di Recente'
        if cat != self.RECENT_CATEGORY:
            self.compendium_manager.add_recent(item, item.get("category") or cat)

        is_monster = "mostri" in item_cat or "png" in item_cat or "npc" in item_cat or "creature" in item_cat or "monster_data" in item or "challenge_rating" in item or "hit_points" in item
        is_item = any(k in item_cat for k in ["oggetti", "equipaggiamento", "armi", "pozioni", "magic-item", "tesor"]) or "rarity" in item
        is_spell = "incantesimi" in item_cat or "spell" in item_cat or "school" in item

        # PDF Manual Item
        if item.get("is_pdf") or item.get("manual"):
            if is_monster and (item.get("monster_data") or "ac" in item or "hp" in item):
                mdata = dict(item.get("monster_data") or {})
                for k, v in item.items():
                    if k not in mdata:
                        mdata[k] = v
                mdata.setdefault("name", item.get("name") or item.get("title"))
                self.statblock_view.show_monster(mdata)
                return
            elif is_item:
                idata = dict(item)
                idata.setdefault("name", item.get("name") or item.get("title"))
                idata.setdefault("desc", item.get("content", item.get("summary", "")))
                self.statblock_view.show_magic_item(idata)
                return
            elif is_spell:
                sdata = dict(item)
                sdata.setdefault("name", item.get("name") or item.get("title"))
                sdata.setdefault("desc", item.get("content", item.get("summary", "")))
                self.statblock_view.show_spell(sdata)
                return
            else:
                self.statblock_view.show_generic(item.get("name") or item.get("title", "Voce Manuale"), item)
                return

        # 1. Se l'item ha già i dati completi (offline o custom o cache)
        if item.get("is_custom") or item.get("actions") or item.get("armor_class") or item.get("type") or item.get("school") or item.get("desc"):
            self._render_item_in_statblock(item, is_monster, is_item, is_spell)
            return

        # 2. Controllo rapido nei record offline locali per evitare fetch
        item_name = item.get("name") or item.get("title", "")
        if is_monster:
            local_m = get_monster_offline(item_name)
            if local_m:
                self.statblock_view.show_monster(local_m)
                return

        # 3. Se necessita fetch dall'API online (ha item["url"])
        url = item.get("url")
        if url:
            if url in self._item_details_cache:
                data = self._item_details_cache[url]
                self._render_item_in_statblock(data, is_monster, is_item, is_spell)
                return

            self.statblock_view.show_loading(item_name)
            def do_fetch_details():
                try:
                    req = urllib.request.Request("https://www.dnd5eapi.co" + url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=3.5) as resp:
                        full_data = json.loads(resp.read().decode('utf-8'))
                    self._item_details_cache[url] = full_data
                    self.after(0, lambda: self._render_item_in_statblock(full_data, is_monster, is_item, is_spell))
                except Exception:
                    self.after(0, lambda: self.statblock_view.show_generic(item_name, item))

            threading.Thread(target=do_fetch_details, daemon=True).start()
        else:
            self._render_item_in_statblock(item, is_monster, is_item, is_spell)


    def _render_item_in_statblock(self, data: Dict[str, Any], is_monster: bool, is_item: bool, is_spell: bool):
        if is_monster:
            self.statblock_view.show_monster(data)
        elif is_item:
            self.statblock_view.show_magic_item(data)
        elif is_spell:
            self.statblock_view.show_spell(data)
        else:
            self.statblock_view.show_generic(data.get("name") or data.get("title", "Dettagli"), data)

    # -------------------------------------------------------------------------
    # IMPORTAZIONE DI ELEMENTI
    # -------------------------------------------------------------------------
    def _on_statblock_action(self, item_data: Dict[str, Any], category: str):
        """Callback invocata al click del pulsante primario in cima allo Statblock."""
        if not self.on_import_callback:
            return

        cat = self.category_var.get()
        item_cat = (item_data.get("category") or cat).lower()

        if "mostr" in item_cat or "png" in item_cat or "npc" in item_cat or "creatur" in item_cat or "monster_data" in item_data or "ac" in item_data:
            real_cat = "Mostri"
        elif "incantesim" in item_cat or "spell" in item_cat:
            real_cat = "Incantesimi"
        elif any(k in item_cat for k in ["oggett", "equipaggiamento", "armi", "pozion", "tesor"]):
            real_cat = "Equipaggiamento"
        elif any(k in item_cat for k in ["regol", "combattimento", "condizion", "pericol", "talent", "guida"]):
            real_cat = "Regole"
        else:
            real_cat = cat

        # Arricchimento dati per compatibilità completa
        name = item_data.get("name") or item_data.get("title", "Elemento")
        item_data["name"] = name
        if "monster_data" in item_data and isinstance(item_data["monster_data"], dict):
            mdata = item_data["monster_data"]
            item_data.setdefault("hit_points", mdata.get("hp", 15))
            item_data.setdefault("hp", mdata.get("hp", 15))
            item_data.setdefault("armor_class", mdata.get("ac", 12))
            item_data.setdefault("ac", mdata.get("ac", 12))
            item_data.setdefault("challenge_rating", mdata.get("cr", "1"))
            item_data.setdefault("cr", mdata.get("cr", "1"))
            if "attributes" in mdata:
                item_data.setdefault("attributes", mdata["attributes"])
            if "type" in mdata:
                item_data.setdefault("type", mdata["type"])
        if not item_data.get("desc") and item_data.get("content"):
            item_data["desc"] = item_data["content"]

        self.on_import_callback(item_data, real_cat)
        messagebox.showinfo("Importazione", f"'{name}' importato con successo!", parent=self)

    def import_selected(self):
        """Importa l'elemento selezionato nella listbox."""
        item = self.get_selected_item()
        if not item:
            messagebox.showinfo("Avviso", "Seleziona prima un elemento dalla lista da aggiungere.", parent=self)
            return
        if not self.on_import_callback:
            return

        cat = self.category_var.get()
        if item.get("is_pdf") or item.get("is_custom") or item.get("actions") or item.get("armor_class") or not item.get("url"):
            self._on_statblock_action(item, cat)
            return

        item_name = item.get("name") or item.get("title", "")
        # Se è un mostro presente localmente nei dati offline SRD, importa istantaneamente
        try:
            from common.srd_offline import get_monster_offline
            local_m = get_monster_offline(item_name)
            if local_m:
                self._on_statblock_action(local_m, cat)
                return
        except Exception:
            pass

        url = item.get("url")
        if url and url in self._item_details_cache:
            self._on_statblock_action(self._item_details_cache[url], cat)
            return

        # Fetch asincrono se online
        self.status_var.set(f"Importazione di {item_name}...")
        def do_import():
            try:
                req = urllib.request.Request("https://www.dnd5eapi.co" + url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3.5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                self._item_details_cache[url] = data
                self.after(0, lambda: self.status_var.set("Importazione completata."))
                self.after(0, lambda: self._on_statblock_action(data, cat))
            except Exception as e:
                self.after(0, lambda: self.status_var.set("Errore nell'importazione."))
                self.after(0, lambda err=e: messagebox.showerror("Errore", str(err)))

        threading.Thread(target=do_import, daemon=True).start()

    def view_details(self):
        """Retrocompatibilità: seleziona l'elemento e aggiorna lo statblock."""
        self._on_item_selected()

    # -------------------------------------------------------------------------
    # IMPORTAZIONE & REINDICIZZAZIONE MANUALI PDF
    # -------------------------------------------------------------------------
    def import_pdf_manual(self):
        """Permette all'utente di importare uno o più manuali PDF dal proprio computer."""
        pdf_files = filedialog.askopenfilenames(
            title="Seleziona Manuali D&D in formato PDF",
            filetypes=[("Documenti PDF", "*.pdf"), ("Tutti i file", "*.*")],
            parent=self
        )
        if not pdf_files:
            return

        os.makedirs(PDF_DIR, exist_ok=True)
        copied = []
        for p in pdf_files:
            fn = os.path.basename(p)
            dest = os.path.join(PDF_DIR, fn)
            try:
                if os.path.abspath(p) != os.path.abspath(dest):
                    shutil.copy2(p, dest)
                copied.append(fn)
            except Exception as e:
                messagebox.showerror("Errore Copia", f"Impossibile copiare {fn}: {e}", parent=self)

        if not copied:
            return

        self.status_var.set(f"Indicizzazione di {len(copied)} manuali PDF in corso...")

        progress_win = tk.Toplevel(self)
        progress_win.title("Indicizzazione Manuali PDF")
        progress_win.geometry("420x160")
        progress_win.transient(self)
        progress_win.grab_set()
        apply_modern_window_style(progress_win)

        tk.Label(progress_win, text="📚 Indicizzazione Manuali PDF", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(pady=(15, 5))
        lbl_info = tk.Label(
            progress_win,
            text=f"Estrazione e indicizzazione di {len(copied)} file PDF in corso...\nQuesto processo crea la cache veloce per il compendio.",
            font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_COLOR, wraplength=380
        )
        lbl_info.pack(pady=5)

        prog = ttk.Progressbar(progress_win, mode="indeterminate")
        prog.pack(fill=tk.X, padx=20, pady=10)
        prog.start(10)

        def _done_cb(count):
            def _ui():
                try:
                    prog.stop()
                    progress_win.destroy()
                except Exception:
                    pass
                self._refresh_categories()
                self.category_var.set("📖 [PDF] Tutti i Manuali (Indice Completo)")
                self._on_category_changed()
                messagebox.showinfo(
                    "Importazione PDF Completata",
                    f"Importati con successo {len(copied)} manuali PDF!\nIndicizzate {count} voci nel compendio.",
                    parent=self
                )
            self.after(0, _ui)

        self.pdf_indexer.reindex_async(on_done_callback=_done_cb)

    def reindex_pdf_manuals(self):
        """Avvia la reindicizzazione dei PDF già presenti in 'manuals_pdf/'."""
        if not self.pdf_indexer.get_pdf_files():
            messagebox.showinfo("Nessun PDF", f"Nessun file PDF trovato in '{PDF_DIR}'.\nUsa 'Importa PDF Manuale...' per aggiungere manuali.", parent=self)
            return

        self.status_var.set("Reindicizzazione manuali PDF in corso...")
        def _done(count):
            self.after(0, lambda: self.status_var.set(f"Reindicizzazione completata: {count} voci."))
            self.after(0, self._refresh_categories)
            self.after(0, self._on_category_changed)
            self.after(0, lambda: messagebox.showinfo("Reindicizzazione", f"Reindicizzazione completata con {count} voci!", parent=self))

        self.pdf_indexer.reindex_async(on_done_callback=_done)

    def _refresh_categories(self):
        new_cats = self._build_category_list()
        self.category_cb["values"] = new_cats

    def create_custom_item(self, existing_item: Optional[Dict[str, Any]] = None, existing_cat: Optional[str] = None):
        cat = existing_cat or (existing_item.get("category") if isinstance(existing_item, dict) else None) or self.category_var.get()
        if cat in (self.GLOBAL_CATEGORY, self.FAVORITES_CATEGORY, self.RECENT_CATEGORY) or cat.startswith("[OFFLINE] ") or "[PDF]" in cat:
            cat = "Mostri" if (getattr(self, "monsters_only", False) or self.is_dm) else "Equipaggiamento"

        is_edit = isinstance(existing_item, dict)
        old_name = (existing_item.get("name") or existing_item.get("title") or "") if is_edit else ""
        is_monster = "mostri" in cat.lower() or "png" in cat.lower() or "npc" in cat.lower() or getattr(self, "monsters_only", False) or (is_edit and ("hp" in existing_item or "armor_class" in existing_item))

        win = tk.Toplevel(self)
        win.transient(self)
        win.grab_set()
        win.title(f"{'Modifica' if is_edit else 'Nuovo'} Custom: {cat}")
        win.minsize(440, 560 if is_monster else 420)
        apply_modern_window_style(win)

        ttk.Label(win, text="Nome:", font=FONT_BOLD).pack(pady=(8, 2), anchor="w", padx=12)
        name_var = tk.StringVar(value=old_name)
        ttk.Entry(win, textvariable=name_var).pack(fill=tk.X, padx=12)

        stat_vars = {}
        if is_monster:
            # 1. Riga Parametri Combattimento
            m_grid = ttk.Frame(win)
            m_grid.pack(fill=tk.X, padx=12, pady=6)
            m_grid.columnconfigure(1, weight=1)
            m_grid.columnconfigure(3, weight=1)
            m_grid.columnconfigure(5, weight=1)

            init_hp = str(existing_item.get("hp", existing_item.get("hit_points", 20))) if is_edit else "20"
            init_ac = str(existing_item.get("ac", existing_item.get("armor_class", 12))) if is_edit else "12"
            init_ini = str(existing_item.get("initiative", 0)) if is_edit else "0"
            init_cr = str(existing_item.get("cr", existing_item.get("challenge_rating", "1"))) if is_edit else "1"
            init_spd = str(existing_item.get("speed", "30 ft")) if is_edit else "30 ft"

            ttk.Label(m_grid, text="HP:", font=FONT_BOLD).grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
            hp_var = tk.StringVar(value=init_hp)
            ttk.Entry(m_grid, textvariable=hp_var, width=7).grid(row=0, column=1, sticky="w", pady=2)

            ttk.Label(m_grid, text="CA:", font=FONT_BOLD).grid(row=0, column=2, sticky="w", padx=(8, 4), pady=2)
            ac_var = tk.StringVar(value=init_ac)
            ttk.Entry(m_grid, textvariable=ac_var, width=7).grid(row=0, column=3, sticky="w", pady=2)

            ttk.Label(m_grid, text="Iniz.:", font=FONT_BOLD).grid(row=0, column=4, sticky="w", padx=(8, 4), pady=2)
            init_var = tk.StringVar(value=init_ini)
            init_entry = ttk.Entry(m_grid, textvariable=init_var, width=7)
            init_entry.grid(row=0, column=5, sticky="w", pady=2)

            ttk.Label(m_grid, text="CR:", font=FONT_BOLD).grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
            cr_var = tk.StringVar(value=init_cr)
            ttk.Entry(m_grid, textvariable=cr_var, width=7).grid(row=1, column=1, sticky="w", pady=2)

            ttk.Label(m_grid, text="Vel.:", font=FONT_BOLD).grid(row=1, column=2, sticky="w", padx=(8, 4), pady=2)
            speed_var = tk.StringVar(value=init_spd)
            ttk.Entry(m_grid, textvariable=speed_var, width=7).grid(row=1, column=3, sticky="w", pady=2)

            # 2. Caratteristiche 5e (Ability Scores: FOR, DES, COS, INT, SAG, CAR)
            attr_box = ttk.LabelFrame(win, text="Caratteristiche 5e (Ability Scores):")
            attr_box.pack(fill=tk.X, padx=12, pady=6)

            attr_inner = tk.Frame(attr_box, bg=SURFACE_COLOR_ALT, padx=4, pady=6)
            attr_inner.pack(fill=tk.X, expand=True)

            existing_attrs = (existing_item.get("attributes") or {}) if is_edit else {}

            for stat_code in ["FOR", "DES", "COS", "INT", "SAG", "CAR"]:
                col = tk.Frame(attr_inner, bg=SURFACE_COLOR_ALT)
                col.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=2)

                default_stat = str(existing_attrs.get(stat_code, 10))
                tk.Label(col, text=stat_code, font=("Segoe UI", 8, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack()
                s_var = tk.StringVar(value=default_stat)
                stat_vars[stat_code] = s_var
                e = tk.Entry(col, textvariable=s_var, width=4, font=("Segoe UI", 10, "bold"), justify="center",
                             bg=SURFACE_COLOR, fg=TEXT_COLOR, relief=tk.SOLID, bd=1)
                e.pack(pady=1)

                try:
                    mod_init = (int(default_stat) - 10) // 2
                    mod_txt = f"({'+' if mod_init >= 0 else ''}{mod_init})"
                except Exception:
                    mod_txt = "(+0)"
                m_lbl = tk.Label(col, text=mod_txt, font=("Segoe UI", 7), bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED)
                m_lbl.pack()

                def _make_stat_listener(sc, sv, ml):
                    def _update_mod(*args):
                        try:
                            v = int(sv.get().strip())
                            mod = (v - 10) // 2
                            ml.config(text=f"({'+' if mod >= 0 else ''}{mod})")
                            if sc == "DES":
                                init_var.set(str(mod))
                        except Exception:
                            ml.config(text="(--)")
                    return _update_mod

                s_var.trace_add("write", _make_stat_listener(stat_code, s_var, m_lbl))

        ttk.Label(win, text="Descrizione / Proprietà / Azioni:", font=FONT_BOLD).pack(pady=(6, 2), anchor="w", padx=12)
        from tkinter import scrolledtext
        desc_text = scrolledtext.ScrolledText(win, height=5, wrap=tk.WORD, bg=SURFACE_COLOR, fg=TEXT_COLOR, insertbackground=ACCENT_GOLD)
        desc_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 6))
        if is_edit and existing_item.get("desc"):
            desc_text.insert("1.0", str(existing_item.get("desc")))

        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Errore", "Inserisci un nome.", parent=win)
                return
            item = {"name": name, "desc": desc_text.get("1.0", tk.END).strip(), "is_custom": True, "category": cat}
            if is_monster:
                try:
                    hp_val = int(hp_var.get())
                    ac_val = int(ac_var.get())
                    init_val = int(init_var.get())
                    item["hp"] = hp_val
                    item["hit_points"] = hp_val
                    item["ac"] = ac_val
                    item["armor_class"] = ac_val
                    item["initiative"] = init_val
                    item["cr"] = cr_var.get().strip() or "1"
                    item["challenge_rating"] = item["cr"]
                    item["speed"] = speed_var.get().strip() or "30 ft"

                    custom_stats = {}
                    for sc in ["FOR", "DES", "COS", "INT", "SAG", "CAR"]:
                        v_str = stat_vars[sc].get().strip()
                        custom_stats[sc] = int(v_str) if v_str else 10

                    from common.srd_offline import extract_and_normalize_attributes
                    full_attrs = extract_and_normalize_attributes({"attributes": custom_stats}, name)
                    item["attributes"] = full_attrs
                    item["strength"] = full_attrs.get("FOR", 10)
                    item["dexterity"] = full_attrs.get("DES", 10)
                    item["constitution"] = full_attrs.get("COS", 10)
                    item["intelligence"] = full_attrs.get("INT", 10)
                    item["wisdom"] = full_attrs.get("SAG", 10)
                    item["charisma"] = full_attrs.get("CAR", 10)
                except Exception as e:
                    print("Error saving custom monster stats:", e)

            if is_edit:
                self.compendium_manager.update_item(cat, old_name, item)
            else:
                self.compendium_manager.add_item(cat, item)
            self.fetch_list()
            self._render_item_in_statblock(item, is_monster, not is_monster, False)
            win.destroy()

        ttk.Button(win, text="Salva Custom", command=save, style="Success.TButton").pack(pady=(4, 12))

    def edit_custom_item(self, item_data: Optional[Dict[str, Any]] = None, category: Optional[str] = None):
        target = item_data or self.get_selected_item()
        if not target or not target.get("is_custom"):
            messagebox.showinfo("Avviso", "Seleziona una voce [Custom] per modificarla.", parent=self)
            return
        self.create_custom_item(existing_item=target, existing_cat=category or target.get("category") or self.category_var.get())

    def edit_selected_custom_item(self):
        self.edit_custom_item(self.get_selected_item(), self.category_var.get())

    def delete_custom_item(self, item_data: Optional[Dict[str, Any]] = None, category: Optional[str] = None):
        target = item_data or self.get_selected_item()
        if not target or not target.get("is_custom"):
            messagebox.showinfo("Avviso", "Seleziona una voce [Custom] per eliminarla.", parent=self)
            return
        name = target.get("name") or target.get("title", "Elemento")
        if not messagebox.askyesno("Conferma Eliminazione", f"Vuoi eliminare definitivamente la voce custom '{name}'?", parent=self):
            return
        cat = category or target.get("category") or self.category_var.get()
        self.compendium_manager.remove_item(cat, name)
        self.fetch_list()
        self.statblock_view.show_placeholder("Voce custom eliminata.")

    def delete_selected_custom_item(self):
        self.delete_custom_item(self.get_selected_item(), self.category_var.get())

    def open_downloader(self):
        try:
            from server.srd_downloader import CompendiumDownloaderUI
            win = CompendiumDownloaderUI(self.master)
            win.grab_set()
            self.wait_window(win)
            self.fetch_list()
        except ImportError as e:
            messagebox.showerror("Errore", str(e))

