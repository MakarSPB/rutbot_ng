import os
import re
import telebot
import logging
import time
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import ensure_directory_exists, ensure_file_exists, load_whitelist, get_movie_count, get_user_count
from rutracker_api import RutrackerAPI
from threading import Thread

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
def setup_logging():
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE')
    use_console = os.getenv('USE_CONSOLE', 'false').lower() == 'true'
    log_format = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    unauthorized_log_file = os.getenv('UNAUTHORIZED_LOG_FILE')
    enable_unauthorized_logging = os.getenv('ENABLE_UNAUTHORIZED_LOGGING', 'true').lower() == 'true'

    try:
        log_level = getattr(logging, log_level)
    except AttributeError:
        raise ValueError(f"Некорректный уровень логирования: {log_level}")

    handlers = [logging.FileHandler(log_file)] if log_file else []
    if use_console:
        handlers.append(logging.StreamHandler())

    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)

    if enable_unauthorized_logging and unauthorized_log_file:
        unauthorized_handler = logging.FileHandler(unauthorized_log_file)
        unauthorized_handler.setLevel(logging.INFO)
        unauthorized_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        global unauthorized_logger
        unauthorized_logger = logging.getLogger('unauthorized')
        unauthorized_logger.addHandler(unauthorized_handler)
        unauthorized_logger.setLevel(logging.INFO)
    else:
        unauthorized_logger = None

setup_logging()

# Проверка переменных окружения
required_env_vars = [
    'LOG_LEVEL', 'LOG_FILE', 'USE_CONSOLE', 'LOG_FORMAT', 'WHITELIST_FILE', 'TELEGRAM_TOKEN',
    'RUTRACKER_USERNAME', 'RUTRACKER_PASSWORD', 'SAVE_DIRECTORY', 'MIN_FILE_SIZE_GB', 'MAX_FILE_SIZE_GB',
    'UNAUTHORIZED_LOG_FILE', 'FORBIDDEN_WORDS', 'BASE_FILE', 'MAX_RESULTS'
]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Отсутствующие переменные окружения: {', '.join(missing_vars)}")

# Настройки из переменных окружения
whitelist_file = os.getenv('WHITELIST_FILE')
min_file_size_gb = float(os.getenv('MIN_FILE_SIZE_GB'))
max_file_size_gb = float(os.getenv('MAX_FILE_SIZE_GB'))
base_file = os.getenv('BASE_FILE')
forbidden_words = os.getenv('FORBIDDEN_WORDS').split(',')
max_results = int(os.getenv('MAX_RESULTS'))
subscribers_file = 'subscribers.txt'

# Генерация комбинаций слов исключений с годами
def generate_forbidden_patterns(forbidden_words):
    years = [str(year) for year in range(1940, 2031)]
    return [f"{word} {year}" for word in forbidden_words for year in years] + [f"{year} {word}" for word in forbidden_words for year in years]

forbidden_patterns = generate_forbidden_patterns(forbidden_words)

# Инициализация бота и API
TOKEN = os.getenv('TELEGRAM_TOKEN')
RUTRACKER_USERNAME = os.getenv('RUTRACKER_USERNAME')
RUTRACKER_PASSWORD = os.getenv('RUTRACKER_PASSWORD')
SAVE_DIRECTORY = os.getenv('SAVE_DIRECTORY')

if not all([TOKEN, RUTRACKER_USERNAME, RUTRACKER_PASSWORD, SAVE_DIRECTORY]):
    raise ValueError("Не все необходимые переменные окружения заданы")

ensure_directory_exists(SAVE_DIRECTORY)
ensure_file_exists(whitelist_file, default_content="")
ensure_file_exists(base_file, default_content="title\n")
ensure_file_exists(subscribers_file, default_content="")

bot = telebot.TeleBot(TOKEN)
rutracker_api = RutrackerAPI(RUTRACKER_USERNAME, RUTRACKER_PASSWORD)
whitelist = load_whitelist(whitelist_file)

# Загрузка подписчиков из файла
def load_subscribers():
    with open(subscribers_file, 'r') as f:
        return set(line.strip() for line in f if line.strip())

# Сохранение подписчиков в файл
def save_subscribers():
    with open(subscribers_file, 'w') as f:
        for subscriber in subscribers:
            f.write(f"{subscriber}\n")

subscribers = load_subscribers()

# Функции для работы с ботом
def send_message_with_search_button(chat_id, text):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔍 Поиск фильма", callback_data="search_prompt"))
    keyboard.add(InlineKeyboardButton("🔗 URL c rutracker", callback_data="get_url"))
    bot.send_message(chat_id, text, reply_markup=keyboard)

def send_message_without_search_button(chat_id, text):
    bot.send_message(chat_id, text)

def log_unauthorized_access(user_id):
    if unauthorized_logger:
        unauthorized_logger.info(f"Неавторизованный доступ: {user_id}")

