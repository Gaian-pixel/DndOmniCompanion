# client/character_manager_ui.py
"""
Modulo UI per la Gestione Offline dei Personaggi (D&D 5e).
Consente di creare, modificare, duplicare, eliminare ed esportare personaggi (PDF/JSON)
in completa autonomia, senza richiedere alcuna connessione a un server DM.
"""

import os
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

from common.theme import (
    apply_modern_window_style, BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT,
    BORDER_COLOR, ACCENT_GOLD, ACCENT_GREEN,
    TEXT_COLOR, TEXT_MUTED,
    FONT_TITLE, FONT_HEADER, FONT_MAIN, FONT_BOLD, FONT_SMALL
)
from common.messagebox import messagebox
from common.i18n import _t
from client.character_manager import CharacterManager, Character
from client.character_creation_wizard import CharacterCreationWizard
from client.character_sheet_ui import CharacterSheetUI, open_export_character_dialog


def get_class_icon(char_class: str) -> str:
    """Restituisce un'icona tematica in base alla classe del personaggio."""
    cls = (char_class or "").lower()
    if any(k in cls for k in ["guerriero", "fighter", "barbaro", "barbarian"]):
        return "⚔️"
    if any(k in cls for k in ["paladino", "paladin", "chierico", "cleric"]):
        return "🛡️"
    if any(k in cls for k in ["mago", "wizard", "stregone", "sorcerer", "warlock"]):
        return "🔮"
    if any(k in cls for k in ["ladro", "rogue", "monaco", "monk"]):
        return "🗡️"
    if any(k in cls for k in ["ranger", "druido", "druid"]):
        return "🏹"
    if any(k in cls for k in ["bardo", "bard"]):
        return "🎵"
    return "👤"


