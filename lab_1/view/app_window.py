
import tkinter as tk
from tkinter import ttk
from view.gradient_slider import GradientSlider
from model.color_math import hsv_to_rgb


class AppWindow(tk.Tk):
    def __init__(self, vm):
        super().__init__()
        self.vm = vm
        self.title("ЛР №1 — Цветовые модели (RGB / XYZ / HSV)")
        self.geometry("1180x720")
        self.configure(bg="#f0f0f0")
        self._updating = False

        self._build_toolbar()
        self._build_panels()
        self._build_preview()

        self.vm.subscribe(self.on_model_changed)
        self.on_model_changed(self.vm)

    def _build_toolbar(self):
        bar = tk.Frame(self, bg="#e4e4e4", pady=6)
        bar.pack(fill="x")

        tk.Label(bar, text="Осветитель:", bg="#e4e4e4").pack(side="left", padx=(10, 4))
        self.var_illum = tk.StringVar(value=self.vm.engine.illuminant)
        for name in ("D65", "D50", "E"):
            tk.Radiobutton(bar, text=name, value=name, variable=self.var_illum,
                           bg="#e4e4e4", command=self._on_illum).pack(side="left")

        tk.Label(bar, text="   Приведение к охвату:", bg="#e4e4e4").pack(side="left")
        self.var_gamut = tk.StringVar(value="clip")
        for val, txt in (("clip", "Clipping"), ("scale", "Scaling")):
            tk.Radiobutton(bar, text=txt, value=val, variable=self.var_gamut,
                           bg="#e4e4e4",
                           command=lambda: self.vm.set_gamut_strategy(self.var_gamut.get())
                           ).pack(side="left")

    def _on_illum(self):
        self.vm.set_illuminant(self.var_illum.get())

    def _build_panels(self):
        wrap = tk.Frame(self, bg="#f0f0f0")
        wrap.pack(fill="both", expand=True, padx=8, pady=8)

        self.sliders = {}
        self.entries = {}

        self._panel_xyz(wrap, 0)
        self._panel_hsv(wrap, 1)
        self._panel_rgb(wrap, 2)

    def _make_slider(self, parent, key, label, gfn, lo, hi, cmd):
        s = GradientSlider(parent, gradient_fn=gfn, minval=lo, maxval=hi,
                           value=0, command=cmd, label=label)
        s.pack(fill="x", pady=(2, 6))
        self.sliders[key] = s
        return s

    def _panel_rgb(self, parent, col):
        f = tk.LabelFrame(parent, text=" RGB ", bg="#f0f0f0", padx=8, pady=6)
        f.grid(row=0, column=col, sticky="nsew", padx=4, pady=4)
        parent.columnconfigure(col, weight=1)
        for i, name in enumerate("RGB"):
            key = f"rgb_{name}"
            self._make_slider(f, key, name, self._gfn_rgb(i), 0, 255,
                              lambda v, k=key: self._on_slider(k, v))
            e = tk.Entry(f, width=6)
            e.pack(anchor="e")
            e.bind("<Return>", lambda _e, k=key: self._on_entry(k))
            self.entries[key] = e

    def _gfn_rgb(self, idx):
        def fn(t):
            rgb = list(self.vm.rgb)
            rgb[idx] = int(round(t * 255))
            return tuple(rgb)
        return fn

    def _panel_xyz(self, parent, col):
        f = tk.LabelFrame(parent, text=" XYZ ", bg="#f0f0f0", padx=8, pady=6)
        f.grid(row=0, column=col, sticky="nsew", padx=4, pady=4)
        lim = ((0.0, 1.2), (0.0, 1.1), (0.0, 1.3))
        for i, name in enumerate("XYZ"):
            key = f"xyz_{name}"
            self._make_slider(f, key, name, self._gfn_xyz(i), lim[i][0], lim[i][1],
                              lambda v, k=key: self._on_slider(k, v))
            e = tk.Entry(f, width=8)
            e.pack(anchor="e")
            e.bind("<Return>", lambda _e, k=key: self._on_entry(k))
            self.entries[key] = e

    def _gfn_xyz(self, idx):
        def fn(t):
            lim = (1.2, 1.1, 1.3)[idx]
            xyz = list(self.vm.xyz)
            xyz[idx] = t * lim
            rgb, _ = self.vm.engine.xyz_to_rgb(xyz, "clip")
            return tuple(rgb)
        return fn

    def _panel_hsv(self, parent, col):
        f = tk.LabelFrame(parent, text=" HSV ", bg="#f0f0f0", padx=8, pady=6)
        f.grid(row=0, column=col, sticky="nsew", padx=4, pady=4)
        for i, (name, hi) in enumerate((("H", 360.0), ("S", 100.0), ("V", 100.0))):
            key = f"hsv_{name}"
            self._make_slider(f, key, name, self._gfn_hsv(i), 0.0, hi,
                              lambda v, k=key: self._on_slider(k, v))
            e = tk.Entry(f, width=8)
            e.pack(anchor="e")
            e.bind("<Return>", lambda _e, k=key: self._on_entry(k))
            self.entries[key] = e

    def _gfn_hsv(self, idx):
        def fn(t):
            h, s, v = self.vm.hsv
            if idx == 0:                       # H: 0..360
                h = t * 360.0
                s = 1.0                        # радуга всегда насыщенная
                v = 1.0
            elif idx == 1:                     # S: 0..1
                s = t
            else:                              # V: 0..1
                v = t
            return tuple(hsv_to_rgb(h, s, v))
        return fn

    def _build_preview(self):
        bar = tk.Frame(self, bg="#f0f0f0")
        bar.pack(fill="x", padx=10, pady=(0, 8))
        self.swatch = tk.Canvas(bar, width=90, height=60, highlightthickness=1,
                                highlightbackground="#888")
        self.swatch.pack(side="left")
        self.info_lbl = tk.Label(bar, text="", bg="#f0f0f0",
                                 font=("Consolas", 11), justify="left")
        self.info_lbl.pack(side="left", padx=12)
        self.warn_lbl = tk.Label(bar, text="", fg="#b35c00", bg="#f0f0f0")
        self.warn_lbl.pack(side="left", padx=12)

    def _on_slider(self, key, value):
        if self._updating:
            return
        self._apply(key, value)

    def _on_entry(self, key):
        if self._updating:
            return
        text = self.entries[key].get().strip().replace(",", ".")
        try:
            value = float(text)
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError
        except ValueError:
            self._restore_entry(key)
            return
        self._apply(key, value)

    def _restore_entry(self, key):
        """Вернуть в поле актуальное значение из модели (после плохого ввода)."""
        fam, comp = key.split("_")
        if fam == "rgb":
            text = str(self.vm.rgb["RGB".index(comp)])
        elif fam == "xyz":
            text = f"{self.vm.xyz['XYZ'.index(comp)]:.4f}"
        else:                                     # hsv
            if comp == "H":
                text = f"{self.vm.hsv[0]:.1f}"
            elif comp == "S":
                text = f"{self.vm.hsv[1] * 100.0:.1f}"
            else:
                text = f"{self.vm.hsv[2] * 100.0:.1f}"
        self.entries[key].delete(0, "end")
        self.entries[key].insert(0, text)

    def _apply(self, key, value):
        fam, comp = key.split("_")

        if fam == "rgb":
            v = int(round(max(0.0, min(255.0, float(value)))))
            rgb = list(self.vm.rgb)
            rgb["RGB".index(comp)] = v
            self.vm.set_rgb(rgb)

        elif fam == "xyz":
            lims = {"X": 1.2, "Y": 1.1, "Z": 1.3}
            v = max(0.0, min(lims[comp], float(value)))
            xyz = list(self.vm.xyz)
            xyz["XYZ".index(comp)] = v
            self.vm.set_xyz(xyz)

        elif fam == "hsv":
            h, s, v = self.vm.hsv
            if comp == "H":
                h = max(0.0, min(360.0, float(value)))   # НЕ делаем %360
            elif comp == "S":
                s = max(0.0, min(1.0, float(value) / 100.0))
            else:
                v = max(0.0, min(1.0, float(value) / 100.0))
            self.vm.set_hsv(h, s, v)

    def on_model_changed(self, vm):
        self._updating = True
        try:
            for i, name in enumerate("RGB"):
                self.sliders[f"rgb_{name}"].set_gradient_fn(self._gfn_rgb(i))
                self.sliders[f"rgb_{name}"].set_value(vm.rgb[i])
                self.entries[f"rgb_{name}"].delete(0, "end")
                self.entries[f"rgb_{name}"].insert(0, str(vm.rgb[i]))

            for i, name in enumerate("XYZ"):
                self.sliders[f"xyz_{name}"].set_gradient_fn(self._gfn_xyz(i))
                self.sliders[f"xyz_{name}"].set_value(vm.xyz[i])
                self.entries[f"xyz_{name}"].delete(0, "end")
                self.entries[f"xyz_{name}"].insert(0, f"{vm.xyz[i]:.4f}")

            hsv_display = [vm.hsv[0], vm.hsv[1] * 100.0, vm.hsv[2] * 100.0]
            for i, name in enumerate("HSV"):
                self.sliders[f"hsv_{name}"].set_gradient_fn(self._gfn_hsv(i))
                self.sliders[f"hsv_{name}"].set_value(hsv_display[i])
                self.entries[f"hsv_{name}"].delete(0, "end")
                self.entries[f"hsv_{name}"].insert(0, f"{hsv_display[i]:.1f}")

            hexc = "#%02x%02x%02x" % tuple(vm.rgb)
            self.swatch.configure(bg=hexc)
            self.info_lbl.configure(
                text=f"HEX {hexc.upper()}   осветитель {vm.engine.illuminant}")
            self.warn_lbl.configure(text=vm.warning)
        finally:
            self._updating = False