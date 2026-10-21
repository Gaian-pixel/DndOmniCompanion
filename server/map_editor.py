# map_editor.py
import tkinter as tk
from common.messagebox import messagebox
from tkinter import simpledialog, filedialog, ttk, colorchooser
import json
import math
import os
from PIL import Image, ImageTk

from common.hex_utils import Hex, HexLayout, SquareLayout
from common.theme import apply_modern_window_style


def clip_polygon_to_rect(poly, xmin, ymin, xmax, ymax):
    """Algoritmo Sutherland-Hodgman per ritagliare un poligono 2D a un rettangolo orientato agli assi."""
    def clip_edge(points, inside, intersect):
        out = []
        if not points:
            return out
        prev = points[-1]
        prev_in = inside(prev)
        for curr in points:
            curr_in = inside(curr)
            if curr_in:
                if not prev_in:
                    out.append(intersect(prev, curr))
                out.append(curr)
            elif prev_in:
                out.append(intersect(prev, curr))
            prev = curr
            prev_in = curr_in
        return out

    def intersect_x(p1, p2, x_boundary):
        dx = p2[0] - p1[0]
        if abs(dx) < 1e-9:
            return (x_boundary, p1[1])
        t = (x_boundary - p1[0]) / dx
        return (x_boundary, p1[1] + t * (p2[1] - p1[1]))

    def intersect_y(p1, p2, y_boundary):
        dy = p2[1] - p1[1]
        if abs(dy) < 1e-9:
            return (p1[0], y_boundary)
        t = (y_boundary - p1[1]) / dy
        return (p1[0] + t * (p2[0] - p1[0]), y_boundary)

    # 1. Sinistra (x >= xmin)
    p = clip_edge(poly, lambda pt: pt[0] >= xmin, lambda p1, p2: intersect_x(p1, p2, xmin))
    # 2. Destra (x <= xmax)
    p = clip_edge(p, lambda pt: pt[0] <= xmax, lambda p1, p2: intersect_x(p1, p2, xmax))
    # 3. Superiore (y >= ymin)
    p = clip_edge(p, lambda pt: pt[1] >= ymin, lambda p1, p2: intersect_y(p1, p2, ymin))
    # 4. Inferiore (y <= ymax)
    p = clip_edge(p, lambda pt: pt[1] <= ymax, lambda p1, p2: intersect_y(p1, p2, ymax))
    return p


class Tooltip:
    def __init__(self, parent):
        self.parent = parent
        self.tip_window = None

    def show(self, event, poi_data):
        if self.tip_window or not poi_data:
            return
        bbox = self.parent.bbox("current")
        if bbox:
            x = bbox[0] + self.parent.winfo_rootx() + 25
            y = bbox[1] + self.parent.winfo_rooty() + 25
        else:
            x = getattr(event, "x_root", 0) + 15
            y = getattr(event, "y_root", 0) + 15
        self.tip_window = tk.Toplevel(self.parent)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        frame = tk.Frame(self.tip_window, bg="#333333", relief="solid", borderwidth=1)
        frame.pack()
        tk.Label(frame, text=poi_data.get('title', ''), font=("", 10, "bold"), bg="#333333", fg="white").pack(pady=(0, 5), padx=5)
        if 'image_tk' in poi_data:
            tk.Label(frame, image=poi_data['image_tk'], bg="#333333").pack(pady=5)
        tk.Label(frame, text=poi_data.get('caption', ''), wraplength=200, bg="#333333", fg="white").pack(padx=5, pady=5)

    def hide(self):
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None


