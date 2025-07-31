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

class MapEditorWindow(tk.Toplevel):
    MAP_SCALES={"Mappa del Mondo / Regione": 15, "Mappa di Esplorazione (POI)": 35, "Mappa di Combattimento": 60}
    POI_COLOR = "#FFD700" # Oro per i POI

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Editor Mappe Esagonali")
        self.geometry("1200x800")
        self.configure(bg="#2b2b2b")

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
        # ... (Questa funzione è quasi identica, le modifiche sono gestite in altre funzioni)
        main_frame=tk.Frame(self, bg="#2b2b2b", padx=10, pady=10); main_frame.pack(fill=tk.BOTH, expand=True)
        toolbar=tk.Frame(main_frame, bg="#2b2b2b"); toolbar.pack(fill=tk.X, pady=5)
        tk.Button(toolbar, text="Carica Immagine", command=self.load_base_image, bg="#007bff", fg="white", activebackground="#0056b3").pack(side=tk.LEFT, padx=5)
        map_scale_frame=tk.Frame(toolbar, bg="#2b2b2b"); map_scale_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(map_scale_frame, text="Tipo di Mappa:", bg="#2b2b2b", fg="white").pack(side=tk.LEFT)
        self.map_scale_var=tk.StringVar()
        map_scale_combo=ttk.Combobox(map_scale_frame, textvariable=self.map_scale_var, values=list(self.MAP_SCALES.keys()), state="readonly")
        map_scale_combo.pack(side=tk.LEFT, padx=5); map_scale_combo.bind("<<ComboboxSelected>>", self.on_map_scale_selected)
        tk.Button(map_scale_frame, text="Colore Griglia", command=self.choose_hex_color, bg="#ffc107", fg="black", activebackground="#e0a800").pack(side=tk.LEFT)
        self.add_poi_button=tk.Button(toolbar, text="Aggiungi POI", command=self.toggle_add_poi_mode, bg="#28a745", fg="white", activebackground="#218838")
        self.add_poi_button.pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Salva Mappa", command=self.save_map, bg="#17a2b8", fg="white", activebackground="#117a8b").pack(side=tk.LEFT, padx=5)
        self.canvas=tk.Canvas(main_frame, bg="#2b2b2b", highlightthickness=0); self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Motion>", self.on_canvas_motion); self.canvas.bind("<Button-1>", self.on_canvas_left_click); self.canvas.bind("<Button-3>", self.on_canvas_right_click); self.canvas.bind("<Leave>", self.on_canvas_leave)
        self.canvas.bind("<MouseWheel>", self._zoom); self.canvas.bind("<Button-4>", self._zoom); self.canvas.bind("<Button-5>", self._zoom)
        self.canvas.bind("<ButtonPress-2>", self._pan_start); self.canvas.bind("<B2-Motion>", self._pan_move)

    def _zoom(self, event):
        """ ### MODIFICATO: Ora gestisce anche lo zoom dell'immagine di sfondo ### """
        factor = 1.1 if (event.num == 4 or event.delta > 0) else 0.9
        
        # Applica lo zoom a griglia e POI
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        self.canvas.scale("all", canvas_x, canvas_y, factor, factor)
        
        # Applica lo zoom all'immagine di sfondo manualmente
        if self.base_image_original:
            self.zoom_level *= factor
            new_width = int(self.base_image_original.width * self.zoom_level)
            new_height = int(self.base_image_original.height * self.zoom_level)
            
            # Evita errori se l'immagine diventa troppo piccola
            if new_width > 0 and new_height > 0:
                resized_img = self.base_image_original.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.base_image_tk = ImageTk.PhotoImage(resized_img)
                self.canvas.itemconfig(self.bg_canvas_id, image=self.base_image_tk)
        else:
             self.zoom_level *= factor

    def load_base_image(self):
        """ ### MODIFICATO: Memorizza l'immagine originale per lo zoom ### """
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if not file_path: return
        self.base_image_path = file_path
        
        self.base_image_original = Image.open(file_path) # Salva l'originale
        self.base_image_tk = ImageTk.PhotoImage(self.base_image_original)
        
        if self.bg_canvas_id:
            self.canvas.itemconfig(self.bg_canvas_id, image=self.base_image_tk)
        else:
            self.bg_canvas_id = self.canvas.create_image(0, 0, image=self.base_image_tk, anchor="nw", tags="base_image")
        
        self.canvas.tag_lower("base_image")

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
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Mappe D&D", "*.json")])
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
            messagebox.showinfo("Salvataggio Completato", f"Mappa salvata con successo.")
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
        color_code = colorchooser.askcolor(title="Scegli un colore");
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
        self.add_poi_mode=not self.add_poi_mode; bg_color="#dc3545" if self.add_poi_mode else "#28a745"; cursor="crosshair" if self.add_poi_mode else ""
        self.add_poi_button.config(bg=bg_color); self.config(cursor=cursor)
    def on_map_scale_selected(self, event=None):
        selected_scale_name=self.map_scale_var.get(); new_size=self.MAP_SCALES[selected_scale_name]
        if self.grid_hexes and messagebox.askyesno("Cambio Scala", "Cambiare la scala cancellerà la griglia esistente. Continuare?"): self._clear_grid()
        elif not self.grid_hexes: self._clear_grid()
        else: return
        self.hex_layout=HexLayout(size=new_size, origin=(new_size, new_size)); messagebox.showinfo("Griglia Impostata", f"Scala '{selected_scale_name}' applicata.")
    def _clear_grid(self):
        self.canvas.delete("hex"); self.grid_hexes.clear(); self.hex_to_canvas_id.clear(); self.pois.clear()
    def _delete_hex_at(self, x, y):
        if not self.hex_layout: return
        target_hex = self.hex_layout.pixel_to_hex((x, y))
        if target_hex in self.grid_hexes:
            # Se l'esagono è un POI, rimuovilo prima dai dati
            if target_hex in self.pois:
                del self.pois[target_hex]
            canvas_id = self.hex_to_canvas_id.pop(target_hex, None)
            if canvas_id: self.canvas.delete(canvas_id)
            self.grid_hexes.remove(target_hex)
    def on_canvas_leave(self, event):
        if self.preview_hex_id: self.canvas.delete(self.preview_hex_id); self.preview_hex_id = None