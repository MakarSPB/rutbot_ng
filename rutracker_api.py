import os
import cloudscraper
import re
import logging
import time
from bs4 import BeautifulSoup

# Чтение ключевых слов и исключающих слов из .env
RUTRACKER_KEYWORDS = [k.strip().lower() for k in os.getenv('RUTRACKER_KEYWORDS', '').split(',') if k.strip()]
RUTRACKER_EXCLUDE = [k.strip().lower() for k in os.getenv('RUTRACKER_EXCLUDE', '').split(',') if k.strip()]

class RutrackerAPI:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = self.create_scraper_with_proxy()
        self.base_url = "https://rutracker.org/forum/"
        self.logged_in = False
        self.proxies = self.setup_proxies()

    def create_scraper_with_proxy(self):
        scraper = cloudscraper.create_scraper(
            browser={'custom': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        if os.getenv('USE_PROXY', 'false').lower() == 'true':
            http_proxy = os.getenv('HTTP_PROXY')
            https_proxy = os.getenv('HTTPS_PROXY')
            proxies = {}
            if http_proxy:
                proxies['http'] = http_proxy
            if https_proxy:
                proxies['https'] = https_proxy
            scraper.proxies = proxies
        return scraper

    def request_with_retries(self, method, url, retries=3, delay=1, timeout=3, **kwargs):
        """
        Универсальный метод для HTTP-запросов с повторными попытками и таймаутом.
        """
        for attempt in range(1, retries + 1):
            try:
                response = self.session.request(method, url, timeout=timeout, **kwargs)
                response.raise_for_status()
                return response
            except Exception as e:
                logging.warning(f"Попытка {attempt} не удалась для {url}: {e}")
                if attempt == retries:
                    logging.error(f"Все попытки исчерпаны для {url}")
                    return None
                time.sleep(delay)

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
            test_scraper = cloudscraper.create_scraper(
                browser={'custom': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            test_scraper.proxies = {"http": proxy_url, "https": proxy_url}
            response = test_scraper.get("http://httpbin.org/ip", timeout=5)
            return response is not None and response.status_code == 200
        except Exception as e:
            logging.error(f"Ошибка при проверке прокси {proxy_url}: {e}")
            return False

    def make_request(self, method, endpoint, **kwargs):
        url = self.base_url + endpoint
        return self.request_with_retries(method, url, **kwargs)

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
            response = self.request_with_retries('POST', login_url, data=payload, headers=headers)
            if response:
                self.logged_in = "logged-in" in response.text or "logout" in response.text
                return self.logged_in
            return False
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
            response = self.request_with_retries('GET', search_url, params=params, headers=headers)
            if not response:
                return {"success": False, "message": "Ошибка при поиске: не удалось получить ответ"}
            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            logging.debug(f"HTML страницы поиска: {response.text[:1000]}...")

            for row in soup.select("tr.hl-tr"):
                try:
                    title_element = row.select_one("a.tLink")
                    if not title_element:
                        continue

                    title = title_element.text.strip()
                    # Фильтрация по ключевым словам
                    if RUTRACKER_KEYWORDS and not any(keyword in title.lower() for keyword in RUTRACKER_KEYWORDS):
                        continue
                    # Исключение по словам
                    if RUTRACKER_EXCLUDE and any(exclude in title.lower() for exclude in RUTRACKER_EXCLUDE):
                        continue

                    topic_id = re.search(r"t=(\d+)", title_element["href"]).group(1)
                    size = row.select_one("td.tor-size").text.strip() if row.select_one("td.tor-size") else "Неизвестно"
                    
                    # Улучшенное извлечение сидов
                    seeders_element = row.select_one("td.seeders")
                    
                    if seeders_element:
                        seeders_bold = seeders_element.select_one("b")
                        if seeders_bold:
                            seeders_text = seeders_bold.text.strip()
                        else:
                            seeders_text = seeders_element.text.strip()
                        seeders_clean = re.sub(r'\D', '', seeders_text)
                        seeders_count = int(seeders_clean) if seeders_clean else 0
                    else:
                        cells = row.select("td")
                        if len(cells) >= 8:
                            for i in [6, 7, 8]:
                                if i < len(cells):
                                    cell_text = cells[i].text.strip()
                                    if re.match(r'^\d+$', cell_text):
                                        seeders_text = cell_text
                                        seeders_count = int(cell_text)
                                        break
                            else:
                                seeders_text = "0"
                                seeders_count = 0
                        else:
                            seeders_text = "0"
                            seeders_count = 0
                    
                    logging.debug(f"Тема: {title}, Сиды текст: '{seeders_text}', очищено: {seeders_count}")

                    results.append({
                        "title": title,
                        "topic_id": topic_id,
                        "size": size,
                        "seeders": str(seeders_count),
                        "seeders_count": seeders_count,
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
            response = self.request_with_retries('GET', download_url, headers=headers, stream=True)
            if response and response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            logging.error(f"Ошибка при скачивании торрента: {e}")
            return None

    def download_torrent_by_url(self, page_url):
        if not self.login():
            return None

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        try:
            response = self.request_with_retries('GET', page_url, headers=headers)
            if not response or response.status_code != 200:
                logging.error(f"Ошибка при загрузке страницы: {response.status_code if response else 'нет ответа'}")
                return None

            soup = BeautifulSoup(response.text, "html.parser")
            download_link_element = soup.select_one("a[href*='dl.php?t=']")
            if not download_link_element:
                logging.error("Ссылка на загрузку торрента не найдена")
                return None

            download_url = self.base_url + download_link_element["href"]
            torrent_response = self.request_with_retries('GET', download_url, headers=headers, stream=True)
            if torrent_response and torrent_response.status_code == 200:
                return torrent_response.content
            else:
                logging.error(f"Ошибка при загрузке торрента: {torrent_response.status_code if torrent_response else 'нет ответа'}")
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

    def get_title_from_url(self, url):
        try:
            response = self.request_with_retries('GET', url)
            if response and response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                title_tag = soup.find('title')
                if title_tag:
                    return title_tag.text
            return None
        except Exception as e:
            logging.error(f"Ошибка при получении заголовка страницы: {e}")
            return None