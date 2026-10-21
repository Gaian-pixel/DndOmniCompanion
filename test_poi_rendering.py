import unittest
import tkinter as tk
from unittest.mock import MagicMock
from PIL import Image

from components.ui_components import HexMapCanvas
from common.hex_utils import Hex, HexLayout
from server.map_editor import MapEditorWindow


class TestPOIRendering(unittest.TestCase):
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
        self.frame = tk.Frame(self.root)
        self.frame.pack()
        self.canvas = HexMapCanvas(self.frame, width=800, height=600)
        self.canvas.pack()
        self.canvas.hex_layout = HexLayout(size=30, origin=(400, 300))
        self.root.update_idletasks()

    def tearDown(self):
        try:
            self.canvas.destroy()
            self.frame.destroy()
        except Exception:
            pass

    def test_canvas_poi_only_borders_colored(self):
        # Configure map with a POI at (0, 0)
        self.canvas.map_data = {
            "hex_size": 30,
            "grid_type": "hex",
            "hex_border_color": "#FFFFFF",
            "hexes": [[0, 0], [1, 0]],
            "pois": {"0,0": {"title": "Taverna", "caption": "Un posto accogliente"}}
        }
        self.canvas.redraw()

        # Find all polygon items created on canvas
        poly_ids = self.canvas.find_withtag("all")
        poi_poly_found = False

        for pid in poly_ids:
            if self.canvas.type(pid) == "polygon":
                outline = self.canvas.itemcget(pid, "outline")
                fill = self.canvas.itemcget(pid, "fill")
                if outline.lower() == "#ffd700":
                    poi_poly_found = True
                    # Fill MUST be empty so the map image underneath is not covered!
                    self.assertEqual(fill, "", "POI fill must be empty so it does not obscure the map image")

        self.assertTrue(poi_poly_found, "A polygon with gold outline (#FFD700) should be rendered for the POI")

    def test_map_editor_poi_border_color(self):
        editor = MagicMock(spec=MapEditorWindow)
        editor.canvas = self.canvas
        editor.POI_COLOR = "#FFD700"
        editor.hex_border_color = "#FFFFFF"
        editor.zoom_level = 1.0
        editor.pan_offset_x = 0
        editor.pan_offset_y = 0
        editor.hex_layout = HexLayout(size=30, origin=(400, 300))
        editor.difficult_terrain = {}
        editor.pois = {Hex(2, 2): {"title": "Torre", "caption": ""}}
        editor.hex_to_canvas_id = {}
        editor.get_terrain_style = lambda h: None

        # When an image is present
        editor.base_image_original = Image.new("RGB", (800, 600))
        canvas_id = MapEditorWindow._draw_single_hex(editor, Hex(2, 2))
        self.assertIsNotNone(canvas_id)
        outline = self.canvas.itemcget(canvas_id, "outline")
        fill = self.canvas.itemcget(canvas_id, "fill")
        self.assertEqual(outline.lower(), "#ffd700")
        self.assertEqual(fill, "")

        # Test _update_grid_color preserves POI outline
        editor.hex_to_canvas_id[Hex(2, 2)] = canvas_id
        editor.hex_border_color = "#FF0000"
        MapEditorWindow._update_grid_color(editor)
        self.assertEqual(self.canvas.itemcget(canvas_id, "outline").lower(), "#ffd700")


if __name__ == "__main__":
    unittest.main()
