import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import json
import threading
import os

from common.theme import apply_modern_window_style
from server.compendium_manager import CompendiumManager

class CompendiumDialog(tk.Toplevel):
    def __init__(self, master, on_import_callback=None, is_dm=True):
        super().__init__(master)
        self.title("Compendio 5e SRD")
        self.geometry("450x600")
        apply_modern_window_style(self)
        self.on_import_callback = on_import_callback
        self.is_dm = is_dm
        
        self.base_url = "https://www.dnd5eapi.co/api"
        self.current_items = []  
        self.compendium_manager = CompendiumManager()
        
        self.setup_ui()
        
    def setup_ui(self):
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Categoria/Sorgente:").pack(side=tk.LEFT)
        self.category_var = tk.StringVar(value="Incantesimi")
        
        categories = ["Incantesimi", "Regole", "Classi", "Tratti", "Equipaggiamento", "Armi", "Pozioni", "Oggetti Magici"]
        if self.is_dm:
            categories = ["Mostri"] + categories
            
        import os
        try:
            from server.srd_downloader import DOWNLOADABLE_COMPENDIUMS
            self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "srd_data")
            self.offline_compendiums = {}
            for comp in DOWNLOADABLE_COMPENDIUMS:
                path = os.path.join(self.data_dir, comp["filename"])
                if os.path.exists(path):
                    name = f"[OFFLINE] {comp['name']}"
                    categories.append(name)
                    self.offline_compendiums[name] = path
        except ImportError:
            self.offline_compendiums = {}
            
        self.category_cb = ttk.Combobox(top_frame, textvariable=self.category_var, values=categories, state="readonly", width=25)
        self.category_cb.pack(side=tk.LEFT, padx=5)
        self.category_cb.bind("<<ComboboxSelected>>", self.fetch_list)
        if not self.is_dm:
            self.category_var.set("Incantesimi")
        else:
            self.category_var.set("Mostri")
        
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Label(search_frame, text="Cerca:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.filter_list)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.listbox = tk.Listbox(self)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.listbox.bind("<Double-Button-1>", lambda e: self.view_details())
        
        self.status_var = tk.StringVar(value="Seleziona una categoria per iniziare.")
        ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel").pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Consulta", command=self.view_details, style="Info.TButton").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Gestisci Compendi", command=self.open_downloader).pack(side=tk.LEFT, padx=5)
        
        if self.is_dm:
            ttk.Button(btn_frame, text="Crea Custom", command=self.create_custom_item).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Importa", command=self.import_selected, style="Primary.TButton").pack(side=tk.RIGHT, padx=5)
        
        self.fetch_list()
        
    def create_custom_item(self):
        cat = self.category_var.get()
        if cat.startswith("[OFFLINE] "):
            messagebox.showinfo("Avviso", "Non puoi creare un custom in una categoria offline. Seleziona una categoria base come 'Mostri' o 'Equipaggiamento'.")
            return
            
        win = tk.Toplevel(self)
        win.title(f"Nuovo Custom: {cat}")
        win.geometry("350x400")
        apply_modern_window_style(win)
        
        ttk.Label(win, text="Nome:").pack(pady=5)
        name_var = tk.StringVar()
        ttk.Entry(win, textvariable=name_var).pack()
        
        if cat == "Mostri":
            ttk.Label(win, text="HP:").pack(pady=5)
            hp_var = tk.StringVar(value="10")
            ttk.Entry(win, textvariable=hp_var).pack()
            
            ttk.Label(win, text="Iniziativa (bonus):").pack(pady=5)
            init_var = tk.StringVar(value="0")
            ttk.Entry(win, textvariable=init_var).pack()
            
        ttk.Label(win, text="Descrizione (opzionale):").pack(pady=5)
        from tkinter import scrolledtext
        desc_text = scrolledtext.ScrolledText(win, height=5, wrap=tk.WORD)
        desc_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        def save():
            if not name_var.get():
                messagebox.showerror("Errore", "Inserisci un nome.")
                return
            
            item = {"name": name_var.get(), "desc": desc_text.get("1.0", tk.END).strip()}
            if cat == "Mostri":
                try:
                    item["hp"] = int(hp_var.get())
                    item["initiative"] = int(init_var.get())
                except:
                    pass
            self.compendium_manager.add_item(cat, item)
            self.update_listbox()
            win.destroy()
            
        ttk.Button(win, text="Salva", command=save, style="Success.TButton").pack(pady=10)

    def open_downloader(self):
        try:
            from server.srd_downloader import CompendiumDownloaderUI
            win = CompendiumDownloaderUI(self.master)
            win.grab_set()
            # Optionally re-setup self after close
            self.wait_window(win)
            self.setup_categories()
        except ImportError as e:
            messagebox.showerror("Errore", str(e))

    def setup_categories(self):
        categories = ["Incantesimi", "Regole", "Classi", "Tratti", "Equipaggiamento", "Armi", "Pozioni", "Oggetti Magici"]
        if self.is_dm:
            categories = ["Mostri"] + categories
        try:
            from server.srd_downloader import DOWNLOADABLE_COMPENDIUMS
            for comp in DOWNLOADABLE_COMPENDIUMS:
                path = os.path.join(self.data_dir, comp["filename"])
                if os.path.exists(path):
                    name = f"[OFFLINE] {comp['name']}"
                    categories.append(name)
                    self.offline_compendiums[name] = path
        except: pass
        self.category_cb["values"] = categories

    def fetch_list(self, event=None):
        cat = self.category_var.get()
        
        if hasattr(self, 'offline_compendiums') and cat in self.offline_compendiums:
            self.status_var.set("Caricamento compendio offline...")
            self.listbox.delete(0, tk.END)
            def do_load():
                try:
                    with open(self.offline_compendiums[cat], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self.current_items = data
                    self.after(0, self.update_listbox)
                    self.after(0, lambda: self.status_var.set(f"Trovati {len(self.current_items)} elementi."))
                except Exception as e:
                    self.after(0, lambda err=e: messagebox.showerror("Errore", str(err)))
            threading.Thread(target=do_load, daemon=True).start()
            return
            
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
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode('utf-8'))
                
                self.current_items = data.get("results", data.get("equipment", []))
                try:
                    self.after(0, self.update_listbox)
                    self.after(0, lambda: self.status_var.set(f"Trovati {len(self.current_items)} elementi."))
                except RuntimeError:
                    pass
            except Exception as e:
                try:
                    self.after(0, lambda: self.status_var.set("Errore nel caricamento."))
                    self.after(0, lambda err=e: messagebox.showerror("Errore", str(err)))
                except RuntimeError:
                    pass
                
        threading.Thread(target=do_fetch, daemon=True).start()

    def update_listbox(self):
        self.listbox.delete(0, tk.END)
        search_text = self.search_var.get().lower()
        
        # Aggiungi prima i custom
        cat = self.category_var.get()
        custom_items = self.compendium_manager.get_items(cat)
        for item in custom_items:
            if "name" in item and search_text in item["name"].lower():
                self.listbox.insert(tk.END, f"[Custom] {item['name']}")
                
        # Poi gli items da SRD o Offline
        for item in self.current_items:
            if "name" in item and search_text in item["name"].lower():
                self.listbox.insert(tk.END, item["name"])

    def filter_list(self, *args):
        self.update_listbox()

    def get_selected_item(self):
        sel = self.listbox.curselection()
        if not sel: return None
        selected_name = self.listbox.get(sel[0])
        
        if selected_name.startswith("[Custom] "):
            real_name = selected_name.replace("[Custom] ", "", 1)
            cat = self.category_var.get()
            for item in self.compendium_manager.get_items(cat):
                if item.get("name") == real_name:
                    return item
            return None
            
        for item in self.current_items:
            if item.get("name") == selected_name:
                return item
        return None

    def view_details(self):
        item = self.get_selected_item()
        if not item: return
        
        cat = self.category_var.get()
        if item.get("is_custom") or (hasattr(self, 'offline_compendiums') and cat in self.offline_compendiums):
            self.show_details_popup(item.get("name", "Dettagli"), item)
            return
            
        url = item.get("url")
        if not url: return
        self.status_var.set(f"Recupero dettagli di {item['name']}...")
        def do_view():
            try:
                req = urllib.request.Request("https://www.dnd5eapi.co" + url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode('utf-8'))
                self.after(0, lambda: self.status_var.set("Dettagli recuperati."))
                self.after(0, lambda: self.show_details_popup(item["name"], data))
            except Exception as e:
                self.after(0, lambda: self.status_var.set("Errore."))
                self.after(0, lambda err=e: messagebox.showerror("Errore", str(err)))
        threading.Thread(target=do_view, daemon=True).start()
        
    def show_details_popup(self, name, data):
        win = tk.Toplevel(self)
        win.title(name)
        win.geometry("500x600")
        apply_modern_window_style(win)
        
        from tkinter import scrolledtext
        txt = scrolledtext.ScrolledText(win, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        lines = []
        if "desc" in data:
            desc = data["desc"]
            if isinstance(desc, list): desc = "\n\n".join(desc)
            lines.append(desc)
            lines.append("\n" + "="*40 + "\n")
            
        for k, v in data.items():
            if k not in ["index", "url", "desc"]:
                if isinstance(v, (str, int, bool)):
                    lines.append(f"{k.capitalize()}: {v}")
                elif isinstance(v, list) and v and isinstance(v[0], dict) and "name" in v[0]:
                    items = ", ".join(i.get("name", "") for i in v)
                    lines.append(f"{k.capitalize()}: {items}")
                elif isinstance(v, dict) and "name" in v:
                    lines.append(f"{k.capitalize()}: {v['name']}")
                    
        txt.insert("1.0", "\n".join(lines))
        txt.config(state="disabled")

    def import_selected(self):
        item = self.get_selected_item()
        if not item or not self.on_import_callback: return
        
        cat = self.category_var.get()
        if item.get("is_custom"):
            self.on_import_callback(item, cat)
            return
            
        if hasattr(self, 'offline_compendiums') and cat in self.offline_compendiums:
            real_cat = "Mostri"
            try:
                from server.srd_downloader import DOWNLOADABLE_COMPENDIUMS
                for comp in DOWNLOADABLE_COMPENDIUMS:
                    if f"[OFFLINE] {comp['name']}" == cat:
                        real_cat = comp["type"]
                        break
            except: pass
            self.on_import_callback(item, real_cat)
            return
            
        url = item.get("url")
        if not url: return
        
        self.status_var.set(f"Importazione di {item['name']}...")
        def do_import():
            try:
                req = urllib.request.Request("https://www.dnd5eapi.co" + url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode('utf-8'))
                
                self.after(0, lambda: self.status_var.set("Importazione completata."))
                self.after(0, lambda: self.on_import_callback(data, cat))
            except Exception as e:
                self.after(0, lambda: self.status_var.set("Errore nell'importazione."))
                self.after(0, lambda err=e: messagebox.showerror("Errore", str(err)))
                
        threading.Thread(target=do_import, daemon=True).start()

