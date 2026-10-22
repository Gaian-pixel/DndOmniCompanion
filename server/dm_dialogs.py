# server/dm_dialogs.py
"""
Dialoghi e finestre secondarie per il Dungeon Master (DM_GUI).
Decomposti per migliorare la manutenibilità e leggibilità del codice server.
"""
import re
import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog
from common.messagebox import messagebox
from common.theme import (
    apply_modern_window_style, BG_COLOR, BORDER_COLOR, TEXT_COLOR, TEXT_MUTED,
    SURFACE_COLOR, SURFACE_COLOR_ALT, ACCENT_GOLD,
    FONT_TITLE, FONT_HEADER, FONT_BOLD, FONT_MAIN, FONT_SMALL
)
from common.game_state import Player
from common.protocol import make_handout_broadcast, make_player_joined
from common.network_utils import broadcast
from common.i18n import _t, get_language, get_distance_unit


class TextHandoutDialog(tk.Toplevel):
    def __init__(self, dm_gui):
        super().__init__(dm_gui.master)
        self.dm_gui = dm_gui
        self.title(_t("handout_dialog_title", default="Condividi Documento / Nota Testuale"))
        self.minsize(580, 450)
        self.transient(dm_gui.master)
        self.grab_set()
        apply_modern_window_style(self)

        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=_t("handout_doc_title", default="Titolo del Documento:"), font=FONT_HEADER).pack(anchor=tk.W, pady=(0, 5))
        self.title_entry = ttk.Entry(main_frame, font=FONT_MAIN)
        self.title_entry.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(main_frame, text=_t("handout_doc_text", default="Testo da mostrare ai giocatori:"), font=FONT_HEADER).pack(anchor=tk.W, pady=(0, 5))
        self.content_text = scrolledtext.ScrolledText(
            main_frame, font=FONT_MAIN, wrap=tk.WORD, height=10,
            bg=SURFACE_COLOR, fg=TEXT_COLOR, insertbackground=ACCENT_GOLD
        )
        self.content_text.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text=_t("btn_send_to_players", default="Invia ai Giocatori (Ctrl+Invio)"), style="Success.TButton", command=self.on_share).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=_t("cancel", default="Annulla"), command=self.destroy).pack(side=tk.RIGHT)

        self.bind("<Control-Return>", lambda e: self.on_share())
        self.title_entry.focus_set()

    def on_share(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning(_t("warning", default="Attenzione"), _t("msg_title_required", default="Il titolo è obbligatorio."), parent=self)
            return
        content = self.content_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning(_t("warning", default="Attenzione"), _t("msg_content_cannot_empty", default="Il contenuto non può essere vuoto."), parent=self)
            return

        broadcast(self.dm_gui.server.game_state, make_handout_broadcast(title, None, content))
        messagebox.showinfo(_t("success", default="Successo"), _t("msg_handout_shared", default="Documento condiviso con tutti i giocatori connessi!"))
        self.destroy()


class CustomNPCDialog(tk.Toplevel):
    def __init__(self, dm_gui=None, master=None, on_save_callback=None, initial_data=None):
        parent_win = dm_gui.master if (dm_gui and hasattr(dm_gui, "master")) else (master or (dm_gui if isinstance(dm_gui, (tk.Tk, tk.Toplevel, tk.Widget)) else None))
        super().__init__(parent_win)
        self.dm_gui = dm_gui
        self.on_save_callback = on_save_callback
        self.initial_data = initial_data or {}
        self.avatar_b64 = self.initial_data.get("avatar_b64", "")
        self.avatar_path = self.initial_data.get("avatar_path", "")

        name_preset = self.initial_data.get("name", "")
        if self.initial_data:
            self.title(f"Scheda PNG / Mostro: {name_preset}" if name_preset else "Modifica Scheda PNG / Mostro")
        else:
            self.title(_t("custom_npc_title", default="Crea Nuovo PNG / Mostro Custom"))

        self.minsize(680, 700)
        self.geometry("740x740")
        if parent_win:
            self.transient(parent_win)
        self.grab_set()
        apply_modern_window_style(self)

        main_frame = ttk.Frame(self, padding="14")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # -------------------------------------------------------------
        # 1. HEADER CARD PROFILO (Nome, Ruolo, Fazione, Razza)
        # -------------------------------------------------------------
        header_card = ttk.LabelFrame(main_frame, text="👤 Profilo Personaggio Non Giocante (PNG)", padding="10")
        header_card.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header_card, text=_t("custom_npc_name", default="Nome PNG / Mostro:"), font=FONT_BOLD).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 4))
        self.name_entry = ttk.Entry(header_card, font=FONT_HEADER)
        if name_preset:
            self.name_entry.insert(0, name_preset)
        self.name_entry.grid(row=0, column=1, columnspan=3, sticky="ew", pady=(0, 6))

        ttk.Label(header_card, text="Ruolo / Professione:", font=FONT_SMALL).grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
        self.role_entry = ttk.Entry(header_card, font=FONT_MAIN)
        self.role_entry.insert(0, self.initial_data.get("role", "Cittadino"))
        self.role_entry.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=2)

        ttk.Label(header_card, text="Fazione:", font=FONT_SMALL).grid(row=1, column=2, sticky="w", padx=(0, 4), pady=2)
        self.faction_var = tk.StringVar(value=self.initial_data.get("faction", "Neutrale"))
        self.faction_combo = ttk.Combobox(header_card, textvariable=self.faction_var, values=["Alleato", "Neutrale", "Nemico"], state="readonly", width=12)
        self.faction_combo.grid(row=1, column=3, sticky="ew", pady=2)

        ttk.Label(header_card, text="Razza / Tipo:", font=FONT_SMALL).grid(row=2, column=0, sticky="w", padx=(0, 4), pady=(4, 0))
        self.race_entry = ttk.Entry(header_card, font=FONT_MAIN)
        self.race_entry.insert(0, self.initial_data.get("race", "Umanoide"))
        self.race_entry.grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=(4, 0))

        ttk.Label(header_card, text="Allineamento:", font=FONT_SMALL).grid(row=2, column=2, sticky="w", padx=(0, 4), pady=(4, 0))
        self.align_entry = ttk.Entry(header_card, font=FONT_MAIN, width=14)
        self.align_entry.insert(0, self.initial_data.get("alignment", "Neutrale"))
        self.align_entry.grid(row=2, column=3, sticky="ew", pady=(4, 0))

        header_card.columnconfigure(1, weight=1)
        header_card.columnconfigure(3, weight=1)

        # Riquadro Token Mappa per Mostro / PNG
        avatar_frame = ttk.Frame(header_card)
        avatar_frame.grid(row=0, column=4, rowspan=3, padx=(12, 0), sticky="n")

        ttk.Label(avatar_frame, text="Token Mappa:", font=FONT_SMALL).pack(anchor="center")
        self.token_canvas = tk.Canvas(avatar_frame, width=64, height=64, bg="#181A20", highlightthickness=0)
        self.token_canvas.pack(pady=2)

        token_btn_box = ttk.Frame(avatar_frame)
        token_btn_box.pack(fill=tk.X, pady=(2, 0))

        def _update_npc_avatar_preview():
            from common.image_utils import render_avatar_on_canvas
            c_name = self.name_entry.get().strip() if hasattr(self, "name_entry") else "PNG"
            render_avatar_on_canvas(self.token_canvas, getattr(self, "avatar_b64", ""), c_name, size=64)

        def _pick_npc_avatar():
            from common.image_utils import open_avatar_file_dialog
            b64, path = open_avatar_file_dialog(parent=self)
            if b64:
                self.avatar_b64 = b64
                self.avatar_path = path
                _update_npc_avatar_preview()

        def _clear_npc_avatar():
            self.avatar_b64 = ""
            self.avatar_path = ""
            _update_npc_avatar_preview()

        ttk.Button(token_btn_box, text="📁 Scegli", command=_pick_npc_avatar, width=7).pack(side=tk.LEFT, padx=1)
        ttk.Button(token_btn_box, text="❌", command=_clear_npc_avatar, width=3).pack(side=tk.LEFT, padx=1)

        _update_npc_avatar_preview()

        # -------------------------------------------------------------
        # 2. NOTEBOOK A SCHEDE TABELLARI (Combattimento, Azioni, Equip, Note DM)
        # -------------------------------------------------------------
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # === SCHEDA 1: STATISTICHE & CARATTERISTICHE 5E ===
        tab_stats = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_stats, text="📊 Statistiche & Attributi")

        stats_box = ttk.LabelFrame(tab_stats, text="⚔️ Parametri di Combattimento:", padding="8")
        stats_box.pack(fill=tk.X, pady=(0, 10))

        grid_frame = ttk.Frame(stats_box)
        grid_frame.pack(fill=tk.X)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(3, weight=1)
        grid_frame.columnconfigure(5, weight=1)

        init_hp = str(self.initial_data.get("hp", self.initial_data.get("hit_points", 15)))
        ttk.Label(grid_frame, text=_t("custom_npc_hp", default="HP Massimi:"), font=FONT_BOLD).grid(row=0, column=0, padx=(0, 6), pady=4, sticky=tk.W)
        self.hp_entry = ttk.Entry(grid_frame, font=FONT_MAIN, width=8)
        self.hp_entry.insert(0, init_hp)
        self.hp_entry.grid(row=0, column=1, pady=4, sticky=tk.W)

        init_ac = str(self.initial_data.get("ac", self.initial_data.get("armor_class", 12)))
        ttk.Label(grid_frame, text=_t("custom_npc_ac", default="Classe Armatura (CA):"), font=FONT_BOLD).grid(row=0, column=2, padx=(12, 6), pady=4, sticky=tk.W)
        self.ac_entry = ttk.Entry(grid_frame, font=FONT_MAIN, width=8)
        self.ac_entry.insert(0, init_ac)
        self.ac_entry.grid(row=0, column=3, pady=4, sticky=tk.W)

        init_init = str(self.initial_data.get("initiative", 0))
        ttk.Label(grid_frame, text=_t("custom_npc_init", default="Iniziativa (bonus):"), font=FONT_BOLD).grid(row=0, column=4, padx=(12, 6), pady=4, sticky=tk.W)
        self.init_entry = ttk.Entry(grid_frame, font=FONT_MAIN, width=8)
        self.init_entry.insert(0, init_init)
        self.init_entry.grid(row=0, column=5, pady=4, sticky=tk.W)

        dist_unit = get_distance_unit()
        default_spd = "9" if dist_unit == "m" else "30"
        init_spd = str(self.initial_data.get("speed", default_spd))
        ttk.Label(grid_frame, text=f"Velocità ({dist_unit}):", font=FONT_BOLD).grid(row=1, column=0, padx=(0, 6), pady=4, sticky=tk.W)
        self.speed_entry = ttk.Entry(grid_frame, font=FONT_MAIN, width=8)
        self.speed_entry.insert(0, init_spd)
        self.speed_entry.grid(row=1, column=1, pady=4, sticky=tk.W)

        init_cr = str(self.initial_data.get("cr", self.initial_data.get("challenge_rating", "1")))
        ttk.Label(grid_frame, text="Grado Sfida (CR):", font=FONT_BOLD).grid(row=1, column=2, padx=(12, 6), pady=4, sticky=tk.W)
        self.cr_entry = ttk.Entry(grid_frame, font=FONT_MAIN, width=8)
        self.cr_entry.insert(0, init_cr)
        self.cr_entry.grid(row=1, column=3, pady=4, sticky=tk.W)

        init_xp = str(self.initial_data.get("xp", 50))
        ttk.Label(grid_frame, text="XP (Esperienza):", font=FONT_BOLD).grid(row=1, column=4, padx=(12, 6), pady=4, sticky=tk.W)
        self.xp_entry = ttk.Entry(grid_frame, font=FONT_MAIN, width=8)
        self.xp_entry.insert(0, init_xp)
        self.xp_entry.grid(row=1, column=5, pady=4, sticky=tk.W)

        attr_box = ttk.LabelFrame(tab_stats, text="🎲 Punteggi di Caratteristica D&D 5e (Ability Scores):", padding="8")
        attr_box.pack(fill=tk.X, pady=(0, 4))

        attr_inner = tk.Frame(attr_box, bg=SURFACE_COLOR_ALT, padx=6, pady=8)
        attr_inner.pack(fill=tk.X, expand=True)

        self.stat_entries = {}
        self.stat_mod_labels = {}
        stats_def = [
            ("FOR", "FOR", "Forza", "10"),
            ("DES", "DES", "Destrezza", "10"),
            ("COS", "COS", "Costituzione", "10"),
            ("INT", "INT", "Intelligenza", "10"),
            ("SAG", "SAG", "Saggezza", "10"),
            ("CAR", "CAR", "Carisma", "10")
        ]

        preset_attrs = self.initial_data.get("attributes", {})
        if not preset_attrs and self.initial_data:
            from common.srd_offline import extract_and_normalize_attributes
            preset_attrs = extract_and_normalize_attributes(self.initial_data, name_preset)

        for code, label, full_name, default_val in stats_def:
            col_frame = tk.Frame(attr_inner, bg=SURFACE_COLOR_ALT)
            col_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=3)

            tk.Label(col_frame, text=label, font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack()

            alias = {"FOR": "STR", "DES": "DEX", "COS": "CON", "INT": "INT", "SAG": "WIS", "CAR": "CHA"}[code]
            val_stat = str(preset_attrs.get(code, preset_attrs.get(alias, default_val)))
            var = tk.StringVar(value=val_stat)
            e = tk.Entry(col_frame, textvariable=var, font=("Segoe UI", 11, "bold"), width=4, justify="center",
                         bg=SURFACE_COLOR, fg=TEXT_COLOR, insertbackground=ACCENT_GOLD, relief=tk.SOLID, bd=1)
            e.pack(pady=2)
            self.stat_entries[code] = (e, var)

            try:
                mod_init = (int(val_stat) - 10) // 2
                mod_text = f"({'+' if mod_init >= 0 else ''}{mod_init})"
            except Exception:
                mod_text = "(+0)"

            mod_lbl = tk.Label(col_frame, text=mod_text, font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED)
            mod_lbl.pack()
            self.stat_mod_labels[code] = mod_lbl

            var.trace_add("write", lambda *args, c=code, v=var, ml=mod_lbl: self._on_stat_changed(c, v, ml))

        # === SCHEDA 2: AZIONI & ATTACCHI ===
        tab_actions = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_actions, text="⚔️ Azioni & Attacchi")

        ttk.Label(tab_actions, text="Azioni di Combattimento, Attacchi in Mischia/Distanza e Tratti Speciali:", font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        self.actions_text = scrolledtext.ScrolledText(
            tab_actions, font=FONT_MAIN, wrap=tk.WORD, height=12,
            bg=SURFACE_COLOR, fg=TEXT_COLOR, insertbackground=ACCENT_GOLD
        )
        self.actions_text.pack(fill=tk.BOTH, expand=True)
        raw_act = self.initial_data.get("actions", "")
        if isinstance(raw_act, list):
            acts_str = "\n\n".join(
                f"⚔️ {a.get('name', 'Azione')}: {a.get('desc', '')}" if isinstance(a, dict) else str(a)
                for a in raw_act
            )
        else:
            acts_str = str(raw_act or "")
        if acts_str:
            self.actions_text.insert("1.0", acts_str)
        else:
            self.actions_text.insert("1.0", "Spada Corta: Tiro per Colpire +4, Portata 1.5m, Danno 1d6+2 perforante.\nArco Corto: TpC +4, Gittata 24/96m, Danno 1d6+2 perforante.")

        # === SCHEDA 3: EQUIPAGGIAMENTO & LOOT ===
        tab_equip = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_equip, text="🎒 Equipaggiamento & Loot")

        ttk.Label(tab_equip, text="Oggetti Posseduti, Armature, Monete (MO/MA/MR) o Loot Rilasciato:", font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        self.equipment_text = scrolledtext.ScrolledText(
            tab_equip, font=FONT_MAIN, wrap=tk.WORD, height=12,
            bg=SURFACE_COLOR, fg=TEXT_COLOR, insertbackground=ACCENT_GOLD
        )
        self.equipment_text.pack(fill=tk.BOTH, expand=True)
        raw_eq = self.initial_data.get("equipment", self.initial_data.get("inventory", ""))
        if isinstance(raw_eq, list):
            eq_str = "\n".join(
                f"- {item.get('name', 'Oggetto')} (x{item.get('qty', 1)})" if isinstance(item, dict) else str(item)
                for item in raw_eq
            )
        else:
            eq_str = str(raw_eq or "")
        if eq_str:
            self.equipment_text.insert("1.0", eq_str)
        else:
            self.equipment_text.insert("1.0", "Cotta di cuoio, borsa da cintura con 15 MO, chiave antica arrugginita.")

        # === SCHEDA 4: BACKGROUND & NOTE DM ===
        tab_notes = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_notes, text="📜 Background & Note DM")

        ttk.Label(tab_notes, text="Personalità, Tratti, Segreti per il DM e Agganci di Trama:", font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        self.notes_text = scrolledtext.ScrolledText(
            tab_notes, font=FONT_MAIN, wrap=tk.WORD, height=12,
            bg=SURFACE_COLOR, fg=TEXT_COLOR, insertbackground=ACCENT_GOLD
        )
        self.notes_text.pack(fill=tk.BOTH, expand=True)
        init_notes = str(self.initial_data.get("notes", self.initial_data.get("desc", "")) or "")
        if init_notes:
            self.notes_text.insert("1.0", init_notes)
        else:
            self.notes_text.insert("1.0", "PERSONALITÀ: Diffidente verso gli stranieri ma fedele alla causa.\nSEGRETO DM: Custodisce l'amuleto che apre la porta segreta del tempio.")

        # -------------------------------------------------------------
        # 3. AZIONI INFERIORI (Salva / Annulla)
        # -------------------------------------------------------------
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_frame, text="💾 Salva Scheda PNG (Ctrl+Invio)", style="Success.TButton", command=self.on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=_t("cancel", default="Annulla"), command=self.destroy).pack(side=tk.RIGHT)

        self.bind("<Control-Return>", lambda e: self.on_save())
        self.name_entry.focus_set()

    def _on_stat_changed(self, code, var, mod_lbl):
        try:
            val = int(var.get().strip())
            mod = (val - 10) // 2
            mod_lbl.config(text=f"({'+' if mod >= 0 else ''}{mod})")
            if code == "DES" and hasattr(self, "init_entry"):
                self.init_entry.delete(0, tk.END)
                self.init_entry.insert(0, str(mod))
        except Exception:
            mod_lbl.config(text="(--)")

    def on_save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning(_t("warning", default="Attenzione"), _t("msg_name_required", default="Il nome è obbligatorio."), parent=self)
            return

        old_name = self.initial_data.get("name") if self.initial_data else None
        if name != old_name and self.dm_gui and hasattr(self.dm_gui, "server") and hasattr(self.dm_gui.server, "game_state"):
            if self.dm_gui.server.game_state.find_player(name):
                messagebox.showerror(_t("error", default="Errore"), _t("msg_entity_exists", default="Un'entità con questo nome esiste già."), parent=self)
                return

        try:
            hp = int(self.hp_entry.get() or 10)
            init = int(self.init_entry.get() or 0)
            ac = int(self.ac_entry.get() or 10)
            raw_spd = float((self.speed_entry.get() or "30").replace(",", "."))
            speed = int(raw_spd) if raw_spd == int(raw_spd) else round(raw_spd, 1)
            cr = self.cr_entry.get().strip() or "1"
            xp = int(self.xp_entry.get() or 50)

            attrs = {}
            for code, (entry_widget, var) in self.stat_entries.items():
                val_str = var.get().strip()
                attrs[code] = int(val_str) if val_str else 10
        except ValueError:
            messagebox.showerror(_t("error", default="Errore"), _t("msg_stat_integer", default="I valori statistici e le caratteristiche devono essere numeri validi."), parent=self)
            return

        from common.srd_offline import extract_and_normalize_attributes
        full_attrs = extract_and_normalize_attributes({"attributes": attrs}, name)

        role = self.role_entry.get().strip() or "Cittadino"
        faction = self.faction_combo.get().strip() or "Neutrale"
        race = self.race_entry.get().strip() or "Umanoide"
        alignment = self.align_entry.get().strip() or "Neutrale"
        actions = self.actions_text.get("1.0", tk.END).strip()
        equipment = self.equipment_text.get("1.0", tk.END).strip()
        notes = self.notes_text.get("1.0", tk.END).strip()

        monster_sheet = {
            "name": name,
            "role": role,
            "faction": faction,
            "race": race,
            "alignment": alignment,
            "hp": hp,
            "hp_current": hp,
            "hp_max": hp,
            "hit_points": hp,
            "ac": ac,
            "armor_class": ac,
            "initiative": init,
            "speed": speed,
            "speed_unit": get_distance_unit(),
            "cr": cr,
            "challenge_rating": cr,
            "xp": xp,
            "attributes": full_attrs,
            "strength": full_attrs.get("FOR", 10),
            "dexterity": full_attrs.get("DES", 10),
            "constitution": full_attrs.get("COS", 10),
            "intelligence": full_attrs.get("INT", 10),
            "wisdom": full_attrs.get("SAG", 10),
            "charisma": full_attrs.get("CAR", 10),
            "actions": actions,
            "equipment": equipment,
            "notes": notes,
            "desc": notes,
            "avatar_b64": getattr(self, "avatar_b64", ""),
            "avatar_path": getattr(self, "avatar_path", ""),
            "is_custom": True
        }

        if self.initial_data:
            merged = dict(self.initial_data)
            merged.update(monster_sheet)
            monster_sheet = merged

        if self.on_save_callback:
            self.on_save_callback(monster_sheet)
            self.destroy()
            return

        if self.dm_gui and hasattr(self.dm_gui, "server"):
            npc = Player(name, None, None)
            npc.hp = hp
            npc.max_hp = hp
            npc.initiative = init
            npc.speed = speed
            npc.is_party_member = (faction == "Alleato")
            npc.avatar_b64 = getattr(self, "avatar_b64", "")
            npc.full_sheet = monster_sheet

            self.dm_gui.server.game_state.add_player(npc)
            broadcast(self.dm_gui.server.game_state, make_player_joined(npc.to_dict()))
            self.dm_gui.log_to_chat(f"[SISTEMA] PNG Custom '{name}' ({role}, {faction}) aggiunto alla sessione.")
            if hasattr(self.dm_gui, "update_player_list"):
                self.dm_gui.update_player_list()

        self.destroy()


