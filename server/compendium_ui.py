# server/compendium_ui.py
"""
Modulo UI per la consultazione e l'importazione rapida di risorse 5e SRD.
Implementa una Split View (Master-Detail) con:
- Lista elementi filtrabile per Categoria, Ricerca, Grado di Sfida (CR), Tipo creatura e Rarità.
- Statblock Card 5e Dark Fantasy interattiva in tempo reale.
- Supporto a compendi online (dnd5eapi) e offline (Open5e, Creature Codex, Tome of Beasts).
"""

import tkinter as tk
from tkinter import ttk
import urllib.request
import json
import threading
import os
from typing import Optional, Callable, Dict, Any, List

from common.messagebox import messagebox
from common.theme import apply_modern_window_style, SURFACE_COLOR, BORDER_COLOR, TEXT_COLOR, TEXT_MUTED, FONT_MAIN, FONT_BOLD, FONT_SMALL
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


class CompendiumDialog(tk.Toplevel):
    """Finestra Compendio 5e SRD con Split View e Statblock interattivo."""

    def __init__(self, master, on_import_callback: Optional[Callable] = None, is_dm: bool = True, initial_category: Optional[str] = None, action_label: Optional[str] = None):
        super().__init__(master)
        self.title("Compendio 5e SRD • Consultazione & Importazione")
        self.minsize(980, 680)
        self.transient(master)
        apply_modern_window_style(self)

        self.on_import_callback = on_import_callback
        self.is_dm = is_dm
        self.initial_category = initial_category
        self.action_label = action_label

        self.base_url = "https://www.dnd5eapi.co/api"
        self.current_items: List[Dict[str, Any]] = []
        self.compendium_manager = CompendiumManager()

        # Cache dettagli recuperati per evitare refetch ripetuti
        self._item_details_cache: Dict[str, Dict[str, Any]] = {}

        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "srd_data")
        self.offline_compendiums: Dict[str, str] = {}

        self.setup_ui()
        self.fetch_list()

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

        self.category_cb = ttk.Combobox(cat_frame, textvariable=self.category_var, values=categories, state="readonly", width=22)
        self.category_cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.category_cb.bind("<<ComboboxSelected>>", self._on_category_changed)

        if self.initial_category and self.initial_category in categories:
            self.category_var.set(self.initial_category)
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

        # 4. Listbox dei risultati con Scrollbar
        list_container = ttk.Frame(left_panel)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.list_scroll = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(
            list_container,
            bg=SURFACE_COLOR,
            fg=TEXT_COLOR,
            selectbackground="#1E3A8A",
            selectforeground="#FDE68A",
            font=FONT_MAIN,
            borderwidth=0,
            relief="flat",
            yscrollcommand=self.list_scroll.set
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

        ttk.Button(btn_frame, text="Gestisci Compendi", command=self.open_downloader).pack(side=tk.LEFT, padx=(0, 4))
        if self.is_dm:
            ttk.Button(btn_frame, text="➕ Crea Custom", command=self.create_custom_item).pack(side=tk.LEFT)
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
        # Rimuove widget filtri precedenti
        for w in self.filter_widgets:
            w.destroy()
        self.filter_widgets.clear()

        cat = self.category_var.get()
        is_monster_cat = "mostri" in cat.lower() or "creature" in cat.lower() or "tome of beasts" in cat.lower()
        is_item_cat = any(k in cat.lower() for k in ["oggetti", "equipaggiamento", "armi", "pozioni", "magic-item"])
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
            rarity_vals = ["Tutte le Rarità", "Comune", "Non comune", "Raro", "Molto raro", "Leggendario", "Artefatto"]
            cb_rar = ttk.Combobox(r1, textvariable=self.rarity_filter_var, values=rarity_vals, state="readonly", width=13)
            cb_rar.pack(side=tk.LEFT, padx=(0, 6))
            cb_rar.bind("<<ComboboxSelected>>", lambda e: self.update_listbox())

            ttk.Label(r1, text="Tipo:", font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 2))
            item_types = ["Tutti i Tipi", "Arma", "Armatura", "Pozione", "Pergamena", "Anello", "Bacchetta/Verga", "Meraviglia"]
            cb_itype = ttk.Combobox(r1, textvariable=self.item_type_filter_var, values=item_types, state="readonly", width=13)
            cb_itype.pack(side=tk.LEFT, fill=tk.X, expand=True)
            cb_itype.bind("<<ComboboxSelected>>", lambda e: self.update_listbox())

        elif is_spell_cat:
            r1 = ttk.Frame(self.filter_frame)
            r1.pack(fill=tk.X, pady=2)
            self.filter_widgets.append(r1)

            ttk.Label(r1, text="Livello:", font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 2))
            lvl_vals = ["Tutti i Livelli", "Trucchetto", "Livello 1", "Livello 2", "Livello 3", "Livello 4", "Livello 5", "Livello 6", "Livello 7", "Livello 8", "Livello 9"]
            cb_lvl = ttk.Combobox(r1, textvariable=self.spell_level_filter_var, values=lvl_vals, state="readonly", width=13)
            cb_lvl.pack(side=tk.LEFT, padx=(0, 6))
            cb_lvl.bind("<<ComboboxSelected>>", lambda e: self.update_listbox())

            ttk.Label(r1, text="Scuola:", font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 2))
            school_vals = ["Tutte le Scuole", "Abiurazione", "Ammaliamento", "Divinazione", "Evocazione", "Illusione", "Invocazione", "Necromanzia", "Trasmutazione"]
            cb_sch = ttk.Combobox(r1, textvariable=self.spell_school_filter_var, values=school_vals, state="readonly", width=13)
            cb_sch.pack(side=tk.LEFT, fill=tk.X, expand=True)
            cb_sch.bind("<<ComboboxSelected>>", lambda e: self.update_listbox())
        else:
            lbl = ttk.Label(self.filter_frame, text="Nessun filtro specifico per questa categoria.", font=FONT_SMALL, foreground=TEXT_MUTED)
            lbl.pack(anchor="w")
            self.filter_widgets.append(lbl)

    # -------------------------------------------------------------------------
    # CARICAMENTO ED ELENCO DATI
    # -------------------------------------------------------------------------
    def fetch_list(self):
        cat = self.category_var.get()

        # Compendio offline locale
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

        # Endpoints API Online
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
                # Fallback trasparente su dati SRD offline locali se assente connessione
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
        search_text = self.search_var.get().lower()
        cat = self.category_var.get()

        is_monster_cat = "mostri" in cat.lower() or "creature" in cat.lower() or "tome of beasts" in cat.lower()
        is_item_cat = any(k in cat.lower() for k in ["oggetti", "equipaggiamento", "armi", "pozioni", "magic-item"])
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
            name = item.get("name", "")
            if search_text and search_text not in name.lower():
                continue
            self.listbox.insert(tk.END, f"[Custom] {name}")

        # 2. SRD / Offline / Online items con filtri avanzati
        shown_count = 0
        for item in self.current_items:
            name = item.get("name", "")
            if search_text and search_text not in name.lower():
                continue

            # Filtri mostro
            if is_monster_cat:
                m_cr = item.get("challenge_rating", item.get("cr"))
                if m_cr is not None and not match_monster_cr(m_cr, cr_filter):
                    continue
                m_type = item.get("type")
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
            if is_monster_cat and "challenge_rating" in item:
                tag = f"[{item['challenge_rating']}] {name}"
            elif is_item_cat and "rarity" in item:
                tag = f"• {name} ({item['rarity']})"
            else:
                tag = name

            self.listbox.insert(tk.END, tag)
            shown_count += 1

        self.status_var.set(f"Elementi visualizzati: {shown_count}")

    # -------------------------------------------------------------------------
    # SELEZIONE E VISUALIZZAZIONE STATBLOCK
    # -------------------------------------------------------------------------
    def get_selected_item(self) -> Optional[Dict[str, Any]]:
        sel = self.listbox.curselection()
        if not sel:
            return None
        selected_text = self.listbox.get(sel[0])

        if selected_text.startswith("[Custom] "):
            real_name = selected_text.replace("[Custom] ", "", 1)
            cat = self.category_var.get()
            for item in self.compendium_manager.get_items(cat):
                if item.get("name") == real_name:
                    return item
            return None

        # Rimuove prefissi tag come '[CR]' o '•'
        clean_name = selected_text
        if clean_name.startswith("[") and "]" in clean_name:
            clean_name = clean_name.split("]", 1)[1].strip()
        elif clean_name.startswith("• "):
            clean_name = clean_name.replace("• ", "", 1).split(" (")[0].strip()

        for item in self.current_items:
            if item.get("name") == clean_name:
                return item
        return None

    def _on_item_selected(self, event=None):
        item = self.get_selected_item()
        if not item:
            return

        cat = self.category_var.get()
        is_monster = "mostri" in cat.lower() or "creature" in cat.lower() or "tome of beasts" in cat.lower()
        is_item = any(k in cat.lower() for k in ["oggetti", "equipaggiamento", "armi", "pozioni", "magic-item"])
        is_spell = "incantesimi" in cat.lower() or "spell" in cat.lower()

        # 1. Se l'item ha già i dati completi (offline o custom o cache)
        if item.get("is_custom") or item.get("actions") or item.get("armor_class") or item.get("type") or item.get("school"):
            self._render_item_in_statblock(item, is_monster, is_item, is_spell)
            return

        # 2. Controllo rapido nei record offline locali per evitare fetch
        item_name = item.get("name", "")
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
                    # Fallback testuale minimale
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
            self.statblock_view.show_generic(data.get("name", "Dettagli"), data)

    def _on_statblock_action(self, item_data: Dict[str, Any], category: str):
        """Callback invocata al click del pulsante primario in cima allo Statblock."""
        if not self.on_import_callback:
            return
        cat = self.category_var.get()
        if "mostri" in cat.lower():
            real_cat = "Mostri"
        elif "incantesimi" in cat.lower():
            real_cat = "Incantesimi"
        elif any(k in cat.lower() for k in ["oggetti", "equipaggiamento", "armi", "pozioni"]):
            real_cat = "Equipaggiamento"
        else:
            real_cat = cat

        self.on_import_callback(item_data, real_cat)
        messagebox.showinfo("Importazione", f"'{item_data.get('name')}' importato con successo!", parent=self)

    def import_selected(self):
        """Importa l'elemento selezionato nella listbox."""
        item = self.get_selected_item()
        if not item or not self.on_import_callback:
            return

        cat = self.category_var.get()
        if item.get("is_custom") or item.get("actions") or item.get("armor_class") or not item.get("url"):
            real_cat = "Mostri" if "mostri" in cat.lower() else cat
            self.on_import_callback(item, real_cat)
            return

        # Fetch asincrono se online
        url = item.get("url")
        self.status_var.set(f"Importazione di {item['name']}...")
        def do_import():
            try:
                req = urllib.request.Request("https://www.dnd5eapi.co" + url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3.5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                self.after(0, lambda: self.status_var.set("Importazione completata."))
                self.after(0, lambda: self.on_import_callback(data, cat))
            except Exception as e:
                self.after(0, lambda: self.status_var.set("Errore nell'importazione."))
                self.after(0, lambda err=e: messagebox.showerror("Errore", str(err)))

        threading.Thread(target=do_import, daemon=True).start()

    def view_details(self):
        """Retrocompatibilità: seleziona l'elemento e aggiorna lo statblock."""
        self._on_item_selected()

    def create_custom_item(self):
        cat = self.category_var.get()
        if cat.startswith("[OFFLINE] "):
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
