# PYCLIPPER

YouTube Shorts/Reels Clipper — download video YouTube, dapatkan rekomendasi segmen klip dari AI, dan potong otomatis ke format portrait 1080×1920.

## Fitur

- Ambil metadata video YouTube (judul, channel, views, likes, dll.)
- Rekomendasi segmen klip pendek via AI (menggunakan `khazai`)
- Pilih resolusi video secara interaktif
- Download & konversi ke format vertikal 1080×1920 (siap upload ke Shorts/Reels)
- Caption siap posting per segmen

## Prasyarat

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/) terinstal di sistem

## Instalasi

```bash
pip install -r requirements.txt
```

## Penggunaan

```bash
python pyclipper.py
```

Masukkan URL YouTube atau video ID, lalu ikuti petunjuk interaktif.

## Cara Kerja

1. Masukkan URL/ID video YouTube
2. Script mengambil data video dan menampilkan info
3. AI menganalisis dan merekomendasikan 3–5 segmen terbaik untuk klip
4. Pilih segmen yang ingin dipotong
5. Pilih resolusi
6. Video di-download, dipotong, dan dikonversi ke portrait 1080×1920
