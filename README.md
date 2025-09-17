# UBEBC rutbot
---
### Бот на Python для поиска и скачивания торрент-файлов с rutracker.org. Бот автоматизирует поиск контента, отправляет торрент-файлы в Telegram и сохраняет их в указанную директорию.
---
### Обновление: добавлена библиотека cloudscraper для обхода защиты Cloudflare.
---
## Основные возможности 
•	🔍 Поиск торрентов на RuTracker с гибкой фильтрацией\
•	📤 Отправка торрент-файлов в чат Telegram\
•	💾 Автоматическое сохранение торрентов на сервере\
•	📊 Ведение базы загруженных файлов с предотвращением дубликатов\
•	📏 Фильтрация результатов по размеру файла\
•	📶 Сортировка результатов по количеству сидов\
•	🔒 Система авторизации пользователей через whitelist\
•	🌐 Поддержка работы через прокси (опционально)\
## Установка
### Системные требования
sudo apt update\
sudo apt install python3 python3-pip\
pip install -r requirements.txt

### Настройка конфигурации
1.	Скопируйте пример конфигурации и настройте его:\
cp .env.example .env\
nano .env

2.	Создайте файл с разрешенными пользователями:\
nano whitelist.txt

Добавьте в файл ID пользователей Telegram (по одному на строку), которым разрешен доступ к боту. ID можно узнать у @getmyid_bot.

## Параметры конфигурации
### Основные настройки

TELEGRAM_TOKEN=                  # Токен бота от @BotFather\
RUTRACKER_USERNAME=              # Логин на RuTracker\
RUTRACKER_PASSWORD=              # Пароль на RuTracker\
SAVE_DIRECTORY=        # Директория для сохранения торрентов

### Настройки поиска и фильтрации

MAX_RESULTS=5                    # Максимальное количество результатов\
MIN_FILE_SIZE_GB=1.3             # Минимальный размер файла в ГБ\
MAX_FILE_SIZE_GB=15              # Максимальный размер файла в ГБ\
FORBIDDEN_WORDS=sample,trailer    # Слова-исключения через запятую

### Логирование и безопасность

LOG_LEVEL=INFO                   # (DEBUG, INFO, WARNING, ERROR)\
LOG_FILE=bot.log                 # Файл логов\
USE_CONSOLE=true                 # Вывод логов в консоль\
WHITELIST_FILE=whitelist.txt     # Файл списка разрешенных пользователей\
UNAUTHORIZED_LOG_FILE=unauthorized_users.log  # Лог неавторизованных пользователей

### Прокси (опционально)

USE_PROXY=false                  # Использовать прокси\
HTTP_PROXY=http://123.4.5.6:789  # HTTP прокси\
HTTPS_PROXY=http://123.4.5.6:789 # HTTPS прокси


## Запуск
### Обычный запуск
python3 bot.py

### Запуск как системный сервис
1.	Настройте файл сервиса:\
sudo cp rutbot.service /etc/systemd/system/\
Поменяйте директории в файле rutbot.service на свои. Для этого выполните команду:\
sudo nano /etc/systemd/system/rutbot.service
sudo systemctl daemon-reload\
sudo systemctl enable rutbot.service\
sudo systemctl start rutbot.service

2.	Установите сервис:\
sudo cp rutbot.service /etc/systemd/system/\
sudo systemctl daemon-reload\
sudo systemctl enable rutbot.service\
sudo systemctl start rutbot.service

3.	Управление сервисом:\
sudo systemctl status rutbot.service  # Проверка статуса\
sudo systemctl stop rutbot.service    # Остановка\
sudo systemctl restart rutbot.service # Перезапуск

## Использование бота
•	/start - Запустить бота и показать меню\
•	/f [название] - Поиск по названию (например: /f Матрица)\
•	/info - Показать статистику (количество фильмов и пользователей)\
### Интерактивное меню:
•	🔍 Поиск фильма - Запуск поиска по названию\
•	🔗 URL c rutracker - Загрузка торрента по прямой ссылке\
При поиске результаты сортируются по количеству сидов и размеру, что обеспечивает получение наиболее качественных и быстро скачиваемых торрентов.

## Лицензия:
Проект распространяется с открытым исходным кодом. Используйте его с соблюдением законодательства и правил сайта rutracker.org.