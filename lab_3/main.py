
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk
import os
import threading
import queue
from processing import filters, morphology

class ImageProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Processor - Nonlinear Filters & Morphology")
        self.root.geometry("1200x800")

        # Variables
        self.original_image = None
        self.processed_image = None
        self.current_image = None
        self.display_image = None
        self.filter_type = tk.StringVar(value="none")
        self.morphology_type = tk.StringVar(value="none")
        self.padding_mode = tk.StringVar(value="reflect")
        self.ksize = tk.IntVar(value=3)
        self.alpha = tk.DoubleVar(value=0.2)
        self.morph_shape = tk.StringVar(value="cross")
        self.se_size = tk.IntVar(value=3)
        self.p_percentile = tk.DoubleVar(value=50.0)
        self.Q_contraharmonic = tk.DoubleVar(value=1.5)
        self.sigma_spatial = tk.DoubleVar(value=1.5)
        self.sigma_range = tk.DoubleVar(value=0.1)
        self.max_ksize = tk.IntVar(value=7)
        self.start_ksize = tk.IntVar(value=3)

        self.se = morphology.create_structuring_element(self.morph_shape.get(), self.se_size.get())

        self.result_queue = queue.Queue()
        self.processing = False

        self.create_gui()

        self.load_test_images()

    def create_gui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=5)

        ttk.Button(toolbar, text="Load Image", command=self.load_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Save Image", command=self.save_image).pack(side=tk.LEFT, padx=5)

        panels_frame = ttk.Frame(main_frame)
        panels_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        left_panel = ttk.LabelFrame(panels_frame, text="Image Preview")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self.image_frame = ttk.Frame(left_panel)
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas_original = tk.Canvas(self.image_frame)
        self.canvas_processed = tk.Canvas(self.image_frame)

        self.canvas_original.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.canvas_processed.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=2, pady=2)

        ttk.Label(self.image_frame, text="Original").pack(side=tk.LEFT, before=self.canvas_original)
        ttk.Label(self.image_frame, text="Processed").pack(side=tk.RIGHT, before=self.canvas_processed)

        hist_frame = ttk.LabelFrame(left_panel, text="Histograms (Intensity)")
        hist_frame.pack(fill=tk.X, padx=5, pady=5)

        self.hist_canvas_original = tk.Canvas(hist_frame, height=120, bg="white")
        self.hist_canvas_processed = tk.Canvas(hist_frame, height=120, bg="white")

        self.hist_canvas_original.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.hist_canvas_processed.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=2, pady=2)

        ttk.Label(hist_frame, text="Original").pack(side=tk.LEFT, before=self.hist_canvas_original)
        ttk.Label(hist_frame, text="Processed").pack(side=tk.RIGHT, before=self.hist_canvas_processed)

        right_panel = ttk.Frame(panels_frame, width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5)

        notebook = ttk.Notebook(right_panel)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text="Order Statistics")
        self.create_filters_tab(tab1)

        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text="Morphology")
        self.create_morphology_tab(tab2)

        tab3 = ttk.Frame(notebook)
        notebook.add(tab3, text="Advanced Filters")
        self.create_advanced_filters_tab(tab3)

        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))

        status_bar = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.status_bar = status_bar

        self.progress_bar = ttk.Progressbar(status_frame, mode="indeterminate", length=150)
        self.progress_bar.pack(side=tk.RIGHT, padx=(5, 0))

    def create_filters_tab(self, parent):
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frame = scrollable_frame

        ttk.Label(frame, text="Filter Type:").pack(anchor=tk.W, pady=2)
        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, pady=5)

        filters = ["none", "median", "min", "max", "percentile", "alpha_trimmed_mean", "adaptive_median", "contraharmonic_mean", "bilateral"]
        for f in filters:
            ttk.Radiobutton(filter_frame, text=f.replace('_', ' ').title(), variable=self.filter_type, value=f).pack(anchor=tk.W)

        param_frame = ttk.LabelFrame(frame, text="Common Parameters")
        param_frame.pack(fill=tk.X, pady=10)

        ttk.Label(param_frame, text="Kernel Size:").pack(anchor=tk.W)
        ttk.Scale(param_frame, from_=3, to=31, orient=tk.HORIZONTAL, variable=self.ksize, command=self.on_filter_change).pack(fill=tk.X)
        ttk.Label(param_frame, textvariable=self.ksize).pack(anchor=tk.W)

        ttk.Label(param_frame, text="Edge Padding:").pack(anchor=tk.W, pady=(5, 0))
        padding_frame = ttk.Frame(param_frame)
        padding_frame.pack(fill=tk.X, pady=2)
        ttk.Radiobutton(padding_frame, text="Reflect", variable=self.padding_mode, value="reflect").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(padding_frame, text="Clamp", variable=self.padding_mode, value="clamp").pack(side=tk.LEFT, padx=5)

        self.params_frame = ttk.LabelFrame(frame, text="Filter Parameters")
        self.params_frame.pack(fill=tk.X, pady=10)

        self.p_label = ttk.Label(self.params_frame, text="Percentile (0-100):")
        self.p_entry = ttk.Entry(self.params_frame, textvariable=self.p_percentile)
        self.p_label.pack(anchor=tk.W)
        self.p_entry.pack(fill=tk.X, pady=2)
        self.p_entry.pack_forget()

        self.alpha_label = ttk.Label(self.params_frame, text="Alpha (0.0-1.0):")
        self.alpha_entry = ttk.Entry(self.params_frame, textvariable=self.alpha)
        self.alpha_label.pack(anchor=tk.W)
        self.alpha_entry.pack(fill=tk.X, pady=2)
        self.alpha_entry.pack_forget()

        self.Q_label = ttk.Label(self.params_frame, text="Q (contraharmonic):")
        self.Q_entry = ttk.Entry(self.params_frame, textvariable=self.Q_contraharmonic)
        self.Q_label.pack(anchor=tk.W)
        self.Q_entry.pack(fill=tk.X, pady=2)
        self.Q_entry.pack_forget()

        self.sigma_s_label = ttk.Label(self.params_frame, text="Sigma Spatial:")
        self.sigma_s_entry = ttk.Entry(self.params_frame, textvariable=self.sigma_spatial)
        self.sigma_s_label.pack(anchor=tk.W)
        self.sigma_s_entry.pack(fill=tk.X, pady=2)
        self.sigma_s_entry.pack_forget()

        self.sigma_r_label = ttk.Label(self.params_frame, text="Sigma Range:")
        self.sigma_r_entry = ttk.Entry(self.params_frame, textvariable=self.sigma_range)
        self.sigma_r_label.pack(anchor=tk.W)
        self.sigma_r_entry.pack(fill=tk.X, pady=2)
        self.sigma_r_entry.pack_forget()

        self.max_ksize_label = ttk.Label(self.params_frame, text="Max Kernel Size:")
        self.max_ksize_entry = ttk.Entry(self.params_frame, textvariable=self.max_ksize)
        self.max_ksize_label.pack(anchor=tk.W)
        self.max_ksize_entry.pack(fill=tk.X, pady=2)
        self.max_ksize_entry.pack_forget()

        self.start_ksize_label = ttk.Label(self.params_frame, text="Start Kernel Size:")
        self.start_ksize_entry = ttk.Entry(self.params_frame, textvariable=self.start_ksize)
        self.start_ksize_label.pack(anchor=tk.W)
        self.start_ksize_entry.pack(fill=tk.X, pady=2)
        self.start_ksize_entry.pack_forget()

        self.apply_filter_btn = ttk.Button(frame, text="Apply Filter", command=self.apply_filter)
        self.apply_filter_btn.pack(pady=10)

    def create_morphology_tab(self, parent):
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frame = scrollable_frame

        ttk.Label(frame, text="Morphology Type:").pack(anchor=tk.W, pady=2)
        morph_frame = ttk.Frame(frame)
        morph_frame.pack(fill=tk.X, pady=5)

        morph_types = ["none", "erosion", "dilation", "opening", "closing", "gradient", "internal_gradient", "external_gradient", "top_hat", "black_hat"]
        for m in morph_types:
            ttk.Radiobutton(morph_frame, text=m.replace('_', ' ').title(), variable=self.morphology_type, value=m).pack(anchor=tk.W)

        se_frame = ttk.LabelFrame(frame, text="Structuring Element")
        se_frame.pack(fill=tk.X, pady=10)

        ttk.Label(se_frame, text="Shape:").pack(anchor=tk.W)
        shape_frame = ttk.Frame(se_frame)
        shape_frame.pack(fill=tk.X, pady=2)

        for shape in ["cross", "square", "diamond", "disk", "line_h", "line_v"]:
            ttk.Radiobutton(shape_frame, text=shape, variable=self.morph_shape, value=shape).pack(side=tk.LEFT, padx=5)

        ttk.Label(se_frame, text="Size:").pack(anchor=tk.W, pady=5)
        se_size_scale = ttk.Scale(se_frame, from_=3, to=21, orient=tk.HORIZONTAL, variable=self.se_size, command=self.update_se)
        se_size_scale.pack(fill=tk.X)
        ttk.Label(se_frame, textvariable=self.se_size).pack(anchor=tk.W)

        ttk.Label(se_frame, text="Edge Padding:").pack(anchor=tk.W, pady=(5, 0))
        morph_padding_frame = ttk.Frame(se_frame)
        morph_padding_frame.pack(fill=tk.X, pady=2)
        ttk.Radiobutton(morph_padding_frame, text="Reflect", variable=self.padding_mode, value="reflect").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(morph_padding_frame, text="Clamp", variable=self.padding_mode, value="clamp").pack(side=tk.LEFT, padx=5)

        self.se_preview = ttk.Label(se_frame, text="Structuring Element Preview:", background="gray")
        self.se_preview.pack(fill=tk.X, pady=5, ipady=50)

        self.apply_morph_btn = ttk.Button(frame, text="Apply Morphology", command=self.apply_morphology)
        self.apply_morph_btn.pack(pady=10)

    def create_advanced_filters_tab(self, parent):
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        frame = scrollable_frame

        summary_label = ttk.Label(frame, text="Nonlinear filters for order statistics:", font=("Helvetica", 10, "bold"))
        summary_label.pack(anchor=tk.W, pady=5)

        ttk.Label(frame, text="• Median filter: Median of pixel neighborhood\n" +
                        "• Min/Max filters: Erosion/Dilation\n" +
                        "• Percentile filter: K-th order statistic\n" +
                        "• Alpha-trimmed mean: Trim outliers then average\n" +
                        "• Adaptive median: Self-adjusting kernel size\n" +
                        "• Contraharmonic mean: Power mean of neighborhood\n" +
                        "• Bilateral: Edge-preserving smoothing\n").pack(anchor=tk.W, padx=5, pady=5)

        ttk.Label(frame, text="Morphological operations for structural analysis:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=5)

        ttk.Label(frame, text="• Erosion: Shrink bright regions\n" +
                        "• Dilation: Expand bright regions\n" +
                        "• Opening: Erosion followed by dilation\n" +
                        "• Closing: Dilation followed by erosion\n" +
                        "• Gradient: Edge detection\n" +
                        "• Top-hat/Black-hat: Small structures extraction\n").pack(anchor=tk.W, padx=5, pady=5)

    def load_test_images(self):
        test_frame = ttk.LabelFrame(self.root, text="Test Images")
        test_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(test_frame, text="Quick Load:").pack(side=tk.LEFT, padx=5)

        for i in range(min(4, 5)): 
            try:
                img_path = f"test_images/noisy/noise_gauss_{i}.png"
                if os.path.exists(img_path):
                    img = Image.open(img_path)
                    img.thumbnail((100, 100))
                    photo = ImageTk.PhotoImage(img)
                    btn = ttk.Button(test_frame, image=photo, command=lambda p=img_path: self.load_test_image(p))
                    btn.image = photo 
                    btn.pack(side=tk.LEFT, padx=2, pady=2)
            except Exception as e:
                print(f"Error loading test image: {e}")

    def load_test_image(self, path):
        try:
            img = Image.open(path)
            self.original_image = np.array(img)
            self.processed_image = np.array(img)
            self.current_image = np.array(img)
            self.display_image = img
            self.display_image_tk = ImageTk.PhotoImage(img)

            self.display_images()

            self.status_bar.config(text=f"Loaded test image: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")

    def load_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff")]
        )
        if file_path:
            try:
                img = Image.open(file_path)
                self.original_image = np.array(img)
                self.processed_image = np.array(img)
                self.current_image = np.array(img)
                self.display_image = img
                self.display_image_tk = ImageTk.PhotoImage(img)

                self.display_images()

                self.status_bar.config(text=f"Loaded image: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")

    def save_image(self):
        if self.processed_image is None:
            messagebox.showwarning("Warning", "No image to save")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("BMP files", "*.bmp")]
        )
        if file_path:
            try:
                img = Image.fromarray(self.processed_image.astype(np.uint8))
                img.save(file_path)
                self.status_bar.config(text=f"Saved image: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image: {e}")

    def display_images(self):
        if self.display_image is None:
            return

        max_width = self.canvas_original.winfo_width() - 20
        max_height = self.canvas_original.winfo_height() - 20

        self.canvas_original.delete("all")
        img_copy = self.display_image.copy()
        img_copy.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        self.original_tk = ImageTk.PhotoImage(img_copy)
        self.canvas_original.create_image(0, 0, image=self.original_tk, anchor=tk.NW)

        if self.processed_image is not None:
            self.canvas_processed.delete("all")
            if self.processed_image.dtype != np.uint8:
                img_proc = self.processed_image
                if img_proc.dtype.kind == 'f':
                    img_proc = np.clip(img_proc, 0, 255).astype(np.uint8)
                elif img_proc.dtype != np.uint8:
                    img_proc = (img_proc - img_proc.min()) / (img_proc.max() - img_proc.min()) * 255
                    img_proc = img_proc.astype(np.uint8)
                img_disp = Image.fromarray(img_proc)
                img_disp.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                self.processed_tk = ImageTk.PhotoImage(img_disp)
                self.canvas_processed.create_image(0, 0, image=self.processed_tk, anchor=tk.NW)

                self._draw_histogram(self.hist_canvas_processed, img_proc)

        self._draw_histogram(self.hist_canvas_original, np.array(self.display_image))

    def _draw_histogram(self, canvas, image):
        canvas.delete("all")
        if image.ndim == 3:
            intensity = np.dot(image[..., :3].astype(np.float64), [0.2989, 0.5870, 0.1140])
        else:
            intensity = image.astype(np.float64)

        hist, _ = np.histogram(intensity, bins=256, range=(0, 255))

        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1 or height <= 1:
            return

        max_count = hist.max()
        if max_count == 0:
            return

        bar_width = width / 256.0
        for i, count in enumerate(hist):
            bar_height = (count / max_count) * (height - 4)
            x0 = i * bar_width
            x1 = x0 + bar_width
            y0 = height - bar_height
            y1 = height
            canvas.create_rectangle(x0, y0, x1, y1, fill="steelblue", outline="")

    def on_filter_change(self, event=None):
        filter_type = self.filter_type.get()

        for widget in [self.p_label, self.p_entry, self.alpha_label, self.alpha_entry,
                       self.Q_label, self.Q_entry, self.sigma_s_label, self.sigma_s_entry,
                       self.sigma_r_label, self.sigma_r_entry, self.max_ksize_label, self.max_ksize_entry,
                       self.start_ksize_label, self.start_ksize_entry]:
            widget.pack_forget()

        if filter_type == "percentile":
            self.p_label.pack(anchor=tk.W)
            self.p_entry.pack(fill=tk.X, pady=2)
        elif filter_type == "alpha_trimmed_mean":
            self.alpha_label.pack(anchor=tk.W)
            self.alpha_entry.pack(fill=tk.X, pady=2)
        elif filter_type == "contraharmonic_mean":
            self.Q_label.pack(anchor=tk.W)
            self.Q_entry.pack(fill=tk.X, pady=2)
        elif filter_type == "bilateral":
            self.sigma_s_label.pack(anchor=tk.W)
            self.sigma_s_entry.pack(fill=tk.X, pady=2)
            self.sigma_r_label.pack(anchor=tk.W)
            self.sigma_r_entry.pack(fill=tk.X, pady=2)
        elif filter_type == "adaptive_median":
            self.max_ksize_label.pack(anchor=tk.W)
            self.max_ksize_entry.pack(fill=tk.X, pady=2)
            self.start_ksize_label.pack(anchor=tk.W)
            self.start_ksize_entry.pack(fill=tk.X, pady=2)

    def apply_filter(self):
        if self.current_image is None:
            messagebox.showwarning("Warning", "No image loaded")
            return
        if self.processing:
            return

        filter_type = self.filter_type.get()
        ksize = self.ksize.get()
        padding = self.padding_mode.get()
        p = self.p_percentile.get()
        alpha = self.alpha.get()
        max_ksize = self.max_ksize.get()
        start_ksize = self.start_ksize.get()
        Q = self.Q_contraharmonic.get()
        sigma_s = self.sigma_spatial.get()
        sigma_r = self.sigma_range.get()
        current_image = self.current_image
        display_image = self.display_image

        def compute():
            if filter_type == "none":
                return np.array(display_image)
            elif filter_type == "median":
                return filters.median_filter(current_image, ksize, padding=padding)
            elif filter_type == "min":
                return filters.min_filter(current_image, ksize, padding=padding)
            elif filter_type == "max":
                return filters.max_filter(current_image, ksize, padding=padding)
            elif filter_type == "percentile":
                return filters.percentile_filter(current_image, ksize, p, padding=padding)
            elif filter_type == "alpha_trimmed_mean":
                return filters.alpha_trimmed_mean_filter(current_image, ksize, alpha, padding=padding)
            elif filter_type == "adaptive_median":
                return filters.adaptive_median_filter(current_image, max_ksize, start_ksize, padding=padding)
            elif filter_type == "contraharmonic_mean":
                return filters.contraharmonic_mean_filter(current_image, ksize, Q, padding=padding)
            elif filter_type == "bilateral":
                return filters.bilateral_filter(current_image, ksize, sigma_s, sigma_r, padding=padding)
            return current_image

        self._run_in_background(compute, f"Applied filter: {filter_type}", "Failed to apply filter")

    def update_se(self, event=None):
        size = self.se_size.get()
        shape = self.morph_shape.get()
        self.se = morphology.create_structuring_element(shape, size)

        se_display = np.zeros((size, size, 3), dtype=np.uint8)
        se_display[self.se == 1] = [255, 255, 255]
        se_img = Image.fromarray(se_display)
        se_img.thumbnail((100, 100), Image.Resampling.LANCZOS)
        self.se_tk = ImageTk.PhotoImage(se_img)
        self.se_preview.configure(image=self.se_tk)

    def apply_morphology(self):
        if self.current_image is None:
            messagebox.showwarning("Warning", "No image loaded")
            return
        if self.processing:
            return

        morph_type = self.morphology_type.get()
        se = self.se
        padding = self.padding_mode.get()
        current_image = self.current_image
        display_image = self.display_image

        def compute():
            if morph_type == "none":
                return np.array(display_image)
            elif morph_type == "erosion":
                return morphology.erosion(current_image, se, padding=padding)
            elif morph_type == "dilation":
                return morphology.dilation(current_image, se, padding=padding)
            elif morph_type == "opening":
                return morphology.opening(current_image, se, padding=padding)
            elif morph_type == "closing":
                return morphology.closing(current_image, se, padding=padding)
            elif morph_type == "gradient":
                return morphology.gradient(current_image, se, padding=padding)
            elif morph_type == "internal_gradient":
                return morphology.internal_gradient(current_image, se, padding=padding)
            elif morph_type == "external_gradient":
                return morphology.external_gradient(current_image, se, padding=padding)
            elif morph_type == "top_hat":
                return morphology.top_hat(current_image, se, padding=padding)
            elif morph_type == "black_hat":
                return morphology.black_hat(current_image, se, padding=padding)
            return current_image

        self._run_in_background(compute, f"Applied morphology: {morph_type}", "Failed to apply morphology")

    def _run_in_background(self, compute_fn, done_message, error_prefix):
        self.processing = True
        self.apply_filter_btn.config(state=tk.DISABLED)
        self.apply_morph_btn.config(state=tk.DISABLED)
        self.status_bar.config(text="Processing...")
        self.progress_bar.start(10)

        def worker():
            try:
                result = compute_fn()
                self.result_queue.put(("ok", result))
            except Exception as e:
                self.result_queue.put(("error", e))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(50, self._check_queue, done_message, error_prefix)

    def _check_queue(self, done_message, error_prefix):
        try:
            status, payload = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(50, self._check_queue, done_message, error_prefix)
            return

        self.progress_bar.stop()
        self.apply_filter_btn.config(state=tk.NORMAL)
        self.apply_morph_btn.config(state=tk.NORMAL)
        self.processing = False

        if status == "ok":
            self.processed_image = payload
            self.display_images()
            self.status_bar.config(text=done_message)
        else:
            self.status_bar.config(text="Ready")
            messagebox.showerror("Error", f"{error_prefix}: {payload}")

    def on_canvas_resize(self, event):
        self.display_images()


def main():
    root = tk.Tk()
    app = ImageProcessorApp(root)

    app.canvas_original.bind("<Configure>", app.on_canvas_resize)
    app.canvas_processed.bind("<Configure>", app.on_canvas_resize)
    app.hist_canvas_original.bind("<Configure>", app.on_canvas_resize)
    app.hist_canvas_processed.bind("<Configure>", app.on_canvas_resize)

    root.mainloop()

if __name__ == "__main__":
    main()