# 🚀 Aria2 Multi-Thread Downloader Pro

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Aria2 Multi-Thread Downloader Pro adalah aplikasi berbasis Python yang membungkus keandalan Aria2 untuk melakukan pengunduhan file super cepat menggunakan metode multi-threading. Dilengkapi dengan konsol log interaktif dan manajemen download yang efisien.

## ✨ Fitur Utama
- **Multi-threaded Downloading:** Membagi file menjadi beberapa bagian untuk memaksimalkan bandwidth.
- **Venv Integrated:** Berjalan mulus di dalam virtual environment terisolasi.
- **Log Console:** Memantau proses download secara real-time.

## 🛠️ Prasyarat
Sebelum menjalankan aplikasi ini, pastikan Anda sudah menyiapkan komponen berikut:
- **Python 3.10+** (Terinstal di sistem Anda)
- **Aria2c Binary:** Unduh [Aria2](https://github.com/aria2/aria2/releases) resmi.
- **FFmpeg & FFprobe:** Unduh biner [FFmpeg Essentials](https://www.gyan.dev/ffmpeg/builds/) untuk Windows.

## 📦 Instalasi & Penggunaan

1. **Clone Repositori ini:**
   ```bash
   git clone [https://github.com/irul1915/Aria-Downloader-GUI-.git](https://github.com/irul1915/Aria-Downloader-GUI-.git)
   cd Aria-Downloader-GUI-
Konfigurasi Folder & File Eksternal (PENTING):
Aplikasi ini membutuhkan binary eksternal yang tidak ikut diunggah karena ukuran filenya yang besar. Silakan atur struktur folder Anda menjadi seperti ini:

Buat folder bernama aria2 di dalam folder utama project, lalu masukkan file aria2c.exe ke dalamnya.

Unduh FFmpeg, lalu ekstrak file ffmpeg.exe dan ffprobe.exe langsung di folder utama project (satu tingkat/setara dengan file main.py).

Struktur direktori Anda harus terlihat seperti ini:

Plaintext
Aria-Downloader-GUI-/
├── aria2/
│   └── aria2c.exe
├── core/
├── ui/
├── ffmpeg.exe
├── ffprobe.exe
├── main.py
└── Run.bat
Buat dan Aktifkan Virtual Environment:

Bash
python -m venv venv
# Windows
venv\Scripts\activate
Instal Dependensi:

Bash
pip install -r requirements.txt
Jalankan Aplikasi:
Klik ganda pada file Run.bat atau jalankan via terminal:

Bash
python main.py