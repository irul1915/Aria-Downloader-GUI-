import os
import time
from PySide6.QtCore import QThread, Signal
from core.ffmpeg_processor import FFmpegProcessor

class RPCPollerWorker(QThread):
    """ Worker terpisah agar jaringan RPC tidak memblokir GUI Utama """
    data_ready = Signal(list)

    def __init__(self, rpc):
        super().__init__()
        self.rpc = rpc
        self.is_running = True

    def run(self):
        while self.is_running:
            # Menggunakan metode yang benar dari Aria2RPC
            downloads = self.rpc.get_all_downloads()
            
            # Emit data hanya jika bukan None (None berarti RPC sedang di-lock oleh thread lain)
            self.data_ready.emit(downloads)
            
            # Interruptible sleep: memecah jeda 1 detik menjadi 10 x 0.1 detik
            # Ini memungkinkan thread berhenti seketika saat aplikasi ditutup
            for _ in range(10):
                if not self.is_running:
                    break
                time.sleep(0.1)

    def stop(self):
        self.is_running = False
        self.wait()


class MediaPipelineWorker(QThread):
    """ Worker orkestrator terpisah untuk mengunduh stream terpisah & memicu FFmpeg """
    status_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, rpc, title, video_url, audio_url, save_dir,
                 video_headers=None, audio_headers=None,
                 convert_audio_only=False, audio_format="mp3"):
        super().__init__()
        self.rpc = rpc
        # Membersihkan nama file agar aman dibaca OS
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
        """ Membangun opsi Aria2 termasuk HTTP headers agar stream URL tidak ditolak server. """
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
        """ Menghentikan proses loop secara aman """
        self.is_running = False

    def run(self):
        try:
            self.status_signal.emit("Menghubungkan stream ke backend Aria2...")
            
            v_filename = f"{self.title}_tmp_v.mp4"
            a_filename = f"{self.title}_tmp_a.m4a"
            
            v_path = os.path.join(self.save_dir, v_filename)
            a_path = os.path.join(self.save_dir, a_filename)

            # Skenario 1: Hanya Unduh Audio -> Convert ke Format Pilihan (MP3/FLAC/OPUS/dll)
            if self.convert_audio_only:
                url_to_download = self.audio_url if self.audio_url else self.video_url
                hdrs = self.audio_headers if self.audio_url else self.video_headers
                options = self._build_aria2_options(self.save_dir, a_filename, hdrs)
                
                # Menggunakan wrapper extended agar thread-safe
                a_gid = self.rpc.add_uri_extended([url_to_download], options)
                if not a_gid: 
                    raise Exception("Gagal menambahkan stream audio ke Aria2.")
                
                self._wait_aria_complete(a_gid, "Audio")
                
                if not self.is_running: return # Hentikan jika user membatalkan
                
                self.status_signal.emit(f"Mengonversi media ke format {self.audio_format.upper()} menggunakan FFmpeg...")
                final_audio_path = os.path.join(self.save_dir, f"{self.title}.{self.audio_format}")
                
                if FFmpegProcessor.convert_to_audio(a_path, final_audio_path):
                    self.finished_signal.emit(True, f"Sukses mengonversi audio ke {self.audio_format.upper()}!\nDisimpan di: {final_audio_path}")
                else:
                    raise Exception(f"FFmpeg gagal mengonversi audio ke format {self.audio_format.upper()}. Pastikan FFmpeg terpasang di komputer Anda.")
            
            # Skenario 2: Unduh Video + Audio Terpisah -> Muxing / Merge
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
        """ Polling internal spesifik menggunakan tell_status agar responsif & anti-freeze """
        while self.is_running:
            try:
                # Menggunakan wrapper tell_status thread-safe
                res = self.rpc.tell_status(gid)
                status = res.get('status')
                
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
                if "gagal di backend" in str(e).lower():
                    raise e
            
            # Interruptible sleep dalam loop
            for _ in range(10):
                if not self.is_running: return
                time.sleep(0.1)