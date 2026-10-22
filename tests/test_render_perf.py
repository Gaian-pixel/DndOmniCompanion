import time
import tkinter as tk
from components.ui_components import HexMapCanvas
from PIL import Image
import base64
from io import BytesIO

def benchmark():
    root = tk.Tk()
    root.geometry("1024x768")
    canvas = HexMapCanvas(root, width=1024, height=768)
    canvas.pack(fill=tk.BOTH, expand=True)
    root.update()

    # Generate test map data with 2500 hexes (50x50)
    hexes = []
    for q in range(-25, 25):
        for r in range(-25, 25):
            hexes.append([q, r])

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

    print(f"Total hexes in test: {len(hexes)}")

    # Measure redraw without bg image
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        canvas.update_data(map_data, players_data, player_name="Hero")
        root.update()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)

    avg_time = sum(times) / len(times)
    print(f"Redraw time (no bg image, 2500 hexes): {avg_time:.2f} ms per frame ({1000/avg_time:.1f} FPS)")

    # Measure zoom performance (simulate 10 zoom steps)
    class FakeEvent:
        def __init__(self, delta=120, x=512, y=384, num=0):
            self.delta = delta
            self.x = x
            self.y = y
            self.num = num

    zoom_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        canvas._zoom(FakeEvent(120))
        root.update()
        t1 = time.perf_counter()
        zoom_times.append((t1 - t0) * 1000)

    avg_zoom = sum(zoom_times) / len(zoom_times)
    print(f"Zoom step time (2500 hexes): {avg_zoom:.2f} ms per step ({1000/avg_zoom:.1f} FPS)")

    # Test with 10,000 hexes (100x100)
    hexes_10k = [[q, r] for q in range(-50, 50) for r in range(-50, 50)]
    map_data["hexes"] = hexes_10k
    t0 = time.perf_counter()
    canvas.update_data(map_data, players_data, player_name="Hero")
    root.update()
    t1 = time.perf_counter()
    print(f"Redraw time (10,000 hexes): {(t1 - t0)*1000:.2f} ms")

    # Test with background image (nave_pirata.jpg)
    try:
        with open("maps/nave_pirata.jpg", "rb") as f:
            b64_img = base64.b64encode(f.read()).decode('utf-8')
        map_data["bg_image_data"] = b64_img
        bg_times = []
        for _ in range(5):
            t0 = time.perf_counter()
            canvas.update_data(map_data, players_data, player_name="Hero")
            root.update()
            t1 = time.perf_counter()
            bg_times.append((t1 - t0) * 1000)
        avg_bg = sum(bg_times) / len(bg_times)
        print(f"Redraw time with BG image (nave_pirata): {avg_bg:.2f} ms")
    except Exception as e:
        print("Bg test skipped:", e)

    root.destroy()

if __name__ == "__main__":
    benchmark()
