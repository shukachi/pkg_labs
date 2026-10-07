import os
import struct
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor

class ImageParser:
    @staticmethod
    def parse_file(filepath):
        try:
            with open(filepath, 'rb') as f:
                magic = f.read(8)
                if len(magic) < 2: return {"status": "Пустой файл"}
                if magic[:2] == b'BM': return ImageParser._parse_bmp(f)
                elif magic[:4] == b'\x89PNG': return ImageParser._parse_png(f)
                elif magic[:2] == b'\xff\xd8': return ImageParser._parse_jpg(f)
                elif magic[:3] == b'GIF': return ImageParser._parse_gif(f)
                elif magic[:2] in (b'II', b'MM'): return ImageParser._parse_tiff(f, magic[:2])
                elif magic[0:1] == b'\x0a' and magic[1] in (0, 2, 3, 4, 5): return ImageParser._parse_pcx(f)
                else: return {"status": "Неизвестный формат"}
        except Exception as e: return {"status": f"Ошибка чтения: {str(e)}"}

    @staticmethod
    def _parse_bmp(f):
        try:
            f.seek(0, 2); actual_size = f.tell(); f.seek(0)
            header = f.read(54)
            if len(header) < 54: return {"status": "Поврежден (BMP < 54 байт)"}
            data = struct.unpack('<2sIHHIIiiHHIIIIII', header)
            if actual_size < data[1]: return {"status": "Поврежден (Размер < bfSize)"}
            
            width, height = abs(data[6]), abs(data[7])
            bpp, comp, biClrUsed = data[9], data[10], data[11]
            x_ppm, y_ppm = data[12], data[13] 
            
            dpi = "Не задано"
            if x_ppm > 0 and y_ppm > 0:
                dpi = f"{round(x_ppm * 0.0254)}x{round(y_ppm * 0.0254)} dpi"
                
            comp_str = {0: "BI_RGB", 1: "BI_RLE8", 2: "BI_RLE4", 3: "BI_BITFIELDS"}.get(comp, f"Unknown({comp})")
            palette_info = f"Палитра: {biClrUsed if biClrUsed > 0 else (1 << bpp)} цветов." if bpp <= 8 else "Direct Color."
            
            return {"width": width, "height": height, "bpp": bpp, "compression": comp_str, "dpi": dpi, "palette_info": palette_info, "format": "BMP", "status": "OK"}
        except Exception as e: return {"status": f"Поврежден (BMP: {str(e)})"}

    @staticmethod
    def _parse_png(f):
        try:
            f.seek(0, 2); file_size = f.tell()
            if file_size < 20: return {"status": "Поврежден (PNG < 20 байт)"}
            f.seek(-12, 2)
            if f.read(12)[4:8] != b'IEND': return {"status": "Поврежден (Нет IEND)"}
            
            f.seek(8)
            width, height, bpp, dpi, color_type_str = 0, 0, 0, "Не задано", ""
            while f.tell() < file_size - 12:
                length = struct.unpack('>I', f.read(4))[0]
                chunk_type = f.read(4)
                if chunk_type == b'IHDR':
                    ihdr = f.read(13)
                    width, height = struct.unpack('>II', ihdr[:8])
                    bit_depth, color_type = ihdr[8], ihdr[9]
                    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type, 1)
                    bpp = bit_depth * channels
                    color_type_str = {0: "Grayscale", 2: "RGB", 3: "Indexed", 4: "Gray+Alpha", 6: "RGBA"}.get(color_type, "Unknown")
                    f.seek(length - 13, 1)
                elif chunk_type == b'pHYs':
                    phys = f.read(9)
                    x_ppu, y_ppu, unit = struct.unpack('>IIB', phys)
                    if unit == 1: dpi = f"{round(x_ppu * 0.0254)}x{round(y_ppu * 0.0254)} dpi"
                    f.seek(length - 9, 1)
                elif chunk_type in (b'IDAT', b'IEND'): break
                else: f.seek(length, 1)
                f.seek(4, 1) 
            return {"width": width, "height": height, "bpp": bpp, "compression": "Deflate (zlib)", "dpi": dpi, "color_type": color_type_str, "format": "PNG", "status": "OK"}
        except Exception as e: return {"status": f"Поврежден (PNG: {str(e)})"}

    @staticmethod
    def _parse_jpg(f):
        try:
            f.seek(0, 2); file_size = f.tell()
            if file_size < 4: return {"status": "Поврежден (JPG < 4 байт)"}
            f.seek(-2, 2)
            if f.read(2) != b'\xff\xd9': return {"status": "Поврежден (Нет EOI)"}
            
            f.seek(2)
            width, height, bpp, dpi = 0, 0, 0, "Не задано"
            dqt_count = 0
            while True:
                marker = f.read(2)
                if len(marker) < 2 or marker[0] != 0xFF: break
                m_type = marker[1]
                if m_type == 0xD9: break
                seg_len = struct.unpack('>H', f.read(2))[0]
                if m_type in (0xC0, 0xC1, 0xC2):
                    precision = struct.unpack('B', f.read(1))[0]
                    h, w = struct.unpack('>HH', f.read(4))
                    components = struct.unpack('B', f.read(1))[0]
                    width, height, bpp = w, h, precision * components
                    f.seek(seg_len - 8, 1)
                elif m_type == 0xE0:
                    jfif = f.read(5)
                    if jfif == b'JFIF\x00':
                        f.read(2)
                        units = struct.unpack('B', f.read(1))[0]
                        x_dens, y_dens = struct.unpack('>HH', f.read(4))
                        if units == 1: dpi = f"{x_dens}x{y_dens} dpi"
                        elif units == 2: dpi = f"{x_dens}x{y_dens} dpcm"
                    f.seek(seg_len - 14, 1)
                elif m_type == 0xDB:
                    dqt_count += 1
                    f.seek(seg_len - 2, 1)
                else: f.seek(seg_len - 2, 1)
            if width == 0: return {"status": "Поврежден (JPG SOF not found)"}
            return {"width": width, "height": height, "bpp": bpp, "compression": "Huffman (DCT)", "dpi": dpi, "dqt_count": dqt_count, "format": "JPEG", "status": "OK"}
        except Exception as e: return {"status": f"Поврежден (JPG: {str(e)})"}

    @staticmethod
    def _parse_gif(f):
        try:
            f.seek(6)
            header = f.read(7)
            if len(header) < 7: return {"status": "Поврежден (GIF)"}
            width, height = struct.unpack('<HH', header[:4])
            packed = header[4]
            bpp = (packed & 0x07) + 1
            has_global_palette = (packed & 0x80) != 0
            palette_size = (1 << bpp) if has_global_palette else 0
            return {"width": width, "height": height, "bpp": bpp, "compression": "LZW", "palette_size": palette_size, "format": "GIF", "status": "OK"}
        except Exception as e: return {"status": f"Поврежден (GIF: {str(e)})"}

    @staticmethod
    def _parse_tiff(f, endian_mark):
        try:
            fmt = '<' if endian_mark == b'II' else '>'
            f.seek(4)
            ifd_offset = struct.unpack(fmt + 'I', f.read(4))[0]
            f.seek(ifd_offset)
            num_entries = struct.unpack(fmt + 'H', f.read(2))[0]
            if num_entries > 1000: return {"status": "Поврежден (TIFF IFD)"}
            tags = {}
            for _ in range(num_entries):
                entry = f.read(12)
                if len(entry) < 12: break
                tag, type_id, count, value_offset = struct.unpack(fmt + 'HHII', entry)
                tags[tag] = (type_id, count, value_offset)
            def get_val(tag):
                if tag not in tags: return None
                t, c, v = tags[tag]
                if t == 3 and c == 1: return v & 0xFFFF
                if t == 4 and c == 1: return v
                return v
            def get_rational(tag):
                if tag not in tags: return None
                t, c, v = tags[tag]
                if t == 5 and c == 1:
                    f.seek(v)
                    num, den = struct.unpack(fmt + 'II', f.read(8))
                    return num / den if den != 0 else 0
                return None
            width, height, bpp, comp = get_val(256), get_val(257), get_val(258), get_val(259)
            res_unit = get_val(296)
            x_res, y_res = get_rational(282), get_rational(283)
            dpi = "Не задано"
            if x_res and y_res:
                if res_unit == 3: x_res *= 2.54; y_res *= 2.54
                dpi = f"{round(x_res)}x{round(y_res)} dpi"
            comp_str = {1: "Без сжатия", 5: "LZW", 7: "JPEG", 8: "Deflate"}.get(comp, f"Unknown({comp})")
            if not width or not height: return {"status": "Поврежден (TIFF: нет геометрии)"}
            return {"width": width, "height": height, "bpp": bpp, "compression": comp_str, "dpi": dpi, "format": "TIFF", "status": "OK"}
        except Exception as e: return {"status": f"Поврежден (TIFF: {str(e)})"}

    @staticmethod
    def _parse_pcx(f):
        try:
            f.seek(0)
            header = f.read(128)
            if len(header) < 128: return {"status": "Поврежден (PCX)"}
            xmin, ymin, xmax, ymax = struct.unpack('<HHHH', header[4:12])
            hdpi, vdpi = struct.unpack('<HH', header[12:16])
            bpp = header[3]
            return {"width": xmax - xmin + 1, "height": ymax - ymin + 1, "bpp": bpp, "compression": "RLE", "dpi": f"{hdpi}x{vdpi} dpi", "format": "PCX", "status": "OK"}
        except Exception as e: return {"status": f"Поврежден (PCX: {str(e)})"}

