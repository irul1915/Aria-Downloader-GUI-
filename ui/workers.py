import os
import time
from PySide6.QtCore import QThread, Signal
from core.ffmpeg_processor import FFmpegProcessor
from utils.logger import log

class RPCPollerWorker(QThread):
    data_ready = Signal(list)

    def __init__(self, rpc):
        super().__init__()
        self.rpc = rpc
        self.is_running = True

    def run(self):
        while self.is_running:
            downloads = self.rpc.get_all_downloads()
            self.data_ready.emit(downloads)
            
            for _ in range(10):
                if not self.is_running:
                    break
                time.sleep(0.1)

    def stop(self):
        self.is_running = False
        self.wait()


class AsyncActionWorker(QThread):
    finished_signal = Signal(bool, str)

    def __init__(self, rpc, action, gid):
        super().__init__()
        self.rpc = rpc
        self.action = action
        self.gid = gid

    def run(self):
        try:
            result = False
            if self.action == 'pause':
                result = self.rpc.pause(self.gid)
            elif self.action == 'resume':
                result = self.rpc.resume(self.gid)
            
            if result:
                self.finished_signal.emit(True, f"Aksi '{self.action}' berhasil untuk GID {self.gid}")
            else:
                self.finished_signal.emit(False, f"Aksi '{self.action}' gagal untuk GID {self.gid}")
        except Exception as e:
            self.finished_signal.emit(False, f"Error saat {self.action}: {str(e)}")


class DeleteDownloadWorker(QThread):
    """
    Worker universal untuk menghapus download.
    - Jika status active/waiting/paused: gunakan forceRemove + opsional hapus file fisik.
    - Jika status complete/error/removed: gunakan removeDownloadResult (tidak hapus file).
    """
    finished_signal = Signal(bool, str)

    def __init__(self, rpc, gid, delete_files=True):
        super().__init__()
        self.rpc = rpc
        self.gid = gid
        self.delete_files = delete_files

    def run(self):
        try:
            # 1. Cek status GID
            status_info = self.rpc.tell_status(self.gid)
            
            # Jika GID sudah tidak ada sama sekali
            if status_info is None:
                self.finished_signal.emit(True, f"Download GID {self.gid} sudah tidak ada di antrian.")
                return
            
            status = status_info.get('status', 'unknown')
            
            # Jika GID not found (fake dict dari tell_status)
            if status == 'removed' and "is not found" in status_info.get('errorMessage', ''):
                self.finished_signal.emit(True, f"Download GID {self.gid} sudah tidak ada di antrian.")
                return
            
            # 2. Ambil path file SEBELUM dihapus dari Aria2 (hanya jika perlu hapus fisik)
            file_paths = []
            if self.delete_files and status not in ('complete',):
                file_paths = self.rpc.get_download_files(self.gid)
            
            # 3. Pilih method remove sesuai status
            result = False
            if status in ('active', 'waiting', 'paused'):
                result = self.rpc.remove(self.gid)  # forceRemove
            else:
                # complete, error, removed (ada di stopped list)
                result = self.rpc.remove_stopped(self.gid)  # removeDownloadResult
            
            if not result:
                self.finished_signal.emit(False, f"Gagal menghapus download GID {self.gid} dari Aria2")
                return
            
            # 4. Hapus file fisik HANYA untuk download yang belum complete
            deleted_count = 0
            if self.delete_files and status not in ('complete',):
                for fp in file_paths:
                    try:
                        if os.path.exists(fp):
                            os.remove(fp)
                            deleted_count += 1
                            log.info(f"File dihapus dari disk: {fp}")
                    except Exception as e:
                        log.warning(f"Gagal menghapus file {fp}: {e}")
            
            # 5. Susun pesan sukses
            if status in ('complete',):
                msg = f"Download GID {self.gid} berhasil dihapus dari histori (file tetap tersimpan di disk)"
            else:
                msg = f"Download GID {self.gid} berhasil dihapus dari antrian"
                if deleted_count > 0:
                    msg += f" dan {deleted_count} file dihapus dari disk"
                elif file_paths:
                    msg += " (file belum tersedia atau sudah dihapus sebelumnya)"
            
            self.finished_signal.emit(True, msg)
            
        except Exception as e:
            self.finished_signal.emit(False, f"Error saat menghapus: {str(e)}")