class DMPlayerSheetViewer(tk.Toplevel):
    def __init__(self, master, player_name, sheet):
        super().__init__(master)
        self.title(_t("sheet_viewer_title", name=player_name, default=f"Scheda Personaggio: {player_name}"))
        self.minsize(700, 680)
        self.transient(master)
        self.grab_set()
        apply_modern_window_style(self)
        
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Header Card
        header_card = ttk.LabelFrame(main_frame, text=_t("general_info", default="Informazioni Generali"), padding="10")
        header_card.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header_card, text=sheet.get("name", player_name), font=FONT_TITLE).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 5))
        
        ttk.Label(header_card, text=_t("lbl_class", default="Classe:"), font=FONT_BOLD).grid(row=1, column=0, sticky="w", padx=(0, 5))
        ttk.Label(header_card, text=f"{sheet.get('char_class', '-')} (Lvl {sheet.get('level', 1)})").grid(row=1, column=1, sticky="w", padx=(0, 20))
        ttk.Label(header_card, text=_t("lbl_race", default="Razza:"), font=FONT_BOLD).grid(row=1, column=2, sticky="w", padx=(0, 5))
        ttk.Label(header_card, text=f"{sheet.get('race', '-')}").grid(row=1, column=3, sticky="w")

        ttk.Label(header_card, text=_t("lbl_alignment", default="Allineamento:"), font=FONT_BOLD).grid(row=2, column=0, sticky="w", padx=(0, 5), pady=(4, 0))
        ttk.Label(header_card, text=f"{sheet.get('alignment', '-')}").grid(row=2, column=1, sticky="w", padx=(0, 20), pady=(4, 0))
        ttk.Label(header_card, text=_t("lbl_background", default="Background:"), font=FONT_BOLD).grid(row=2, column=2, sticky="w", padx=(0, 5), pady=(4, 0))
        ttk.Label(header_card, text=f"{sheet.get('background', '-')}").grid(row=2, column=3, sticky="w", pady=(4, 0))

        # 2. Notebook a Schede Tabellari
        nb = ttk.Notebook(main_frame)
        nb.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Statistiche & Caratteristiche
        tab_stats = ttk.Frame(nb, padding="10")
        nb.add(tab_stats, text=_t("tab_stats_attributes", default="📊 Statistiche & Attributi"))

        vital_frame = ttk.LabelFrame(tab_stats, text=_t("combat", default="Combattimento"), padding="10")
        vital_frame.pack(fill=tk.X, pady=(0, 10))
        
        from common.srd_offline import normalize_ac_value, normalize_speed_value
        hp_cur = sheet.get("hp_current", 0)
        hp_max = sheet.get("hp_max", 0)
        ac = normalize_ac_value(sheet.get("ac", sheet.get("armor_class", 10)))
        init = sheet.get("initiative", 0)
        raw_speed = sheet.get("speed", 30)
        speed_val, speed_disp, speed_unit = normalize_speed_value(raw_speed, default_unit=sheet.get("speed_unit"))

        for col, (label, val, subtitle, tooltip_str) in enumerate([
            (_t("hit_points", default="Punti Ferita (HP)"), f"{hp_cur} / {hp_max}", None, None),
            (_t("armor_class", default="Classe Armatura (CA)"), str(ac), None, f"CA Base: {ac}"),
            (_t("initiative", default="Iniziativa"), f"{'+' if init >= 0 else ''}{init}", None, None),
            (_t("speed", default="Velocità"), f"{speed_val} {speed_unit}", (speed_disp if " • " in speed_disp else None), speed_disp)
        ]):
            box = ttk.Frame(vital_frame, relief="ridge", padding="8")
            box.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5)
            ttk.Label(box, text=label, font=FONT_SMALL, anchor="center").pack()
            ttk.Label(box, text=val, font=FONT_HEADER, anchor="center").pack(pady=2)
            if subtitle:
                ttk.Label(box, text=subtitle, font=("Segoe UI", 8, "italic"), foreground="#9CA3AF", anchor="center").pack()
            if tooltip_str:
                from components.ui_components import ToolTip
                ToolTip(box, tooltip_str)

        attr_frame = ttk.LabelFrame(tab_stats, text=_t("ability_scores", default="Punteggi di Caratteristica"), padding="10")
        attr_frame.pack(fill=tk.BOTH, expand=True)

        attr_tree = ttk.Treeview(attr_frame, columns=("Attr", "Score", "Mod"), show="headings", height=6)
        attr_tree.heading("Attr", text=_t("col_ability", default="Caratteristica"))
        attr_tree.heading("Score", text=_t("col_base_score", default="Punteggio Base"))
        attr_tree.heading("Mod", text=_t("col_modifier", default="Modificatore"))
        attr_tree.column("Attr", width=150, anchor="center")
        attr_tree.column("Score", width=120, anchor="center")
        attr_tree.column("Mod", width=120, anchor="center")
        attr_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        attrs = sheet.get("attributes", {})
        if not attrs or all(v == 10 for v in attrs.values()):
            from common.srd_offline import extract_and_normalize_attributes
            attrs = extract_and_normalize_attributes(sheet, sheet.get("name", player_name))

        if get_language() == "en":
            attr_names = {
                "FOR": "Strength (STR)", "DES": "Dexterity (DEX)", "COS": "Constitution (CON)",
                "INT": "Intelligence (INT)", "SAG": "Wisdom (WIS)", "CAR": "Charisma (CHA)"
            }
        else:
            attr_names = {
                "FOR": "Forza (FOR)", "DES": "Destrezza (DES)", "COS": "Costituzione (COS)",
                "INT": "Intelligenza (INT)", "SAG": "Saggezza (SAG)", "CAR": "Carisma (CAR)"
            }
        for k in ["FOR", "DES", "COS", "INT", "SAG", "CAR"]:
            score = attrs.get(k)
            if score is None:
                alias = {"FOR": "STR", "DES": "DEX", "COS": "CON", "INT": "INT", "SAG": "WIS", "CAR": "CHA"}[k]
                score = attrs.get(alias, 10)
            mod = (score - 10) // 2
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            attr_tree.insert("", tk.END, values=(attr_names.get(k, k), score, mod_str))

        # Tab Azioni & Attacchi (Mostri / PNG)
        actions = sheet.get("actions", [])
        if not actions and player_name:
            try:
                from common.srd_offline import get_monster_offline
                srd_m = get_monster_offline(player_name)
                if srd_m and srd_m.get("actions"):
                    actions = srd_m.get("actions", [])
            except Exception:
                pass

        if actions:
            from common.srd_offline import format_monster_action_tooltip
            from components.ui_components import ToolTip
            tab_act = ttk.Frame(nb, padding="10")
            nb.add(tab_act, text=_t("tab_actions_attacks", default="⚔️ Azioni & Attacchi"))

            ttk.Label(tab_act, text=f"Azioni di Combattimento ({len(actions)}):", font=FONT_BOLD).pack(anchor="w", pady=(0, 5))
            
            act_container = ttk.Frame(tab_act)
            act_container.pack(fill=tk.BOTH, expand=True)

            act_canvas = tk.Canvas(act_container, bg=SURFACE_COLOR, highlightthickness=0)
            act_scrollbar = ttk.Scrollbar(act_container, orient="vertical", command=act_canvas.yview)
            act_scrollable_frame = ttk.Frame(act_canvas)

            act_scrollable_frame.bind(
                "<Configure>",
                lambda e: act_canvas.configure(scrollregion=act_canvas.bbox("all"))
            )
            act_canvas.create_window((0, 0), window=act_scrollable_frame, anchor="nw")
            act_canvas.configure(yscrollcommand=act_scrollbar.set)

            act_canvas.pack(side="left", fill="both", expand=True)
            act_scrollbar.pack(side="right", fill="y")

            for act in actions:
                a_name = act.get("name", "Azione") if isinstance(act, dict) else str(act).split(".")[0].strip()
                a_desc = act.get("desc", "") if isinstance(act, dict) else str(act)
                
                card = ttk.LabelFrame(act_scrollable_frame, text=f"⚔️ {a_name}", padding="8")
                card.pack(fill=tk.X, expand=True, padx=4, pady=4)
                
                tip_text = format_monster_action_tooltip(act, player_name)
                ToolTip(card, tip_text)

                info_parts = []
                if isinstance(act, dict) and act.get("attack_bonus"):
                    info_parts.append(f"TpC: +{act['attack_bonus']}")
                m_hit = re.search(r'Hit:\s*([0-9]+\s*\([^)]+\)[^.]+)', a_desc)
                if m_hit:
                    info_parts.append(f"Danno: {m_hit.group(1).strip()}")
                elif isinstance(act, dict) and act.get("damage_dice"):
                    info_parts.append(f"Danno: {act['damage_dice']}")
                
                if info_parts:
                    ttk.Label(card, text="  •  ".join(info_parts), font=FONT_BOLD, foreground=ACCENT_GOLD).pack(anchor="w")
                
                if a_desc:
                    lbl_desc = ttk.Label(card, text=a_desc, wraplength=580, justify="left", font=FONT_SMALL)
                    lbl_desc.pack(anchor="w", pady=(2, 0))
                    ToolTip(lbl_desc, tip_text)

        # Tab Equipaggiamento & Inventario (Tabella)
        tab_inv = ttk.Frame(nb, padding="10")
        nb.add(tab_inv, text=_t("tab_inventory", default="🎒 Inventario"))

        inv_tree_frame = ttk.Frame(tab_inv)
        inv_tree_frame.pack(fill=tk.BOTH, expand=True)

        inv_tree = ttk.Treeview(inv_tree_frame, columns=("Slot", "Nome", "Tipo", "Qty", "Desc"), show="headings")
        inv_tree.heading("Slot", text="#")
        inv_tree.heading("Nome", text=_t("col_item_name", default="Nome Oggetto"))
        inv_tree.heading("Tipo", text=_t("col_type", default="Tipologia"))
        inv_tree.heading("Qty", text=_t("col_quantity", default="Quantità"))
        inv_tree.heading("Desc", text=_t("col_desc_effect", default="Descrizione / Effetto"))
        inv_tree.column("Slot", width=40, anchor="center")
        inv_tree.column("Nome", width=150)
        inv_tree.column("Tipo", width=110, anchor="center")
        inv_tree.column("Qty", width=60, anchor="center")
        inv_tree.column("Desc", width=250)
        inv_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inv_scroll = ttk.Scrollbar(inv_tree_frame, orient=tk.VERTICAL, command=inv_tree.yview)
        inv_tree.configure(yscroll=inv_scroll.set)
        inv_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        grid = sheet.get("inventory_grid", [])
        slot_idx = 1
        if isinstance(grid, list):
            for it in grid:
                if it:
                    inv_tree.insert("", tk.END, values=(
                        str(slot_idx),
                        it.get("name", "Sconosciuto"),
                        it.get("type", "Oggetto"),
                        str(it.get("qty", 1)),
                        it.get("desc", "-")
                    ))
                    slot_idx += 1
        raw_inv = sheet.get("inventory")
        if raw_inv and isinstance(raw_inv, str) and slot_idx == 1:
            inv_tree.insert("", tk.END, values=("1", _t("text_inventory", default="Inventario Testuale"), "Testo", "1", raw_inv))

        curr_frame = ttk.LabelFrame(tab_inv, text=_t("coin_pouch", default="Borsa delle Monete"), padding="8")
        curr_frame.pack(fill=tk.X, pady=(10, 0))
        currency = sheet.get("currency", {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0})
        if not isinstance(currency, dict):
            currency = {"MO": sheet.get("gp", 0)}
        
        if get_language() == "en":
            currency_labels = [("MR", "Copper (CP)"), ("MA", "Silver (SP)"), ("ME", "Electrum (EP)"), ("MO", "Gold (GP)"), ("MP", "Platinum (PP)")]
        else:
            currency_labels = [("MR", "Rame (MR)"), ("MA", "Argento (MA)"), ("ME", "Electrum (ME)"), ("MO", "Oro (MO)"), ("MP", "Platino (MP)")]

        for c_key, c_name in currency_labels:
            c_box = ttk.Frame(curr_frame, padding="5")
            c_box.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
            ttk.Label(c_box, text=c_name, font=FONT_SMALL).pack()
            ttk.Label(c_box, text=str(currency.get(c_key, 0)), font=FONT_BOLD, foreground=ACCENT_GOLD if c_key=="MO" else TEXT_COLOR).pack()

        # Tab 3: Grimorio & Incantesimi (Tabella)
        tab_spells = ttk.Frame(nb, padding="10")
        nb.add(tab_spells, text=_t("tab_spellbook", default="✨ Grimorio"))

        slots_frame = ttk.LabelFrame(tab_spells, text=_t("spell_slots", default="Slot Incantesimo"), padding="8")
        slots_frame.pack(fill=tk.X, pady=(0, 10))
        spell_slots = sheet.get("spell_slots", {})
        if isinstance(spell_slots, dict):
            for i in range(1, 10):
                s_info = spell_slots.get(str(i), {"max": 0, "current": 0})
                if isinstance(s_info, dict):
                    m = s_info.get("max", 0)
                    c = s_info.get("current", 0)
                elif isinstance(s_info, list):
                    m = s_info[1] if len(s_info) > 1 else 0
                    c = s_info[0] if len(s_info) > 0 else 0
                else:
                    m, c = 0, 0
                s_box = ttk.Frame(slots_frame, padding="4")
                s_box.pack(side=tk.LEFT, expand=True)
                ttk.Label(s_box, text=f"Lvl {i}", font=FONT_SMALL).pack()
                ttk.Label(s_box, text=f"{c}/{m}", font=FONT_BOLD).pack()

        spells_tree_frame = ttk.Frame(tab_spells)
        spells_tree_frame.pack(fill=tk.BOTH, expand=True)

        spells_tree = ttk.Treeview(spells_tree_frame, columns=("Lvl", "Nome", "Tempo", "Raggio", "Desc"), show="headings")
        spells_tree.heading("Lvl", text=_t("col_level", default="Livello"))
        spells_tree.heading("Nome", text=_t("col_spell_name", default="Nome Incantesimo"))
        spells_tree.heading("Tempo", text=_t("col_casting_time", default="Lancio"))
        spells_tree.heading("Raggio", text=_t("col_range", default="Raggio / Gittata"))
        spells_tree.heading("Desc", text=_t("col_desc_effect", default="Descrizione / Effetto"))
        spells_tree.column("Lvl", width=70, anchor="center")
        spells_tree.column("Nome", width=140)
        spells_tree.column("Tempo", width=80, anchor="center")
        spells_tree.column("Raggio", width=80, anchor="center")
        spells_tree.column("Desc", width=250)
        spells_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        spells_scroll = ttk.Scrollbar(spells_tree_frame, orient=tk.VERTICAL, command=spells_tree.yview)
        spells_tree.configure(yscroll=spells_scroll.set)
        spells_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        spellbook = sheet.get("spellbook", [])
        if isinstance(spellbook, list):
            for sp in spellbook:
                if isinstance(sp, dict):
                    lvl = sp.get("level", 0)
                    lvl_display = _t("cantrip", default="Trucchetto") if lvl == 0 else f"{_t('col_level', default='Livello')} {lvl}"
                    spells_tree.insert("", tk.END, values=(
                        lvl_display,
                        sp.get("name", "Sconosciuto"),
                        sp.get("time", "-"),
                        sp.get("range", "-"),
                        sp.get("desc", "-")
                    ))
        raw_spells = sheet.get("spells")
        if raw_spells and isinstance(raw_spells, str) and not spellbook:
            spells_tree.insert("", tk.END, values=("-", _t("text_spells", default="Incantesimi Testuali"), "-", "-", raw_spells))

        # Tab 4: Privilegi & Note
        tab_notes = ttk.Frame(nb, padding="10")
        nb.add(tab_notes, text=_t("tab_features_notes", default="📜 Privilegi & Note"))

        ttk.Label(tab_notes, text=_t("features_traits", default="Tratti e Privilegi:"), font=FONT_BOLD).pack(anchor=tk.W, pady=(0, 2))
        features_txt = scrolledtext.ScrolledText(
            tab_notes, height=8, wrap=tk.WORD, font=FONT_MAIN,
            bg=SURFACE_COLOR, fg=TEXT_COLOR
        )
        features_txt.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        features_txt.insert("1.0", sheet.get("features", _t("no_features_registered", default="Nessun tratto speciale registrato.")))
        features_txt.config(state="disabled")

        ttk.Label(tab_notes, text=_t("notes_background", default="Note e Background:"), font=FONT_BOLD).pack(anchor=tk.W, pady=(0, 2))
        notes_txt = scrolledtext.ScrolledText(
            tab_notes, height=6, wrap=tk.WORD, font=FONT_MAIN,
            bg=SURFACE_COLOR, fg=TEXT_COLOR
        )
        notes_txt.pack(fill=tk.BOTH, expand=True)
        notes_txt.insert("1.0", sheet.get("notes", _t("no_notes_present", default="Nessuna nota presente.")))
        notes_txt.config(state="disabled")

        close_btn = ttk.Button(main_frame, text=_t("btn_close_sheet", default="Chiudi Scheda"), command=self.destroy)
        close_btn.pack(side=tk.BOTTOM, pady=(10, 0))


