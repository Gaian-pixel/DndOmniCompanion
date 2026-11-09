import sys
import os
import time
import base64
import unittest
import tkinter as tk
from io import BytesIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from components.ui_components import HexMapCanvas
from PIL import Image


class TestRenderPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.geometry("1024x768")
            cls.root.withdraw()
        except Exception:
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def setUp(self):
        if not self.root:
            self.skipTest("Tkinter non disponibile in questo ambiente")

    def test_hex_map_culling_and_redraw_performance(self):
        """Verifica che il culling del viewport mantenga il rendering reattivo anche con migliaia di celle."""
        canvas = HexMapCanvas(self.root, width=1024, height=768)
        canvas.pack(fill=tk.BOTH, expand=True)
        self.root.update()

        # Genera mappa 50x50 (2500 esagoni)
        hexes = [[q, r] for q in range(-25, 25) for r in range(-25, 25)]
        map_data = {
            "hex_size": 30,
            "hex_border_color": "#333333",
            "hexes": hexes,
            "pois": {"0,0": "Town", "5,5": "Dungeon"},
            "walls": [[1, 1], [1, 2], [1, 3]],
            "fow_enabled": True,
            "fow_revealed": [[q, r] for q in range(-10, 10) for r in range(-10, 10)],
        }
        players_data = {
            "Hero": {"position": [0, 0], "hp": 25, "hp_max": 30, "is_party_member": True},
            "Goblin": {"position": [2, 2], "hp": 7, "hp_max": 7, "conditions": ["Avvelenato"]},
        }

        t0 = time.perf_counter()
        canvas.update_data(map_data, players_data, player_name="Hero")
        self.root.update()
        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000

        # Verifica che il rendering completi entro 500ms
        self.assertLess(elapsed_ms, 500, f"Redraw troppo lento: {elapsed_ms:.2f} ms")

        # Verifica culling su zoom
        class FakeWheelEvent:
            def __init__(self, delta=120):
                self.delta = delta
                self.x = 512
                self.y = 384
                self.num = 0

        t_zoom_0 = time.perf_counter()
        canvas._zoom(FakeWheelEvent(120))
        self.root.update()
        t_zoom_1 = time.perf_counter()
        zoom_ms = (t_zoom_1 - t_zoom_0) * 1000
        self.assertLess(zoom_ms, 250, f"Zoom redraw troppo lento: {zoom_ms:.2f} ms")

        canvas.destroy()


def benchmark():
    root = tk.Tk()
    root.geometry("1024x768")
    canvas = HexMapCanvas(root, width=1024, height=768)
    canvas.pack(fill=tk.BOTH, expand=True)
    root.update()

    hexes = [[q, r] for q in range(-25, 25) for r in range(-25, 25)]
    map_data = {
        "hex_size": 30,
        "hex_border_color": "#333333",
        "hexes": hexes,
        "pois": {"0,0": "Town", "5,5": "Dungeon"},
        "walls": [[1, 1], [1, 2], [1, 3]],
        "fow_enabled": True,
        "fow_revealed": [[q, r] for q in range(-10, 10) for r in range(-10, 10)],
    }
    players_data = {
        "Hero": {"position": [0, 0], "hp": 25, "hp_max": 30, "is_party_member": True},
        "Goblin": {"position": [2, 2], "hp": 7, "hp_max": 7, "conditions": ["Avvelenato"]},
    }

    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        canvas.update_data(map_data, players_data, player_name="Hero")
        root.update()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)

    avg_time = sum(times) / len(times)
    print(f"Redraw time (2500 hexes): {avg_time:.2f} ms per frame ({1000/avg_time:.1f} FPS)")
    root.destroy()


if __name__ == "__main__":
    unittest.main()