class ScanEngine:
    def __init__(self):
        self.is_running = False
        self.result_queue = queue.Queue() 
    def start_scan(self, folder_path):
        if self.is_running: return
        files = [os.path.join(root, name) for root, _, filenames in os.walk(folder_path) for name in filenames]
        if not files:
            self.result_queue.put(('ERROR', "Файлы не найдены."))
            return
        self.is_running = True
        self.result_queue.put(('SET_MAX_PROGRESS', len(files)))
        threading.Thread(target=self._worker, args=(files,), daemon=True).start()
    def _worker(self, files):
        with ThreadPoolExecutor(max_workers=min(os.cpu_count() or 4, 8)) as executor:
            futures = {executor.submit(ImageParser.parse_file, f): f for f in files}
            processed = 0
            for future in futures:
                filepath = futures[future]
                try:
                    result = future.result()
                    result['filename'] = os.path.basename(filepath)
                    result['path'] = filepath
                    self.result_queue.put(('DATA', result))
                except Exception as e:
                    self.result_queue.put(('DATA', {'filename': os.path.basename(filepath), 'path': filepath, 'status': f'Ошибка: {e}'}))
                processed += 1
                self.result_queue.put(('PROGRESS', processed))
        self.result_queue.put(('DONE', None))
        self.is_running = False

