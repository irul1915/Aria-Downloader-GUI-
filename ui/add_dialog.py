from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QFileDialog

class AddDownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tambah Unduhan Baru / Torrent")
        self.setMinimumWidth(550)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        layout.addWidget(QLabel("<b>Opsi 1: Masukkan URL File / Magnet Link Torrent:</b>"))
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("https://... atau magnet:?xt=urn:btih:...")
        layout.addWidget(self.url_input)

        label_or = QLabel("— ATAU —")
        label_or.setStyleSheet("color: #777777;")
        layout.addWidget(label_or)

        layout.addWidget(QLabel("<b>Opsi 2: Pilih File .torrent Lokal:</b>"))
        torrent_layout = QHBoxLayout()
        self.torrent_path_input = QLineEdit(self)
        self.torrent_path_input.setPlaceholderText("Belum ada file torrent yang dipilih...")
        self.torrent_path_input.setReadOnly(True)
        
        self.btn_browse = QPushButton("📁 Cari File", self)
        self.btn_browse.clicked.connect(self.browse_torrent_file)
        
        torrent_layout.addWidget(self.torrent_path_input)
        torrent_layout.addWidget(self.btn_browse)
        layout.addLayout(torrent_layout)

        layout.addWidget(QLabel("Nama Subfolder Tujuan (Opsional):"))
        self.folder_input = QLineEdit(self)
        self.folder_input.setPlaceholderText("Kosongkan untuk mengunduh ke direktori utama")
        layout.addWidget(self.folder_input)

        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Batal", self)
        self.btn_ok = QPushButton("Mulai Download", self)
        self.btn_ok.setDefault(True)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)
        
        self.url_input.textChanged.connect(self.clear_torrent_path)

    def browse_torrent_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih File Torrent", "", "Torrent Files (*.torrent)")
        if file_path:
            self.torrent_path_input.setText(file_path)
            self.url_input.clear()

    def clear_torrent_path(self):
        if self.url_input.text().strip():
            self.torrent_path_input.clear()

    def get_data(self):
        return (self.url_input.text().strip(), self.torrent_path_input.text().strip(), self.folder_input.text().strip())