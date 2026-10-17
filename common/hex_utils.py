# hex_utils.py
import math

class Hex:
    def __init__(self, q, r):
        self.q = q
        self.r = r
        self.s = -q - r

    def __eq__(self, other):
        if not isinstance(other, Hex):
            return False
        return self.q == other.q and self.r == other.r

    def __hash__(self):
        return hash((self.q, self.r))

    def __getitem__(self, item):
        if item == 0:
            return self.q
        elif item == 1:
            return self.r
        elif item == 2:
            return self.s
        raise IndexError("Hex index out of range")

    def distance(self, other: "Hex", grid_type: str = "hex") -> int:
        return int(grid_distance(self, other, grid_type))

class SquareLayout:
    def __init__(self, size, origin=(0, 0)):
        self.size = size
        self.origin = origin

    def hex_to_pixel(self, h: "Hex") -> tuple[float, float]:
        """Convert grid cell (q, r) to pixel center coordinates."""
        q = getattr(h, 'q', h[0])
        r = getattr(h, 'r', h[1])
        x = self.origin[0] + (q + 0.5) * self.size
        y = self.origin[1] + (r + 0.5) * self.size
        return x, y

    def pixel_to_hex(self, p: tuple[float, float]) -> Hex:
        """Convert pixel coordinates to grid cell (q, r)."""
        px = p[0] - self.origin[0]
        py = p[1] - self.origin[1]
        q = int(math.floor(px / self.size))
        r = int(math.floor(py / self.size))
        return Hex(q, r)

    def hex_corners(self, h: "Hex") -> list[tuple[float, float]]:
        """Return 4 corner points of the square cell."""
        cx, cy = self.hex_to_pixel(h)
        half = self.size / 2.0
        return [
            (cx - half, cy - half),
            (cx + half, cy - half),
            (cx + half, cy + half),
            (cx - half, cy + half)
        ]

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

def grid_distance(a: Hex, b: Hex, grid_type: str = "hex") -> float:
    aq = a.q if hasattr(a, 'q') else a[0]
    ar = a.r if hasattr(a, 'r') else a[1]
    bq = b.q if hasattr(b, 'q') else b[0]
    br = b.r if hasattr(b, 'r') else b[1]
    if grid_type == "square":
        return max(abs(aq - bq), abs(ar - br))
    elif grid_type in ("none", "gridless"):
        return math.hypot(aq - bq, ar - br)
    else:
        as_ = a.s if hasattr(a, 's') else (-aq - ar)
        bs_ = b.s if hasattr(b, 's') else (-bq - br)
        return max(abs(aq - bq), abs(ar - br), abs(as_ - bs_))

def hex_distance(a: Hex, b: Hex) -> int:
    return int(grid_distance(a, b, "hex"))

def get_sphere_hexes(origin: Hex, radius: int, grid_type: str = "hex") -> list[Hex]:
    results = []
    if grid_type in ("square", "none", "gridless"):
        for dq in range(-radius, radius + 1):
            for dr in range(-radius, radius + 1):
                results.append(Hex(origin.q + dq, origin.r + dr))
    else:
        for dq in range(-radius, radius + 1):
            for dr in range(max(-radius, -dq - radius), min(radius, -dq + radius) + 1):
                results.append(Hex(origin.q + dq, origin.r + dr))
    return results

def hex_linedraw(a: Hex, b: Hex, grid_type: str = "hex") -> list[Hex]:
    dist = int(grid_distance(a, b, grid_type))
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
        if grid_type in ("square", "none", "gridless"):
            results.append(Hex(int(round(q_frac)), int(round(r_frac))))
        else:
            results.append(hex_round(q_frac, r_frac))
    return results

def get_line_hexes(start_hex: Hex, target_hex: Hex, length_in_hexes: int = None) -> list[Hex]:
    dist = hex_distance(start_hex, target_hex)
    if dist == 0:
        return [start_hex]
    if length_in_hexes is None:
        length_in_hexes = dist + 1
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
    if dir_len == 0:
        return [start_hex]
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
        if v_len == 0:
            results.append(h)
            continue
        
        cos_angle = (v_x * dir_x + v_y * dir_y) / v_len
        if cos_angle >= math.cos(math.radians(30)) - 1e-5:
            results.append(h)
            
    return results

