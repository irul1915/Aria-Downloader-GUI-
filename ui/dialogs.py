from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QFileDialog, QFormLayout, QDialogButtonBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

class AddDownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Download")
        
        # Auto width berdasarkan rasio screen (minimal 450px, tidak lebih lebar dari 600px)
        screen_width = QGuiApplication.primaryScreen().availableGeometry().width()
        ideal_width = min(600, max(450, int(screen_width * 0.3)))
        self.setMinimumWidth(ideal_width)
        
        main_layout = QVBoxLayout(self)
        
        # Menggunakan QFormLayout agar label dan input sejajar sempurna
        form_layout = QFormLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/file.zip")
        self.url_input.setClearButtonEnabled(True) # Fitur modern clear URL
        
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_btn = QPushButton("Browse...")
        self.path_btn.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.path_btn)
        
        self.conn_input = QLineEdit("16")
        
        form_layout.addRow("Download URL:", self.url_input)
        form_layout.addRow("Save To:", path_layout)
        form_layout.addRow("Max Connections:", self.conn_input)
        
        main_layout.addLayout(form_layout)
        main_layout.addSpacing(10)

        # Standard Button Box agar tombol Ok/Cancel mengikuti standar OS (Kanan di Win, Kiri di Mac)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Ok).setText("Download Now")
        
        main_layout.addWidget(self.button_box)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Directory")
        if folder:
            self.path_input.setText(folder)
            
    def get_data(self):
        return {
            "url": self.url_input.text().strip(), # Pastikan tidak ada spasi sisa
            "path": self.path_input.text().strip(),
            "split": self.conn_input.text().strip()
        }