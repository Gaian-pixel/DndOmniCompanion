import tkinter as tk
from tkinter import ttk
import os
from common.messagebox import messagebox
from common.i18n import _t, get_language
from common.file_utils import get_writable_dir, load_json, atomic_save_json
from common.theme import (
    TEXT_COLOR, ACCENT_RED, ACCENT_GOLD, SURFACE_COLOR, SURFACE_COLOR_ALT,
    BORDER_COLOR, BG_COLOR, TEXT_MUTED, FONT_MAIN, FONT_BOLD, FONT_HEADER, FONT_SMALL,
    apply_modern_window_style
)
from .character_creation_wizard import CharacterCreationWizard


SETTINGS_PATH = os.path.join(get_writable_dir(), "client_data", "settings.json")


def _resolve_settings_path(settings_path=None):
    return settings_path or os.environ.get("DND_SETTINGS_PATH") or SETTINGS_PATH


def load_server_history(settings_path=None):
    """Carica l'ultimo IP server usato e la lista dei server recenti da settings.json."""
    target_path = _resolve_settings_path(settings_path)
    settings = load_json(target_path, default={}) or {}
    last_ip = settings.get("last_server_ip", "127.0.0.1")
    recents = settings.get("recent_servers", [])
    if not recents:
        recents = [last_ip] if last_ip else ["127.0.0.1"]
    if "127.0.0.1" not in recents:
        recents.append("127.0.0.1")
    return last_ip, recents


def save_server_history(ip: str, settings_path=None):
    """Salva l'IP server nella cronologia persistente in settings.json."""
    if not ip or not ip.strip():
        return
    clean_ip = ip.strip()
    target_path = _resolve_settings_path(settings_path)
    settings = load_json(target_path, default={}) or {}
    recents = settings.get("recent_servers", [])
    if clean_ip in recents:
        recents.remove(clean_ip)
    recents.insert(0, clean_ip)
    settings["recent_servers"] = recents[:6]
    settings["last_server_ip"] = clean_ip
    try:
        atomic_save_json(target_path, settings)
    except Exception as e:
        print(f"[LoginDialog] Errore salvataggio server: {e}")


