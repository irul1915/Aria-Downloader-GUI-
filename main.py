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
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin():
    if sys.platform == 'win32' and not is_admin():
        log.info("Aplikasi mendeteksi kurangnya privilese. Meminta akses Administrator penuh...")
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        
        try:
            result = ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                sys.executable, 
                f'"{script}" {params}', 
                None, 
                1
            )
            if result > 32:
                sys.exit(0)
            else:
                log.error("Pengguna menolak memberikan izin Administrator.")
        except Exception as e:
            log.error(f"Gagal melakukan elevasi privilese: {e}")

def main():
    if sys.platform == 'win32':
        if not is_admin():
            run_as_admin()
            return

    log.info("Aplikasi berjalan dengan Hak Akses Istimewa Penuh (Privileged Mode).")

    app = QApplication(sys.argv)

    aria2_manager = Aria2ProcessManager()
    if not aria2_manager.start():
        log.critical("Aplikasi dihentikan karena backend Aria2 gagal inisialisasi.")
        sys.exit(1)

    rpc = Aria2RPC(url=f"http://localhost:{aria2_manager.port}/rpc")
    db = DBManager()

    window = MainWindow(rpc, db)
    window.show()

    exit_code = app.exec()
    
    log.info("Menutup aplikasi, membersihkan semua subprocess...")
    
    # SAFETY NET: Pastikan session tersimpan sebelum proses aria2c dimatikan
    # Ini mencegah ghost download jika closeEvent tidak terpanggil (force kill, crash, dll.)
    try:
        rpc.save_session()
        log.info("Session aria2c berhasil disimpan sebelum shutdown backend.")
    except Exception as e:
        log.warning(f"Safety net saveSession gagal: {e}")
    
    aria2_manager.stop()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()