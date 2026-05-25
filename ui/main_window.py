import os
import re
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QTableWidget, QTableWidgetItem, QPushButton, 
                               QHeaderView, QAbstractItemView, QMessageBox, QApplication)
from PySide6.QtCore import Qt, QEvent, QTimer

from ui.media_dialog import MediaDownloaderDialog
from ui.add_dialog import AddDownloadDialog
from ui.workers import MediaPipelineWorker, RPCPollerWorker, AsyncActionWorker, DeleteDownloadWorker
from utils.logger import log

class MainWindow(QMainWindow):
    def __init__(self, rpc, db):
        super().__init__()
        self.rpc = rpc
        self.db = db
        
        self.setWindowTitle("Aria2 Multi-Thread Downloader Pro")
        self.resize(950, 550) 
        
        self._active_media_workers = set()
        self._active_action_workers = set()
        
        self._clipboard_history = set()
        self._last_clipboard_text = ""
        self._clipboard_timer = QTimer(self)
        self._clipboard_timer.timeout.connect(self._check_clipboard)
        self._clipboard_timer.start(1000)
        
        self.setup_ui()
        
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
        
        self.table.viewport().installEventFilter(self)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        main_layout.addWidget(self.table)

    def eventFilter(self, source, event):
        if source == self.table.viewport() and event.type() == QEvent.MouseButtonPress:
            item = self.table.itemAt(event.pos())
            if not item:
                self.table.clearSelection()
        return super().eventFilter(source, event)

    def mousePressEvent(self, event):
        self.table.clearSelection()
        super().mousePressEvent(event)

    def _check_clipboard(self):
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text().strip()
            
            if not text or text == self._last_clipboard_text:
                return
            self._last_clipboard_text = text
            
            link_type, url = self._classify_link(text)
            if not link_type:
                return
            
            if url in self._clipboard_history:
                return
            self._clipboard_history.add(url)
            
            self.raise_()
            self.activateWindow()
            
            if link_type == 'youtube':
                log.info(f"Clipboard: Link YouTube terdeteksi -> {url}")
                self._show_media_downloader(prefill_url=url)
            else:
                log.info(f"Clipboard: Link {link_type} terdeteksi -> {url}")
                self._show_add_dialog(prefill_url=url)
                
        except Exception as e:
            log.error(f"Error clipboard monitor: {e}")

    def _classify_link(self, text):
        text = text.strip()
        if not text:
            return None, None
        
        if text.startswith('magnet:?xt=urn:btih:'):
            return 'magnet', text
        
        yt_pattern = re.compile(
            r'^(https?://)?(www\.)?(youtube\.com|youtu\.be|youtube-nocookie\.com)/.+',
            re.IGNORECASE
        )
        if yt_pattern.match(text):
            return 'youtube', text
        
        if re.search(r'\.torrent(?:\?.*)?$', text, re.IGNORECASE):
            return 'torrent', text
        
        if text.startswith('http://') or text.startswith('https://'):
            return 'direct', text
        
        return None, None

    def _show_add_dialog(self, prefill_url=None):
        dialog = AddDownloadDialog(self, prefill_url=prefill_url)
        if dialog.exec():
            url, torrent_path, subfolder = dialog.get_data()
            gid = None
            if torrent_path:
                gid = self.rpc.add_torrent(torrent_path, subfolder)
            elif url:
                gid = self.rpc.add_uri(url, subfolder)
                
            if gid:
                save_path = os.path.join(self.rpc.download_dir, subfolder) if subfolder else self.rpc.download_dir
                self.db.save_download(gid, torrent_path or url, url, save_path)

    def show_add_dialog(self):
        self._show_add_dialog()

    def update_table(self, downloads):
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

        if row_to_select != -1:
            self.table.selectRow(row_to_select)

    def get_selected_gid(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges: return None
        row = selected_ranges[0].topRow()
        item = self.table.item(row, 0)
        return item.text() if item else None

    def _get_selected_status(self):
        """Mengambil status uppercase dari row yang dipilih (kolom ke-5)."""
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            return None
        row = selected_ranges[0].topRow()
        item = self.table.item(row, 5)
        return item.text() if item else None

    def _run_async_action(self, action, gid):
        if not gid:
            return
        
        worker = AsyncActionWorker(self.rpc, action, gid)
        worker.finished_signal.connect(lambda success, msg, w=worker: self._on_action_finished(success, msg, w))
        self._active_action_workers.add(worker)
        worker.start()

    def _on_action_finished(self, success, message, worker):
        if worker in self._active_action_workers:
            self._active_action_workers.remove(worker)
        worker.deleteLater()
        
        if not success:
            self.statusBar().showMessage(f"Gagal: {message}", 5000)
            log.warning(message)
        else:
            self.statusBar().showMessage(message, 3000)
            log.info(message)

    def pause_download(self):
        gid = self.get_selected_gid()
        if gid:
            self._run_async_action('pause', gid)

    def resume_download(self):
        gid = self.get_selected_gid()
        if gid:
            self._run_async_action('resume', gid)

    def delete_download(self):
        gid = self.get_selected_gid()
        if not gid:
            return
        
        status = self._get_selected_status()
        
        # Jika COMPLETE: hanya hapus histori, file tetap di disk
        if status == "COMPLETE":
            reply = QMessageBox.question(
                self, 
                "Hapus dari Histori",
                f"Hapus download GID {gid} dari daftar histori?\n\nFile yang sudah selesai diunduh akan tetap tersimpan di disk.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            
            worker = DeleteDownloadWorker(self.rpc, gid, delete_files=False)
            worker.finished_signal.connect(lambda success, msg, w=worker: self._on_action_finished(success, msg, w))
            self._active_action_workers.add(worker)
            worker.start()
        
        # Jika belum complete: hapus antrian + hapus file fisik
        else:
            reply = QMessageBox.question(
                self, 
                "Hapus Download & File",
                f"Anda yakin ingin membatalkan dan menghapus download GID {gid} beserta file-nya dari disk?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            
            worker = DeleteDownloadWorker(self.rpc, gid, delete_files=True)
            worker.finished_signal.connect(lambda success, msg, w=worker: self._on_action_finished(success, msg, w))
            self._active_action_workers.add(worker)
            worker.start()

    def _show_media_downloader(self, prefill_url=None):
        dialog = MediaDownloaderDialog(self, prefill_url=prefill_url)
        if not dialog.exec():
            return
            
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
        
        worker.status_signal.connect(lambda msg: self.statusBar().showMessage(msg))
        worker.finished_signal.connect(lambda s, m, w=worker: self.on_media_pipeline_finished(s, m, w))
        
        self._active_media_workers.add(worker)
        worker.start()
        self.statusBar().showMessage("Memulai koneksi Media Downloader...")

    def open_media_downloader(self):
        self._show_media_downloader()

    def on_media_pipeline_finished(self, success, message, worker):
        if worker in self._active_media_workers:
            self._active_media_workers.remove(worker)
        worker.deleteLater()

        if success:
            QMessageBox.information(self, "Proses Sukses", message)
        else:
            # Jika user sengaja menghapus download dari antrian, jangan tampilkan sebagai error critical
            if "dibatalkan karena dihapus oleh user" in message.lower():
                QMessageBox.information(self, "Proses Dibatalkan", message)
            else:
                QMessageBox.critical(self, "Proses Gagal", f"Terjadi Kesalahan:\n{message}")
        self.statusBar().clearMessage()

    def closeEvent(self, event):
        self._clipboard_timer.stop()
        
        try:
            self.rpc.save_session()
            log.info("Session aria2c disimpan via closeEvent.")
        except Exception as e:
            log.warning(f"Gagal menyimpan session di closeEvent: {e}")
        
        self.worker.stop()
        
        for action_worker in self._active_action_workers:
            action_worker.wait(1000)
        self._active_action_workers.clear()
        
        for media_worker in self._active_media_workers:
            media_worker.stop()
            media_worker.wait(2000)
            
        event.accept()