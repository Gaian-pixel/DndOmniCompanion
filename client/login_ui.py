import tkinter as tk
from tkinter import ttk
import os
from common.messagebox import messagebox
from common.i18n import _t, get_language
from common.file_utils import get_writable_dir, load_json, atomic_save_json
from common.theme import (
    TEXT_COLOR, ACCENT_RED, ACCENT_GOLD, SURFACE_COLOR, SURFACE_COLOR_ALT,
    BORDER_COLOR, BG_COLOR, TEXT_MUTED, FONT_MAIN, FONT_BOLD, FONT_HEADER,
    apply_modern_window_style
)
from .character_sheet_ui import CharacterSheetUI
from .character_creation_wizard import CharacterCreationWizard


SETTINGS_PATH = os.path.join(get_writable_dir(), "client_data", "settings.json")


def load_server_history():
    """Carica l'ultimo IP server usato e la lista dei server recenti da settings.json."""
    settings = load_json(SETTINGS_PATH, default={}) or {}
    last_ip = settings.get("last_server_ip", "127.0.0.1")
    recents = settings.get("recent_servers", [])
    if not recents:
        recents = [last_ip] if last_ip else ["127.0.0.1"]
    if "127.0.0.1" not in recents:
        recents.append("127.0.0.1")
    return last_ip, recents


def save_server_history(ip: str):
    """Salva l'IP server nella cronologia persistente in settings.json."""
    if not ip or not ip.strip():
        return
    clean_ip = ip.strip()
    settings = load_json(SETTINGS_PATH, default={}) or {}
    recents = settings.get("recent_servers", [])
    if clean_ip in recents:
        recents.remove(clean_ip)
    recents.insert(0, clean_ip)
    settings["recent_servers"] = recents[:6]
    settings["last_server_ip"] = clean_ip
    try:
        atomic_save_json(SETTINGS_PATH, settings)
    except Exception as e:
        print(f"[LoginDialog] Errore salvataggio server: {e}")


