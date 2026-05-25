import yt_dlp
from utils.logger import log

class YTDLPExtractor:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }

    def analyze_url(self, url):
        """ Mengambil metadata media tanpa mendownload filenya """
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:
                    main_info = info['entries'][0] if info['entries'] else info
                    title = f"[Playlist] {info.get('title', 'Unknown')}"
                else:
                    main_info = info
                    title = info.get('title', 'Unknown Title')

                result = {
                    'title': title,
                    'thumbnail': main_info.get('thumbnail', ''),
                    'uploader': main_info.get('uploader', 'Unknown Channel'),
                    'formats': []
                }

                for f in main_info.get('formats', []):
                    # [FIX] Skip format tanpa direct URL atau HLS/DASH manifest
                    # yang tidak bisa diunduh langsung oleh Aria2
                    if not f.get('url'):
                        continue
                    protocol = f.get('protocol', '')
                    if protocol in ('m3u8', 'm3u8_native', 'http_dash_segments', 'f4m', 'ism'):
                        continue

                    vcodec = f.get('vcodec', 'none')
                    acodec = f.get('acodec', 'none')
                    
                    if vcodec != 'none' or acodec != 'none':
                        filesize = f.get('filesize') or f.get('filesize_approx') or 0
                        resolution = f.get('resolution')
                        
                        if not resolution or resolution == 'multiple':
                            if vcodec == 'none':
                                resolution = 'audio only'
                            else:
                                resolution = f"{f.get('height', 'unknown')}p"

                        result['formats'].append({
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext', 'mp4'),
                            'resolution': resolution,
                            'filesize': filesize,
                            'vcodec': vcodec,
                            'acodec': acodec,
                            'fps': f.get('fps', '-'),
                            'tbr': f.get('tbr', '-'),
                            'url': f.get('url'),
                            # [FIX] Sertakan HTTP headers agar Aria2 bisa akses stream URL
                            'http_headers': f.get('http_headers', {})
                        })
                        
                return result
        except Exception as e:
            log.error(f"YT-DLP Extract Error: {e}")
            raise Exception(f"Gagal mengekstrak metadata: {str(e)}")