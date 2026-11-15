import unittest
from unittest.mock import patch
import tkinter as tk
import os
import json
import tempfile
from PIL import Image

from server.map_editor import MapEditorWindow, clip_polygon_to_rect
from common.hex_utils import Hex, HexLayout, SquareLayout


class TestMapEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.editor = MapEditorWindow(self.root)
        self.editor.withdraw()

    def tearDown(self):
        try:
            if hasattr(self.editor, "_zoom_timer") and self.editor._zoom_timer:
                self.editor.after_cancel(self.editor._zoom_timer)
            self.editor.destroy()
        except Exception:
            pass

    def test_initial_state(self):
        self.assertEqual(self.editor.zoom_level, 1.0)
        self.assertEqual(self.editor.pan_offset_x, 0.0)
        self.assertEqual(self.editor.pan_offset_y, 0.0)
        self.assertEqual(len(self.editor.grid_hexes), 0)
        self.assertEqual(self.editor.current_grid_type, "hex")

    def test_coordinate_transforms(self):
        wx, wy = 150.0, 220.0
        sx, sy = self.editor.world_to_screen(wx, wy)
        self.assertEqual((sx, sy), (150.0, 220.0))
        
        back_wx, back_wy = self.editor.screen_to_world(sx, sy)
        self.assertAlmostEqual(back_wx, wx)
        self.assertAlmostEqual(back_wy, wy)

        self.editor.zoom_level = 2.0
        self.editor.pan_offset_x = 50.0
        self.editor.pan_offset_y = -30.0

        sx, sy = self.editor.world_to_screen(wx, wy)
        self.assertAlmostEqual(sx, 150.0 * 2.0 + 50.0)
        self.assertAlmostEqual(sy, 220.0 * 2.0 - 30.0)

        back_wx, back_wy = self.editor.screen_to_world(sx, sy)
        self.assertAlmostEqual(back_wx, wx)
        self.assertAlmostEqual(back_wy, wy)

    def test_zoom_fixed_point_math(self):
        class MockEvent:
            num = 4
            delta = 120
            x = 400
            y = 300

        self.editor.pan_offset_x = 20.0
        self.editor.pan_offset_y = 40.0
        self.editor.zoom_level = 1.0

        before_wx, before_wy = self.editor.screen_to_world(400, 300)
        self.editor._zoom(MockEvent())

        after_wx, after_wy = self.editor.screen_to_world(400, 300)
        self.assertAlmostEqual(before_wx, after_wx, places=5)
        self.assertAlmostEqual(before_wy, after_wy, places=5)

    def test_pan_math(self):
        class MockEvent:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        self.editor._pan_start(MockEvent(100, 100))
        self.editor._pan_move(MockEvent(150, 180))

        self.assertEqual(self.editor.pan_offset_x, 50.0)
        self.assertEqual(self.editor.pan_offset_y, 80.0)

        self.editor._pan_move(MockEvent(160, 190))
        self.assertEqual(self.editor.pan_offset_x, 60.0)
        self.assertEqual(self.editor.pan_offset_y, 90.0)

    def test_zoom_in_zoom_out_buttons(self):
        initial_zoom = self.editor.zoom_level
        self.editor.zoom_in(center_x=200, center_y=150)
        self.assertGreater(self.editor.zoom_level, initial_zoom)

        zoomed = self.editor.zoom_level
        self.editor.zoom_out(center_x=200, center_y=150)
        self.assertLess(self.editor.zoom_level, zoomed)

    def test_reset_view_and_fit_to_window(self):
        test_img = Image.new("RGB", (800, 600), color="red")
        self.editor.base_image_original = test_img
        self.editor.zoom_level = 2.5
        self.editor.pan_offset_x = 120
        self.editor.pan_offset_y = -80

        self.editor.reset_view()
        self.assertEqual(self.editor.zoom_level, 1.0)
        self.assertEqual(self.editor.pan_offset_x, 0.0)
        self.assertEqual(self.editor.pan_offset_y, 0.0)

        self.editor.fit_to_window()
        self.assertGreater(self.editor.zoom_level, 0.0)
        self.assertLessEqual(self.editor.zoom_level, 1.0)

    def test_hex_and_square_layout_creation(self):
        layout_hex = self.editor._create_layout(35, "hex")
        self.assertIsInstance(layout_hex, HexLayout)
        self.assertEqual(layout_hex.origin, (0, 0))

        layout_sq = self.editor._create_layout(35, "square")
        self.assertIsInstance(layout_sq, SquareLayout)
        self.assertEqual(layout_sq.origin, (0, 0))

    def test_add_and_delete_hex(self):
        self.editor.hex_layout = self.editor._create_layout(35, "hex")
        self.editor.base_image_original = Image.new("RGB", (500, 500))
        
        self.editor._add_hex_at(100, 100)
        self.assertEqual(len(self.editor.grid_hexes), 1)
        added_hex = list(self.editor.grid_hexes)[0]
        self.assertIn(added_hex, self.editor.hex_to_canvas_id)

        self.editor._delete_hex_at(100, 100)
        self.assertEqual(len(self.editor.grid_hexes), 0)
        self.assertEqual(len(self.editor.hex_to_canvas_id), 0)

        self.editor._add_hex_at(600, 600)
        self.assertEqual(len(self.editor.grid_hexes), 0)

    def test_auto_grid_generation_flush_with_all_four_sides(self):
        W, H = 800, 600
        test_img = Image.new("RGB", (W, H), color="blue")
        self.editor.base_image_original = test_img

        # 1. Hex grid auto-generation: verify perfect flush match on all 4 sides (top, bottom, left, right)
        self.editor.current_hex_size = 60
        self.editor.grid_type_var.set("hex")
        self.editor.hex_layout = self.editor._create_layout(60, "hex")
        self.editor.generate_auto_grid(silent=True)

        self.assertGreater(len(self.editor.grid_hexes), 10)

        all_hex_x, all_hex_y = [], []
        for hex_id in self.editor.hex_to_canvas_id.values():
            coords = self.editor.canvas.coords(hex_id)
            all_hex_x.extend(coords[0::2])
            all_hex_y.extend(coords[1::2])

        self.assertEqual(min(all_hex_x), 0.0)
        self.assertEqual(max(all_hex_x), W)
        self.assertEqual(min(all_hex_y), 0.0)
        self.assertEqual(max(all_hex_y), H)

        # 2. Square grid auto-generation: verify perfect flush match on all 4 sides
        self.editor.grid_type_var.set("square")
        self.editor.on_grid_type_selected()

        self.assertGreater(len(self.editor.grid_hexes), 10)

        all_sq_x, all_sq_y = [], []
        for hex_id in self.editor.hex_to_canvas_id.values():
            coords = self.editor.canvas.coords(hex_id)
            all_sq_x.extend(coords[0::2])
            all_sq_y.extend(coords[1::2])

        self.assertEqual(min(all_sq_x), 0.0)
        self.assertEqual(max(all_sq_x), W)
        self.assertEqual(min(all_sq_y), 0.0)
        self.assertEqual(max(all_sq_y), H)

    def test_switch_grid_type_under_active_grab_never_freezes(self):
        test_img = Image.new("RGB", (800, 600), color="blue")
        self.editor.base_image_original = test_img
        self.editor.current_hex_size = 60
        self.editor.current_grid_type = "hex"
        self.editor.grid_type_var.set("hex")
        self.editor.hex_layout = self.editor._create_layout(60, "hex")
        self.editor.generate_auto_grid(silent=True)

        self.assertGreater(len(self.editor.grid_hexes), 0)
        
        # Simulate active grab from parent
        self.editor.grab_set()
        try:
            self.editor.grid_type_var.set("square")
            self.editor.on_grid_type_selected()

            self.assertEqual(self.editor.current_grid_type, "square")
            self.assertGreater(len(self.editor.grid_hexes), 0)
            
            # Switch back to hex
            self.editor.grid_type_var.set("hex")
            self.editor.on_grid_type_selected()
            self.assertEqual(self.editor.current_grid_type, "hex")
        finally:
            self.editor.grab_release()

    def test_poi_and_terrain_manipulation(self):
        self.editor.current_hex_size = 35
        self.editor.hex_layout = self.editor._create_layout(35, "hex")
        self.editor._add_hex_at(50, 50)
        target_hex = list(self.editor.grid_hexes)[0]

        # Toggle terrain
        self.editor.terrain_type_var.set("Ghiaccio")
        self.editor._toggle_terrain_at(50, 50)
        self.assertEqual(self.editor.difficult_terrain.get(target_hex), "ghiaccio")

        # Toggle terrain off
        self.editor._toggle_terrain_at(50, 50)
        self.assertNotIn(target_hex, self.editor.difficult_terrain)

        # Add POI with mock dialog
        with patch("tkinter.simpledialog.askstring", side_effect=["Locanda del Drago", "Un rifugio caldo"]):
            self.editor._add_poi_at(50, 50)
            self.assertIn(target_hex, self.editor.pois)
            self.assertEqual(self.editor.pois[target_hex]["title"], "Locanda del Drago")

    def test_image_and_grid_alignment_under_zoom_and_pan(self):
        test_img = Image.new("RGB", (400, 300), color="green")
        self.editor.base_image_original = test_img
        self.editor.current_hex_size = 30
        self.editor.hex_layout = self.editor._create_layout(30, "hex")
        
        self.editor._add_hex_at(200, 150)
        h = list(self.editor.grid_hexes)[0]
        
        wx, wy = self.editor.hex_layout.hex_to_pixel(h)
        
        self.editor.redraw()
        img_coords_init = self.editor.canvas.coords(self.editor.bg_canvas_id)
        self.assertEqual(img_coords_init, [0.0, 0.0])
        
        self.editor.zoom_level = 1.5
        self.editor.pan_offset_x = 40.0
        self.editor.pan_offset_y = -25.0
        self.editor.redraw()

        img_coords = self.editor.canvas.coords(self.editor.bg_canvas_id)
        self.assertEqual(img_coords, [40.0, -25.0])

        expected_center_screen_x = wx * 1.5 + 40.0
        expected_center_screen_y = wy * 1.5 - 25.0

        hex_canvas_id = self.editor.hex_to_canvas_id[h]
        poly_coords = self.editor.canvas.coords(hex_canvas_id)
        
        xs = poly_coords[0::2]
        ys = poly_coords[1::2]
        centroid_x = sum(xs) / len(xs)
        centroid_y = sum(ys) / len(ys)

        self.assertAlmostEqual(centroid_x, expected_center_screen_x, places=4)
        self.assertAlmostEqual(centroid_y, expected_center_screen_y, places=4)

    def test_save_and_load_map(self):
        self.editor.current_hex_size = 35
        self.editor.hex_layout = self.editor._create_layout(35, "hex")
        self.editor.grid_hexes.add(Hex(1, 2))
        self.editor.grid_hexes.add(Hex(3, 4))
        self.editor.pois[Hex(1, 2)] = {"title": "City of Gold", "caption": "A legendary place"}
        self.editor.difficult_terrain[Hex(3, 4)] = "palude"

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp_path = tmp.name

        try:
            pois_to_save = {f"{h.q},{h.r}": data for h, data in self.editor.pois.items()}
            diff_terrain_to_save = {f"{h.q},{h.r}": t_type for h, t_type in self.editor.difficult_terrain.items()}
            map_data = {
                "base_image_path": "",
                "hex_size": 35,
                "grid_type": "hex",
                "map_scale_type": "exploration",
                "hex_border_color": "white",
                "hexes": [[h.q, h.r] for h in self.editor.grid_hexes],
                "pois": pois_to_save,
                "difficult_terrain": diff_terrain_to_save
            }
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(map_data, f)

            self.editor._clear_grid()
            self.assertEqual(len(self.editor.grid_hexes), 0)

            with open(tmp_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)

            hex_size = loaded_data.get("hex_size", 35)
            self.editor.hex_layout = self.editor._create_layout(hex_size, loaded_data.get("grid_type", "hex"))
            for pos in loaded_data.get("hexes", []):
                self.editor.grid_hexes.add(Hex(pos[0], pos[1]))
            for k, p_data in loaded_data.get("pois", {}).items():
                parts = k.split(",")
                self.editor.pois[Hex(int(parts[0]), int(parts[1]))] = p_data
            for k, t_val in loaded_data.get("difficult_terrain", {}).items():
                parts = k.split(",")
                self.editor.difficult_terrain[Hex(int(parts[0]), int(parts[1]))] = t_val

            self.assertEqual(len(self.editor.grid_hexes), 2)
            self.assertIn(Hex(1, 2), self.editor.grid_hexes)
            self.assertIn(Hex(3, 4), self.editor.grid_hexes)
            self.assertEqual(self.editor.pois[Hex(1, 2)]["title"], "City of Gold")
            self.assertEqual(self.editor.difficult_terrain[Hex(3, 4)], "palude")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_tactical_layers_authoring_drag_paint_and_tool_exclusion(self):
        self.editor.base_image_original = Image.new("RGB", (500, 500), color="gray")
        self.editor.current_hex_size = 35
        self.editor.hex_layout = self.editor._create_layout(35, "hex")
        self.editor.generate_auto_grid(silent=True)

        class _Evt:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        def _hex_screen_evt(h):
            wx, wy = self.editor.hex_layout.hex_to_pixel(h)
            sx, sy = self.editor.world_to_screen(wx, wy)
            return _Evt(sx, sy)

        hexes_sorted = sorted(self.editor.grid_hexes, key=lambda h: (h.q, h.r))
        h1, h2, h3, h4, h5 = hexes_sorted[1], hexes_sorted[2], hexes_sorted[3], hexes_sorted[4], hexes_sorted[5]

        # Mutual exclusion tra tool editor
        self.editor.toggle_add_poi_mode()
        self.assertEqual(self.editor.editor_tool, "poi")
        self.assertTrue(self.editor.add_poi_mode)
        self.editor.set_editor_tool("wall")
        self.assertEqual(self.editor.editor_tool, "wall")
        self.assertFalse(self.editor.add_poi_mode)
        self.assertFalse(self.editor.add_terrain_mode)

        # Drag-paint muri: click su h1 + motion su h2 + motion su h1 non annulla h1 nello stesso tratto
        self.editor.on_canvas_left_click(_hex_screen_evt(h1))
        self.editor._on_canvas_b1_motion(_hex_screen_evt(h2))
        self.editor._on_canvas_b1_motion(_hex_screen_evt(h1))
        self.editor._on_canvas_b1_release()
        self.assertIn(h1, self.editor.walls)
        self.assertIn(h2, self.editor.walls)

        # Copertura 1/2 rimpiazza muro sulla stessa cella; 3/4 su h3
        self.editor.set_editor_tool("half_cover")
        self.editor.on_canvas_left_click(_hex_screen_evt(h1))
        self.assertIn(h1, self.editor.half_cover)
        self.assertNotIn(h1, self.editor.walls)
        self.editor.set_editor_tool("three_quarters_cover")
        self.editor.on_canvas_left_click(_hex_screen_evt(h3))
        self.assertIn(h3, self.editor.three_quarters_cover)

        # Ciclo stato porte su h4: closed -> open -> locked -> secret -> rimossa
        self.editor.set_editor_tool("door")
        ev4 = _hex_screen_evt(h4)
        for exp_state in ("closed", "open", "locked", "secret"):
            self.editor.on_canvas_left_click(ev4)
            self.assertEqual(self.editor.doors[h4]["state"], exp_state)
        self.editor.on_canvas_left_click(ev4)
        self.assertNotIn(h4, self.editor.doors)
        self.editor.on_canvas_left_click(ev4)
        self.assertIn(h4, self.editor.doors)

        # Ciclo luci su h5: Torcia (4) -> Lanterna (6) -> rimossa
        self.editor.set_editor_tool("light")
        ev5 = _hex_screen_evt(h5)
        self.editor.on_canvas_left_click(ev5)
        self.assertEqual(self.editor.lights[h5]["bright"], 4)
        self.editor.on_canvas_left_click(ev5)
        self.assertEqual(self.editor.lights[h5]["bright"], 6)
        self.editor.on_canvas_left_click(ev5)
        self.assertNotIn(h5, self.editor.lights)

        # Spawn point toggle su h5
        self.editor.set_editor_tool("spawn")
        self.editor.on_canvas_left_click(ev5)
        self.assertEqual(self.editor.spawn_point, [h5.q, h5.r])
        self.editor.on_canvas_left_click(ev5)
        self.assertIsNone(self.editor.spawn_point)

        # Toggle tool attivo su se stesso torna a "cells"
        self.editor.set_editor_tool("spawn")
        self.assertEqual(self.editor.editor_tool, "cells")

    def test_non_destructive_grid_type_switch_preserves_layers(self):
        self.editor.base_image_original = Image.new("RGB", (400, 400), color="navy")
        self.editor.current_hex_size = 35
        self.editor.current_grid_type = "hex"
        self.editor.grid_type_var.set("hex")
        self.editor.hex_layout = self.editor._create_layout(35, "hex")
        self.editor.generate_auto_grid(silent=True)

        self.editor.pois[Hex(2, 2)] = {"title": "Altare", "caption": "Antico"}
        self.editor.difficult_terrain[Hex(2, 3)] = "fango"
        self.editor.walls.add(Hex(3, 2))
        self.editor.half_cover.add(Hex(1, 2))
        self.editor.three_quarters_cover.add(Hex(1, 3))
        self.editor.doors[Hex(2, 1)] = {"q": 2, "r": 1, "state": "closed"}
        self.editor.lights[Hex(1, 1)] = {"q": 1, "r": 1, "bright": 4, "dim": 4}
        self.editor.spawn_point = [2, 2]

        self.editor.grid_type_var.set("square")
        self.editor.on_grid_type_selected()

        self.assertEqual(self.editor.current_grid_type, "square")
        self.assertIsInstance(self.editor.hex_layout, SquareLayout)
        self.assertEqual(len(self.editor.pois), 1)
        self.assertEqual(next(iter(self.editor.pois.values()))["title"], "Altare")
        self.assertEqual(len(self.editor.difficult_terrain), 1)
        self.assertEqual(len(self.editor.walls), 1)
        self.assertEqual(len(self.editor.half_cover), 1)
        self.assertEqual(len(self.editor.three_quarters_cover), 1)
        self.assertEqual(len(self.editor.doors), 1)
        self.assertEqual(len(self.editor.lights), 1)
        self.assertIsNotNone(self.editor.spawn_point)

    def test_load_and_save_tactical_layers_and_embedded_bg_fallback(self):
        import base64
        from io import BytesIO

        buf = BytesIO()
        Image.new("RGB", (64, 48), color="purple").save(buf, format="PNG")
        emb_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        with tempfile.TemporaryDirectory() as tmpd:
            src_path = os.path.join(tmpd, "src_map.json")
            out_path = os.path.join(tmpd, "saved_map.json")
            payload = {
                "base_image_path": "Z:/missing_host_path/dungeon.png",
                "bg_image_data": emb_b64,
                "hex_size": 60,
                "grid_type": "square",
                "hexes": [[q, r] for q in range(3) for r in range(3)],
                "walls": [[1, 1], ["0,0", "1,0"]],
                "half_cover": [[2, 1]],
                "three_quarters_cover": [[2, 2]],
                "doors": [{"q": 1, "r": 0, "state": "secret"}, {"edge": ["0,0", "0,1"], "state": "locked", "dc": 16}],
                "lights": [{"q": 0, "r": 2, "bright": 4, "dim": 4}],
                "spawn_point": [0, 0],
            }
            with open(src_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)

            with patch("tkinter.filedialog.askopenfilename", return_value=src_path), \
                 patch("tkinter.messagebox.showinfo"):
                self.editor.load_map_file()

            self.assertIsNotNone(self.editor.base_image_original)
            self.assertEqual(self.editor.base_image_original.size, (64, 48))
            self.assertIn(Hex(1, 1), self.editor.walls)
            self.assertEqual(self.editor._extra_walls, [["0,0", "1,0"]])
            self.assertIn(Hex(2, 1), self.editor.half_cover)
            self.assertIn(Hex(2, 2), self.editor.three_quarters_cover)
            self.assertEqual(self.editor.doors[Hex(1, 0)]["state"], "secret")
            self.assertEqual(len(self.editor._extra_doors), 1)
            self.assertIn(Hex(0, 2), self.editor.lights)
            self.assertEqual(self.editor.spawn_point, [0, 0])

            with patch("tkinter.filedialog.asksaveasfilename", return_value=out_path), \
                 patch("tkinter.messagebox.showinfo"):
                self.editor.save_map()

            with open(out_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertIn([1, 1], saved["walls"])
            self.assertIn(["0,0", "1,0"], saved["walls"])
            self.assertEqual(saved["half_cover"], [[2, 1]])
            self.assertEqual(saved["three_quarters_cover"], [[2, 2]])
            self.assertTrue(any(d.get("q") == 1 and d.get("r") == 0 and d.get("state") == "secret" for d in saved["doors"]))
            self.assertTrue(any(d.get("edge") == ["0,0", "0,1"] for d in saved["doors"]))
            self.assertEqual(saved["lights"], [{"q": 0, "r": 2, "bright": 4, "dim": 4}])
            self.assertEqual(saved["spawn_point"], [0, 0])
            self.assertTrue(saved.get("bg_image_data"))

    def test_undo_redo_and_resize_grid_preserve_and_prune(self):
        self.editor.grid_type_var.set("square")
        self.editor.current_grid_type = "square"
        self.editor.current_hex_size = 20
        self.editor.hex_layout = self.editor._create_layout(20, "square")
        self.editor.resize_grid(5, 4, push_undo=False)
        self.assertEqual(len(self.editor.grid_hexes), 20)

        px_in, py_in = self.editor.hex_layout.hex_to_pixel(Hex(1, 1))
        px_out, py_out = self.editor.hex_layout.hex_to_pixel(Hex(4, 3))
        self.editor._toggle_layer_flag_at(px_in, py_in, "wall", silent=True)
        self.editor._drag_undo_pushed = False
        self.editor._toggle_layer_flag_at(px_out, py_out, "wall", silent=True)
        self.editor._drag_undo_pushed = False
        self.assertEqual(len(self.editor.walls), 2)

        # Resize smaller: keeps (1,1), prunes (4,3), push_undo=True makes it undoable
        self.editor.resize_grid(3, 3, push_undo=True)
        self.assertEqual(len(self.editor.grid_hexes), 9)
        self.assertEqual(self.editor.walls, {Hex(1, 1)})

        self.assertTrue(self.editor.undo())
        self.assertEqual(len(self.editor.grid_hexes), 20)
        self.assertEqual(self.editor.walls, {Hex(1, 1), Hex(4, 3)})

        self.assertTrue(self.editor.redo())
        self.assertEqual(len(self.editor.grid_hexes), 9)
        self.assertEqual(self.editor.walls, {Hex(1, 1)})

    def test_gridless_auto_grid_and_new_layers_roundtrip(self):
        self.editor.base_image_original = Image.new("RGB", (180, 90), color="black")
        self.editor.current_hex_size = 30  # SquareLayout size = 45px -> 4 cols x 2 rows = 8
        self.editor.current_grid_type = "none"
        self.editor.grid_type_var.set("none")
        self.editor.hex_layout = self.editor._create_layout(30, "none")
        self.editor.generate_auto_grid(silent=True)
        self.assertEqual(self.editor.grid_hexes, {Hex(q, r) for q in range(4) for r in range(2)})

        px0, py0 = self.editor.hex_layout.hex_to_pixel(Hex(0, 0))
        px1, py1 = self.editor.hex_layout.hex_to_pixel(Hex(1, 0))
        px2, py2 = self.editor.hex_layout.hex_to_pixel(Hex(2, 1))
        px3, py3 = self.editor.hex_layout.hex_to_pixel(Hex(3, 1))
        self.editor._toggle_trap_at(px0, py0, silent=True, name="Fossa Segreta", dc=15, damage="2d6")
        self.editor._toggle_loot_at(px1, py1, silent=True, item_name="Pozione di Guarigione", gold=40)
        self.editor._toggle_teleport_at(px2, py2, silent=True, dest_map="cripta.json")
        self.editor._toggle_room_pin_at(px3, py3, silent=True, title="Ingresso", read_aloud="Aria gelida.")

        with tempfile.TemporaryDirectory() as tmpd:
            out_path = os.path.join(tmpd, "layers_map.json")
            with patch("tkinter.filedialog.asksaveasfilename", return_value=out_path), \
                 patch("tkinter.messagebox.showinfo"):
                self.editor.save_map()
            self.editor._clear_grid(preserve_layers=False)
            self.assertEqual(len(self.editor.traps), 0)
            with patch("tkinter.filedialog.askopenfilename", return_value=out_path), \
                 patch("tkinter.messagebox.showinfo"):
                self.editor.load_map_file()

        self.assertEqual(self.editor.traps[Hex(0, 0)]["name"], "Fossa Segreta")
        self.assertEqual(self.editor.loots[Hex(1, 0)]["gold"], 40)
        self.assertEqual(self.editor.teleports[Hex(2, 1)], "cripta.json")
        self.assertEqual(self.editor.room_pins[Hex(3, 1)]["title"], "Ingresso")

    def test_task039_load_base_image_clears_stale_bg_and_removed_spawn_stays_deleted(self):
        with tempfile.TemporaryDirectory() as tmpd:
            img1 = os.path.join(tmpd, "bg1.png")
            img2 = os.path.join(tmpd, "bg2.png")
            map1 = os.path.join(tmpd, "map1.json")
            map2 = os.path.join(tmpd, "map2.json")
            Image.new("RGB", (64, 64), color="red").save(img1)
            Image.new("RGB", (96, 96), color="blue").save(img2)

            initial_payload = {
                "grid_type": "square",
                "hex_size": 30,
                "hexes": [[0, 0], [1, 0]],
                "spawn_point": [1, 0],
                "bg_image_data": "STALE_BASE64_BLOB",
                "bg_image_hash": "stale_hash_123",
            }
            with open(map1, "w", encoding="utf-8") as f:
                json.dump(initial_payload, f)

            with patch("tkinter.filedialog.askopenfilename", return_value=map1), \
                 patch("server.map_editor.messagebox.showinfo"), \
                 patch("server.map_editor.messagebox.showerror"), \
                 patch("server.map_editor.messagebox.showwarning"), \
                 patch("tkinter.messagebox.showinfo"):
                self.editor.load_map_file()
            self.assertEqual(self.editor.spawn_point, [1, 0])

            # Replace base image & clear spawn_point, then save
            with patch("tkinter.filedialog.askopenfilename", return_value=img2), \
                 patch("server.map_editor.messagebox.askyesno", return_value=False), \
                 patch("server.map_editor.messagebox.showinfo"), \
                 patch("tkinter.messagebox.askyesno", return_value=False):
                self.editor.load_base_image()
            self.assertNotIn("bg_image_data", self.editor._preserved_map_metadata)
            self.assertNotIn("bg_image_hash", self.editor._preserved_map_metadata)

            self.editor.spawn_point = None
            with patch("tkinter.filedialog.asksaveasfilename", return_value=map2), \
                 patch("server.map_editor.messagebox.showinfo"), \
                 patch("server.map_editor.messagebox.showerror"), \
                 patch("tkinter.messagebox.showinfo"):
                self.editor.save_map()

            with open(map2, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertNotIn("spawn_point", saved)
            self.assertNotEqual(saved.get("bg_image_data"), "STALE_BASE64_BLOB")


if __name__ == "__main__":
    unittest.main()