def check_access(chat_id):
    if chat_id not in whitelist:
        log_unauthorized_access(chat_id)
        send_message_without_search_button(chat_id, "Доступ запрещен.")
        return False
    return True

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not check_access(message.chat.id):
        return
    send_message_with_search_button(message.chat.id, "Привет! Используй команду /f [название фильма]\nдля поиска или нажми кнопку ниже.\nМожно делать общий поиск по жанрам или годам\nПример: комедия 2024.")

@bot.message_handler(commands=['info'])
def send_info(message):
    if not check_access(message.chat.id):
        return
    movie_count = get_movie_count(base_file)
    user_count = get_user_count(whitelist_file)
    bot.send_message(message.chat.id, f"Всего на сервере фильмов: {movie_count}\nВсего пользователей бота: {user_count}")

@bot.message_handler(commands=['sub'])
def sub(message):
    if not check_access(message.chat.id):
        return
    if message.chat.id in subscribers:
        subscribers.discard(message.chat.id)
        save_subscribers()
        bot.send_message(message.chat.id, "Вы отписались от уведомлений об обновлениях.")
    else:
        subscribers.add(message.chat.id)
        save_subscribers()
        bot.send_message(message.chat.id, "Вы подписались на уведомления об обновлениях.")

@bot.callback_query_handler(func=lambda call: call.data == "search_prompt")
def search_prompt(call):
    msg = bot.send_message(call.message.chat.id, "Введите название фильма для поиска:")
    bot.register_next_step_handler(msg, process_search_step, msg.message_id)

    # Добавление кнопки "Отмена"
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel_search"))
    bot.send_message(call.message.chat.id, "Вы можете отменить поиск, нажав кнопку ниже.", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "get_url")
def get_url_prompt(call):
    msg = bot.send_message(call.message.chat.id, "Отправьте ссылку для загрузки торрент-файла:")

    # Добавление кнопки "Отмена"
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel_search"))
    bot.send_message(call.message.chat.id, "Вы можете отменить загрузку, нажав кнопку ниже.", reply_markup=keyboard)

    bot.register_next_step_handler(msg, process_get_url_step)

def process_search_step(message, prompt_message_id):
    if message.text.startswith('/'):
        send_message_with_search_button(message.chat.id, "Пожалуйста, укажите название фильма без команды.")
        return
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)
    search_movie_internal(message, message.text)

def process_get_url_step(message):
    if message.text.startswith('/'):
        send_message_with_search_button(message.chat.id, "Пожалуйста, отправьте ссылку без команды.")
        return
    url = message.text
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    status_message = bot.send_message(message.chat.id, "⏳ Загружаю торрент-файл... Пожалуйста, подождите.")
    try:
        torrent_content = rutracker_api.download_torrent_by_url(url)
        if torrent_content:
            # Извлечение id топика из URL
            topic_id_match = re.search(r't=(\d+)', url)
            if topic_id_match:
                topic_id = topic_id_match.group(1)
                file_path = os.path.join(SAVE_DIRECTORY, f"{topic_id}.torrent")
                with open(file_path, 'wb') as f:
                    f.write(torrent_content)
                os.chmod(file_path, 0o755)
                bot.delete_message(chat_id=message.chat.id, message_id=status_message.message_id)
                bot.send_document(message.chat.id, torrent_content, visible_file_name=f"{topic_id}.torrent", caption="✅ Вот ваш торрент-файл!\n\nБольше ничего делать не надо - всё само скачается и скоро появится на нашем Plex")
                
                # Логирование информации о загруженном файле
                logging.info(f"Торрент-файл загружен: {file_path}")

                # Извлечение заголовка страницы
                title = rutracker_api.get_title_from_url(url)
                if title:
                    title = title.split('/')[0].strip()
                    # Логирование результата в BASE_FILE
                    if not rutracker_api.log_search_result(base_file, title, forbidden_words, forbidden_patterns):
                        bot.send_message(message.chat.id, "😆 Файл уже есть на Plex. Торрент не будет загружен.")
                # Добавление кнопок поиска после отправки торрент-файла
                send_message_with_search_button(message.chat.id, "Вы можете начать новый поиск или загрузить другой файл.")
            else:
                bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text="❌ Не удалось извлечь id топика из ссылки.")
        else:
            raise ValueError("Ошибка при загрузке торрент-файла")
    except Exception as e:
        logging.error(f"Ошибка при загрузке торрент-файла: {e}")
        # Добавление кнопки "Отмена"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel_search"))
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text="❌ Ошибка при загрузке торрент-файла. Пожалуйста, попробуйте ещё раз позже.", reply_markup=keyboard)

@bot.message_handler(commands=['f'])
def search_movie(message):
    if not check_access(message.chat.id):
        return
    query = message.text.replace('/f', '').strip()
    if not query:
        send_message_with_search_button(message.chat.id, "Пожалуйста, укажите название фильма. Например: /f Матрица")
        return
    search_movie_internal(message, query)

