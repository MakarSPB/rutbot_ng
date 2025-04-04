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
                
                # Более тщательная проверка элемента с сидами
                seeders_element = row.select_one("td.seeders")
                
                # Добавляем логирование для отладки
                if seeders_element:
                    logging.debug(f"Текст элемента seeders: '{seeders_element.text}'")
                    
                    # Проверяем наличие вложенных элементов
                    seeders_b = seeders_element.select_one("b")
                    if seeders_b:
                        seeders = seeders_b.text.strip()
                    else:
                        seeders = seeders_element.text.strip()
                else:
                    seeders = "0"
                
                # Удаляем все нецифровые символы для надежного преобразования
                seeders_clean = re.sub(r'[^\d]', '', seeders)
                seeders_count = int(seeders_clean) if seeders_clean else 0
                
                logging.debug(f"Извлеченное значение сидов: {seeders}, преобразовано в: {seeders_count}")

                results.append({
                    "title": title,
                    "topic_id": topic_id,
                    "size": size,
                    "seeders": seeders,
                    "seeders_count": seeders_count,
                    "download_link": f"{self.base_url}dl.php?t={topic_id}"
                })
            except Exception as e:
                logging.error(f"Ошибка при парсинге: {e}")

        return {"success": True, "results": results}
    except Exception as e:
        logging.error(f"Ошибка при поиске: {e}")
        return {"success": False, "message": f"Ошибка при поиске: {e}"}
