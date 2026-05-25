@echo off
setlocal enabledelayedexpansion
title Aria2 Multi-Thread Downloader Pro - Setup & Launcher

:: ============================================================
:: Aria2 Multi-Thread Downloader Pro - Smart Launcher
:: Auto-detect Python, Auto-install if missing, Auto-elevate
:: ============================================================

echo ============================================
echo   Aria2 Multi-Thread Downloader Pro
echo   Smart Launcher v1.0
echo ============================================
echo.

:: --- Fungsi: Cek apakah sedang berjalan sebagai Administrator ---
net session >nul 2>&1
if %errorlevel% == 0 (
    set "IS_ADMIN=1"
) else (
    set "IS_ADMIN=0"
)

:: --- Step 1: Deteksi Python ---
echo [1/3] Mengecek instalasi Python di sistem...

set "PYTHON_FOUND=0"
set "PYTHON_PATH="

:: Cek python di PATH
python --version >nul 2>&1
if %errorlevel% == 0 (
    set "PYTHON_FOUND=1"
    for /f "delims=" %%i in ('where python') do set "PYTHON_PATH=%%i"
    echo     [OK] Python ditemukan di PATH: %PYTHON_PATH%
    goto :PYTHON_OK
)

:: Cek python3 di PATH (untuk sistem yang menggunakan python3)
python3 --version >nul 2>&1
if %errorlevel% == 0 (
    set "PYTHON_FOUND=1"
    for /f "delims=" %%i in ('where python3') do set "PYTHON_PATH=%%i"
    echo     [OK] Python3 ditemukan di PATH: %PYTHON_PATH%
    goto :PYTHON_OK
)

:: Cek venv python (jika ada)
if exist "venv\Scripts\python.exe" (
    set "PYTHON_FOUND=1"
    set "PYTHON_PATH=venv\Scripts\python.exe"
    echo     [OK] Python ditemukan di virtual environment: %PYTHON_PATH%
    goto :PYTHON_OK
)

:: Cek lokasi umum instalasi Python
set "COMMON_PATHS=C:\Python39\python.exe C:\Python310\python.exe C:\Python311\python.exe C:\Python312\python.exe C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python39\python.exe C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe"

for %%p in (%COMMON_PATHS%) do (
    if exist "%%p" (
        set "PYTHON_FOUND=1"
        set "PYTHON_PATH=%%p"
        echo     [OK] Python ditemukan di: %%p
        goto :PYTHON_OK
    )
)

echo     [X] Python TIDAK ditemukan di sistem.
echo.

:: --- Step 2: Python tidak ditemukan, perlu instalasi ---
echo [2/3] Python tidak terdeteksi. Memulai proses instalasi otomatis...
echo.

:: Cek apakah sudah running sebagai admin
if %IS_ADMIN% == 0 (
    echo [!] Diperlukan hak akses Administrator untuk menginstal Python.
    echo     Mencoba menjalankan ulang sebagai Administrator...
    echo.

    :: Re-launch diri sendiri dengan runas
    powershell -Command "Start-Process '%~f0' -Verb runAs"
    exit /b
)

:: --- Running sebagai Admin, lanjut instalasi ---
echo [INFO] Menjalankan dengan hak Administrator. Melanjutkan instalasi Python...
echo.

:: Buat folder temp
set "TEMP_DIR=%TEMP%\AriaDownloader_Setup"
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: Download Python installer (versi 3.11 - stable dan compatible)
set "PYTHON_INSTALLER=%TEMP_DIR%\python_installer.exe"
echo [INFO] Mengunduh Python 3.11 dari official repository...
echo     URL: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
echo     Mohon tunggu, ini memerlukan koneksi internet...
echo.

powershell -Command "& {$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%PYTHON_INSTALLER%'}"

if not exist "%PYTHON_INSTALLER%" (
    echo [ERROR] Gagal mengunduh installer Python. Periksa koneksi internet Anda.
    echo.
    pause
    exit /b 1
)

echo [OK] Download berhasil. Memulai instalasi silent...
echo     Proses ini memerlukan waktu 2-5 menit...
echo.

:: Install Python dengan opsi silent
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_doc=0 Include_launcher=1 InstallLauncherAllUsers=1

if %errorlevel% neq 0 (
    echo [ERROR] Instalasi Python gagal. Exit code: %errorlevel%
    echo.
    pause
    exit /b 1
)

echo [OK] Instalasi Python selesai!
echo     Membersihkan file installer...
echo.

del /f /q "%PYTHON_INSTALLER%"

:: Refresh environment variables agar PATH baru terdeteksi
set "PATH=%PATH%;C:\Python311;C:\Python311\Scripts"

:: Verifikasi ulang
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python masih tidak terdeteksi setelah instalasi. Silakan restart komputer dan coba lagi.
    echo.
    pause
    exit /b 1
)

for /f "delims=" %%i in ('where python') do set "PYTHON_PATH=%%i"
echo [OK] Python berhasil diinstal dan terdeteksi: %PYTHON_PATH%
echo.

:: --- Step 3: Setup Virtual Environment & Dependencies ---
:PYTHON_OK
echo [3/3] Menyiapkan environment aplikasi...
echo.

:: Cek apakah venv sudah ada
if not exist "venv" (
    echo [INFO] Virtual environment belum ada. Membuat venv baru...
    "%PYTHON_PATH%" -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Gagal membuat virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment berhasil dibuat.
) else (
    echo [OK] Virtual environment ditemukan.
)

:: Cek dan install dependencies
if exist "requirements.txt" (
    echo [INFO] Menginstal dependensi dari requirements.txt...
    "venv\Scripts\pip.exe" install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [WARNING] Beberapa dependensi mungkin gagal diinstal, mencoba melanjutkan...
    ) else (
        echo [OK] Dependensi berhasil diinstal.
    )
) else (
    echo [INFO] File requirements.txt tidak ditemukan, melewati instalasi dependensi.
)

echo.
echo ============================================
echo   Setup Selesai - Memulai Aplikasi
echo ============================================
echo.

:: --- Jalankan Aplikasi ---
echo Menjalankan Aria2 Multi-Thread Downloader Pro...
echo.

"venv\Scripts\python.exe" main.py

echo.
echo ============================================
echo   Aplikasi telah ditutup.
echo ============================================
pause
