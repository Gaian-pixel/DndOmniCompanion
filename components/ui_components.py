# ui_components.py
import tkinter as tk
import base64
import math
from io import BytesIO
from PIL import Image, ImageTk, ImageDraw
from common.hex_utils import (
    Hex, HexLayout, hex_distance,
    get_sphere_hexes, get_cone_hexes, get_line_hexes, get_visible_hexes
)

class HexMapCanvas(tk.Canvas):
    """Un widget Canvas riutilizzabile per visualizzare e interagire con una mappa esagonale."""
    
    def __init__(self, parent, **kwargs):
        bg_color = kwargs.pop('bg', "#1e1e1e")
        super().__init__(parent, bg=bg_color, highlightthickness=0, **kwargs)

        self.zoom_level = 1.0
        self.pan_offset_x, self.pan_offset_y = 0, 0
        self._pan_start_x, self._pan_start_y = 0, 0
        self._drag_start_x, self._drag_start_y = 0, 0
        self._is_panning = False
        self._rendered_pan_x, self._rendered_pan_y = 0, 0
        self._pan_redraw_timer = None
        self._configure_timer = None
        self._last_win_w, self._last_win_h = 0, 0
        self._map_hexes_set = None
        
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
        self.bind("<plus>", lambda e: self.zoom_in(e.x, e.y))
        self.bind("<minus>", lambda e: self.zoom_out(e.x, e.y))
        self.bind("<equal>", lambda e: self.zoom_in(e.x, e.y))
        self.bind("<KP_Add>", lambda e: self.zoom_in(e.x, e.y))
        self.bind("<KP_Subtract>", lambda e: self.zoom_out(e.x, e.y))
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
        self.bind("<Configure>", self._on_configure)
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

    def _on_configure(self, event):
        if event.width > 1 and event.height > 1 and (event.width != self._last_win_w or event.height != self._last_win_h):
            self._last_win_w = event.width
            self._last_win_h = event.height
            if self._configure_timer is not None:
                self.after_cancel(self._configure_timer)
            self._configure_timer = self.after(60, self._on_configure_redraw)

    def _on_configure_redraw(self):
        self._configure_timer = None
        self.redraw()

    def _zoom(self, event):
        factor = 1.15 if (event.num == 4 or getattr(event, "delta", 0) > 0) else 0.85
        new_zoom = max(0.05, min(10.0, self.zoom_level * factor))
        if abs(new_zoom - self.zoom_level) < 1e-5:
            return
            
        if getattr(self, "map_background_original", None):
            if self.map_background_original.width * new_zoom * self.map_background_original.height * new_zoom > 256000000:
                return

        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        self.zoom_level = new_zoom
        self.pan_offset_x = event.x - world_x * self.zoom_level
        self.pan_offset_y = event.y - world_y * self.zoom_level
        self.redraw()

    def zoom_in(self, center_x=None, center_y=None):
        cw = max(self.winfo_width(), 100)
        ch = max(self.winfo_height(), 100)
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
        cw = max(self.winfo_width(), 100)
        ch = max(self.winfo_height(), 100)
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

    def _pan_start(self, event):
        self._pan_start_x = event.x
        self._pan_start_y = event.y
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._is_panning = False

    def _pan_move(self, event):
        dx = event.x - self._pan_start_x
        dy = event.y - self._pan_start_y
        self.pan_offset_x += dx
        self.pan_offset_y += dy
        self._pan_start_x = event.x
        self._pan_start_y = event.y

        if abs(event.x - self._drag_start_x) > 4 or abs(event.y - self._drag_start_y) > 4:
            self._is_panning = True

        self.move("all", dx, dy)

        cw = max(self.winfo_width(), 200)
        ch = max(self.winfo_height(), 200)
        pan_drift_x = abs(self.pan_offset_x - getattr(self, "_rendered_pan_x", 0))
        pan_drift_y = abs(self.pan_offset_y - getattr(self, "_rendered_pan_y", 0))
        if pan_drift_x > cw * 0.45 or pan_drift_y > ch * 0.45:
            self._schedule_pan_redraw()

    def _schedule_pan_redraw(self):
        if self._pan_redraw_timer is not None:
            self.after_cancel(self._pan_redraw_timer)
        self._pan_redraw_timer = self.after(50, self._on_pan_drift_redraw)

    def _on_pan_drift_redraw(self):
        self._pan_redraw_timer = None
        self.redraw()

    def _on_ping_click_b2(self, event):
        if self._pan_redraw_timer is not None:
            self.after_cancel(self._pan_redraw_timer)
            self._pan_redraw_timer = None

        if self._is_panning:
            self._is_panning = False
            self.redraw()
        else:
            self._on_ping_click(event)

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
        if getattr(self, 'map_data', None) is not map_data:
            self._map_hexes_set = None
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

        cw = self.winfo_width()
        ch = self.winfo_height()
        if cw <= 1:
            try: cw = int(self.cget("width"))
            except Exception: cw = 1024
        if ch <= 1:
            try: ch = int(self.cget("height"))
            except Exception: ch = 768

        self._rendered_pan_x = self.pan_offset_x
        self._rendered_pan_y = self.pan_offset_y

        hex_size = self.map_data.get("hex_size", 30)
        self.hex_layout = HexLayout(size=hex_size, origin=(0, 0))

        # Viewport bounds in world coords with overdraw margin for smooth panning
        margin = 0.2
        scr_x1, scr_y1 = -cw * margin, -ch * margin
        scr_x2, scr_y2 = cw * (1.0 + margin), ch * (1.0 + margin)

        world_x1 = (scr_x1 - self.pan_offset_x) / self.zoom_level
        world_x2 = (scr_x2 - self.pan_offset_x) / self.zoom_level
        world_y1 = (scr_y1 - self.pan_offset_y) / self.zoom_level
        world_y2 = (scr_y2 - self.pan_offset_y) / self.zoom_level

        # Gestione immagine di sfondo con caching e crop del viewport se grande
        image_data_b64 = self.map_data.get("bg_image_data")
        if image_data_b64:
            if getattr(self, '_last_b64', None) != image_data_b64:
                try:
                    image_bytes = base64.b64decode(image_data_b64)
                    self.map_background_original = Image.open(BytesIO(image_bytes))
                    self._last_b64 = image_data_b64
                    self._last_zoom = None
                    self.map_background_tk = None
                except Exception as e:
                    self.map_background_original = None
                    print(f"Errore decodifica immagine: {e}")
        else:
            self.map_background_original = None
            self._last_b64 = None

        if getattr(self, 'map_background_original', None):
            orig_w, orig_h = self.map_background_original.size
            full_w = int(orig_w * self.zoom_level)
            full_h = int(orig_h * self.zoom_level)
            
            # Crop dinamico solo se l'immagine a schermo supera 4M pixel (per evitare OutOfMemory su zoom estremi)
            if full_w * full_h > 4000000:
                crop_x1 = max(0, int((scr_x1 - self.pan_offset_x) / self.zoom_level))
                crop_y1 = max(0, int((scr_y1 - self.pan_offset_y) / self.zoom_level))
                crop_x2 = min(orig_w, int((scr_x2 - self.pan_offset_x) / self.zoom_level))
                crop_y2 = min(orig_h, int((scr_y2 - self.pan_offset_y) / self.zoom_level))
                if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                    target_w = max(1, int((crop_x2 - crop_x1) * self.zoom_level))
                    target_h = max(1, int((crop_y2 - crop_y1) * self.zoom_level))
                    try:
                        cropped = self.map_background_original.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                        resized_img = cropped.resize((target_w, target_h), Image.Resampling.BILINEAR)
                        self.map_background_tk = ImageTk.PhotoImage(resized_img)
                        dest_x = crop_x1 * self.zoom_level + self.pan_offset_x
                        dest_y = crop_y1 * self.zoom_level + self.pan_offset_y
                        self.create_image(dest_x, dest_y, image=self.map_background_tk, anchor="nw")
                    except Exception as e:
                        print("Errore rendering sfondo:", e)
            else:
                if self._last_zoom != self.zoom_level or getattr(self, "map_background_tk", None) is None:
                    try:
                        resized_img = self.map_background_original.resize((full_w, full_h), Image.Resampling.BILINEAR)
                        self.map_background_tk = ImageTk.PhotoImage(resized_img)
                        self._last_zoom = self.zoom_level
                    except Exception as e:
                        print("Errore resizing sfondo:", e)
                if getattr(self, "map_background_tk", None):
                    self.create_image(self.pan_offset_x, self.pan_offset_y, image=self.map_background_tk, anchor="nw")

        # Sets per lookup rapido O(1)
        pois_data = {(int(k.split(',')[0]), int(k.split(',')[1])): v for k, v in self.map_data.get("pois", {}).items()}
        border_color = self.map_data.get("hex_border_color", "white")
        
        fow_enabled = self.map_data.get("fow_enabled", False)
        is_dm = not bool(self.player_name)
        draft_key = "fow_draft" if ("fow_draft" in self.map_data and is_dm) else "fow_revealed"
        fow_revealed = {tuple(h) for h in self.map_data.get(draft_key, [])}
        walls_data = self.map_data.get("walls", [])
        walls_set = {tuple(w) for w in walls_data}
        walls_hex_set = {Hex(w[0], w[1]) for w in walls_data}

        visible_now = set()
        if not is_dm and self.player_name in self.players_data:
            pdata = self.players_data[self.player_name]
            pos = pdata.get('position') if isinstance(pdata, dict) else pdata
            if pos is None: pos = [0, 0]
            vision_rad = pdata.get('vision_radius', 6) if isinstance(pdata, dict) else 6
            visible_now = {(h.q, h.r) for h in get_visible_hexes(Hex(pos[0], pos[1]), vision_rad, walls_hex_set)}

        half_cover_set = {tuple(c) for c in self.map_data.get("half_cover", [])}
        three_quarters_cover_set = {tuple(c) for c in self.map_data.get("three_quarters_cover", [])}

        # Cache e calcolo esagoni visibili
        raw_hexes = self.map_data.get("hexes", [])
        if self._map_hexes_set is None or len(self._map_hexes_set) != len(raw_hexes):
            self._map_hexes_set = {tuple(h) for h in raw_hexes}

        sqrt3 = 1.7320508075688772
        sqrt3_size = sqrt3 * hex_size
        step_x = 1.5 * hex_size

        min_q = int(math.floor((world_x1 - hex_size) / step_x))
        max_q = int(math.ceil((world_x2 + hex_size) / step_x))

        _BASE_OFFSETS = (
            (1.0, 0.0),
            (0.5, 0.8660254037844386),
            (-0.5, 0.8660254037844386),
            (-1.0, 0.0),
            (-0.5, -0.8660254037844386),
            (0.5, -0.8660254037844386)
        )
        scaled_size = hex_size * self.zoom_level
        corner_offsets = tuple((dx * scaled_size, dy * scaled_size) for dx, dy in _BASE_OFFSETS)
        line_w = max(1, int(1/self.zoom_level)) if self.zoom_level < 1 else 1

        # Trova esagoni intersecanti con il viewport
        candidate_count = (max_q - min_q + 1) * int((world_y2 - world_y1) / sqrt3_size + 2)
        if candidate_count < len(self._map_hexes_set):
            visible_hex_list = []
            for q in range(min_q, max_q + 1):
                min_r = int(math.floor((world_y1 - hex_size) / sqrt3_size - q * 0.5))
                max_r = int(math.ceil((world_y2 + hex_size) / sqrt3_size - q * 0.5))
                for r in range(min_r, max_r + 1):
                    if (q, r) in self._map_hexes_set:
                        visible_hex_list.append((q, r))
        else:
            visible_hex_list = [
                (q, r) for q, r in self._map_hexes_set
                if (min_q <= q <= max_q) and (world_y1 - hex_size <= hex_size * (sqrt3 * 0.5 * q + sqrt3 * r) <= world_y2 + hex_size)
            ]

        for q, r in visible_hex_list:
            cx = step_x * q
            cy = hex_size * (sqrt3 * 0.5 * q + sqrt3 * r)
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y

            scaled_corners = [(sx + dx, sy + dy) for dx, dy in corner_offsets]
            hex_tup = (q, r)

            fill_color = "#FFD700" if hex_tup in pois_data else ""
            stipple_pattern = ""

            if hex_tup in walls_set:
                fill_color = "#101010"
            elif hex_tup in half_cover_set:
                fill_color = "#8B4513"
            elif hex_tup in three_quarters_cover_set:
                fill_color = "#A0522D"
            elif fow_enabled and hex_tup not in fow_revealed:
                if is_dm:
                    fill_color = "gray25"
                    stipple_pattern = "gray50"
                else:
                    fill_color = "black"
            elif fow_enabled and not is_dm and hex_tup not in visible_now:
                fill_color = "gray10"
                stipple_pattern = "gray75"

            if scaled_size < 8.0 and not fill_color:
                continue

            self.create_polygon(scaled_corners, fill=fill_color, outline=border_color, width=line_w, stipple=stipple_pattern)

        # Disegna le aree d'effetto (AoE)
        if getattr(self, "aoes_data", None):
            for aoe in self.aoes_data:
                origin = Hex(*aoe["origin"])
                color = aoe.get("color", "red")
                aoe_type = aoe.get("type", "sfera")
                if aoe_type in ("sfera", "cubo"):
                    aoe_hexes = get_sphere_hexes(origin, aoe["size"])
                elif aoe_type == "cono":
                    aoe_hexes = get_cone_hexes(origin, Hex(*aoe.get("target", aoe["origin"])), aoe["size"])
                elif aoe_type == "linea":
                    aoe_hexes = get_line_hexes(origin, Hex(*aoe.get("target", aoe["origin"])))
                else:
                    aoe_hexes = []

                for h in aoe_hexes:
                    if fow_enabled and not is_dm and (h.q, h.r) not in fow_revealed:
                        continue
                    cx = step_x * h.q
                    cy = hex_size * (sqrt3 * 0.5 * h.q + sqrt3 * h.r)
                    if not (world_x1 - hex_size <= cx <= world_x2 + hex_size and world_y1 - hex_size <= cy <= world_y2 + hex_size):
                        continue
                    sx = cx * self.zoom_level + self.pan_offset_x
                    sy = cy * self.zoom_level + self.pan_offset_y
                    scaled_corners = [(sx + dx, sy + dy) for dx, dy in corner_offsets]
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
            l_tup = (l["q"], l["r"])
            if fow_enabled and not is_dm and l_tup not in fow_revealed:
                continue
            cx = step_x * l["q"]
            cy = hex_size * (sqrt3 * 0.5 * l["q"] + sqrt3 * l["r"])
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            if scr_x1 <= sx <= scr_x2 and scr_y1 <= sy <= scr_y2:
                self.create_rectangle(sx-10, sy-10, sx+10, sy+10, fill="gold", outline="brown")
                self.create_text(sx, sy, text="Loot", font=("", max(8, int(10*self.zoom_level))))

        # Draw Lights
        lights_data = self.map_data.get("lights", [])
        for l in lights_data:
            l_tup = (l["q"], l["r"])
            if fow_enabled and not is_dm and l_tup not in fow_revealed:
                continue
            cx = step_x * l["q"]
            cy = hex_size * (sqrt3 * 0.5 * l["q"] + sqrt3 * l["r"])
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            if scr_x1 <= sx <= scr_x2 and scr_y1 <= sy <= scr_y2:
                self.create_oval(sx-5, sy-5, sx+5, sy+5, fill="yellow", outline="orange")

        # Draw Teleports
        teleports_data = self.map_data.get("teleports", {})
        for k in teleports_data:
            q_str, r_str = k.split(",")
            t_q, t_r = int(q_str), int(r_str)
            if fow_enabled and not is_dm and (t_q, t_r) not in fow_revealed:
                continue
            cx = step_x * t_q
            cy = hex_size * (sqrt3 * 0.5 * t_q + sqrt3 * t_r)
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            if scr_x1 <= sx <= scr_x2 and scr_y1 <= sy <= scr_y2:
                self.create_oval(sx-6, sy-6, sx+6, sy+6, fill="blue", outline="cyan", width=2)
                if is_dm:
                    self.create_text(sx, sy-15, text="🚪", font=("", max(8, int(10*self.zoom_level))))

        # Draw Spawn Point
        spawn_point = self.map_data.get("spawn_point")
        if spawn_point and is_dm:
            sp_q, sp_r = spawn_point[0], spawn_point[1]
            cx = step_x * sp_q
            cy = hex_size * (sqrt3 * 0.5 * sp_q + sqrt3 * sp_r)
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            if scr_x1 <= sx <= scr_x2 and scr_y1 <= sy <= scr_y2:
                self.create_text(sx, sy, text="[S]\nSpawn", font=("Arial", max(8, int(10*self.zoom_level)), "bold"), fill="#00FF00", justify="center")

        # Tokens (Players e PNG)
        for name, pdata in self.players_data.items():
            if isinstance(pdata, dict):
                pos = pdata.get('position') or [0, 0]
                conditions = pdata.get('conditions', [])
                size_mult = pdata.get('size', 1)
                aura_radius = pdata.get('aura_radius', 0)
                aura_color = pdata.get('aura_color', 'yellow')
                hp = pdata.get('hp', 0)
                hp_max = pdata.get('hp_max', 0)
            else:
                pos = pdata or [0, 0]
                conditions = []
                size_mult = 1
                aura_radius = 0
                aura_color = 'yellow'
                hp = 0
                hp_max = 0

            q, r = pos[0], pos[1]
            if fow_enabled and not is_dm and (q, r) not in visible_now:
                continue

            cx = step_x * q
            cy = hex_size * (sqrt3 * 0.5 * q + sqrt3 * r)
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y

            radius = 12 * size_mult
            screen_aura_r = (aura_radius * hex_size * sqrt3 * self.zoom_level) if aura_radius > 0 else 0
            max_r = max(radius + 20, screen_aura_r + 10)
            if not (scr_x1 - max_r <= sx <= scr_x2 + max_r and scr_y1 - max_r <= sy <= scr_y2 + max_r):
                continue

            is_me = (name == self.player_name)
            is_party = pdata.get('is_party_member', False) if isinstance(pdata, dict) else False
            if is_me:
                token_base_color = "#2B8A3E"
                token_border_color = "#D4AF37"
            elif is_party:
                token_base_color = "#1971C2"
                token_border_color = "#4DABF7"
            else:
                token_base_color = "#C92A2A"
                token_border_color = "#FF8787"

            # Aura magica ad anelli concentrici
            if aura_radius > 0:
                self.create_oval(sx - screen_aura_r, sy - screen_aura_r, 
                                 sx + screen_aura_r, sy + screen_aura_r, 
                                 fill="", outline=aura_color, dash=(8, 4), width=3)
                inner_aura_r = max(radius + 2, screen_aura_r * 0.7)
                self.create_oval(sx - inner_aura_r, sy - inner_aura_r,
                                 sx + inner_aura_r, sy + inner_aura_r,
                                 fill="", outline=aura_color, dash=(4, 4), width=1)

            # Evidenziazione Turno Attivo (Doppio anello oro radiante)
            is_turn = getattr(self, "turn_player_name", "") == name
            if is_turn:
                self.create_oval(sx-(radius+5), sy-(radius+5), sx+(radius+5), sy+(radius+5), fill="", outline="#FCC419", width=2)
                self.create_oval(sx-(radius+3), sy-(radius+3), sx+(radius+3), sy+(radius+3), fill="", outline="#D4AF37", width=3)

            # Ombreggiatura per profondita token
            self.create_oval(sx-radius+1, sy-radius+2, sx+radius+1, sy+radius+2, fill="#0A0B0D", outline="")

            is_invisible = "Invisibile" in conditions
            avatar_b64 = pdata.get('avatar_b64') if isinstance(pdata, dict) else None

            if avatar_b64:
                target_size = max(16, int(radius * 2))
                cache_key = f"{name}_{target_size}"
                if cache_key not in self._avatar_cache:
                    try:
                        img_bytes = base64.b64decode(avatar_b64)
                        img = Image.open(BytesIO(img_bytes)).convert("RGBA")
                        img = img.resize((target_size, target_size), Image.Resampling.BILINEAR)
                        mask = Image.new('L', (target_size, target_size), 0)
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
                    self.create_image(sx, sy, image=tk_img, anchor="center")
                    ring_outline = "gray" if is_invisible else token_border_color
                    ring_dash = (2, 2) if is_invisible else ""
                    self.create_oval(sx-radius, sy-radius, sx+radius, sy+radius, fill="", outline=ring_outline, width=2, dash=ring_dash)
                else:
                    outline_style = "gray" if is_invisible else token_border_color
                    dash_style = (2, 2) if is_invisible else ""
                    self.create_oval(sx-radius, sy-radius, sx+radius, sy+radius, fill=token_base_color, outline=outline_style, width=2, dash=dash_style)
                    self.create_text(sx, sy, text=name[:2].upper(), fill="white", font=("Segoe UI", 8, "bold"))
            else:
                outline_style = "gray" if is_invisible else token_border_color
                dash_style = (2, 2) if is_invisible else ""
                self.create_oval(sx-radius, sy-radius, sx+radius, sy+radius, fill=token_base_color, outline=outline_style, width=2, dash=dash_style)
                self.create_text(sx, sy, text=name[:2].upper(), fill="white", font=("Segoe UI", 8, "bold"))

            if hp_max > 0:
                bar_w = radius * 2.2
                bar_h = 4
                bar_y = sy + radius + 3
                bar_x = sx - (bar_w / 2)
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
                start_x = sx + radius - box_size/2
                start_y = sy - radius - box_size/2
                for i, cond in enumerate(conditions):
                    c_x = start_x + (i * box_size)
                    bg_color = cond_colors.get(cond, "red")
                    fg_color = "black" if bg_color in ["yellow", "white", "green"] else "white"
                    abbrev_map = {"Avvelenato": "Av", "Prono": "P", "Trattenuto": "Tr"}
                    abbrev = abbrev_map.get(cond, cond[:2].capitalize())
                    self.create_rectangle(c_x, start_y, c_x + box_size, start_y + box_size, fill=bg_color, outline="black")
                    self.create_text(c_x + box_size/2, start_y + box_size/2, text=abbrev, fill=fg_color, font=("Arial", 6, "bold"))

        # --- ENVIRONMENTS & COMBAT OVERLAYS ---
        w = self.winfo_width()
        h = self.winfo_height()
        
        # 1. Day/Night Cycle
        hour = getattr(self, "time_hour", 12)
        if hour < 6 or hour > 19:
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

