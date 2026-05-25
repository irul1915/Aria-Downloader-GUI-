import xmlrpc.client
import logging
import os
import threading

logger = logging.getLogger("AriaDownloader")

class Aria2RPC:
    def __init__(self, url="http://localhost:6800/rpc", download_dir="C:\\Users\\Administrator\\Downloads\\AriaDownloads"):
        self.url = url
        self.download_dir = download_dir
        self.secret_token = "token:ariasecret123"
        self.lock = threading.Lock()
        self._local = threading.local()

    def _get_server(self):
        if not hasattr(self._local, 'server'):
            self._local.server = xmlrpc.client.ServerProxy(self.url)
        return self._local.server

    def save_session(self):
        with self.lock:
            try:
                self._get_server().aria2.saveSession(self.secret_token)
                logger.info("Session file berhasil disimpan.")
                return True
            except Exception as e:
                logger.error(f"RPC Error saat saveSession: {e}")
                return False

    def add_uri(self, url, subfolder=None):
        options = {
            'split': '16',
            'max-connection-per-server': '16',
            'min-split-size': '1M'
        }
        if subfolder:
            options['dir'] = os.path.join(self.download_dir, subfolder)
        else:
            options['dir'] = self.download_dir

        gid = None
        with self.lock:
            try:
                gid = self._get_server().aria2.addUri(self.secret_token, [url], options)
                logger.info(f"Berhasil menambahkan unduhan dengan GID: {gid}")
            except Exception as e:
                logger.error(f"RPC Error saat menambahkan download: {e}")
                return None
        
        if gid:
            self.save_session()
        return gid

    def add_torrent(self, torrent_path, subfolder=None):
        options = {}
        if subfolder:
            options['dir'] = os.path.join(self.download_dir, subfolder)
        else:
            options['dir'] = self.download_dir

        gid = None
        try:
            with open(torrent_path, "rb") as f:
                torrent_data = xmlrpc.client.Binary(f.read())
            
            with self.lock:
                gid = self._get_server().aria2.addTorrent(self.secret_token, torrent_data, [], options)
                logger.info(f"Berhasil menambahkan torrent dengan GID: {gid}")
        except Exception as e:
            logger.error(f"RPC Error saat menambahkan torrent: {e}")
            return None
        
        if gid:
            self.save_session()
        return gid

    def tell_status(self, gid):
        try:
            return self._get_server().aria2.tellStatus(self.secret_token, gid)
        except xmlrpc.client.Fault as e:
            if "is not found" in str(e):
                return {
                    "status": "removed",
                    "errorMessage": str(e),
                    "gid": gid,
                    "completedLength": "0",
                    "totalLength": "0",
                    "downloadSpeed": "0"
                }
            logger.error(f"RPC Error tellStatus untuk GID {gid}: {e}")
            return None
        except Exception as e:
            logger.error(f"RPC Error tellStatus untuk GID {gid}: {e}")
            return None

    def get_download_status(self, gid):
        """Mengembalikan status string (active, waiting, paused, complete, error, removed, unknown) atau None."""
        try:
            res = self.tell_status(gid)
            if res is None:
                return None
            return res.get('status', 'unknown')
        except Exception:
            return None

    def get_download_files(self, gid):
        """Mengambil list path file absolut dari GID."""
        try:
            res = self._get_server().aria2.tellStatus(self.secret_token, gid)
            files = res.get('files', [])
            paths = []
            for f in files:
                path = f.get('path', '')
                if path:
                    paths.append(path)
            return paths
        except Exception as e:
            logger.warning(f"Gagal mengambil file list untuk GID {gid}: {e}")
            return []

    def add_uri_extended(self, uris, options):
        gid = None
        with self.lock:
            try:
                gid = self._get_server().aria2.addUri(self.secret_token, uris, options)
            except Exception as e:
                logger.error(f"RPC Error addUri khusus: {e}")
        
        if gid:
            self.save_session()
        return gid

    def get_all_downloads(self):
        try:
            server = self._get_server()
            active = server.aria2.tellActive(self.secret_token)
            waiting = server.aria2.tellWaiting(self.secret_token, 0, 1000)
            stopped = server.aria2.tellStopped(self.secret_token, 0, 1000)
            
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
            return []

    def pause(self, gid):
        result = False
        with self.lock:
            try: 
                result = self._get_server().aria2.pause(self.secret_token, gid)
            except Exception: 
                pass
        
        if result:
            self.save_session()
        return result

    def resume(self, gid):
        result = False
        with self.lock:
            try: 
                result = self._get_server().aria2.unpause(self.secret_token, gid)
            except Exception: 
                pass
        
        if result:
            self.save_session()
        return result

    def remove(self, gid):
        """Hapus dari active/waiting list (forceRemove)."""
        result = False
        with self.lock:
            try: 
                result = self._get_server().aria2.forceRemove(self.secret_token, gid)
            except Exception: 
                pass
        
        if result:
            self.save_session()
        return result

    def remove_stopped(self, gid):
        """Hapus dari stopped list (complete/error/removed) menggunakan removeDownloadResult."""
        with self.lock:
            try:
                result = self._get_server().aria2.removeDownloadResult(self.secret_token, gid)
                logger.info(f"removeDownloadResult sukses untuk GID {gid}")
                return result
            except Exception as e:
                logger.error(f"RPC Error removeDownloadResult untuk GID {gid}: {e}")
                return False