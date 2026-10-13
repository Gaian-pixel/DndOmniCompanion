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
        self.dragging_token_name = None
        self.on_token_drop_callback = None
        
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
        self.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.bind("<Shift-Button-1>", self._on_ping_click)
        self.bind("<Button-3>", self._on_ruler_start)
        self.bind("<B3-Motion>", self._on_ruler_drag)
        self.bind("<ButtonRelease-3>", self._on_ruler_end)
        self.bind("<Shift-Button-3>", self._on_wall_toggle)
        self.bind("<Alt-Button-3>", self._on_half_cover_toggle)
        self.bind("<Control-Button-3>", self._on_three_quarters_cover_toggle)

        self.bind("<Control-Button-1>", self._on_draw_start)
        self.bind("<Control-B1-Motion>", self._on_draw_move)
        self.bind("<Control-ButtonRelease-1>", self._on_draw_end)
        self.bind("<Motion>", self._on_mouse_motion)
        self.hover_tooltip = None
        self._hovered_token = None
        self.on_hex_right_click_callback = None

        self.drawn_lines = []

    def set_on_hex_right_click_callback(self, func):
        self.on_hex_right_click_callback = func

    def set_on_click_callback(self, func):
        self.on_hex_click_callback = func

    def set_on_ping_callback(self, func):
        self.on_ping_callback = func

    def set_on_wall_toggle_callback(self, func):
        self.on_wall_toggle_callback = func

    def set_on_cover_toggle_callback(self, func):
        self.on_cover_toggle_callback = func

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
        new_zoom = self.zoom_level * factor
        if getattr(self, "map_background_original", None):
            # Limit max zoom pixels to avoid memory errors (e.g. max 100 million pixels)
            if self.map_background_original.width * new_zoom * self.map_background_original.height * new_zoom > 64000000:
                return # Prevent zooming in further
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
        
        self.dragging_token_name = None
        if getattr(self, 'players_data', None):
            for name, pdata in self.players_data.items():
                pos = pdata.get('position', [0, 0]) if isinstance(pdata, dict) else pdata
                if Hex(*pos) == clicked_hex:
                    self.dragging_token_name = name
                    break
        
        self._last_clicked_hex = clicked_hex
        self.on_hex_click_callback(clicked_hex)

    def _on_canvas_drag(self, event):
        if getattr(self, 'dragging_token_name', None):
            self.delete('ghost_token')
            self.create_oval(event.x-10, event.y-10, event.x+10, event.y+10, fill='', outline='white', dash=(2,2), tags='ghost_token')
            return


    def _on_canvas_release(self, event):
        self.delete('ghost_token')
        if getattr(self, 'dragging_token_name', None):
            if self.hex_layout and self.on_token_drop_callback:
                world_x = (event.x - self.pan_offset_x) / self.zoom_level
                world_y = (event.y - self.pan_offset_y) / self.zoom_level
                drop_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
                self.on_token_drop_callback(self.dragging_token_name, drop_hex.q, drop_hex.r)
            self.dragging_token_name = None

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
        clicked_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
        
        token_name = None
        if getattr(self, 'players_data', None):
            for name, pdata in self.players_data.items():
                pos = pdata.get('position', [0, 0]) if isinstance(pdata, dict) else pdata
                if hasattr(clicked_hex, "q"):
                    # Hex object
                    from common.hex_utils import Hex
                    if Hex(*pos) == clicked_hex:
                        token_name = name
                        break
                        
        if getattr(self, 'on_hex_right_click_callback', None):
            self.on_hex_right_click_callback(event, clicked_hex, token_name)
            return

        self._ruler_start_hex = clicked_hex


    def _on_mouse_motion(self, event):
        if not getattr(self, 'hex_layout', None): return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        hovered_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
        
        token_name = None
        if getattr(self, 'players_data', None):
            for name, pdata in self.players_data.items():
                pos = pdata.get('position', [0, 0]) if isinstance(pdata, dict) else pdata
                from common.hex_utils import Hex
                if Hex(*pos) == hovered_hex:
                    # Controlliamo la nebbia di guerra per il client
                    if getattr(self, 'fow_enabled', False) and getattr(self, 'player_name', None):
                        visible = getattr(self, 'visible_hexes', set())
                        if hovered_hex not in visible:
                            continue # Non mostrare tooltip se non e' visibile
                    token_name = name
                    break
                    
        if token_name != getattr(self, '_hovered_token', None):
            self._hovered_token = token_name
            self._update_hover_tooltip(event, token_name)
        elif token_name and self.hover_tooltip:
            # Segui il mouse
            x = self.winfo_rootx() + event.x + 15
            y = self.winfo_rooty() + event.y + 15
            self.hover_tooltip.wm_geometry(f"+{x}+{y}")

    def _update_hover_tooltip(self, event, token_name):
        if getattr(self, 'hover_tooltip', None):
            self.hover_tooltip.destroy()
            self.hover_tooltip = None
            
        if token_name:
            import tkinter as tk
            self.hover_tooltip = tk.Toplevel(self)
            self.hover_tooltip.wm_overrideredirect(True)
            self.hover_tooltip.attributes('-topmost', True)
            x = self.winfo_rootx() + event.x + 15
            y = self.winfo_rooty() + event.y + 15
            self.hover_tooltip.wm_geometry(f"+{x}+{y}")
            
            pdata = self.players_data[token_name]
            hp = pdata.get('hp', '?') if isinstance(pdata, dict) else '?'
            hp_max = pdata.get('hp_max', '?') if isinstance(pdata, dict) else '?'
            
            text = f"{token_name}"
            if isinstance(pdata, dict) and 'hp' in pdata:
                text += f"\nHP: {hp}/{hp_max}"
                
            label = tk.Label(self.hover_tooltip, text=text, background="#36393F", foreground="white", relief="solid", borderwidth=1, font=("Helvetica", 9, "bold"))
            label.pack(padx=3, pady=3)

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

    def _on_half_cover_toggle(self, event):
        if not self.hex_layout or not getattr(self, 'on_cover_toggle_callback', None): return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        clicked_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
        if hasattr(self, 'map_data'):
            half_cover = self.map_data.setdefault("half_cover", [])
            pos = [clicked_hex.q, clicked_hex.r]
            if pos in half_cover:
                half_cover.remove(pos)
            else:
                half_cover.append(pos)
            self.redraw()
        self.on_cover_toggle_callback(clicked_hex.q, clicked_hex.r, "half_cover")

    def _on_three_quarters_cover_toggle(self, event):
        if not self.hex_layout or not getattr(self, 'on_cover_toggle_callback', None): return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        clicked_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
        if hasattr(self, 'map_data'):
            tq_cover = self.map_data.setdefault("three_quarters_cover", [])
            pos = [clicked_hex.q, clicked_hex.r]
            if pos in tq_cover:
                tq_cover.remove(pos)
            else:
                tq_cover.append(pos)
            self.redraw()
        self.on_cover_toggle_callback(clicked_hex.q, clicked_hex.r, "three_quarters_cover")

    def draw_ping(self, q, r, color="red"):
        if not self.hex_layout: return
        hex_obj = Hex(q, r)
        center_x, center_y = self.hex_layout.hex_to_pixel(hex_obj)
        screen_x = center_x * self.zoom_level + self.pan_offset_x
        screen_y = center_y * self.zoom_level + self.pan_offset_y
        
        radius = self.hex_layout.size * self.zoom_level
        ping_outer = self.create_oval(screen_x - radius, screen_y - radius, 
                                      screen_x + radius, screen_y + radius, 
                                      outline=color, width=3)
        ping_inner = self.create_oval(screen_x - radius * 0.5, screen_y - radius * 0.5, 
                                      screen_x + radius * 0.5, screen_y + radius * 0.5, 
                                      outline=color, width=2)
        ping_dot = self.create_oval(screen_x - 3, screen_y - 3, screen_x + 3, screen_y + 3, fill=color, outline="")
        
        ping_ids = [ping_outer, ping_inner, ping_dot]
        self.after(2200, lambda: [self.delete(pid) for pid in ping_ids])

    def center_view(self):
        """Centra la vista della mappa mantenendo lo zoom attuale."""
        cw = self.winfo_width()
        ch = self.winfo_height()
        if getattr(self, "map_background_original", None):
            w = self.map_background_original.width * self.zoom_level
            h = self.map_background_original.height * self.zoom_level
            self.pan_offset_x = (cw - w) / 2
            self.pan_offset_y = (ch - h) / 2
        else:
            self.pan_offset_x = cw / 2
            self.pan_offset_y = ch / 2
        self.redraw()

    def update_data(self, map_data, players_data, player_name="", turn_player_name="", aoes_data=None, time_hour=12, weather="Sereno", combat_active=False, combat_order=None):
        """Salva i dati necessari per il ridisegno."""
        self.map_data = map_data
        self.players_data = players_data
        self.player_name = player_name
        self.turn_player_name = turn_player_name
        self.aoes_data = aoes_data or []
        self.time_hour = time_hour
        self.weather = weather
        self.combat_active = combat_active
        self.combat_order = combat_order or []
        self.redraw()

    def redraw(self):

        if not hasattr(self, '_avatar_cache'):
            self._avatar_cache = {}

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
                try:
                    if self._last_zoom != self.zoom_level:
                        # Usa un resampling più veloce (NEAREST o BILINEAR) invece di LANCZOS per prestazioni real-time
                        resample_mode = Image.Resampling.NEAREST if new_width * new_height > 4000000 else Image.Resampling.BILINEAR
                        resized_img = self.map_background_original.resize((new_width, new_height), resample_mode)
                        self.map_background_tk = ImageTk.PhotoImage(resized_img)
                        self._last_zoom = self.zoom_level
                    self.create_image(self.pan_offset_x, self.pan_offset_y, image=self.map_background_tk, anchor="nw")
                except Exception as e:
                    print(f"Errore ridimensionamento: {e}")

        pois_data = {Hex(int(k.split(',')[0]), int(k.split(',')[1])): v for k, v in self.map_data.get("pois", {}).items()}
        border_color = self.map_data.get("hex_border_color", "white")
        
        fow_enabled = self.map_data.get("fow_enabled", False)
        is_dm = not bool(self.player_name)
        draft_key = "fow_draft" if ("fow_draft" in self.map_data and is_dm) else "fow_revealed"
        fow_revealed = {Hex(h[0], h[1]) for h in self.map_data.get(draft_key, [])}
        walls_data = self.map_data.get("walls", [])
        walls_set = {Hex(w[0], w[1]) for w in walls_data}
        
        visible_now = set()
        if not is_dm and self.player_name in self.players_data:
            from common.hex_utils import get_visible_hexes
            pdata = self.players_data[self.player_name]
            pos = pdata.get('position') if isinstance(pdata, dict) else pdata
            if pos is None:
                pos = [0, 0]
            vision_rad = pdata.get('vision_radius', 6) if isinstance(pdata, dict) else 6
            visible_now = set(get_visible_hexes(Hex(pos[0], pos[1]), vision_rad, walls_set))
            
        half_cover_data = self.map_data.get("half_cover", [])
        three_quarters_cover_data = self.map_data.get("three_quarters_cover", [])
        
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
            elif [q, r] in half_cover_data:
                fill_color = "#8B4513"
                stipple_pattern = ""
            elif [q, r] in three_quarters_cover_data:
                fill_color = "#A0522D"
                stipple_pattern = ""
            elif fow_enabled and current_hex not in fow_revealed:
                if is_dm:
                    fill_color = "gray25"
                    stipple_pattern = "gray50"
                else:
                    fill_color = "black"
                    stipple_pattern = ""
            elif fow_enabled and not is_dm and current_hex not in visible_now:
                fill_color = "gray10"
                stipple_pattern = "gray75"
            
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

        # Draw Loots
        loots_data = self.map_data.get("loots", [])
        for l in loots_data:
            lh = Hex(l["q"], l["r"])
            if fow_enabled and not is_dm and lh not in fow_revealed:
                continue
            cx, cy = self.hex_layout.hex_to_pixel(lh)
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            self.create_rectangle(sx-10, sy-10, sx+10, sy+10, fill="gold", outline="brown")
            self.create_text(sx, sy, text="Loot", font=("", max(8, int(10*self.zoom_level))))
            
        # Draw Lights
        lights_data = self.map_data.get("lights", [])
        for l in lights_data:
            lh = Hex(l["q"], l["r"])
            if fow_enabled and not is_dm and lh not in fow_revealed:
                continue
            cx, cy = self.hex_layout.hex_to_pixel(lh)
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            self.create_oval(sx-5, sy-5, sx+5, sy+5, fill="yellow", outline="orange")
            
        # Draw Teleports
        teleports_data = self.map_data.get("teleports", {})
        for k in teleports_data:
            q_str, r_str = k.split(",")
            lh = Hex(int(q_str), int(r_str))
            if fow_enabled and not is_dm and lh not in fow_revealed:
                continue
            cx, cy = self.hex_layout.hex_to_pixel(lh)
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            self.create_oval(sx-6, sy-6, sx+6, sy+6, fill="blue", outline="cyan", width=2)
            if is_dm:
                self.create_text(sx, sy-15, text="🚪", font=("", max(8, int(10*self.zoom_level))))
            
        # Draw Spawn Point
        spawn_point = self.map_data.get("spawn_point")
        if spawn_point and is_dm:
            lh = Hex(*spawn_point)
            cx, cy = self.hex_layout.hex_to_pixel(lh)
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            self.create_text(sx, sy, text="[S]\nSpawn", font=("Arial", max(8, int(10*self.zoom_level)), "bold"), fill="#00FF00", justify="center")
            
        for name, pdata in self.players_data.items():

            if isinstance(pdata, dict):
                pos = pdata.get('position')
                if pos is None:
                    pos = [0, 0]
                conditions = pdata.get('conditions', [])
                size_mult = pdata.get('size', 1)
                aura_radius = pdata.get('aura_radius', 0)
                aura_color = pdata.get('aura_color', 'yellow')
                hp = pdata.get('hp', 0)
                hp_max = pdata.get('hp_max', 0)
            else:
                pos = pdata
                if pos is None:
                    pos = [0, 0]
                conditions = []
                size_mult = 1
                aura_radius = 0
                aura_color = 'yellow'
                hp = 0
                hp_max = 0
                
            q, r = pos
            current_hex = Hex(q, r)
            
            # Se la nebbia è attiva, non disegnare player se l'esagono è nascosto e siamo un giocatore
            if fow_enabled and not is_dm:
                if current_hex not in visible_now:
                    continue
                
            center_x, center_y = self.hex_layout.hex_to_pixel(current_hex)
            screen_x = center_x * self.zoom_level + self.pan_offset_x
            screen_y = center_y * self.zoom_level + self.pan_offset_y
            is_me = (name == self.player_name)
            is_party = pdata.get('is_party_member', False) if isinstance(pdata, dict) else False
            if is_me:
                token_base_color = "#2B8A3E"   # Smeraldo eroe
                token_border_color = "#D4AF37" # Bordo oro
            elif is_party:
                token_base_color = "#1971C2"   # Blu arcano alleati
                token_border_color = "#4DABF7"
            else:
                token_base_color = "#C92A2A"   # Cremisi mostri / NPC
                token_border_color = "#FF8787"

            radius = 12 * size_mult
            
            # Aura magica ad anelli concentrici
            if aura_radius > 0:
                screen_aura_r = aura_radius * self.hex_layout.size * 1.732 * self.zoom_level
                self.create_oval(screen_x - screen_aura_r, screen_y - screen_aura_r, 
                                 screen_x + screen_aura_r, screen_y + screen_aura_r, 
                                 fill="", outline=aura_color, dash=(8, 4), width=3)
                inner_aura_r = max(radius + 2, screen_aura_r * 0.7)
                self.create_oval(screen_x - inner_aura_r, screen_y - inner_aura_r,
                                 screen_x + inner_aura_r, screen_y + inner_aura_r,
                                 fill="", outline=aura_color, dash=(4, 4), width=1)
            
            # Evidenziazione Turno Attivo (Doppio anello oro radiante)
            is_turn = getattr(self, "turn_player_name", "") == name
            if is_turn:
                self.create_oval(screen_x-(radius+5), screen_y-(radius+5), screen_x+(radius+5), screen_y+(radius+5), fill="", outline="#FCC419", width=2)
                self.create_oval(screen_x-(radius+3), screen_y-(radius+3), screen_x+(radius+3), screen_y+(radius+3), fill="", outline="#D4AF37", width=3)
            
            # Ombreggiatura per profondità token
            self.create_oval(screen_x-radius+1, screen_y-radius+2, screen_x+radius+1, screen_y+radius+2, fill="#0A0B0D", outline="")

            is_invisible = "Invisibile" in conditions
            avatar_b64 = pdata.get('avatar_b64') if isinstance(pdata, dict) else None
            
            if avatar_b64:
                cache_key = f"{name}_{size_mult}_{self.zoom_level}"
                if cache_key not in self._avatar_cache:
                    try:
                        img_bytes = base64.b64decode(avatar_b64)
                        img = Image.open(BytesIO(img_bytes))
                        target_size = int(radius * 2)
                        img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
                        
                        mask = Image.new('L', (target_size, target_size), 0)
                        from PIL import ImageDraw
                        draw = ImageDraw.Draw(mask)
                        draw.ellipse((0, 0, target_size, target_size), fill=255)
                        
                        circular_img = Image.new('RGBA', (target_size, target_size), (0,0,0,0))
                        circular_img.paste(img, (0,0), mask=mask)
                        
                        self._avatar_cache[cache_key] = ImageTk.PhotoImage(circular_img)
                    except Exception as e:
                        print("Error loading avatar:", e)
                        self._avatar_cache[cache_key] = None
                        
                tk_img = self._avatar_cache.get(cache_key)
                if tk_img:
                    self.create_image(screen_x, screen_y, image=tk_img, anchor="center")
                    ring_outline = "gray" if is_invisible else token_border_color
                    ring_dash = (2, 2) if is_invisible else ""
                    self.create_oval(screen_x-radius, screen_y-radius, screen_x+radius, screen_y+radius, fill="", outline=ring_outline, width=2, dash=ring_dash)
                else:
                    outline_style = "gray" if is_invisible else token_border_color
                    dash_style = (2, 2) if is_invisible else ""
                    self.create_oval(screen_x-radius, screen_y-radius, screen_x+radius, screen_y+radius, fill=token_base_color, outline=outline_style, width=2, dash=dash_style)
                    self.create_text(screen_x, screen_y, text=name[:2].upper(), fill="white", font=("Segoe UI", 8, "bold"))
            else:
                outline_style = "gray" if is_invisible else token_border_color
                dash_style = (2, 2) if is_invisible else ""
                self.create_oval(screen_x-radius, screen_y-radius, screen_x+radius, screen_y+radius, fill=token_base_color, outline=outline_style, width=2, dash=dash_style)
                self.create_text(screen_x, screen_y, text=name[:2].upper(), fill="white", font=("Segoe UI", 8, "bold"))

            if hp_max > 0:
                bar_w = radius * 2.2
                bar_h = 4
                bar_y = screen_y + radius + 3
                bar_x = screen_x - (bar_w / 2)
                hp_ratio = max(0.0, min(1.0, hp / hp_max))
                self.create_rectangle(bar_x, bar_y, bar_x + bar_w, bar_y + bar_h, fill="#1A1B1E", outline="#2C2E33")
                if hp_ratio > 0:
                    bar_color = "#2B8A3E" if hp_ratio > 0.5 else ("#F59F00" if hp_ratio > 0.25 else "#C92A2A")
                    self.create_rectangle(bar_x, bar_y, bar_x + (bar_w * hp_ratio), bar_y + bar_h, fill=bar_color, outline="")

            if conditions:
                cond_colors = {
                    "Avvelenato": "green", "Accecato": "gray", "Prono": "brown", "Stordito": "yellow",
                    "Spaventato": "purple", "Invisibile": "white", "Incapacitato": "orange", "Paralizzato": "blue"
                }
                
                box_size = 10
                start_x = screen_x + radius - box_size/2
                start_y = screen_y - radius - box_size/2
                
                for i, cond in enumerate(conditions):
                    cx = start_x + (i * box_size)
                    bg_color = cond_colors.get(cond, "red")
                    fg_color = "black" if bg_color in ["yellow", "white", "green"] else "white"
                    
                    abbrev_map = {
                        "Avvelenato": "Av",
                        "Prono": "P",
                        "Trattenuto": "Tr"
                    }
                    abbrev = abbrev_map.get(cond, cond[:2].capitalize())
                    
                    self.create_rectangle(cx, start_y, cx + box_size, start_y + box_size, fill=bg_color, outline="black")
                    self.create_text(cx + box_size/2, start_y + box_size/2, text=abbrev, fill=fg_color, font=("Arial", 6, "bold"))
                    
        # --- ENVIRONMENTS & COMBAT OVERLAYS ---
        w = self.winfo_width()
        h = self.winfo_height()
        
        # 1. Day/Night Cycle
        hour = getattr(self, "time_hour", 12)
        if hour < 6 or hour > 19:
            # Draw a semi-transparent dark rectangle (using stipple since tk canvas alpha is hard, or just skip if too ugly)
            # A trick for pseudo-transparency in tk canvas is drawing many lines or stipples.
            # We'll use a text overlay or simple gray50 stipple
            self.create_rectangle(0, 0, w, h, fill="black", stipple="gray50", outline="", tags="night_overlay")
            self.create_text(w/2, 20, text=f"Notte ({hour}:00)", fill="white", font=("Arial", 12, "bold"))
            
        # 2. Weather
        weather = getattr(self, "weather", "Sereno")
        if weather == "Pioggia":
            self.create_rectangle(0, 0, w, h, fill="blue", stipple="gray25", outline="", tags="weather_overlay")
            self.create_text(w/2, 40, text="Pioggia", fill="lightblue", font=("Arial", 12, "bold"))
        elif weather == "Neve":
            self.create_rectangle(0, 0, w, h, fill="white", stipple="gray25", outline="", tags="weather_overlay")
            self.create_text(w/2, 40, text="Neve", fill="white", font=("Arial", 12, "bold"))
            
        # 3. Public Initiative Tracker
        if getattr(self, "combat_active", False) and getattr(self, "combat_order", None):
            order = self.combat_order
            # Draw a floating box on the top right
            box_width = 150
            box_height = 30 + len(order) * 20
            start_x = w - box_width - 10
            start_y = 10
            self.create_rectangle(start_x, start_y, start_x + box_width, start_y + box_height, fill="#2c2f33", outline="gold", width=2)
            self.create_text(start_x + box_width/2, start_y + 15, text="Iniziativa", fill="gold", font=("Arial", 10, "bold"))
            
            for i, name in enumerate(order):
                color = "white"
                prefix = ""
                if name == getattr(self, "turn_player_name", ""):
                    color = "#00ff00"
                    prefix = "▶ "
                self.create_text(start_x + 10, start_y + 35 + i * 20, text=f"{prefix}{i+1}. {name}", fill=color, font=("Arial", 9), anchor="w")

class ToolTip:
    """Finestrella di tooltip mostrata al passaggio del mouse."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert") or (0, 0, 0, 0)
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

