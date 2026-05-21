import sys
import os
import ctypes
from PySide6.QtWidgets import QApplication
from core.aria2_process import Aria2ProcessManager
from core.aria2_rpc import Aria2RPC
from database.db_manager import DBManager
from ui.main_window import MainWindow
from utils.logger import log

def is_admin():
    """ Memeriksa apakah skrip saat ini berjalan dengan hak akses Administrator """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin():
    """ 
    [FITUR BYPASS PRIVILEGE] 
    Memaksa Windows memunculkan dialog UAC untuk menaikkan privilese skrip ke Administrator penuh.
    """
    if sys.platform == 'win32' and not is_admin():
        log.info("Aplikasi mendeteksi kurangnya privilese. Meminta akses Administrator penuh...")
        # Mengambil argumen asli saat skrip dijalankan
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        
        # Menjalankan ulang dirinya sendiri dengan shell 'runas' (Run as Administrator)
        try:
            result = ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                sys.executable, 
                f'"{script}" {params}', 
                None, 
                1
            )
            # Jika proses pemicuan berhasil, matikan instansi script nond-admin ini
            if result > 32:
                sys.exit(0)
            else:
                log.error("Pengguna menolak memberikan izin Administrator.")
        except Exception as e:
            log.error(f"Gagal melakukan elevasi privilese: {e}")
            
        # Jika user menolak, aplikasi tetap berjalan di mode biasa (mungkin akan log error)

def main():
    # 1. Jalankan proteksi elevasi admin jika di Windows
    if sys.platform == 'win32':
        if not is_admin():
            run_as_admin()
            return # Keluar dari thread ini karena instansi baru versi Admin sedang dibuka

    log.info("Aplikasi berjalan dengan Hak Akses Istimewa Penuh (Privileged Mode).")

    # 2. Inisialisasi Aplikasi PySide6
    app = QApplication(sys.argv)

    # 3. Nyalakan Backend Aria2 Manager
    aria2_manager = Aria2ProcessManager()
    if not aria2_manager.start():
        log.critical("Aplikasi dihentikan karena backend Aria2 gagal inisialisasi.")
        sys.exit(1)

    # 4. Hubungkan ke RPC & Database
    rpc = Aria2RPC(url=f"http://localhost:{aria2_manager.port}/rpc")
    db = DBManager()

    # 5. Tampilkan Jendela Utama
    window = MainWindow(rpc, db)
    window.show()

    # 6. Amankan penutupan backend saat aplikasi ditutup oleh user
    exit_code = app.exec()
    
    log.info("Menutup aplikasi, membersihkan semua subprocess...")
    aria2_manager.stop()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()