class LoginDialog(tk.Toplevel):
    """
    Dialogo di connessione e unione a una partita D&D.
    Consente all'utente di selezionare/digitare subito l'IP del Server
    e scegliere il personaggio con cui unirsi alla sessione.
    """

    def __init__(self, master, character_manager, initial_character=None, initial_ip=None):
        super().__init__(master)
        self.title(_t("login_dialog_title"))
        self.minsize(480, 480)
        apply_modern_window_style(self)
        self.transient(master)
        self.grab_set()
        
        self.manager = character_manager
        self.initial_character = initial_character
        self.result = None # Verrà impostato a (ip_server, character)
        self.default_font = ("Georgia", 10)
        
        saved_ip, self.recent_servers = load_server_history()
        self.current_ip = initial_ip or saved_ip or "127.0.0.1"
        
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Scorciatoie da tastiera
        self.bind("<Escape>", lambda e: self.on_close())
        self.bind("<Return>", lambda e: self.connect())
        
        # Centra la finestra rispetto al master
        self.update_idletasks()
        try:
            mw = master.winfo_width()
            mh = master.winfo_height()
            mx = master.winfo_rootx()
            my = master.winfo_rooty()
            w = 520
            h = 510
            x = max(0, mx + (mw - w) // 2)
            y = max(0, my + (mh - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
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
        
        titles_box = tk.Frame(top_row, bg=SURFACE_COLOR)
        titles_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(titles_box, text=_t("login_dialog_title"), font=("Georgia", 14, "bold"), bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
        tk.Label(titles_box, text=_t("login_dialog_sub"), font=("Segoe UI", 8), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(1, 0))
        
        tk.Frame(main_frame, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=(0, 12))
        
        # 2. SEZIONE SERVER IP
        server_sec = tk.Frame(main_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        server_sec.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(server_sec, text=_t("login_server_ip"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(0, 6))
        
        ip_row = tk.Frame(server_sec, bg=SURFACE_COLOR)
        ip_row.pack(fill=tk.X)
        
        self.ip_var = tk.StringVar(value=self.current_ip)
        self.ip_combo = ttk.Combobox(ip_row, textvariable=self.ip_var, values=self.recent_servers, font=("Segoe UI", 10))
        self.ip_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        ttk.Button(ip_row, text=_t("login_btn_local"), command=self.set_local_ip, style="Dark.TButton").pack(side=tk.RIGHT)
        
        tk.Label(server_sec, text="Porta predefinita: 5000 (puoi specificare es. 192.168.1.100 o hostname:porta)", font=("Segoe UI", 8), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(4, 0))
        
        # 3. SEZIONE PERSONAGGIO
        char_sec = tk.Frame(main_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        char_sec.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        
        tk.Label(char_sec, text=_t("login_select_char"), font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(0, 6))
        
        list_frame = tk.Frame(char_sec, bg=SURFACE_COLOR)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        self.char_listbox = tk.Listbox(
            list_frame, 
            font=self.default_font, 
            bg=SURFACE_COLOR_ALT, 
            fg=TEXT_COLOR, 
            selectbackground="#3B5BDB", 
            selectforeground="#FFFFFF",
            height=6, 
            relief="flat", 
            highlightthickness=1, 
            highlightbackground=BORDER_COLOR
        )
        self.char_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.char_listbox.bind("<Double-Button-1>", lambda e: self.connect())
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.char_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.char_listbox.config(yscrollcommand=scrollbar.set)
        
        self.refresh_listbox()
        
        char_btn_row = tk.Frame(char_sec, bg=SURFACE_COLOR)
        char_btn_row.pack(fill=tk.X)
        
        ttk.Button(char_btn_row, text=_t("login_btn_create"), command=self.create_character, style="Info.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))
        ttk.Button(char_btn_row, text=_t("login_btn_edit"), command=self.edit_character, style="Dark.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
        ttk.Button(char_btn_row, text=_t("login_btn_delete"), command=self.delete_character, style="Danger.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))
        
        # 4. BOTTONI DI CONFERMA / ANNULLA IN BASSO
        bottom_box = tk.Frame(main_frame)
        bottom_box.pack(fill=tk.X)
        
        ttk.Button(bottom_box, text=_t("login_btn_cancel"), command=self.on_close, style="Dark.TButton").pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(bottom_box, text=_t("login_btn_connect"), command=self.connect, style="Primary.TButton").pack(side=tk.RIGHT)

    def set_local_ip(self):
        """Imposta rapidamente l'IP su localhost (127.0.0.1)."""
        self.ip_var.set("127.0.0.1")

    def refresh_listbox(self):
        """Aggiorna la lista dei personaggi con dettagli e preserva/imposta la selezione attiva."""
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

    def create_character(self):
        """Apre il wizard di creazione personaggio e seleziona il nuovo eroe."""
        def on_wizard_done(new_char):
            self.initial_character = new_char
            self.refresh_listbox()

        ui = CharacterCreationWizard(self, self.manager, on_complete_callback=on_wizard_done)
        self.wait_window(ui)

    def edit_character(self):
        """Apre la scheda del personaggio selezionato per la modifica."""
        sel = self.char_listbox.curselection()
        characters = getattr(self.manager, "characters", [])
        if not sel or not characters or sel[0] >= len(characters):
            messagebox.showwarning(_t("warning"), "Seleziona un personaggio da modificare." if get_language() == "it" else "Select a character to edit.")
            return
        char = characters[sel[0]]
        ui = CharacterSheetUI(self, char, self.manager, on_save_callback=self.refresh_listbox, is_connected=False)
        self.wait_window(ui)
        self.refresh_listbox()
        
    def delete_character(self):
        """Elimina il personaggio selezionato previa conferma."""
        sel = self.char_listbox.curselection()
        characters = getattr(self.manager, "characters", [])
        if not sel or not characters or sel[0] >= len(characters):
            messagebox.showwarning(_t("warning"), "Seleziona un personaggio da eliminare." if get_language() == "it" else "Select a character to delete.")
            return
        char = characters[sel[0]]
        if messagebox.askyesno("Conferma", f"Sei sicuro di voler eliminare il personaggio '{char.name}'?"):
            self.manager.delete_character(char)
            self.initial_character = None
            self.refresh_listbox()

    def connect(self):
        """Conferma la scelta del server e del personaggio ed esce dal dialogo."""
        ip = self.ip_var.get().strip()
        if not ip:
            messagebox.showerror("Errore", "Inserisci l'IP o l'indirizzo del server.")
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
