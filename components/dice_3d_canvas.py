# components/dice_3d_canvas.py
"""
Motore 3D Vettoriale Nativo per Dadi Poliedrici D&D 5e su Canvas Tkinter.
Zero dipendenze esterne (solo librerie standard math, random, wave, struct, tkinter).

Supporta tutti i dadi poliedrici:
- d4 (Tetraedro regolare)
- d6 (Cubo / Esaedro)
- d8 (Ottaedro regolare)
- d10 (Trapezoedro pentagonale 0-9)
- d12 (Dodecaedro regolare)
- d20 (Icosaedro regolare)
- d100 (Percentile '00'-'90')

Funzionalità:
- Shading Lambertiano direzionale con riflessi metallici e bordi dorati Dark Fantasy.
- Z-sorting (Painter's algorithm) per rendering 3D prospettico privo di glitch.
- Fisica balistica con gravità, rimbalzi elastici su tavolo/bordi, frizione e decelerazione.
- Orientamento esatto sulla faccia estratta dal motore dei dadi (common.dice).
- Effetti speciali per Successo Critico (20 naturale) e Fallimento Critico (1 naturale).
- Supporto a lanci multipli e Vantaggio/Svantaggio (il dado scartato si attenua/dissolve).
- Generazione sintetica ed esecuzione locale di effetti sonori di rimbalzo dadi (WAV).
"""

import math
import random
import os
import struct
import wave
import threading
import tkinter as tk
from typing import List, Dict, Any, Tuple, Optional, Callable


# ==============================================================================
# 1. MATEMATICA VETTORIALE, MATRICIALE E QUATERNIONI 3D
# ==============================================================================

def vec3_norm(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / l, v[1] / l, v[2] / l) if l > 1e-9 else (0.0, 0.0, 1.0)

def vec3_dot(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

def vec3_cross(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0]
    )