class StarterKitItemEditorDialog(tk.Toplevel):
    """
    Dialogo modale dedicato per creare o modificare un singolo oggetto dell'equipaggiamento iniziale.
    Permette di impostare Nome, Categoria, Quantità, Peso e Descrizione/Effetto in una scheda pulita.
    """
    def __init__(self, parent, item_data=None, on_save=None):
        super().__init__(parent)
        self.item_data = item_data or {}
        self.on_save = on_save
        self.is_edit = bool(item_data)

        title = "✏️ Modifica Oggetto Equipaggiamento" if self.is_edit else "➕ Aggiungi Oggetto Equipaggiamento"
        self.title(title)
        self.geometry("480x430")
        self.minsize(440, 390)
        self.transient(parent)
        self.grab_set()
        apply_modern_window_style(self)

        container = tk.Frame(self, bg=BG_COLOR, padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(container, text=title, font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
        sub_text = "Modifica le proprietà dell'oggetto iniziale per il party:" if self.is_edit else "Inserisci le proprietà del nuovo oggetto iniziale per i PG:"
        tk.Label(container, text=sub_text, font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(2, 10))

        # 1. Nome Oggetto
        tk.Label(container, text="Nome Oggetto:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        self.ent_name = ttk.Entry(container, font=FONT_MAIN)
        self.ent_name.insert(0, self.item_data.get("name", ""))
        self.ent_name.pack(fill=tk.X, pady=(2, 10))
        self.ent_name.focus_set()

        # 2. Tipo / Categoria
        tk.Label(container, text="Tipo / Categoria:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        types = [
            "Equipaggiamento", "Consumabile", "Arma", "Armatura", "Scudo",
            "Munizioni", "Documento", "Valuta", "Strumenti", "Focus", "Magico", "Oggetto"
        ]
        self.cb_type = ttk.Combobox(container, values=types, font=FONT_MAIN)
        self.cb_type.set(self.item_data.get("type", "Equipaggiamento"))
        self.cb_type.pack(fill=tk.X, pady=(2, 10))

        # 3. Quantità e Peso su riga doppia
        row_fields = tk.Frame(container, bg=BG_COLOR)
        row_fields.pack(fill=tk.X, pady=(0, 10))
        row_fields.columnconfigure(0, weight=1)
        row_fields.columnconfigure(1, weight=1)

        f_qty = tk.Frame(row_fields, bg=BG_COLOR)
        f_qty.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(f_qty, text="Quantità:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        self.sp_qty = ttk.Spinbox(f_qty, from_=1, to=9999, font=FONT_MAIN)
        self.sp_qty.set(self.item_data.get("qty", 1))
        self.sp_qty.pack(fill=tk.X, pady=(2, 0))

        f_weight = tk.Frame(row_fields, bg=BG_COLOR)
        f_weight.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(f_weight, text="Peso unitario (lbs):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        self.sp_weight = ttk.Spinbox(f_weight, from_=0.0, to=999.0, increment=0.5, font=FONT_MAIN)
        self.sp_weight.set(self.item_data.get("weight", 1.0))
        self.sp_weight.pack(fill=tk.X, pady=(2, 0))

        # 4. Descrizione o Proprietà
        tk.Label(container, text="Descrizione o Effetto:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
        self.txt_desc = scrolledtext.ScrolledText(
            container, height=4, font=FONT_SMALL,
            bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, relief="flat",
            highlightbackground=BORDER_COLOR, highlightthickness=1, wrap=tk.WORD
        )
        self.txt_desc.insert("1.0", self.item_data.get("desc", ""))
        self.txt_desc.pack(fill=tk.BOTH, expand=True, pady=(2, 12))

        # 5. Pulsanti Salva / Annulla
        btn_box = tk.Frame(container, bg=BG_COLOR)
        btn_box.pack(fill=tk.X)

        btn_save = ttk.Button(btn_box, text="💾 Salva Oggetto", style="Gold.TButton", command=self._save_and_close)
        btn_save.pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_box, text="Annulla", command=self.destroy).pack(side=tk.RIGHT)

        self.bind("<Return>", lambda e: self._save_and_close())
        self.bind("<Escape>", lambda e: self.destroy())

    def _save_and_close(self):
        name = self.ent_name.get().strip()
        if not name:
            messagebox.showwarning("Attenzione", "Inserisci il nome dell'oggetto.", parent=self)
            return

        item_type = self.cb_type.get().strip() or "Equipaggiamento"
        try:
            qty = max(1, int(self.sp_qty.get()))
        except ValueError:
            qty = 1

        try:
            weight = max(0.0, float(str(self.sp_weight.get()).replace(",", ".")))
        except ValueError:
            weight = 0.0

        desc = self.txt_desc.get("1.0", tk.END).strip()

        result = {
            "name": name,
            "type": item_type,
            "qty": qty,
            "weight": weight,
            "desc": desc
        }
        if self.on_save:
            self.on_save(result)
        self.destroy()


class CampaignStarterKitDialog(tk.Toplevel):
    def __init__(self, dm_gui, initial_items=None, on_save_callback=None):
        parent = dm_gui if isinstance(dm_gui, (tk.Tk, tk.Toplevel)) else getattr(dm_gui, "master", None)
        super().__init__(parent)
        self.dm_gui = dm_gui
        self.on_save_callback = on_save_callback
        self.title(_t("starter_kit_title", default="Configura Starter Pack Campagna (Equipaggiamento Iniziale)"))
        self.minsize(700, 520)
        self.geometry("740x550")
        if parent:
            self.transient(parent)
        self.grab_set()
        apply_modern_window_style(self)

        from common.starter_equipment import get_campaign_starter_kit, DEFAULT_CAMPAIGN_STARTER_KIT
        if initial_items is not None:
            self.items = [i.copy() for i in initial_items]
        else:
            cur_kit = None
            if hasattr(self.dm_gui, "server") and hasattr(self.dm_gui.server, "game_state"):
                cur_kit = getattr(self.dm_gui.server.game_state, "campaign_starter_kit", None)
            elif hasattr(self.dm_gui, "game_state") and self.dm_gui.game_state:
                cur_kit = getattr(self.dm_gui.game_state, "campaign_starter_kit", None)
            if not cur_kit:
                cur_kit = get_campaign_starter_kit()
            self.items = [i.copy() for i in cur_kit]

        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=_t("starter_kit_header", default="Equipaggiamento Iniziale della Campagna"), font=FONT_HEADER).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(
            main_frame,
            text=_t("starter_kit_desc", default="I nuovi PG riceveranno automaticamente questi oggetti al loro primo login in questa campagna (fai doppio clic su un elemento per modificarlo):"),
            wraplength=660
        ).pack(anchor=tk.W, pady=(0, 10))

        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.tree = ttk.Treeview(tree_frame, columns=("Nome", "Tipo", "Qty", "Peso", "Desc"), show="headings", height=9)
        self.tree.heading("Nome", text=_t("col_item_name", default="Nome Oggetto"))
        self.tree.heading("Tipo", text=_t("col_type", default="Tipo"))
        self.tree.heading("Qty", text=_t("col_quantity", default="Quantità"))
        self.tree.heading("Peso", text=_t("col_weight", default="Peso (lbs)"))
        self.tree.heading("Desc", text=_t("col_description", default="Descrizione"))
        self.tree.column("Nome", width=170)
        self.tree.column("Tipo", width=110, anchor="center")
        self.tree.column("Qty", width=65, anchor="center")
        self.tree.column("Peso", width=75, anchor="center")
        self.tree.column("Desc", width=240)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-Button-1>", lambda e: self.on_edit_item())
        self.tree.bind("<Return>", lambda e: self.on_edit_item())
        self.tree.bind("<Delete>", lambda e: self.on_remove_item())
        self.tree.bind("<BackSpace>", lambda e: self.on_remove_item())

        self.refresh_list()

        btn_row = ttk.Frame(main_frame)
        btn_row.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(btn_row, text=_t("btn_add_item", default="➕ Aggiungi Oggetto"), command=self.on_add_item, style="Gold.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="📖 Aggiungi dal Compendio...", command=self.on_add_from_compendium, style="Primary.TButton").pack(side=tk.LEFT, padx=3)
        self.btn_edit = ttk.Button(btn_row, text=_t("btn_edit_selected", default="✏️ Modifica Selezionato"), command=self.on_edit_item)
        self.btn_edit.pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text=_t("btn_remove_selected", default="🗑️ Rimuovi Selezionato"), command=self.on_remove_item).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text=_t("btn_reset_defaults", default="🔄 Ripristina Predefiniti"), command=self.on_reset_defaults).pack(side=tk.LEFT, padx=3)

        bottom_row = ttk.Frame(main_frame)
        bottom_row.pack(fill=tk.X)
        ttk.Button(bottom_row, text=_t("btn_save_config", default="Salva Configurazione"), style="Success.TButton", command=self.on_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_row, text=_t("cancel", default="Annulla"), command=self.destroy).pack(side=tk.RIGHT)

    def refresh_list(self):
        for it in self.tree.get_children():
            self.tree.delete(it)
        for idx, item in enumerate(self.items):
            self.tree.insert("", tk.END, iid=str(idx), values=(
                item.get("name", ""),
                item.get("type", "Oggetto"),
                str(item.get("qty", 1)),
                str(item.get("weight", 0.0)),
                item.get("desc", "")
            ))

    def on_add_item(self):
        def _add_callback(new_item):
            self.items.append(new_item)
            self.refresh_list()
            new_idx = str(len(self.items) - 1)
            self.tree.selection_set(new_idx)
            self.tree.see(new_idx)

        StarterKitItemEditorDialog(self, item_data=None, on_save=_add_callback)

    def on_add_from_compendium(self):
        try:
            from server.compendium_ui import CompendiumDialog
            def _on_imported(item_data, category):
                name = item_data.get("name") or item_data.get("title", "Nuovo Oggetto")
                raw_cat = ""
                eq_cat = item_data.get("equipment_category")
                if isinstance(eq_cat, dict):
                    raw_cat = eq_cat.get("name", "")
                elif isinstance(eq_cat, str):
                    raw_cat = eq_cat
                if not raw_cat:
                    raw_cat = item_data.get("type", category or "Equipaggiamento")

                cat_lower = (str(raw_cat) + " " + str(category)).lower()
                if "weapon" in cat_lower or "arma" in cat_lower:
                    item_type = "Arma"
                elif "armor" in cat_lower or "armatura" in cat_lower:
                    item_type = "Armatura"
                elif "shield" in cat_lower or "scudo" in cat_lower:
                    item_type = "Scudo"
                elif "potion" in cat_lower or "pozione" in cat_lower or "consumab" in cat_lower:
                    item_type = "Consumabile"
                elif "ammunition" in cat_lower or "munizion" in cat_lower:
                    item_type = "Munizioni"
                elif "magic" in cat_lower or "magico" in cat_lower:
                    item_type = "Magico"
                elif "tool" in cat_lower or "strument" in cat_lower:
                    item_type = "Strumenti"
                else:
                    item_type = "Equipaggiamento"

                try:
                    weight = float(item_data.get("weight", 1.0) or 0.0)
                except (ValueError, TypeError):
                    weight = 0.0

                desc_parts = []
                if item_data.get("damage"):
                    dmg = item_data["damage"]
                    dice = dmg.get("damage_dice", "")
                    dtype = dmg.get("damage_type", {}).get("name", "") if isinstance(dmg.get("damage_type"), dict) else str(dmg.get("damage_type", ""))
                    if dice:
                        desc_parts.append(f"Danno: {dice} {dtype}".strip())
                if item_data.get("armor_class"):
                    ac_info = item_data["armor_class"]
                    base_ac = ac_info.get("base", 10) if isinstance(ac_info, dict) else ac_info
                    desc_parts.append(f"CA: {base_ac}")
                if item_data.get("properties"):
                    props = [p.get("name") for p in item_data["properties"] if isinstance(p, dict) and p.get("name")]
                    if props:
                        desc_parts.append(f"Proprietà: {', '.join(props)}")

                raw_desc = item_data.get("desc", "") or item_data.get("content", "")
                if isinstance(raw_desc, list):
                    raw_desc = " ".join(str(d) for d in raw_desc)
                if raw_desc:
                    desc_parts.append(str(raw_desc).strip())

                full_desc = " | ".join(desc_parts) if desc_parts else "Oggetto dal Compendio 5e"

                new_item = {
                    "name": name,
                    "type": item_type,
                    "qty": 1,
                    "weight": weight,
                    "desc": full_desc
                }
                self.items.append(new_item)
                self.refresh_list()
                new_idx = str(len(self.items) - 1)
                self.tree.selection_set(new_idx)
                self.tree.see(new_idx)

            dlg = CompendiumDialog(self, on_import_callback=_on_imported, is_dm=True, initial_category="Equipaggiamento", action_label="➕ Aggiungi al Kit")
            dlg.grab_set()
        except Exception as e:
            messagebox.showerror("Errore Compendio", f"Impossibile aprire il compendio: {e}", parent=self)

    def on_edit_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Modifica Oggetto", "Seleziona un oggetto dalla tabella per modificarlo (oppure fai doppio clic sulla riga).", parent=self)
            return
        idx = int(sel[0])
        if idx < 0 or idx >= len(self.items):
            return
        current_item = self.items[idx]

        def _edit_callback(updated_item):
            self.items[idx] = updated_item
            self.refresh_list()
            self.tree.selection_set(str(idx))
            self.tree.see(str(idx))

        StarterKitItemEditorDialog(self, item_data=current_item, on_save=_edit_callback)

    def on_remove_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Rimuovi Oggetto", "Seleziona un oggetto dalla tabella da rimuovere.", parent=self)
            return
        idx = int(sel[0])
        if idx < 0 or idx >= len(self.items):
            return
        item_name = self.items[idx].get("name", "questo oggetto")
        if messagebox.askyesno("Conferma Rimozione", f"Vuoi davvero rimuovere '{item_name}' dall'equipaggiamento iniziale?", parent=self):
            self.items.pop(idx)
            self.refresh_list()

    def on_reset_defaults(self):
        from common.starter_equipment import DEFAULT_CAMPAIGN_STARTER_KIT
        if messagebox.askyesno(_t("btn_reset_defaults", default="Ripristina Predefiniti"), _t("msg_confirm_reset_starter_kit", default="Vuoi ripristinare il kit iniziale predefinito della campagna?"), parent=self):
            self.items = [i.copy() for i in DEFAULT_CAMPAIGN_STARTER_KIT]
            self.refresh_list()

    def on_save(self):
        if self.on_save_callback:
            self.on_save_callback(self.items)

        if hasattr(self.dm_gui, "server") and hasattr(self.dm_gui.server, "game_state"):
            self.dm_gui.server.game_state.campaign_starter_kit = [i.copy() for i in self.items]
        elif hasattr(self.dm_gui, "game_state") and self.dm_gui.game_state:
            self.dm_gui.game_state.campaign_starter_kit = [i.copy() for i in self.items]

        if not self.on_save_callback:
            from common.starter_equipment import save_campaign_starter_kit
            save_campaign_starter_kit(self.items)

        messagebox.showinfo(_t("save", default="Salvato"), _t("msg_starter_kit_saved", default="Equipaggiamento iniziale salvato con successo!"), parent=self)
        self.destroy()

