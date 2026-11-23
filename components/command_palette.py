"""Command palette, rule detail viewer, toast notifications, and tooltips."""

import tkinter as tk

from common.i18n import _t

__all__ = [
    "ToolTip",
    "ToastNotification",
    "show_toast",
    "show_rule_detail_popup",
    "CommandPaletteDialog",
]


class ToolTip:
    """Finestrella di tooltip Dark Fantasy mostrata al passaggio del mouse con supporto a callable per i18n dinamico."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip, add="+")
        self.widget.bind("<Leave>", self.hide_tip, add="+")
        self.widget.bind("<ButtonPress>", self.hide_tip, add="+")
        self.widget.bind("<Destroy>", self.hide_tip, add="+")

    def set_text(self, text):
        self.text = text

    def show_tip(self, event=None):
        if self.tip_window:
            return
        try:
            if not self.widget.winfo_exists():
                return
            tip_text = self.text() if callable(self.text) else self.text
            if not tip_text:
                return
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.attributes("-topmost", True)
            frame = tk.Frame(tw, bg="#181B22", highlightbackground="#D4AF37", highlightthickness=1, padx=8, pady=4)
            frame.pack(fill=tk.BOTH, expand=True)
            label = tk.Label(
                frame, text=tip_text, justify=tk.LEFT,
                bg="#181B22", fg="#ECEFF1", font=("Segoe UI", 9),
                wraplength=320
            )
            label.pack()
            tw.update_idletasks()
            tw_w = tw.winfo_reqwidth()
            tw_h = tw.winfo_reqheight()
            sw = tw.winfo_screenwidth()
            sh = tw.winfo_screenheight()
            if x + tw_w + 12 > sw:
                x = max(8, sw - tw_w - 12)
            if y + tw_h + 12 > sh:
                y = max(8, self.widget.winfo_rooty() - tw_h - 6)
            tw.wm_geometry(f"+{x}+{y}")
        except Exception:
            self.hide_tip()

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            try:
                tw.destroy()
            except Exception:
                pass


class ToastNotification:
    """Notifica non bloccante a scomparsa in stile dark fantasy."""
    _active_toasts = []

    def __init__(self, parent, message, title=None, duration=3500, toast_type="info", icon=None, color=None):
        self.parent = parent
        self.duration = duration
        self._after_id = None

        type_styles = {
            "info": {"bg": "#1e232a", "fg": "#f0f6fc", "accent": "#d4af37", "icon": icon or "ℹ️"},
            "secondary": {"bg": "#1e232a", "fg": "#f0f6fc", "accent": "#8b949e", "icon": icon or "📌"},
            "success": {"bg": "#13231b", "fg": "#f0f6fc", "accent": "#2ea043", "icon": icon or "✨"},
            "warning": {"bg": "#2b2111", "fg": "#f0f6fc", "accent": "#d29922", "icon": icon or "⚠️"},
            "danger": {"bg": "#2d1517", "fg": "#f0f6fc", "accent": "#f85149", "icon": icon or "💥"},
            "gold": {"bg": "#252112", "fg": "#f0f6fc", "accent": "#e3b341", "icon": icon or "💰"},
            "loot": {"bg": "#1c222d", "fg": "#f0f6fc", "accent": "#58a6ff", "icon": icon or "🎒"},
        }
        style = dict(type_styles.get(toast_type, type_styles["info"]))
        if color:
            style["accent"] = color

        self.win = tk.Toplevel(parent)
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True)

        try:
            parent.update_idletasks()
            pw = parent.winfo_width()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
        except Exception:
            pw, px, py = 1000, 100, 100

        offset_y = 60 + len(ToastNotification._active_toasts) * 75
        self.win.geometry(f"330x68+{px + max(10, pw - 350)}+{py + offset_y}")

        frame = tk.Frame(self.win, bg=style["bg"], highlightbackground=style["accent"], highlightthickness=2, padx=10, pady=6)
        frame.pack(fill=tk.BOTH, expand=True)

        header_frame = tk.Frame(frame, bg=style["bg"])
        header_frame.pack(fill=tk.X)

        title_text = f"{style['icon']} {title or toast_type.capitalize()}"
        lbl_title = tk.Label(header_frame, text=title_text, font=("Georgia", 10, "bold"), fg=style["accent"], bg=style["bg"])
        lbl_title.pack(side=tk.LEFT)

        btn_close = tk.Label(header_frame, text="✕", font=("Arial", 9), fg="#8b949e", bg=style["bg"], cursor="hand2")
        btn_close.pack(side=tk.RIGHT)
        btn_close.bind("<Button-1>", lambda e: self.destroy())

        lbl_msg = tk.Label(frame, text=message, font=("Arial", 9), fg=style["fg"], bg=style["bg"], wraplength=300, justify=tk.LEFT)
        lbl_msg.pack(anchor="w", pady=(2, 0))

        self.win.update_idletasks()
        toast_h = max(68, min(140, frame.winfo_reqheight() + 4))
        self._toast_height = toast_h
        self._parent = parent
        self.win.geometry(f"330x{toast_h}+{px + max(10, pw - 350)}+{py + offset_y}")

        ToastNotification._active_toasts.append(self)
        ToastNotification._reflow_active_toasts()
        def _on_toast_destroyed(e=None):
            if e and getattr(e, "widget", None) != self.win:
                return
            if getattr(self, "_after_id", None) is not None:
                try:
                    self.win.after_cancel(self._after_id)
                except Exception:
                    pass
                self._after_id = None
            if self in ToastNotification._active_toasts:
                ToastNotification._active_toasts.remove(self)
                ToastNotification._reflow_active_toasts()
        try:
            self.win.bind("<Destroy>", _on_toast_destroyed, add="+")
        except Exception:
            pass
        self._after_id = self.win.after(self.duration, self.destroy)

    @classmethod
    def _reflow_active_toasts(cls):
        """Riallinea verticalmente i toast attivi evitando sovrapposizioni o spazi vuoti."""
        y_cursor = 60
        for t in list(cls._active_toasts):
            try:
                if not t.win.winfo_exists():
                    continue
                parent = getattr(t, "_parent", None)
                pw = parent.winfo_width() if parent else 1000
                px = parent.winfo_rootx() if parent else 100
                py = parent.winfo_rooty() if parent else 100
                th = max(68, getattr(t, "_toast_height", 68))
                t.win.geometry(f"330x{th}+{px + max(10, pw - 350)}+{py + y_cursor}")
                y_cursor += th + 8
            except Exception:
                pass

    def destroy(self):
        if self in ToastNotification._active_toasts:
            ToastNotification._active_toasts.remove(self)
        if getattr(self, "_after_id", None) is not None:
            try:
                self.win.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        try:
            self.win.destroy()
        except Exception:
            pass
        ToastNotification._reflow_active_toasts()


def show_toast(parent, message, title=None, duration=3500, toast_type="info", icon=None, color=None):
    """Funzione di utilità per mostrare un toast non bloccante."""
    try:
        return ToastNotification(parent, message, title=title, duration=duration, toast_type=toast_type, icon=icon, color=color)
    except Exception:
        return None


def show_rule_detail_popup(parent, rule_dict):
    """Mostra i dettagli completi di una regola in una comoda finestra modale."""
    win = tk.Toplevel(parent)
    title = rule_dict.get("title", "Regola 5e")
    win.title(title)
    win.geometry("560x440")
    win.minsize(450, 320)
    win.configure(bg="#111318")
    win.transient(parent)

    container = tk.Frame(win, bg="#111318", padx=16, pady=14)
    container.pack(fill=tk.BOTH, expand=True)

    header = tk.Frame(container, bg="#111318")
    header.pack(fill=tk.X, pady=(0, 8))

    lbl_title = tk.Label(header, text=title, font=("Segoe UI", 12, "bold"), bg="#111318", fg="#F59E0B")
    lbl_title.pack(side=tk.LEFT)

    manual_info = f"{rule_dict.get('manual', '5e')} • {rule_dict.get('page_ref', '')}"
    lbl_ref = tk.Label(header, text=manual_info, font=("Segoe UI", 9), bg="#1F242D", fg="#9CA3AF", padx=6, pady=2)
    lbl_ref.pack(side=tk.RIGHT)

    txt_content = tk.Text(container, bg="#181B22", fg="#E5E7EB", font=("Segoe UI", 10), wrap=tk.WORD, bd=0, padx=10, pady=10)
    scroll = tk.Scrollbar(container, orient=tk.VERTICAL, command=txt_content.yview)
    txt_content.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    txt_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    body = rule_dict.get("content") or rule_dict.get("summary", "")
    txt_content.insert(tk.END, body)
    txt_content.configure(state=tk.DISABLED)

    win.bind("<Escape>", lambda e: win.destroy())


class CommandPaletteDialog(tk.Toplevel):
    """
    Tavolozza dei Comandi Rapida (Ctrl + K) in stile Foundry VTT / VS Code / Spotlight.
    Permette di:
    - Eseguire tiri di dadi istantanei (/roll 1d20+5, 2d6, ecc.)
    - Cercare e centrare all'istante token e PNG sulla mappa
    - Ricercare regole, condizioni, mostri e incantesimi dai manuali D&D 5e
    - Eseguire scorciatoie rapide della UI (Righello, Zoom, Centra, Compendio, Scheda)
    """
    def __init__(self, master, map_canvas=None, on_action=None, is_dm=False, player_names=None):
        super().__init__(master)
        self.master = master
        self.map_canvas = map_canvas
        self.on_action = on_action
        self.is_dm = is_dm
        self.player_names = player_names or []

        self.title(_t("cmd_palette_title", default="Command Palette & Quick Search"))
        self.configure(bg="#111318")
        self.minsize(620, 480)
        self.transient(master)

        # Centra sopra la finestra master
        try:
            pw = master.winfo_width()
            ph = master.winfo_height()
            px = master.winfo_rootx()
            py = master.winfo_rooty()
            if pw > 200 and ph > 200:
                cw = 640
                ch = 490
                cx = max(px + 10, px + (pw - cw) // 2)
                cy = max(py + 10, py + (ph - ch) // 3)
                self.geometry(f"{cw}x{ch}+{cx}+{cy}")
        except Exception:
            self.geometry("640x490")

        self._manuals_manager = None
        self._results = []
        self._active_filter = "ALL"

        self._setup_ui()
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Up>", self._on_arrow_up)
        self.bind("<Down>", self._on_arrow_down)
        self.bind("<Return>", self._on_enter)

        self._focus_job = self.after(50, lambda: self.search_entry.focus_set() if self.winfo_exists() else None)
        def _on_palette_destroyed(e=None):
            if e and getattr(e, "widget", None) != self:
                return
            if getattr(self, "_focus_job", None) is not None:
                try:
                    self.after_cancel(self._focus_job)
                except Exception:
                    pass
                self._focus_job = None
        self.bind("<Destroy>", _on_palette_destroyed, add="+")
        self._perform_search("")

    def _setup_ui(self):
        main_box = tk.Frame(self, bg="#111318", highlightbackground="#D4AF37", highlightthickness=1.5, padx=12, pady=12)
        main_box.pack(fill=tk.BOTH, expand=True)

        # 1. Barra di Ricerca Header
        search_box = tk.Frame(main_box, bg="#181B22", highlightbackground="#374151", highlightthickness=1, padx=8, pady=6)
        search_box.pack(fill=tk.X, pady=(0, 8))

        lbl_icon = tk.Label(search_box, text="🔍", font=("Segoe UI Emoji", 13), bg="#181B22", fg="#F59E0B")
        lbl_icon.pack(side=tk.LEFT, padx=(2, 8))

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            search_box, textvariable=self.search_var, font=("Segoe UI", 12),
            bg="#181B22", fg="#F9FAFB", insertbackground="#F59E0B", bd=0, relief=tk.FLAT
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<KeyRelease>", self._on_search_key)

        lbl_esc = tk.Label(search_box, text="ESC", font=("Segoe UI", 8, "bold"), bg="#242832", fg="#9CA3AF", padx=5, pady=1)
        lbl_esc.pack(side=tk.RIGHT, padx=2)
        lbl_esc.bind("<Button-1>", lambda e: self.destroy())

        # 2. Filter Pills
        filter_bar = tk.Frame(main_box, bg="#111318")
        filter_bar.pack(fill=tk.X, pady=(0, 8))

        self._filter_buttons = {}
        filters = [
            ("ALL", "Tutti"),
            ("ROLL", _t("cmd_type_roll", default="🎲 Dadi")),
            ("TOKEN", _t("cmd_type_token", default="📍 Token")),
            ("RULE", _t("cmd_type_rule", default="📖 Regole")),
            ("ACTION", _t("cmd_type_action", default="⚡ Azioni")),
        ]
        for f_key, f_label in filters:
            btn = tk.Button(
                filter_bar, text=f_label, font=("Segoe UI", 8, "bold"),
                bg="#2563EB" if f_key == "ALL" else "#1F242D",
                fg="#FFFFFF" if f_key == "ALL" else "#9CA3AF",
                activebackground="#3B82F6", activeforeground="#FFFFFF",
                bd=0, relief=tk.FLAT, padx=8, pady=2,
                command=lambda k=f_key: self._set_filter(k)
            )
            btn.pack(side=tk.LEFT, padx=3)
            self._filter_buttons[f_key] = btn

        # 3. Content Split (Listbox a sinistra, Preview a destra)
        split_frame = tk.Frame(main_box, bg="#111318")
        split_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        split_frame.columnconfigure(0, weight=3)
        split_frame.columnconfigure(1, weight=2)
        split_frame.rowconfigure(0, weight=1)

        # Lista Risultati
        list_container = tk.Frame(split_frame, bg="#14171E", highlightbackground="#2D333F", highlightthickness=1)
        list_container.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.results_listbox = tk.Listbox(
            list_container, bg="#14171E", fg="#E5E7EB", selectbackground="#1E3A8A",
            selectforeground="#FDE68A", font=("Segoe UI", 9), activestyle="none",
            bd=0, highlightthickness=0
        )
        scrollbar = tk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.results_listbox.yview)
        self.results_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.results_listbox.bind("<<ListboxSelect>>", self._on_list_select)
        self.results_listbox.bind("<Double-Button-1>", lambda e: self._execute_selected())

        # Pannello Preview Dettagli a destra
        preview_container = tk.Frame(split_frame, bg="#181B22", highlightbackground="#2D333F", highlightthickness=1, padx=10, pady=8)
        preview_container.grid(row=0, column=1, sticky="nsew")

        self.prev_title_lbl = tk.Label(preview_container, text="Seleziona un elemento", font=("Segoe UI", 10, "bold"), bg="#181B22", fg="#F59E0B", wraplength=210, justify=tk.LEFT)
        self.prev_title_lbl.pack(anchor="w", pady=(0, 4))

        self.prev_badge_lbl = tk.Label(preview_container, text="", font=("Segoe UI", 8), bg="#262C38", fg="#9CA3AF", padx=4, pady=1)
        self.prev_badge_lbl.pack(anchor="w", pady=(0, 6))

        self.prev_text = tk.Text(
            preview_container, bg="#14161C", fg="#D1D5DB", font=("Segoe UI", 9),
            wrap=tk.WORD, bd=0, highlightthickness=0, height=8
        )
        self.prev_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.prev_text.configure(state=tk.DISABLED)

        self.btn_execute = tk.Button(
            preview_container, text="↵ Esegui / Seleziona", font=("Segoe UI", 9, "bold"),
            bg="#2563EB", fg="white", activebackground="#3B82F6", bd=0, relief=tk.FLAT,
            padx=10, pady=4, command=self._execute_selected
        )
        self.btn_execute.pack(fill=tk.X)

        # 4. Status Hint Footer
        hint_lbl = tk.Label(
            main_box, text=_t("cmd_palette_hint", default="↑ / ↓ Naviga  •  ↵ Seleziona / Esegui  •  Esc Chiudi"),
            font=("Segoe UI", 8), bg="#111318", fg="#6B7280"
        )
        hint_lbl.pack(anchor="w")

    def _set_filter(self, filter_key):
        self._active_filter = filter_key
        for k, btn in self._filter_buttons.items():
            if k == filter_key:
                btn.configure(bg="#2563EB", fg="#FFFFFF")
            else:
                btn.configure(bg="#1F242D", fg="#9CA3AF")
        self._perform_search(self.search_var.get())

    def _on_search_key(self, event=None):
        if event and event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        self._perform_search(self.search_var.get())

    def _get_manuals_manager(self):
        if self._manuals_manager is None:
            try:
                from common.manuals_manager import ManualsManager
                self._manuals_manager = ManualsManager()
            except Exception as e:
                print("Error loading ManualsManager in CommandPalette:", e)
        return self._manuals_manager

    def _perform_search(self, query):
        q = (query or "").strip().lower()
        results = []

        # 1. DADI (Roll)
        is_roll_query = (
            q.startswith("/roll") or q.startswith("/r") or
            any(k in q for k in ["d4", "d6", "d8", "d10", "d12", "d20", "d100"]) or
            ("d" in q and any(c.isdigit() for c in q))
        )
        if is_roll_query:
            formula = q
            if formula.startswith("/roll"):
                formula = formula[5:].strip()
            elif formula.startswith("/r"):
                formula = formula[2:].strip()
            formula = formula or "1d20"
            results.append({
                "type": "ROLL",
                "icon": "🎲",
                "title": f"Lancia: {formula}",
                "badge": "Tiro Dadi",
                "summary": f"Invia il tiro dadi '{formula}' al tavolo virtuale.",
                "payload": formula
            })

        # 2. TOKEN SULLA MAPPA
        if self.map_canvas and hasattr(self.map_canvas, "players_data"):
            p_data = self.map_canvas.players_data
            cur_map = getattr(self.map_canvas, "map_data", {}) or {}
            fow_enabled = bool(cur_map.get("fow_enabled", False))
            rev_set = {(h[0], h[1]) for h in cur_map.get("fow_revealed", []) if isinstance(h, (list, tuple)) and len(h) >= 2}
            my_name = getattr(self.map_canvas, "player_name", None)

            is_dm_view = bool(getattr(self, "is_dm", False) or getattr(self.map_canvas, "is_dm", False))
            for name, data in p_data.items():
                if not is_dm_view and isinstance(data, dict):
                    if data.get("layer", "token") == "gm" or data.get("is_hidden", False) or data.get("in_pocket_dimension"):
                        continue
                    if fow_enabled and name != my_name and not data.get("is_party_member", False) and not data.get("is_companion", False):
                        pos_t = data.get("position", [0, 0])
                        if (pos_t[0], pos_t[1]) not in rev_set:
                            continue

                conds = data.get("conditions", []) if isinstance(data, dict) else []
                pos = data.get("position", [0, 0]) if isinstance(data, dict) else (data or [0, 0])
                hp = data.get("hp", "?") if isinstance(data, dict) else "?"
                hp_max = data.get("hp_max", data.get("max_hp", "?")) if isinstance(data, dict) else "?"

                cond_str = ", ".join(conds) if conds else "Nessuna"
                matches_token = (not q) or (q in name.lower()) or any(q in c.lower() for c in conds)
                if matches_token:
                    is_ally_or_self = bool(
                        is_dm_view
                        or name == my_name
                        or (isinstance(data, dict) and (data.get("is_party_member") or data.get("is_companion")))
                    )
                    if is_ally_or_self:
                        badge_txt = f"HP {hp}/{hp_max} • Hex [{pos[0]},{pos[1]}]"
                        sum_txt = f"Nome: {name}\nSalute: {hp}/{hp_max}\nPosizione Hex: {pos}\nCondizioni: {cond_str}"
                    else:
                        if isinstance(hp, (int, float)) and isinstance(hp_max, (int, float)) and hp_max > 0:
                            ratio = hp / hp_max
                            status_lbl = "A Terra" if hp <= 0 else ("Sanguinante" if ratio <= 0.5 else ("Ferito" if ratio < 1.0 else "Incolume"))
                        else:
                            status_lbl = str(data.get("health_status", "Ostile")) if isinstance(data, dict) else "Ostile"
                        badge_txt = f"Stato: {status_lbl}"
                        sum_txt = f"Nome: {name}\nStato: {status_lbl}\nCondizioni: {cond_str}"
                    results.append({
                        "type": "TOKEN",
                        "icon": "📍",
                        "title": f"Token: {name}",
                        "badge": badge_txt,
                        "summary": sum_txt,
                        "payload": name
                    })

        # 3. AZIONI RAPIDE DELLA UI
        actions = [
            ("toggle_fullscreen", "⛶ Schermo Intero (F11)", "Attiva o disattiva la visualizzazione a schermo intero."),
            ("toggle_pan", "✋ Naviga Mappa / Pan (Tasto H, P o Spazio)", "Alterna la modalità navigazione mappa per trascinare con tasto sinistro senza rotella."),
            ("center_map", "👆 Centra Vista Mappa", "Centra il canvas all'origine o sui token del tavolo."),
            ("toggle_ruler", "📏 Attiva / Disattiva Righello", "Alterna la modalità misuratore di distanza in piedi (ft)."),
            ("zoom_in", "➕ Ingrandisci Mappa (Zoom +)", "Aumenta il livello di ingrandimento del canvas."),
            ("zoom_out", "➖ Riduci Mappa (Zoom -)", "Diminuisce il livello di ingrandimento del canvas."),
            ("open_aoe", "💥 Sagoma Area d'Effetto (AoE)", "Configura e posiziona cerchi, coni, cubi o linee."),
            ("open_manuals", "📖 Apri Compendio & Manuali", "Esplora i manuali ufficiali 5e e note homebrew."),
            ("open_sheet", "📜 Apri Scheda Personaggio", "Visualizza la scheda interattiva del tuo eroe."),
            ("roll_d20", "🎲 Tira 1d20 Istantaneo", "Esegue immediatamente un d20 rapido."),
        ]
        for act_id, act_title, act_desc in actions:
            if (not q) or (q in act_title.lower()) or (q in act_desc.lower()) or (q in act_id):
                results.append({
                    "type": "ACTION",
                    "icon": "⚡",
                    "title": act_title,
                    "badge": "Azione Rapida",
                    "summary": act_desc,
                    "payload": act_id
                })

        # 4. REGOLE E COMPENDIO 5e
        mm = self._get_manuals_manager()
        if mm:
            try:
                rule_hits = mm.search(q if q else "")
                for r in rule_hits[:15]:
                    results.append({
                        "type": "RULE",
                        "icon": "📖",
                        "title": r.get("title", "Regola"),
                        "badge": f"{r.get('manual', '5e')} • {r.get('category', 'Regole')}",
                        "summary": r.get("summary") or r.get("content", "")[:180],
                        "payload": r
                    })
            except Exception as e:
                print("Error searching manuals in CommandPalette:", e)

        # Filtra per categoria attiva
        if self._active_filter != "ALL":
            results = [r for r in results if r["type"] == self._active_filter]

        self._results = results
        self.results_listbox.delete(0, tk.END)

        if not results:
            self.results_listbox.insert(tk.END, "  Nessun risultato trovato")
            self._update_preview(None)
            return

        for r in results:
            self.results_listbox.insert(tk.END, f" {r['icon']}  {r['title']}")

        self.results_listbox.select_set(0)
        self._update_preview(results[0])

    def _on_list_select(self, event=None):
        sel = self.results_listbox.curselection()
        if sel and sel[0] < len(self._results):
            self._update_preview(self._results[sel[0]])

    def _update_preview(self, item):
        self.prev_text.configure(state=tk.NORMAL)
        self.prev_text.delete("1.0", tk.END)

        if not item:
            self.prev_title_lbl.config(text="Nessun elemento")
            self.prev_badge_lbl.config(text="")
            self.prev_text.configure(state=tk.DISABLED)
            return

        self.prev_title_lbl.config(text=f"{item['icon']} {item['title']}")
        self.prev_badge_lbl.config(text=item.get("badge", ""))
        self.prev_text.insert(tk.END, item.get("summary", ""))
        self.prev_text.configure(state=tk.DISABLED)

        # Testo del bottone contestualizzato
        if item["type"] == "ROLL":
            self.btn_execute.config(text="🎲 Lancia Ora")
        elif item["type"] == "TOKEN":
            self.btn_execute.config(text="📍 Centra sulla Mappa")
        elif item["type"] == "RULE":
            self.btn_execute.config(text="📖 Leggi Regola Completa")
        else:
            self.btn_execute.config(text="↵ Esegui Azione")

    def _on_arrow_up(self, event=None):
        sel = self.results_listbox.curselection()
        if sel and sel[0] > 0:
            idx = sel[0] - 1
            self.results_listbox.selection_clear(0, tk.END)
            self.results_listbox.selection_set(idx)
            self.results_listbox.activate(idx)
            self.results_listbox.see(idx)
            self._update_preview(self._results[idx])
        return "break"

    def _on_arrow_down(self, event=None):
        sel = self.results_listbox.curselection()
        if sel and sel[0] < len(self._results) - 1:
            idx = sel[0] + 1
            self.results_listbox.selection_clear(0, tk.END)
            self.results_listbox.selection_set(idx)
            self.results_listbox.activate(idx)
            self.results_listbox.see(idx)
            self._update_preview(self._results[idx])
        elif not sel and self._results:
            self.results_listbox.selection_set(0)
            self._update_preview(self._results[0])
        return "break"

    def _on_enter(self, event=None):
        self._execute_selected()
        return "break"

    def _execute_selected(self):
        sel = self.results_listbox.curselection()
        if not sel or sel[0] >= len(self._results):
            return

        item = self._results[sel[0]]
        itype = item["type"]
        payload = item["payload"]

        if itype == "ROLL":
            formula = payload
            if self.on_action:
                self.on_action("roll", formula)
            self.destroy()
            show_toast(self.master, f"Tiro dadi eseguito: {formula}", title="Tiro Dadi", icon="🎲")

        elif itype == "TOKEN":
            token_name = payload
            if self.map_canvas and hasattr(self.map_canvas, "center_on_token"):
                self.map_canvas.center_on_token(token_name)
            if self.on_action:
                self.on_action("center_token", token_name)
            self.destroy()
            show_toast(self.master, f"Mappa centrata su: {token_name}", title="Token", icon="📍")

        elif itype == "ACTION":
            act_id = payload
            if act_id == "center_map" and self.map_canvas:
                self.map_canvas.center_view()
            elif act_id == "zoom_in" and self.map_canvas:
                self.map_canvas.zoom_in()
            elif act_id == "zoom_out" and self.map_canvas:
                self.map_canvas.zoom_out()
            elif act_id == "toggle_ruler":
                if self.on_action:
                    self.on_action("action", "toggle_ruler")
                elif self.map_canvas:
                    self.map_canvas.ruler_mode = not getattr(self.map_canvas, "ruler_mode", False)
                    self.map_canvas.redraw()
            elif act_id == "toggle_fullscreen":
                if self.on_action:
                    self.on_action("action", "toggle_fullscreen")
                else:
                    top = self.master.winfo_toplevel()
                    try:
                        is_fs = bool(top.attributes("-fullscreen"))
                        top.attributes("-fullscreen", not is_fs)
                    except Exception:
                        pass
            elif act_id == "roll_d20":
                if self.on_action:
                    self.on_action("roll", "1d20")
            elif self.on_action:
                self.on_action("action", act_id)
            self.destroy()

        elif itype == "RULE":
            rule_dict = payload
            if isinstance(rule_dict, dict):
                show_rule_detail_popup(self.master, rule_dict)
            if self.on_action:
                self.on_action("rule", rule_dict)
