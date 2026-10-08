# map_editor.py
import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox, ttk, colorchooser
import json
from PIL import Image, ImageTk

from common.hex_utils import Hex, HexLayout

class Tooltip:
    # Questa classe interna non necessita di modifiche
    def __init__(self, parent):
        self.parent=parent; self.tip_window=None
    def show(self, event, poi_data):
        if self.tip_window or not poi_data: return
        x, y, _, _=self.parent.bbox("current"); x += self.parent.winfo_rootx() + 25; y += self.parent.winfo_rooty() + 25
        self.tip_window=tk.Toplevel(self.parent)
        self.tip_window.wm_overrideredirect(True); self.tip_window.wm_geometry(f"+{x}+{y}")
        frame=tk.Frame(self.tip_window, bg="#333333", relief="solid", borderwidth=1); frame.pack()
        tk.Label(frame, text=poi_data['title'], font=("", 10, "bold"), bg="#333333", fg="white").pack(pady=(0, 5), padx=5)
        if 'image_tk' in poi_data:
            tk.Label(frame, image=poi_data['image_tk'], bg="#333333").pack(pady=5)
        tk.Label(frame, text=poi_data['caption'], wraplength=200, bg="#333333", fg="white").pack(padx=5, pady=5)
    def hide(self):
        if self.tip_window: self.tip_window.destroy()
        self.tip_window=None

from common.theme import apply_modern_window_style