class MediaPipelineWorker(QThread):
    status_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, rpc, title, video_url, audio_url, save_dir,
                 video_headers=None, audio_headers=None,
                 convert_audio_only=False, audio_format="mp3"):
        super().__init__()
        self.rpc = rpc
        self.title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-')]).strip()
        if not self.title:
            self.title = "Downloaded_Media"
        self.video_url = video_url
        self.audio_url = audio_url
        self.video_headers = video_headers or {}
        self.audio_headers = audio_headers or {}
        self.save_dir = save_dir
        self.convert_audio_only = convert_audio_only
        self.audio_format = audio_format.lower()
        self.is_running = True

    def _build_aria2_options(self, save_dir, filename, headers):
        options = {
            'dir': save_dir,
            'out': filename,
            'split': '16',                         
            'max-connection-per-server': '16',    
            'min-split-size': '1M',                
            'max-tries': '5',
            'retry-wait': '3',
        }
        if headers:
            header_list = [f"{k}: {v}" for k, v in headers.items()]
            options['header'] = header_list
        return options

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            self.status_signal.emit("Menghubungkan stream ke backend Aria2...")
            
            v_filename = f"{self.title}_tmp_v.mp4"
            a_filename = f"{self.title}_tmp_a.m4a"
            
            v_path = os.path.join(self.save_dir, v_filename)
            a_path = os.path.join(self.save_dir, a_filename)

            if self.convert_audio_only:
                url_to_download = self.audio_url if self.audio_url else self.video_url
                hdrs = self.audio_headers if self.audio_url else self.video_headers
                options = self._build_aria2_options(self.save_dir, a_filename, hdrs)
                
                a_gid = self.rpc.add_uri_extended([url_to_download], options)
                if not a_gid: 
                    raise Exception("Gagal menambahkan stream audio ke Aria2.")
                
                self._wait_aria_complete(a_gid, "Audio")
                
                if not self.is_running: return
                
                self.status_signal.emit(f"Mengonversi media ke format {self.audio_format.upper()} menggunakan FFmpeg...")
                final_audio_path = os.path.join(self.save_dir, f"{self.title}.{self.audio_format}")
                
                if FFmpegProcessor.convert_to_audio(a_path, final_audio_path):
                    self.finished_signal.emit(True, f"Sukses mengonversi audio ke {self.audio_format.upper()}!\nDisimpan di: {final_audio_path}")
                else:
                    raise Exception(f"FFmpeg gagal mengonversi audio ke format {self.audio_format.upper()}. Pastikan FFmpeg terpasang di komputer Anda.")
            
            else:
                if not self.video_url:
                    raise Exception("URL video kosong. Format yang dipilih mungkin menggunakan HLS/DASH manifest yang tidak didukung Aria2. Coba pilih resolusi lain.")

                v_options = self._build_aria2_options(self.save_dir, v_filename, self.video_headers)
                v_gid = self.rpc.add_uri_extended([self.video_url], v_options)
                if not v_gid: 
                    raise Exception("Gagal menambahkan stream video ke Aria2.")
                
                a_gid = None
                if self.audio_url:
                    a_options = self._build_aria2_options(self.save_dir, a_filename, self.audio_headers)
                    a_gid = self.rpc.add_uri_extended([self.audio_url], a_options)

                self._wait_aria_complete(v_gid, "Video")
                if a_gid and self.is_running:
                    self._wait_aria_complete(a_gid, "Audio")

                if not self.is_running: return

                final_video = os.path.join(self.save_dir, f"{self.title}_final.mp4")

                if a_gid and os.path.exists(a_path):
                    self.status_signal.emit("Menggabungkan track Video + Audio (FFmpeg Muxing)...")
                    if FFmpegProcessor.merge_video_audio(v_path, a_path, final_video):
                        self.finished_signal.emit(True, f"Sukses menggabungkan video & audio!\nDisimpan di: {final_video}")
                    else:
                        raise Exception("FFmpeg gagal menggabungkan video & audio. Pastikan FFmpeg terinstall di PATH.")
                else:
                    if os.path.exists(v_path):
                        os.rename(v_path, final_video)
                    self.finished_signal.emit(True, f"Sukses mengunduh video!\nDisimpan di: {final_video}")

        except Exception as e:
            if self.is_running:
                self.finished_signal.emit(False, str(e))

    def _wait_aria_complete(self, gid, label):
        consecutive_errors = 0
        max_errors = 5
        
        while self.is_running:
            try:
                res = self.rpc.tell_status(gid)
                
                if res is None:
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        raise Exception(f"Koneksi RPC gagal {max_errors}x berturut-turut saat polling {label}.")
                    self.status_signal.emit(f"Menunggu koneksi RPC untuk {label}... ({consecutive_errors}/{max_errors})")
                    for _ in range(5):
                        if not self.is_running: return
                        time.sleep(0.1)
                    continue
                
                consecutive_errors = 0
                status = res.get('status')
                
                # Jika user menghapus GID dari antrian, hentikan worker gracefully
                if status == 'removed' and "is not found" in res.get('errorMessage', ''):
                    raise Exception(f"Unduhan {label} dibatalkan karena dihapus oleh user dari antrian Aria2.")
                
                completed = int(res.get('completedLength', 0))
                total = int(res.get('totalLength', 0))
                speed_bytes = int(res.get('downloadSpeed', 0))
                
                progress = "0%"
                if total > 0:
                    progress = f"{(completed / total) * 100:.1f}%"
                
                if speed_bytes >= 1024 * 1024:
                    speed = f"{speed_bytes / (1024 * 1024):.2f} MB/s"
                else:
                    speed = f"{speed_bytes / 1024:.1f} KB/s"

                self.status_signal.emit(f"Mendownload {label} Stream [{progress}] - Speed: {speed}")
                
                if status == 'complete':
                    break
                elif status in ('error', 'removed'):
                    error_msg = res.get('errorMessage', 'Tidak ada pesan error dari Aria2.')
                    raise Exception(f"Unduhan {label} gagal di backend Aria2.\nPesan: {error_msg}")
                    
            except Exception as e:
                if any(k in str(e).lower() for k in ["gagal di backend", "dibatalkan karena dihapus", "koneksi rpc gagal"]):
                    raise e
            
            for _ in range(10):
                if not self.is_running: return
                time.sleep(0.1)