class MapEditorWindow(tk.Toplevel):
    MAP_SCALES = {
        "Mappa del Mondo / Regione": 15,
        "Mappa di Esplorazione (POI)": 35,
        "Mappa di Combattimento": 60
    }
    MAP_SCALE_TYPES = {
        "Mappa del Mondo / Regione": "world",
        "Mappa di Esplorazione (POI)": "exploration",
        "Mappa di Combattimento": "combat"
    }
    POI_COLOR = "#FFD700"  # Oro per i POI

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Editor Mappe Esagonali")
        self.minsize(1200, 800)
        apply_modern_window_style(self)

        self.pois = {}
        self.difficult_terrain = {}
        self.add_terrain_mode = False
        
        self.grid_hexes = set()
        self.hex_to_canvas_id = {}
        self.hex_layout = None
        self.current_hex_size = 35
        self.current_grid_type = "hex"
        self.base_image_path = ""
        self.current_hover_poi = None
        self.add_poi_mode = False
        self.preview_hex_id = None
        self.hex_border_color = "white"

        # Trasformazione Vista: Zoom e Pan unificati
        self.zoom_level = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self._pan_start_x = 0.0
        self._pan_start_y = 0.0

        # Gestione immagine di sfondo
        self.base_image_original = None
        self.base_image_tk = None
        self.bg_canvas_id = None
        self._zoom_timer = None

        self.setup_gui()
        self.tooltip = Tooltip(self.canvas)

    def setup_gui(self):
        main_frame = ttk.Frame(self, padding=(10, 10))
        main_frame.pack(fill=tk.BOTH, expand=True)

        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=5)

        ttk.Button(toolbar, text="Carica Immagine", command=self.load_base_image, style="Info.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Carica Mappa", command=self.load_map_file, style="Info.TButton").pack(side=tk.LEFT, padx=5)

        map_scale_frame = ttk.Frame(toolbar)
        map_scale_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(map_scale_frame, text="Tipo di Mappa:").pack(side=tk.LEFT)
        self.map_scale_var = tk.StringVar()
        map_scale_combo = ttk.Combobox(map_scale_frame, textvariable=self.map_scale_var, values=list(self.MAP_SCALES.keys()), state="readonly")
        map_scale_combo.pack(side=tk.LEFT, padx=5)
        map_scale_combo.bind("<<ComboboxSelected>>", self.on_map_scale_selected)
        ttk.Button(map_scale_frame, text="Colore Griglia", command=self.choose_hex_color).pack(side=tk.LEFT)
        
        grid_type_frame = ttk.Frame(toolbar)
        grid_type_frame.pack(side=tk.LEFT, padx=10)
        ttk.Label(grid_type_frame, text="Griglia:").pack(side=tk.LEFT)
        self.grid_type_var = tk.StringVar(value="hex")
        grid_type_combo = ttk.Combobox(grid_type_frame, textvariable=self.grid_type_var, values=["hex", "square", "none"], state="readonly", width=8)
        grid_type_combo.pack(side=tk.LEFT, padx=5)
        grid_type_combo.bind("<<ComboboxSelected>>", self.on_grid_type_selected)

        self.add_poi_button = ttk.Button(toolbar, text="Aggiungi POI", command=self.toggle_add_poi_mode, style="Success.TButton")
        self.add_poi_button.pack(side=tk.LEFT, padx=5)
        
        terrain_frame = ttk.Frame(toolbar)
        terrain_frame.pack(side=tk.LEFT, padx=5)
        self.add_terrain_button = ttk.Button(terrain_frame, text="🌾 Terreno Difficile", command=self.toggle_add_terrain_mode, style="Secondary.TButton")
        self.add_terrain_button.pack(side=tk.LEFT, padx=2)
        self.terrain_type_var = tk.StringVar(value="Fango")
        self.terrain_type_combo = ttk.Combobox(terrain_frame, textvariable=self.terrain_type_var, values=["Fango", "Ghiaccio", "Rovi", "Macerie", "Palude"], state="readonly", width=8)
        self.terrain_type_combo.pack(side=tk.LEFT, padx=2)

        # Controlli Zoom & Reset
        zoom_frame = ttk.Frame(toolbar)
        zoom_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(zoom_frame, text="🔍+", width=3, command=self.zoom_in).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_frame, text="🔍-", width=3, command=self.zoom_out).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_frame, text="100%", width=5, command=self.reset_view).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_frame, text="⛶ Adatta", command=self.fit_to_window).pack(side=tk.LEFT, padx=1)

        ttk.Button(toolbar, text="Salva Mappa", command=self.save_map, style="Primary.TButton").pack(side=tk.LEFT, padx=5)

        self.canvas = tk.Canvas(main_frame, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Motion>", self.on_canvas_motion)
        self.canvas.bind("<Button-1>", self.on_canvas_left_click)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<Leave>", self.on_canvas_leave)
        self.canvas.bind("<MouseWheel>", self._zoom)
        self.canvas.bind("<Button-4>", self._zoom)
        self.canvas.bind("<Button-5>", self._zoom)
        self.bind("<plus>", lambda e: self.zoom_in(e.x, e.y))
        self.bind("<equal>", lambda e: self.zoom_in(e.x, e.y))
        self.bind("<KP_Add>", lambda e: self.zoom_in(e.x, e.y))
        self.bind("<minus>", lambda e: self.zoom_out(e.x, e.y))
        self.bind("<KP_Subtract>", lambda e: self.zoom_out(e.x, e.y))
        self.canvas.bind("<ButtonPress-2>", self._pan_start)
        self.canvas.bind("<B2-Motion>", self._pan_move)
        self.canvas.bind("<Alt-ButtonPress-1>", self._pan_start)
        self.canvas.bind("<Alt-B1-Motion>", self._pan_move)

    def _create_layout(self, hex_size, grid_type=None):
        if grid_type is None:
            grid_type = self.grid_type_var.get() if hasattr(self, "grid_type_var") else "hex"
        if grid_type == "square":
            return SquareLayout(size=hex_size * 1.5, origin=(0, 0))
        elif grid_type in ("none", "gridless"):
            return SquareLayout(size=hex_size * 1.5, origin=(0, 0))
        else:
            return HexLayout(size=hex_size, origin=(0, 0))

    def screen_to_world(self, sx, sy):
        wx = (sx - self.pan_offset_x) / self.zoom_level
        wy = (sy - self.pan_offset_y) / self.zoom_level
        return wx, wy

    def world_to_screen(self, wx, wy):
        sx = wx * self.zoom_level + self.pan_offset_x
        sy = wy * self.zoom_level + self.pan_offset_y
        return sx, sy

    def _zoom(self, event):
        """Zoom centrato sul cursore del mouse perfettamente allineato tra immagine e griglia."""
        factor = 1.15 if (event.num == 4 or getattr(event, "delta", 0) > 0) else 0.85
        new_zoom = max(0.05, min(10.0, self.zoom_level * factor))
        if abs(new_zoom - self.zoom_level) < 1e-5:
            return
            
        if self.base_image_original:
            if self.base_image_original.width * new_zoom * self.base_image_original.height * new_zoom > 64000000:
                return

        mouse_wx, mouse_wy = self.screen_to_world(event.x, event.y)
        self.zoom_level = new_zoom
        self.pan_offset_x = event.x - mouse_wx * self.zoom_level
        self.pan_offset_y = event.y - mouse_wy * self.zoom_level

        if hasattr(self, "_zoom_timer") and self._zoom_timer:
            self.after_cancel(self._zoom_timer)
            self._zoom_timer = None

        # Redraw immediato e veloce (NEAREST)
        self.redraw(high_res=False)

        # Debounce per rendering ad alta definizione (LANCZOS)
        self._zoom_timer = self.after(250, lambda: self.redraw(high_res=True))

    def zoom_in(self, center_x=None, center_y=None):
        cw = max(self.canvas.winfo_width(), 100)
        ch = max(self.canvas.winfo_height(), 100)
        cx = center_x if center_x is not None else cw / 2
        cy = center_y if center_y is not None else ch / 2
        class FakeEvent:
            pass
        e = FakeEvent()
        e.num = 0
        e.delta = 120
        e.x = cx
        e.y = cy
        self._zoom(e)

    def zoom_out(self, center_x=None, center_y=None):
        cw = max(self.canvas.winfo_width(), 100)
        ch = max(self.canvas.winfo_height(), 100)
        cx = center_x if center_x is not None else cw / 2
        cy = center_y if center_y is not None else ch / 2
        class FakeEvent:
            pass
        e = FakeEvent()
        e.num = 0
        e.delta = -120
        e.x = cx
        e.y = cy
        self._zoom(e)

    def reset_view(self):
        """Ripristina lo zoom al 100% e azzera il pan."""
        self.zoom_level = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.redraw(high_res=True)

    def fit_to_window(self):
        """Adatta l'immagine e la griglia alle dimensioni correnti della finestra."""
        if not self.base_image_original:
            return
        cw = max(self.canvas.winfo_width(), 100)
        ch = max(self.canvas.winfo_height(), 100)
        iw, ih = self.base_image_original.size
        scale_w = cw / iw
        scale_h = ch / ih
        self.zoom_level = min(scale_w, scale_h, 1.0)
        self.pan_offset_x = (cw - iw * self.zoom_level) / 2.0
        self.pan_offset_y = (ch - ih * self.zoom_level) / 2.0
        self.redraw(high_res=True)

    def _pan_start(self, event):
        self._pan_start_x = event.x
        self._pan_start_y = event.y

    def _pan_move(self, event):
        dx = event.x - self._pan_start_x
        dy = event.y - self._pan_start_y
        self.pan_offset_x += dx
        self.pan_offset_y += dy
        self._pan_start_x = event.x
        self._pan_start_y = event.y
        self.canvas.move("all", dx, dy)

    def redraw(self, high_res=False):
        """Ridisegna l'intera scena (sfondo e griglia) garantendo perfetto allineamento."""
        # 1. Immagine di sfondo
        if self.base_image_original:
            orig_w, orig_h = self.base_image_original.size
            new_width = max(1, int(orig_w * self.zoom_level))
            new_height = max(1, int(orig_h * self.zoom_level))
            
            if new_width * new_height < 64000000:
                resample = Image.Resampling.LANCZOS if high_res else Image.Resampling.NEAREST
                resized_img = self.base_image_original.resize((new_width, new_height), resample)
                self.base_image_tk = ImageTk.PhotoImage(resized_img)
                
                if self.bg_canvas_id is None:
                    self.bg_canvas_id = self.canvas.create_image(
                        self.pan_offset_x, self.pan_offset_y,
                        image=self.base_image_tk, anchor="nw", tags="base_image"
                    )
                else:
                    self.canvas.coords(self.bg_canvas_id, self.pan_offset_x, self.pan_offset_y)
                    self.canvas.itemconfig(self.bg_canvas_id, image=self.base_image_tk)
                self.canvas.tag_lower("base_image")
        elif self.bg_canvas_id is not None:
            self.canvas.delete(self.bg_canvas_id)
            self.bg_canvas_id = None
            self.base_image_tk = None

        # 2. Griglia
        self.canvas.delete("hex")
        self.canvas.delete("preview")
        self.hex_to_canvas_id.clear()
        self.preview_hex_id = None
        
        if self.hex_layout:
            for h in self.grid_hexes:
                self._draw_single_hex(h)

    def _draw_single_hex(self, h: Hex, is_preview=False):
        if not self.hex_layout:
            return None
        corners = self.hex_layout.hex_corners(h)
        
        # Se c'è un'immagine di sfondo, ritaglia i vertici esattamente al perimetro dell'immagine [0, W] x [0, H]
        if self.base_image_original:
            w = self.base_image_original.width
            h_img = self.base_image_original.height
            corners = clip_polygon_to_rect(corners, 0, 0, w, h_img)
            if len(corners) < 3:
                return None

        screen_corners = [
            (cx * self.zoom_level + self.pan_offset_x, cy * self.zoom_level + self.pan_offset_y)
            for cx, cy in corners
        ]
        t_style = self.get_terrain_style(h)
        if is_preview:
            style = {"fill": "", "outline": "red", "width": 2}
        elif t_style:
            style = {"fill": t_style["fill"], "stipple": t_style["stipple"], "outline": self.hex_border_color, "width": 1}
        elif h in self.pois:
            style = {"fill": self.POI_COLOR, "stipple": "", "outline": self.hex_border_color, "width": 1}
        else:
            style = {"fill": "gray50", "stipple": "gray25", "outline": self.hex_border_color, "width": 1}
        
        tag = "preview" if is_preview else "hex"
        canvas_id = self.canvas.create_polygon(screen_corners, **style, tags=tag)
        if not is_preview:
            self.hex_to_canvas_id[h] = canvas_id
        return canvas_id

    def get_terrain_style(self, h):
        if h in self.difficult_terrain:
            t_type = self.difficult_terrain[h].lower()
            TERRAIN_COLORS = {
                "fango": ("#78350F", "gray25"),
                "ghiaccio": ("#0284C7", "gray25"),
                "rovi": ("#166534", "gray50"),
                "macerie": ("#475569", "gray50"),
                "palude": ("#0F766E", "gray25"),
            }
            fill_c, stipple_p = TERRAIN_COLORS.get(t_type, ("#B45309", "gray25"))
            return {"fill": fill_c, "stipple": stipple_p}
        return None

    def choose_hex_color(self):
        color_code = colorchooser.askcolor(title="Scegli un colore", initialcolor=self.hex_border_color)
        if color_code and color_code[1]:
            self.hex_border_color = color_code[1]
            self._update_grid_color()

    def _update_grid_color(self):
        for hex_id in self.hex_to_canvas_id.values():
            self.canvas.itemconfig(hex_id, outline=self.hex_border_color)

    def load_base_image(self):
        """Carica un'immagine di sfondo e reimposta la vista."""
        maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
        file_path = filedialog.askopenfilename(initialdir=maps_dir, filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if not file_path:
            return
        self.base_image_path = file_path
        self.base_image_original = Image.open(file_path)
        
        self.zoom_level = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.redraw(high_res=True)
        
        # Generazione automatica se c'è già una scala impostata
        if self.hex_layout and not self.grid_hexes:
            grid_type = self.grid_type_var.get() if hasattr(self, "grid_type_var") else "hex"
            if messagebox.askyesno("Generazione Automatica", f"Vuoi riempire automaticamente l'immagine appena caricata con la griglia {grid_type}?", parent=self):
                self.generate_auto_grid(silent=False)

    def load_map_file(self):
        """Carica una mappa esistente in formato JSON nell'editor."""
        maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
        file_path = filedialog.askopenfilename(initialdir=maps_dir, filetypes=[("Mappe D&D", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._clear_grid()
            hex_size = data.get("hex_size", 60)
            self.current_hex_size = hex_size
            grid_type = data.get("grid_type", "hex")
            self.current_grid_type = grid_type
            if hasattr(self, "grid_type_var"):
                self.grid_type_var.set(grid_type)
            
            # Scala della mappa
            map_scale_type = data.get("map_scale_type", "combat")
            for name, scale_t in self.MAP_SCALE_TYPES.items():
                if scale_t == map_scale_type:
                    self.map_scale_var.set(name)
                    break

            self.hex_layout = self._create_layout(hex_size, grid_type)
            if "hex_border_color" in data:
                self.hex_border_color = data["hex_border_color"]
            
            pois_data = data.get("pois", {})
            for k, p_data in pois_data.items():
                parts = k.split(",")
                self.pois[Hex(int(parts[0]), int(parts[1]))] = p_data
            
            diff_data = data.get("difficult_terrain", {})
            if isinstance(diff_data, dict):
                for k, t_val in diff_data.items():
                    parts = k.split(",")
                    t_str = t_val if isinstance(t_val, str) else t_val.get("type", "fango")
                    self.difficult_terrain[Hex(int(parts[0]), int(parts[1]))] = t_str
            
            for pos in data.get("hexes", []):
                h = Hex(pos[0], pos[1])
                self.grid_hexes.add(h)

            base_img = data.get("base_image_path", "")
            if base_img and os.path.exists(base_img):
                self.base_image_path = base_img
                self.base_image_original = Image.open(base_img)
            elif base_img:
                alt_path = os.path.join(maps_dir, os.path.basename(base_img))
                if os.path.exists(alt_path):
                    self.base_image_path = alt_path
                    self.base_image_original = Image.open(alt_path)

            self.zoom_level = 1.0
            self.pan_offset_x = 0.0
            self.pan_offset_y = 0.0
            self.redraw(high_res=True)
            messagebox.showinfo("Mappa Caricata", f"Caricata mappa con {len(self.grid_hexes)} celle.", parent=self)
        except Exception as e:
            messagebox.showerror("Errore di Caricamento", f"Impossibile caricare la mappa: {e}", parent=self)

    def save_map(self):
        """Salva i dati della mappa (celle, POI, terreni difficili, immagine, scala) in formato JSON."""
        if not self.hex_layout:
            messagebox.showerror("Errore", "Non puoi salvare una mappa senza una scala.", parent=self)
            return
        maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
        file_path = filedialog.asksaveasfilename(initialdir=maps_dir, defaultextension=".json", filetypes=[("Mappe D&D", "*.json")])
        if not file_path:
            return
        
        pois_to_save = {f"{h.q},{h.r}": data for h, data in self.pois.items()}
        scale_type = self.MAP_SCALE_TYPES.get(self.map_scale_var.get(), "combat")
        diff_terrain_to_save = {f"{h.q},{h.r}": t_type for h, t_type in self.difficult_terrain.items()}
        
        hex_size = getattr(self, "current_hex_size", 60)
        grid_type = self.grid_type_var.get() if hasattr(self, "grid_type_var") else "hex"
        
        map_data = {
            "base_image_path": self.base_image_path,
            "hex_size": hex_size,
            "grid_type": grid_type,
            "map_scale_type": scale_type,
            "hex_border_color": self.hex_border_color,
            "hexes": [[h.q, h.r] for h in self.grid_hexes],
            "pois": pois_to_save,
            "difficult_terrain": diff_terrain_to_save
        }
        try:
            with open(file_path, 'w', encoding="utf-8") as f:
                json.dump(map_data, f, indent=2)
            messagebox.showinfo("Salvataggio Completato", "Mappa salvata con successo.", parent=self)
        except Exception as e:
            messagebox.showerror("Errore di Salvataggio", f"Impossibile salvare la mappa: {e}", parent=self)

    def _add_hex_at(self, wx, wy):
        """Aggiunge un esagono o quadrato nella posizione del mondo specificata."""
        if not self.hex_layout:
            messagebox.showwarning("Scala non impostata", "Prima scegli un tipo di mappa dal menu in alto.", parent=self)
            return

        if self.base_image_original:
            if not (0 <= wx <= self.base_image_original.width and 0 <= wy <= self.base_image_original.height):
                return

        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex not in self.grid_hexes:
            self.grid_hexes.add(target_hex)
            self._draw_single_hex(target_hex)

    def _delete_hex_at(self, wx, wy):
        """Cancella una cella nella posizione del mondo specificata."""
        if not self.hex_layout:
            return

        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex in self.grid_hexes:
            if target_hex in self.pois:
                del self.pois[target_hex]
            if target_hex in self.difficult_terrain:
                del self.difficult_terrain[target_hex]
            canvas_id = self.hex_to_canvas_id.pop(target_hex, None)
            if canvas_id:
                self.canvas.delete(canvas_id)
            self.grid_hexes.remove(target_hex)

    def _add_poi_at(self, wx, wy):
        """Aggiunge o modifica un POI nella cella selezionata."""
        if not self.hex_layout:
            return
        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex not in self.grid_hexes:
            messagebox.showwarning("Azione non valida", "Puoi aggiungere un Punto di Interesse solo su un esagono esistente.", parent=self)
            return

        title = simpledialog.askstring("Nuovo POI", "Inserisci il titolo:", parent=self)
        if not title:
            return
        caption = simpledialog.askstring("Nuovo POI", "Inserisci la didascalia:", parent=self)
        self.pois[target_hex] = {"title": title, "caption": caption or ""}
        hex_id = self.hex_to_canvas_id.get(target_hex)
        if hex_id:
            self.canvas.itemconfig(hex_id, fill=self.POI_COLOR, stipple="")
            self.canvas.addtag_withtag("poi", hex_id)
        self.toggle_add_poi_mode()

    def _toggle_terrain_at(self, wx, wy):
        """Imposta o rimuove terreno difficile nella cella selezionata."""
        if not self.hex_layout:
            return
        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex not in self.grid_hexes:
            messagebox.showwarning("Azione non valida", "Puoi impostare terreno difficile solo su esagoni esistenti.", parent=self)
            return

        t_type = self.terrain_type_var.get().lower()
        if target_hex in self.difficult_terrain and self.difficult_terrain[target_hex] == t_type:
            del self.difficult_terrain[target_hex]
            hex_id = self.hex_to_canvas_id.get(target_hex)
            if hex_id:
                self.canvas.itemconfig(hex_id, fill="gray50", stipple="gray25")
        else:
            self.difficult_terrain[target_hex] = t_type
            t_style = self.get_terrain_style(target_hex)
            hex_id = self.hex_to_canvas_id.get(target_hex)
            if hex_id and t_style:
                self.canvas.itemconfig(hex_id, fill=t_style["fill"], stipple=t_style["stipple"])

    def on_canvas_left_click(self, event):
        wx, wy = self.screen_to_world(event.x, event.y)
        if self.add_poi_mode:
            self._add_poi_at(wx, wy)
        elif getattr(self, "add_terrain_mode", False):
            self._toggle_terrain_at(wx, wy)
        else:
            self._delete_hex_at(wx, wy)

    def on_canvas_right_click(self, event):
        wx, wy = self.screen_to_world(event.x, event.y)
        self._add_hex_at(wx, wy)

    def on_canvas_motion(self, event):
        self.handle_poi_hover(event)
        if self.hex_layout and not self.add_poi_mode and not getattr(self, "add_terrain_mode", False):
            if self.preview_hex_id:
                self.canvas.delete(self.preview_hex_id)
                self.preview_hex_id = None
            wx, wy = self.screen_to_world(event.x, event.y)
            if self.base_image_original:
                if not (0 <= wx <= self.base_image_original.width and 0 <= wy <= self.base_image_original.height):
                    return
            target_hex = self.hex_layout.pixel_to_hex((wx, wy))
            if target_hex not in self.grid_hexes:
                self.preview_hex_id = self._draw_single_hex(target_hex, is_preview=True)

    def on_canvas_leave(self, event):
        if self.preview_hex_id:
            self.canvas.delete(self.preview_hex_id)
            self.preview_hex_id = None
        self.tooltip.hide()
        self.current_hover_poi = None

    def handle_poi_hover(self, event):
        if not self.hex_layout:
            return
        wx, wy = self.screen_to_world(event.x, event.y)
        hovered_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if hovered_hex in self.pois:
            if self.current_hover_poi != hovered_hex:
                self.current_hover_poi = hovered_hex
                self.tooltip.hide()
                self.tooltip.show(event, self.pois[hovered_hex])
        else:
            self.current_hover_poi = None
            self.tooltip.hide()

    def toggle_add_poi_mode(self):
        self.add_poi_mode = not self.add_poi_mode
        if self.add_poi_mode and getattr(self, "add_terrain_mode", False):
            self.toggle_add_terrain_mode()
        style_name = "Primary.TButton" if self.add_poi_mode else "Success.TButton"
        cursor = "crosshair" if self.add_poi_mode else ""
        self.add_poi_button.config(style=style_name)
        self.config(cursor=cursor)

    def toggle_add_terrain_mode(self):
        self.add_terrain_mode = not getattr(self, "add_terrain_mode", False)
        if self.add_terrain_mode and getattr(self, "add_poi_mode", False):
            self.toggle_add_poi_mode()
        style_name = "Primary.TButton" if self.add_terrain_mode else "Secondary.TButton"
        cursor = "crosshair" if self.add_terrain_mode else ""
        self.add_terrain_button.config(style=style_name)
        self.config(cursor=cursor)

    def on_map_scale_selected(self, event=None):
        selected_scale_name = self.map_scale_var.get()
        new_size = self.MAP_SCALES[selected_scale_name]
        self.current_hex_size = new_size
        
        if self.grid_hexes:
            if not messagebox.askyesno("Cambio Scala", "Cambiare la scala cancellerà la griglia esistente. Continuare?", parent=self):
                return
            self._clear_grid()
            
        grid_type = self.grid_type_var.get() if hasattr(self, "grid_type_var") else "hex"
        self.hex_layout = self._create_layout(new_size, grid_type)
        
        if self.base_image_original:
            if messagebox.askyesno("Generazione Automatica", f"Vuoi riempire automaticamente l'intera immagine con la griglia {grid_type}?", parent=self):
                self.generate_auto_grid(silent=False)
                return
                
        messagebox.showinfo("Griglia Impostata", f"Scala '{selected_scale_name}' applicata. Usa il tasto destro per aggiungere celle manualmente.", parent=self)

    def on_grid_type_selected(self, event=None):
        """Passaggio pulito e istantaneo tra tipi di griglia senza popup bloccanti né freeze da grab."""
        new_grid_type = self.grid_type_var.get()
        old_grid_type = getattr(self, "current_grid_type", "hex")
        if old_grid_type == new_grid_type:
            return
            
        self.current_grid_type = new_grid_type
        if hasattr(self, "current_hex_size") and self.current_hex_size:
            self.hex_layout = self._create_layout(self.current_hex_size, new_grid_type)
            if self.base_image_original:
                self.generate_auto_grid(silent=True)
            else:
                self._clear_grid()
                self.redraw(high_res=True)

    def generate_auto_grid(self, silent=False):
        """Genera automaticamente le celle su tutta l'estensione dell'immagine caricata combaciando perfettamente col perimetro."""
        if not self.base_image_original or not self.hex_layout:
            return
        width = self.base_image_original.width
        height = self.base_image_original.height
        
        grid_type = self.grid_type_var.get() if hasattr(self, "grid_type_var") else "hex"
        
        if grid_type == "square":
            cell_size = self.hex_layout.size
            cols = max(1, int(math.ceil(width / cell_size)))
            rows = max(1, int(math.ceil(height / cell_size)))
            est_count = cols * rows
        else:
            hex_size = self.current_hex_size
            hex_w = math.sqrt(3) * hex_size
            hex_h = 1.5 * hex_size
            est_count = int((width / hex_w) * (height / hex_h))
            
        if not silent and est_count > 5000:
            if not messagebox.askyesno("Attenzione", f"Generare circa {est_count} celle potrebbe richiedere qualche secondo. Continuare?", parent=self):
                return

        self._clear_grid()
        
        if grid_type == "square":
            cell_size = self.hex_layout.size
            cols = max(1, int(math.ceil(width / cell_size)))
            rows = max(1, int(math.ceil(height / cell_size)))
            for q in range(cols):
                for r in range(rows):
                    self.grid_hexes.add(Hex(q, r))
        else:
            hex_size = self.current_hex_size
            hex_w = math.sqrt(3) * hex_size
            hex_h = 1.5 * hex_size
            step_x = max(1, int(hex_w / 2))
            step_y = max(1, int(hex_h / 2))
            
            for px in range(0, width + step_x, step_x):
                for py in range(0, height + step_y, step_y):
                    h = self.hex_layout.pixel_to_hex((px, py))
                    if h not in self.grid_hexes:
                        corners = self.hex_layout.hex_corners(h)
                        clipped = clip_polygon_to_rect(corners, 0, 0, width, height)
                        if len(clipped) >= 3:
                            self.grid_hexes.add(h)

        self.redraw(high_res=True)
        if not silent:
            messagebox.showinfo("Griglia Generata", f"Generate {len(self.grid_hexes)} celle con successo.", parent=self)

    def _clear_grid(self):
        self.canvas.delete("hex")
        self.canvas.delete("preview")
        self.grid_hexes.clear()
        self.hex_to_canvas_id.clear()
        self.pois.clear()
        self.difficult_terrain.clear()
        self.preview_hex_id = None
