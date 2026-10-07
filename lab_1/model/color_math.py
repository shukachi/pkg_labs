
from __future__ import annotations
from typing import Dict, List, Tuple

Vec3 = List[float]
Mat3 = List[List[float]]


ILLUMINANTS: Dict[str, Tuple[float, float]] = {
    "D65": (0.31270, 0.32900),
    "D50": (0.34570, 0.35850),
    "E":   (1.0 / 3.0, 1.0 / 3.0),
}

PRIMARIES_SRGB: List[Tuple[float, float]] = [
    (0.6400, 0.3300),   # R
    (0.3000, 0.6000),   # G
    (0.1500, 0.0600),   # B
]


def mat_vec(m: Mat3, v: Vec3) -> Vec3:
    return [m[i][0] * v[0] + m[i][1] * v[1] + m[i][2] * v[2] for i in range(3)]


def mat_inv(m: Mat3) -> Mat3:
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if abs(det) < 1e-12:
        raise ValueError("Вырожденная матрица")
    return [
        [(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det],
        [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
        [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det],
    ]


def build_rgb_to_xyz(white_xy: Tuple[float, float],
                     primaries: List[Tuple[float, float]] = PRIMARIES_SRGB):
    """Выводит матрицу RGB->XYZ из цветностей первичных и белой точки."""
    xw, yw = white_xy
    W = [xw / yw, 1.0, (1.0 - xw - yw) / yw]     

    xs = [p[0] for p in primaries]
    ys = [p[1] for p in primaries]
    zs = [1.0 - p[0] - p[1] for p in primaries]

    M0 = [
        [xs[j] / ys[j] for j in range(3)],
        [1.0, 1.0, 1.0],
        [zs[j] / ys[j] for j in range(3)],
    ]
    S = mat_vec(mat_inv(M0), W)
    M = [[M0[i][j] * S[j] for j in range(3)] for i in range(3)]
    return M, W


class ColorEngine:

    def __init__(self, illuminant: str = "D65"):
        self.illuminant = illuminant
        self._rebuild()

    def _rebuild(self):
        self.white_xy = ILLUMINANTS[self.illuminant]
        self.M_rgb2xyz, self.white_xyz = build_rgb_to_xyz(self.white_xy)
        self.M_xyz2rgb = mat_inv(self.M_rgb2xyz)

    def set_illuminant(self, name: str):
        if name not in ILLUMINANTS:
            raise KeyError(f"Неизвестный осветитель: {name}")
        self.illuminant = name
        self._rebuild()          

    @staticmethod
    def srgb_expand(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    @staticmethod
    def srgb_compress(c: float) -> float:
        c = min(1.0, max(0.0, c))
        return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055

    def rgb_to_xyz(self, rgb255: Vec3) -> Vec3:
        lin = [self.srgb_expand(c / 255.0) for c in rgb255]
        return mat_vec(self.M_rgb2xyz, lin)

    def xyz_to_rgb(self, xyz: Vec3, strategy: str = "clip"):
        lin = mat_vec(self.M_xyz2rgb, xyz)
        out_of_gamut = any(c < -1e-9 or c > 1.0 + 1e-9 for c in lin)

        if strategy == "clip":
            lin2 = [min(1.0, max(0.0, c)) for c in lin]
        else:                                    # scaling
            lin2 = self.scale_to_gamut(lin)

        srgb = [self.srgb_compress(c) for c in lin2]
        return [int(round(c * 255)) for c in srgb], out_of_gamut

    @staticmethod
    def scale_to_gamut(v: Vec3) -> Vec3:
        lo, hi = min(v), max(v)
        if lo >= 0.0 and hi <= 1.0:
            return list(v)
        d = hi - lo
        if d > 1.0:
            return [(c - lo) / d for c in v]
        if lo < 0.0:
            return [c - lo for c in v]
        return [c - (hi - 1.0) for c in v]

def rgb_to_hsv(rgb255: Vec3) -> Vec3:
    r, g, b = [c / 255.0 for c in rgb255]
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d == 0.0:
        h = 0.0
    elif mx == r:
        h = (60.0 * ((g - b) / d)) % 360.0
    elif mx == g:
        h = 60.0 * ((b - r) / d) + 120.0
    else:
        h = 60.0 * ((r - g) / d) + 240.0
    s = 0.0 if mx == 0.0 else d / mx
    return [h, s, mx]


def hsv_to_rgb(h: float, s: float, v: float) -> Vec3:
    h = h % 360.0
    c = v * s
    x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
    m = v - c
    if   h < 60.0:  r, g, b = c, x, 0.0
    elif h < 120.0: r, g, b = x, c, 0.0
    elif h < 180.0: r, g, b = 0.0, c, x
    elif h < 240.0: r, g, b = 0.0, x, c
    elif h < 300.0: r, g, b = x, 0.0, c
    else:           r, g, b = c, 0.0, x
    return [int(round((r + m) * 255)), int(round((g + m) * 255)), int(round((b + m) * 255))]