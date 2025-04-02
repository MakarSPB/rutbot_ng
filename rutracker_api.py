import os
import requests
import re
import logging
from bs4 import BeautifulSoup

class RutrackerAPI:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.base_url = "https://rutracker.org/forum/"
        self.logged_in = False
        self.proxies = self.setup_proxies()

    def setup_proxies(self):
        try:
            if os.getenv('USE_PROXY', 'false').lower() == 'true':
                proxies = {
                    "http": os.getenv('HTTP_PROXY'),
                    "https": os.getenv('HTTPS_PROXY')
                }
                if not all(proxies.values()):
                    raise ValueError("Не настроены прокси-серверы")
                if not all(self.validate_proxy(proxy) for proxy in proxies.values()):
                    raise ValueError("Некорректные настройки прокси")
                return proxies
            else:
                return None
        except Exception as e:
            logging.error(f"Ошибка при настройке прокси: {e}")
            return None

    def validate_proxy(self, proxy_url):
        try:
            requests.get("http://httpbin.org/ip", proxies={"http": proxy_url}, timeout=5)
            return True
        except Exception as e:
            logging.error(f"Ошибка при проверке прокси {proxy_url}: {e}")
            return False

    def make_request(self, method, endpoint, **kwargs):
        url = self.base_url + endpoint
        return self.session.request(method, url, proxies=self.proxies, **kwargs)

    def login(self):
        if self.logged_in:
            return True

        login_url = self.base_url + "login.php"
        payload = {
            "login_username": self.username,
            "login_password": self.password,
            "login": "вход"
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = self.session.post(
                login_url, 
                data=payload, 
                headers=headers,
                proxies=self.proxies
            )

            self.logged_in = "logged-in" in response.text or "logout" in response.text
            return self.logged_in
        except Exception as e:
            logging.error(f"Ошибка при авторизации: {e}")
            return False

    def search_movie(self, movie_name):
        if not self.login():
            return {"success": False, "message": "Ошибка авторизации на RuTracker"}

        search_url = self.base_url + "tracker.php"
        params = {"nm": movie_name}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = self.session.get(
                search_url,
                params=params,
                headers=headers,
                proxies=self.proxies
            )

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            for row in soup.select("tr.hl-tr"):
                try:
                    title_element = row.select_one("a.tLink")
                    if not title_element:
                        continue

                    title = title_element.text.strip()

                    if not any(keyword in title.lower() for keyword in ["фантастика", "драма", "фэнтези", "ужасы", "мелодрама", "комедия", "боевик", "арт-хаус", "триллер"]):
                        continue

                    topic_id = re.search(r"t=(\d+)", title_element["href"]).group(1)

                    size_element = row.select_one("td.tor-size")
                    size = size_element.text.strip() if size_element else "Неизвестно"

                    seeders_element = row.select_one("td.seeders")
                    seeders = seeders_element.text.strip() if seeders_element else "0"

                    results.append({
                        "title": title,
                        "topic_id": topic_id,
                        "size": size,
                        "seeders": seeders,
                        "download_link": f"{self.base_url}dl.php?t={topic_id}"
                    })
                except Exception as e:
                    logging.error(f"Ошибка при парсинге: {e}")

            return {"success": True, "results": results}
        except Exception as e:
            logging.error(f"Ошибка при поиске: {e}")
            return {"success": False, "message": f"Ошибка при поиске: {e}"}

    def get_torrent(self, topic_id):
        if not self.login():
            return None

        download_url = f"{self.base_url}dl.php?t={topic_id}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = self.session.get(
                download_url, 
                headers=headers,
                proxies=self.proxies,
                stream=True
            )

            if response.status_code == 200:
                return response.content

            return None
        except Exception as e:
            logging.error(f"Ошибка при скачивании торрента: {e}")
            return None