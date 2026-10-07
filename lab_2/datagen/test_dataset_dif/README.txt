=== ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ===

01_bmp_24bit_good.bmp: Статус OK. Ширина/Высота: 10x10, BPP: 24, Сжатие: BI_RGB. Палитра: отсутствует (Direct Color).
02_bmp_8bit_palette_good.bmp: Статус OK. BPP: 8. Палитра: 256 цветов (формат BGR0...).
03_bmp_8bit_rle_good.bmp: Статус OK. Сжатие: BI_RLE8.
04_bmp_truncated_bad.bmp: Статус 'Поврежден (Размер файла меньше указанного в заголовке)'.
05_png_good.png: Статус OK. Сжатие: Deflate. Фильтрация: Адаптивная (метод 0...).
06_png_no_iend_bad.png: Статус 'Поврежден (Отсутствует чанк IEND в конце файла)'.
07_png_truncated_ihdr_bad.png: Статус 'Поврежден (IHDR обрезан)'.
08_jpg_good.jpg: Статус OK. Сжатие: Huffman (DCT). DPI: 72x72 dpi.
09_jpg_no_eoi_bad.jpg: Статус 'Поврежден (Отсутствует маркер EOI (FF D9))'.
10_jpg_no_sof_bad.jpg: Статус 'Поврежден (JPG SOF not found)'.
11_gif_good.gif: Статус OK. Ширина/Высота: 10x10, BPP: 1, Сжатие: LZW.
12_gif_truncated_bad.gif: Статус 'Поврежден (GIF)'.
13_tiff_good.tiff: Статус OK. Ширина/Высота: 10x10, BPP: 8, Сжатие: Без сжатия.
14_tiff_bad_ifd.tiff: Статус 'Поврежден (TIFF IFD)' или ошибка чтения (выход за границы).
15_pcx_good.pcx: Статус OK. Ширина/Высота: 10x10, BPP: 8, Сжатие: RLE, DPI: 72x72.
16_pcx_truncated_bad.pcx: Статус 'Поврежден (PCX)'.
17_empty_file.xyz: Статус 'Пустой файл'.
18_unknown_format.dat: Статус 'Неизвестный формат / Поврежден'.