# 🚀 Aria2 Multi-Thread Downloader Pro

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows-informational.svg)](https://www.microsoft.com/windows)

Aplikasi downloader berbasis Python yang membungkus keandalan **Aria2** untuk melakukan pengunduhan file super cepat menggunakan metode multi-threading — dilengkapi konsol log real-time dan manajemen download yang efisien.

</div>

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|---|---|
| ⚡ **Multi-threaded Downloading** | Membagi file menjadi beberapa bagian untuk memaksimalkan bandwidth |
| 🐍 **Venv Integrated** | Berjalan di dalam virtual environment yang terisolasi |
| 📋 **Log Console** | Memantau proses download secara real-time |

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