class MapEditorWindow(tk.Toplevel):
    MAP_SCALES={"Mappa del Mondo / Regione": 15, "Mappa di Esplorazione (POI)": 35, "Mappa di Combattimento": 60}
    POI_COLOR = "#FFD700" # Oro per i POI

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Editor Mappe Esagonali")
        self.geometry("1200x800")
        apply_modern_window_style(self)

        ### MODIFICATO: self.pois è ora un dizionario per mappare Hex -> Dati POI ###
        self.pois = {}
        
        self.grid_hexes=set(); self.hex_to_canvas_id={}
        self.hex_layout=None; self.base_image_path=""
        self.current_hover_poi=None; self.add_poi_mode=False; self.preview_hex_id=None
        self.zoom_level = 1.0; self.hex_border_color = "white"

        ### NUOVO: Variabili per la gestione dell'immagine di sfondo ###
        self.base_image_original = None # Immagine PIL originale non scalata
        self.base_image_tk = None       # Immagine Tkinter attualmente visualizzata
        self.bg_canvas_id = None        # ID dell'oggetto immagine sul canvas

        self.setup_gui()
        self.tooltip=Tooltip(self.canvas)

    def setup_gui(self):
        main_frame=ttk.Frame(self, padding=(10, 10)); main_frame.pack(fill=tk.BOTH, expand=True)
        toolbar=ttk.Frame(main_frame); toolbar.pack(fill=tk.X, pady=5)
        ttk.Button(toolbar, text="Carica Immagine", command=self.load_base_image, style="Info.TButton").pack(side=tk.LEFT, padx=5)
        map_scale_frame=ttk.Frame(toolbar); map_scale_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(map_scale_frame, text="Tipo di Mappa:").pack(side=tk.LEFT)
        self.map_scale_var=tk.StringVar()
        map_scale_combo=ttk.Combobox(map_scale_frame, textvariable=self.map_scale_var, values=list(self.MAP_SCALES.keys()), state="readonly")
        map_scale_combo.pack(side=tk.LEFT, padx=5); map_scale_combo.bind("<<ComboboxSelected>>", self.on_map_scale_selected)
        ttk.Button(map_scale_frame, text="Colore Griglia", command=self.choose_hex_color).pack(side=tk.LEFT)
        self.add_poi_button=ttk.Button(toolbar, text="Aggiungi POI", command=self.toggle_add_poi_mode, style="Success.TButton")
        self.add_poi_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Salva Mappa", command=self.save_map, style="Primary.TButton").pack(side=tk.LEFT, padx=5)
        self.canvas=tk.Canvas(main_frame, bg="#2b2b2b", highlightthickness=0); self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Motion>", self.on_canvas_motion); self.canvas.bind("<Button-1>", self.on_canvas_left_click); self.canvas.bind("<Button-3>", self.on_canvas_right_click); self.canvas.bind("<Leave>", self.on_canvas_leave)
        self.canvas.bind("<MouseWheel>", self._zoom); self.canvas.bind("<Button-4>", self._zoom); self.canvas.bind("<Button-5>", self._zoom)
        self.canvas.bind("<ButtonPress-2>", self._pan_start); self.canvas.bind("<B2-Motion>", self._pan_move)

    def _zoom(self, event):
        """ ### MODIFICATO: Ora gestisce anche lo zoom dell'immagine di sfondo con debounce e filtri veloci ### """
        factor = 1.1 if (event.num == 4 or event.delta > 0) else 0.9
        
        # Applica lo zoom a griglia e POI
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        self.canvas.scale("all", canvas_x, canvas_y, factor, factor)
        
        # Applica lo zoom all'immagine di sfondo manualmente usando un filtro velocissimo
        if self.base_image_original:
            self.zoom_level *= factor
            new_width = int(self.base_image_original.width * self.zoom_level)
            new_height = int(self.base_image_original.height * self.zoom_level)
            
            # Evita errori se l'immagine diventa troppo piccola
            if new_width > 0 and new_height > 0:
                # Usa NEAREST per prestazioni in tempo reale
                resized_img = self.base_image_original.resize((new_width, new_height), Image.Resampling.NEAREST)
                self.base_image_tk = ImageTk.PhotoImage(resized_img)
                self.canvas.itemconfig(self.bg_canvas_id, image=self.base_image_tk)
                
                # Cancella il vecchio timer di debounce
                if hasattr(self, "_zoom_timer") and self._zoom_timer:
                    self.after_cancel(self._zoom_timer)
                
                # Imposta un timer per ridisegnare ad alta qualità (LANCZOS) quando si smette di zoomare
                self._zoom_timer = self.after(300, self._render_high_res_image, new_width, new_height)
        else:
             self.zoom_level *= factor

    def _render_high_res_image(self, width, height):
        if self.base_image_original:
            resized_img = self.base_image_original.resize((width, height), Image.Resampling.LANCZOS)
            self.base_image_tk = ImageTk.PhotoImage(resized_img)
            self.canvas.itemconfig(self.bg_canvas_id, image=self.base_image_tk)
            self._zoom_timer = None

    def load_base_image(self):
        """ ### MODIFICATO: Memorizza l'immagine originale per lo zoom ### """
        import os
        maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
        file_path = filedialog.askopenfilename(initialdir=maps_dir, filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if not file_path: return
        self.base_image_path = file_path
        
        self.base_image_original = Image.open(file_path) # Salva l'originale
        self.base_image_tk = ImageTk.PhotoImage(self.base_image_original)
        
        if self.bg_canvas_id:
            self.canvas.itemconfig(self.bg_canvas_id, image=self.base_image_tk)
        else:
            self.bg_canvas_id = self.canvas.create_image(0, 0, image=self.base_image_tk, anchor="nw", tags="base_image")
        
        self.canvas.tag_lower("base_image")
        
        # Generazione automatica se c'è già una scala impostata
        if self.hex_layout and not self.grid_hexes:
            if messagebox.askyesno("Generazione Automatica", "Vuoi riempire automaticamente l'immagine appena caricata con gli esagoni?"):
                self.generate_auto_grid()

    def _add_poi_at(self, x, y):
        """ ### MODIFICATO: Trasforma un esagono in un POI ### """
        if not self.hex_layout: return
        
        target_hex = self.hex_layout.pixel_to_hex((x, y))
        
        # Controlla se l'esagono esiste nella griglia
        if target_hex not in self.grid_hexes:
            messagebox.showwarning("Azione non valida", "Puoi aggiungere un Punto di Interesse solo su un esagono esistente.")
            return

        title = simpledialog.askstring("Nuovo POI", "Inserisci il titolo:", parent=self)
        if not title: return
        caption = simpledialog.askstring("Nuovo POI", "Inserisci la didascalia:", parent=self)
        
        # Salva i dati del POI nel dizionario
        self.pois[target_hex] = {"title": title, "caption": caption}
        
        # Colora l'esagono e aggiungi il tag "poi"
        hex_id = self.hex_to_canvas_id.get(target_hex)
        if hex_id:
            self.canvas.itemconfig(hex_id, fill=self.POI_COLOR, stipple="")
            self.canvas.addtag_withtag("poi", hex_id)
        
        self.toggle_add_poi_mode() # Disattiva la modalità dopo aver aggiunto

    def handle_poi_hover(self, event):
        """ ### MODIFICATO: Cerca il POI tramite le coordinate dell'esagono ### """
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        hovered_hex = self.hex_layout.pixel_to_hex((canvas_x, canvas_y)) if self.hex_layout else None
        
        # Se l'esagono sotto il mouse è un POI, mostra il tooltip
        if hovered_hex and hovered_hex in self.pois:
            if self.current_hover_poi != hovered_hex:
                self.current_hover_poi = hovered_hex
                self.tooltip.hide()
                self.tooltip.show(event, self.pois[hovered_hex])
        else:
            self.current_hover_poi = None
            self.tooltip.hide()

    def save_map(self):
        """ ### MODIFICATO: Salva i POI nel nuovo formato ### """
        if not self.hex_layout: messagebox.showerror("Errore", "Non puoi salvare una mappa senza una scala."); return
        import os
        maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
        file_path = filedialog.asksaveasfilename(initialdir=maps_dir, defaultextension=".json", filetypes=[("Mappe D&D", "*.json")])
        if not file_path: return
        
        # Converte le chiavi Hex in stringhe per il salvataggio in JSON
        pois_to_save = {f"{h.q},{h.r}": data for h, data in self.pois.items()}
        
        map_data = {
            "base_image_path": self.base_image_path,
            "hex_size": self.hex_layout.size,
            "hex_border_color": self.hex_border_color,
            "hexes": [[h.q, h.r] for h in self.grid_hexes],
            "pois": pois_to_save
        }
        try:
            with open(file_path, 'w') as f: json.dump(map_data, f, indent=2)
            messagebox.showinfo("Salvataggio Completato", "Mappa salvata con successo.")
        except Exception as e:
            messagebox.showerror("Errore di Salvataggio", f"Impossibile salvare la mappa: {e}")
            
    def _add_hex_at(self, x, y):
        """Aggiunge un esagono nella posizione del mouse."""
        if not self.hex_layout:
            messagebox.showwarning("Scala non impostata", "Prima scegli un tipo di mappa dal menu in alto.")
            return

        target_hex = self.hex_layout.pixel_to_hex((x, y))
        
        # Aggiungi l'esagono solo se non esiste già
        if target_hex not in self.grid_hexes:
            self.grid_hexes.add(target_hex)
            self._draw_single_hex(target_hex)

    def _delete_hex_at(self, x, y):
        """Cancella un esagono nella posizione del mouse."""
        if not self.hex_layout: return

        target_hex = self.hex_layout.pixel_to_hex((x, y))
        
        # Cancella l'esagono solo se esiste
        if target_hex in self.grid_hexes:
            # Se l'esagono è un POI, rimuovilo prima dai dati
            if target_hex in self.pois:
                del self.pois[target_hex]
            
            canvas_id = self.hex_to_canvas_id.pop(target_hex, None)
            if canvas_id:
                self.canvas.delete(canvas_id)
            self.grid_hexes.remove(target_hex)

    # --- Il resto delle funzioni rimane quasi invariato ---
    def _pan_start(self, event): self.canvas.scan_mark(event.x, event.y)
    def _pan_move(self, event): self.canvas.scan_dragto(event.x, event.y, gain=1)
    def choose_hex_color(self):
        color_code = colorchooser.askcolor(title="Scegli un colore")
        if color_code and color_code[1]: self.hex_border_color = color_code[1]; self._update_grid_color()
    def _update_grid_color(self):
        for hex_id in self.hex_to_canvas_id.values(): self.canvas.itemconfig(hex_id, outline=self.hex_border_color)
    def on_canvas_left_click(self, event):
        canvas_x = self.canvas.canvasx(event.x); canvas_y = self.canvas.canvasy(event.y)
        if self.add_poi_mode: self._add_poi_at(canvas_x, canvas_y)
        else: self._delete_hex_at(canvas_x, canvas_y)
    def on_canvas_right_click(self, event):
        canvas_x = self.canvas.canvasx(event.x); canvas_y = self.canvas.canvasy(event.y)
        self._add_hex_at(canvas_x, canvas_y)
    def on_canvas_motion(self, event):
        self.handle_poi_hover(event) # L'hover dei tooltip usa ancora le coordinate dell'evento
        if self.hex_layout and not self.add_poi_mode:
            canvas_x=self.canvas.canvasx(event.x); canvas_y=self.canvas.canvasy(event.y)
            if self.preview_hex_id: self.canvas.delete(self.preview_hex_id)
            target_hex = self.hex_layout.pixel_to_hex((canvas_x, canvas_y))
            if target_hex not in self.grid_hexes: self.preview_hex_id = self._draw_single_hex(target_hex, is_preview=True)
    def _draw_single_hex(self, h: Hex, is_preview=False):
        corners = self.hex_layout.hex_corners(h)
        style = {"fill": "", "outline": "red", "width": 2} if is_preview else {"fill": "gray50", "stipple": "gray25", "outline": self.hex_border_color, "width": 1}
        canvas_id = self.canvas.create_polygon(corners, **style, tags="hex")
        if not is_preview: self.hex_to_canvas_id[h] = canvas_id
        return canvas_id
    def toggle_add_poi_mode(self):
        self.add_poi_mode=not self.add_poi_mode; 
        style_name = "Primary.TButton" if self.add_poi_mode else "Success.TButton"
        cursor="crosshair" if self.add_poi_mode else ""
        self.add_poi_button.config(style=style_name); self.config(cursor=cursor)
    def on_map_scale_selected(self, event=None):
        selected_scale_name=self.map_scale_var.get()
        new_size=self.MAP_SCALES[selected_scale_name]
        
        if self.grid_hexes:
            if not messagebox.askyesno("Cambio Scala", "Cambiare la scala cancellerà la griglia esistente. Continuare?"):
                return
            self._clear_grid()
            
        self.hex_layout = HexLayout(size=new_size, origin=(new_size, new_size))
        
        # Generazione automatica se c'è un'immagine
        if self.base_image_original:
            if messagebox.askyesno("Generazione Automatica", "Vuoi riempire automaticamente l'intera immagine con gli esagoni?"):
                self.generate_auto_grid()
                return
                
        messagebox.showinfo("Griglia Impostata", f"Scala '{selected_scale_name}' applicata. Usa il tasto destro per aggiungere esagoni manualmente.")
        
    def generate_auto_grid(self):
        if not self.base_image_original or not self.hex_layout: return
        width = self.base_image_original.width
        height = self.base_image_original.height
        
        import math
        hex_w = math.sqrt(3) * self.hex_layout.size
        hex_h = 1.5 * self.hex_layout.size
        est_count = int((width / hex_w) * (height / hex_h))
        
        if est_count > 5000:
            if not messagebox.askyesno("Attenzione", f"Generare circa {est_count} esagoni potrebbe causare rallentamenti. Sei sicuro di voler continuare?"):
                return
                
        step_x = max(1, int(hex_w / 2))
        step_y = max(1, int(hex_h / 2))
        
        for px in range(0, width + step_x, step_x):
            for py in range(0, height + step_y, step_y):
                h = self.hex_layout.pixel_to_hex((px, py))
                if h not in self.grid_hexes:
                    self.grid_hexes.add(h)
                    self._draw_single_hex(h)
                    
        messagebox.showinfo("Griglia Generata", f"Generati {len(self.grid_hexes)} esagoni con successo.")
    def _clear_grid(self):
        self.canvas.delete("hex"); self.grid_hexes.clear(); self.hex_to_canvas_id.clear(); self.pois.clear()
    def on_canvas_leave(self, event):
        if self.preview_hex_id: self.canvas.delete(self.preview_hex_id); self.preview_hex_id = None