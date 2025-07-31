# ui_components.py
import tkinter as tk
import base64
from io import BytesIO
from PIL import Image, ImageTk
from common.hex_utils import Hex, HexLayout

class HexMapCanvas(tk.Canvas):
    """Un widget Canvas riutilizzabile per visualizzare e interagire con una mappa esagonale."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#2b2b2b", highlightthickness=0, **kwargs)

        self.zoom_level = 1.0
        self.pan_offset_x, self.pan_offset_y = 0, 0
        self._pan_start_x, self._pan_start_y = 0, 0
        
        self.hex_layout = None
        self.map_background_original = None
        self.map_background_tk = None
        
        self.on_hex_click_callback = None

        self.bind("<MouseWheel>", self._zoom)
        self.bind("<Button-4>", self._zoom)
        self.bind("<Button-5>", self._zoom)
        self.bind("<ButtonPress-2>", self._pan_start)
        self.bind("<B2-Motion>", self._pan_move)
        self.bind("<Button-1>", self._on_canvas_click)

    def set_on_click_callback(self, func):
        self.on_hex_click_callback = func

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
        self.redraw()

    def _on_canvas_click(self, event):
        if not self.hex_layout or not self.on_hex_click_callback: return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        clicked_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
        self.on_hex_click_callback(clicked_hex)

    def update_data(self, map_data, players_data, player_name=""):
        """Salva i dati necessari per il ridisegno."""
        self.map_data = map_data
        self.players_data = players_data
        self.player_name = player_name
        self.redraw()

    def redraw(self):
        self.delete("all")
        if not getattr(self, 'map_data', None):
            self.create_text(self.winfo_width()/2, self.winfo_height()/2, 
                             text="Nessuna mappa caricata.", fill="grey", font=("", 12))
            return

        hex_size = self.map_data.get("hex_size", 30)
        self.hex_layout = HexLayout(size=hex_size, origin=(0, 0))
        
        # Gestione immagine di sfondo (ora interna al componente)
        image_data_b64 = self.map_data.get("bg_image_data")
        if image_data_b64:
            try:
                image_bytes = base64.b64decode(image_data_b64)
                self.map_background_original = Image.open(BytesIO(image_bytes))
            except Exception as e:
                self.map_background_original = None
                print(f"Errore decodifica immagine: {e}")
        
        if self.map_background_original:
            new_width = int(self.map_background_original.width * self.zoom_level)
            new_height = int(self.map_background_original.height * self.zoom_level)
            if new_width > 0 and new_height > 0:
                resized_img = self.map_background_original.resize((new_width, new_height), Image.Resampling.LANCZOS)
                self.map_background_tk = ImageTk.PhotoImage(resized_img)
                self.create_image(self.pan_offset_x, self.pan_offset_y, image=self.map_background_tk, anchor="nw")

        pois_data = {Hex(int(k.split(',')[0]), int(k.split(',')[1])): v for k, v in self.map_data.get("pois", {}).items()}
        border_color = self.map_data.get("hex_border_color", "white")
        
        for q, r in self.map_data.get("hexes", []):
            current_hex = Hex(q, r)
            scaled_corners = [(px * self.zoom_level + self.pan_offset_x, py * self.zoom_level + self.pan_offset_y) 
                              for px, py in self.hex_layout.hex_corners(current_hex)]
            fill_color = "#FFD700" if current_hex in pois_data else ""
            self.create_polygon(scaled_corners, fill=fill_color, outline=border_color, width=max(1, 1/self.zoom_level))
        
        for name, pos in self.players_data.items():
            q, r = pos
            center_x, center_y = self.hex_layout.hex_to_pixel(Hex(q, r))
            screen_x = center_x * self.zoom_level + self.pan_offset_x
            screen_y = center_y * self.zoom_level + self.pan_offset_y
            color = "#90EE90" if name == self.player_name else "#87CEEB"
            radius = 10
            self.create_oval(screen_x-radius, screen_y-radius, screen_x+radius, radius+screen_y, fill=color, outline="white")
            self.create_text(screen_x, screen_y, text=name[:2], fill="black")