def has_line_of_sight(origin: Hex, target: Hex, walls) -> bool:
    """Verifica se c'è linea di vista diretta tra origin e target su griglia esagonale.
    Se un esagono intermedio è un muro, la linea di vista è ostruita."""
    if origin == target:
        return True
    wall_set = set()
    for w in walls:
        if isinstance(w, Hex):
            wall_set.add((w.q, w.r))
        elif isinstance(w, (list, tuple)) and len(w) >= 2:
            wall_set.add((w[0], w[1]))
            
    line = hex_linedraw(origin, target)
    for p in line:
        if p != origin and p != target and (p.q, p.r) in wall_set:
            return False
    return True

def get_visible_hexes(origin: Hex, radius: int, walls, grid_type: str = "hex") -> list[Hex]:
    """Restituisce tutti gli esagoni o celle entro il raggio privi di ostruzioni visive da muri."""
    visible = set()
    visible.add(origin)
    wall_set = set()
    for w in walls:
        if isinstance(w, Hex):
            wall_set.add((w.q, w.r))
        elif isinstance(w, (list, tuple)) and len(w) >= 2:
            wall_set.add((w[0], w[1]))
            
    sphere = get_sphere_hexes(origin, radius, grid_type=grid_type)
    for h in sphere:
        if h == origin:
            continue
        line = hex_linedraw(origin, h, grid_type=grid_type)
        is_visible = True
        for p in line:
            if (p.q, p.r) in wall_set and p != origin and p != h:
                is_visible = False
                break
        if is_visible:
            visible.add(h)
    return list(visible)

def get_cover_between(origin: Hex, target: Hex, half_cover=None, three_quarters=None, intermediate_creatures=None) -> tuple[int, str]:
    """
    Calcola la Copertura D&D 5e tra origin e target.
    Regole 5e:
    - Se la traiettoria interseca una creatura (alleata o nemica): Mezza Copertura (+2 CA e +2 TS Des).
    - Se interseca un ostacolo di mezza copertura (muretto, rocce basse): +2 CA.
    - Se interseca un ostacolo di tre quarti (grata, feritoia, tronco massiccio): +5 CA.
    Ritorna: (bonus_ca, nome_copertura)
    """
    if origin == target:
        return (0, "")
        
    line = hex_linedraw(origin, target)
    intermediate = [p for p in line if p != origin and p != target]
    if not intermediate:
        return (0, "")
        
    half_set = set()
    if half_cover:
        for h in half_cover:
            if isinstance(h, Hex): half_set.add((h.q, h.r))
            elif isinstance(h, (list, tuple)) and len(h) >= 2: half_set.add((h[0], h[1]))
            
    tq_set = set()
    if three_quarters:
        for t in three_quarters:
            if isinstance(t, Hex): tq_set.add((t.q, t.r))
            elif isinstance(t, (list, tuple)) and len(t) >= 2: tq_set.add((t[0], t[1]))

    creature_set = set()
    if intermediate_creatures:
        for c in intermediate_creatures:
            if isinstance(c, Hex): creature_set.add((c.q, c.r))
            elif isinstance(c, (list, tuple)) and len(c) >= 2: creature_set.add((c[0], c[1]))
            elif hasattr(c, "position") and c.position: creature_set.add((c.position[0], c.position[1]))

    # Check Tre Quarti (+5 CA)
    for p in intermediate:
        if (p.q, p.r) in tq_set:
            return (5, "Tre Quarti di Copertura")

    # Check Mezza Copertura (+2 CA)
    for p in intermediate:
        if (p.q, p.r) in half_set:
            return (2, "Mezza Copertura (Ostacolo)")
        if (p.q, p.r) in creature_set:
            return (2, "Mezza Copertura (Creatura interposta)")

    return (0, "")