class LoginDialog(tk.Toplevel):
    """
    Dialogo di connessione e unione a una partita D&D.
    Consente all'utente di selezionare/digitare subito l'IP del Server
    e scegliere il personaggio con cui unirsi alla sessione.
    """

    def __init__(self, master, character_manager, initial_character=None, initial_ip=None, lock_character=False):
        super().__init__(master)
        self.title(_t("login_dialog_title"))
        self.lock_character = bool(lock_character and initial_character is not None)
        self.minsize(480, 415 if self.lock_character else 480)
        apply_modern_window_style(self)
        self.transient(master)
        self.grab_set()
        
        self.manager = character_manager
        self.initial_character = initial_character
        self.result = None # Verrà impostato a (ip_server, character)
        self.session_password = ""
        self.password_var = tk.StringVar(value="")
        self.default_font = ("Georgia", 10)
        
        saved_ip, self.recent_servers = load_server_history()
        self.current_ip = initial_ip or saved_ip or "127.0.0.1"
        
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Scorciatoie da tastiera
        self.bind("<Escape>", lambda e: self.on_close())
        self.bind("<Return>", lambda e: self.connect())
        
        self._fitting_geometry = False
        self._fit_geometry(center=True)

    def setup_ui(self):
        self._main_frame = ttk.Frame(self, padding=20)
        main_frame = self._main_frame
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.bind("<Configure>", self._on_main_configure)
        
        # 1. HEADER SECTION
        hdr_frame = tk.Frame(main_frame, bg=SURFACE_COLOR)
        hdr_frame.pack(fill=tk.X, pady=(0, 14))
        
        top_row = tk.Frame(hdr_frame, bg=SURFACE_COLOR)
        top_row.pack(fill=tk.X)
        
        shield_cv = tk.Canvas(top_row, width=38, height=34, bg=SURFACE_COLOR, highlightthickness=0, bd=0)
        shield_cv.pack(side=tk.LEFT, padx=(0, 10))
        shield_cv.create_polygon(
            6, 4, 19, 2, 32, 4, 32, 17, 28, 25, 19, 31, 10, 25, 6, 17,
            fill="#3B5BDB", outline="#748FFC", width=1.5
        )
        shield_cv.create_line(19, 3, 19, 29, fill="#DBE4FF", width=1.5)
        shield_cv.create_line(8, 14, 30, 14, fill="#DBE4FF", width=1.5)
        
        self.titles_box = tk.Frame(top_row, bg=SURFACE_COLOR)
        self.titles_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.title_lbl = tk.Label(
            self.titles_box,
            text=_t("login_dialog_title"),
            font=("Georgia", 14, "bold"),
            bg=SURFACE_COLOR,
            fg=ACCENT_GOLD,
            justify=tk.LEFT,
            anchor="w",
        )
        self.title_lbl.pack(anchor="w")
        self.sub_lbl = tk.Label(
            self.titles_box,
            text=_t("login_dialog_sub"),
            font=("Segoe UI", 8),
            bg=SURFACE_COLOR,
            fg=TEXT_MUTED,
            justify=tk.LEFT,
            anchor="w",
            wraplength=390,
        )
        self.sub_lbl.pack(anchor="w", fill=tk.X, pady=(1, 0))
        
        tk.Frame(main_frame, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=(0, 12))
        
        # 2. SEZIONE SERVER IP
        self.server_sec = tk.Frame(main_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        server_sec = self.server_sec
        server_sec.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(server_sec, text=_t("login_server_ip"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(0, 6))
        
        ip_row = tk.Frame(server_sec, bg=SURFACE_COLOR)
        ip_row.pack(fill=tk.X)
        
        # Pack button BEFORE combobox so Locale (127.0.0.1) is never crushed on narrow widths
        self.btn_local = ttk.Button(ip_row, text=_t("login_btn_local"), command=self.set_local_ip, style="Dark.TButton")
        self.btn_local.pack(side=tk.RIGHT)
        self.ip_var = tk.StringVar(value=self.current_ip)
        self.ip_combo = ttk.Combobox(ip_row, textvariable=self.ip_var, values=self.recent_servers, font=("Segoe UI", 10), width=18)
        self.ip_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        self.port_hint_lbl = tk.Label(
            server_sec,
            text=_t("login_port_hint"),
            font=("Segoe UI", 8),
            bg=SURFACE_COLOR,
            fg=TEXT_MUTED,
            justify=tk.LEFT,
            anchor="w",
            wraplength=430,
        )
        self.port_hint_lbl.pack(anchor="w", fill=tk.X, pady=(4, 0))

        pin_row = tk.Frame(server_sec, bg=SURFACE_COLOR)
        pin_row.pack(fill=tk.X, pady=(6, 0))
        tk.Label(pin_row, text=_t("login_session_pin"), font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 8))
        # Pack eye toggle BEFORE expanding entry so it stays visible even at high DPI / narrow widths
        self._pin_visible = False
        self.pin_toggle_btn = ttk.Button(pin_row, text="👁", width=3, command=self._toggle_pin_visibility, style="Dark.TButton")
        self.pin_toggle_btn.pack(side=tk.RIGHT, padx=(6, 0))
        self.pin_entry = ttk.Entry(pin_row, textvariable=self.password_var, show="•", font=("Segoe UI", 10), width=12)
        self.pin_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 4. BOTTONI DI CONFERMA / ANNULLA IN BASSO (pack side=BOTTOM before expanding char_sec so CTAs never clip)
        bottom_box = ttk.Frame(main_frame)
        bottom_box.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.btn_cancel = ttk.Button(bottom_box, text=_t("login_btn_cancel"), command=self.on_close, style="Dark.TButton")
        self.btn_cancel.pack(side=tk.RIGHT, padx=(8, 0))
        self.btn_connect = ttk.Button(bottom_box, text=_t("login_btn_connect"), command=self.connect, style="Primary.TButton")
        self.btn_connect.pack(side=tk.RIGHT)
        
        # 3. SEZIONE PERSONAGGIO
        self.char_sec = tk.Frame(main_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        char_sec = self.char_sec
        char_sec.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        self.char_listbox = None
        self.hero_row = None
        self.locked_hero_lbl = None
        self.btn_change_char = None
        if self.lock_character and self.initial_character is not None:
            tk.Label(char_sec, text=_t("login_locked_char_hdr"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(0, 6))
            self.hero_row = tk.Frame(char_sec, bg=SURFACE_COLOR_ALT, highlightbackground=ACCENT_GOLD, highlightthickness=1, padx=10, pady=8)
            self.hero_row.pack(fill=tk.X, pady=(0, 4))
            c = self.initial_character
            camp = f" [{c.campaign}]" if getattr(c, "campaign", None) else ""
            race = f" ({c.race})" if getattr(c, "race", None) else ""
            # Pack Change Hero button BEFORE the hero summary label so long titles wrap instead of crushing the button
            self.btn_change_char = ttk.Button(
                self.hero_row,
                text=_t("login_btn_change_char"),
                command=self.unlock_character_selection,
                style="Dark.TButton"
            )
            self.btn_change_char.pack(side=tk.RIGHT, padx=(10, 0))
            self.locked_hero_lbl = tk.Label(
                self.hero_row,
                text=f"⚔️  {c.name}  •  Lv.{c.level} {c.char_class}{race}{camp}",
                font=FONT_BOLD,
                bg=SURFACE_COLOR_ALT,
                fg=ACCENT_GOLD,
                justify=tk.LEFT,
                anchor="w",
                wraplength=310,
            )
            self.locked_hero_lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, anchor="w")
        else:
            tk.Label(char_sec, text=_t("login_select_char"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(0, 6))
            
            char_btn_row = tk.Frame(char_sec, bg=SURFACE_COLOR)
            char_btn_row.pack(side=tk.BOTTOM, fill=tk.X)
            self.btn_manage_hub = ttk.Button(char_btn_row, text=_t("login_btn_manage_hub"), command=self.open_character_hub, style="Info.TButton")
            self.btn_manage_hub.pack(fill=tk.X)

            list_frame = tk.Frame(char_sec, bg=SURFACE_COLOR)
            list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

            _, sh = self._available_screen_bounds()
            lb_rows = 4 if sh < 560 else 6
            self.char_listbox = tk.Listbox(
                list_frame, 
                font=self.default_font, 
                bg=SURFACE_COLOR_ALT, 
                fg=TEXT_COLOR, 
                selectbackground="#3B5BDB", 
                selectforeground="#FFFFFF",
                height=lb_rows, 
                relief="flat", 
                highlightthickness=1, 
                highlightbackground=BORDER_COLOR
            )
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.char_listbox.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.char_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.char_listbox.bind("<Double-Button-1>", lambda e: self.connect())
            self.char_listbox.config(yscrollcommand=scrollbar.set)
            
            self.refresh_listbox()

    def _available_screen_bounds(self):
        try:
            sw = int(self.winfo_screenwidth() or 1280)
        except Exception:
            sw = 1280
        try:
            sh = int(self.winfo_screenheight() or 800)
        except Exception:
            sh = 800
        return max(320, sw), max(320, sh)

    def _update_wraplengths(self, dialog_width=None):
        """Aggiorna dinamicamente il wraplength delle etichette alla larghezza corrente/target."""
        if dialog_width is not None and int(dialog_width) > 40:
            inner_w = max(220, int(dialog_width) - 40)
            titles_w = inner_w - 48
            server_w = inner_w
            hero_w = inner_w - 26
        else:
            titles_w = self.titles_box.winfo_width() if getattr(self, "titles_box", None) else 0
            server_w = self.server_sec.winfo_width() if getattr(self, "server_sec", None) else 0
            hero_w = self.hero_row.winfo_width() if getattr(self, "hero_row", None) else 0

        if getattr(self, "sub_lbl", None) and self.sub_lbl.winfo_exists():
            ref_w = titles_w if titles_w > 40 else 390
            new_wrap = max(140, int(ref_w) - 8)
            try:
                old_wrap = int(float(self.sub_lbl.cget("wraplength") or 0))
            except Exception:
                old_wrap = 0
            if abs(new_wrap - old_wrap) >= 2:
                self.sub_lbl.configure(wraplength=new_wrap)

        if getattr(self, "port_hint_lbl", None) and self.port_hint_lbl.winfo_exists():
            ref_w = server_w if server_w > 40 else 440
            new_wrap = max(160, int(ref_w) - 32)
            try:
                old_wrap = int(float(self.port_hint_lbl.cget("wraplength") or 0))
            except Exception:
                old_wrap = 0
            if abs(new_wrap - old_wrap) >= 2:
                self.port_hint_lbl.configure(wraplength=new_wrap)

        if getattr(self, "locked_hero_lbl", None) and self.locked_hero_lbl.winfo_exists():
            ref_w = hero_w if hero_w > 40 else 430
            btn_req = 0
            if getattr(self, "btn_change_char", None) and self.btn_change_char.winfo_exists():
                btn_req = max(60, int(self.btn_change_char.winfo_reqwidth() or 86))
            new_wrap = max(120, int(ref_w) - btn_req - 40)
            try:
                old_wrap = int(float(self.locked_hero_lbl.cget("wraplength") or 0))
            except Exception:
                old_wrap = 0
            if abs(new_wrap - old_wrap) >= 2:
                self.locked_hero_lbl.configure(wraplength=new_wrap)

    def _on_main_configure(self, event=None):
        if getattr(self, "_fitting_geometry", False):
            return
        if event is None or getattr(event, "widget", None) is not getattr(self, "_main_frame", None):
            return
        w = int(getattr(event, "width", 0) or 0)
        if w > 40:
            self._update_wraplengths(dialog_width=w)

    def _fit_geometry(self, center=False):
        """Dimensiona e centra la finestra garantendo zero clipping su testi lunghi e schermi compatti."""
        self._fitting_geometry = True
        try:
            sw, sh = self._available_screen_bounds()
            max_w = max(320, sw - 40)
            max_h = max(320, sh - 60)

            self.update_idletasks()
            seed_w = min(max_w, max(520, self.winfo_width() if not center else 520))
            self._update_wraplengths(dialog_width=seed_w)
            self.update_idletasks()

            req_w = int(self.winfo_reqwidth() or 0)
            base_w = min(max_w, 520 if center else max(520, self.winfo_width()))
            w = min(max_w, max(base_w, req_w + 16))
            if abs(w - seed_w) >= 2:
                self._update_wraplengths(dialog_width=w)
                self.update_idletasks()
                req_w = int(self.winfo_reqwidth() or req_w)

            req_h = int(self.winfo_reqheight() or 0)
            base_h = min(max_h, (435 if self.lock_character else 520) if center else max(520, self.winfo_height()))
            h = min(max_h, max(base_h, req_h + 16))

            # Measure minimum height cleanly at compact width, then restore target width wraplengths
            cand_min_w = min(max_w, max(480, req_w if req_w > 520 else 480))
            if abs(cand_min_w - w) >= 2:
                self._update_wraplengths(dialog_width=cand_min_w)
                self.update_idletasks()
                min_req_w = int(self.winfo_reqwidth() or cand_min_w)
                min_req_h = int(self.winfo_reqheight() or req_h)
                self._update_wraplengths(dialog_width=w)
                self.update_idletasks()
            else:
                min_req_w = req_w
                min_req_h = req_h

            min_w = min(max_w, max(460, min_req_w))
            min_h = min(max_h, max(415 if self.lock_character else 480, max(req_h, min_req_h)))
            h = min(max_h, max(h, min_h))
            try:
                self.minsize(min_w, min_h)
            except Exception:
                pass

            try:
                if center:
                    mw = self.master.winfo_width()
                    mh = self.master.winfo_height()
                    mx = self.master.winfo_rootx()
                    my = self.master.winfo_rooty()
                    x = mx + (mw - w) // 2
                    y = my + (mh - h) // 2
                else:
                    x = self.winfo_rootx()
                    y = self.winfo_rooty()
                x = max(0, min(max(0, sw - w), x))
                y = max(0, min(max(0, sh - h), y))
                self.geometry(f"{w}x{h}+{x}+{y}")
                self.update_idletasks()
            except Exception:
                pass
        finally:
            self._fitting_geometry = False

    def _toggle_pin_visibility(self):
        """Mostra o nasconde il PIN di sessione."""
        self._pin_visible = not getattr(self, "_pin_visible", False)
        if getattr(self, "pin_entry", None):
            self.pin_entry.config(show="" if self._pin_visible else "•")

    def unlock_character_selection(self):
        """Sblocca la selezione completa dei personaggi restando nel dialogo di connessione."""
        self.lock_character = False
        for child in list(self.winfo_children()):
            child.destroy()
        self.setup_ui()
        self._fit_geometry(center=False)

    def set_local_ip(self):
        """Imposta rapidamente l'IP su localhost (127.0.0.1)."""
        self.ip_var.set("127.0.0.1")

    def refresh_listbox(self):
        """Aggiorna la lista dei personaggi con dettagli e preserva/imposta la selezione attiva."""
        if not getattr(self, "char_listbox", None):
            return
        self.char_listbox.delete(0, tk.END)
        characters = getattr(self.manager, "characters", [])
        
        if not characters:
            self.char_listbox.insert(tk.END, f"  {_t('login_no_characters_note')}")
            self.char_listbox.itemconfig(0, fg=TEXT_MUTED)
            return

        target_idx = 0
        init_name = getattr(self.initial_character, "name", None) if self.initial_character else None

        for idx, c in enumerate(characters):
            camp = f" [{c.campaign}]" if getattr(c, "campaign", None) else ""
            race = f" ({c.race})" if getattr(c, "race", None) else ""
            self.char_listbox.insert(tk.END, f"  ⚔️  {c.name}  •  Lv.{c.level} {c.char_class}{race}{camp}")
            if init_name and c.name == init_name:
                target_idx = idx

        self.char_listbox.selection_set(target_idx)
        self.char_listbox.activate(target_idx)
        self.char_listbox.see(target_idx)

    def open_character_hub(self):
        """Apre l'Hub unificato Gestione Personaggi per creare, modificare, duplicare o esportare eroi."""
        from .character_manager_ui import CharacterManagerDialog
        selected_id = getattr(self.initial_character, "id", None)
        if not selected_id and self.char_listbox:
            sel = self.char_listbox.curselection()
            chars = getattr(self.manager, "characters", [])
            if sel and 0 <= sel[0] < len(chars):
                selected_id = getattr(chars[sel[0]], "id", None)

        def on_hub_selected(char):
            self.initial_character = char

        dlg = CharacterManagerDialog(
            self,
            manager=self.manager,
            on_select_callback=on_hub_selected,
            selected_char_id=selected_id
        )
        self.wait_window(dlg)
        self.refresh_listbox()

    def create_character(self):
        """Apre il wizard di creazione personaggio e seleziona il nuovo eroe."""
        def on_wizard_done(new_char):
            self.initial_character = new_char
            self.refresh_listbox()

        ui = CharacterCreationWizard(self, self.manager, on_complete_callback=on_wizard_done)
        self.wait_window(ui)

    def connect(self):
        """Conferma la scelta del server e del personaggio ed esce dal dialogo."""
        ip = self.ip_var.get().strip()
        if not ip:
            messagebox.showerror("Errore", "Inserisci l'IP o l'indirizzo del server.")
            return
        if ":" in ip and ip.count(":") == 1:
            host_part, port_part = ip.split(":", 1)
            if not host_part.strip() or not port_part.strip().isdigit() or not (1 <= int(port_part.strip()) <= 65535):
                messagebox.showerror("Errore", "Porta del server non valida (usa un numero tra 1 e 65535).")
                return

        self.session_password = self.password_var.get().strip()

        if self.lock_character and self.initial_character is not None:
            save_server_history(ip)
            self.result = (ip, self.initial_character)
            self.destroy()
            return
            
        characters = getattr(self.manager, "characters", [])
        if not characters:
            if messagebox.askyesno("Nessun Personaggio", "Non hai ancora nessun personaggio creato.\nVuoi crearne uno adesso?"):
                self.create_character()
            return

        sel = self.char_listbox.curselection()
        if not sel or sel[0] >= len(characters):
            messagebox.showerror(_t("error"), _t("login_no_char_selected"))
            return
            
        char = characters[sel[0]]
        save_server_history(ip)
        self.result = (ip, char)
        self.destroy()
        
    def on_close(self):
        """Chiude il dialogo senza connettere."""
        self.result = None
        self.destroy()
