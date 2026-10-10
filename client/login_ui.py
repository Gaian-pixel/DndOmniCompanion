import tkinter as tk
from common.messagebox import messagebox
from tkinter import ttk
from common.theme import BG_COLOR, TEXT_COLOR, ACCENT_RED, SURFACE_COLOR, BORDER_COLOR, apply_modern_window_style
from .character_manager import Character
from .character_sheet_ui import CharacterSheetUI
from .character_creation_wizard import CharacterCreationWizard

class LoginDialog(tk.Toplevel):
    def __init__(self, master, character_manager):
        super().__init__(master)
        self.title("Accesso alla Sessione D&D")
        self.minsize(400, 350)
        apply_modern_window_style(self)
        self.transient(master)
        self.grab_set()
        
        self.manager = character_manager
        self.result = None # Verrà impostato a (ip_server, character)
        self.default_font = ("Georgia", 11)
        
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Server IP:").pack(anchor="w")
        self.ip_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(main_frame, textvariable=self.ip_var).pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(main_frame, text="Seleziona Personaggio:").pack(anchor="w")
        
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.char_listbox = tk.Listbox(list_frame, font=self.default_font, bg=SURFACE_COLOR, fg=TEXT_COLOR, selectbackground=ACCENT_RED, height=6, relief="flat", highlightthickness=1, highlightbackground=BORDER_COLOR)
        self.char_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, command=self.char_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.char_listbox.config(yscrollcommand=scrollbar.set)
        
        self.refresh_listbox()
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Crea Nuovo (Wizard)", command=self.create_character).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(btn_frame, text="Modifica", command=self.edit_character).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        ttk.Button(main_frame, text="Connetti al Server", command=self.connect).pack(fill=tk.X, pady=(10, 0))

    def refresh_listbox(self):
        self.char_listbox.delete(0, tk.END)
        for c in self.manager.characters:
            camp = f" [{c.campaign}]" if c.campaign else ""
            self.char_listbox.insert(tk.END, f"{c.name} - Lv.{c.level} {c.char_class}{camp}")

    def create_character(self):
        ui = CharacterCreationWizard(self, self.manager, on_complete_callback=lambda _: self.refresh_listbox())
        self.wait_window(ui)

    def edit_character(self):
        sel = self.char_listbox.curselection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un personaggio da modificare.")
            return
        char = self.manager.characters[sel[0]]
        ui = CharacterSheetUI(self, char, self.manager, on_save_callback=lambda _: self.refresh_listbox())
        self.wait_window(ui)

    def connect(self):
        ip = self.ip_var.get().strip()
        if not ip:
            messagebox.showerror("Errore", "Inserisci l'IP del server.")
            return
            
        sel = self.char_listbox.curselection()
        if not sel:
            messagebox.showerror("Errore", "Seleziona o crea un personaggio per connetterti.")
            return
            
        char = self.manager.characters[sel[0]]
        self.result = (ip, char)
        self.destroy()
        
    def on_close(self):
        self.destroy()