def search_movie_internal(message, query):
    if rutracker_api.is_query_already_searched(base_file, query):
        send_message_with_search_button(message.chat.id, "Файл уже есть на сервере.")
        return

    status_message = bot.send_message(message.chat.id, f"🔍 Ищу фильм '{query}' на RuTracker...")

    search_result = rutracker_api.search_movie(query)

    if not search_result["success"]:
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text=search_result["message"])
        send_message_with_search_button(message.chat.id, search_result["message"])
        return

    results = search_result["results"]

    if not results:
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text=f"По запросу '{query}' ничего не найдено.")
        send_message_with_search_button(message.chat.id, f"По запросу '{query}' ничего не найдено.")
        return

    filtered_results = []
    for result in results:
        try:
            size_str = result['size'].lower()
            if 'gb' in size_str or 'гб' in size_str:
                match = re.search(r'(\d+[.,]?\d*)', size_str)
                if match:
                    size_value = float(match.group(1).replace(',', '.'))
                    if min_file_size_gb <= size_value <= max_file_size_gb:
                        result['size_value'] = size_value
                        filtered_results.append(result)
        except Exception as e:
            logging.error(f"Ошибка при обработке размера: {e}")

    results = filtered_results

    if not results:
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text=f"По запросу '{query}' чет я ничего не нашел :(")
        send_message_with_search_button(message.chat.id, f"По запросу '{query}' чет я ничего не нашел :(")
        return

    results = sorted(results, key=lambda x: x.get('size_value', 0))[:max_results]

    result_text = f"Найдено {len(results)} результатов по запросу '{query}' ({min_file_size_gb}-{max_file_size_gb} ГБ):\n\n"
    for idx, result in enumerate(results, 1):
        result_text += f"{idx}. {result['title']}\n   Размер: {result['size']}, Сиды: {result['seeders']}\n\n"

    markup = InlineKeyboardMarkup()
    for idx, result in enumerate(results, 1):
        markup.add(InlineKeyboardButton(f"#{idx} [Размер: {result['size']}]", callback_data=f"download_{result['topic_id']}_{query}"))

    markup.add(InlineKeyboardButton("Отмена", callback_data="cancel_search"))

    bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text=result_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('download_'))
def download_torrent(call):
    if not check_access(call.message.chat.id):
        return

    data = call.data.replace('download_', '').split('_')
    topic_id, query = data[0], '_'.join(data[1:])

    if rutracker_api.is_title_already_logged(base_file, query):
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="❗️ Этот торрент уже был загружен ранее.")
        return

    search_result = rutracker_api.search_movie(query)
    for result in search_result["results"]:
        if result["topic_id"] == topic_id:
            if not rutracker_api.log_search_result(base_file, result["title"], forbidden_words, forbidden_patterns):
                bot.send_message(call.message.chat.id, "😆 Файл уже есть на Plex. Торрент не будет загружен.")
                return
            break

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="⏳ Скачиваю торрент-файл... Пожалуйста, подождите.")

    try:
        torrent_data = rutracker_api.get_torrent(topic_id)

        if torrent_data:
            file_path = os.path.join(SAVE_DIRECTORY, f"{topic_id}.torrent")
            with open(file_path, 'wb') as f:
                f.write(torrent_data)
            os.chmod(file_path, 0o755)

            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_document(call.message.chat.id, torrent_data, visible_file_name=f"rutracker_{topic_id}.torrent", caption="✅ Вот ваш торрент-файл!\n\nБольше ничего делать не надо - всё само скачается и скоро появится на нашем Plex")

            # Логирование информации о загруженном файле
            logging.info(f"Торрент-файл загружен: {file_path}")

            # Добавление кнопок поиска после отправки торрент-файла
            send_message_with_search_button(call.message.chat.id, "Вы можете начать новый поиск или загрузить другой файл.")
        else:
            raise ValueError("Ошибка при загрузке торрент-файла")
    except Exception as e:
        logging.error(f"Ошибка при загрузке торрент-файла: {e}")
        # Добавление кнопки "Отмена"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel_search"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="❌ Не удалось скачать торрент-файл. Пожалуйста, попробуйте ещё раз позже.", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_search")
def cancel_search(call):
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    send_message_with_search_button(call.message.chat.id, "Поиск отменён. Используйте команду /start для нового поиска.")

# Функция для проверки изменений в файле BASE_FILE
def check_base_file_updates():
    last_modified_time = os.path.getmtime(base_file)
    last_lines = set()
    with open(base_file, 'r') as f:
        last_lines = set(f.readlines())
    while True:
        time.sleep(15)  # Проверка каждые 15 секунд
        current_modified_time = os.path.getmtime(base_file)
        if current_modified_time != last_modified_time:
            last_modified_time = current_modified_time
            with open(base_file, 'r') as f:
                current_lines = set(f.readlines())
            new_lines = current_lines - last_lines
            if new_lines:
                notify_subscribers(new_lines)
            last_lines = current_lines

# Функция для уведомления подписчиков
def notify_subscribers(new_lines):
    new_lines_text = ''.join(new_lines)
    for chat_id in subscribers:
        bot.send_message(chat_id, f"Файл BASE_FILE был обновлён. Добавлены:\n{new_lines_text}")

# Запуск проверки обновлений в отдельном потоке
update_thread = Thread(target=check_base_file_updates)
update_thread.start()

# Запуск бота
if __name__ == "__main__":
    logging.info("Бот запущен")
    bot.polling(none_stop=True)

