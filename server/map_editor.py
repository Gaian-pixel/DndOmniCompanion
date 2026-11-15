# map_editor.py
import tkinter as tk
from common.messagebox import messagebox
from tkinter import simpledialog, filedialog, ttk, colorchooser
import base64
from io import BytesIO
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
        self.walls = set()
        self._extra_walls = []
        self.half_cover = set()
        self.three_quarters_cover = set()
        self.doors = {}
        self._extra_doors = []
        self.lights = {}
        self.traps = {}
        self.loots = {}
        self.teleports = {}
        self.room_pins = {}
        self.spawn_point = None
        self.add_terrain_mode = False
        self.editor_tool = "cells"
        self._drag_painted_hexes = set()
        self._drag_undo_pushed = False
        self._undo_stack = []
        self._redo_stack = []
        self._preserved_map_metadata = {}
        
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

        # Controlli Zoom & Reset
        zoom_frame = ttk.Frame(toolbar)
        zoom_frame.pack(side=tk.LEFT, padx=5)
        ttk.Button(zoom_frame, text="🔍+", width=3, command=self.zoom_in).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_frame, text="🔍-", width=3, command=self.zoom_out).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_frame, text="100%", width=5, command=self.reset_view).pack(side=tk.LEFT, padx=1)
        ttk.Button(zoom_frame, text="⛶ Adatta", command=self.fit_to_window).pack(side=tk.LEFT, padx=1)

        history_frame = ttk.Frame(toolbar)
        history_frame.pack(side=tk.LEFT, padx=5)
        self.undo_button = ttk.Button(history_frame, text="↩️ Annulla", command=self.undo, style="Secondary.TButton")
        self.undo_button.pack(side=tk.LEFT, padx=1)
        self.redo_button = ttk.Button(history_frame, text="↪️ Ripeti", command=self.redo, style="Secondary.TButton")
        self.redo_button.pack(side=tk.LEFT, padx=1)
        ttk.Button(history_frame, text="📐 Ridimensiona", command=self.open_resize_grid_dialog, style="Secondary.TButton").pack(side=tk.LEFT, padx=(6, 1))

        ttk.Button(toolbar, text="Salva Mappa", command=self.save_map, style="Primary.TButton").pack(side=tk.RIGHT, padx=5)

        layers_bar = ttk.Frame(main_frame)
        layers_bar.pack(fill=tk.X, pady=(0, 3))
        ttk.Label(layers_bar, text="Strati & Pennelli:").pack(side=tk.LEFT, padx=(0, 6))

        self.cells_tool_button = ttk.Button(layers_bar, text="⬜ Celle (+/-)", command=lambda: self.set_editor_tool("cells"), style="Primary.TButton")
        self.cells_tool_button.pack(side=tk.LEFT, padx=2)
        self.add_poi_button = ttk.Button(layers_bar, text="📌 POI", command=self.toggle_add_poi_mode, style="Success.TButton")
        self.add_poi_button.pack(side=tk.LEFT, padx=2)
        
        self.add_terrain_button = ttk.Button(layers_bar, text="🌾 Terreno Difficile", command=self.toggle_add_terrain_mode, style="Secondary.TButton")
        self.add_terrain_button.pack(side=tk.LEFT, padx=2)
        self.terrain_type_var = tk.StringVar(value="Fango")
        self.terrain_type_combo = ttk.Combobox(layers_bar, textvariable=self.terrain_type_var, values=["Fango", "Ghiaccio", "Rovi", "Macerie", "Palude"], state="readonly", width=8)
        self.terrain_type_combo.pack(side=tk.LEFT, padx=2)

        self.wall_tool_button = ttk.Button(layers_bar, text="🧱 Muri", command=lambda: self.set_editor_tool("wall"), style="Secondary.TButton")
        self.wall_tool_button.pack(side=tk.LEFT, padx=2)
        self.half_cover_button = ttk.Button(layers_bar, text="🛡️ Copertura 1/2", command=lambda: self.set_editor_tool("half_cover"), style="Secondary.TButton")
        self.half_cover_button.pack(side=tk.LEFT, padx=2)
        self.tq_cover_button = ttk.Button(layers_bar, text="🛡️ Copertura 3/4", command=lambda: self.set_editor_tool("three_quarters_cover"), style="Secondary.TButton")
        self.tq_cover_button.pack(side=tk.LEFT, padx=2)
        self.door_tool_button = ttk.Button(layers_bar, text="🚪 Porte", command=lambda: self.set_editor_tool("door"), style="Secondary.TButton")
        self.door_tool_button.pack(side=tk.LEFT, padx=2)
        self.light_tool_button = ttk.Button(layers_bar, text="💡 Luci", command=lambda: self.set_editor_tool("light"), style="Secondary.TButton")
        self.light_tool_button.pack(side=tk.LEFT, padx=2)
        self.spawn_tool_button = ttk.Button(layers_bar, text="🚩 Spawn", command=lambda: self.set_editor_tool("spawn"), style="Secondary.TButton")
        self.spawn_tool_button.pack(side=tk.LEFT, padx=2)

        layers_bar_extra = ttk.Frame(main_frame)
        layers_bar_extra.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(layers_bar_extra, text="Oggetti & Note:").pack(side=tk.LEFT, padx=(0, 6))
        self.trap_tool_button = ttk.Button(layers_bar_extra, text="💣 Trappole", command=lambda: self.set_editor_tool("trap"), style="Secondary.TButton")
        self.trap_tool_button.pack(side=tk.LEFT, padx=2)
        self.loot_tool_button = ttk.Button(layers_bar_extra, text="💎 Tesori", command=lambda: self.set_editor_tool("loot"), style="Secondary.TButton")
        self.loot_tool_button.pack(side=tk.LEFT, padx=2)
        self.teleport_tool_button = ttk.Button(layers_bar_extra, text="🌀 Portali", command=lambda: self.set_editor_tool("teleport"), style="Secondary.TButton")
        self.teleport_tool_button.pack(side=tk.LEFT, padx=2)
        self.room_pin_tool_button = ttk.Button(layers_bar_extra, text="🏷️ Stanze", command=lambda: self.set_editor_tool("room_pin"), style="Secondary.TButton")
        self.room_pin_tool_button.pack(side=tk.LEFT, padx=2)

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
        self.bind("<Control-z>", self._on_ctrl_undo)
        self.bind("<Control-Z>", self._on_ctrl_undo)
        self.bind("<Control-y>", self._on_ctrl_redo)
        self.bind("<Control-Y>", self._on_ctrl_redo)
        self.bind("<Control-Shift-Z>", self._on_ctrl_redo)
        self.canvas.bind("<ButtonPress-2>", self._pan_start)
        self.canvas.bind("<B2-Motion>", self._pan_move)
        self.canvas.bind("<Alt-ButtonPress-1>", self._pan_start)
        self.canvas.bind("<Alt-B1-Motion>", self._pan_move)
        self.canvas.bind("<B1-Motion>", self._on_canvas_b1_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_b1_release)
        self.canvas.bind("<KeyPress-space>", self._on_space_press)
        self.canvas.bind("<KeyRelease-space>", self._on_space_release)
        self.bind("<KeyPress-space>", self._on_space_press)
        self.bind("<KeyRelease-space>", self._on_space_release)
        self.bind("<Up>", lambda e: self.pan_by(0, 60))
        self.bind("<Down>", lambda e: self.pan_by(0, -60))
        self.bind("<Left>", lambda e: self.pan_by(60, 0))
        self.bind("<Right>", lambda e: self.pan_by(-60, 0))
        def _on_editor_destroy(e=None):
            if e and getattr(e, "widget", None) != self:
                return
            if getattr(self, "_zoom_timer", None) is not None:
                try: self.after_cancel(self._zoom_timer)
                except Exception: pass
                self._zoom_timer = None
        self.bind("<Destroy>", _on_editor_destroy, add="+")

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

    def pan_by(self, dx, dy):
        focus = self.focus_get()
        if focus:
            try:
                cls_name = focus.winfo_class()
                if cls_name in ("Entry", "Text", "TEntry", "Combobox", "TCombobox", "Spinbox", "TSpinbox"):
                    return
            except Exception:
                pass
        self.pan_offset_x += dx
        self.pan_offset_y += dy
        self.canvas.move("all", dx, dy)

    def _on_space_press(self, event=None):
        focus = self.focus_get()
        if focus:
            try:
                cls_name = focus.winfo_class()
                if cls_name in ("Entry", "Text", "TEntry", "Combobox", "TCombobox", "Spinbox", "TSpinbox"):
                    return
            except Exception:
                pass
        if not getattr(self, "_space_held", False):
            self._space_held = True
            try:
                self.canvas.config(cursor="fleur")
            except Exception:
                pass
        return "break"

    def _on_space_release(self, event=None):
        if getattr(self, "_space_held", False):
            self._space_held = False
            try:
                self.canvas.config(cursor="")
            except Exception:
                pass
        return "break"

    def _on_canvas_b1_motion(self, event):
        if getattr(self, "_space_held", False):
            self._pan_move(event)
            return
        tool = getattr(self, "editor_tool", None)
        if not tool:
            if getattr(self, "add_terrain_mode", False):
                tool = "terrain"
        if tool in ("terrain", "wall", "half_cover", "three_quarters_cover") and self.hex_layout:
            wx, wy = self.screen_to_world(event.x, event.y)
            target_hex = self.hex_layout.pixel_to_hex((wx, wy))
            painted = getattr(self, "_drag_painted_hexes", None)
            if not isinstance(painted, set):
                self._drag_painted_hexes = set()
                painted = self._drag_painted_hexes
            if target_hex not in painted:
                painted.add(target_hex)
                if tool == "terrain":
                    self._toggle_terrain_at(wx, wy, silent=True)
                elif tool in ("wall", "half_cover", "three_quarters_cover"):
                    self._toggle_layer_flag_at(wx, wy, tool, silent=True)

    def _on_canvas_b1_release(self, event=None):
        if isinstance(getattr(self, "_drag_painted_hexes", None), set):
            self._drag_painted_hexes.clear()
        self._drag_undo_pushed = False

    def _is_focus_in_text_input(self):
        focus = self.focus_get()
        if not focus:
            return False
        try:
            return focus.winfo_class() in ("Entry", "Text", "TEntry", "Combobox", "TCombobox", "Spinbox", "TSpinbox")
        except Exception:
            return False

    def _on_ctrl_undo(self, event=None):
        if self._is_focus_in_text_input():
            return
        self.undo()
        return "break"

    def _on_ctrl_redo(self, event=None):
        if self._is_focus_in_text_input():
            return
        self.redo()
        return "break"

    def _capture_snapshot(self):
        import copy
        return {
            "grid_hexes": {(h.q, h.r) for h in self.grid_hexes},
            "pois": { (h.q, h.r): copy.deepcopy({k: v for k, v in p.items() if k != "image_tk"} if isinstance(p, dict) else p) for h, p in self.pois.items() },
            "difficult_terrain": { (h.q, h.r): v for h, v in self.difficult_terrain.items() },
            "walls": { (h.q, h.r) for h in self.walls },
            "_extra_walls": copy.deepcopy(getattr(self, "_extra_walls", []) or []),
            "half_cover": { (h.q, h.r) for h in self.half_cover },
            "three_quarters_cover": { (h.q, h.r) for h in self.three_quarters_cover },
            "doors": { (h.q, h.r): copy.deepcopy(v) for h, v in self.doors.items() },
            "_extra_doors": copy.deepcopy(getattr(self, "_extra_doors", []) or []),
            "lights": { (h.q, h.r): copy.deepcopy(v) for h, v in self.lights.items() },
            "traps": { (h.q, h.r): copy.deepcopy(v) for h, v in self.traps.items() },
            "loots": { (h.q, h.r): copy.deepcopy(v) for h, v in self.loots.items() },
            "teleports": { (h.q, h.r): v for h, v in self.teleports.items() },
            "room_pins": { (h.q, h.r): copy.deepcopy(v) for h, v in self.room_pins.items() },
            "spawn_point": list(self.spawn_point) if self.spawn_point is not None else None,
            "current_hex_size": getattr(self, "current_hex_size", 35),
            "current_grid_type": getattr(self, "current_grid_type", "hex"),
        }

    def _restore_snapshot(self, snap):
        import copy
        self.current_hex_size = snap.get("current_hex_size", self.current_hex_size)
        self.current_grid_type = snap.get("current_grid_type", self.current_grid_type)
        if hasattr(self, "grid_type_var"):
            self.grid_type_var.set(self.current_grid_type)
        self.hex_layout = self._create_layout(self.current_hex_size, self.current_grid_type)
        self.grid_hexes = {Hex(q, r) for q, r in snap.get("grid_hexes", ())}
        self.pois = {Hex(k[0], k[1]): copy.deepcopy(v) for k, v in snap.get("pois", {}).items()}
        self.difficult_terrain = {Hex(k[0], k[1]): v for k, v in snap.get("difficult_terrain", {}).items()}
        self.walls = {Hex(q, r) for q, r in snap.get("walls", ())}
        self._extra_walls = copy.deepcopy(snap.get("_extra_walls", []))
        self.half_cover = {Hex(q, r) for q, r in snap.get("half_cover", ())}
        self.three_quarters_cover = {Hex(q, r) for q, r in snap.get("three_quarters_cover", ())}
        self.doors = {Hex(k[0], k[1]): copy.deepcopy(v) for k, v in snap.get("doors", {}).items()}
        self._extra_doors = copy.deepcopy(snap.get("_extra_doors", []))
        self.lights = {Hex(k[0], k[1]): copy.deepcopy(v) for k, v in snap.get("lights", {}).items()}
        self.traps = {Hex(k[0], k[1]): copy.deepcopy(v) for k, v in snap.get("traps", {}).items()}
        self.loots = {Hex(k[0], k[1]): copy.deepcopy(v) for k, v in snap.get("loots", {}).items()}
        self.teleports = {Hex(k[0], k[1]): v for k, v in snap.get("teleports", {}).items()}
        self.room_pins = {Hex(k[0], k[1]): copy.deepcopy(v) for k, v in snap.get("room_pins", {}).items()}
        sp = snap.get("spawn_point")
        self.spawn_point = list(sp) if isinstance(sp, (list, tuple)) and len(sp) >= 2 else None
        self.redraw(high_res=True)

    def _push_undo_state(self):
        self._undo_stack.append(self._capture_snapshot())
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        """Annulla l'ultima modifica della mappa ripristinando lo snapshot precedente."""
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._capture_snapshot())
        if len(self._redo_stack) > 50:
            self._redo_stack.pop(0)
        self._restore_snapshot(self._undo_stack.pop())
        return True

    def redo(self):
        """Ripete una modifica annullata in precedenza."""
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._capture_snapshot())
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
        self._restore_snapshot(self._redo_stack.pop())
        return True

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

        # 2. Griglia e strati tattici
        self.canvas.delete("hex")
        self.canvas.delete("preview")
        self.canvas.delete("layer_overlay")
        self.hex_to_canvas_id.clear()
        self.preview_hex_id = None
        
        if self.hex_layout:
            for h in self.grid_hexes:
                self._draw_single_hex(h)
            self._draw_editor_layer_badges()

    def _draw_editor_layer_badges(self):
        if not self.hex_layout:
            return
        walls = self.walls if isinstance(getattr(self, "walls", None), set) else set()
        half_c = self.half_cover if isinstance(getattr(self, "half_cover", None), set) else set()
        tq_c = self.three_quarters_cover if isinstance(getattr(self, "three_quarters_cover", None), set) else set()
        doors = self.doors if isinstance(getattr(self, "doors", None), dict) else {}
        lights = self.lights if isinstance(getattr(self, "lights", None), dict) else {}
        spawn = getattr(self, "spawn_point", None)

        def _center_screen(h):
            px, py = self.hex_layout.hex_to_pixel(h)
            return px * self.zoom_level + self.pan_offset_x, py * self.zoom_level + self.pan_offset_y

        r_badge = max(5, 9 * self.zoom_level)
        for h in walls:
            sx, sy = _center_screen(h)
            self.canvas.create_text(sx, sy, text="🧱", font=("Segoe UI Emoji", max(8, int(11 * self.zoom_level))), fill="#E2E8F0", tags="layer_overlay")
        for h in half_c:
            sx, sy = _center_screen(h)
            self.canvas.create_text(sx, sy, text="½", font=("Segoe UI", max(8, int(10 * self.zoom_level)), "bold"), fill="#38BDF8", tags="layer_overlay")
        for h in tq_c:
            sx, sy = _center_screen(h)
            self.canvas.create_text(sx, sy, text="¾", font=("Segoe UI", max(8, int(10 * self.zoom_level)), "bold"), fill="#60A5FA", tags="layer_overlay")
        for h, d_info in doors.items():
            sx, sy = _center_screen(h)
            st = d_info.get("state", "closed")
            col = "#22C55E" if st == "open" else ("#EF4444" if st == "locked" else ("#A855F7" if st == "secret" else "#F59E0B"))
            self.canvas.create_oval(sx - r_badge, sy - r_badge, sx + r_badge, sy + r_badge, fill=col, outline="#111827", width=1.5, tags="layer_overlay")
            self.canvas.create_text(sx, sy, text="🚪", font=("Segoe UI Emoji", max(7, int(9 * self.zoom_level))), tags="layer_overlay")
        for h, l_info in lights.items():
            sx, sy = _center_screen(h)
            l_col = l_info.get("color", "#FFD700")
            self.canvas.create_oval(sx - r_badge * 1.3, sy - r_badge * 1.3, sx + r_badge * 1.3, sy + r_badge * 1.3, fill="", outline=l_col, width=2, dash=(3, 2), tags="layer_overlay")
            self.canvas.create_text(sx, sy, text="💡", font=("Segoe UI Emoji", max(8, int(10 * self.zoom_level))), tags="layer_overlay")
        if isinstance(spawn, (list, tuple)) and len(spawn) >= 2:
            sx, sy = _center_screen(Hex(int(spawn[0]), int(spawn[1])))
            self.canvas.create_oval(sx - r_badge * 1.2, sy - r_badge * 1.2, sx + r_badge * 1.2, sy + r_badge * 1.2, fill="#16A34A", outline="#BBF7D0", width=2, tags="layer_overlay")
            self.canvas.create_text(sx, sy, text="🚩", font=("Segoe UI Emoji", max(8, int(10 * self.zoom_level))), tags="layer_overlay")
        for h, t_info in (getattr(self, "traps", None) or {}).items():
            sx, sy = _center_screen(h)
            t_col = "#EF4444" if t_info.get("triggered") else "#F97316"
            self.canvas.create_oval(sx - r_badge, sy - r_badge, sx + r_badge, sy + r_badge, fill="#431407", outline=t_col, width=1.8, tags="layer_overlay")
            self.canvas.create_text(sx, sy, text="💣", font=("Segoe UI Emoji", max(7, int(9 * self.zoom_level))), tags="layer_overlay")
        for h in (getattr(self, "loots", None) or {}):
            sx, sy = _center_screen(h)
            self.canvas.create_rectangle(sx - r_badge, sy - r_badge, sx + r_badge, sy + r_badge, fill="#713F12", outline="#FACC15", width=1.8, tags="layer_overlay")
            self.canvas.create_text(sx, sy, text="💎", font=("Segoe UI Emoji", max(7, int(9 * self.zoom_level))), tags="layer_overlay")
        for h in (getattr(self, "teleports", None) or {}):
            sx, sy = _center_screen(h)
            self.canvas.create_oval(sx - r_badge * 1.1, sy - r_badge * 1.1, sx + r_badge * 1.1, sy + r_badge * 1.1, fill="#0C4A6E", outline="#38BDF8", width=2, tags="layer_overlay")
            self.canvas.create_text(sx, sy, text="🌀", font=("Segoe UI Emoji", max(7, int(9 * self.zoom_level))), tags="layer_overlay")
        for h, pin_info in (getattr(self, "room_pins", None) or {}).items():
            sx, sy = _center_screen(h)
            self.canvas.create_oval(sx - r_badge, sy - r_badge, sx + r_badge, sy + r_badge, fill="#1E1B4B", outline="#A78BFA", width=1.8, tags="layer_overlay")
            self.canvas.create_text(sx, sy, text="🏷️", font=("Segoe UI Emoji", max(7, int(9 * self.zoom_level))), tags="layer_overlay")

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
        walls = self.walls if isinstance(getattr(self, "walls", None), set) else set()
        half_c = self.half_cover if isinstance(getattr(self, "half_cover", None), set) else set()
        tq_c = self.three_quarters_cover if isinstance(getattr(self, "three_quarters_cover", None), set) else set()
        doors = self.doors if isinstance(getattr(self, "doors", None), dict) else {}

        t_style = self.get_terrain_style(h)
        if is_preview:
            style = {"fill": "", "outline": "red", "width": 2}
        elif h in walls:
            style = {"fill": "#0F172A", "stipple": "gray75", "outline": "#64748B", "width": 2}
        elif t_style:
            style = {"fill": t_style["fill"], "stipple": t_style["stipple"], "outline": self.hex_border_color, "width": 1}
        elif h in self.pois:
            # Per i POI coloriamo solo il bordo per non coprire l'immagine sottostante
            normal_fill = "gray50" if not self.base_image_original else ""
            normal_stipple = "gray25" if not self.base_image_original else ""
            style = {"fill": normal_fill, "stipple": normal_stipple, "outline": self.POI_COLOR, "width": 2}
        elif h in tq_c:
            style = {"fill": "#1E3A8A", "stipple": "gray25", "outline": "#60A5FA", "width": 2}
        elif h in half_c:
            style = {"fill": "#0369A1", "stipple": "gray12", "outline": "#38BDF8", "width": 1.5}
        elif h in doors:
            normal_fill = "gray50" if not self.base_image_original else ""
            normal_stipple = "gray25" if not self.base_image_original else ""
            style = {"fill": normal_fill, "stipple": normal_stipple, "outline": "#F59E0B", "width": 2}
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
        for h, hex_id in self.hex_to_canvas_id.items():
            if h in self.pois:
                self.canvas.itemconfig(hex_id, outline=self.POI_COLOR, width=2)
            else:
                self.canvas.itemconfig(hex_id, outline=self.hex_border_color, width=1)

    def load_base_image(self):
        """Carica un'immagine di sfondo e reimposta la vista."""
        maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
        file_path = filedialog.askopenfilename(initialdir=maps_dir, filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if not file_path:
            return
        self.base_image_path = file_path
        self.base_image_original = Image.open(file_path)
        if isinstance(getattr(self, "_preserved_map_metadata", None), dict):
            self._preserved_map_metadata.pop("bg_image_data", None)
            self._preserved_map_metadata.pop("bg_image_hash", None)
        
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
            import copy
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._preserved_map_metadata = copy.deepcopy(data) if isinstance(data, dict) else {}
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

            def _parse_hex_entry(entry):
                if isinstance(entry, (list, tuple)) and len(entry) >= 2 and isinstance(entry[0], int) and isinstance(entry[1], int):
                    return Hex(entry[0], entry[1])
                if isinstance(entry, str) and "," in entry:
                    p = entry.split(",", 1)
                    try:
                        return Hex(int(p[0].strip()), int(p[1].strip()))
                    except (ValueError, TypeError):
                        return None
                return None

            for w in data.get("walls", []) or []:
                wh = _parse_hex_entry(w)
                if wh is not None:
                    self.walls.add(wh)
                else:
                    self._extra_walls.append(copy.deepcopy(w))

            for c in data.get("half_cover", []) or []:
                ch = _parse_hex_entry(c)
                if ch is not None:
                    self.half_cover.add(ch)

            for c in data.get("three_quarters_cover", []) or []:
                ch = _parse_hex_entry(c)
                if ch is not None:
                    self.three_quarters_cover.add(ch)

            for d in data.get("doors", []) or []:
                if isinstance(d, dict) and "q" in d and "r" in d:
                    dh = Hex(int(d["q"]), int(d["r"]))
                    self.doors[dh] = copy.deepcopy(d)
                else:
                    self._extra_doors.append(copy.deepcopy(d))

            for l_item in data.get("lights", []) or []:
                if isinstance(l_item, dict) and "q" in l_item and "r" in l_item:
                    lh = Hex(int(l_item["q"]), int(l_item["r"]))
                    self.lights[lh] = copy.deepcopy(l_item)

            for tr_item in data.get("traps", []) or []:
                if isinstance(tr_item, dict) and "q" in tr_item and "r" in tr_item:
                    th = Hex(int(tr_item["q"]), int(tr_item["r"]))
                    self.traps[th] = copy.deepcopy(tr_item)

            for lt_item in data.get("loots", []) or []:
                if isinstance(lt_item, dict) and "q" in lt_item and "r" in lt_item:
                    lth = Hex(int(lt_item["q"]), int(lt_item["r"]))
                    self.loots[lth] = copy.deepcopy(lt_item)

            raw_teleports = data.get("teleports", {}) or {}
            if isinstance(raw_teleports, dict):
                for tk_coord, dest_map in raw_teleports.items():
                    if isinstance(tk_coord, str) and "," in tk_coord:
                        tp_parts = tk_coord.split(",", 1)
                        try:
                            self.teleports[Hex(int(tp_parts[0].strip()), int(tp_parts[1].strip()))] = str(dest_map)
                        except (ValueError, TypeError):
                            pass
            elif isinstance(raw_teleports, list):
                for tp_item in raw_teleports:
                    if isinstance(tp_item, dict) and "q" in tp_item and "r" in tp_item:
                        dest_val = tp_item.get("target_map") or tp_item.get("dest_map") or tp_item.get("dest") or tp_item.get("map") or ""
                        try:
                            self.teleports[Hex(int(tp_item["q"]), int(tp_item["r"]))] = str(dest_val)
                        except (ValueError, TypeError):
                            pass

            for pin_item in data.get("room_pins", []) or []:
                if isinstance(pin_item, dict) and "q" in pin_item and "r" in pin_item:
                    ph = Hex(int(pin_item["q"]), int(pin_item["r"]))
                    self.room_pins[ph] = copy.deepcopy(pin_item)

            self._undo_stack.clear()
            self._redo_stack.clear()

            sp = data.get("spawn_point")
            if isinstance(sp, (list, tuple)) and len(sp) >= 2:
                self.spawn_point = [int(sp[0]), int(sp[1])]

            base_img = data.get("base_image_path", "")
            if base_img and os.path.exists(base_img):
                self.base_image_path = base_img
                self.base_image_original = Image.open(base_img)
            elif base_img:
                alt_path = os.path.join(maps_dir, os.path.basename(base_img))
                if os.path.exists(alt_path):
                    self.base_image_path = alt_path
                    self.base_image_original = Image.open(alt_path)

            if self.base_image_original is None:
                from common.network_utils import resolve_map_image_data
                b64_img = resolve_map_image_data(data, extra_dirs=[os.path.dirname(file_path), maps_dir])
                if isinstance(b64_img, str) and b64_img:
                    img_obj = Image.open(BytesIO(base64.b64decode(b64_img)))
                    img_obj.load()
                    self.base_image_original = img_obj
                    if base_img:
                        self.base_image_path = base_img

            self.zoom_level = 1.0
            self.pan_offset_x = 0.0
            self.pan_offset_y = 0.0
            self.redraw(high_res=True)
            messagebox.showinfo("Mappa Caricata", f"Caricata mappa con {len(self.grid_hexes)} celle.", parent=self)
        except Exception as e:
            messagebox.showerror("Errore di Caricamento", f"Impossibile caricare la mappa: {e}", parent=self)

    def save_map(self):
        """Salva i dati della mappa (celle, POI, terreni difficili, strati tattici, immagine, scala) in formato JSON."""
        if not self.hex_layout:
            messagebox.showerror("Errore", "Non puoi salvare una mappa senza una scala.", parent=self)
            return
        maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
        file_path = filedialog.asksaveasfilename(initialdir=maps_dir, defaultextension=".json", filetypes=[("Mappe D&D", "*.json")])
        if not file_path:
            return
        
        import copy
        pois_to_save = {
            f"{h.q},{h.r}": ({kp: vp for kp, vp in pdata.items() if kp != "image_tk"} if isinstance(pdata, dict) else pdata)
            for h, pdata in self.pois.items()
        }
        scale_type = self.MAP_SCALE_TYPES.get(self.map_scale_var.get(), "combat")
        diff_terrain_to_save = {f"{h.q},{h.r}": t_type for h, t_type in self.difficult_terrain.items()}
        walls_to_save = [[h.q, h.r] for h in sorted(self.walls, key=lambda x: (x.q, x.r))] + copy.deepcopy(getattr(self, "_extra_walls", []) or [])
        half_cover_to_save = [[h.q, h.r] for h in sorted(self.half_cover, key=lambda x: (x.q, x.r))]
        tq_cover_to_save = [[h.q, h.r] for h in sorted(self.three_quarters_cover, key=lambda x: (x.q, x.r))]
        doors_to_save = [copy.deepcopy(d) for _, d in sorted(self.doors.items(), key=lambda kv: (kv[0].q, kv[0].r))] + copy.deepcopy(getattr(self, "_extra_doors", []) or [])
        lights_to_save = [copy.deepcopy(l) for _, l in sorted(self.lights.items(), key=lambda kv: (kv[0].q, kv[0].r))]
        traps_to_save = [copy.deepcopy(t) for _, t in sorted(self.traps.items(), key=lambda kv: (kv[0].q, kv[0].r))]
        loots_to_save = [copy.deepcopy(l) for _, l in sorted(self.loots.items(), key=lambda kv: (kv[0].q, kv[0].r))]
        teleports_to_save = {f"{h.q},{h.r}": dest for h, dest in sorted(self.teleports.items(), key=lambda kv: (kv[0].q, kv[0].r))}
        room_pins_to_save = [copy.deepcopy(p) for _, p in sorted(self.room_pins.items(), key=lambda kv: (kv[0].q, kv[0].r))]
        
        hex_size = getattr(self, "current_hex_size", 60)
        grid_type = self.grid_type_var.get() if hasattr(self, "grid_type_var") else "hex"
        
        map_data = copy.deepcopy(getattr(self, "_preserved_map_metadata", {}) or {})
        map_data.update({
            "base_image_path": self.base_image_path,
            "hex_size": hex_size,
            "grid_type": grid_type,
            "map_scale_type": scale_type,
            "hex_border_color": self.hex_border_color,
            "hexes": [[h.q, h.r] for h in self.grid_hexes],
            "pois": pois_to_save,
            "difficult_terrain": diff_terrain_to_save,
            "walls": walls_to_save,
            "half_cover": half_cover_to_save,
            "three_quarters_cover": tq_cover_to_save,
            "doors": doors_to_save,
            "lights": lights_to_save,
            "traps": traps_to_save,
            "loots": loots_to_save,
            "teleports": teleports_to_save,
            "room_pins": room_pins_to_save,
        })
        if self.spawn_point is not None:
            map_data["spawn_point"] = list(self.spawn_point)
        else:
            map_data.pop("spawn_point", None)
        if not map_data.get("bg_image_data") and self.base_image_original is not None:
            if not self.base_image_path or not os.path.exists(self.base_image_path):
                buf = BytesIO()
                self.base_image_original.save(buf, format="PNG")
                map_data["bg_image_data"] = base64.b64encode(buf.getvalue()).decode("utf-8")
        self._preserved_map_metadata = copy.deepcopy(map_data)
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
            self._push_undo_state()
            self.grid_hexes.add(target_hex)
            self._draw_single_hex(target_hex)

    def _delete_hex_at(self, wx, wy):
        """Cancella una cella nella posizione del mondo specificata."""
        if not self.hex_layout:
            return

        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex in self.grid_hexes:
            self._push_undo_state()
            self.pois.pop(target_hex, None)
            self.difficult_terrain.pop(target_hex, None)
            self.walls.discard(target_hex)
            self.half_cover.discard(target_hex)
            self.three_quarters_cover.discard(target_hex)
            self.doors.pop(target_hex, None)
            self.lights.pop(target_hex, None)
            self.traps.pop(target_hex, None)
            self.loots.pop(target_hex, None)
            self.teleports.pop(target_hex, None)
            self.room_pins.pop(target_hex, None)
            if isinstance(self.spawn_point, (list, tuple)) and len(self.spawn_point) >= 2:
                if self.spawn_point[0] == target_hex.q and self.spawn_point[1] == target_hex.r:
                    self.spawn_point = None
            canvas_id = self.hex_to_canvas_id.pop(target_hex, None)
            if canvas_id:
                self.canvas.delete(canvas_id)
            self.grid_hexes.remove(target_hex)
            self._draw_editor_layer_badges_refresh()

    def _draw_editor_layer_badges_refresh(self):
        self.canvas.delete("layer_overlay")
        self._draw_editor_layer_badges()

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
        self._push_undo_state()
        self.pois[target_hex] = {"title": title, "caption": caption or ""}
        hex_id = self.hex_to_canvas_id.get(target_hex)
        if hex_id:
            normal_fill = "gray50" if not self.base_image_original else ""
            normal_stipple = "gray25" if not self.base_image_original else ""
            self.canvas.itemconfig(hex_id, fill=normal_fill, outline=self.POI_COLOR, width=2, stipple=normal_stipple)
            self.canvas.addtag_withtag("poi", hex_id)
        self.toggle_add_poi_mode()

    def _toggle_terrain_at(self, wx, wy, silent=False):
        """Imposta o rimuove terreno difficile nella cella selezionata."""
        if not self.hex_layout:
            return
        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex not in self.grid_hexes:
            if not silent:
                messagebox.showwarning("Azione non valida", "Puoi impostare terreno difficile solo su esagoni esistenti.", parent=self)
            return

        if not getattr(self, "_drag_undo_pushed", False):
            self._push_undo_state()
            self._drag_undo_pushed = True
        t_type = self.terrain_type_var.get().lower()
        if target_hex in self.difficult_terrain and self.difficult_terrain[target_hex] == t_type:
            del self.difficult_terrain[target_hex]
            hex_id = self.hex_to_canvas_id.get(target_hex)
            if hex_id:
                empty_fill = "gray50" if not self.base_image_original else ""
                empty_stipple = "gray25" if not self.base_image_original else ""
                self.canvas.itemconfig(hex_id, fill=empty_fill, stipple=empty_stipple)
        else:
            self.difficult_terrain[target_hex] = t_type
            t_style = self.get_terrain_style(target_hex)
            hex_id = self.hex_to_canvas_id.get(target_hex)
            if hex_id and t_style:
                self.canvas.itemconfig(hex_id, fill=t_style["fill"], stipple=t_style["stipple"])

    def _refresh_single_hex(self, target_hex):
        old_id = self.hex_to_canvas_id.pop(target_hex, None)
        if old_id:
            self.canvas.delete(old_id)
        self._draw_single_hex(target_hex)
        self._draw_editor_layer_badges_refresh()

    def _toggle_layer_flag_at(self, wx, wy, layer_name, silent=False):
        """Attiva o disattiva uno strato tattico (muro o copertura) su una cella."""
        if not self.hex_layout:
            return
        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex not in self.grid_hexes:
            if not silent:
                messagebox.showwarning("Azione non valida", "Puoi modificare gli strati tattici solo su celle esistenti.", parent=self)
            return

        layer_map = {
            "wall": self.walls,
            "half_cover": self.half_cover,
            "three_quarters_cover": self.three_quarters_cover,
        }
        target_set = layer_map.get(layer_name)
        if target_set is None:
            return
        if not getattr(self, "_drag_undo_pushed", False):
            self._push_undo_state()
            self._drag_undo_pushed = True
        if target_hex in target_set:
            target_set.remove(target_hex)
        else:
            for other_name, other_set in layer_map.items():
                if other_name != layer_name:
                    other_set.discard(target_hex)
            target_set.add(target_hex)
        self._refresh_single_hex(target_hex)

    def _toggle_door_at(self, wx, wy):
        """Cicla stato porta su una cella: closed -> open -> locked -> secret -> rimossa."""
        if not self.hex_layout:
            return
        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex not in self.grid_hexes:
            messagebox.showwarning("Azione non valida", "Puoi inserire porte solo su celle esistenti.", parent=self)
            return

        self._push_undo_state()
        states = ["closed", "open", "locked", "secret"]
        existing = self.doors.get(target_hex)
        if existing is None:
            self.doors[target_hex] = {"q": target_hex.q, "r": target_hex.r, "state": "closed", "dc": 15}
        else:
            cur_state = existing.get("state", "closed")
            if cur_state in states and states.index(cur_state) + 1 < len(states):
                existing["state"] = states[states.index(cur_state) + 1]
            else:
                self.doors.pop(target_hex, None)
        self._refresh_single_hex(target_hex)

    def _toggle_light_at(self, wx, wy):
        """Cicla una sorgente luminosa sulla cella: Torcia (4/4) -> Lanterna (6/6) -> rimossa."""
        if not self.hex_layout:
            return
        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex not in self.grid_hexes:
            messagebox.showwarning("Azione non valida", "Puoi inserire luci solo su celle esistenti.", parent=self)
            return

        self._push_undo_state()
        existing = self.lights.get(target_hex)
        if existing is None:
            self.lights[target_hex] = {"q": target_hex.q, "r": target_hex.r, "bright": 4, "dim": 4, "color": "#FFD700", "label": "Torcia"}
        elif existing.get("bright", 4) <= 4:
            self.lights[target_hex] = {"q": target_hex.q, "r": target_hex.r, "bright": 6, "dim": 6, "color": "#F59E0B", "label": "Lanterna"}
        else:
            self.lights.pop(target_hex, None)
        self._refresh_single_hex(target_hex)

    def _set_spawn_at(self, wx, wy):
        """Imposta o rimuove il punto di spawn del party sulla cella cliccata."""
        if not self.hex_layout:
            return
        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex not in self.grid_hexes:
            messagebox.showwarning("Azione non valida", "Puoi impostare lo spawn solo su celle esistenti.", parent=self)
            return

        self._push_undo_state()
        if isinstance(self.spawn_point, (list, tuple)) and len(self.spawn_point) >= 2 and self.spawn_point[0] == target_hex.q and self.spawn_point[1] == target_hex.r:
            self.spawn_point = None
        else:
            self.spawn_point = [target_hex.q, target_hex.r]
        self._draw_editor_layer_badges_refresh()

    def _toggle_trap_at(self, wx, wy, silent=False, name="Trappola a Trabocchetto", dc=13, damage="2d10", damage_type="Perforante"):
        """Aggiunge o rimuove una trappola sulla cella selezionata."""
        if not self.hex_layout:
            return
        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex not in self.grid_hexes:
            if not silent:
                messagebox.showwarning("Azione non valida", "Puoi posizionare trappole solo su celle esistenti.", parent=self)
            return
        if target_hex in self.traps:
            self._push_undo_state()
            self.traps.pop(target_hex, None)
            self._refresh_single_hex(target_hex)
            return
        if not silent:
            entered = simpledialog.askstring("Nuova Trappola", "Nome della trappola:", initialvalue=name, parent=self)
            if not entered:
                return
            name = entered.strip()
            entered_dc = simpledialog.askinteger("Nuova Trappola", "CD Percezione / Salvezza:", initialvalue=dc, minvalue=5, maxvalue=30, parent=self)
            if entered_dc is not None:
                dc = entered_dc
            entered_dmg = simpledialog.askstring("Nuova Trappola", "Dadi danno (es. 2d10):", initialvalue=damage, parent=self)
            if entered_dmg:
                damage = entered_dmg.strip()
        self._push_undo_state()
        self.traps[target_hex] = {
            "q": target_hex.q,
            "r": target_hex.r,
            "name": name,
            "dc": int(dc),
            "damage": str(damage),
            "damage_type": damage_type,
            "hidden": True,
            "triggered": False,
            "secret": True,
        }
        self._refresh_single_hex(target_hex)

    def _toggle_loot_at(self, wx, wy, silent=False, item_name="Forziere del Tesoro", gold=25):
        """Aggiunge o rimuove un tesoro/bottino sulla cella selezionata."""
        if not self.hex_layout:
            return
        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex not in self.grid_hexes:
            if not silent:
                messagebox.showwarning("Azione non valida", "Puoi posizionare tesori solo su celle esistenti.", parent=self)
            return
        if target_hex in self.loots:
            self._push_undo_state()
            self.loots.pop(target_hex, None)
            self._refresh_single_hex(target_hex)
            return
        if not silent:
            entered = simpledialog.askstring("Nuovo Tesoro", "Nome oggetto o contenitore:", initialvalue=item_name, parent=self)
            if not entered:
                return
            item_name = entered.strip()
            entered_gp = simpledialog.askinteger("Nuovo Tesoro", "Monete d'oro (MO):", initialvalue=gold, minvalue=0, maxvalue=100000, parent=self)
            if entered_gp is not None:
                gold = entered_gp
        self._push_undo_state()
        self.loots[target_hex] = {
            "q": target_hex.q,
            "r": target_hex.r,
            "item": item_name,
            "items": [{"name": item_name, "qty": 1}],
            "gold": int(gold),
            "hidden": False,
        }
        self._refresh_single_hex(target_hex)

    def _toggle_teleport_at(self, wx, wy, silent=False, dest_map="taverna.json"):
        """Aggiunge o rimuove un portale di teletrasporto mappa sulla cella selezionata."""
        if not self.hex_layout:
            return
        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex not in self.grid_hexes:
            if not silent:
                messagebox.showwarning("Azione non valida", "Puoi posizionare portali solo su celle esistenti.", parent=self)
            return
        if target_hex in self.teleports:
            self._push_undo_state()
            self.teleports.pop(target_hex, None)
            self._refresh_single_hex(target_hex)
            return
        if not silent:
            entered = simpledialog.askstring("Nuovo Portale", "Nome file mappa di destinazione (in maps/):", initialvalue=dest_map, parent=self)
            if not entered:
                return
            dest_map = os.path.basename(entered.strip())
        if not dest_map:
            return
        self._push_undo_state()
        self.teleports[target_hex] = dest_map
        self._refresh_single_hex(target_hex)

    def _toggle_room_pin_at(self, wx, wy, silent=False, title="Stanza", read_aloud=""):
        """Aggiunge o rimuove una spilla descrittiva di stanza sulla cella selezionata."""
        if not self.hex_layout:
            return
        target_hex = self.hex_layout.pixel_to_hex((wx, wy))
        if target_hex not in self.grid_hexes:
            if not silent:
                messagebox.showwarning("Azione non valida", "Puoi inserire spille stanza solo su celle esistenti.", parent=self)
            return
        if target_hex in self.room_pins:
            self._push_undo_state()
            self.room_pins.pop(target_hex, None)
            self._refresh_single_hex(target_hex)
            return
        if not silent:
            entered = simpledialog.askstring("Nuova Spilla Stanza", "Titolo stanza:", initialvalue=title, parent=self)
            if not entered:
                return
            title = entered.strip()
            entered_read = simpledialog.askstring("Nuova Spilla Stanza", "Testo da leggere ad alta voce (opzionale):", initialvalue=read_aloud, parent=self)
            if entered_read is not None:
                read_aloud = entered_read.strip()
        self._push_undo_state()
        self.room_pins[target_hex] = {
            "id": f"pin_{target_hex.q}_{target_hex.r}",
            "q": target_hex.q,
            "r": target_hex.r,
            "title": title,
            "read_aloud": read_aloud,
            "dm_notes": "",
        }
        self._refresh_single_hex(target_hex)

    def set_editor_tool(self, tool_name):
        """Seleziona in modo mutuamente esclusivo il pennello attivo nell'editor mappe."""
        if getattr(self, "editor_tool", "cells") == tool_name and tool_name != "cells":
            tool_name = "cells"
        self.editor_tool = tool_name
        self.add_poi_mode = (tool_name == "poi")
        self.add_terrain_mode = (tool_name == "terrain")
        button_map = {
            "cells": ("cells_tool_button", "Secondary.TButton"),
            "poi": ("add_poi_button", "Success.TButton"),
            "terrain": ("add_terrain_button", "Secondary.TButton"),
            "wall": ("wall_tool_button", "Secondary.TButton"),
            "half_cover": ("half_cover_button", "Secondary.TButton"),
            "three_quarters_cover": ("tq_cover_button", "Secondary.TButton"),
            "door": ("door_tool_button", "Secondary.TButton"),
            "light": ("light_tool_button", "Secondary.TButton"),
            "spawn": ("spawn_tool_button", "Secondary.TButton"),
            "trap": ("trap_tool_button", "Secondary.TButton"),
            "loot": ("loot_tool_button", "Secondary.TButton"),
            "teleport": ("teleport_tool_button", "Secondary.TButton"),
            "room_pin": ("room_pin_tool_button", "Secondary.TButton"),
        }
        for key, (attr_name, default_style) in button_map.items():
            btn = getattr(self, attr_name, None)
            if btn is not None and hasattr(btn, "config"):
                btn.config(style="Primary.TButton" if key == tool_name else default_style)
        if hasattr(self, "config"):
            try:
                self.config(cursor="crosshair" if tool_name != "cells" else "")
            except Exception:
                pass

    def on_canvas_left_click(self, event):
        if getattr(self, "_space_held", False):
            self._pan_start(event)
            return
        self._drag_undo_pushed = False
        wx, wy = self.screen_to_world(event.x, event.y)
        tool = getattr(self, "editor_tool", "cells")
        if self.add_poi_mode or tool == "poi":
            self._add_poi_at(wx, wy)
        elif getattr(self, "add_terrain_mode", False) or tool == "terrain":
            if self.hex_layout:
                self._drag_painted_hexes = {self.hex_layout.pixel_to_hex((wx, wy))}
            self._toggle_terrain_at(wx, wy)
        elif tool in ("wall", "half_cover", "three_quarters_cover"):
            if self.hex_layout:
                self._drag_painted_hexes = {self.hex_layout.pixel_to_hex((wx, wy))}
            self._toggle_layer_flag_at(wx, wy, tool)
        elif tool == "door":
            self._toggle_door_at(wx, wy)
        elif tool == "light":
            self._toggle_light_at(wx, wy)
        elif tool == "spawn":
            self._set_spawn_at(wx, wy)
        elif tool == "trap":
            self._toggle_trap_at(wx, wy)
        elif tool == "loot":
            self._toggle_loot_at(wx, wy)
        elif tool == "teleport":
            self._toggle_teleport_at(wx, wy)
        elif tool == "room_pin":
            self._toggle_room_pin_at(wx, wy)
        else:
            self._delete_hex_at(wx, wy)

    def on_canvas_right_click(self, event):
        wx, wy = self.screen_to_world(event.x, event.y)
        self._add_hex_at(wx, wy)

    def on_canvas_motion(self, event):
        self.handle_poi_hover(event)
        tool = getattr(self, "editor_tool", "cells")
        if self.hex_layout and tool == "cells" and not self.add_poi_mode and not getattr(self, "add_terrain_mode", False):
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
        self.set_editor_tool("cells" if getattr(self, "add_poi_mode", False) else "poi")

    def toggle_add_terrain_mode(self):
        self.set_editor_tool("cells" if getattr(self, "add_terrain_mode", False) else "terrain")

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

    def _remap_hex_coord(self, h, old_layout, new_layout):
        if old_layout is None or new_layout is None:
            return h
        px, py = old_layout.hex_to_pixel(h)
        return new_layout.pixel_to_hex((px, py))

    def on_grid_type_selected(self, event=None):
        """Passaggio non distruttivo tra tipi di griglia rimappando gli strati tramite centri pixel."""
        new_grid_type = self.grid_type_var.get()
        old_grid_type = getattr(self, "current_grid_type", "hex")
        if old_grid_type == new_grid_type:
            return

        self._push_undo_state()
        old_layout = self.hex_layout
        self.current_grid_type = new_grid_type
        if hasattr(self, "current_hex_size") and self.current_hex_size:
            new_layout = self._create_layout(self.current_hex_size, new_grid_type)
            self.hex_layout = new_layout
            if old_layout is not None and new_layout is not None:
                self.pois = {self._remap_hex_coord(h, old_layout, new_layout): v for h, v in self.pois.items()}
                self.difficult_terrain = {self._remap_hex_coord(h, old_layout, new_layout): v for h, v in self.difficult_terrain.items()}
                self.walls = {self._remap_hex_coord(h, old_layout, new_layout) for h in self.walls}
                self.half_cover = {self._remap_hex_coord(h, old_layout, new_layout) for h in self.half_cover}
                self.three_quarters_cover = {self._remap_hex_coord(h, old_layout, new_layout) for h in self.three_quarters_cover}

                remapped_doors = {}
                for h, d in self.doors.items():
                    nh = self._remap_hex_coord(h, old_layout, new_layout)
                    dc = dict(d)
                    dc["q"], dc["r"] = nh.q, nh.r
                    remapped_doors[nh] = dc
                self.doors = remapped_doors

                remapped_lights = {}
                for h, l_info in self.lights.items():
                    nh = self._remap_hex_coord(h, old_layout, new_layout)
                    lc = dict(l_info)
                    lc["q"], lc["r"] = nh.q, nh.r
                    remapped_lights[nh] = lc
                self.lights = remapped_lights

                remapped_traps = {}
                for h, t_info in self.traps.items():
                    nh = self._remap_hex_coord(h, old_layout, new_layout)
                    tc = dict(t_info)
                    tc["q"], tc["r"] = nh.q, nh.r
                    remapped_traps[nh] = tc
                self.traps = remapped_traps

                remapped_loots = {}
                for h, lt_info in self.loots.items():
                    nh = self._remap_hex_coord(h, old_layout, new_layout)
                    ltc = dict(lt_info)
                    ltc["q"], ltc["r"] = nh.q, nh.r
                    remapped_loots[nh] = ltc
                self.loots = remapped_loots

                self.teleports = {self._remap_hex_coord(h, old_layout, new_layout): dest for h, dest in self.teleports.items()}

                remapped_pins = {}
                for h, p_info in self.room_pins.items():
                    nh = self._remap_hex_coord(h, old_layout, new_layout)
                    pc = dict(p_info)
                    pc["q"], pc["r"] = nh.q, nh.r
                    remapped_pins[nh] = pc
                self.room_pins = remapped_pins

                if isinstance(self.spawn_point, (list, tuple)) and len(self.spawn_point) >= 2:
                    ns = self._remap_hex_coord(Hex(int(self.spawn_point[0]), int(self.spawn_point[1])), old_layout, new_layout)
                    self.spawn_point = [ns.q, ns.r]

            if self.base_image_original:
                self.generate_auto_grid(silent=True, preserve_layers=True)
            else:
                if old_layout is not None and new_layout is not None:
                    self.grid_hexes = {self._remap_hex_coord(h, old_layout, new_layout) for h in self.grid_hexes}
                self.redraw(high_res=True)

    def open_resize_grid_dialog(self):
        """Chiede nuove dimensioni (colonne x righe) e ridimensiona la griglia."""
        cols = simpledialog.askinteger("Ridimensiona Griglia", "Numero di colonne (X):", initialvalue=20, minvalue=1, maxvalue=200, parent=self)
        if not cols:
            return
        rows = simpledialog.askinteger("Ridimensiona Griglia", "Numero di righe (Y):", initialvalue=15, minvalue=1, maxvalue=200, parent=self)
        if not rows:
            return
        self.resize_grid(cols, rows)

    def resize_grid(self, cols: int, rows: int, push_undo: bool = True):
        """Rigenera la griglia alle dimensioni rettangolari indicate mantenendo gli strati interni ai confini."""
        cols = max(1, int(cols))
        rows = max(1, int(rows))
        grid_type = self.grid_type_var.get() if hasattr(self, "grid_type_var") else getattr(self, "current_grid_type", "hex")
        if not self.hex_layout:
            self.hex_layout = self._create_layout(getattr(self, "current_hex_size", 35), grid_type)
        if push_undo:
            self._push_undo_state()
        self.canvas.delete("hex")
        self.canvas.delete("preview")
        self.canvas.delete("layer_overlay")
        self.grid_hexes.clear()
        self.hex_to_canvas_id.clear()
        self.preview_hex_id = None
        if grid_type in ("square", "none", "gridless"):
            for q in range(cols):
                for r in range(rows):
                    self.grid_hexes.add(Hex(q, r))
        else:
            for row in range(rows):
                for col in range(cols):
                    self.grid_hexes.add(Hex(col - (row // 2), row))
        # Mantieni solo gli elementi di strato ricompresi nella nuova griglia
        self.pois = {h: v for h, v in self.pois.items() if h in self.grid_hexes}
        self.difficult_terrain = {h: v for h, v in self.difficult_terrain.items() if h in self.grid_hexes}
        self.walls = {h for h in self.walls if h in self.grid_hexes}
        self.half_cover = {h for h in self.half_cover if h in self.grid_hexes}
        self.three_quarters_cover = {h for h in self.three_quarters_cover if h in self.grid_hexes}
        self.doors = {h: v for h, v in self.doors.items() if h in self.grid_hexes}
        self.lights = {h: v for h, v in self.lights.items() if h in self.grid_hexes}
        self.traps = {h: v for h, v in self.traps.items() if h in self.grid_hexes}
        self.loots = {h: v for h, v in self.loots.items() if h in self.grid_hexes}
        self.teleports = {h: v for h, v in self.teleports.items() if h in self.grid_hexes}
        self.room_pins = {h: v for h, v in self.room_pins.items() if h in self.grid_hexes}
        if isinstance(self.spawn_point, (list, tuple)) and len(self.spawn_point) >= 2:
            if Hex(int(self.spawn_point[0]), int(self.spawn_point[1])) not in self.grid_hexes:
                self.spawn_point = None
        self.redraw(high_res=True)

    def generate_auto_grid(self, silent=False, preserve_layers=False):
        """Genera automaticamente le celle su tutta l'estensione dell'immagine caricata combaciando perfettamente col perimetro."""
        if not self.base_image_original or not self.hex_layout:
            return
        width = self.base_image_original.width
        height = self.base_image_original.height
        
        grid_type = self.grid_type_var.get() if hasattr(self, "grid_type_var") else "hex"
        is_rect_grid = grid_type in ("square", "none", "gridless")
        
        if is_rect_grid:
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

        self._clear_grid(preserve_layers=preserve_layers)
        
        if is_rect_grid:
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

    def _clear_grid(self, preserve_layers=False):
        self.canvas.delete("hex")
        self.canvas.delete("preview")
        self.canvas.delete("layer_overlay")
        self.grid_hexes.clear()
        self.hex_to_canvas_id.clear()
        self.preview_hex_id = None
        if not preserve_layers:
            self.pois.clear()
            self.difficult_terrain.clear()
            self.walls.clear()
            self._extra_walls.clear()
            self.half_cover.clear()
            self.three_quarters_cover.clear()
            self.doors.clear()
            self._extra_doors.clear()
            self.lights.clear()
            self.traps.clear()
            self.loots.clear()
            self.teleports.clear()
            self.room_pins.clear()
            self.spawn_point = None
