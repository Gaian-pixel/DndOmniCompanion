import os
import urllib.request
import urllib.parse
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import html.parser
from common.theme import apply_modern_window_style

MAPS_REPO = [
    {
        "name": "Costa della Spada (Faerûn) - Alta Ris.",
        "description": "Mappa ufficiale D&D ad altissima risoluzione della Costa della Spada.",
        "url": "https://media.wizards.com/2015/images/dnd/resources/Sword-Coast-Map_HighRes.jpg",
        "filename": "sword_coast_high.jpg"
    },
    {
        "name": "Costa della Spada (Faerûn) - Media Ris.",
        "description": "Mappa ufficiale D&D a media risoluzione per PC meno potenti.",
        "url": "https://media.wizards.com/2015/images/dnd/resources/Sword-Coast-Map_MedRes.jpg",
        "filename": "sword_coast_med.jpg"
    },
    {
        "name": "Mappa del Mondo Esagonale",
        "description": "Una classica mappa del mondo a esagoni (Open Source).",
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/75/Hex_map.png",
        "filename": "hex_world.png"
    }
]

class ImageParser(html.parser.HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            for attr, val in attrs:
                if attr == 'src':
                    full_url = urllib.parse.urljoin(self.base_url, val)
                    self.images.append(full_url)

class MapDownloaderDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Downloader Mappe")
        self.geometry("750x550")
        apply_modern_window_style(self)
        
        self.maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
        os.makedirs(self.maps_dir, exist_ok=True)
        
        self.setup_ui()

    def setup_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tab_repo = ttk.Frame(self.notebook)
        self.tab_scraper = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_repo, text="Mappe Predefinite")
        self.notebook.add(self.tab_scraper, text="Scraping da URL")
        
        self.setup_repo_tab()
        self.setup_scraper_tab()

    def setup_repo_tab(self):
        ttk.Label(self.tab_repo, text="Seleziona una mappa pronta all'uso da scaricare:", style='Title.TLabel').pack(pady=10)
        
        list_frame = ttk.Frame(self.tab_repo)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        self.tree_repo = ttk.Treeview(list_frame, columns=("Nome", "Descrizione", "Stato"), show="headings", height=8)
        self.tree_repo.heading("Nome", text="Nome Mappa")
        self.tree_repo.heading("Descrizione", text="Descrizione")
        self.tree_repo.heading("Stato", text="Stato")
        
        self.tree_repo.column("Nome", width=180)
        self.tree_repo.column("Descrizione", width=250)
        self.tree_repo.column("Stato", width=100)
        
        self.tree_repo.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree_repo.yview)
        self.tree_repo.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.populate_repo_list()
        
        bot_frame = ttk.Frame(self.tab_repo)
        bot_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.btn_download_repo = ttk.Button(bot_frame, text="Scarica Selezionata", command=self.download_selected_repo, style='Success.TButton')
        self.btn_download_repo.pack(side=tk.LEFT)
        
        self.progress_var_repo = tk.DoubleVar()
        self.progress_bar_repo = ttk.Progressbar(bot_frame, variable=self.progress_var_repo, maximum=100)
        self.progress_bar_repo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        self.status_label_repo = ttk.Label(bot_frame, text="")
        self.status_label_repo.pack(side=tk.LEFT, padx=10)

    def populate_repo_list(self):
        for item in self.tree_repo.get_children():
            self.tree_repo.delete(item)
            
        for i, m in enumerate(MAPS_REPO):
            filepath = os.path.join(self.maps_dir, m["filename"])
            status = "Scaricata" if os.path.exists(filepath) else "Non scaricata"
            self.tree_repo.insert("", tk.END, iid=str(i), values=(m["name"], m["description"], status))

    def download_selected_repo(self):
        selected = self.tree_repo.selection()
        if not selected:
            messagebox.showwarning("Nessuna selezione", "Seleziona una mappa dalla lista.")
            return
            
        index = int(selected[0])
        map_info = MAPS_REPO[index]
        self._start_download(map_info["url"], map_info["filename"], self.btn_download_repo, self.progress_var_repo, self.status_label_repo, self.populate_repo_list)

    def setup_scraper_tab(self):
        top_frame = ttk.Frame(self.tab_scraper)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Inserisci l'URL di una pagina web per cercare immagini (es. Pinterest, blog, etc.):").pack(side=tk.TOP, anchor="w", pady=5)
        
        url_frame = ttk.Frame(top_frame)
        url_frame.pack(fill=tk.X)
        ttk.Label(url_frame, text="URL:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        btn_scrape = ttk.Button(url_frame, text="Analizza Pagina", command=self.scrape_url, style='Info.TButton')
        btn_scrape.pack(side=tk.LEFT, padx=5)

        list_frame = ttk.Frame(self.tab_scraper)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tree_scrape = ttk.Treeview(list_frame, columns=("URL", "Nome File"), show="headings", height=8)
        self.tree_scrape.heading("URL", text="Indirizzo Immagine")
        self.tree_scrape.heading("Nome File", text="Nome File Suggerito")
        
        self.tree_scrape.column("URL", width=450)
        self.tree_scrape.column("Nome File", width=150)
        
        self.tree_scrape.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree_scrape.yview)
        self.tree_scrape.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        bot_frame = ttk.Frame(self.tab_scraper)
        bot_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.btn_download_scrape = ttk.Button(bot_frame, text="Scarica Immagine", command=self.download_selected_scrape, style='Success.TButton', state=tk.DISABLED)
        self.btn_download_scrape.pack(side=tk.LEFT)
        
        self.progress_var_scrape = tk.DoubleVar()
        self.progress_bar_scrape = ttk.Progressbar(bot_frame, variable=self.progress_var_scrape, maximum=100)
        self.progress_bar_scrape.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        self.status_label_scrape = ttk.Label(bot_frame, text="")
        self.status_label_scrape.pack(side=tk.LEFT, padx=10)

    def scrape_url(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        
        if not url.startswith('http'):
            url = 'https://' + url
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)
            
        self.status_label_scrape.config(text="Ricerca in corso...")
        for item in self.tree_scrape.get_children():
            self.tree_scrape.delete(item)
            self.btn_download_scrape.config(state=tk.DISABLED)
            
        def task():
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    content_type = response.getheader('Content-Type', '')
                    # Se l'URL punta direttamente a un'immagine
                    if content_type.startswith('image/'):
                        self.after(0, self._add_scraped_image, url)
                        self.after(0, lambda: self.status_label_scrape.config(text="Immagine trovata!"))
                        return
                    
                    html_content = response.read().decode('utf-8', errors='ignore')
                    parser = ImageParser(url)
                    parser.feed(html_content)
                    
                    # Filtro formati comuni ed escludo le icone piccolissime (per lo più svg/gif)
                    valid_exts = ('.png', '.jpg', '.jpeg', '.webp')
                    found = 0
                    for img_url in set(parser.images):
                        url_lower = img_url.lower()
                        # Allow if it has a valid extension or looks like an image URL without explicit extension but not svg/gif
                        if any(url_lower.endswith(ext) for ext in valid_exts) or ('/image/' in url_lower):
                            self.after(0, self._add_scraped_image, img_url)
                            found += 1
                            
                    self.after(0, lambda: self.status_label_scrape.config(text=f"Trovate {found} immagini supportate."))
            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("Errore Scraping", f"Impossibile analizzare l'URL:\n{err}"))
                self.after(0, lambda: self.status_label_scrape.config(text="Errore durante la ricerca."))
                
        threading.Thread(target=task, daemon=True).start()

    def _add_scraped_image(self, img_url):
        filename = img_url.split('/')[-1].split('?')[0]
        if not filename or '.' not in filename:
            filename = "immagine_mappa.jpg"
        self.tree_scrape.insert("", tk.END, values=(img_url, filename))
        self.btn_download_scrape.config(state=tk.NORMAL)

    def download_selected_scrape(self):
        selected = self.tree_scrape.selection()
        if not selected:
            messagebox.showwarning("Nessuna selezione", "Seleziona un'immagine dalla lista.")
            return
            
        values = self.tree_scrape.item(selected[0], 'values')
        img_url = values[0]
        suggested_filename = values[1]
        
        filename = simpledialog.askstring("Nome File", "Salva l'immagine come:", initialvalue=suggested_filename)
        if not filename:
            return
            
        if not any(filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']):
            filename += ".jpg"
            
        self._start_download(img_url, filename, self.btn_download_scrape, self.progress_var_scrape, self.status_label_scrape)

    def _start_download(self, url, filename, btn, progress_var, status_label, callback=None):
        filepath = os.path.join(self.maps_dir, filename)
        if os.path.exists(filepath):
            if not messagebox.askyesno("Mappa Esistente", "La mappa esiste già nella cartella 'maps'. Sovrascrivere?"):
                return
                
        btn.config(state="disabled")
        status_label.config(text="Scaricamento in corso...")
        progress_var.set(0)
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        thread = threading.Thread(target=self._download_task, args=(req, filepath, btn, progress_var, status_label, callback))
        thread.daemon = True
        thread.start()

    def _download_task(self, req, filepath, btn, progress_var, status_label, callback):
        try:
            with urllib.request.urlopen(req, timeout=15) as response, open(filepath, 'wb') as out_file:
                total_size = response.getheader('Content-Length')
                total_size = int(total_size) if total_size else 1000000
                    
                block_size = 8192
                read_so_far = 0
                
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    out_file.write(buffer)
                    read_so_far += len(buffer)
                    
                    if total_size > 0:
                        percent = (read_so_far / total_size) * 100
                        self.after(0, progress_var.set, min(percent, 100))
                        
            self.after(0, self._download_complete, True, "Scaricata con successo!", btn, progress_var, status_label, callback)
        except Exception as e:
            self.after(0, self._download_complete, False, f"Errore: {str(e)}", btn, progress_var, status_label, callback)

    def _download_complete(self, success, message, btn, progress_var, status_label, callback):
        btn.config(state="normal")
        status_label.config(text=message)
        progress_var.set(100 if success else 0)
        
        if callback:
            callback()
        
        if success:
            messagebox.showinfo("Successo", "Immagine scaricata e salvata nella cartella 'maps'. Puoi caricarla subito dall'Editor Mappe!")
