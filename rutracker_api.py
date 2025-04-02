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
        if os.getenv('USE_PROXY', 'false').lower() == 'true':
            proxies = {
                "http": os.getenv('HTTP_PROXY'),
                "https": os.getenv('HTTPS_PROXY')
            }
            if not all(proxies.values()):
                logging.error("Не настроены прокси-серверы")
                return None
            if not all(self.validate_proxy(proxy) for proxy in proxies.values()):
                logging.error("Некорректные настройки прокси")
                return None
            return proxies
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
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        try:
            response = self.session.post(login_url, data=payload, headers=headers, proxies=self.proxies)
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
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        try:
            response = self.session.get(search_url, params=params, headers=headers, proxies=self.proxies)
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
                    size = row.select_one("td.tor-size").text.strip() if row.select_one("td.tor-size") else "Неизвестно"
                    seeders = row.select_one("td.seeders").text.strip() if row.select_one("td.seeders") else "0"

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
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        try:
            response = self.session.get(download_url, headers=headers, proxies=self.proxies, stream=True)
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            logging.error(f"Ошибка при скачивании торрента: {e}")
            return None

    def download_torrent_by_url(self, page_url, base_file, forbidden_words, forbidden_patterns):
        if not self.login():
            return None

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        try:
            response = self.session.get(page_url, headers=headers, proxies=self.proxies)
            if response.status_code != 200:
                logging.error(f"Ошибка при загрузке страницы: {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, "html.parser")
            download_link_element = soup.select_one("a[href*='dl.php?t=']")
            if not download_link_element:
                logging.error("Ссылка на загрузку торрента не найдена")
                return None

            # Извлечение названия
            title_element = soup.select_one("title")
            if not title_element:
                logging.error("Не удалось извлечь название страницы")
                return None
            title = title_element.text.split('/')[0].strip()

            download_url = self.base_url + download_link_element["href"]
            torrent_response = self.session.get(download_url, headers=headers, proxies=self.proxies, stream=True)
            if torrent_response.status_code == 200:
                # Логирование результата в BASE_FILE
                if not self.log_search_result(base_file, title, forbidden_words, forbidden_patterns):
                    logging.info("Файл уже есть на Plex. Торрент не будет загружен.")
                    return None
                return torrent_response.content
            else:
                logging.error(f"Ошибка при загрузке торрента: {torrent_response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Ошибка при загрузке торрента по ссылке: {e}")
            return None

    def is_query_already_searched(self, base_file, query):
        try:
            if not os.path.exists(base_file):
                return False
            with open(base_file, 'r') as file:
                return any(query.lower() in line.lower() for line in file)
        except Exception as e:
            logging.error(f"Ошибка при проверке запроса в base.csv: {e}")
            return False

    def log_search_result(self, base_file, title, forbidden_words, forbidden_patterns):
        try:
            extracted_title = re.split(r'\s*/\s*', title)[0]
            if any(word.lower() in extracted_title.lower() for word in forbidden_words) or \
               any(re.search(pattern, extracted_title, re.IGNORECASE) for pattern in forbidden_patterns):
                logging.info(f"Запрещенное слово найдено в заголовке: {extracted_title}")
                return False
            if self.is_title_already_logged(base_file, extracted_title):
                logging.info(f"Строка уже существует в base.csv: {extracted_title}")
                return False
            with open(base_file, 'a', encoding='utf-8') as file:
                file.write(f'"{extracted_title}"\n')
            return True
        except Exception as e:
            logging.error(f"Ошибка при логировании поискового запроса: {e}")
            return False

    def is_title_already_logged(self, base_file, title):
        try:
            if not os.path.exists(base_file):
                return False
            with open(base_file, 'r', encoding='utf-8') as file:
                return any(f'"{title}"' in line for line in file)
        except Exception as e:
            logging.error(f"Ошибка при проверке наличия записи в base.csv: {e}")
            return False