class AppView:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Metadata Extractor (Рубин Дмитрий)")
        self.root.geometry("1050x750")
        self.engine = ScanEngine()
        self.items_data = {} 
        self.folder_path = ""
        self._build_ui()
        self._poll_queue()

    def _build_ui(self):
        ctrl_frame = ttk.Frame(self.root, padding=10)
        ctrl_frame.pack(fill=tk.X)
        self.lbl_path = ttk.Label(ctrl_frame, text="Папка не выбрана", foreground="blue")
        self.lbl_path.pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="Выбрать папку", command=self._select_folder).pack(side=tk.LEFT, padx=5)
        self.btn_start = ttk.Button(ctrl_frame, text="Сканировать", command=self._start_scan, state=tk.DISABLED)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        self.progress_bar = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)
        
        columns = ("filename", "width", "height", "bpp", "compression", "dpi", "status")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings")
        for col, text, w in zip(columns, ["Имя файла", "Ширина (px)", "Высота (px)", "Глубина (bit)", "Сжатие", "Разрешение (DPI)", "Статус"], [200, 70, 70, 70, 120, 110, 180]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w)
        scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5, side=tk.TOP)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        
        details_frame = ttk.LabelFrame(self.root, text="📖 Детальный анализ (Откуда берется / Зачем нужна / Формулы)", padding=10)
        details_frame.pack(fill=tk.X, padx=10, pady=10, side=tk.BOTTOM)
        self.lbl_details = tk.Text(details_frame, height=14, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 10), bg="#fcfcfc", relief=tk.FLAT)
        self.lbl_details.pack(fill=tk.X)
        self._update_details("Выберите файл из списка для детального анализа.")

    def _update_details(self, text):
        self.lbl_details.config(state=tk.NORMAL)
        self.lbl_details.delete(1.0, tk.END)
        self.lbl_details.insert(tk.END, text)
        self.lbl_details.config(state=tk.DISABLED)

    def _select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.folder_path = path
            self.lbl_path.config(text=f"Выбрано: {os.path.basename(path)}")
            self.btn_start.config(state=tk.NORMAL)

    def _start_scan(self):
        self.tree.delete(*self.tree.get_children())
        self.items_data.clear()
        self._update_details("Выберите файл из списка для детального анализа.")
        self.btn_start.config(state=tk.DISABLED)
        self.engine.start_scan(self.folder_path)

    def _poll_queue(self):
        try:
            while True:
                msg_type, payload = self.engine.result_queue.get_nowait()
                if msg_type == 'SET_MAX_PROGRESS':
                    self.progress_bar['maximum'] = payload
                    self.progress_bar['value'] = 0
                elif msg_type == 'PROGRESS': self.progress_bar['value'] = payload
                elif msg_type == 'DATA': self._add_row(payload)
                elif msg_type == 'DONE': self.btn_start.config(state=tk.NORMAL)
                elif msg_type == 'ERROR':
                    messagebox.showinfo("Информация", payload)
                    self.btn_start.config(state=tk.NORMAL)
        except queue.Empty: pass
        self.root.after(50, self._poll_queue)

    def _add_row(self, data):
        is_ok = data.get('status') == 'OK'
        vals = (data.get('filename', ''), data.get('width', '') if is_ok else '', data.get('height', '') if is_ok else '', data.get('bpp', '') if is_ok else '', data.get('compression', '') if is_ok else '', data.get('dpi', '') if is_ok else '', data.get('status', ''))
        item_id = self.tree.insert("", tk.END, values=vals)
        self.items_data[item_id] = data

    def _on_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        data = self.items_data.get(selected[0], {})
        lines = [f"📁 ФАЙЛ: {data.get('filename', 'N/A')}", f"📂 ПУТЬ: {data.get('path', 'N/A')}\n"]
        
        if data.get('status') == 'OK':
            w, h = data.get('width', 0), data.get('height', 0)
            
            if w and h:
                megapixels = (w * h) / 1_000_000
                aspect_ratio = w / h if h > 0 else 0
                lines.append(f"📐 1. СООТНОШЕНИЕ СТОРОН (Aspect Ratio): {aspect_ratio:.2f}")
                lines.append(f"   ├─ Формула: Width / Height ({w} / {h})")
                lines.append(f"   └─ Зачем нужна: Показывает геометрические пропорции изображения (напр., 1.78 — это 16:9).")
                lines.append(f"🖼️ 2. РАЗРЕШЕНИЕ В МЕГАПИКСЕЛЯХ: {megapixels:.2f} MP")
                lines.append(f"   ├─ Формула: (Width * Height) / 1_000_000")
                lines.append(f"   └─ Зачем нужна: Показывает общее количество светочувствительных точек (важно для печати и кропа).\n")
            
            dpi_val = data.get('dpi', 'Не задано')
            lines.append(f"🖨️ 3. ПЛОТНОСТЬ ПИКСЕЛЕЙ (DPI): {dpi_val}")
            lines.append(f"   ├─ Откуда берется: Считывается из заголовка (APP0 в JPG, pHYs в PNG, biXPelsPerMeter в BMP).")
            lines.append(f"   └─ Зачем нужна: Указывает принтеру, сколько точек на дюйм использовать. На экран НЕ влияет!")
            lines.append(f"   ⚠️ Примечание: DPI НЕЛЬЗЯ рассчитать через W и H, так как файл не знает своего физ. размера в дюймах.\n")
            
            lines.append(f"🎨 4. ГЛУБИНА ЦВЕТА (BPP): {data.get('bpp')} бит (Откуда: IHDR/SOF/biBitCount. Зачем: Определяет кол-во оттенков).")
            lines.append(f"🗜️ 5. СЖАТИЕ: {data.get('compression')} (Откуда: Заголовок формата. Зачем: Алгоритм упаковки данных).\n")
            
            lines.append("✨ 6. СПЕЦИФИЧНЫЕ ПАРАМЕТРЫ ФОРМАТА:")
            if 'palette_info' in data: lines.append(f"   • [BMP] {data['palette_info']}")
            if 'color_type' in data: lines.append(f"   • [PNG] Color Type: {data['color_type']}")
            if 'palette_size' in data: lines.append(f"   • [GIF] Размер палитры: {data['palette_size']} цветов.")
            if 'dqt_count' in data: lines.append(f"   • [JPEG] Таблиц квантования (DQT): {data['dqt_count']} шт.")
        else:
            lines.append(f"❌ СОСТОЯНИЕ: Файл поврежден.\n   Детали: {data.get('status')}")
        self._update_details("\n".join(lines))

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    if 'clam' in style.theme_names(): style.theme_use('clam')
    AppView(root)
    root.mainloop()