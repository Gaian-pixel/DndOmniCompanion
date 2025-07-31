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