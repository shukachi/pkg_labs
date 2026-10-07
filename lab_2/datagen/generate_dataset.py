import os
import struct

def create_dataset():
    base_dir = "test_dataset_8k"
    os.makedirs(base_dir, exist_ok=True)

    # =========================================================================
    # 8K ИЗОБРАЖЕНИЯ (7680 x 4320)
    # =========================================================================
    # 8K JPEG (Только заголовки, но с реальными размерами 7680x4320)
    soi = b'\xff\xd8'
    eoi = b'\xff\xd9'
    app0_len = struct.pack('>H', 16)
    app0_data = b'JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00'
    sof0_len = struct.pack('>H', 17)
    # precision=8, h=4320 (0x10E0), w=7680 (0x1E00), components=3
    sof0_data_8k = b'\x08\x10\xe0\x1e\x00\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01'
    with open(os.path.join(base_dir, "01_jpg_8k_good.jpg"), "wb") as f:
        f.write(soi + b'\xff\xe0' + app0_len + app0_data + b'\xff\xc0' + sof0_len + sof0_data_8k + eoi)

    # 8K PNG
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr_len = struct.pack('>I', 13)
    ihdr_type = b'IHDR'
    ihdr_data_8k = struct.pack('>IIBBBBB', 7680, 4320, 8, 2, 0, 0, 0)
    ihdr_crc = b'\x00\x00\x00\x00'
    iend_len = struct.pack('>I', 0)
    iend_type = b'IEND'
    iend_crc = b'\x00\x00\x00\x00'
    with open(os.path.join(base_dir, "02_png_8k_good.png"), "wb") as f:
        f.write(sig + ihdr_len + ihdr_type + ihdr_data_8k + ihdr_crc + iend_len + iend_type + iend_crc)

    # 8K GIF
    with open(os.path.join(base_dir, "03_gif_8k_good.gif"), "wb") as f:
        f.write(b'GIF89a' + struct.pack('<HH', 7680, 4320) + b'\x00\x00\x00')

    # =========================================================================
    # БИТЫЕ ФАЙЛЫ (Для проверки валидации)
    # =========================================================================
    # Битый 8K JPEG (Нет EOI)
    with open(os.path.join(base_dir, "04_jpg_8k_no_eoi_bad.jpg"), "wb") as f:
        f.write(soi + b'\xff\xe0' + app0_len + app0_data + b'\xff\xc0' + sof0_len + sof0_data_8k)
        
    # Пустой файл
    with open(os.path.join(base_dir, "05_empty.xyz"), "wb") as f: pass

    print(f"✅ Датасет с 8K создан в папке: {os.path.abspath(base_dir)}")

if __name__ == "__main__":
    create_dataset()