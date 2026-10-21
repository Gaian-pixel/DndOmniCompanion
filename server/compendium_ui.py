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
from typing import Optional, Callable, Dict, Any, List

from common.messagebox import messagebox
from common.theme import (
    apply_modern_window_style, SURFACE_COLOR, BORDER_COLOR, TEXT_COLOR, TEXT_MUTED,
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
)
from common.pdf_manuals_indexer import PDFManualsIndexer, PDF_DIR


class CompendiumDialog(tk.Toplevel):
    """Finestra Compendio 5e con Split View, Statblock interattivo e supporto Manuali PDF."""

    def __init__(self, master, on_import_callback: Optional[Callable] = None, is_dm: bool = True, initial_category: Optional[str] = None, action_label: Optional[str] = None):
        super().__init__(master)
        self.title("Compendio 5e SRD & Manuali PDF • Consultazione & Importazione")
        self.minsize(1020, 700)
        self.geometry("1100x740")
        self.transient(master)
        apply_modern_window_style(self)

        self.on_import_callback = on_import_callback
        self.is_dm = is_dm
        self.initial_category = initial_category
        self.action_label = action_label

        self.base_url = "https://www.dnd5eapi.co/api"
        self.current_items: List[Dict[str, Any]] = []
        self.compendium_manager = CompendiumManager()
        self.pdf_indexer = PDFManualsIndexer()

        # Cache dettagli recuperati per evitare refetch ripetuti
        self._item_details_cache: Dict[str, Dict[str, Any]] = {}

        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "srd_data")
        self.offline_compendiums: Dict[str, str] = {}

        self.setup_ui()
        self.fetch_list()

    def _build_category_list(self) -> List[str]:
        categories = ["Incantesimi", "Regole", "Classi", "Tratti", "Equipaggiamento", "Armi", "Pozioni", "Oggetti Magici"]
        if self.is_dm:
            categories = ["Mostri"] + categories

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

        return categories + pdf_cats

    def setup_ui(self):
        # Master-Detail PanedWindow
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # -------------------------------------------------------------
        # PANNELLO SINISTRO (Lista & Filtri)
        # -------------------------------------------------------------
        left_panel = ttk.Frame(self.paned, padding="8")
        self.paned.add(left_panel, weight=0)

        # 1. Categoria
        cat_frame = ttk.Frame(left_panel)
        cat_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(cat_frame, text="Categoria:", font=FONT_BOLD).pack(side=tk.LEFT, padx=(0, 4))
        self.category_var = tk.StringVar()

        categories = self._build_category_list()
        self.category_cb = ttk.Combobox(cat_frame, textvariable=self.category_var, values=categories, state="readonly", width=28)
        self.category_cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.category_cb.bind("<<ComboboxSelected>>", self._on_category_changed)

        if self.initial_category:
            matched = None
            for c in categories:
                if c.lower() == self.initial_category.lower() or self.initial_category.lower() in c.lower():
                    matched = c
                    break
            self.category_var.set(matched or categories[0])
        elif self.is_dm:
            self.category_var.set("Mostri")
        else:
            self.category_var.set("Incantesimi")

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

        # 3. Casella di ricerca
        search_frame = ttk.Frame(left_panel)
        search_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(search_frame, text="🔍 Cerca:", font=FONT_BOLD).pack(side=tk.LEFT, padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.update_listbox())
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 4. Listbox con scrollbar
        list_container = ttk.Frame(left_panel)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.list_scroll = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(
            list_container,
            yscrollcommand=self.list_scroll.set,
            font=FONT_MAIN,
            selectbackground=BORDER_COLOR,
            selectforeground=TEXT_COLOR,
            activestyle="none",
            width=36,
            height=16
        )
        self.list_scroll.config(command=self.listbox.yview)

        self.list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.listbox.bind("<<ListboxSelect>>", self._on_item_selected)
        self.listbox.bind("<Double-Button-1>", lambda e: self.import_selected())

        # 5. Status bar sinistra
        self.status_var = tk.StringVar(value="Pronto.")
        ttk.Label(left_panel, textvariable=self.status_var, font=FONT_SMALL, foreground=TEXT_MUTED).pack(fill=tk.X, pady=(0, 4))

        # 6. Bottoni inferiori
        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="📂 Importa PDF Manuale...", command=self.import_pdf_manual, style="Gold.TButton").pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text="🔄 Reindicizza PDF", command=self.reindex_pdf_manuals).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text="Compendi Online", command=self.open_downloader).pack(side=tk.LEFT, padx=(0, 3))
        if self.is_dm:
            ttk.Button(btn_frame, text="➕ Custom", command=self.create_custom_item).pack(side=tk.LEFT, padx=(0, 3))
        if self.on_import_callback:
            import_btn_label = self.action_label or "➕ Importa Selezionato"
            ttk.Button(btn_frame, text=import_btn_label, command=self.import_selected, style="Gold.TButton").pack(side=tk.RIGHT)

        # -------------------------------------------------------------
        # PANNELLO DESTRO (Statblock Card 5e)
        # -------------------------------------------------------------
        right_panel = ttk.Frame(self.paned)
        self.paned.add(right_panel, weight=1)

        action_txt = self.action_label or ("Schiera sulla Mappa" if self.is_dm else "Aggiungi al Personaggio")
        self.statblock_view = StatblockCardView(
            right_panel,
            on_primary_action=self._on_statblock_action,
            action_label=action_txt
        )
        self.statblock_view.pack(fill=tk.BOTH, expand=True)

    # -------------------------------------------------------------------------
    # GESTIONE FILTRI RAPIDI
    # -------------------------------------------------------------------------
    def _on_category_changed(self, event=None):
        self._update_filter_bar()
        self.fetch_list()

    def _update_filter_bar(self):
        for w in self.filter_widgets:
            w.destroy()
        self.filter_widgets.clear()

        cat = self.category_var.get()
        is_monster_cat = "mostri" in cat.lower() or "creature" in cat.lower() or "tome of beasts" in cat.lower() or "monster manual" in cat.lower()
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

    # -------------------------------------------------------------------------
    # CARICAMENTO DATI (PDF, OFFLINE E ONLINE)
    # -------------------------------------------------------------------------
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

        # 2. Compendi Offline scaricati
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

        # 3. Endpoints API Online
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

    def update_listbox(self):
        self.listbox.delete(0, tk.END)
        search_text = self.search_var.get().lower().strip()
        cat = self.category_var.get()

        is_monster_cat = "mostri" in cat.lower() or "creature" in cat.lower() or "tome of beasts" in cat.lower() or "monster manual" in cat.lower()
        is_item_cat = any(k in cat.lower() for k in ["oggetti", "equipaggiamento", "armi", "pozioni", "magic-item", "tesor"])
        is_spell_cat = "incantesimi" in cat.lower() or "spell" in cat.lower()

        cr_filter = self.cr_filter_var.get()
        type_filter = self.type_filter_var.get()
        rarity_filter = self.rarity_filter_var.get()
        item_type_filter = self.item_type_filter_var.get()
        spell_lvl_filter = self.spell_level_filter_var.get()
        spell_school_filter = self.spell_school_filter_var.get()

        # 1. Custom items
        custom_items = self.compendium_manager.get_items(cat)
        for item in custom_items:
            name = item.get("name") or item.get("title", "")
            if search_text and search_text not in name.lower():
                continue
            self.listbox.insert(tk.END, f"[Custom] {name}")

        # 2. Elementi correnti (SRD, Offline, PDF Manuals)
        shown_count = 0
        for item in self.current_items:
            name = item.get("name") or item.get("title", "")
            if not name:
                continue

            # Ricerca flessibile: nome, parole chiave (anche in italiano!) e summary
            if search_text:
                name_l = name.lower()
                kws = [str(k).lower() for k in item.get("keywords", [])]
                summary_l = str(item.get("summary", "")).lower()
                if search_text not in name_l and not any(search_text in k for k in kws) and search_text not in summary_l:
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
                s_lvl = item.get("level")
                if s_lvl is not None and not match_spell_level(s_lvl, spell_lvl_filter):
                    continue
                s_sch = item.get("school")
                if s_sch is not None and not match_spell_school(s_sch, spell_school_filter):
                    continue

            # Tag visuale elegante nella lista
            if item.get("is_pdf") or item.get("manual"):
                m_code = item.get("manual", "PDF")
                tag = f"[{m_code}] {name}"
            elif is_monster_cat and "challenge_rating" in item:
                tag = f"[{item['challenge_rating']}] {name}"
            elif is_item_cat and "rarity" in item:
                tag = f"• {name} ({item['rarity']})"
            else:
                tag = name

            self.listbox.insert(tk.END, tag)
            shown_count += 1

        self.status_var.set(f"Elementi visualizzati: {shown_count}")

    # -------------------------------------------------------------------------
    # DETTAGLI E STATBLOCK
    # -------------------------------------------------------------------------
    def get_selected_item(self) -> Optional[Dict[str, Any]]:
        sel = self.listbox.selection()
        if not sel:
            return None
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

        is_monster = "mostri" in item_cat or "creature" in item_cat or "monster_data" in item
        is_item = any(k in item_cat for k in ["oggetti", "equipaggiamento", "armi", "pozioni", "magic-item", "tesor"])
        is_spell = "incantesimi" in item_cat or "spell" in item_cat

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
        if item.get("is_custom") or item.get("actions") or item.get("armor_class") or item.get("type") or item.get("school"):
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

        if "mostr" in item_cat or "creatur" in item_cat or "monster_data" in item_data or "ac" in item_data:
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
        if not item or not self.on_import_callback:
            return

        cat = self.category_var.get()
        if item.get("is_pdf") or item.get("is_custom") or item.get("actions") or item.get("armor_class") or not item.get("url"):
            self._on_statblock_action(item, cat)
            return

        # Fetch asincrono se online
        url = item.get("url")
        item_name = item.get("name") or item.get("title", "")
        self.status_var.set(f"Importazione di {item_name}...")
        def do_import():
            try:
                req = urllib.request.Request("https://www.dnd5eapi.co" + url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3.5) as response:
                    data = json.loads(response.read().decode('utf-8'))
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

    def create_custom_item(self):
        cat = self.category_var.get()
        if cat.startswith("[OFFLINE] ") or "[PDF]" in cat:
            messagebox.showinfo("Avviso", "Seleziona una categoria base come 'Mostri' o 'Equipaggiamento' per creare un custom.")
            return

        win = tk.Toplevel(self)
        win.transient(self)
        win.grab_set()
        win.title(f"Nuovo Custom: {cat}")
        win.minsize(360, 420)
        apply_modern_window_style(win)

        ttk.Label(win, text="Nome:", font=FONT_BOLD).pack(pady=4)
        name_var = tk.StringVar()
        ttk.Entry(win, textvariable=name_var).pack(fill=tk.X, padx=12)

        if "mostri" in cat.lower():
            ttk.Label(win, text="HP:", font=FONT_BOLD).pack(pady=4)
            hp_var = tk.StringVar(value="20")
            ttk.Entry(win, textvariable=hp_var).pack(fill=tk.X, padx=12)

            ttk.Label(win, text="CA (Classe Armatura):", font=FONT_BOLD).pack(pady=4)
            ac_var = tk.StringVar(value="12")
            ttk.Entry(win, textvariable=ac_var).pack(fill=tk.X, padx=12)

            ttk.Label(win, text="Iniziativa (bonus):", font=FONT_BOLD).pack(pady=4)
            init_var = tk.StringVar(value="0")
            ttk.Entry(win, textvariable=init_var).pack(fill=tk.X, padx=12)

        ttk.Label(win, text="Descrizione / Proprietà:", font=FONT_BOLD).pack(pady=4)
        from tkinter import scrolledtext
        desc_text = scrolledtext.ScrolledText(win, height=6, wrap=tk.WORD)
        desc_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        def save():
            if not name_var.get():
                messagebox.showerror("Errore", "Inserisci un nome.", parent=win)
                return
            item = {"name": name_var.get(), "desc": desc_text.get("1.0", tk.END).strip(), "is_custom": True}
            if "mostri" in cat.lower():
                try:
                    item["hp"] = int(hp_var.get())
                    item["ac"] = int(ac_var.get())
                    item["initiative"] = int(init_var.get())
                except Exception:
                    pass
            self.compendium_manager.add_item(cat, item)
            self.update_listbox()
            win.destroy()

        ttk.Button(win, text="Salva Custom", command=save, style="Success.TButton").pack(pady=10)

    def open_downloader(self):
        try:
            from server.srd_downloader import CompendiumDownloaderUI
            win = CompendiumDownloaderUI(self.master)
            win.grab_set()
            self.wait_window(win)
            self.fetch_list()
        except ImportError as e:
            messagebox.showerror("Errore", str(e))
