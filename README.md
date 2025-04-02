# UBEBC rutbot
------------

Бот на питоне для поиска файлов на rutraker.org и скачивания торрент файлов.\
Бот пуляет файлы в чат и кладёт их на диск в нужную дирекеторю.\
Так же ведёт базу скачаноего в файл.\
При повторном запросе файла, бот проверяет базу и не качает файл повторно.\
Присутствует отключаемая работа через прокси.\
Бот умеет фильтровать запросы по размеру файлов.\

------------
Копируем .env.example в .env и заполняем его данными:

Общие настройки:
TELEGRAM_TOKEN=Ваш токен\
RUTRACKER_USERNAME=Логин от rutracker\
RUTRACKER_PASSWORD=пароль от rutracker\
SAVE_DIRECTORY=место куда сохранять торрент файлы

Фильтр резульатов поиска:\
MAX_RESULTS=5\
MIN_FILE_SIZE_GB=1.3\
MAX_FILE_SIZE_GB=6

Настройка логов:\
Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL) INFO - штатный режим.

LOG_LEVEL=INFO\
LOG_FILE=bot.log\
USE_CONSOLE=true\
LOG_FORMAT='%(asctime)s - %(name)s - %(levelname)s - %(message)s'\
LOG_DATE_FORMAT='%Y-%m-%d %H:%M:%S'

Настройка PROXY (true/false):\
USE_PROXY=false\
HTTP_PROXY=http:123.4.5.6:789\
HTTPS_PROXY=http:123.4.5.6:789

Прочие файлы, при отсутствии создаются автоматически:\
DOWNLOAD_COUNT_FILE=download_count.txt\
WHITELIST_FILE=whitelist.txt

База фильмов\
BASE_FILE=base.csv

Слова-исключения для base.csv\
Запросы с этими словами и их комбинацией с годом, не попадут в базу\
Пример: Комедия 2024\
Слова через запятую без пробелов.\
FORBIDDEN_WORDS=комедия,боевик,фантастика,фентэзи,драма,мелодрама,ситком


------------

whitelist.txt - добавляем в него id юзеров телеги.\ 
(узнать свой id можно у @getmyid_bot)\
Каждый в новой строке.

Пример:

0000000000\
000000000

------------

Минималочка: 
sudo apt update\
sudo apt install python3\
sudo apt-get install python3-pip\
pip install -r requirements.txt

------------

Запуск:

pythone3 bot.py

или мутим сервис - rutbot.service

Правим файл под себя rutbot.service\
копируем его в /etc/systemd/system/

sudo cp rutbot.service /etc/systemd/system/
перезагружаем демон\
sudo systemctl daemon-reload

добавляем в автозапуск:\
sudo systemctl enable rutbot.service

Старт/Стоп:\
sudo systemctl start/stop rutbot.service
