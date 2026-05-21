import os
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QTableWidget, QTableWidgetItem, QPushButton, 
                               QHeaderView, QAbstractItemView, QMessageBox)
from PySide6.QtCore import Qt, QEvent

from ui.media_dialog import MediaDownloaderDialog
from ui.add_dialog import AddDownloadDialog
from ui.workers import MediaPipelineWorker, RPCPollerWorker

class MainWindow(QMainWindow):
    def __init__(self, rpc, db):
        super().__init__()
        self.rpc = rpc
        self.db = db
        
        self.setWindowTitle("Aria2 Multi-Thread Downloader Pro")
        self.resize(950, 550) 
        
        # Set untuk menyimpan referensi agar thread tidak di-Garbage Collect saat berjalan
        self._active_media_workers = set()
        
        self.setup_ui()
        
        # Memulai thread background poller
        self.worker = RPCPollerWorker(self.rpc)
        self.worker.data_ready.connect(self.update_table)
        self.worker.start()

    def setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("➕ Tambah Download", self)
        self.btn_media = QPushButton("🎥 Media Downloader", self)
        self.btn_pause = QPushButton("⏸️ Pause", self)
        self.btn_resume = QPushButton("▶️ Lanjutkan", self)
        self.btn_delete = QPushButton("🗑️ Hapus", self)
        
        self.btn_add.clicked.connect(self.show_add_dialog)
        self.btn_media.clicked.connect(self.open_media_downloader)
        self.btn_pause.clicked.connect(self.pause_download)
        self.btn_resume.clicked.connect(self.resume_download)
        self.btn_delete.clicked.connect(self.delete_download)

        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_media)
        button_layout.addWidget(self.btn_pause)
        button_layout.addWidget(self.btn_resume)
        button_layout.addWidget(self.btn_delete)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["GID", "Nama File", "Ukuran", "Progress", "Kecepatan", "Status"])
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Menggunakan EventFilter Qt murni untuk mendeteksi klik ruang kosong di tabel
        self.table.viewport().installEventFilter(self)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        main_layout.addWidget(self.table)

    def eventFilter(self, source, event):
        """ Implementasi standar untuk unselect jika area kosong di viewport tabel di-klik """
        if source == self.table.viewport() and event.type() == QEvent.MouseButtonPress:
            item = self.table.itemAt(event.pos())
            if not item:
                self.table.clearSelection()
        return super().eventFilter(source, event)

    def mousePressEvent(self, event):
        """ Unselect jika klik area kosong di jendela (luar tabel) """
        self.table.clearSelection()
        super().mousePressEvent(event)

    def show_add_dialog(self):
        dialog = AddDownloadDialog(self)
        if dialog.exec():
            url, torrent_path, subfolder = dialog.get_data()
            gid = None
            if torrent_path:
                gid = self.rpc.add_torrent(torrent_path, subfolder)
            elif url:
                gid = self.rpc.add_uri(url, subfolder)
                
            # Log koneksi ke Database (Diperbaiki agar fitur db berfungsi)
            if gid:
                save_path = os.path.join(self.rpc.download_dir, subfolder) if subfolder else self.rpc.download_dir
                self.db.save_download(gid, torrent_path or url, url, save_path)

    def update_table(self, downloads):
        """ Mengupdate tabel dengan pengamanan Lock dan flicker-free """
        # Abaikan sinyal pengosongan jika Thread RPC sedang tertahan Lock Mutex
        if downloads is None:
            return

        selected_gid = self.get_selected_gid()
        self.table.setRowCount(0)
        
        row_to_select = -1

        for index, dl in enumerate(downloads):
            self.table.insertRow(index)
            
            gid = dl.get('gid', '-')
            self.table.setItem(index, 0, QTableWidgetItem(gid))
            self.table.setItem(index, 1, QTableWidgetItem(dl.get('name', '-')))
            self.table.setItem(index, 2, QTableWidgetItem(dl.get('total_length', '-')))
            self.table.setItem(index, 3, QTableWidgetItem(dl.get('progress', '-')))
            self.table.setItem(index, 4, QTableWidgetItem(dl.get('download_speed', '-')))
            self.table.setItem(index, 5, QTableWidgetItem(dl.get('status', '').upper()))
            
            if gid == selected_gid:
                row_to_select = index

        # Kembalikan seleksi jika masih ada di daftar
        if row_to_select != -1:
            self.table.selectRow(row_to_select)

    def get_selected_gid(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges: return None
        row = selected_ranges[0].topRow()
        item = self.table.item(row, 0)
        return item.text() if item else None

    def pause_download(self):
        if gid := self.get_selected_gid(): self.rpc.pause(gid)

    def resume_download(self):
        if gid := self.get_selected_gid(): self.rpc.resume(gid)

    def delete_download(self):
        if gid := self.get_selected_gid(): self.rpc.remove(gid)

    def open_media_downloader(self):
        dialog = MediaDownloaderDialog(self)
        if dialog.exec():
            save_dir = str(Path(self.rpc.download_dir) / "MediaOut")
            os.makedirs(save_dir, exist_ok=True)

            worker = MediaPipelineWorker(
                rpc=self.rpc,
                title=dialog.metadata['title'],
                video_url=dialog.selected_video_url,
                audio_url=dialog.selected_audio_url,
                video_headers=dialog.selected_video_headers,
                audio_headers=dialog.selected_audio_headers,
                save_dir=save_dir,
                convert_audio_only=dialog.convert_audio_only,
                audio_format=dialog.selected_audio_format
            )
            
            # Hubungkan sinyal ke fungsi dan sertakan referensi worker
            worker.status_signal.connect(lambda msg: self.statusBar().showMessage(msg))
            worker.finished_signal.connect(lambda s, m, w=worker: self.on_media_pipeline_finished(s, m, w))
            
            # Menjaga referensi worker agar tidak crash dihancurkan sistem (Garbage Collect)
            self._active_media_workers.add(worker)
            
            worker.start()
            self.statusBar().showMessage("Memulai koneksi Media Downloader...")

    def on_media_pipeline_finished(self, success, message, worker):
        # Bersihkan memori dan hapus referensi worker karena sudah selesai
        if worker in self._active_media_workers:
            self._active_media_workers.remove(worker)
        worker.deleteLater()

        if success:
            QMessageBox.information(self, "Proses Sukses", message)
        else:
            QMessageBox.critical(self, "Proses Gagal", f"Terjadi Kesalahan:\n{message}")
        self.statusBar().clearMessage()

    def closeEvent(self, event):
        """ Menghentikan semua aktivitas thread secara elegan saat aplikasi ditutup """
        self.worker.stop()
        
        # Kirim sinyal stop ke semua worker media yang sedang aktif
        for media_worker in self._active_media_workers:
            media_worker.stop()
            media_worker.wait(2000) # Batas waktu 2 detik sebelum kill
            
        event.accept()