class CharacterManagerFrame(tk.Frame):
    """
    Frame autonomo per la gestione offline dei personaggi.
    Utilizzabile sia incorporato (mono-finestra in main.py) sia dentro CharacterManagerDialog.
    """
    def __init__(
        self, 
        master: tk.Tk | tk.Toplevel | tk.Frame, 
        manager: Optional[CharacterManager] = None, 
        on_select_callback: Optional[Callable[[Character], None]] = None,
        on_close_callback: Optional[Callable[[], None]] = None,
        on_create_wizard_callback: Optional[Callable[[], None]] = None,
        is_embedded: bool = False,
        **kwargs
    ):
        super().__init__(master, bg=BG_COLOR, **kwargs)
        self.manager = manager or CharacterManager()
        self.on_select_callback = on_select_callback
        self.on_close_callback = on_close_callback
        self.on_create_wizard_callback = on_create_wizard_callback
        self.is_embedded = is_embedded
        self.selected_character: Optional[Character] = None
        self.filtered_characters: list[Character] = []

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.apply_filter())

        self.setup_ui()
        self.refresh_list()

    def close_view(self):
        if self.on_close_callback:
            self.on_close_callback()
        else:
            self.destroy()

    def setup_ui(self):
        container = tk.Frame(self, bg=BG_COLOR, padx=16, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        # --- HEADER ---
        hdr_frame = tk.Frame(container, bg=BG_COLOR)
        hdr_frame.pack(fill=tk.X, pady=(0, 10))

        top_row = tk.Frame(hdr_frame, bg=BG_COLOR)
        top_row.pack(fill=tk.X)

        tk.Label(
            top_row,
            text="👤",
            font=("Segoe UI", 20),
            bg=BG_COLOR,
            fg=ACCENT_GOLD
        ).pack(side=tk.LEFT, padx=(0, 8))

        title_box = tk.Frame(top_row, bg=BG_COLOR)
        title_box.pack(side=tk.LEFT, fill=tk.X)

        tk.Label(
            title_box,
            text=_t("char_manager_header"),
            font=FONT_TITLE,
            bg=BG_COLOR,
            fg=ACCENT_GOLD
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text=_t("char_manager_desc"),
            font=FONT_SMALL,
            bg=BG_COLOR,
            fg=TEXT_MUTED
        ).pack(anchor="w")

        if self.on_close_callback:
            btn_back = ttk.Button(
                top_row,
                text="← Torna al Menu",
                command=self.close_view,
                style="Tool.TButton"
            )
            btn_back.pack(side=tk.RIGHT, padx=4)

        # Linea divisoria dorata sottile
        tk.Frame(hdr_frame, bg="#A37F2C", height=1).pack(fill=tk.X, pady=(8, 0))

        # --- SEARCH & FILTER BAR ---
        filter_frame = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=6)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(filter_frame, text="🔍", font=FONT_MAIN, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(2, 6))
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, font=FONT_MAIN)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        ttk.Button(
            filter_frame, 
            text="✖", 
            width=3, 
            style="Tool.TButton", 
            command=lambda: self.search_var.set("")
        ).pack(side=tk.LEFT)

        # --- MAIN SPLIT VIEW (2 COLONNE: LISTA & DETTAGLI) ---
        split_frame = tk.Frame(container, bg=BG_COLOR)
        split_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        split_frame.columnconfigure(0, weight=5)
        split_frame.columnconfigure(1, weight=5)
        split_frame.rowconfigure(0, weight=1)

        # === COLONNA SINISTRA: LISTA PERSONAGGI ===
        left_col = tk.Frame(split_frame, bg=BG_COLOR)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        # Treeview con scrollbar
        tree_container = tk.Frame(left_col, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        tree_container.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        columns = ("name", "class_lvl", "race", "campaign")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("name", text="Nome")
        self.tree.heading("class_lvl", text="Classe & Livello")
        self.tree.heading("race", text="Razza")
        self.tree.heading("campaign", text="Campagna")

        self.tree.column("name", width=140, anchor="w")
        self.tree.column("class_lvl", width=120, anchor="w")
        self.tree.column("race", width=90, anchor="w")
        self.tree.column("campaign", width=90, anchor="w")

        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_selection_changed)
        self.tree.bind("<Double-1>", lambda _: self.open_selected_sheet())

        # Barra pulsanti azione sotto la lista
        btn_bar = tk.Frame(left_col, bg=BG_COLOR)
        btn_bar.pack(fill=tk.X)

        ttk.Button(
            btn_bar, 
            text=_t("char_manager_btn_wizard"), 
            style="Primary.TButton", 
            command=self.create_wizard_character
        ).pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)

        ttk.Button(
            btn_bar, 
            text=_t("char_manager_btn_manual"), 
            command=self.create_manual_character
        ).pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)

        ttk.Button(
            btn_bar, 
            text=_t("char_manager_btn_duplicate"), 
            command=self.duplicate_selected_character
        ).pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)

        ttk.Button(
            btn_bar, 
            text=_t("char_manager_btn_delete"), 
            style="Danger.TButton", 
            command=self.delete_selected_character
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # === COLONNA DESTRA: DETTAGLI & ANTEPRIMA ===
        self.right_col = tk.Frame(split_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=14, pady=12)
        self.right_col.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self.render_empty_details()

        # --- BOTTOM BAR ---
        bottom_bar = tk.Frame(container, bg=BG_COLOR)
        bottom_bar.pack(fill=tk.X)

        self.count_lbl = tk.Label(bottom_bar, text="", font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED)
        self.count_lbl.pack(side=tk.LEFT)

        ttk.Button(bottom_bar, text="← Torna al Menu" if self.on_close_callback else _t("ok"), width=16, command=self.close_view).pack(side=tk.RIGHT)

    def refresh_list(self):
        """Ricarica tutti i personaggi dal manager e aggiorna la visualizzazione."""
        self.manager.load_characters()
        self.apply_filter()

    def apply_filter(self):
        query = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        self.filtered_characters = []

        for c in self.manager.characters:
            c_name = getattr(c, "name", "")
            c_class = getattr(c, "char_class", "")
            c_race = getattr(c, "race", "")
            c_camp = getattr(c, "campaign", "")
            search_blob = f"{c_name} {c_class} {c_race} {c_camp}".lower()

            if not query or query in search_blob:
                self.filtered_characters.append(c)
                camp_display = c_camp if c_camp else "-"
                self.tree.insert(
                    "", 
                    tk.END, 
                    iid=c.id, 
                    values=(c.name, f"{c.char_class} Lv.{c.level}", c.race or "-", camp_display)
                )

        count = len(self.manager.characters)
        self.count_lbl.config(text=_t("char_manager_count", count=count))

        # Se c'è un personaggio selezionato precedentemente ancora valido, selezionalo
        if self.selected_character and any(c.id == self.selected_character.id for c in self.filtered_characters):
            self.tree.selection_set(self.selected_character.id)
            self.render_character_details(self.selected_character)
        elif self.filtered_characters:
            first_id = self.filtered_characters[0].id
            self.tree.selection_set(first_id)
            self.selected_character = self.filtered_characters[0]
            self.render_character_details(self.selected_character)
        else:
            self.selected_character = None
            self.render_empty_details()

    def on_selection_changed(self, event=None):
        sel = self.tree.selection()
        if not sel:
            self.selected_character = None
            self.render_empty_details()
            return

        char_id = sel[0]
        self.selected_character = self.manager.get_character_by_id(char_id)
        if self.selected_character:
            self.render_character_details(self.selected_character)
        else:
            self.render_empty_details()

    def render_empty_details(self):
        for w in self.right_col.winfo_children():
            w.destroy()

        placeholder = tk.Frame(self.right_col, bg=SURFACE_COLOR)
        placeholder.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            placeholder,
            text="🛡️",
            font=("Segoe UI", 36),
            bg=SURFACE_COLOR,
            fg="#4A4D54"
        ).pack(pady=(40, 10))

        tk.Label(
            placeholder,
            text=_t("char_manager_no_selection"),
            font=FONT_MAIN,
            bg=SURFACE_COLOR,
            fg=TEXT_MUTED,
            wraplength=300,
            justify="center"
        ).pack()

    def render_character_details(self, char: Character):
        for w in self.right_col.winfo_children():
            w.destroy()

        scroll_canvas = tk.Canvas(self.right_col, bg=SURFACE_COLOR, highlightthickness=0, bd=0)
        scroll_bar = ttk.Scrollbar(self.right_col, orient="vertical", command=scroll_canvas.yview)
        scroll_frame = tk.Frame(scroll_canvas, bg=SURFACE_COLOR)

        scroll_frame.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        )
        canvas_window = scroll_canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def _on_canvas_configure(event):
            scroll_canvas.itemconfig(canvas_window, width=event.width)

        scroll_canvas.bind("<Configure>", _on_canvas_configure)
        scroll_canvas.configure(yscrollcommand=scroll_bar.set)

        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)

        # Header Personaggio
        top_box = tk.Frame(scroll_frame, bg=SURFACE_COLOR)
        top_box.pack(fill=tk.X, pady=(0, 8))

        if getattr(char, "avatar_b64", ""):
            from common.image_utils import render_avatar_on_canvas
            card_canvas = tk.Canvas(top_box, width=48, height=48, bg=SURFACE_COLOR, highlightthickness=0)
            card_canvas.pack(side=tk.LEFT, padx=(0, 10))
            render_avatar_on_canvas(card_canvas, char.avatar_b64, char.name, size=48)
        else:
            icon = get_class_icon(char.char_class)
            tk.Label(
                top_box,
                text=icon,
                font=("Segoe UI", 26),
                bg=SURFACE_COLOR,
                fg=ACCENT_GOLD
            ).pack(side=tk.LEFT, padx=(0, 10))

        name_box = tk.Frame(top_box, bg=SURFACE_COLOR)
        name_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            name_box,
            text=char.name,
            font=FONT_HEADER,
            bg=SURFACE_COLOR,
            fg=ACCENT_GOLD
        ).pack(anchor="w")

        sub_info = f"{char.race or 'Razza sconosciuta'} • {char.char_class or 'Avventuriero'} (Livello {char.level})"
        tk.Label(
            name_box,
            text=sub_info,
            font=FONT_SMALL,
            bg=SURFACE_COLOR,
            fg=TEXT_COLOR
        ).pack(anchor="w")

        camp_info = f"Campagna: {char.campaign}" if char.campaign else "Nessuna campagna assegnata"
        tk.Label(
            name_box,
            text=camp_info,
            font=FONT_SMALL,
            bg=SURFACE_COLOR,
            fg=TEXT_MUTED
        ).pack(anchor="w")

        # Linea divisoria
        tk.Frame(scroll_frame, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=(4, 8))

        # Badge Rapidi Combattimento (HP, CA, Velocità, Iniziativa)
        badges_frame = tk.Frame(scroll_frame, bg=SURFACE_COLOR)
        badges_frame.pack(fill=tk.X, pady=(0, 8))

        hp_text = f"❤️ HP: {char.hp_current}/{char.hp_max}"
        ac_text = f"🛡️ CA: {char.ac}"
        spd_text = f"👟 {char.speed} {getattr(char, 'speed_unit', 'ft')}"
        init_mod = getattr(char, "initiative", 0)
        init_sign = f"+{init_mod}" if init_mod >= 0 else str(init_mod)
        init_text = f"⚡ Iniz: {init_sign}"

        for txt, color in [(hp_text, ACCENT_GREEN), (ac_text, "#5C7CFA"), (spd_text, "#FAB005"), (init_text, "#FA5252")]:
            tk.Label(
                badges_frame,
                text=txt,
                font=FONT_BOLD,
                bg=SURFACE_COLOR_ALT,
                fg=color,
                padx=6,
                pady=3,
                highlightbackground=BORDER_COLOR,
                highlightthickness=1
            ).pack(side=tk.LEFT, padx=(0, 4), expand=True, fill=tk.X)

        # Griglia 6 Caratteristiche
        attr_container = tk.LabelFrame(scroll_frame, text="Caratteristiche Base", bg=SURFACE_COLOR, fg=TEXT_MUTED, font=FONT_SMALL, padx=8, pady=6)
        attr_container.pack(fill=tk.X, pady=(0, 8))

        attr_keys = ["FOR", "DES", "COS", "INT", "SAG", "CAR"]
        for idx, k in enumerate(attr_keys):
            score = char.attributes.get(k, 10)
            try:
                val = int(score)
                mod = (val - 10) // 2
                mod_str = f"+{mod}" if mod >= 0 else str(mod)
            except Exception:
                val = 10
                mod_str = "+0"

            col = idx % 3
            row = idx // 3

            cell = tk.Frame(attr_container, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=4, pady=3)
            cell.grid(row=row, column=col, sticky="nsew", padx=3, pady=3)
            attr_container.columnconfigure(col, weight=1)

            tk.Label(cell, text=k, font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED).pack()
            tk.Label(cell, text=f"{val} ({mod_str})", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).pack()

        # Sommario Inventario, Armi & Grimorio
        summary_frame = tk.Frame(scroll_frame, bg=SURFACE_COLOR)
        summary_frame.pack(fill=tk.X, pady=(0, 12))

        weapons_count = len(getattr(char, "weapons", []))
        spells_count = len(getattr(char, "spellbook", []))
        inv_count = sum(1 for it in getattr(char, "inventory_grid", []) if it) + len(getattr(char, "inventory", []))

        tk.Label(
            summary_frame,
            text=f"⚔️ {weapons_count} Armi  •  📜 {spells_count} Incantesimi  •  🎒 {inv_count} Oggetti",
            font=FONT_SMALL,
            bg=SURFACE_COLOR,
            fg=TEXT_MUTED
        ).pack(anchor="w")

        # --- TASTI DI AZIONE SCHEDA ---
        actions_box = tk.Frame(scroll_frame, bg=SURFACE_COLOR)
        actions_box.pack(fill=tk.X, pady=(4, 0))

        ttk.Button(
            actions_box,
            text=_t("char_manager_btn_open_sheet"),
            style="Gold.TButton",
            command=self.open_selected_sheet
        ).pack(fill=tk.X, pady=(0, 4))

        ttk.Button(
            actions_box,
            text=_t("char_manager_btn_export"),
            command=self.export_selected_character
        ).pack(fill=tk.X, pady=(0, 4))

        if self.on_select_callback:
            ttk.Button(
                actions_box,
                text=_t("char_manager_btn_select"),
                style="Primary.TButton",
                command=self.confirm_selection
            ).pack(fill=tk.X)

    def open_selected_sheet(self):
        """Apre la Scheda Personaggio completa (offline) per visualizzare o modificare tutti i dati."""
        if not self.selected_character:
            messagebox.showwarning("Attenzione", "Seleziona un personaggio dall'elenco prima di aprire la scheda.", parent=self)
            return

        def on_sheet_saved():
            self.refresh_list()

        sheet = CharacterSheetUI(
            self,
            self.selected_character,
            self.manager,
            is_connected=False,
            on_save_callback=on_sheet_saved
        )
        self.wait_window(sheet)
        self.refresh_list()

    def export_selected_character(self):
        """Esporta direttamente il personaggio in formato PDF ufficiale D&D o backup JSON."""
        if not self.selected_character:
            messagebox.showwarning("Attenzione", "Seleziona un personaggio da esportare.", parent=self)
            return
        open_export_character_dialog(self, self.selected_character)

    def create_wizard_character(self):
        """Apre la creazione guidata passo-passo."""
        if self.on_create_wizard_callback:
            self.on_create_wizard_callback()
            return

        def on_created(new_char):
            self.refresh_list()
            if new_char and hasattr(new_char, "id"):
                self.selected_character = new_char
                if self.tree.exists(new_char.id):
                    self.tree.selection_set(new_char.id)
                    self.tree.see(new_char.id)
                self.render_character_details(new_char)

        wizard = CharacterCreationWizard(self.winfo_toplevel(), self.manager, on_complete_callback=on_created)
        self.wait_window(wizard)

    def create_manual_character(self):
        """Crea un personaggio vuoto e apre direttamente la scheda per la compilazione manuale."""
        c = Character(name="Nuovo Eroe")
        self.manager.add_character(c)
        self.refresh_list()
        self.selected_character = c
        if self.tree.exists(c.id):
            self.tree.selection_set(c.id)
            self.tree.see(c.id)
        self.open_selected_sheet()

    def duplicate_selected_character(self):
        """Duplica il personaggio selezionato creando una copia indipendente."""
        if not self.selected_character:
            messagebox.showwarning("Attenzione", "Seleziona un personaggio da duplicare.", parent=self)
            return

        char_dict = self.selected_character.to_dict()
        char_dict["id"] = os.urandom(4).hex()
        char_dict["name"] = f"{self.selected_character.name} (Copia)"

        copy_char = Character.from_dict(char_dict)
        self.manager.add_character(copy_char)
        self.refresh_list()

        if self.tree.exists(copy_char.id):
            self.tree.selection_set(copy_char.id)
            self.tree.see(copy_char.id)
            self.selected_character = copy_char
            self.render_character_details(copy_char)

        messagebox.showinfo("Duplicazione", f"Personaggio duplicato con successo come '{copy_char.name}'.", parent=self)

    def delete_selected_character(self):
        """Elimina il personaggio selezionato previa conferma dell'utente."""
        if not self.selected_character:
            messagebox.showwarning("Attenzione", "Seleziona un personaggio da eliminare.", parent=self)
            return

        confirm_msg = _t("char_manager_delete_confirm", name=self.selected_character.name)
        if messagebox.askyesno("Conferma Eliminazione", confirm_msg, parent=self):
            deleted_name = self.selected_character.name
            self.manager.delete_character(self.selected_character)
            self.selected_character = None
            self.refresh_list()
            messagebox.showinfo("Eliminato", f"Il personaggio '{deleted_name}' è stato eliminato.", parent=self)

    def confirm_selection(self):
        """Conferma la selezione e invoca la callback esterna (se presente)."""
        if self.selected_character and self.on_select_callback:
            cb = self.on_select_callback
            char = self.selected_character
            self.close_view()
            cb(char)


class CharacterManagerDialog(tk.Toplevel):
    """
    Finestra modale per la gestione autonoma ed offline dei personaggi (retrocompatibile al 100%).
    Incapsula CharacterManagerFrame delegando metodi ed attributi.
    """
    def __init__(
        self, 
        master: tk.Tk | tk.Toplevel, 
        manager: Optional[CharacterManager] = None, 
        on_select_callback: Optional[Callable[[Character], None]] = None
    ):
        super().__init__(master)
        self.title(_t("char_manager_title"))
        self.minsize(860, 560)
        self.transient(master)
        self.grab_set()
        apply_modern_window_style(self)
        self.configure(bg=BG_COLOR)

        self._frame_internal = CharacterManagerFrame(
            self,
            manager=manager,
            on_select_callback=on_select_callback,
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
