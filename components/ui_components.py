# ui_components.py
import tkinter as tk
import base64
import math
from io import BytesIO
from PIL import Image, ImageTk, ImageDraw
from common.hex_utils import (
    Hex, HexLayout, SquareLayout, hex_distance, grid_distance,
    get_sphere_hexes, get_cone_hexes, get_line_hexes, get_visible_hexes
)
from common.i18n import _t, get_language

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
        self._ruler_text_bg_id = None
        self.ruler_mode = False
        self.pen_mode = False
        self.pen_color = "red"
        self.brush_radius = 0
        self.fow_enabled = False
        self.visible_hexes = set()

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
        self.bind("<Leave>", lambda e: self._update_hover_tooltip(e, None))
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
                    self.on_draw_callback(world_points, getattr(self, "pen_color", "red"))
            self.delete("temp_draw")
            del self._current_drawing

    def toggle_pen_mode(self, enabled=None):
        if enabled is None:
            self.pen_mode = not getattr(self, "pen_mode", False)
        else:
            self.pen_mode = bool(enabled)
        return self.pen_mode

    def clear_drawings(self):
        self.drawn_lines = []
        self.delete("temp_draw")
        self.redraw()

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

    def toggle_ruler_mode(self):
        self.ruler_mode = not getattr(self, "ruler_mode", False)
        if not self.ruler_mode:
            self.clear_ruler()
            try:
                self.config(cursor="")
            except Exception:
                pass
        else:
            try:
                self.config(cursor="tcross")
            except Exception:
                pass
        self.redraw()
        return self.ruler_mode

    def clear_ruler(self):
        self._ruler_start_hex = None
        self._ruler_current_hex = None
        self._ruler_pinned_start = None
        self._ruler_pinned_end = None
        self.delete("ruler_overlay")
        if getattr(self, '_ruler_line_id', None):
            self.delete(self._ruler_line_id)
            self._ruler_line_id = None
        if getattr(self, '_ruler_text_id', None):
            self.delete(self._ruler_text_id)
            self._ruler_text_id = None
        if getattr(self, '_ruler_text_bg_id', None):
            self.delete(self._ruler_text_bg_id)
            self._ruler_text_bg_id = None

    def _on_canvas_click(self, event):
        if getattr(self, "pen_mode", False):
            self._on_draw_start(event)
            return

        # 1. Controlla click su Carousel di Iniziativa
        if getattr(self, '_initiative_ribbon_bboxes', None):
            for bx1, by1, bx2, by2, bname in self._initiative_ribbon_bboxes:
                if bx1 <= event.x <= bx2 and by1 <= event.y <= by2:
                    self.center_on_token(bname)
                    return

        # 2. Controlla click su Controlli HUD Galleggianti (In basso a sinistra)
        if getattr(self, '_hud_control_bboxes', None):
            for bx1, by1, bx2, by2, action_key in self._hud_control_bboxes:
                if bx1 <= event.x <= bx2 and by1 <= event.y <= by2:
                    if action_key == "center":
                        self.center_view()
                    elif action_key == "zoom_in":
                        self.zoom_in()
                    elif action_key == "zoom_out":
                        self.zoom_out()
                    elif action_key == "ruler":
                        self.toggle_ruler_mode()
                    return

        # 3. Controlla click su Pillola Clima & Notte (In alto a destra)
        if getattr(self, '_weather_badge_bbox', None):
            wbx1, wby1, wbx2, wby2 = self._weather_badge_bbox
            if wbx1 <= event.x <= wbx2 and wby1 <= event.y <= wby2:
                return

        if not self.hex_layout: return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        clicked_hex = self.hex_layout.pixel_to_hex((world_x, world_y))

        if getattr(self, "ruler_mode", False):
            if self._ruler_start_hex is None:
                self._ruler_pinned_start = None
                self._ruler_pinned_end = None
                self._ruler_start_hex = clicked_hex
                self._ruler_current_hex = clicked_hex
                self._draw_ruler_between(clicked_hex, clicked_hex)
            else:
                self._ruler_pinned_start = self._ruler_start_hex
                self._ruler_pinned_end = clicked_hex
                self._on_ruler_drag(event)
                self._ruler_start_hex = None
                self._ruler_current_hex = None
            return

        if not self.on_hex_click_callback: return
        
        self.dragging_token_name = None
        self._drag_start_hex = None
        if getattr(self, 'players_data', None):
            for name, pdata in self.players_data.items():
                pos = pdata.get('position', [0, 0]) if isinstance(pdata, dict) else pdata
                if Hex(*pos) == clicked_hex:
                    self.dragging_token_name = name
                    self._drag_start_hex = clicked_hex
                    break
        
        self._last_clicked_hex = clicked_hex
        self.on_hex_click_callback(clicked_hex)

    def _on_canvas_drag(self, event):
        if getattr(self, "pen_mode", False):
            self._on_draw_move(event)
            return
        if getattr(self, "ruler_mode", False) and self._ruler_start_hex:
            self._on_ruler_drag(event)
            return
        if getattr(self, 'dragging_token_name', None) and getattr(self, '_drag_start_hex', None) and self.hex_layout:
            self.delete('ghost_token')
            self.delete('ghost_path')
            
            world_x = (event.x - self.pan_offset_x) / self.zoom_level
            world_y = (event.y - self.pan_offset_y) / self.zoom_level
            curr_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
            
            start_wx, start_wy = self.hex_layout.hex_to_pixel(self._drag_start_hex)
            start_sx = start_wx * self.zoom_level + self.pan_offset_x
            start_sy = start_wy * self.zoom_level + self.pan_offset_y
            
            target_wx, target_wy = self.hex_layout.hex_to_pixel(curr_hex)
            target_sx = target_wx * self.zoom_level + self.pan_offset_x
            target_sy = target_wy * self.zoom_level + self.pan_offset_y
            
            dist_hex = self._drag_start_hex.distance(curr_hex)
            from common.i18n import speed_to_hexes, format_distance_hexes, get_map_scale_info
            active_map_data = getattr(self, "map_data", None)
            scale_info = get_map_scale_info(active_map_data)
            dist_str = format_distance_hexes(dist_hex, map_data=active_map_data, include_travel_time=True)
            
            pdata = self.players_data.get(self.dragging_token_name, {})
            base_speed = 30
            speed_unit = None
            conds = []
            if isinstance(pdata, dict):
                base_speed = pdata.get('speed', 30) or 30
                speed_unit = pdata.get('speed_unit')
                conds = pdata.get('conditions', [])
            is_dashed = ("Scatto" in conds or "Dash" in conds)
            base_hexes = speed_to_hexes(base_speed, speed_unit)
            max_hexes = base_hexes * 2 if is_dashed else base_hexes
            
            is_tactical_scale = (scale_info.get("scale_type") == "combat")
            is_over = (dist_hex > max_hexes) if is_tactical_scale else False
            path_color = "#EF4444" if is_over else ("#3B82F6" if not is_tactical_scale else "#10B981")
            
            # 1. Traccia scia di movimento tratteggiata (Ghost Path)
            self.create_line(start_sx, start_sy, target_sx, target_sy, fill=path_color, width=3, dash=(6, 4), tags='ghost_path')
            
            # 2. Ghost Token di destinazione
            scaled_r = max(10, int(13 * self.zoom_level))
            self.create_oval(target_sx - scaled_r, target_sy - scaled_r, target_sx + scaled_r, target_sy + scaled_r,
                             fill="#111827", outline=path_color, width=2, dash=(3, 2), tags='ghost_path')
            self.create_text(target_sx, target_sy, text=self.dragging_token_name[:2].upper(),
                             fill=path_color, font=("Segoe UI", max(7, int(9 * self.zoom_level)), "bold"), tags='ghost_path')
            
            # 3. Floating Pill Badge con distanza live nella scala della mappa e unità scelta
            dash_alert = f" • [⚠️ {_t('action_dash')}]" if is_over else ""
            badge_text = f"👣 {dist_str} ({dist_hex} hex){dash_alert}"
            badge_y = target_sy - scaled_r - 16
            bw = len(badge_text) * 3.6 + 12
            bx1, bx2 = target_sx - bw, target_sx + bw
            by1, by2 = badge_y - 10, badge_y + 10
            self.create_rectangle(bx1, by1, bx2, by2, fill="#0F172A", outline=path_color, width=1.5, tags='ghost_path')
            self.create_text(target_sx, badge_y, text=badge_text, fill="#FFFFFF" if not is_over else "#FCA5A5",
                             font=("Segoe UI", 9, "bold"), tags='ghost_path')
            return

    def _on_canvas_release(self, event):
        if getattr(self, "pen_mode", False):
            self._on_draw_end(event)
            return
        self.delete('ghost_token')
        self.delete('ghost_path')
        if getattr(self, 'dragging_token_name', None):
            if self.hex_layout and self.on_token_drop_callback:
                world_x = (event.x - self.pan_offset_x) / self.zoom_level
                world_y = (event.y - self.pan_offset_y) / self.zoom_level
                drop_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
                self.on_token_drop_callback(self.dragging_token_name, drop_hex.q, drop_hex.r)
            self.dragging_token_name = None
        self._drag_start_hex = None

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
        if getattr(self, "ruler_mode", False) and self._ruler_start_hex:
            self._on_ruler_drag(event)
            return
        if not getattr(self, 'hex_layout', None): return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        hovered_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
        self._last_hover_hex = hovered_hex
        self._update_coord_hud(hovered_hex)
        
        token_name = None
        if getattr(self, 'players_data', None):
            for name, pdata in self.players_data.items():
                pos = pdata.get('position', [0, 0]) if isinstance(pdata, dict) else pdata
                from common.hex_utils import Hex
                if Hex(*pos) == hovered_hex:
                    # Controlliamo la nebbia di guerra per il client
                    fow_active = getattr(self, 'fow_enabled', False) or (isinstance(getattr(self, 'map_data', None), dict) and self.map_data.get('fow_enabled', False))
                    if fow_active and getattr(self, 'player_name', None):
                        visible = getattr(self, 'visible_hexes', set())
                        if (hovered_hex.q, hovered_hex.r) not in visible and hovered_hex not in visible:
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
            try:
                self.hover_tooltip.destroy()
            except Exception:
                pass
            self.hover_tooltip = None
            
        if token_name and getattr(self, 'players_data', None) and token_name in self.players_data:
            self.hover_tooltip = tk.Toplevel(self)
            self.hover_tooltip.wm_overrideredirect(True)
            self.hover_tooltip.attributes('-topmost', True)
            x = self.winfo_rootx() + (event.x if event else 0) + 16
            y = self.winfo_rooty() + (event.y if event else 0) + 16
            self.hover_tooltip.wm_geometry(f"+{x}+{y}")
            
            pdata = self.players_data[token_name]
            card = tk.Frame(self.hover_tooltip, bg="#181B22", highlightbackground="#D4AF37", highlightthickness=1, padx=8, pady=5)
            card.pack(fill=tk.BOTH, expand=True)

            tk.Label(card, text=f"⚔️ {token_name}", bg="#181B22", fg="#F59E0B", font=("Segoe UI", 9, "bold"), anchor="w").pack(anchor="w")

            if isinstance(pdata, dict):
                hp = pdata.get('hp', '?')
                hp_max = pdata.get('hp_max', '?')
                temp_hp = pdata.get('temp_hp', 0) or 0
                ac = pdata.get('ac') or (pdata.get('full_sheet', {}) or {}).get('ac')
                conds = pdata.get('conditions', [])

                details = []
                if 'hp' in pdata:
                    t_str = f" (+{temp_hp})" if temp_hp > 0 else ""
                    details.append(f"❤️ HP: {hp}/{hp_max}{t_str}")
                if ac:
                    details.append(f"🛡️ CA: {ac}")
                if details:
                    tk.Label(card, text="  •  ".join(details), bg="#181B22", fg="#ECEFF1", font=("Segoe UI", 8, "bold"), anchor="w").pack(anchor="w", pady=(1, 0))
                if conds:
                    tk.Label(card, text=f"✨ {', '.join(conds)}", bg="#181B22", fg="#60A5FA", font=("Segoe UI", 8), anchor="w").pack(anchor="w", pady=(1, 0))

    def _on_ruler_drag(self, event):
        if not self.hex_layout or not self._ruler_start_hex: return
        world_x = (event.x - self.pan_offset_x) / self.zoom_level
        world_y = (event.y - self.pan_offset_y) / self.zoom_level
        current_hex = self.hex_layout.pixel_to_hex((world_x, world_y))
        self._ruler_current_hex = current_hex
        self._draw_ruler_between(self._ruler_start_hex, current_hex)

    def _draw_ruler_between(self, start_hex, end_hex):
        if not self.hex_layout or not start_hex or not end_hex:
            return
        from common.hex_utils import hex_distance, hex_linedraw
        from common.i18n import format_distance_hexes, get_map_scale_info

        active_map_data = getattr(self, "map_data", None)
        scale_info = get_map_scale_info(active_map_data)
        dist_hexes = hex_distance(start_hex, end_hex)
        dist_str = format_distance_hexes(dist_hexes, map_data=active_map_data, include_travel_time=True)

        per_hex = scale_info["per_hex"]
        per_hex_str = str(int(per_hex)) if per_hex == int(per_hex) else f"{per_hex:g}"
        scale_badge = f"1 hex = {per_hex_str} {scale_info['unit_label']}"

        self.delete("ruler_overlay")
        if getattr(self, '_ruler_line_id', None):
            self.delete(self._ruler_line_id)
        if getattr(self, '_ruler_text_id', None):
            self.delete(self._ruler_text_id)
        if getattr(self, '_ruler_text_bg_id', None):
            self.delete(self._ruler_text_bg_id)

        # Evidenzia gli esagoni attraversati dal righello in base alla scala della mappa
        try:
            path_hexes = hex_linedraw(start_hex, end_hex)
            if len(path_hexes) <= 60:
                for ph in path_hexes:
                    corners = self.hex_layout.hex_corners(ph)
                    sc_corners = [
                        (cx * self.zoom_level + self.pan_offset_x, cy * self.zoom_level + self.pan_offset_y)
                        for cx, cy in corners
                    ]
                    is_endpoint = (ph == start_hex or ph == end_hex)
                    self.create_polygon(
                        sc_corners,
                        fill="",
                        outline="#F59E0B" if is_endpoint else "#FBBF24",
                        width=2.0 if is_endpoint else 1.2,
                        dash=() if is_endpoint else (3, 3),
                        tags="ruler_overlay"
                    )
        except Exception:
            pass

        start_x, start_y = self.hex_layout.hex_to_pixel(start_hex)
        end_x, end_y = self.hex_layout.hex_to_pixel(end_hex)
        
        screen_start_x = start_x * self.zoom_level + self.pan_offset_x
        screen_start_y = start_y * self.zoom_level + self.pan_offset_y
        screen_end_x = end_x * self.zoom_level + self.pan_offset_x
        screen_end_y = end_y * self.zoom_level + self.pan_offset_y

        self._ruler_line_id = self.create_line(
            screen_start_x, screen_start_y, screen_end_x, screen_end_y,
            fill="#F59E0B", dash=(6, 4), width=2.5, arrow=tk.LAST, tags="ruler_overlay"
        )
        
        mid_x = (screen_start_x + screen_end_x) / 2
        mid_y = (screen_start_y + screen_end_y) / 2 - 16
        self._ruler_text_id = self.create_text(
            mid_x, mid_y, text=f"📏 {dist_str} ({dist_hexes} hex • {scale_badge})",
            fill="#FDE68A", font=("Segoe UI", 10, "bold"), tags="ruler_overlay"
        )
        
        bbox = self.bbox(self._ruler_text_id)
        if bbox:
            pad_x, pad_y = 7, 4
            self._ruler_text_bg_id = self.create_rectangle(
                bbox[0] - pad_x, bbox[1] - pad_y, bbox[2] + pad_x, bbox[3] + pad_y,
                fill="#0F172A", outline="#F59E0B", width=1.5, tags="ruler_overlay"
            )
            self.tag_lower(self._ruler_text_bg_id, self._ruler_text_id)

    def _on_ruler_end(self, event):
        self.delete("ruler_overlay")
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
        self._ruler_current_hex = None

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

    def center_on_hex(self, target_hex):
        """Centra la visuale su un esagono specifico."""
        if not self.hex_layout: return
        cw = self.winfo_width()
        ch = self.winfo_height()
        wx, wy = self.hex_layout.hex_to_pixel(target_hex)
        self.pan_offset_x = (cw / 2) - (wx * self.zoom_level)
        self.pan_offset_y = (ch / 2) - (wy * self.zoom_level)
        self.redraw()

    def center_on_token(self, token_name):
        """Centra la visuale su un token specificato per nome."""
        if not getattr(self, 'players_data', None): return
        pdata = self.players_data.get(token_name)
        if not pdata: return
        pos = pdata.get('position', [0, 0]) if isinstance(pdata, dict) else pdata
        self.center_on_hex(Hex(*pos))

    def update_data(self, map_data, players_data, player_name="", turn_player_name="", aoes_data=None, time_hour=12, weather="Sereno", combat_active=False, combat_order=None, round_number=1):
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
        self.round_number = round_number
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
        grid_type = self.map_data.get("grid_type", "hex")
        if grid_type == "square":
            self.hex_layout = SquareLayout(size=hex_size * 1.5, origin=(0, 0))
        elif grid_type in ("none", "gridless"):
            self.hex_layout = SquareLayout(size=hex_size * 1.5, origin=(0, 0))
        else:
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
        
        fow_enabled = bool(self.map_data.get("fow_enabled", False))
        self.fow_enabled = fow_enabled
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
            vision_rad = max(pdata.get('vision_radius', 6) if isinstance(pdata, dict) else 6, pdata.get('light_radius', 0) if isinstance(pdata, dict) else 0)
            visible_now = {(h.q, h.r) for h in get_visible_hexes(Hex(pos[0], pos[1]), vision_rad, walls_hex_set, grid_type=grid_type)}

            # Condividi visione/luce con altri membri del party che hanno sorgenti di luce attive
            for other_name, other_pdata in self.players_data.items():
                if other_name != self.player_name and isinstance(other_pdata, dict) and other_pdata.get('is_party_member', False):
                    o_light = other_pdata.get('light_radius', 0)
                    if o_light > 0:
                        o_pos = other_pdata.get('position', [0, 0])
                        visible_now.update({(h.q, h.r) for h in get_visible_hexes(Hex(o_pos[0], o_pos[1]), o_light, walls_hex_set, grid_type=grid_type)})

        self.visible_hexes = visible_now

        half_cover_set = {tuple(c) for c in self.map_data.get("half_cover", [])}
        three_quarters_cover_set = {tuple(c) for c in self.map_data.get("three_quarters_cover", [])}

        # Cache e calcolo celle visibili nel viewport
        raw_hexes = self.map_data.get("hexes", [])
        if self._map_hexes_set is None or len(self._map_hexes_set) != len(raw_hexes):
            self._map_hexes_set = {tuple(h) for h in raw_hexes}

        is_square = grid_type in ("square", "none", "gridless")
        line_w = max(1, int(1/self.zoom_level)) if self.zoom_level < 1 else 1

        if is_square:
            cell_size = hex_size * 1.5
            scaled_size = cell_size * self.zoom_level
            half_s = 0.5 * scaled_size

            min_q = int(math.floor(world_x1 / cell_size)) - 1
            max_q = int(math.ceil(world_x2 / cell_size)) + 1
            min_r = int(math.floor(world_y1 / cell_size)) - 1
            max_r = int(math.ceil(world_y2 / cell_size)) + 1

            candidate_count = (max_q - min_q + 1) * (max_r - min_r + 1)
            if candidate_count < len(self._map_hexes_set):
                visible_hex_list = []
                for q in range(min_q, max_q + 1):
                    for r in range(min_r, max_r + 1):
                        if (q, r) in self._map_hexes_set:
                            visible_hex_list.append((q, r))
            else:
                visible_hex_list = [
                    (q, r) for q, r in self._map_hexes_set
                    if (min_q <= q <= max_q) and (min_r <= r <= max_r)
                ]
            corner_offsets = ()
        else:
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
            cx, cy = self.hex_layout.hex_to_pixel(Hex(q, r))
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y

            if is_square:
                scaled_corners = [
                    (sx - half_s, sy - half_s),
                    (sx + half_s, sy - half_s),
                    (sx + half_s, sy + half_s),
                    (sx - half_s, sy + half_s)
                ]
            else:
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
            elif fow_enabled:
                if is_dm:
                    if hex_tup not in fow_revealed:
                        fill_color = "gray25"
                        stipple_pattern = "gray50"
                else:
                    if hex_tup in visible_now:
                        fill_color = ""
                    elif hex_tup in fow_revealed:
                        fill_color = "gray10"
                        stipple_pattern = "gray75"
                    else:
                        fill_color = "black"

            if scaled_size < 8.0 and not fill_color:
                continue

            cell_outline = "" if grid_type in ("none", "gridless") else border_color
            if cell_outline or fill_color:
                self.create_polygon(scaled_corners, fill=fill_color, outline=cell_outline, width=line_w, stipple=stipple_pattern)

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
                    aoe_hexes = get_line_hexes(origin, Hex(*aoe.get("target", aoe["origin"])), aoe.get("size", 3))
                else:
                    aoe_hexes = []

                for h in aoe_hexes:
                    if fow_enabled and not is_dm and (h.q, h.r) not in fow_revealed:
                        continue
                    cx, cy = self.hex_layout.hex_to_pixel(h)
                    margin_size = hex_size * 1.5 if is_square else hex_size
                    if not (world_x1 - margin_size <= cx <= world_x2 + margin_size and world_y1 - margin_size <= cy <= world_y2 + margin_size):
                        continue
                    sx = cx * self.zoom_level + self.pan_offset_x
                    sy = cy * self.zoom_level + self.pan_offset_y
                    if is_square:
                        scaled_corners = [
                            (sx - half_s, sy - half_s),
                            (sx + half_s, sy - half_s),
                            (sx + half_s, sy + half_s),
                            (sx - half_s, sy + half_s)
                        ]
                    else:
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
            if fow_enabled and not is_dm and l_tup not in fow_revealed and l_tup not in visible_now:
                continue
            cx, cy = self.hex_layout.hex_to_pixel(Hex(l["q"], l["r"]))
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            if scr_x1 <= sx <= scr_x2 and scr_y1 <= sy <= scr_y2:
                self.create_rectangle(sx-10, sy-10, sx+10, sy+10, fill="gold", outline="brown")
                self.create_text(sx, sy, text="Loot", font=("", max(8, int(10*self.zoom_level))))

        # Draw Lights
        lights_data = self.map_data.get("lights", [])
        for l in lights_data:
            l_tup = (l["q"], l["r"])
            if fow_enabled and not is_dm and l_tup not in fow_revealed and l_tup not in visible_now:
                continue
            cx, cy = self.hex_layout.hex_to_pixel(Hex(l["q"], l["r"]))
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            if scr_x1 <= sx <= scr_x2 and scr_y1 <= sy <= scr_y2:
                self.create_oval(sx-5, sy-5, sx+5, sy+5, fill="yellow", outline="orange")

        # Draw Teleports
        teleports_data = self.map_data.get("teleports", {})
        for k in teleports_data:
            q_str, r_str = k.split(",")
            t_q, t_r = int(q_str), int(r_str)
            if fow_enabled and not is_dm and (t_q, t_r) not in fow_revealed and (t_q, t_r) not in visible_now:
                continue
            cx, cy = self.hex_layout.hex_to_pixel(Hex(t_q, t_r))
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            if scr_x1 <= sx <= scr_x2 and scr_y1 <= sy <= scr_y2:
                self.create_oval(sx-6, sy-6, sx+6, sy+6, fill="blue", outline="cyan", width=2)
                if is_dm:
                    self.create_text(sx, sy-15, text="🚪", font=("", max(8, int(10*self.zoom_level))))

        # Draw Traps (Trappole D&D 5e)
        traps_data = self.map_data.get("traps", [])
        for tr in traps_data:
            tr_q = tr.get("q", 0)
            tr_r = tr.get("r", 0)
            is_trig = tr.get("triggered", False)
            is_hid = tr.get("hidden", True)
            if not is_dm and is_hid and not is_trig:
                continue
            if fow_enabled and not is_dm and (tr_q, tr_r) not in fow_revealed and (tr_q, tr_r) not in visible_now:
                continue
            cx, cy = self.hex_layout.hex_to_pixel(Hex(tr_q, tr_r))
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            if scr_x1 <= sx <= scr_x2 and scr_y1 <= sy <= scr_y2:
                icon = "💥" if is_trig else "⚠️"
                self.create_text(sx, sy, text=icon, font=("Arial", max(9, int(13 * self.zoom_level))))

        # Draw Spawn Point
        spawn_point = self.map_data.get("spawn_point")
        if spawn_point and is_dm:
            sp_q, sp_r = spawn_point[0], spawn_point[1]
            cx, cy = self.hex_layout.hex_to_pixel(Hex(sp_q, sp_r))
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y
            if scr_x1 <= sx <= scr_x2 and scr_y1 <= sy <= scr_y2:
                self.create_text(sx, sy, text="[S]\nSpawn", font=("Arial", max(8, int(10*self.zoom_level)), "bold"), fill="#00FF00", justify="center")

        # Tokens (Players e PNG)
        TOKEN_SIZE_MAP = {
            "tiny": 0.5, "minuscola": 0.5,
            "small": 0.8, "piccola": 0.8,
            "medium": 1.0, "media": 1.0,
            "large": 1.8, "grande": 1.8,
            "huge": 2.6, "enorme": 2.6,
            "gargantuan": 3.5, "mastodontica": 3.5
        }
        for name, pdata in self.players_data.items():
            if isinstance(pdata, dict):
                pos = pdata.get('position') or [0, 0]
                conditions = pdata.get('conditions', [])
                raw_size = pdata.get('size', 1)
                layer = pdata.get('layer', 'token')
                aura_radius = pdata.get('aura_radius', 0)
                aura_color = pdata.get('aura_color', 'yellow')
                hp = pdata.get('hp', 0)
                hp_max = pdata.get('hp_max', 0)
            else:
                pos = pdata or [0, 0]
                conditions = []
                raw_size = 1
                layer = 'token'
                aura_radius = 0
                aura_color = 'yellow'
                hp = 0
                hp_max = 0

            # GM Layer: hidden completely from players
            is_gm_layer = (layer == 'gm')
            if is_gm_layer and not is_dm:
                continue

            if isinstance(raw_size, str):
                size_mult = TOKEN_SIZE_MAP.get(raw_size.lower(), 1.0)
            elif isinstance(raw_size, (int, float)):
                size_mult = float(raw_size)
            else:
                size_mult = 1.0

            is_me = (name == self.player_name)
            q, r = pos[0], pos[1]
            if fow_enabled and not is_dm and (q, r) not in visible_now and not is_me:
                continue

            cx, cy = self.hex_layout.hex_to_pixel(Hex(q, r))
            sx = cx * self.zoom_level + self.pan_offset_x
            sy = cy * self.zoom_level + self.pan_offset_y

            radius = 12 * size_mult
            step_dist = (hex_size * 1.5 if is_square else hex_size * 1.7320508075688772)
            screen_aura_r = (aura_radius * step_dist * self.zoom_level) if aura_radius > 0 else 0
            max_r = max(radius + 20, screen_aura_r + 10)
            if not (scr_x1 - max_r <= sx <= scr_x2 + max_r and scr_y1 - max_r <= sy <= scr_y2 + max_r):
                continue

            is_me = (name == self.player_name)
            is_party = pdata.get('is_party_member', False) if isinstance(pdata, dict) else False
            leg_res = pdata.get('legendary_resistances_max', 0) if isinstance(pdata, dict) else 0
            leg_act = pdata.get('legendary_actions_max', 0) if isinstance(pdata, dict) else 0
            is_boss = (leg_res > 0 or leg_act > 0)

            if is_gm_layer:
                token_base_color = "#3B185F"
                token_border_color = "#A855F7"
                ring_width = 2.4
            elif is_me:
                token_base_color = "#059669"
                token_border_color = "#F59E0B"
                ring_width = 2.5
            elif is_party:
                token_base_color = "#2563EB"
                token_border_color = "#60A5FA"
                ring_width = 2.0
            elif is_boss:
                token_base_color = "#881337"
                token_border_color = "#F59E0B"
                ring_width = 2.5
            else:
                token_base_color = "#DC2626"
                token_border_color = "#F87171"
                ring_width = 1.8

            # Aura magica ad anelli concentrici
            if aura_radius > 0:
                self.create_oval(sx - screen_aura_r, sy - screen_aura_r, 
                                 sx + screen_aura_r, sy + screen_aura_r, 
                                 fill="", outline=aura_color, dash=(8, 4), width=3)
                inner_aura_r = max(radius + 2, screen_aura_r * 0.7)
                self.create_oval(sx - inner_aura_r, sy - inner_aura_r,
                                 sx + inner_aura_r, sy + inner_aura_r,
                                 fill="", outline=aura_color, dash=(4, 4), width=1)

            # Luce Dinamica (Torcia, Lanterna, Incantesimo Luce)
            light_radius = pdata.get('light_radius', 0) if isinstance(pdata, dict) else 0
            light_color = pdata.get('light_color', '#FFD700') if isinstance(pdata, dict) else '#FFD700'
            if light_radius > 0:
                screen_light_r = (light_radius * step_dist * self.zoom_level)
                self.create_oval(sx - screen_light_r, sy - screen_light_r,
                                 sx + screen_light_r, sy + screen_light_r,
                                 fill="", outline=light_color, dash=(5, 5), width=2)

            # Evidenziazione Turno Attivo (Doppio anello oro radiante)
            is_turn = getattr(self, "turn_player_name", "") == name
            if is_turn:
                self.create_oval(sx-(radius+5), sy-(radius+5), sx+(radius+5), sy+(radius+5), fill="", outline="#FCC419", width=2)
                self.create_oval(sx-(radius+3), sy-(radius+3), sx+(radius+3), sy+(radius+3), fill="", outline="#D4AF37", width=3)

            # 3D Soft Drop-Shadow below token base
            self.create_oval(sx - radius + 1, sy - radius + 3, sx + radius + 1, sy + radius + 4, fill="#050608", outline="")
            self.create_oval(sx - radius, sy - radius + 2, sx + radius, sy + radius + 2, fill="#0E1015", outline="")

            # Dynamic outer ring halo for Heroes and Bosses
            if (is_me or is_boss) and not is_turn:
                self.create_oval(sx - (radius + 1.5), sy - (radius + 1.5), sx + (radius + 1.5), sy + (radius + 1.5), fill="", outline=token_border_color, width=1)

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
                    ring_outline = "#A855F7" if is_gm_layer else ("gray" if is_invisible else token_border_color)
                    ring_dash = (4, 2) if is_gm_layer else ((2, 2) if is_invisible else "")
                    self.create_oval(sx-radius, sy-radius, sx+radius, sy+radius, fill="", outline=ring_outline, width=ring_width, dash=ring_dash)
                else:
                    outline_style = "#A855F7" if is_gm_layer else ("gray" if is_invisible else token_border_color)
                    dash_style = (4, 2) if is_gm_layer else ((2, 2) if is_invisible else "")
                    self.create_oval(sx-radius, sy-radius, sx+radius, sy+radius, fill=token_base_color, outline=outline_style, width=ring_width, dash=dash_style)
                    self.create_text(sx, sy, text=name[:2].upper(), fill="white", font=("Segoe UI", 8, "bold"))
            else:
                outline_style = "#A855F7" if is_gm_layer else ("gray" if is_invisible else token_border_color)
                dash_style = (4, 2) if is_gm_layer else ((2, 2) if is_invisible else "")
                self.create_oval(sx-radius, sy-radius, sx+radius, sy+radius, fill=token_base_color, outline=outline_style, width=ring_width, dash=dash_style)
                self.create_text(sx, sy, text=name[:2].upper(), fill="white", font=("Segoe UI", 8, "bold"))

            if is_gm_layer:
                self.create_text(sx, sy - radius - 7, text="[GM]", fill="#C084FC", font=("Segoe UI", max(7, int(8 * self.zoom_level)), "bold"))

            # Distintivo Boss Leggendario (👑)
            if is_boss:
                self.create_text(sx - radius, sy - radius, text="👑", font=("Segoe UI Emoji", max(9, int(11 * self.zoom_level))))

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
                cond_badge_map = {
                    "Morto": ("#2B0000", "💀"),
                    "Incosciente": ("#1864AB", "💤"),
                    "Privo di Sensi": ("#1864AB", "💤"),
                    "Prono": ("#8F4F00", "🔻"),
                    "Concentrazione": ("#D9480F", "⚡"),
                    "Schivata": ("#1971C2", "🛡️"),
                    "Aiuto": ("#2F9E44", "🤝"),
                    "Avvelenato": ("#2B8A3E", "🤢"),
                    "Accecato": ("#495057", "👁️"),
                    "Paralizzato": ("#0C8599", "⚡"),
                    "Trattenuto": ("#6741D9", "🕸️"),
                    "Invisibile": ("#868E96", "👻"),
                    "Spaventato": ("#A61E4D", "😱"),
                    "Stabilizzato": ("#099268", "🩹"),
                    "Sordo": ("#495057", "🔇"),
                    "Afferrato": ("#E67700", "✊"),
                    "Incantato": ("#D6336C", "💖"),
                    "Pietrificato": ("#5C5F66", "🗿")
                }
                badge_r = max(6, int(8 * min(self.zoom_level, 1.2)))
                start_x = sx - radius
                start_y = sy - radius - badge_r - 2
                for i, cond in enumerate(conditions[:5]):
                    badge_info = cond_badge_map.get(cond, ("#C92A2A", cond[:2].upper()))
                    bg_color, symbol = badge_info
                    b_x = start_x + (i * (badge_r * 2 + 2))
                    b_y = start_y
                    self.create_oval(b_x - badge_r, b_y - badge_r, b_x + badge_r, b_y + badge_r, fill=bg_color, outline="#FFFFFF", width=1)
                    font_size = max(6, int(badge_r * 1.1))
                    self.create_text(b_x, b_y, text=symbol, font=("Segoe UI Emoji", font_size), fill="white")

        # --- ENVIRONMENTS & COMBAT OVERLAYS ---
        w = cw
        h = ch
        
        # 1 & 2. Day/Night Cycle & Weather Overlays
        self._draw_environment_and_weather_overlays(w, h)
            
        # 3. Horizontal Initiative Carousel Ribbon (Foundry VTT / D&D Beyond modern style)
        self._initiative_ribbon_bboxes = []
        if getattr(self, "combat_active", False) and getattr(self, "combat_order", None):
            order = [name for name in self.combat_order if name in self.players_data]
            if order:
                card_w = 72
                card_h = 56
                spacing = 6
                badge_w = 70
                total_w = len(order) * (card_w + spacing) - spacing + badge_w + 14
                cw = self.winfo_width()
                start_x = max(10, (cw - total_w) / 2)
                start_y = 10
                
                # Sfondo bar container arrotondato (dark translucent glassmorphism)
                self.create_rectangle(
                    start_x - 6, start_y, start_x + total_w + 6, start_y + card_h + 8,
                    fill="#111318", outline="#D4AF37", width=1.5, tags="hud_initiative"
                )
                
                # Badge Round sulla sinistra
                round_num = getattr(self, "round_number", 1)
                self.create_rectangle(
                    start_x, start_y + 4, start_x + badge_w, start_y + card_h + 4,
                    fill="#1F242D", outline="#F59E0B", width=1, tags="hud_initiative"
                )
                self.create_text(start_x + badge_w/2, start_y + 20, text=f"⚔️ R{round_num}", fill="#F59E0B", font=("Segoe UI", 11, "bold"), tags="hud_initiative")
                self.create_text(start_x + badge_w/2, start_y + 38, text="ROUND", fill="#9CA3AF", font=("Segoe UI", 7, "bold"), tags="hud_initiative")
                
                # Disegna le card dei partecipanti orizzontalmente
                cx_offset = start_x + badge_w + 10
                for idx, name in enumerate(order):
                    is_current = (name == getattr(self, "turn_player_name", ""))
                    card_x1 = cx_offset
                    card_y1 = start_y + 4
                    card_x2 = card_x1 + card_w
                    card_y2 = card_y1 + card_h
                    
                    pdata = self.players_data.get(name, {})
                    is_party = pdata.get('is_party_member', False) if isinstance(pdata, dict) else False
                    hp = pdata.get('hp', 0) if isinstance(pdata, dict) else 0
                    hp_max = pdata.get('hp_max', 1) if isinstance(pdata, dict) else 1
                    
                    # Colori card
                    if is_current:
                        card_bg = "#2D2208"
                        card_border = "#F59E0B"
                        card_w_border = 2
                        name_color = "#FDE68A"
                    else:
                        card_bg = "#181B22"
                        card_border = "#3B82F6" if is_party else "#EF4444"
                        card_w_border = 1
                        name_color = "#E5E7EB"
                    
                    self.create_rectangle(card_x1, card_y1, card_x2, card_y2, fill=card_bg, outline=card_border, width=card_w_border, tags="hud_initiative")
                    
                    # Indicatore freccia per il turno corrente
                    if is_current:
                        self.create_text((card_x1 + card_x2)/2, card_y1 - 3, text="▼", fill="#F59E0B", font=("Segoe UI", 8, "bold"), tags="hud_initiative")
                    
                    # Nome troncato a 8 caratteri
                    short_name = name[:7] + "…" if len(name) > 8 else name
                    self.create_text((card_x1 + card_x2)/2, card_y1 + 14, text=short_name, fill=name_color, font=("Segoe UI", 8, "bold" if is_current else "normal"), tags="hud_initiative")
                    
                    # Ordine turno
                    self.create_text(card_x1 + 10, card_y2 - 12, text=f"#{idx+1}", fill="#9CA3AF", font=("Segoe UI", 7), tags="hud_initiative")
                    
                    # Mini barra HP sotto la card
                    hp_ratio = max(0.0, min(1.0, hp / max(1, hp_max)))
                    hp_bar_w = card_w - 24
                    hp_bar_x = card_x1 + 18
                    hp_bar_y = card_y2 - 12
                    self.create_rectangle(hp_bar_x, hp_bar_y - 2.5, hp_bar_x + hp_bar_w, hp_bar_y + 2.5, fill="#374151", outline="", tags="hud_initiative")
                    if hp_ratio > 0:
                        bar_color = "#10B981" if hp_ratio > 0.5 else ("#F59E0B" if hp_ratio > 0.25 else "#EF4444")
                        self.create_rectangle(hp_bar_x, hp_bar_y - 2.5, hp_bar_x + (hp_bar_w * hp_ratio), hp_bar_y + 2.5, fill=bar_color, outline="", tags="hud_initiative")
                    
                    # Registra bounding box per click
                    self._initiative_ribbon_bboxes.append((card_x1, card_y1, card_x2, card_y2, name))
                    cx_offset += card_w + spacing

        # 4. Floating Glassmorphism Map Controls (Bottom-Left Minimalist HUD)
        cw = self.winfo_width()
        ch = self.winfo_height()
        if cw > 220 and ch > 160:
            hud_x = 16
            hud_y = ch - 52
            hud_btn_w = 32
            hud_btn_h = 32
            hud_spacing = 6
            buttons = [
                ("👆", "center"),
                ("➕", "zoom_in"),
                ("➖", "zoom_out"),
                ("📏", "ruler"),
            ]
            total_hud_w = len(buttons) * (hud_btn_w + hud_spacing) - hud_spacing + 14
            
            # Sfondo pillola HUD
            self.create_rectangle(hud_x, hud_y, hud_x + total_hud_w, hud_y + hud_btn_h + 8,
                                  fill="#111318", outline="#374151", width=1, tags="hud_controls")
            
            self._hud_control_bboxes = []
            cur_bx = hud_x + 7
            for icon, action_key in buttons:
                bx1 = cur_bx
                by1 = hud_y + 4
                bx2 = bx1 + hud_btn_w
                by2 = by1 + hud_btn_h
                
                btn_bg = "#2563EB" if (action_key == "ruler" and getattr(self, "ruler_mode", False)) else "#1A1D24"
                btn_border = "#60A5FA" if (action_key == "ruler" and getattr(self, "ruler_mode", False)) else "#374151"
                
                self.create_rectangle(bx1, by1, bx2, by2, fill=btn_bg, outline=btn_border, width=1, tags="hud_controls")
                self.create_text((bx1 + bx2)/2, (by1 + by2)/2, text=icon, font=("Segoe UI Emoji", 11), tags="hud_controls")
                
                self._hud_control_bboxes.append((bx1, by1, bx2, by2, action_key))
                cur_bx += hud_btn_w + hud_spacing

        # 5. Live Coordinates, Map Scale & Zoom Badge (Bottom-Right HUD)
        self._update_coord_hud()

        # 6. Ripristina eventuale righello attivo o fissato dopo zoom/pan/cambio unità
        r_start = getattr(self, "_ruler_start_hex", None) or getattr(self, "_ruler_pinned_start", None)
        r_end = getattr(self, "_ruler_current_hex", None) or getattr(self, "_ruler_pinned_end", None)
        if r_start and r_end:
            self._draw_ruler_between(r_start, r_end)

    def _update_coord_hud(self, hovered_hex=None):
        self.delete("hud_coords")
        cw = self.winfo_width()
        ch = self.winfo_height()
        if cw > 350 and ch > 150:
            from common.i18n import get_map_scale_info
            scale_info = get_map_scale_info(getattr(self, "map_data", None))
            per_hex = scale_info["per_hex"]
            per_hex_str = str(int(per_hex)) if per_hex == int(per_hex) else f"{per_hex:g}"
            scale_str = f"1 hex={per_hex_str}{scale_info['unit_label']}"

            zoom_pct = int(self.zoom_level * 100)
            h_hex = hovered_hex or getattr(self, '_last_hover_hex', None)
            coord_str = f"⬡ {scale_str} • {zoom_pct}%"
            if h_hex:
                coord_str = f"⬡ q:{h_hex.q}, r:{h_hex.r} • {scale_str} • {zoom_pct}%"
            badge_w = len(coord_str) * 6.3 + 16
            bx2 = cw - 16
            bx1 = bx2 - badge_w
            by2 = ch - 16
            by1 = by2 - 24
            self.create_rectangle(bx1, by1, bx2, by2, fill="#0F1115", outline="#374151", width=1, tags="hud_coords")
            self.create_text((bx1 + bx2)/2, (by1 + by2)/2, text=coord_str, fill="#9CA3AF", font=("Segoe UI", 8, "bold"), tags="hud_coords")

    def _draw_environment_and_weather_overlays(self, w, h):
        """Disegna l'atmosfera temporale (Giorno/Notte/Alba/Tramonto) e il clima dinamico (Sereno, Pioggia, Tempesta, Neve, Nebbia)."""
        import random

        # 1. Ciclo Giorno / Notte / Alba / Tramonto
        hour = getattr(self, "time_hour", 12)
        is_night = False
        time_period_desc = ""
        if hour < 6 or hour > 19:
            is_night = True
            time_period_desc = "Notte"
            self.create_rectangle(0, 0, w, h, fill="#050811", stipple="gray50", outline="", tags="night_overlay")
        elif 6 <= hour < 8:
            time_period_desc = "Alba"
            self.create_rectangle(0, 0, w, h, fill="#fef3c7", stipple="gray12", outline="", tags="night_overlay")
        elif 18 <= hour <= 19:
            time_period_desc = "Tramonto"
            self.create_rectangle(0, 0, w, h, fill="#ea580c", stipple="gray12", outline="", tags="night_overlay")

        # 2. Normalizzazione del clima (supporto bilingue IT / EN)
        raw_weather = str(getattr(self, "weather", "Sereno")).strip()
        norm = raw_weather.lower()
        WEATHER_MAP = {
            "sereno": "sereno",
            "clear": "sereno",
            "sole": "sereno",
            "sunny": "sereno",
            "pioggia": "pioggia",
            "rain": "pioggia",
            "rainy": "pioggia",
            "tempesta": "tempesta",
            "storm": "tempesta",
            "stormy": "tempesta",
            "temporale": "tempesta",
            "neve": "neve",
            "snow": "neve",
            "snowy": "neve",
            "nebbia": "nebbia",
            "fog": "nebbia",
            "foggy": "nebbia",
            "mist": "nebbia",
            "misty": "nebbia"
        }
        w_key = WEATHER_MAP.get(norm, "sereno")

        # RNG deterministico per mantenere costanti le particelle ad ogni pan / zoom
        seed_val = 1337 + sum(ord(c) for c in w_key)
        rng = random.Random(seed_val)

        # 3. Atmosfera e particelle visive del clima
        if w_key == "pioggia":
            # Filtro pioggia blu scuro / ardesia
            self.create_rectangle(0, 0, w, h, fill="#1e3a8a", stipple="gray25", outline="", tags="weather_overlay")
            
            # Scie di pioggia diagonali
            drop_count = min(180, max(75, int((w * h) / 4500)))
            for _ in range(drop_count):
                x = rng.randint(-20, w)
                y = rng.randint(0, h)
                dy = rng.randint(14, 22)
                dx = 4
                col = rng.choice(["#60a5fa", "#93c5fd", "#bfdbfe"])
                self.create_line(x, y, x + dx, y + dy, fill=col, width=1, tags="weather_overlay")
            
            # Schizzi e increspature d'acqua
            for _ in range(max(10, drop_count // 6)):
                rx = rng.randint(20, max(21, w - 20))
                ry = rng.randint(20, max(21, h - 20))
                self.create_oval(rx - 3, ry - 1, rx + 3, ry + 1, outline="#93c5fd", width=1, tags="weather_overlay")

        elif w_key == "tempesta":
            # Filtro tempesta: oscurità profonda + atmosfera indaco/tempestosa
            self.create_rectangle(0, 0, w, h, fill="#020617", stipple="gray50", outline="", tags="weather_overlay")
            self.create_rectangle(0, 0, w, h, fill="#1e1b4b", stipple="gray25", outline="", tags="weather_overlay")
            
            # Pioggia torrenziale e sferzante dal vento
            storm_drops = min(260, max(110, int((w * h) / 3200)))
            for _ in range(storm_drops):
                x = rng.randint(-60, w)
                y = rng.randint(0, h)
                dy = rng.randint(18, 30)
                dx = 9
                col = rng.choice(["#38bdf8", "#60a5fa", "#93c5fd", "#e2e8f0"])
                lw = 1 if rng.random() > 0.35 else 2
                self.create_line(x, y, x + dx, y + dy, fill=col, width=lw, tags="weather_overlay")
            
            # Fulmine ramificato spettacolare nel cielo
            lx = int(w * 0.65)
            ly = 0
            cur_x, cur_y = lx, ly
            bolt_pts = [(cur_x, cur_y)]
            while cur_y < h * 0.68:
                cur_x += rng.randint(-35, 30)
                cur_y += rng.randint(25, 55)
                bolt_pts.append((cur_x, cur_y))
            
            if len(bolt_pts) >= 3:
                # Bagliore esterno azzurro ciano
                self.create_line(bolt_pts, fill="#38bdf8", width=4, capstyle=tk.ROUND, joinstyle=tk.ROUND, tags="weather_overlay")
                # Nucleo bianco incandescente
                self.create_line(bolt_pts, fill="#ffffff", width=2, capstyle=tk.ROUND, joinstyle=tk.ROUND, tags="weather_overlay")
                
                # Ramificazione secondaria
                mid_idx = len(bolt_pts) // 2
                fx, fy = bolt_pts[mid_idx]
                fork_pts = [(fx, fy)]
                for _ in range(3):
                    fx += rng.randint(-40, -10)
                    fy += rng.randint(18, 40)
                    fork_pts.append((fx, fy))
                self.create_line(fork_pts, fill="#38bdf8", width=3, capstyle=tk.ROUND, joinstyle=tk.ROUND, tags="weather_overlay")
                self.create_line(fork_pts, fill="#ffffff", width=1.5, capstyle=tk.ROUND, joinstyle=tk.ROUND, tags="weather_overlay")

        elif w_key == "neve":
            # Filtro gelido invernale bianco / azzurro ghiaccio
            self.create_rectangle(0, 0, w, h, fill="#cbd5e1", stipple="gray25", outline="", tags="weather_overlay")
            self.create_rectangle(0, 0, w, h, fill="#e0f2fe", stipple="gray12", outline="", tags="weather_overlay")
            
            # Fiocchi di neve cadenti
            flake_count = min(190, max(80, int((w * h) / 4200)))
            for _ in range(flake_count):
                x = rng.randint(0, w)
                y = rng.randint(0, h)
                r = rng.choice([1, 1.5, 2, 2.5, 3])
                col = rng.choice(["#ffffff", "#f8fafc", "#f1f5f9", "#e2e8f0", "#bae6fd"])
                self.create_oval(x - r, y - r, x + r, y + r, fill=col, outline="", tags="weather_overlay")
            
            # Cristalli di brina e stelle di ghiaccio
            for _ in range(max(10, flake_count // 7)):
                fx = rng.randint(15, max(16, w - 15))
                fy = rng.randint(15, max(16, h - 15))
                self.create_line(fx - 3, fy, fx + 3, fy, fill="#ffffff", width=1, tags="weather_overlay")
                self.create_line(fx, fy - 3, fx, fy + 3, fill="#ffffff", width=1, tags="weather_overlay")
                self.create_line(fx - 2, fy - 2, fx + 2, fy + 2, fill="#ffffff", width=1, tags="weather_overlay")
                self.create_line(fx - 2, fy + 2, fx + 2, fy - 2, fill="#ffffff", width=1, tags="weather_overlay")

        elif w_key == "nebbia":
            # Filtro nebbia densa e foschia volumetrica
            self.create_rectangle(0, 0, w, h, fill="#475569", stipple="gray50", outline="", tags="weather_overlay")
            self.create_rectangle(0, 0, w, h, fill="#94a3b8", stipple="gray25", outline="", tags="weather_overlay")
            
            # Banchi di nebbia densi e ondulati
            cloud_count = min(36, max(16, int((w * h) / 24000)))
            for _ in range(cloud_count):
                cx = rng.randint(-40, w + 40)
                cy = rng.randint(-20, h + 20)
                rx = rng.randint(90, 220)
                ry = rng.randint(45, 120)
                stip = rng.choice(["gray25", "gray12", "gray25"])
                fcol = rng.choice(["#64748b", "#94a3b8", "#cbd5e1", "#e2e8f0"])
                self.create_oval(cx - rx, cy - ry, cx + rx, cy + ry, fill=fcol, stipple=stip, outline="", tags="weather_overlay")

        # 4. Elegante Pill HUD Clima & Notte in alto a destra
        WEATHER_META = {
            "sereno": ("☀️", "Sereno", "#EAB308", "#FEF08A"),
            "pioggia": ("🌧️", "Pioggia", "#38BDF8", "#BAE6FD"),
            "tempesta": ("⛈️", "Tempesta", "#F59E0B", "#FDE68A"),
            "neve": ("❄️", "Neve", "#67E8F9", "#E0F2FE"),
            "nebbia": ("🌫️", "Nebbia", "#94A3B8", "#F1F5F9"),
        }
        icon, canon_name, border_col, text_col = WEATHER_META.get(w_key, ("☀️", "Sereno", "#EAB308", "#FEF08A"))
        
        try:
            from common.i18n import translate_weather
            weather_label = translate_weather(canon_name)
        except Exception:
            weather_label = canon_name
            
        if is_night:
            badge_text = f"🌙 {hour:02d}:00  •  {icon} {weather_label}"
            badge_w = 175
        elif time_period_desc:
            p_icon = "🌅" if time_period_desc == "Alba" else "🌇"
            badge_text = f"{p_icon} {time_period_desc}  •  {icon} {weather_label}"
            badge_w = 175
        else:
            badge_text = f"{icon} {weather_label}"
            badge_w = 115

        self._weather_badge_bbox = None
        if w > 200 and h > 120:
            bx2 = w - 16
            bx1 = bx2 - badge_w
            by1 = 12
            # Se il nastro di iniziativa è visibile al centro-alto, abbassa la pillola per non sovrapporsi
            if getattr(self, "combat_active", False) and getattr(self, "combat_order", None):
                by1 = 76
            by2 = by1 + 26
            
            self._weather_badge_bbox = (bx1, by1, bx2, by2)
            self.create_rectangle(bx1, by1, bx2, by2, fill="#111318", outline=border_col, width=1.5, tags="weather_overlay")
            self.create_text((bx1 + bx2)/2, (by1 + by2)/2, text=badge_text, fill=text_col, font=("Segoe UI", 9, "bold"), tags="weather_overlay")

class ToolTip:
    """Finestrella di tooltip Dark Fantasy mostrata al passaggio del mouse con supporto a callable per i18n dinamico."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip, add="+")
        self.widget.bind("<Leave>", self.hide_tip, add="+")
        self.widget.bind("<ButtonPress>", self.hide_tip, add="+")
        self.widget.bind("<Destroy>", self.hide_tip, add="+")

    def set_text(self, text):
        self.text = text

    def show_tip(self, event=None):
        if self.tip_window:
            return
        try:
            if not self.widget.winfo_exists():
                return
            tip_text = self.text() if callable(self.text) else self.text
            if not tip_text:
                return
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.attributes("-topmost", True)
            frame = tk.Frame(tw, bg="#181B22", highlightbackground="#D4AF37", highlightthickness=1, padx=8, pady=4)
            frame.pack(fill=tk.BOTH, expand=True)
            label = tk.Label(
                frame, text=tip_text, justify=tk.LEFT,
                bg="#181B22", fg="#ECEFF1", font=("Segoe UI", 9),
                wraplength=320
            )
            label.pack()
            tw.update_idletasks()
            tw_w = tw.winfo_reqwidth()
            tw_h = tw.winfo_reqheight()
            sw = tw.winfo_screenwidth()
            sh = tw.winfo_screenheight()
            if x + tw_w + 12 > sw:
                x = max(8, sw - tw_w - 12)
            if y + tw_h + 12 > sh:
                y = max(8, self.widget.winfo_rooty() - tw_h - 6)
            tw.wm_geometry(f"+{x}+{y}")
        except Exception:
            self.hide_tip()

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            try:
                tw.destroy()
            except Exception:
                pass


class ToastNotification:
    """Notifica non bloccante a scomparsa in stile dark fantasy."""
    _active_toasts = []

    def __init__(self, parent, message, title=None, duration=3500, toast_type="info", icon=None):
        self.parent = parent
        self.duration = duration
        
        type_styles = {
            "info": {"bg": "#1e232a", "fg": "#f0f6fc", "accent": "#d4af37", "icon": icon or "ℹ️"},
            "success": {"bg": "#13231b", "fg": "#f0f6fc", "accent": "#2ea043", "icon": icon or "✨"},
            "warning": {"bg": "#2b2111", "fg": "#f0f6fc", "accent": "#d29922", "icon": icon or "⚠️"},
            "danger": {"bg": "#2d1517", "fg": "#f0f6fc", "accent": "#f85149", "icon": icon or "💥"},
            "gold": {"bg": "#252112", "fg": "#f0f6fc", "accent": "#e3b341", "icon": icon or "💰"},
            "loot": {"bg": "#1c222d", "fg": "#f0f6fc", "accent": "#58a6ff", "icon": icon or "🎒"},
        }
        style = type_styles.get(toast_type, type_styles["info"])
        
        self.win = tk.Toplevel(parent)
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True)
        
        try:
            parent.update_idletasks()
            pw = parent.winfo_width()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
        except Exception:
            pw, px, py = 1000, 100, 100

        offset_y = 60 + len(ToastNotification._active_toasts) * 75
        self.win.geometry(f"330x68+{px + max(10, pw - 350)}+{py + offset_y}")

        frame = tk.Frame(self.win, bg=style["bg"], highlightbackground=style["accent"], highlightthickness=2, padx=10, pady=6)
        frame.pack(fill=tk.BOTH, expand=True)

        header_frame = tk.Frame(frame, bg=style["bg"])
        header_frame.pack(fill=tk.X)

        title_text = f"{style['icon']} {title or toast_type.capitalize()}"
        lbl_title = tk.Label(header_frame, text=title_text, font=("Georgia", 10, "bold"), fg=style["accent"], bg=style["bg"])
        lbl_title.pack(side=tk.LEFT)

        btn_close = tk.Label(header_frame, text="✕", font=("Arial", 9), fg="#8b949e", bg=style["bg"], cursor="hand2")
        btn_close.pack(side=tk.RIGHT)
        btn_close.bind("<Button-1>", lambda e: self.destroy())

        lbl_msg = tk.Label(frame, text=message, font=("Arial", 9), fg=style["fg"], bg=style["bg"], wraplength=300, justify=tk.LEFT)
        lbl_msg.pack(anchor="w", pady=(2, 0))

        ToastNotification._active_toasts.append(self)
        self.win.after(self.duration, self.destroy)

    def destroy(self):
        if self in ToastNotification._active_toasts:
            ToastNotification._active_toasts.remove(self)
        try:
            self.win.destroy()
        except Exception:
            pass


def show_toast(parent, message, title=None, duration=3500, toast_type="info", icon=None):
    """Funzione di utilità per mostrare un toast non bloccante."""
    try:
        return ToastNotification(parent, message, title=title, duration=duration, toast_type=toast_type, icon=icon)
    except Exception:
        return None


def show_rule_detail_popup(parent, rule_dict):
    """Mostra i dettagli completi di una regola in una comoda finestra modale."""
    win = tk.Toplevel(parent)
    title = rule_dict.get("title", "Regola 5e")
    win.title(title)
    win.geometry("560x440")
    win.minsize(450, 320)
    win.configure(bg="#111318")
    win.transient(parent)

    container = tk.Frame(win, bg="#111318", padx=16, pady=14)
    container.pack(fill=tk.BOTH, expand=True)

    header = tk.Frame(container, bg="#111318")
    header.pack(fill=tk.X, pady=(0, 8))

    lbl_title = tk.Label(header, text=title, font=("Segoe UI", 12, "bold"), bg="#111318", fg="#F59E0B")
    lbl_title.pack(side=tk.LEFT)

    manual_info = f"{rule_dict.get('manual', '5e')} • {rule_dict.get('page_ref', '')}"
    lbl_ref = tk.Label(header, text=manual_info, font=("Segoe UI", 9), bg="#1F242D", fg="#9CA3AF", padx=6, pady=2)
    lbl_ref.pack(side=tk.RIGHT)

    txt_content = tk.Text(container, bg="#181B22", fg="#E5E7EB", font=("Segoe UI", 10), wrap=tk.WORD, bd=0, padx=10, pady=10)
    scroll = tk.Scrollbar(container, orient=tk.VERTICAL, command=txt_content.yview)
    txt_content.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    txt_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    body = rule_dict.get("content") or rule_dict.get("summary", "")
    txt_content.insert(tk.END, body)
    txt_content.configure(state=tk.DISABLED)

    win.bind("<Escape>", lambda e: win.destroy())


class CommandPaletteDialog(tk.Toplevel):
    """
    Tavolozza dei Comandi Rapida (Ctrl + K) in stile Foundry VTT / VS Code / Spotlight.
    Permette di:
    - Eseguire tiri di dadi istantanei (/roll 1d20+5, 2d6, ecc.)
    - Cercare e centrare all'istante token e PNG sulla mappa
    - Ricercare regole, condizioni, mostri e incantesimi dai manuali D&D 5e
    - Eseguire scorciatoie rapide della UI (Righello, Zoom, Centra, Compendio, Scheda)
    """
    def __init__(self, master, map_canvas=None, on_action=None, is_dm=False, player_names=None):
        super().__init__(master)
        self.master = master
        self.map_canvas = map_canvas
        self.on_action = on_action
        self.is_dm = is_dm
        self.player_names = player_names or []
        
        self.title(_t("cmd_palette_title", default="Command Palette & Quick Search"))
        self.configure(bg="#111318")
        self.minsize(620, 480)
        self.transient(master)

        # Centra sopra la finestra master
        try:
            pw = master.winfo_width()
            ph = master.winfo_height()
            px = master.winfo_rootx()
            py = master.winfo_rooty()
            if pw > 200 and ph > 200:
                cw = 640
                ch = 490
                cx = max(px + 10, px + (pw - cw) // 2)
                cy = max(py + 10, py + (ph - ch) // 3)
                self.geometry(f"{cw}x{ch}+{cx}+{cy}")
        except Exception:
            self.geometry("640x490")

        self._manuals_manager = None
        self._results = []
        self._active_filter = "ALL"

        self._setup_ui()
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Up>", self._on_arrow_up)
        self.bind("<Down>", self._on_arrow_down)
        self.bind("<Return>", self._on_enter)
        
        self.after(50, lambda: self.search_entry.focus_set())
        self._perform_search("")

    def _setup_ui(self):
        main_box = tk.Frame(self, bg="#111318", highlightbackground="#D4AF37", highlightthickness=1.5, padx=12, pady=12)
        main_box.pack(fill=tk.BOTH, expand=True)

        # 1. Barra di Ricerca Header
        search_box = tk.Frame(main_box, bg="#181B22", highlightbackground="#374151", highlightthickness=1, padx=8, pady=6)
        search_box.pack(fill=tk.X, pady=(0, 8))

        lbl_icon = tk.Label(search_box, text="🔍", font=("Segoe UI Emoji", 13), bg="#181B22", fg="#F59E0B")
        lbl_icon.pack(side=tk.LEFT, padx=(2, 8))

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            search_box, textvariable=self.search_var, font=("Segoe UI", 12),
            bg="#181B22", fg="#F9FAFB", insertbackground="#F59E0B", bd=0, relief=tk.FLAT
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind("<KeyRelease>", self._on_search_key)

        lbl_esc = tk.Label(search_box, text="ESC", font=("Segoe UI", 8, "bold"), bg="#242832", fg="#9CA3AF", padx=5, pady=1)
        lbl_esc.pack(side=tk.RIGHT, padx=2)
        lbl_esc.bind("<Button-1>", lambda e: self.destroy())

        # 2. Filter Pills
        filter_bar = tk.Frame(main_box, bg="#111318")
        filter_bar.pack(fill=tk.X, pady=(0, 8))

        self._filter_buttons = {}
        filters = [
            ("ALL", "Tutti"),
            ("ROLL", _t("cmd_type_roll", default="🎲 Dadi")),
            ("TOKEN", _t("cmd_type_token", default="📍 Token")),
            ("RULE", _t("cmd_type_rule", default="📖 Regole")),
            ("ACTION", _t("cmd_type_action", default="⚡ Azioni")),
        ]
        for f_key, f_label in filters:
            btn = tk.Button(
                filter_bar, text=f_label, font=("Segoe UI", 8, "bold"),
                bg="#2563EB" if f_key == "ALL" else "#1F242D",
                fg="#FFFFFF" if f_key == "ALL" else "#9CA3AF",
                activebackground="#3B82F6", activeforeground="#FFFFFF",
                bd=0, relief=tk.FLAT, padx=8, pady=2,
                command=lambda k=f_key: self._set_filter(k)
            )
            btn.pack(side=tk.LEFT, padx=3)
            self._filter_buttons[f_key] = btn

        # 3. Content Split (Listbox a sinistra, Preview a destra)
        split_frame = tk.Frame(main_box, bg="#111318")
        split_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        split_frame.columnconfigure(0, weight=3)
        split_frame.columnconfigure(1, weight=2)
        split_frame.rowconfigure(0, weight=1)

        # Lista Risultati
        list_container = tk.Frame(split_frame, bg="#14171E", highlightbackground="#2D333F", highlightthickness=1)
        list_container.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.results_listbox = tk.Listbox(
            list_container, bg="#14171E", fg="#E5E7EB", selectbackground="#1E3A8A",
            selectforeground="#FDE68A", font=("Segoe UI", 9), activestyle="none",
            bd=0, highlightthickness=0
        )
        scrollbar = tk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.results_listbox.yview)
        self.results_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.results_listbox.bind("<<ListboxSelect>>", self._on_list_select)
        self.results_listbox.bind("<Double-Button-1>", lambda e: self._execute_selected())

        # Pannello Preview Dettagli a destra
        preview_container = tk.Frame(split_frame, bg="#181B22", highlightbackground="#2D333F", highlightthickness=1, padx=10, pady=8)
        preview_container.grid(row=0, column=1, sticky="nsew")

        self.prev_title_lbl = tk.Label(preview_container, text="Seleziona un elemento", font=("Segoe UI", 10, "bold"), bg="#181B22", fg="#F59E0B", wraplength=210, justify=tk.LEFT)
        self.prev_title_lbl.pack(anchor="w", pady=(0, 4))

        self.prev_badge_lbl = tk.Label(preview_container, text="", font=("Segoe UI", 8), bg="#262C38", fg="#9CA3AF", padx=4, pady=1)
        self.prev_badge_lbl.pack(anchor="w", pady=(0, 6))

        self.prev_text = tk.Text(
            preview_container, bg="#14161C", fg="#D1D5DB", font=("Segoe UI", 9),
            wrap=tk.WORD, bd=0, highlightthickness=0, height=8
        )
        self.prev_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.prev_text.configure(state=tk.DISABLED)

        self.btn_execute = tk.Button(
            preview_container, text="↵ Esegui / Seleziona", font=("Segoe UI", 9, "bold"),
            bg="#2563EB", fg="white", activebackground="#3B82F6", bd=0, relief=tk.FLAT,
            padx=10, pady=4, command=self._execute_selected
        )
        self.btn_execute.pack(fill=tk.X)

        # 4. Status Hint Footer
        hint_lbl = tk.Label(
            main_box, text=_t("cmd_palette_hint", default="↑ / ↓ Naviga  •  ↵ Seleziona / Esegui  •  Esc Chiudi"),
            font=("Segoe UI", 8), bg="#111318", fg="#6B7280"
        )
        hint_lbl.pack(anchor="w")

    def _set_filter(self, filter_key):
        self._active_filter = filter_key
        for k, btn in self._filter_buttons.items():
            if k == filter_key:
                btn.configure(bg="#2563EB", fg="#FFFFFF")
            else:
                btn.configure(bg="#1F242D", fg="#9CA3AF")
        self._perform_search(self.search_var.get())

    def _on_search_key(self, event=None):
        if event and event.keysym in ("Up", "Down", "Return", "Escape"):
            return
        self._perform_search(self.search_var.get())

    def _get_manuals_manager(self):
        if self._manuals_manager is None:
            try:
                from common.manuals_manager import ManualsManager
                self._manuals_manager = ManualsManager()
            except Exception as e:
                print("Error loading ManualsManager in CommandPalette:", e)
        return self._manuals_manager

    def _perform_search(self, query):
        q = (query or "").strip().lower()
        results = []

        # 1. DADI (Roll)
        is_roll_query = (
            q.startswith("/roll") or q.startswith("/r") or
            any(k in q for k in ["d4", "d6", "d8", "d10", "d12", "d20", "d100"]) or
            ("d" in q and any(c.isdigit() for c in q))
        )
        if is_roll_query:
            formula = q
            if formula.startswith("/roll"):
                formula = formula[5:].strip()
            elif formula.startswith("/r"):
                formula = formula[2:].strip()
            formula = formula or "1d20"
            results.append({
                "type": "ROLL",
                "icon": "🎲",
                "title": f"Lancia: {formula}",
                "badge": "Tiro Dadi",
                "summary": f"Invia il tiro dadi '{formula}' al tavolo virtuale.",
                "payload": formula
            })

        # 2. TOKEN SULLA MAPPA
        if self.map_canvas and hasattr(self.map_canvas, "players_data"):
            p_data = self.map_canvas.players_data
            for name, data in p_data.items():
                conds = data.get("conditions", []) if isinstance(data, dict) else []
                pos = data.get("position", [0, 0]) if isinstance(data, dict) else (data or [0, 0])
                hp = data.get("hp", "?") if isinstance(data, dict) else "?"
                hp_max = data.get("hp_max", "?") if isinstance(data, dict) else "?"
                
                cond_str = ", ".join(conds) if conds else "Nessuna"
                matches_token = (not q) or (q in name.lower()) or any(q in c.lower() for c in conds)
                if matches_token:
                    results.append({
                        "type": "TOKEN",
                        "icon": "📍",
                        "title": f"Token: {name}",
                        "badge": f"HP {hp}/{hp_max} • Hex [{pos[0]},{pos[1]}]",
                        "summary": f"Nome: {name}\nSalute: {hp}/{hp_max}\nPosizione Hex: {pos}\nCondizioni: {cond_str}",
                        "payload": name
                    })

        # 3. AZIONI RAPIDE DELLA UI
        actions = [
            ("center_map", "👆 Centra Vista Mappa", "Centra il canvas all'origine o sui token del tavolo."),
            ("toggle_ruler", "📏 Attiva / Disattiva Righello", "Alterna la modalità misuratore di distanza in piedi (ft)."),
            ("zoom_in", "➕ Ingrandisci Mappa (Zoom +)", "Aumenta il livello di ingrandimento del canvas."),
            ("zoom_out", "➖ Riduci Mappa (Zoom -)", "Diminuisce il livello di ingrandimento del canvas."),
            ("open_aoe", "💥 Sagoma Area d'Effetto (AoE)", "Configura e posiziona cerchi, coni, cubi o linee."),
            ("open_manuals", "📖 Apri Compendio & Manuali", "Esplora i manuali ufficiali 5e e note homebrew."),
            ("open_sheet", "📜 Apri Scheda Personaggio", "Visualizza la scheda interattiva del tuo eroe."),
            ("roll_d20", "🎲 Tira 1d20 Istantaneo", "Esegue immediatamente un d20 rapido."),
        ]
        for act_id, act_title, act_desc in actions:
            if (not q) or (q in act_title.lower()) or (q in act_desc.lower()) or (q in act_id):
                results.append({
                    "type": "ACTION",
                    "icon": "⚡",
                    "title": act_title,
                    "badge": "Azione Rapida",
                    "summary": act_desc,
                    "payload": act_id
                })

        # 4. REGOLE E COMPENDIO 5e
        mm = self._get_manuals_manager()
        if mm:
            try:
                rule_hits = mm.search(q if q else "")
                for r in rule_hits[:15]:
                    results.append({
                        "type": "RULE",
                        "icon": "📖",
                        "title": r.get("title", "Regola"),
                        "badge": f"{r.get('manual', '5e')} • {r.get('category', 'Regole')}",
                        "summary": r.get("summary") or r.get("content", "")[:180],
                        "payload": r
                    })
            except Exception as e:
                print("Error searching manuals in CommandPalette:", e)

        # Filtra per categoria attiva
        if self._active_filter != "ALL":
            results = [r for r in results if r["type"] == self._active_filter]

        self._results = results
        self.results_listbox.delete(0, tk.END)

        if not results:
            self.results_listbox.insert(tk.END, "  Nessun risultato trovato")
            self._update_preview(None)
            return

        for r in results:
            self.results_listbox.insert(tk.END, f" {r['icon']}  {r['title']}")

        self.results_listbox.select_set(0)
        self._update_preview(results[0])

    def _on_list_select(self, event=None):
        sel = self.results_listbox.curselection()
        if sel and sel[0] < len(self._results):
            self._update_preview(self._results[sel[0]])

    def _update_preview(self, item):
        self.prev_text.configure(state=tk.NORMAL)
        self.prev_text.delete("1.0", tk.END)

        if not item:
            self.prev_title_lbl.config(text="Nessun elemento")
            self.prev_badge_lbl.config(text="")
            self.prev_text.configure(state=tk.DISABLED)
            return

        self.prev_title_lbl.config(text=f"{item['icon']} {item['title']}")
        self.prev_badge_lbl.config(text=item.get("badge", ""))
        self.prev_text.insert(tk.END, item.get("summary", ""))
        self.prev_text.configure(state=tk.DISABLED)

        # Testo del bottone contestualizzato
        if item["type"] == "ROLL":
            self.btn_execute.config(text="🎲 Lancia Ora")
        elif item["type"] == "TOKEN":
            self.btn_execute.config(text="📍 Centra sulla Mappa")
        elif item["type"] == "RULE":
            self.btn_execute.config(text="📖 Leggi Regola Completa")
        else:
            self.btn_execute.config(text="↵ Esegui Azione")

    def _on_arrow_up(self, event=None):
        sel = self.results_listbox.curselection()
        if sel and sel[0] > 0:
            idx = sel[0] - 1
            self.results_listbox.selection_clear(0, tk.END)
            self.results_listbox.selection_set(idx)
            self.results_listbox.activate(idx)
            self.results_listbox.see(idx)
            self._update_preview(self._results[idx])
        return "break"

    def _on_arrow_down(self, event=None):
        sel = self.results_listbox.curselection()
        if sel and sel[0] < len(self._results) - 1:
            idx = sel[0] + 1
            self.results_listbox.selection_clear(0, tk.END)
            self.results_listbox.selection_set(idx)
            self.results_listbox.activate(idx)
            self.results_listbox.see(idx)
            self._update_preview(self._results[idx])
        elif not sel and self._results:
            self.results_listbox.selection_set(0)
            self._update_preview(self._results[0])
        return "break"

    def _on_enter(self, event=None):
        self._execute_selected()
        return "break"

    def _execute_selected(self):
        sel = self.results_listbox.curselection()
        if not sel or sel[0] >= len(self._results):
            return

        item = self._results[sel[0]]
        itype = item["type"]
        payload = item["payload"]

        if itype == "ROLL":
            formula = payload
            if self.on_action:
                self.on_action("roll", formula)
            self.destroy()
            show_toast(self.master, f"Tiro dadi eseguito: {formula}", title="Tiro Dadi", icon="🎲")

        elif itype == "TOKEN":
            token_name = payload
            if self.map_canvas and hasattr(self.map_canvas, "center_on_token"):
                self.map_canvas.center_on_token(token_name)
            if self.on_action:
                self.on_action("center_token", token_name)
            self.destroy()
            show_toast(self.master, f"Mappa centrata su: {token_name}", title="Token", icon="📍")

        elif itype == "ACTION":
            act_id = payload
            if act_id == "center_map" and self.map_canvas:
                self.map_canvas.center_view()
            elif act_id == "zoom_in" and self.map_canvas:
                self.map_canvas.zoom_in()
            elif act_id == "zoom_out" and self.map_canvas:
                self.map_canvas.zoom_out()
            elif act_id == "toggle_ruler" and self.map_canvas:
                self.map_canvas.ruler_mode = not getattr(self.map_canvas, "ruler_mode", False)
                self.map_canvas.redraw()
            elif act_id == "roll_d20":
                if self.on_action:
                    self.on_action("roll", "1d20")
            elif self.on_action:
                self.on_action("action", act_id)
            self.destroy()

        elif itype == "RULE":
            rule_dict = payload
            if isinstance(rule_dict, dict):
                show_rule_detail_popup(self.master, rule_dict)
            if self.on_action:
                self.on_action("rule", rule_dict)


