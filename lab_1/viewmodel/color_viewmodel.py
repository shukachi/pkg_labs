from __future__ import annotations
from model.color_math import ColorEngine, rgb_to_hsv, hsv_to_rgb


class ColorViewModel:
    def __init__(self, illuminant: str = "D65"):
        self.engine = ColorEngine(illuminant)
        self.gamut_strategy = "clip"

        self.rgb = [255, 0, 0]
        self.xyz = [0.0, 0.0, 0.0]
        self.hsv = [0.0, 1.0, 1.0]
        self.warning = ""

        self._listeners = []
        self.recompute()

    # ---------- инфраструктура ----------
    def subscribe(self, fn):
        self._listeners.append(fn)

    def notify(self):
        for fn in self._listeners:
            fn(self)

    def _refresh_hsv(self):
        """Обновляет S и V из RGB, но НЕ затирает пользовательский H
        в двух случаях:
          1) цвет ахроматический (S ≈ 0) — у серого оттенок не определён;
          2) на границе заворота H=360 ≡ 0 — оставляем то, что стоит
             под ползунком, чтобы он не «прыгал» с правого края в левый.
        """
        h_new, s, v = rgb_to_hsv(self.rgb)
        old_h = self.hsv[0]

        if s > 1e-9:
            if old_h >= 359.99 and h_new <= 0.01:
                pass                       # заворот 360→0 — не сбрасываем
            elif old_h <= 0.01 and h_new >= 359.99:
                pass                       # заворот 0→360
            else:
                old_h = h_new

        self.hsv = [old_h, s, v]

    # ---------- пересчёт ----------
    def recompute(self):
        self.xyz = self.engine.rgb_to_xyz(self.rgb)
        self._refresh_hsv()
        self.notify()

    # ---------- сеттеры ----------
    def set_rgb(self, rgb):
        self.rgb = [int(round(min(255, max(0, c)))) for c in rgb]
        self.warning = ""
        self.recompute()

    def set_hsv(self, h, s, v):
        try:
            h = float(h); s = float(s); v = float(v)
        except (TypeError, ValueError):
            return
        # НЕ делаем h %= 360 — пользователь имеет право стоять на 360.
        h = max(0.0, min(360.0, h))
        s = max(0.0, min(1.0, s))
        v = max(0.0, min(1.0, v))

        # Сначала фиксируем намерение пользователя, потом считаем цвет.
        self.hsv = [h, s, v]
        self.rgb = hsv_to_rgb(h, s, v)     # hsv_to_rgb сам сделает % 360
        self.warning = ""
        self.recompute()

    def set_xyz(self, xyz):
        # XYZ сохраняем «как ввёл пользователь», чтобы ползунки XYZ
        # могли ходить до 1.2/1.1/1.3 и не откатывались назад.
        try:
            self.xyz = [float(c) for c in xyz]
        except (TypeError, ValueError):
            return
        rgb, clipped = self.engine.xyz_to_rgb(self.xyz, self.gamut_strategy)
        self.rgb = rgb
        self.warning = self._gamut_warning(clipped)
        self._refresh_hsv()
        self.notify()

    def set_illuminant(self, name):
        self.engine.set_illuminant(name)
        self.xyz = self.engine.rgb_to_xyz(self.rgb)
        self._refresh_hsv()
        self.notify()

    def set_gamut_strategy(self, s):
        self.gamut_strategy = s
        rgb, clipped = self.engine.xyz_to_rgb(self.xyz, s)
        self.rgb = rgb
        self.warning = self._gamut_warning(clipped)
        self._refresh_hsv()
        self.notify()

    def _gamut_warning(self, clipped: bool) -> str:
        if not clipped:
            return ""
        name = ("обрезание (Clipping)"
                if self.gamut_strategy == "clip"
                else "масштабирование (Scaling)")
        return f" Цвет вне охвата sRGB — выполнено {name}."