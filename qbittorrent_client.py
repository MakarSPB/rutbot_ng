import os
import requests

class QBittorrentClient:
    def __init__(self):
        self.url = os.getenv('QBITTORRENT_URL')
        self.username = os.getenv('QBITTORRENT_USERNAME')
        self.password = os.getenv('QBITTORRENT_PASSWORD')
        self.save_path = os.getenv('QBITTORRENT_SAVE_PATH')
        self.category = os.getenv('QBITTORRENT_CATEGORY')
        self.session = requests.Session()
        self._login()

    def _login(self):
        login_url = f"{self.url}/api/v2/auth/login"
        data = {
            'username': self.username,
            'password': self.password
        }
        resp = self.session.post(login_url, data=data)
        if resp.text != 'Ok.':
            raise Exception("Не удалось авторизоваться в qBittorrent Web UI")

    def add_torrent(self, torrent_bytes, filename):
        add_url = f"{self.url}/api/v2/torrents/add"
        files = {'torrents': (filename, torrent_bytes)}
        data = {}
        if self.save_path:
            data['savepath'] = self.save_path
        if self.category:
            data['category'] = self.category
        resp = self.session.post(add_url, data=data, files=files)
        if resp.status_code != 200:
            raise Exception(f"Ошибка добавления торрента: {resp.text}")