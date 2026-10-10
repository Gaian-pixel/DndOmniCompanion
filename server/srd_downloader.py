import tkinter as tk
from common.messagebox import messagebox
from tkinter import ttk
import urllib.request
import os
import threading

DOWNLOADABLE_COMPENDIUMS = [
    {
        "name": "5e SRD - Mostri (Open5e)",
        "url": "https://raw.githubusercontent.com/Open5e/open5e-api/master/data/WOTC_5e_SRD_v5.1/monsters.json",
        "filename": "open5e_monsters.json",
        "type": "Mostri"
    },
    {
        "name": "5e SRD - Incantesimi (Open5e)",
        "url": "https://raw.githubusercontent.com/Open5e/open5e-api/master/data/WOTC_5e_SRD_v5.1/spells.json",
        "filename": "open5e_spells.json",
        "type": "Incantesimi"
    },
    {
        "name": "5e SRD - Oggetti Magici (Open5e)",
        "url": "https://raw.githubusercontent.com/Open5e/open5e-api/master/data/WOTC_5e_SRD_v5.1/magicitems.json",
        "filename": "open5e_magicitems.json",
        "type": "Oggetti Magici"
    },
    {
        "name": "Tome of Beasts (Kobold Press) - Mostri",
        "url": "https://raw.githubusercontent.com/Open5e/open5e-api/master/data/tome_of_beasts/monsters.json",
        "filename": "tob_monsters.json",
        "type": "Mostri"
    },
    {
        "name": "Creature Codex (Kobold Press) - Mostri",
        "url": "https://raw.githubusercontent.com/Open5e/open5e-api/master/data/creature_codex/monsters.json",
        "filename": "cc_monsters.json",
        "type": "Mostri"
    }
]

from common.theme import apply_modern_window_style

class CompendiumDownloaderUI(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Gestore Compendi Offline")
        self.minsize(550, 400)
        apply_modern_window_style(self)
        
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "srd_data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.setup_ui()
        
    def setup_ui(self):
        ttk.Label(self, text="Compendi e SRD Aggiuntivi (Offline)", style="Title.TLabel").pack(pady=10)
        ttk.Label(self, text="Scarica questi compendi famosi per consultarli e importarli istantaneamente senza connessione Internet.", style="Muted.TLabel", wraplength=500).pack(pady=5)
        
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tree = ttk.Treeview(frame, columns=("Nome", "Stato"), show="headings", height=8)
        self.tree.heading("Nome", text="Nome Compendio")
        self.tree.heading("Stato", text="Stato")
        self.tree.column("Nome", width=350)
        self.tree.column("Stato", width=150, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.refresh_list()
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Aggiorna Lista", command=self.refresh_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Scarica Selezionato", command=self.download_selected, style="Success.TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Elimina", command=self.delete_selected, style="Primary.TButton").pack(side=tk.RIGHT, padx=5)
        
        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel").pack(side=tk.BOTTOM, fill=tk.X, pady=2)

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for comp in DOWNLOADABLE_COMPENDIUMS:
            path = os.path.join(self.data_dir, comp["filename"])
            if os.path.exists(path):
                size_mb = os.path.getsize(path) / (1024 * 1024)
                status = f"Scaricato ({size_mb:.1f} MB)"
            else:
                status = "Non Scaricato"
            self.tree.insert("", tk.END, values=(comp["name"], status))

    def get_selected_compendium(self):
        sel = self.tree.selection()
        if not sel: return None
        name = self.tree.item(sel[0])["values"][0]
        for comp in DOWNLOADABLE_COMPENDIUMS:
            if comp["name"] == name:
                return comp
        return None

    def download_selected(self):
        comp = self.get_selected_compendium()
        if not comp: return
        
        path = os.path.join(self.data_dir, comp["filename"])
        
        self.status_var.set(f"Download in corso: {comp['name']}...")
        
        def do_download():
            try:
                req = urllib.request.Request(comp["url"], headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = response.read()
                with open(path, "wb") as f:
                    f.write(data)
                self.after(0, lambda: self.status_var.set("Download completato!"))
                self.after(0, self.refresh_list)
            except Exception as e:
                self.after(0, lambda: self.status_var.set("Errore nel download."))
                self.after(0, lambda err=e: messagebox.showerror("Errore", str(err)))
                
        threading.Thread(target=do_download, daemon=True).start()
        
    def delete_selected(self):
        comp = self.get_selected_compendium()
        if not comp: return
        
        path = os.path.join(self.data_dir, comp["filename"])
        if os.path.exists(path):
            if messagebox.askyesno("Elimina", f"Sei sicuro di voler eliminare {comp['name']}?"):
                os.remove(path)
                self.refresh_list()
                self.status_var.set("File eliminato.")

