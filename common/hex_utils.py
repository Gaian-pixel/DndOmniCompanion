# hex_utils.py
import math

class Hex:
    def __init__(self, q, r):
        self.q = q
        self.r = r
        self.s = -q - r

    def __eq__(self, other):
        return self.q == other.q and self.r == other.r

    def __hash__(self):
        return hash((self.q, self.r))

class HexLayout:
    def __init__(self, size, origin):
        self.size = size
        self.origin = origin

    def hex_to_pixel(self, h: Hex) -> tuple[float, float]:
        x = self.size * (3/2 * h.q)
        y = self.size * (math.sqrt(3)/2 * h.q + math.sqrt(3) * h.r)
        return x + self.origin[0], y + self.origin[1]

    def pixel_to_hex(self, p: tuple[float, float]) -> Hex:
        px, py = (p[0] - self.origin[0]) / self.size, (p[1] - self.origin[1]) / self.size
        q = (2/3 * px)
        r = (-1/3 * px + math.sqrt(3)/3 * py)
        return self._hex_round(q, r)

    def hex_corners(self, h: Hex) -> list[tuple[float, float]]:
        center_x, center_y = self.hex_to_pixel(h)
        corners = []
        for i in range(6):
            angle_deg = 60 * i
            angle_rad = math.pi / 180 * angle_deg
            corners.append((center_x + self.size * math.cos(angle_rad),
                            center_y + self.size * math.sin(angle_rad)))
        return corners

    def _hex_round(self, q_frac, r_frac):
        return hex_round(q_frac, r_frac)

def hex_round(q_frac, r_frac) -> Hex:
    s_frac = -q_frac - r_frac
    q = int(round(q_frac))
    r = int(round(r_frac))
    s = int(round(s_frac))
    q_diff, r_diff, s_diff = abs(q - q_frac), abs(r - r_frac), abs(s - s_frac)
    if q_diff > r_diff and q_diff > s_diff:
        q = -r - s
    elif r_diff > s_diff:
        r = -q - s
    return Hex(q, r)

def hex_distance(a: Hex, b: Hex) -> int:
    return max(abs(a.q - b.q), abs(a.r - b.r), abs(a.s - b.s))

def get_sphere_hexes(origin: Hex, radius: int) -> list[Hex]:
    results = []
    for dq in range(-radius, radius + 1):
        for dr in range(max(-radius, -dq - radius), min(radius, -dq + radius) + 1):
            results.append(Hex(origin.q + dq, origin.r + dr))
    return results

def get_line_hexes(a: Hex, b: Hex) -> list[Hex]:
    dist = hex_distance(a, b)
    if dist == 0:
        return [a]
    results = []
    for i in range(dist + 1):
        t = i / dist
        q_frac = a.q + (b.q - a.q) * t
        r_frac = a.r + (b.r - a.r) * t
        results.append(hex_round(q_frac, r_frac))
    return results

def hex_linedraw(a: Hex, b: Hex) -> list[Hex]:
    dist = hex_distance(a, b)
    if dist == 0:
        return [a]
    results = []
    # Add a small epsilon offset to prevent exact edge intersection tie-breaking differently
    a_q, a_r = a.q + 1e-6, a.r + 1e-6
    b_q, b_r = b.q + 1e-6, b.r + 1e-6
    for i in range(dist + 1):
        t = i / dist
        q_frac = a_q + (b_q - a_q) * t
        r_frac = a_r + (b_r - a_r) * t
        results.append(hex_round(q_frac, r_frac))
    return results

def get_cone_hexes(origin: Hex, target: Hex, length: int) -> list[Hex]:
    """Approssimazione semplice di un cono in una griglia esagonale. 
    Il cono si espande verso il target."""
    if hex_distance(origin, target) == 0:
        return [origin]
    
    # Normalizziamo la direzione verso il target come un vettore 2D (q, r) approssimato
    dist = hex_distance(origin, target)
    dq = (target.q - origin.q) / dist
    dr = (target.r - origin.r) / dist
    
    results = []
    # Scansioniamo una sfera di raggio `length` e prendiamo solo gli esagoni 
    # che sono nel semispazio "in avanti" e entro un certo angolo.
    # Usiamo il prodotto scalare per filtrare.
    for hex in get_sphere_hexes(origin, length):
        v_q = hex.q - origin.q
        v_r = hex.r - origin.r
        dot = v_q * dq + v_r * dr
        h_dist = hex_distance(origin, hex)
        # Se il prodotto scalare è proporzionale alla distanza, è "davanti". 
        # Per un cono largo a ~60 gradi, limitiamo l'angolo.
        if h_dist > 0:
            cos_angle = dot / h_dist
            if cos_angle > 0.5: # Circa 60 gradi
                results.append(hex)
    
    # Aggiungiamo sempre l'origine
    if origin not in results:
        results.append(origin)
    return results


# --- Nuove funzioni richieste ---

def get_line_hexes(start_hex: Hex, target_hex: Hex, length_in_hexes: int) -> list[Hex]:
    dist = hex_distance(start_hex, target_hex)
    if dist == 0:
        return [start_hex]
    results = []
    a_q, a_r = start_hex.q + 1e-6, start_hex.r + 1e-6
    b_q, b_r = target_hex.q + 1e-6, target_hex.r + 1e-6
    for i in range(length_in_hexes):
        t = i / dist
        q_frac = a_q + (b_q - a_q) * t
        r_frac = a_r + (b_r - a_r) * t
        results.append(hex_round(q_frac, r_frac))
    return results

def get_cone_hexes(start_hex: Hex, target_hex: Hex, length_in_hexes: int) -> list[Hex]:
    if hex_distance(start_hex, target_hex) == 0:
        return [start_hex]
    
    layout = HexLayout(1.0, (0.0, 0.0))
    start_px = layout.hex_to_pixel(start_hex)
    target_px = layout.hex_to_pixel(target_hex)
    
    dir_x = target_px[0] - start_px[0]
    dir_y = target_px[1] - start_px[1]
    dir_len = math.hypot(dir_x, dir_y)
    dir_x /= dir_len
    dir_y /= dir_len
    
    results = []
    for h in get_sphere_hexes(start_hex, length_in_hexes):
        if h.q == start_hex.q and h.r == start_hex.r:
            results.append(h)
            continue
        h_px = layout.hex_to_pixel(h)
        v_x = h_px[0] - start_px[0]
        v_y = h_px[1] - start_px[1]
        v_len = math.hypot(v_x, v_y)
        
        cos_angle = (v_x * dir_x + v_y * dir_y) / v_len
        if cos_angle >= math.cos(math.radians(30)) - 1e-5:
            results.append(h)
            
    return results

def get_visible_hexes(origin: Hex, radius: int, walls: set) -> list[Hex]:
    visible = set()
    visible.add(origin)
    sphere = get_sphere_hexes(origin, radius)
    for h in sphere:
        if h == origin: continue
        line = hex_linedraw(origin, h)
        is_visible = True
        for p in line:
            if p in walls and p != origin and p != h:
                is_visible = False
                break
        if is_visible:
            visible.add(h)
    return list(visible)
