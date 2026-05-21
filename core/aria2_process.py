import subprocess
import os
import sys
import time
from pathlib import Path
from utils.logger import log

def get_resource_path(relative_path):
    """ Dapatkan path absolute yang mendukung development dan PyInstaller secara presisi """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    
    # Menggunakan folder tempat file ini berada, lalu naik satu tingkat ke root proyek
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class Aria2ProcessManager:
    def __init__(self):
        self.process = None
        self.port = 6850
        self.secret = "ariasecret123"

    def _cleanup_existing_process(self):
        """ Membersihkan sisa proses aria2c yang menggantung di Windows """
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "aria2c.exe"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=0x08000000
                )
                time.sleep(0.5)
            except Exception:
                pass

    def start(self):
        # 1. Bersihkan instansi lama
        self._cleanup_existing_process()

        # 2. Cari path biner aria2c.exe
        aria_exe = get_resource_path(os.path.join('aria2', 'aria2c.exe'))
        
        if not os.path.exists(aria_exe):
            # Pencarian cadangan di root folder jika ditaruh manual oleh pengguna
            aria_exe = os.path.join(os.getcwd(), 'aria2c.exe')
            if not os.path.exists(aria_exe):
                log.error("Biner aria2c.exe tidak ditemukan di folder /aria2/ maupun root proyek.")
                return False

        # 3. Tentukan folder unduhan aman
        download_dir = str(Path.home() / "Downloads" / "AriaDownloads")
        os.makedirs(download_dir, exist_ok=True)

        # 4. Buat file session kosong jika belum ada (mencegah error session lock)
        session_file = os.path.join(download_dir, "aria2.session")
        try:
            if not os.path.exists(session_file):
                with open(session_file, "w") as f:
                    pass
        except Exception as e:
            log.warning(f"Tidak bisa membuat file sesi: {e}")

        # 5. Susun argumen seaman mungkin (Menggunakan loopback lokal 127.0.0.1)
        args = [
            aria_exe,
            "--enable-rpc=true",
            "--rpc-allow-origin-all=true",
            f"--rpc-listen-port={self.port}",
            f"--rpc-secret={self.secret}",
            f"--input-file={session_file}",
            f"--save-session={session_file}",
            "--save-session-interval=60",
            "--max-concurrent-downloads=5",
            "--split=16",
            "--max-connection-per-server=16",
            "--min-split-size=1M",          # Memaksa file kecil tetap di-split
            "--disk-cache=64M",             # Menggunakan disk-cache 64MB agar Full Speed
            f"--dir={download_dir}",
            "--continue=true",
            "--quiet=true",
            "--disable-ipv6=true",          # Cukup diatur di sini sebagai opsi global
            "--max-tries=5",
            "--retry-wait=3",
            "--connect-timeout=30",
            "--timeout=60",
        ]

        try:
            creation_flags = 0x08000000 if sys.platform == "win32" else 0
            
            # Jalankan proses dengan penangkap pipe error
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                creationflags=creation_flags,
                cwd=os.path.dirname(aria_exe) # PAKSA working directory ke lokasi berkas .exe berada
            )
            
            # Beri jeda 1 detik untuk memantau stabilitas proses
            time.sleep(1.0)
            
            # Cek apakah proses langsung mati (poll() akan menghasilkan angka exit code jika mati)
            poll_status = self.process.poll()
            if poll_status is not None:
                # Ambil pesan kesalahan langsung dari sistem internal aria2c
                _, stderr_data = self.process.communicate()
                error_msg = stderr_data.decode(errors='ignore').strip()
                log.error(f"Aria2c keluar mendadak saat start (Exit Code: {poll_status}). Pesan: {error_msg}")
                return False

            log.info(f"Aria2 backend started di direktori: {download_dir}")
            return True
            
        except Exception as e:
            log.error(f"Gagal menyalakan eksekusi backend Aria2: {str(e)}")
            self.process = None
            return False

    def stop(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
                log.info("Aria2 backend stopped.")
            except Exception:
                self._cleanup_existing_process()
                log.info("Aria2 backend stopped via forced cleanup.")
            finally:
                self.process = None
        else:
            self._cleanup_existing_process()