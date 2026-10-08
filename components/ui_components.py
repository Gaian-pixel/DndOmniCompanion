# ui_components.py
import tkinter as tk
import base64
from io import BytesIO
from PIL import Image, ImageTk
from common.hex_utils import Hex, HexLayout

class HexMapCanvas(tk.Canvas):
    """Un widget Canvas riutilizzabile per visualizzare e interagire con una mappa esagonale."""
    
    def __init__(self, parent, **kwargs):
        bg_color = kwargs.pop('bg', "#1e1e1e")
        super().__init__(parent, bg=bg_color, highlightthickness=0, **kwargs)

        self.zoom_level = 1.0
        self.pan_offset_x, self.pan_offset_y = 0, 0
        self._pan_start_x, self._pan_start_y = 0, 0
        
        self.hex_layout = None
        self.map_background_original = None
        self.map_background_tk = None
        self._last_b64 = None
        self._last_zoom = None
        
        self.on_hex_click_callback = None
        self.on_ping_callback = None
        
        self._ruler_start_hex = None
        self._ruler_line_id = None
        self._ruler_text_id = None

        self.bind("<MouseWheel>", self._zoom)
        self.bind("<Button-4>", self._zoom)
        self.bind("<Button-5>", self._zoom)
        self.bind("<ButtonPress-2>", self._pan_start)
        self.bind("<B2-Motion>", self._pan_move)
        self.bind("<ButtonRelease-2>", self._on_ping_click_b2)
        self.bind("<Button-1>", self._on_canvas_click)
        self.bind("<B1-Motion>", self._on_canvas_drag)
        self.bind("<Shift-Button-1>", self._on_ping_click)
        self.bind("<Button-3>", self._on_ruler_start)
        self.bind("<B3-Motion>", self._on_ruler_drag)
        self.bind("<ButtonRelease-3>", self._on_ruler_end)
        self.bind("<Shift-Button-3>", self._on_wall_toggle)

        self.bind("<Control-Button-1>", self._on_draw_start)
        self.bind("<Control-B1-Motion>", self._on_draw_move)
        self.bind("<Control-ButtonRelease-1>", self._on_draw_end)

        self.drawn_lines = []

    def set_on_click_callback(self, func):
        self.on_hex_click_callback = func

    def set_on_ping_callback(self, func):
        self.on_ping_callback = func

    def set_on_wall_toggle_callback(self, func):
        self.on_wall_toggle_callback = func

    def set_on_draw_callback(self, func):
        self.on_draw_callback = func

    def draw_remote_line(self, points, color):
        self.drawn_lines.append({"points": points, "color": color})
        self.redraw()

    def _on_draw_start(self, event):
        self._current_drawing = [(event.x, event.y)]
        
    def _on_draw_move(self, event):
        if hasattr(self, '_current_drawing'):
            self._current_drawing.append((event.x, event.y))
            if len(self._current_drawing) >= 2:
                p1 = self._current_drawing[-2]
                p2 = self._current_drawing[-1]
                self.create_line(p1[0], p1[1], p2[0], p2[1], fill="red", width=2, tags="temp_draw")

    def _on_draw_end(self, event):
        if hasattr(self, '_current_drawing'):
            if len(self._current_drawing) > 1:
                world_points = [((px - self.pan_offset_x) / self.zoom_level, (py - self.pan_offset_y) / self.zoom_level) for px, py in self._current_drawing]
                if getattr(self, 'on_draw_callback', None):
                    self.on_draw_callback(world_points, "red")
            self.delete("temp_draw")
            del self._current_drawing

    def _zoom(self, event):
        factor = 1.1 if (event.num == 4 or event.delta > 0) else 0.9
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        self.zoom_level *= factor
        new_screen_x = world_x * self.zoom_level
        new_screen_y = world_y * self.zoom_level
        self.pan_offset_x += event.x - new_screen_x
        self.pan_offset_y += event.y - new_screen_y
        self.redraw()

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
        self.move("all", dx, dy)

    def _on_canvas_click(self, event):
        if not self.hex_layout or not self.on_hex_click_callback: return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        clicked_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
        self._last_clicked_hex = clicked_hex
        self.on_hex_click_callback(clicked_hex)

    def _on_canvas_drag(self, event):
        if not self.hex_layout or not self.on_hex_click_callback: return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        hovered_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
        if not hasattr(self, '_last_clicked_hex') or self._last_clicked_hex != hovered_hex:
            self._last_clicked_hex = hovered_hex
            self.on_hex_click_callback(hovered_hex)

    def _on_ping_click(self, event):
        if not self.hex_layout or not self.on_ping_callback: return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        clicked_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
        self.on_ping_callback(clicked_hex)

    def _on_ping_click_b2(self, event):
        # Only ping if we didn't pan much
        dx = abs(event.x - self._pan_start_x)
        dy = abs(event.y - self._pan_start_y)
        if dx < 5 and dy < 5:
            self._on_ping_click(event)

    def _on_ruler_start(self, event):
        if not self.hex_layout: return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        self._ruler_start_hex = self.hex_layout.pixel_to_hex((world_x, world_y))

    def _on_ruler_drag(self, event):
        if not self.hex_layout or not self._ruler_start_hex: return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        current_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
        
        # Calculate distance
        from common.hex_utils import hex_distance
        dist_hexes = hex_distance(self._ruler_start_hex, current_hex)
        dist_ft = dist_hexes * 5

        # Draw line and text
        if self._ruler_line_id:
            self.delete(self._ruler_line_id)
        if self._ruler_text_id:
            self.delete(self._ruler_text_id)

        start_x, start_y = self.hex_layout.hex_to_pixel(self._ruler_start_hex)
        end_x, end_y = self.hex_layout.hex_to_pixel(current_hex)
        
        screen_start_x = start_x * self.zoom_level + self.pan_offset_x
        screen_start_y = start_y * self.zoom_level + self.pan_offset_y
        screen_end_x = end_x * self.zoom_level + self.pan_offset_x
        screen_end_y = end_y * self.zoom_level + self.pan_offset_y

        self._ruler_line_id = self.create_line(screen_start_x, screen_start_y, screen_end_x, screen_end_y, 
                                               fill="white", dash=(4, 4), width=2, arrow=tk.LAST)
        
        mid_x = (screen_start_x + screen_end_x) / 2
        mid_y = (screen_start_y + screen_end_y) / 2
        self._ruler_text_id = self.create_text(mid_x, mid_y, text=f"{dist_ft} ft.", 
                                               fill="white", font=("Arial", 12, "bold"))
        
        # Add a dark background to text for visibility
        bbox = self.bbox(self._ruler_text_id)
        if bbox:
            if hasattr(self, '_ruler_text_bg_id') and self._ruler_text_bg_id:
                self.delete(self._ruler_text_bg_id)
            self._ruler_text_bg_id = self.create_rectangle(bbox, fill="black", outline="black")
            self.tag_lower(self._ruler_text_bg_id, self._ruler_text_id)

    def _on_ruler_end(self, event):
        if self._ruler_line_id:
            self.delete(self._ruler_line_id)
            self._ruler_line_id = None
        if self._ruler_text_id:
            self.delete(self._ruler_text_id)
            self._ruler_text_id = None
        if hasattr(self, '_ruler_text_bg_id') and self._ruler_text_bg_id:
            self.delete(self._ruler_text_bg_id)
            self._ruler_text_bg_id = None
        self._ruler_start_hex = None

    def _on_wall_toggle(self, event):
        if not self.hex_layout or not getattr(self, 'on_wall_toggle_callback', None): return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        clicked_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
        self.on_wall_toggle_callback(clicked_hex.q, clicked_hex.r)

    def show_ping(self, q, r, color="yellow"):
        if not self.hex_layout: return
        hex_obj = Hex(q, r)
        center_x, center_y = self.hex_layout.hex_to_pixel(hex_obj)
        screen_x = center_x * self.zoom_level + self.pan_offset_x
        screen_y = center_y * self.zoom_level + self.pan_offset_y
        
        radius = self.hex_layout.size * self.zoom_level
        ping_id = self.create_oval(screen_x - radius, screen_y - radius, 
                                   screen_x + radius, screen_y + radius, 
                                   outline=color, width=4)
        
        # Remove after 2 seconds
        self.after(2000, lambda: self.delete(ping_id))

    def update_data(self, map_data, players_data, player_name="", turn_player_name="", aoes_data=None):
        """Salva i dati necessari per il ridisegno."""
        self.map_data = map_data
        self.players_data = players_data
        self.player_name = player_name
        self.turn_player_name = turn_player_name
        self.aoes_data = aoes_data or []
        self.redraw()

    def redraw(self):
        self.delete("all")
        if not getattr(self, 'map_data', None):
            self.create_text(self.winfo_width()/2, self.winfo_height()/2, 
                             text="Nessuna mappa caricata.", fill="grey", font=("", 12))
            return

        hex_size = self.map_data.get("hex_size", 30)
        self.hex_layout = HexLayout(size=hex_size, origin=(0, 0))
        
        # Gestione immagine di sfondo ottimizzata con caching
        image_data_b64 = self.map_data.get("bg_image_data")
        if image_data_b64:
            if self._last_b64 != image_data_b64:
                try:
                    image_bytes = base64.b64decode(image_data_b64)
                    self.map_background_original = Image.open(BytesIO(image_bytes))
                    self._last_b64 = image_data_b64
                    self._last_zoom = None  # Forza il ridimensionamento
                except Exception as e:
                    self.map_background_original = None
                    print(f"Errore decodifica immagine: {e}")
        else:
            self.map_background_original = None
            self._last_b64 = None
        
        if getattr(self, 'map_background_original', None):
            new_width = int(self.map_background_original.width * self.zoom_level)
            new_height = int(self.map_background_original.height * self.zoom_level)
            if new_width > 0 and new_height > 0:
                if self._last_zoom != self.zoom_level:
                    # Usa un resampling più veloce (NEAREST o BILINEAR) invece di LANCZOS per prestazioni real-time
                    resized_img = self.map_background_original.resize((new_width, new_height), Image.Resampling.BILINEAR)
                    self.map_background_tk = ImageTk.PhotoImage(resized_img)
                    self._last_zoom = self.zoom_level
                self.create_image(self.pan_offset_x, self.pan_offset_y, image=self.map_background_tk, anchor="nw")

        pois_data = {Hex(int(k.split(',')[0]), int(k.split(',')[1])): v for k, v in self.map_data.get("pois", {}).items()}
        border_color = self.map_data.get("hex_border_color", "white")
        
        fow_enabled = self.map_data.get("fow_enabled", False)
        is_dm = not bool(self.player_name)
        draft_key = "fow_draft" if ("fow_draft" in self.map_data and is_dm) else "fow_revealed"
        fow_revealed = {Hex(h[0], h[1]) for h in self.map_data.get(draft_key, [])}
        walls_data = self.map_data.get("walls", [])
        
        for q, r in self.map_data.get("hexes", []):
            current_hex = Hex(q, r)
            scaled_corners = [(px * self.zoom_level + self.pan_offset_x, py * self.zoom_level + self.pan_offset_y) 
                              for px, py in self.hex_layout.hex_corners(current_hex)]
            
            fill_color = "#FFD700" if current_hex in pois_data else ""
            stipple_pattern = ""
            
            # Logica Fog of War e Muri
            if [q, r] in walls_data:
                fill_color = "#101010"
                stipple_pattern = ""
            elif fow_enabled and current_hex not in fow_revealed:
                if is_dm:
                    fill_color = "gray25"
                    stipple_pattern = "gray50"
                else:
                    fill_color = "black"
                    stipple_pattern = ""
            
            self.create_polygon(scaled_corners, fill=fill_color, outline=border_color, width=max(1, 1/self.zoom_level), stipple=stipple_pattern)
        
        
        # Disegna le aree d'effetto (AoE)
        if getattr(self, "aoes_data", None):
            from common.hex_utils import get_sphere_hexes, get_cone_hexes, get_line_hexes
            for aoe in self.aoes_data:
                origin = Hex(*aoe["origin"])
                color = aoe.get("color", "red")
                aoe_type = aoe.get("type", "sfera")
                
                if aoe_type == "sfera" or aoe_type == "cubo":
                    hexes = get_sphere_hexes(origin, aoe["size"])
                elif aoe_type == "cono":
                    target = Hex(*aoe.get("target", aoe["origin"]))
                    hexes = get_cone_hexes(origin, target, aoe["size"])
                elif aoe_type == "linea":
                    target = Hex(*aoe.get("target", aoe["origin"]))
                    hexes = get_line_hexes(origin, target)
                else:
                    hexes = []
                
                for h in hexes:
                    if fow_enabled and not is_dm and h not in fow_revealed:
                        continue
                    scaled_corners = [(px * self.zoom_level + self.pan_offset_x, py * self.zoom_level + self.pan_offset_y) 
                                      for px, py in self.hex_layout.hex_corners(h)]
                    self.create_polygon(scaled_corners, fill=color, outline=color, width=2, stipple="gray50")

        # Disegna linee a mano libera
        for line_data in getattr(self, 'drawn_lines', []):
            points = line_data.get("points", [])
            color = line_data.get("color", "red")
            if len(points) >= 2:
                screen_points = []
                for wx, wy in points:
                    sx = wx * self.zoom_level + self.pan_offset_x
                    sy = wy * self.zoom_level + self.pan_offset_y
                    screen_points.extend([sx, sy])
                self.create_line(screen_points, fill=color, width=2, smooth=True)

        for name, pdata in self.players_data.items():

            if isinstance(pdata, dict):
                pos = pdata.get('position', [0, 0])
                conditions = pdata.get('conditions', [])
                size_mult = pdata.get('size', 1)
                aura_radius = pdata.get('aura_radius', 0)
                aura_color = pdata.get('aura_color', 'yellow')
            else:
                pos = pdata
                conditions = []
                size_mult = 1
                aura_radius = 0
                aura_color = 'yellow'
                
            q, r = pos
            current_hex = Hex(q, r)
            
            # Se la nebbia è attiva, non disegnare player se l'esagono è nascosto e siamo un giocatore
            if fow_enabled and not is_dm and current_hex not in fow_revealed:
                continue
                
            center_x, center_y = self.hex_layout.hex_to_pixel(current_hex)
            screen_x = center_x * self.zoom_level + self.pan_offset_x
            screen_y = center_y * self.zoom_level + self.pan_offset_y
            color = "#90EE90" if name == self.player_name else "#87CEEB"
            radius = 10 * size_mult
            
            if aura_radius > 0:
                screen_aura_r = aura_radius * self.hex_layout.size * self.zoom_level
                self.create_oval(screen_x - screen_aura_r, screen_y - screen_aura_r, 
                                 screen_x + screen_aura_r, screen_y + screen_aura_r, 
                                 fill="", outline=aura_color, dash=(4, 4))
            
            is_turn = getattr(self, "turn_player_name", "") == name
            if is_turn:
                self.create_oval(screen_x-(radius+3), screen_y-(radius+3), screen_x+(radius+3), screen_y+(radius+3), fill="", outline="red", width=3)
                
            self.create_oval(screen_x-radius, screen_y-radius, screen_x+radius, screen_y+radius, fill=color, outline="white")
            self.create_text(screen_x, screen_y, text=name[:2], fill="black", font=("Arial", 8, "bold"))
            
            if conditions:
                # Draw condition abbreviations
                cond_colors = {
                    "Avvelenato": "green", "Accecato": "gray", "Prono": "brown", "Stordito": "yellow",
                    "Spaventato": "purple", "Invisibile": "white", "Incapacitato": "orange", "Paralizzato": "blue"
                }
                
                # Draw them in a row above the token
                box_size = 10
                start_x = screen_x - (len(conditions) * box_size) / 2
                start_y = screen_y - radius - box_size - 2
                
                for i, cond in enumerate(conditions):
                    cx = start_x + (i * box_size)
                    bg_color = cond_colors.get(cond, "red")
                    fg_color = "black" if bg_color in ["yellow", "white", "green"] else "white"
                    
                    self.create_rectangle(cx, start_y, cx + box_size, start_y + box_size, fill=bg_color, outline="black")
                    self.create_text(cx + box_size/2, start_y + box_size/2, text=cond[:1].upper(), fill=fg_color, font=("Arial", 6, "bold"))