def vec3_add(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def vec3_sub(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def vec3_scale(v: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def quat_from_axis_angle(axis: Tuple[float, float, float], angle: float) -> Tuple[float, float, float, float]:
    half = angle * 0.5
    s = math.sin(half)
    ax = vec3_norm(axis)
    return (math.cos(half), ax[0] * s, ax[1] * s, ax[2] * s)

def quat_multiply(q1: Tuple[float, float, float, float], q2: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    )

def quat_to_matrix(q: Tuple[float, float, float, float]) -> List[List[float]]:
    w, x, y, z = q
    return [
        [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w),       2.0 * (x * z + y * w)],
        [2.0 * (x * y + z * w),       1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
        [2.0 * (x * z - y * w),       2.0 * (y * z + x * w),       1.0 - 2.0 * (x * x + y * y)]
    ]

def quat_slerp(q1: Tuple[float, float, float, float], q2: Tuple[float, float, float, float], t: float) -> Tuple[float, float, float, float]:
    dot = q1[0] * q2[0] + q1[1] * q2[1] + q1[2] * q2[2] + q1[3] * q2[3]
    if dot < 0.0:
        q2 = (-q2[0], -q2[1], -q2[2], -q2[3])
        dot = -dot
    if dot > 0.9995:
        res = (
            q1[0] + t * (q2[0] - q1[0]),
            q1[1] + t * (q2[1] - q1[1]),
            q1[2] + t * (q2[2] - q1[2]),
            q1[3] + t * (q2[3] - q1[3])
        )
        l = math.sqrt(sum(x * x for x in res))
        return (res[0] / l, res[1] / l, res[2] / l, res[3] / l)
    
    theta = math.acos(max(-1.0, min(1.0, dot)))
    sin_theta = math.sin(theta)
    w1 = math.sin((1.0 - t) * theta) / sin_theta
    w2 = math.sin(t * theta) / sin_theta
    return (
        w1 * q1[0] + w2 * q2[0],
        w1 * q1[1] + w2 * q2[1],
        w1 * q1[2] + w2 * q2[2],
        w1 * q1[3] + w2 * q2[3]
    )

def matrix_to_quat(M: List[List[float]]) -> Tuple[float, float, float, float]:
    tr = M[0][0] + M[1][1] + M[2][2]
    if tr > 0.0:
        S = math.sqrt(tr + 1.0) * 2.0
        w = 0.25 * S
        x = (M[2][1] - M[1][2]) / S
        y = (M[0][2] - M[2][0]) / S
        z = (M[1][0] - M[0][1]) / S
    elif M[0][0] > M[1][1] and M[0][0] > M[2][2]:
        S = math.sqrt(max(1e-9, 1.0 + M[0][0] - M[1][1] - M[2][2])) * 2.0
        w = (M[2][1] - M[1][2]) / S
        x = 0.25 * S
        y = (M[0][1] + M[1][0]) / S
        z = (M[0][2] + M[2][0]) / S
    elif M[1][1] > M[2][2]:
        S = math.sqrt(max(1e-9, 1.0 + M[1][1] - M[0][0] - M[2][2])) * 2.0
        w = (M[0][2] - M[2][0]) / S
        x = (M[0][1] + M[1][0]) / S
        y = 0.25 * S
        z = (M[1][2] + M[2][1]) / S
    else:
        S = math.sqrt(max(1e-9, 1.0 + M[2][2] - M[0][0] - M[1][1])) * 2.0
        w = (M[1][0] - M[0][1]) / S
        x = (M[0][2] + M[2][0]) / S
        y = (M[1][2] + M[2][1]) / S
        z = 0.25 * S
    l = math.sqrt(w * w + x * x + y * y + z * z)
    return (w / l, x / l, y / l, z / l) if l > 1e-9 else (1.0, 0.0, 0.0, 0.0)

def mat_vec_mul(M: List[List[float]], v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (
        M[0][0] * v[0] + M[0][1] * v[1] + M[0][2] * v[2],
        M[1][0] * v[0] + M[1][1] * v[1] + M[1][2] * v[2],
        M[2][0] * v[0] + M[2][1] * v[1] + M[2][2] * v[2]
    )

def get_face_target_matrix(face_normal: Tuple[float, float, float], face_up: Tuple[float, float, float]) -> List[List[float]]:
    """Calcola la matrice di rotazione ortogonale che orienta face_normal verso la telecamera (+Z) e face_up verso l'alto dello schermo in 3D (+Y)."""
    n = vec3_norm(face_normal)
    d = vec3_dot(face_up, n)
    u = vec3_norm((face_up[0] - d * n[0], face_up[1] - d * n[1], face_up[2] - d * n[2]))
    r = vec3_norm(vec3_cross(u, n))
    return [
        [r[0], r[1], r[2]],
        [u[0], u[1], u[2]],
        [n[0], n[1], n[2]]
    ]


# ==============================================================================
# 2. DEFINIZIONI GEOMETRICHE DEI POLIEDRI (d4, d6, d8, d10, d12, d20, d100)
# ==============================================================================

class PolyhedronModel:
    def __init__(
        self,
        name: str,
        vertices: List[Tuple[float, float, float]],
        faces: List[List[int]],
        face_numbers: List[Any],
        face_normals: List[Tuple[float, float, float]],
        face_ups: List[Tuple[float, float, float]],
        base_color: str,
        highlight_color: str,
        text_color: str
    ):
        self.name = name
        self.vertices = [vec3_norm(v) for v in vertices]
        self.faces = faces
        self.face_numbers = face_numbers
        self.face_normals = [vec3_norm(n) for n in face_normals]
        self.face_ups = [vec3_norm(u) for u in face_ups]
        self.base_color = base_color
        self.highlight_color = highlight_color
        self.text_color = text_color


def _build_d4() -> PolyhedronModel:
    # Tetrahedron: 4 vertices, 4 faces
    verts = [
        vec3_norm(( 1.0,  1.0,  1.0)),
        vec3_norm(( 1.0, -1.0, -1.0)),
        vec3_norm((-1.0,  1.0, -1.0)),
        vec3_norm((-1.0, -1.0,  1.0))
    ]
    faces = [
        [0, 1, 2],
        [0, 2, 3],
        [0, 3, 1],
        [1, 3, 2]
    ]
    normals = []
    ups = []
    for f in faces:
        p0, p1, p2 = verts[f[0]], verts[f[1]], verts[f[2]]
        n = vec3_norm(vec3_cross(vec3_sub(p1, p0), vec3_sub(p2, p0)))
        c = vec3_scale(vec3_add(vec3_add(p0, p1), p2), 1.0 / 3.0)
        if vec3_dot(n, c) < 0:
            n = vec3_scale(n, -1.0)
        normals.append(n)
        ups.append(vec3_norm(vec3_sub(p0, c)))
    nums = [1, 2, 3, 4]
    return PolyhedronModel("d4", verts, faces, nums, normals, ups, "#334155", "#64748B", "#F59E0B")


def _build_d6() -> PolyhedronModel:
    # Cube: 8 vertices, 6 faces
    verts = []
    for x in (-1.0, 1.0):
        for y in (-1.0, 1.0):
            for z in (-1.0, 1.0):
                verts.append(vec3_norm((x, y, z)))
    
    # 6 faces: opposites sum to 7 (1-6, 2-5, 3-4)
    # Normals: Front(0,0,1)=1, Back(0,0,-1)=6, Top(0,1,0)=2, Bottom(0,-1,0)=5, Right(1,0,0)=3, Left(-1,0,0)=4
    faces = [
        [1, 3, 7, 5], # Front (+Z) -> 1
        [0, 4, 6, 2], # Back (-Z) -> 6
        [2, 3, 7, 6], # Top (+Y) -> 2
        [0, 1, 5, 4], # Bottom (-Y) -> 5
        [4, 5, 7, 6], # Right (+X) -> 3
        [0, 2, 3, 1]  # Left (-X) -> 4
    ]
    normals = [
        (0.0, 0.0, 1.0),
        (0.0, 0.0, -1.0),
        (0.0, 1.0, 0.0),
        (0.0, -1.0, 0.0),
        (1.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0)
    ]
    ups = [
        (0.0, 1.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, -1.0),
        (0.0, 0.0, 1.0),
        (0.0, 1.0, 0.0),
        (0.0, 1.0, 0.0)
    ]
    nums = [1, 6, 2, 5, 3, 4]
    return PolyhedronModel("d6", verts, faces, nums, normals, ups, "#1E3A8A", "#3B82F6", "#FFFFFF")


def _build_d8() -> PolyhedronModel:
    # Octahedron: 6 vertices, 8 faces
    verts = [
        ( 1.0,  0.0,  0.0), # 0
        (-1.0,  0.0,  0.0), # 1
        ( 0.0,  1.0,  0.0), # 2
        ( 0.0, -1.0,  0.0), # 3
        ( 0.0,  0.0,  1.0), # 4
        ( 0.0,  0.0, -1.0)  # 5
    ]
    faces = [
        [0, 2, 4], [1, 3, 5], # 1 and 8 (opposites)
        [0, 4, 3], [1, 5, 2], # 2 and 7
        [0, 3, 5], [1, 2, 4], # 3 and 6
        [0, 5, 2], [1, 4, 3]  # 4 and 5
    ]
    nums = [1, 8, 2, 7, 3, 6, 4, 5]
    normals = []
    ups = []
    for f in faces:
        p0, p1, p2 = verts[f[0]], verts[f[1]], verts[f[2]]
        c = vec3_scale(vec3_add(vec3_add(p0, p1), p2), 1.0 / 3.0)
        n = vec3_norm(c)
        normals.append(n)
        ups.append(vec3_norm(vec3_sub(p0, c)))
    return PolyhedronModel("d8", verts, faces, nums, normals, ups, "#065F46", "#10B981", "#FDE047")


def _build_d10(is_d100: bool = False) -> PolyhedronModel:
    # Pentagonal Trapezohedron: 12 vertices, 10 planar kite faces
    h = 0.15
    k = (2.0 * math.sin(math.pi / 5.0) + math.sin(2.0 * math.pi / 5.0)) / (2.0 * math.sin(math.pi / 5.0) - math.sin(2.0 * math.pi / 5.0))
    H = h * k
    r = 1.0
    verts = [(0.0, H, 0.0), (0.0, -H, 0.0)]
    for i in range(5):
        ang = 2.0 * math.pi * i / 5.0
        verts.append((r * math.cos(ang), h, r * math.sin(ang)))
    for i in range(5):
        ang = 2.0 * math.pi * (i + 0.5) / 5.0
        verts.append((r * math.cos(ang), -h, r * math.sin(ang)))
    
    faces = []
    for i in range(5):
        u1, u2 = 2 + i, 2 + ((i + 1) % 5)
        l1 = 7 + i
        faces.append([0, u1, l1, u2])
    for i in range(5):
        l1, l2 = 7 + i, 7 + ((i + 1) % 5)
        u2 = 2 + ((i + 1) % 5)
        faces.append([1, l2, u2, l1])
        
    normals = []
    ups = []
    for f in faces:
        p0, p1, p2, p3 = [verts[idx] for idx in f]
        d1 = vec3_sub(p2, p0)
        d2 = vec3_sub(p3, p1)
        n = vec3_norm(vec3_cross(d1, d2))
        c = vec3_scale(vec3_add(vec3_add(p0, p1), vec3_add(p2, p3)), 0.25)
        if vec3_dot(n, c) < 0:
            n = vec3_scale(n, -1.0)
        normals.append(n)
        ups.append(vec3_norm(vec3_sub(p0, c)))
        
    if is_d100:
        nums = ["00", "50", "10", "60", "20", "70", "30", "80", "40", "90"]
        return PolyhedronModel("d100", verts, faces, nums, normals, ups, "#78350F", "#D97706", "#FFFFFF")
    else:
        nums = [1, 6, 2, 7, 3, 8, 4, 9, 5, 10]
        return PolyhedronModel("d10", verts, faces, nums, normals, ups, "#9A3412", "#F97316", "#FEF08A")


def _build_d20() -> PolyhedronModel:
    # Icosahedron: 12 vertices, 20 faces
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    raw_verts = [
        (-1.0,  phi, 0.0), ( 1.0,  phi, 0.0), (-1.0, -phi, 0.0), ( 1.0, -phi, 0.0),
        (0.0, -1.0,  phi), (0.0,  1.0,  phi), (0.0, -1.0, -phi), (0.0,  1.0, -phi),
        ( phi, 0.0, -1.0), ( phi, 0.0,  1.0), (-phi, 0.0, -1.0), (-phi, 0.0,  1.0)
    ]
    verts = [vec3_norm(v) for v in raw_verts]
    faces = [
        [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
        [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
        [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
        [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]
    ]
    normals = []
    ups = []
    for f in faces:
        p0, p1, p2 = verts[f[0]], verts[f[1]], verts[f[2]]
        c = vec3_scale(vec3_add(vec3_add(p0, p1), p2), 1.0 / 3.0)
        n = vec3_norm(c)
        normals.append(n)
        ups.append(vec3_norm(vec3_sub(p0, c)))
        
    # Pair opposites (sum to 21)
    paired = set()
    pairs = []
    for i in range(len(normals)):
        if i in paired: continue
        for j in range(i + 1, len(normals)):
            if j in paired: continue
            if vec3_dot(normals[i], normals[j]) < -0.98:
                paired.add(i)
                paired.add(j)
                pairs.append((i, j))
                break
    nums = [0] * 20
    for idx, (i, j) in enumerate(pairs):
        v = idx + 1
        nums[i] = v
        nums[j] = 21 - v
    return PolyhedronModel("d20", verts, faces, nums, normals, ups, "#991B1B", "#DC2626", "#FDE047")


def _build_d12() -> PolyhedronModel:
    # Dodecahedron: Dual of D20 (20 vertices, 12 pentagonal faces)
    d20 = _build_d20()
    verts = []
    for f in d20.faces:
        p0, p1, p2 = d20.vertices[f[0]], d20.vertices[f[1]], d20.vertices[f[2]]
        c = vec3_norm(vec3_scale(vec3_add(vec3_add(p0, p1), p2), 1.0 / 3.0))
        verts.append(c)
        
    faces = []
    normals = []
    ups = []
    for v_idx in range(12):
        center = d20.vertices[v_idx] # normal
        face_verts = [fi for fi, f in enumerate(d20.faces) if v_idx in f]
        ref = (1.0, 0.0, 0.0) if abs(center[0]) < 0.8 else (0.0, 1.0, 0.0)
        tangent = vec3_norm(vec3_cross(center, ref))
        bitangent = vec3_norm(vec3_cross(center, tangent))
        
        sorted_v = sorted(face_verts, key=lambda vi: math.atan2(
            vec3_dot(verts[vi], bitangent),
            vec3_dot(verts[vi], tangent)
        ))
        faces.append(sorted_v)
        normals.append(center)
        ups.append(vec3_norm(vec3_sub(verts[sorted_v[0]], center)))
        
    paired = set()
    pairs = []
    for i in range(len(normals)):
        if i in paired: continue
        for j in range(i + 1, len(normals)):
            if j in paired: continue
            if vec3_dot(normals[i], normals[j]) < -0.98:
                paired.add(i)
                paired.add(j)
                pairs.append((i, j))
                break
    nums = [0] * 12
    for idx, (i, j) in enumerate(pairs):
        v = idx + 1
        nums[i] = v
        nums[j] = 13 - v
    return PolyhedronModel("d12", verts, faces, nums, normals, ups, "#6B21A8", "#A855F7", "#FDE047")


_POLY_REGISTRY: Dict[str, PolyhedronModel] = {}

def get_polyhedron(die_type: str) -> PolyhedronModel:
    dt = str(die_type).lower().strip()
    if dt not in _POLY_REGISTRY:
        if dt == "d4":
            _POLY_REGISTRY[dt] = _build_d4()
        elif dt == "d6":
            _POLY_REGISTRY[dt] = _build_d6()
        elif dt == "d8":
            _POLY_REGISTRY[dt] = _build_d8()
        elif dt in ("d10", "1d10"):
            _POLY_REGISTRY[dt] = _build_d10(is_d100=False)
        elif dt in ("d100", "1d100", "d%"):
            _POLY_REGISTRY[dt] = _build_d10(is_d100=True)
        elif dt == "d12":
            _POLY_REGISTRY[dt] = _build_d12()
        else:
            _POLY_REGISTRY[dt] = _build_d20()
    return _POLY_REGISTRY[dt]


# ==============================================================================
# 3. GENERAZIONE ED ESECUZIONE AUDIO DI RIMBALZO (SFX WAV)
# ==============================================================================

_SOUND_LOCK = threading.Lock()
_SOUND_FILE_PATH: Optional[str] = None

def ensure_dice_sound_file() -> str:
    """Genera e salva un file WAV di impatto dadi se non esiste già nella cache."""
    global _SOUND_FILE_PATH
    if _SOUND_FILE_PATH and os.path.exists(_SOUND_FILE_PATH):
        return _SOUND_FILE_PATH
    
    try:
        from common.utils import get_writable_dir
        base_dir = get_writable_dir()
    except Exception:
        base_dir = "."
        
    cache_dir = os.path.join(base_dir, "client_data", "audio_cache")
    os.makedirs(cache_dir, exist_ok=True)
    wav_path = os.path.join(cache_dir, "dice_roll_clack.wav")
    
    if not os.path.exists(wav_path):
        sample_rate = 44100
        duration = 0.22
        n_samples = int(sample_rate * duration)
        impacts = [(0.0, 1.0, 1200), (0.045, 0.65, 980), (0.095, 0.40, 1450)]
        samples = [0.0] * n_samples
        for start_t, amp, freq in impacts:
            start_idx = int(start_t * sample_rate)
            for i in range(start_idx, n_samples):
                t = (i - start_idx) / sample_rate
                decay = math.exp(-t * 48.0)
                noise = (random.random() * 2.0 - 1.0) * 0.45
                wave_val = math.sin(2.0 * math.pi * freq * t) * 0.55
                samples[i] += (wave_val + noise) * decay * amp
        max_val = max(abs(s) for s in samples) or 1.0
        int_samples = [int((s / max_val) * 32767 * 0.85) for s in samples]
        with wave.open(wav_path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(struct.pack("<" + "h" * len(int_samples), *int_samples))
            
    _SOUND_FILE_PATH = wav_path
    return wav_path


def play_dice_bounce_sound():
    """Riproduce il suono di rimbalzo del dado in modo asincrono."""
    def _play():
        try:
            path = ensure_dice_sound_file()
            import winsound
            winsound.PlaySound(path, winsound.SND_ASYNC | winsound.SND_FILENAME)
        except Exception:
            pass
    threading.Thread(target=_play, daemon=True).start()


# ==============================================================================
# 4. CLASSE ISTANZA DI DADO 3D (Fisica, Rotazione, Shading)
# ==============================================================================

class Die3DInstance:
    """Rappresenta un singolo dado poliedrico simulato in 3D nello spazio del Canvas."""

    def __init__(
        self,
        die_type: str,
        target_value: Any,
        start_x: float,
        start_y: float,
        dest_x: float,
        dest_y: float,
        radius: float = 52.0,
        is_crit: bool = False,
        is_fumble: bool = False,
        is_discarded: bool = False,
        sound_enabled: bool = True
    ):
        self.model = get_polyhedron(die_type)
        self.target_value = target_value
        self.radius = radius
        self.is_crit = is_crit
        self.is_fumble = is_fumble
        self.is_discarded = is_discarded
        self.sound_enabled = sound_enabled
        
        # Posizione 3D (X, Y su canvas, Z è altezza sopra il tavolo)
        self.x = start_x
        self.y = start_y
        self.z = random.uniform(80.0, 140.0)
        
        self.dest_x = dest_x
        self.dest_y = dest_y
        
        # Velocità lineare
        self.vx = (dest_x - start_x) * 1.5 + random.uniform(-40.0, 40.0)
        self.vy = (dest_y - start_y) * 1.5 + random.uniform(-40.0, 40.0)
        self.vz = random.uniform(-100.0, -250.0)
        
        # Rotazione corrente (quaternione)
        axis = (random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0), random.uniform(-1.0, 1.0))
        self.quat = quat_from_axis_angle(axis, random.uniform(0.0, 2.0 * math.pi))
        
        # Velocità angolare
        self.ang_vel = [
            random.uniform(10.0, 18.0) * random.choice((-1, 1)),
            random.uniform(10.0, 18.0) * random.choice((-1, 1)),
            random.uniform(10.0, 18.0) * random.choice((-1, 1))
        ]
        
        # Calcolo orientamento target per mostrare la faccia corretta verso la telecamera (+Z)
        target_idx = 0
        t_str = str(target_value).strip().lower()
        found = False
        for idx, val in enumerate(self.model.face_numbers):
            if str(val).strip().lower() == t_str:
                target_idx = idx
                found = True
                break
        if not found:
            if self.model.name == "d10" and t_str in ("10", "0"):
                for idx, val in enumerate(self.model.face_numbers):
                    if str(val) in ("10", "0"):
                        target_idx = idx
                        found = True
                        break
            elif self.model.name == "d100":
                try:
                    num_int = int(target_value)
                    tens = f"{((num_int % 100) // 10) * 10:02d}"
                    for idx, val in enumerate(self.model.face_numbers):
                        if str(val) == tens:
                            target_idx = idx
                            found = True
                            break
                except Exception:
                    pass
        self.target_idx = target_idx
        self.target_value = self.model.face_numbers[target_idx]
        
        # Matrice di orientamento target
        target_mat = get_face_target_matrix(
            self.model.face_normals[target_idx],
            self.model.face_ups[target_idx]
        )
        self.target_quat = matrix_to_quat(target_mat)
        
        # Stato
        self.settle_progress = 0.0
        self.is_settled = False
        self.bounce_count = 0
        self.aura_pulse = 0.0

    def update(self, dt: float, progress: float, bounds: Tuple[float, float, float, float]):
        """Aggiorna fisica, rotazione e convergenza verso la faccia finale."""
        min_x, min_y, max_x, max_y = bounds
        
        if progress < 0.65 and not self.is_settled:
            # Fase di rotolamento balistico e rimbalzi
            self.vz += 980.0 * dt # Gravità
            self.z -= self.vz * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            
            # Rimbalzo sul tavolo (Z <= 0)
            if self.z <= 0.0:
                self.z = 0.0
                if abs(self.vz) > 40.0:
                    self.vz = -self.vz * 0.55
                    self.vx *= 0.78
                    self.vy *= 0.78
                    self.ang_vel[0] *= 0.80
                    self.ang_vel[1] *= 0.80
                    self.ang_vel[2] *= 0.80
                    self.bounce_count += 1
                    if self.sound_enabled and self.bounce_count <= 4:
                        play_dice_bounce_sound()
                else:
                    self.vz = 0.0
                    
            # Rimbalzo sui bordi visivi
            pad = self.radius + 10
            if self.x < min_x + pad:
                self.x = min_x + pad
                self.vx = -self.vx * 0.7
            elif self.x > max_x - pad:
                self.x = max_x - pad
                self.vx = -self.vx * 0.7
                
            if self.y < min_y + pad:
                self.y = min_y + pad
                self.vy = -self.vy * 0.7
            elif self.y > max_y - pad:
                self.y = max_y - pad
                self.vy = -self.vy * 0.7
                
            # Integrazione rotazione
            w_len = math.sqrt(sum(w * w for w in self.ang_vel))
            if w_len > 0.01:
                dq = quat_from_axis_angle(self.ang_vel, w_len * dt)
                self.quat = quat_multiply(dq, self.quat)
                
        else:
            # Fase di assestamento elegante sulla faccia target (Slerp)
            self.z = max(0.0, self.z * 0.85)
            self.vx = 0.0
            self.vy = 0.0
            self.vz = 0.0
            
            # Interpolazione fluida della posizione verso dest_x, dest_y
            settle_t = min(1.0, (progress - 0.65) / 0.35)
            smooth_t = settle_t * settle_t * (3.0 - 2.0 * settle_t)
            
            self.x = self.x + (self.dest_x - self.x) * (dt * 8.0)
            self.y = self.y + (self.dest_y - self.y) * (dt * 8.0)
            
            self.quat = quat_slerp(self.quat, self.target_quat, min(1.0, dt * 10.0))
            if settle_t >= 0.95 or progress >= 0.98:
                self.quat = self.target_quat
                self.x = self.dest_x
                self.y = self.dest_y
                self.is_settled = True
                self.aura_pulse += dt * 4.0

    def render(self, canvas: tk.Canvas):
        """Proietta e disegna il dado 3D con ombre, facce sfaccettate e numeri in stile Dark Fantasy."""
        M = quat_to_matrix(self.quat)
        
        # 1. Ombra sotto il dado sul tavolo
        shadow_rx = self.radius * (0.85 + self.z * 0.002)
        shadow_ry = shadow_rx * 0.45
        shadow_alpha_tint = max(0.2, 1.0 - (self.z / 180.0))
        if shadow_alpha_tint > 0.1:
            sh_x = self.x
            sh_y = self.y + self.radius * 0.65
            canvas.create_oval(
                sh_x - shadow_rx, sh_y - shadow_ry,
                sh_x + shadow_rx, sh_y + shadow_ry,
                fill="#0A0B0E", outline="", tags="dice_shadow"
            )
            
        # 2. Alone / Glow se il dado è fermo ed è Critico
        if self.is_settled and self.is_crit:
            pulse = math.sin(self.aura_pulse) * 6.0
            glow_r = self.radius + 14.0 + pulse
            canvas.create_oval(
                self.x - glow_r, self.y - glow_r,
                self.x + glow_r, self.y + glow_r,
                outline="#FDE047", width=3, tags="dice_glow"
            )
        elif self.is_settled and self.is_fumble:
            glow_r = self.radius + 10.0
            canvas.create_oval(
                self.x - glow_r, self.y - glow_r,
                self.x + glow_r, self.y + glow_r,
                outline="#EF4444", width=3, tags="dice_glow"
            )
            
        # 3. Trasformazione dei vertici e facce
        scale = self.radius * (1.0 + self.z * 0.0015)
        trans_verts = []
        for v in self.model.vertices:
            rv = mat_vec_mul(M, v)
            # Proiezione 2D ortogonale/prospettica dolce
            px = self.x + rv[0] * scale
            py = self.y - rv[1] * scale # Y invertita su schermo
            trans_verts.append((px, py, rv[2]))
            
        # Vettore luce direzionale da alto-sinistra
        light_vec = vec3_norm((-0.45, 0.65, 0.60))
        
        # Calcolo facce per Painter's Algorithm (Z-sorting)
        face_render_data = []
        for f_idx, face in enumerate(self.model.faces):
            # Normale trasformata
            orig_n = self.model.face_normals[f_idx]
            rn = mat_vec_mul(M, orig_n)
            
            # Backface check dolce
            if rn[2] <= -0.15:
                continue
                
            # Calcolo Z medio
            avg_z = sum(trans_verts[vi][2] for vi in face) / len(face)
            face_render_data.append((avg_z, f_idx, rn))
            
        # Ordina facce dalla più lontana (Z minore) alla più vicina (Z maggiore)
        face_render_data.sort(key=lambda item: item[0])
        
        # Palette colori
        if self.is_discarded:
            base_rgb = (55, 65, 81) # Grigio scuro opaco
            edge_color = "#4B5563"
            txt_color = "#9CA3AF"
        elif self.is_crit and self.is_settled:
            base_rgb = (217, 119, 6) # Oro brillante trionfale
            edge_color = "#FDE047"
            txt_color = "#78350F"
        elif self.is_fumble and self.is_settled:
            base_rgb = (127, 29, 29) # Sangue cupo
            edge_color = "#EF4444"
            txt_color = "#FCA5A5"
        else:
            # Base dal modello
            hex_c = self.model.base_color.lstrip("#")
            base_rgb = tuple(int(hex_c[i:i+2], 16) for i in (0, 2, 4))
            edge_color = "#D4AF37" if self.model.name in ("d20", "d12") else "#94A3B8"
            txt_color = self.model.text_color
            
        # Disegno facce
        for avg_z, f_idx, rn in face_render_data:
            face = self.model.faces[f_idx]
            pts = []
            for vi in face:
                pts.extend([trans_verts[vi][0], trans_verts[vi][1]])
                
            # Shading Lambertiano
            diffuse = max(0.0, vec3_dot(rn, light_vec))
            # Speculare
            half = vec3_norm(vec3_add(light_vec, (0.0, 0.0, 1.0)))
            spec = max(0.0, vec3_dot(rn, half)) ** 12
            
            brightness = 0.38 + 0.52 * diffuse + 0.28 * spec
            r_c = min(255, max(0, int(base_rgb[0] * brightness)))
            g_c = min(255, max(0, int(base_rgb[1] * brightness)))
            b_c = min(255, max(0, int(base_rgb[2] * brightness)))
            fill_hex = f"#{r_c:02x}{g_c:02x}{b_c:02x}"
            
            # Se il dado è fermo ed è la faccia target vincente, evidenziamo il bordo
            is_target_face = (f_idx == self.target_idx)
            is_facing_front = (rn[2] >= 0.88)
            is_winning_face = self.is_settled and (is_target_face or is_facing_front)
            
            f_outline = "#FDE047" if is_winning_face else edge_color
            f_width = 3 if is_winning_face else 2
            
            canvas.create_polygon(pts, fill=fill_hex, outline=f_outline, width=f_width, tags="dice_face")
            
            # Disegno del numero della faccia se rivolta verso la camera
            if rn[2] > 0.40:
                cx = sum(trans_verts[vi][0] for vi in face) / len(face)
                cy = sum(trans_verts[vi][1] for vi in face) / len(face)
                
                num_val = self.model.face_numbers[f_idx]
                num_str = str(num_val)
                if num_str in ("6", "9"):
                    num_str += "." # Distinzione 6 e 9
                    
                if self.is_settled:
                    if is_winning_face:
                        font_sz = max(13, int(20 * (self.radius / 52.0)))
                        canvas.create_text(
                            cx + 1, cy + 1,
                            text=num_str, font=("Georgia", font_sz, "bold"),
                            fill="#000000", tags="dice_num"
                        )
                        canvas.create_text(
                            cx, cy,
                            text=num_str, font=("Georgia", font_sz, "bold"),
                            fill=txt_color, tags="dice_num"
                        )
                    else:
                        font_sz = max(8, int(11 * (self.radius / 52.0)))
                        canvas.create_text(
                            cx, cy,
                            text=num_str, font=("Georgia", font_sz, "bold"),
                            fill="#64748B", tags="dice_num"
                        )
                else:
                    font_sz = max(9, int(15 * (self.radius / 52.0) * rn[2]))
                    canvas.create_text(
                        cx + 1, cy + 1,
                        text=num_str, font=("Georgia", font_sz, "bold"),
                        fill="#000000", tags="dice_num"
                    )
                    canvas.create_text(
                        cx, cy,
                        text=num_str, font=("Georgia", font_sz, "bold"),
                        fill=txt_color, tags="dice_num"
                    )


# ==============================================================================
# 5. OVERLAY WIDGET SU CANVAS (Dice3DOverlay)
# ==============================================================================

class Dice3DOverlay:
    """
    Overlay animato per il lancio dei dadi 3D poliedrici.
    Si posiziona sopra il widget genitore (es. map_outer_frame o master)
    e mostra dadi che rotolano, si assestano e presentano il banner dei risultati.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_complete: Optional[Callable[[], None]] = None,
        sound_enabled: bool = True,
        speed: str = "normal"
    ):
        self.parent = parent
        self.on_complete = on_complete
        self.sound_enabled = sound_enabled
        self.speed = speed
        
        # Durata totale in base alla velocità
        speed_map = {"fast": 0.9, "normal": 1.5, "dramatic": 2.4}
        self.total_duration = speed_map.get(speed, 1.5)
        self.auto_close_delay = 1.6 # secondi dopo l'arresto
        
        self.canvas = tk.Canvas(
            parent,
            bg="#0E1015",
            highlightthickness=0,
            borderwidth=0
        )
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        
        self.dice: List[Die3DInstance] = []
        self.elapsed = 0.0
        self.is_running = False
        self.is_finished = False
        self.timer_id: Optional[str] = None
        
        self.banner_info: Dict[str, Any] = {}

    def roll(
        self,
        formula: str,
        roll_result: Dict[str, Any],
        player_name: str = "Giocatore",
        reason: str = "",
        on_complete: Optional[Callable[[], None]] = None
    ):
        """Avvia l'animazione del lancio con i dati del risultato del motore roll_dice."""
        if on_complete:
            self.on_complete = on_complete
            
        self.parent.update_idletasks()
        pw = max(400, self.parent.winfo_width())
        ph = max(300, self.parent.winfo_height())
        
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Misc.tkraise(self.canvas)
        
        # Estrai dadi da animare
        dice_to_roll = self._extract_dice_list(formula, roll_result)
        
        # Distribuisci posizioni finali dei dadi
        n = len(dice_to_roll)
        spacing = min(130.0, (pw * 0.8) / max(1, n))
        start_center_x = pw / 2.0 - ((n - 1) * spacing) / 2.0
        center_y = ph * 0.42
        
        self.dice.clear()
        for i, d_info in enumerate(dice_to_roll):
            target_x = start_center_x + i * spacing
            target_y = center_y
            
            # Posizione di lancio casuale da un bordo
            launch_x = random.choice([target_x - 180.0, target_x + 180.0])
            launch_y = target_y - random.uniform(100.0, 180.0)
            
            die_inst = Die3DInstance(
                die_type=d_info.get("die", "d20"),
                target_value=d_info.get("val", 20),
                start_x=launch_x,
                start_y=launch_y,
                dest_x=target_x,
                dest_y=target_y,
                radius=min(56.0, spacing * 0.44),
                is_crit=d_info.get("is_crit", False),
                is_fumble=d_info.get("is_fumble", False),
                is_discarded=d_info.get("is_discarded", False),
                sound_enabled=self.sound_enabled
            )
            self.dice.append(die_inst)
            
        self.banner_info = {
            "player": player_name,
            "reason": reason,
            "formula": formula,
            "total": roll_result.get("total", 0),
            "modifier": roll_result.get("modifier", 0),
            "rolls": roll_result.get("rolls", []),
            "other_rolls": roll_result.get("other_rolls", []),
            "is_crit": roll_result.get("is_crit", False),
            "is_fumble": roll_result.get("is_fumble", False) or roll_result.get("is_crit_fail", False)
        }
        
        self.elapsed = 0.0
        self.is_running = True
        self.is_finished = False
        
        if self.sound_enabled:
            play_dice_bounce_sound()
            
        self._animate_step()

    def _extract_dice_list(self, formula: str, res: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Estrae la lista dei dadi individuali e dei valori per il rendering 3D."""
        dice_list = []
        is_crit = res.get("is_crit", False)
        is_fumble = res.get("is_fumble", False) or res.get("is_crit_fail", False)
        
        # Caso Vantaggio / Svantaggio con due d20
        other_rolls = res.get("other_rolls", [])
        rolls = res.get("rolls", [])
        
        if other_rolls and len(rolls) == 1 and len(other_rolls) == 1:
            kept_val = rolls[0]
            disc_val = other_rolls[0]
            dice_list.append({
                "die": "d20", "val": kept_val,
                "is_crit": is_crit, "is_fumble": is_fumble,
                "is_discarded": False
            })
            dice_list.append({
                "die": "d20", "val": disc_val,
                "is_crit": False, "is_fumble": False,
                "is_discarded": True
            })
            return dice_list
            
        # Parse formula base per determinare il tipo di dado (d4, d6, d8, d10, d12, d20, d100)
        import re
        tokens = re.findall(r'(\d*)d(\d+)', formula.lower())
        if tokens:
            t_idx = 0
            for cnt_s, sides_s in tokens:
                cnt = int(cnt_s) if cnt_s else 1
                sides = int(sides_s)
                die_name = f"d{sides}"
                for _ in range(cnt):
                    val = rolls[t_idx] if t_idx < len(rolls) else (random.randint(1, sides))
                    t_idx += 1
                    dice_list.append({
                        "die": die_name,
                        "val": val,
                        "is_crit": is_crit if die_name == "d20" and val == 20 else False,
                        "is_fumble": is_fumble if die_name == "d20" and val == 1 else False,
                        "is_discarded": False
                    })
                    if len(dice_list) >= 8: # Limite a 8 dadi visivi per pulizia a schermo
                        break
                if len(dice_list) >= 8:
                    break
        else:
            # Fallback generico
            for i, val in enumerate(rolls[:6]):
                dice_list.append({
                    "die": "d20",
                    "val": val,
                    "is_crit": is_crit if val == 20 else False,
                    "is_fumble": is_fumble if val == 1 else False,
                    "is_discarded": False
                })
                
        if not dice_list:
            dice_list.append({
                "die": "d20",
                "val": res.get("total", 20),
                "is_crit": is_crit,
                "is_fumble": is_fumble,
                "is_discarded": False
            })
            
        return dice_list

    def _animate_step(self):
        if not self.is_running:
            return
            
        dt = 0.020 # 50 FPS
        self.elapsed += dt
        progress = min(1.0, self.elapsed / self.total_duration)
        
        pw = max(400, self.canvas.winfo_width())
        ph = max(300, self.canvas.winfo_height())
        bounds = (20.0, 20.0, pw - 20.0, ph - 20.0)
        
        # Aggiorna fisica
        for d in self.dice:
            d.update(dt, progress, bounds)
            
        # Pulisci canvas e ridisegna
        self.canvas.delete("all")
        
        # Sfondo semitrasparente scuro con texture a griglia discreta
        self.canvas.create_rectangle(0, 0, pw, ph, fill="#0B0C0E", outline="", tags="bg")
        
        # Ridisegna tutti i dadi
        for d in self.dice:
            d.render(self.canvas)
            
        # Quando i dadi si sono assestati, mostra il banner dei risultati
        if progress >= 0.90:
            self._render_result_banner(pw, ph)
            
        if progress >= 1.0 and not self.is_finished:
            self.is_finished = True
            # Pianifica chiusura automatica dopo breve attesa
            self.timer_id = self.canvas.after(int(self.auto_close_delay * 1000), self.dismiss)
        else:
            self.timer_id = self.canvas.after(20, self._animate_step)

    def _render_result_banner(self, pw: float, ph: float):
        """Disegna la card scura con cornice dorata e dettagli del tiro."""
        bw = min(480.0, pw * 0.9)
        bh = 110.0
        bx = (pw - bw) / 2.0
        by = ph * 0.68
        
        # Card Background
        self.canvas.create_rectangle(
            bx, by, bx + bw, by + bh,
            fill="#181A20", outline="#D4AF37", width=2, tags="banner"
        )
        
        p_name = self.banner_info.get("player", "Giocatore")
        reason = self.banner_info.get("reason", "")
        form = self.banner_info.get("formula", "")
        tot = self.banner_info.get("total", 0)
        rolls = self.banner_info.get("rolls", [])
        other_rolls = self.banner_info.get("other_rolls", [])
        mod = self.banner_info.get("modifier", 0)
        is_crit = self.banner_info.get("is_crit", False)
        is_fumble = self.banner_info.get("is_fumble", False)
        
        header_text = f"{p_name} • {reason or form}"
        self.canvas.create_text(
            pw / 2.0, by + 18,
            text=header_text, font=("Georgia", 11, "bold"),
            fill="#CBD5E1", tags="banner"
        )
        
        # Stringa formula dettagliata
        rolls_str = "+".join(map(str, rolls))
        if other_rolls:
            rolls_str = f"[{rolls_str}] (scartato: {other_rolls})"
        else:
            rolls_str = f"[{rolls_str}]"
            
        mod_str = f" + {mod}" if mod > 0 else (f" - {abs(mod)}" if mod < 0 else "")
        res_text = f"🎲 {rolls_str}{mod_str} = {tot}"
        
        num_color = "#2ECC71" if is_crit else ("#ED4245" if is_fumble else "#FDE047")
        self.canvas.create_text(
            pw / 2.0, by + 48,
            text=res_text, font=("Georgia", 16, "bold"),
            fill=num_color, tags="banner"
        )
        
        # Badge di stato
        if is_crit:
            badge = "🌟 20 NATURALE - SUCCESSO CRITICO!"
            b_color = "#2ECC71"
        elif is_fumble:
            badge = "💀 1 NATURALE - FALLIMENTO CRITICO!"
            b_color = "#ED4245"
        else:
            badge = "Clicca per chiudere subito"
            b_color = "#94A3B8"
            
        self.canvas.create_text(
            pw / 2.0, by + 82,
            text=badge, font=("Segoe UI", 10, "bold" if (is_crit or is_fumble) else "italic"),
            fill=b_color, tags="banner"
        )

    def _on_canvas_click(self, event):
        """Un click durante il roll salta subito al termine; un click al termine chiude immediatamente."""
        if not self.is_finished:
            # Salta subito all'arresto
            self.elapsed = self.total_duration
            for d in self.dice:
                d.is_settled = True
                d.quat = d.target_quat
                d.x = d.dest_x
                d.y = d.dest_y
                d.z = 0.0
            self._animate_step()
        else:
            self.dismiss()

    def dismiss(self):
        """Nasconde e chiude l'overlay liberando le risorse."""
        if self.timer_id:
            try:
                self.canvas.after_cancel(self.timer_id)
            except Exception:
                pass
            self.timer_id = None
            
        self.is_running = False
        self.canvas.place_forget()
        self.canvas.delete("all")
        
        if self.on_complete:
            cb = self.on_complete
            self.on_complete = None
            try:
                cb()
            except Exception:
                pass
