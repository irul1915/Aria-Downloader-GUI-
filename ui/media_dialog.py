from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import QThread, Signal, Qt
from core.ytdlp_extractor import YTDLPExtractor

class AnalyzeWorker(QThread):
    result_ready = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            extractor = YTDLPExtractor()
            data = extractor.analyze_url(self.url)
            self.result_ready.emit(data)
        except Exception as e:
            self.error_occurred.emit(str(e))

class MediaDownloaderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.metadata = None
        self.selected_video_url = None
        self.selected_audio_url = None
        self.selected_video_headers = {}  # [FIX] HTTP headers untuk stream video
        self.selected_audio_headers = {}  # [FIX] HTTP headers untuk stream audio
        self.convert_audio_only = False
        self.selected_audio_format = "mp3" # Default format
        
        self.setWindowTitle("Media Extractor (yt-dlp + FFmpeg)")
        self.setMinimumSize(750, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste URL Video (YouTube, TikTok, Twitter, Instagram, dll...)")
        self.btn_analyze = QPushButton("🔍 Analyze URL")
        self.btn_analyze.clicked.connect(self.start_analysis)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.btn_analyze)
        layout.addLayout(url_layout)

        self.lbl_info = QLabel("Masukkan URL video untuk di-ekstrak oleh yt-dlp.")
        self.lbl_info.setStyleSheet("font-weight: bold; color: #333333;")
        self.lbl_info.setWordWrap(True)
        layout.addWidget(self.lbl_info)

        self.table_formats = QTableWidget(0, 5)
        self.table_formats.setHorizontalHeaderLabels(["Resolution/Type", "Extension", "FPS", "Bitrate", "Size Estimate"])
        self.table_formats.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_formats.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_formats.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table_formats)

        layout.addWidget(QLabel("Audio Track (Untuk digabungkan ke Video):"))
        self.combo_audio = QComboBox()
        layout.addWidget(self.combo_audio)

        btn_layout = QHBoxLayout()
        self.btn_dl_video = QPushButton("🎬 Download Video + Audio")
        self.btn_dl_audio = QPushButton("🎵 Download Audio Only")
        self.btn_dl_video.setEnabled(False)
        self.btn_dl_audio.setEnabled(False)
        
        # [FITUR BARU] Menu dropdown pilihan format audio ekstensi lagu
        self.lbl_format = QLabel("Format Audio:")
        self.combo_audio_format = QComboBox()
        self.combo_audio_format.addItems(["mp3", "flac", "opus", "wav", "m4a", "aac"])
        self.combo_audio_format.setFixedWidth(75)
        self.combo_audio_format.currentTextChanged.connect(self.update_audio_button_text)
        
        self.btn_dl_video.clicked.connect(lambda: self.process_selection(audio_only=False))
        self.btn_dl_audio.clicked.connect(lambda: self.process_selection(audio_only=True))
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.lbl_format)
        btn_layout.addWidget(self.combo_audio_format)
        btn_layout.addWidget(self.btn_dl_audio)
        btn_layout.addWidget(self.btn_dl_video)
        layout.addLayout(btn_layout)
        
        self.update_audio_button_text()

    def update_audio_button_text(self):
        """ Mengubah label tombol secara dinamis mengikuti pilihan format """
        fmt = self.combo_audio_format.currentText().upper()
        self.btn_dl_audio.setText(f"🎵 Download Audio Only ({fmt})")

    def start_analysis(self):
        url = self.url_input.text().strip()
        if not url: return
        
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setText("Analyzing...")
        self.lbl_info.setText("Sedang menghubungi server via yt-dlp API (Anti-Freeze)...")
        
        self.worker = AnalyzeWorker(url)
        self.worker.result_ready.connect(self.on_success)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def on_success(self, data):
        self.metadata = data
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("🔍 Analyze URL")
        self.lbl_info.setText(f"🎬 Judul: {data['title']}\n👤 Channel/Uploader: {data['uploader']}")

        self.table_formats.setRowCount(0)
        self.combo_audio.clear()

        videos = [f for f in data['formats'] if f['vcodec'] != 'none']
        audios = [f for f in data['formats'] if f['acodec'] != 'none' and f['vcodec'] == 'none']

        for idx, v in enumerate(reversed(videos)):
            self.table_formats.insertRow(idx)
            size_mb = f"{v['filesize']/(1024*1024):.1f} MB" if v['filesize'] else "Unknown"
            
            item_res = QTableWidgetItem(v['resolution'])
            # [FIX] Simpan URL + headers sekaligus sebagai dict
            item_res.setData(Qt.UserRole, {'url': v['url'], 'headers': v.get('http_headers', {})})
            
            self.table_formats.setItem(idx, 0, item_res)
            self.table_formats.setItem(idx, 1, QTableWidgetItem(v['ext']))
            self.table_formats.setItem(idx, 2, QTableWidgetItem(str(v['fps'])))
            self.table_formats.setItem(idx, 3, QTableWidgetItem(f"{v['tbr']:.0f} kbps" if isinstance(v['tbr'], (int, float)) else "-"))
            self.table_formats.setItem(idx, 4, QTableWidgetItem(size_mb))

        for a in reversed(audios):
            size_mb = f" ({a['filesize']/(1024*1024):.1f} MB)" if a['filesize'] else ""
            # [FIX] Simpan URL + headers sebagai dict di userData combo
            self.combo_audio.addItem(
                f"{a['acodec']} (.{a['ext']}){size_mb}",
                {'url': a['url'], 'headers': a.get('http_headers', {})}
            )

        if not audios:
            self.combo_audio.addItem("Audio bawaan video stream (jika ada)", None)

        self.btn_dl_video.setEnabled(True)
        self.btn_dl_audio.setEnabled(True)

    def on_error(self, err):
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("🔍 Analyze URL")
        self.lbl_info.setText("Gagal mengambil info video.")
        QMessageBox.critical(self, "Extraction Error", err)

    def process_selection(self, audio_only):
        self.convert_audio_only = audio_only
        self.selected_audio_format = self.combo_audio_format.currentText().lower()
        
        if audio_only:
            audio_data = self.combo_audio.currentData()
            if isinstance(audio_data, dict):
                self.selected_audio_url = audio_data.get('url')
                self.selected_audio_headers = audio_data.get('headers', {})
            else:
                self.selected_audio_url = audio_data
                self.selected_audio_headers = {}
            self.selected_video_url = None
            self.selected_video_headers = {}
            
            if not self.selected_audio_url:
                if self.table_formats.rowCount() > 0:
                    data = self.table_formats.item(0, 0).data(Qt.UserRole)
                    if isinstance(data, dict):
                        self.selected_audio_url = data.get('url')
                        self.selected_audio_headers = data.get('headers', {})
                    else:
                        self.selected_audio_url = data
            if not self.selected_audio_url:
                QMessageBox.warning(self, "Peringatan", "Tidak menemukan audio track yang valid!")
                return
        else:
            selected_items = self.table_formats.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Peringatan", "Silakan pilih resolusi video pada tabel terlebih dahulu!")
                return
            
            row = self.table_formats.row(selected_items[0])
            video_data = self.table_formats.item(row, 0).data(Qt.UserRole)
            if isinstance(video_data, dict):
                self.selected_video_url = video_data.get('url')
                self.selected_video_headers = video_data.get('headers', {})
            else:
                self.selected_video_url = video_data
                self.selected_video_headers = {}

            audio_data = self.combo_audio.currentData()
            if isinstance(audio_data, dict):
                self.selected_audio_url = audio_data.get('url')
                self.selected_audio_headers = audio_data.get('headers', {})
            else:
                self.selected_audio_url = audio_data
                self.selected_audio_headers = {}

            # [FIX] Validasi URL video tidak boleh kosong sebelum lanjut
            if not self.selected_video_url:
                QMessageBox.warning(
                    self, "URL Tidak Valid",
                    "Format yang dipilih tidak punya URL direct (mungkin HLS/DASH).\n"
                    "Coba pilih resolusi lain, atau gunakan Download Audio Only."
                )
                return

        self.accept()