
import tkinter as tk


class GradientSlider(tk.Frame):
    BAR_H = 22
    HANDLE_W = 3

    def __init__(self, master, gradient_fn, minval, maxval, value,
                 command=None, width=340, height=44, label="", **kw):
        try:
            bg_color = master.cget("bg")
        except Exception:
            bg_color = "#f0f0f0"

        super().__init__(master, bg=bg_color, **kw)

        self._gfn = gradient_fn
        self._min, self._max = minval, maxval
        self._val = value
        self._cmd = command
        self._label = label
        self._img = None
        self._bar_width = width

        self._canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=bg_color,
        )
        self._canvas.pack(fill="both", expand=True)

        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.bind("<Button-1>", self._on_pointer)
        self._canvas.bind("<B1-Motion>", self._on_pointer)
        self.after(1, self.redraw)

    def set_value(self, v, silent=True):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return
        if v != v or v in (float("inf"), float("-inf")):   # NaN / ±inf
            return
        self._val = min(self._max, max(self._min, v))
        self.redraw()

    def get_value(self):
        return self._val

    def set_gradient_fn(self, fn):
        self._gfn = fn
        self.redraw()

    def redraw(self):
        c = self._canvas
        w = max(2, c.winfo_width())
        if w < 5:
            w = self._bar_width

        self._img = tk.PhotoImage(width=w, height=self.BAR_H)
        row = []
        for x in range(w):
            t = x / (w - 1)
            r, g, b = self._gfn(t)
            row.append(f"#{r:02x}{g:02x}{b:02x}")
        s = "{" + " ".join(row) + "}"
        for y in range(self.BAR_H):
            self._img.put(s, to=(0, y))

        c.delete("all")
        c.create_image(0, 0, image=self._img, anchor="nw")
        c.create_rectangle(0, 0, w - 1, self.BAR_H - 1,
                           outline="#555555", width=1)

        t = (self._val - self._min) / (self._max - self._min)
        hx = int(t * (w - 1))
        c.create_line(hx, -4, hx, self.BAR_H + 4,
                      fill="white", width=self.HANDLE_W + 2)
        c.create_line(hx, -4, hx, self.BAR_H + 4,
                      fill="black", width=self.HANDLE_W)

        c.create_text(6, self.BAR_H + 12, anchor="w", text=self._label,
                      fill="#333333", font=("Segoe UI", 8))

    def _on_resize(self, _evt):
        self.redraw()

    def _on_pointer(self, evt):
        c = self._canvas
        w = c.winfo_width()
        t = min(1.0, max(0.0, evt.x / (w - 1)))
        self._val = self._min + t * (self._max - self._min)
        self.redraw()
        if self._cmd:
            self._cmd(self._val)
    