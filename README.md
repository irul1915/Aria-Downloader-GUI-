# 🚀 Aria2 Multi-Thread Downloader Pro

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows-informational.svg)](https://www.microsoft.com/windows)

Aplikasi downloader all-in-one berbasis Python yang membungkus keandalan **Aria2** — mendukung direct link, torrent, magnet link, hingga download video & audio YouTube dengan kecepatan maksimal berkat multi-threading.

</div>

---

## ✨ Fitur Utama

### 🔗 1. Direct Link Downloader
- Download file dari URL langsung (HTTP/HTTPS/FTP)
- Mendukung **multi-threading** — file dibagi menjadi beberapa segmen untuk memaksimalkan kecepatan bandwidth
- Mendukung **resume download** jika koneksi terputus

### 🌊 2. Torrent Downloader
- Download via **file `.torrent`** — cukup browse dan pilih file torrent Anda
- Download via **Magnet Link** — tempel magnet link langsung di aplikasi
- Memanfaatkan engine Aria2 untuk manajemen peer yang efisien

### 🎬 3. YouTube Downloader
Download video maupun audio dari YouTube dengan mudah:

| Mode | Deskripsi |
|---|---|
| 🎥 **Video Download** | Download video dalam berbagai resolusi |
| 🎵 **Audio Only** | Ekstrak dan konversi audio ke berbagai format |

**Format audio yang didukung:**

| Format | Keterangan |
|---|---|
| `FLAC` | Lossless, kualitas tertinggi |
| `OPUS` | Lossy modern, ukuran kecil & kualitas baik |
| `MP3` | Format paling universal |
| `AAC` | Kompatibel luas, cocok untuk perangkat Apple |
| `WAV` | Uncompressed, cocok untuk editing audio |
| `M4A` | Format native YouTube, kualitas tinggi |

> Konversi audio menggunakan **FFmpeg** secara otomatis di background.

---

## ⚙️ Keunggulan Teknis

| Fitur | Deskripsi |
|---|---|
| ⚡ **Multi-threaded Downloading** | Membagi file menjadi beberapa bagian untuk memaksimalkan bandwidth |
| 🔄 **Resume Support** | Melanjutkan download yang terputus secara otomatis |
| 🐍 **Venv Integrated** | Berjalan di dalam virtual environment yang terisolasi |
| 📋 **Log Console Real-time** | Memantau progress dan log download secara langsung |
| 🎞️ **FFmpeg Integration** | Konversi audio/video langsung dari dalam aplikasi |

---

## 🛠️ Prasyarat

Pastikan komponen berikut sudah tersedia di sistem Anda sebelum melanjutkan:

- **[Python 3.10+](https://www.python.org/downloads/)** — Terinstal di sistem Anda
- **[Aria2c Binary](https://github.com/aria2/aria2/releases)** — Download binary resmi Aria2
- **[FFmpeg & FFprobe](https://www.gyan.dev/ffmpeg/builds/)** — Download FFmpeg Essentials build untuk Windows

---

## 📁 Struktur Direktori

> ⚠️ **Penting:** Binary eksternal tidak ikut diunggah karena ukurannya yang besar. Susun folder Anda secara manual sesuai struktur di bawah ini.

```
Aria-Downloader-GUI-/
├── aria2/
│   └── aria2c.exe          ← Letakkan aria2c.exe di sini
├── core/
├── ui/
├── ffmpeg.exe              ← Letakkan di folder utama project
├── ffprobe.exe             ← Letakkan di folder utama project
├── main.py
├── requirements.txt
└── Run.bat
```

---

## 📦 Instalasi & Penggunaan

### 1. Clone Repositori

```bash
git clone https://github.com/irul1915/Aria-Downloader-GUI-.git
cd Aria-Downloader-GUI-
```

### 2. Konfigurasi Binary Eksternal

- Buat folder `aria2/` di dalam folder utama project, lalu masukkan `aria2c.exe` ke dalamnya.
- Download FFmpeg Essentials, lalu ekstrak `ffmpeg.exe` dan `ffprobe.exe` langsung ke folder utama project (sejajar dengan `main.py`).

### 3. Buat & Aktifkan Virtual Environment

```bash
python -m venv venv
```

```bash
# Windows
venv\Scripts\activate
```

### 4. Instal Dependensi

```bash
pip install -r requirements.txt
```

### 5. Jalankan Aplikasi

Klik dua kali file **`Run.bat`**, atau jalankan via terminal:

```bash
python main.py
```

---

## 📄 Lisensi

Didistribusikan di bawah lisensi **MIT**. Lihat [`LICENSE`](LICENSE) untuk informasi lebih lanjut.
