import os
import qbittorrentapi
from io import BytesIO

# Удаляем переменные окружения прокси до создания клиента
for var in ["HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(var, None)

class QBittorrentClient:
    def __init__(self):
        self.host = os.getenv('QBITTORRENT_URL')
        self.username = os.getenv('QBITTORRENT_USERNAME')
        self.password = os.getenv('QBITTORRENT_PASSWORD')
        self.save_path = os.getenv('QBITTORRENT_SAVE_PATH')
        self.category = os.getenv('QBITTORRENT_CATEGORY')
        self.client = qbittorrentapi.Client(
            host=self.host,
            username=self.username,
            password=self.password,
            REQUESTS_ARGS={"proxies": {}, "timeout": 10}
        )
        try:
            self.client.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            raise Exception(f"Не удалось авторизоваться в qBittorrent Web UI: {e}")

    def add_torrent(self, torrent_bytes, filename):
        torrent_file = BytesIO(torrent_bytes)
        torrent_file.name = filename
        self.client.torrents_add(
            torrent_files=torrent_file,
            save_path=self.save_path,
            category=self.category
        )

    def check_connection(self):
        try:
            self.client.app_version()
            return True
        except Exception:
            return False