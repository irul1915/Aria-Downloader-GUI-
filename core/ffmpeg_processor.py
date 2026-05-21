import subprocess
import os
import sys
import shutil
from utils.logger import log

class FFmpegProcessor:
    @staticmethod
    def _get_ffmpeg_command():
        """ Mendeteksi lokasi berkas biner ffmpeg secara aman & mendukung Cross-Platform """
        # Fix Bug: Hapus ketergantungan pada ekstensi .exe jika berjalan di Mac/Linux
        exe_name = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'

        if hasattr(sys, '_MEIPASS'):
            pyinstaller_path = os.path.join(sys._MEIPASS, exe_name)
            if os.path.exists(pyinstaller_path):
                return pyinstaller_path

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        local_project_path = os.path.join(project_root, exe_name)
        if os.path.exists(local_project_path):
            return local_project_path

        local_folder_path = os.path.join(project_root, 'ffmpeg', exe_name)
        if os.path.exists(local_folder_path):
            return local_folder_path

        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg

        return None

    @staticmethod
    def merge_video_audio(video_path, audio_path, output_path):
        """
        Menggabungkan video & audio secara instan dengan Sistem Fallback 3 Lapis
        untuk mencegah kegagalan akibat ketidakcocokan Codec (seperti WebM/VP9).
        """
        ffmpeg_cmd = FFmpegProcessor._get_ffmpeg_command()
        if not ffmpeg_cmd:
            log.error("FFmpeg tidak ditemukan di sistem PATH maupun folder proyek lokal.")
            return False

        creation_flags = 0x08000000 if sys.platform == "win32" else 0

        # Lapis 1: Muxing Instan (Pure Copy) - Selesai dalam 1-3 detik
        cmd_pure_copy = [
            ffmpeg_cmd, '-y', '-hide_banner', '-loglevel', 'error',
            '-i', video_path, '-i', audio_path,
            '-c:v', 'copy', '-c:a', 'copy',
            output_path
        ]

        try:
            subprocess.run(cmd_pure_copy, check=True, creationflags=creation_flags)
            FFmpegProcessor._cleanup_temp_files(video_path, audio_path)
            return True
            
        except subprocess.CalledProcessError:
            log.warning("Fast muxing murni gagal. Terdeteksi codec yang tidak kompatibel dengan MP4. Mencoba Fallback 1...")
            
            # Lapis 2: Muxing Semi-Instan (Video Copy, Audio dirubah ke AAC standar)
            # Sangat berguna jika videonya H.264 tapi audionya tidak standar
            cmd_audio_convert = [
                ffmpeg_cmd, '-y', '-hide_banner', '-loglevel', 'error',
                '-i', video_path, '-i', audio_path,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                '-threads', '0',
                output_path
            ]
            try:
                subprocess.run(cmd_audio_convert, check=True, creationflags=creation_flags)
                FFmpegProcessor._cleanup_temp_files(video_path, audio_path)
                return True
                
            except subprocess.CalledProcessError:
                log.warning("Fallback 1 gagal karena Video Codec (misal VP9/AV1) ditolak oleh MP4. Menggunakan Fallback Universal MKV...")
                
                # Lapis 3: Fallback Penyelamat (Ganti kontainer ke .mkv)
                # Memaksa stream copy berjalan sukses tanpa mempedulikan jenis codec
                base_name, _ = os.path.splitext(output_path)
                mkv_output_path = f"{base_name}.mkv"
                
                cmd_mkv_fallback = [
                    ffmpeg_cmd, '-y', '-hide_banner', '-loglevel', 'error',
                    '-i', video_path, '-i', audio_path,
                    '-c:v', 'copy', '-c:a', 'copy',
                    mkv_output_path
                ]
                
                try:
                    subprocess.run(cmd_mkv_fallback, check=True, creationflags=creation_flags)
                    FFmpegProcessor._cleanup_temp_files(video_path, audio_path)
                    log.info(f"Berhasil diselamatkan dan disimpan sebagai: {mkv_output_path}")
                    return True
                except Exception as e:
                    log.error(f"Semua lapis Muxing gagal total: {e}")
                    return False

    @staticmethod
    def convert_to_audio(input_path, output_path, bitrate='320k'):
        """
        Mengonversi media ke format audio pilihan secara optimal.
        Akan melewatkan render ulang jika input dan output memiliki format ekstensi yang sama.
        """
        ffmpeg_cmd = FFmpegProcessor._get_ffmpeg_command()
        if not ffmpeg_cmd:
            log.error("FFmpeg tidak ditemukan.")
            return False

        _, ext = os.path.splitext(output_path.lower())
        _, input_ext = os.path.splitext(input_path.lower())

        # Bypass kompresi ulang jika tidak diperlukan
        if (input_ext == '.m4a' and ext in ['.m4a', '.aac']) or (input_ext == ext):
            cmd = [
                ffmpeg_cmd, '-y', '-hide_banner', '-loglevel', 'error',
                '-i', input_path,
                '-vn', '-c:a', 'copy',
                output_path
            ]
        else:
            # Multi-threading aktif hanya jika benar-benar butuh konversi kompresi
            cmd = [
                ffmpeg_cmd, '-y', '-hide_banner', '-loglevel', 'error',
                '-i', input_path,
                '-vn', '-threads', '0'
            ]

            if ext == '.mp3':
                cmd.extend(['-c:a', 'libmp3lame', '-b:a', bitrate])
            elif ext == '.flac':
                cmd.extend(['-c:a', 'flac'])
            elif ext == '.opus':
                cmd.extend(['-c:a', 'libopus', '-b:a', '160k'])
            elif ext == '.wav':
                cmd.extend(['-c:a', 'pcm_s16le'])
            elif ext in ['.m4a', '.aac']:
                cmd.extend(['-c:a', 'aac', '-b:a', '256k'])
            else:
                cmd.extend(['-c:a', 'copy'])

            cmd.append(output_path)

        try:
            creation_flags = 0x08000000 if sys.platform == "win32" else 0
            subprocess.run(cmd, check=True, creationflags=creation_flags)
            
            # Hapus file mentah setelah konversi berhasil
            if os.path.exists(input_path) and input_path != output_path:
                os.remove(input_path)
            return True
            
        except Exception as e:
            log.error(f"FFmpeg Audio Conversion Error: {e}")
            return False

    @staticmethod
    def _cleanup_temp_files(video_path, audio_path):
        """ Fungsi helper internal untuk membersihkan file temporary secara aman """
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            log.warning(f"Gagal menghapus file temporary: {e}")