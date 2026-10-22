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


if __name__ == "__main__":
    unittest.main()
