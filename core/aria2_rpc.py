import xmlrpc.client
import logging
import os
import threading  # Tambahkan modul untuk penanganan thread lock

logger = logging.getLogger("AriaDownloader")

class Aria2RPC:
    def __init__(self, url="http://localhost:6800/rpc", download_dir="C:\\Users\\Administrator\\Downloads\\AriaDownloads"):
        self.server = xmlrpc.client.ServerProxy(url)
        self.download_dir = download_dir
        self.secret_token = "token:ariasecret123" 
        self.lock = threading.Lock() # Lock Mutex untuk mencegah tabrakan koneksi antar thread

    def add_uri(self, url, subfolder=None):
        uris = [url]
        
        # Opsi kecepatan (Hanya masukkan parameter per-download yang diizinkan RPC)
        options = {
            'split': '16',
            'max-connection-per-server': '16',
            'min-split-size': '1M'
        }
        
        if subfolder:
            options['dir'] = os.path.join(self.download_dir, subfolder)
        else:
            options['dir'] = self.download_dir

        with self.lock:
            try:
                gid = self.server.aria2.addUri(self.secret_token, uris, options)
                logger.info(f"Berhasil menambahkan unduhan dengan GID: {gid}")
                return gid
            except Exception as e:
                logger.error(f"RPC Error saat menambahkan download: {e}")
                return None

    def add_torrent(self, torrent_path, subfolder=None):
        options = {}
        if subfolder:
            options['dir'] = os.path.join(self.download_dir, subfolder)
        else:
            options['dir'] = self.download_dir

        try:
            with open(torrent_path, "rb") as f:
                torrent_data = xmlrpc.client.Binary(f.read())
            
            with self.lock:
                gid = self.server.aria2.addTorrent(self.secret_token, torrent_data, [], options)
                logger.info(f"Berhasil menambahkan torrent dengan GID: {gid}")
                return gid
        except Exception as e:
            logger.error(f"RPC Error saat menambahkan torrent: {e}")
            return None

    def tell_status(self, gid):
        """ Wrapper thread-safe baru untuk digunakan oleh MediaPipelineWorker """
        with self.lock:
            try:
                return self.server.aria2.tellStatus(self.secret_token, gid)
            except Exception as e:
                logger.error(f"RPC Error tellStatus untuk GID {gid}: {e}")
                raise e

    def add_uri_extended(self, uris, options):
        """ Wrapper thread-safe baru untuk kustom URI dari MediaPipelineWorker """
        with self.lock:
            try:
                return self.server.aria2.addUri(self.secret_token, uris, options)
            except Exception as e:
                logger.error(f"RPC Error addUri khusus: {e}")
                return None

    def get_all_downloads(self):
        with self.lock:
            try:
                active = self.server.aria2.tellActive(self.secret_token)
                waiting = self.server.aria2.tellWaiting(self.secret_token, 0, 1000)
                stopped = self.server.aria2.tellStopped(self.secret_token, 0, 1000)
                
                raw_downloads = active + waiting + stopped
                formatted_downloads = []

                for dl in raw_downloads:
                    gid = dl.get('gid', '-')
                    name = "Unknown"
                    files = dl.get('files', [])
                    if files:
                        path = files[0].get('path', '')
                        if path:
                            name = os.path.basename(path)
                        else:
                            bt = dl.get('bittorrent', {})
                            if bt and 'info' in bt and 'name' in bt['info']:
                                name = bt['info']['name']
                            elif files[0].get('uris'):
                                name = os.path.basename(files[0]['uris'][0].get('uri', ''))
                    
                    if not name or name == "Unknown":
                        name = f"Task_{gid}"

                    completed_bytes = int(dl.get('completedLength', 0))
                    total_bytes = int(dl.get('totalLength', 0))
                    speed_bytes = int(dl.get('downloadSpeed', 0))

                    total_length_mb = f"{total_bytes / (1024 * 1024):.2f} MB" if total_bytes > 0 else "0.00 MB"
                    
                    progress = "0%"
                    if total_bytes > 0:
                        progress = f"{(completed_bytes / total_bytes) * 100:.1f}%"
                    if dl.get('status') == 'complete':
                        progress = "100%"

                    if speed_bytes >= 1024 * 1024:
                        download_speed = f"{speed_bytes / (1024 * 1024):.2f} MB/s"
                    else:
                        download_speed = f"{speed_bytes / 1024:.1f} KB/s"

                    formatted_downloads.append({
                        'gid': gid,
                        'name': name,
                        'total_length': total_length_mb,
                        'progress': progress,
                        'download_speed': download_speed,
                        'status': dl.get('status', 'unknown')
                    })

                return formatted_downloads
            except Exception as e:
                logger.error(f"Error di get_all_downloads: {e}")
                # Kembalikan None alih-alih list kosong jika terjadi error rpc sesaat
                return None 

    def pause(self, gid):
        with self.lock:
            try: return self.server.aria2.pause(self.secret_token, gid)
            except Exception: return False

    def resume(self, gid):
        with self.lock:
            try: return self.server.aria2.unpause(self.secret_token, gid)
            except Exception: return False

    def remove(self, gid):
        with self.lock:
            try: return self.server.aria2.forceRemove(self.secret_token, gid)
            except Exception: return False