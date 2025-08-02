import os
import re
import telebot
import logging
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import (
    ensure_directory_exists,
    get_user_count,
    add_user,
    is_user_allowed,
    get_all_users,
    get_user_role,
    set_user_role,
)
from rutracker_api import RutrackerAPI
from jellyfin_api import JellyfinAPI

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
    'LOG_LEVEL', 'LOG_FILE', 'USE_CONSOLE', 'LOG_FORMAT', 'TELEGRAM_TOKEN',
    'RUTRACKER_USERNAME', 'RUTRACKER_PASSWORD', 'SAVE_DIRECTORY', 'MIN_FILE_SIZE_GB', 'MAX_FILE_SIZE_GB',
    'UNAUTHORIZED_LOG_FILE', 'FORBIDDEN_WORDS', 'MAX_RESULTS',
    'JELLYFIN_URL', 'JELLYFIN_API_KEY'
]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Отсутствующие переменные окружения: {', '.join(missing_vars)}")

# Настройки из переменных окружения
min_file_size_gb = float(os.getenv('MIN_FILE_SIZE_GB'))
max_file_size_gb = float(os.getenv('MAX_FILE_SIZE_GB'))
forbidden_words = os.getenv('FORBIDDEN_WORDS').split(',')
max_results = int(os.getenv('MAX_RESULTS'))

# Инициализация бота и API
TOKEN = os.getenv('TELEGRAM_TOKEN')
RUTRACKER_USERNAME = os.getenv('RUTRACKER_USERNAME')
RUTRACKER_PASSWORD = os.getenv('RUTRACKER_PASSWORD')
SAVE_DIRECTORY = os.getenv('SAVE_DIRECTORY')

if not all([TOKEN, RUTRACKER_USERNAME, RUTRACKER_PASSWORD, SAVE_DIRECTORY]):
    raise ValueError("Не все необходимые переменные окружения заданы")

ensure_directory_exists(SAVE_DIRECTORY)

bot = telebot.TeleBot(TOKEN)
rutracker_api = RutrackerAPI(RUTRACKER_USERNAME, RUTRACKER_PASSWORD)
jellyfin_api = JellyfinAPI()

# Проверка наличия фильма в Jellyfin
def is_movie_in_jellyfin(title):
    return jellyfin_api.movie_exists(title)

# Проверка подключения к RuTracker
def check_rutracker_status():
    try:
        return rutracker_api.login()
    except Exception as e:
        logging.error(f"Ошибка проверки RuTracker: {e}")
        return False

# Проверка подключения к Jellyfin
def check_jellyfin_status():
    try:
        # Пробуем получить список фильмов с пустым поиском
        return jellyfin_api.movie_exists("")
    except Exception as e:
        logging.error(f"Ошибка проверки Jellyfin: {e}")
        return False

# Функции для работы с ботом
def send_message_with_search_button(chat_id, text):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔍 Поиск фильма", callback_data="search_prompt"))
    keyboard.add(InlineKeyboardButton("🔗 URL c rutracker", callback_data="get_url"))
    bot.send_message(chat_id, text, reply_markup=keyboard)

def send_message_without_search_button(chat_id, text):
    bot.send_message(chat_id, text)

def log_unauthorized_access(user_id):
    if 'unauthorized_logger' in globals() and unauthorized_logger:
        unauthorized_logger.info(f"Неавторизованный доступ: {user_id}")

def check_access(chat_id):
    if not is_user_allowed(chat_id):
        log_unauthorized_access(chat_id)
        # Не отвечаем пользователям, которых нет в базе
        return False
    return True

# Глобальный фильтр: не отвечать неавторизованным пользователям
def authorized_only(func):
    def wrapper(message, *args, **kwargs):
        if not check_access(message.chat.id):
            return
        return func(message, *args, **kwargs)
    return wrapper

def authorized_only_callback(func):
    def wrapper(call, *args, **kwargs):
        if not check_access(call.message.chat.id):
            return
        return func(call, *args, **kwargs)
    return wrapper

@bot.message_handler(commands=['start'])
@authorized_only
def send_welcome(message):
    add_user(message.chat.id)
    role = get_user_role(message.chat.id)
    if role == 'admin':
        welcome = "Вы администратор. "
    else:
        welcome = ""
    send_message_with_search_button(
        message.chat.id,
        f"{welcome}Привет! Используй команду /f [название фильма]\nдля поиска или нажми кнопку ниже.\nМожно делать общий поиск по жанрам или годам\nПример: комедия 2024."
    )

@bot.message_handler(commands=['info'])
@authorized_only
def send_info(message):
    user_count = get_user_count()
    bot.send_message(
        message.chat.id,
        f"Всего пользователей бота: {user_count}"
    )

@bot.message_handler(commands=['users'])
@authorized_only
def list_users(message):
    if get_user_role(message.chat.id) != 'admin':
        bot.send_message(message.chat.id, "Доступ запрещён.")
        return
    users = get_all_users()
    if not users:
        bot.send_message(message.chat.id, "Пользователей нет.")
        return
    text = "Пользователи:\n"
    for user in users:
        text += f"ID: {user['telegram_id']}, Роль: {user['role']}\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['setrole'])
@authorized_only
def set_role(message):
    if get_user_role(message.chat.id) != 'admin':
        bot.send_message(message.chat.id, "Доступ запрещён.")
        return
    try:
        _, user_id, role = message.text.split()
        if role not in ('user', 'admin'):
            bot.send_message(message.chat.id, "Роль должна быть 'user' или 'admin'.")
            return
        set_user_role(user_id, role)
        bot.send_message(message.chat.id, f"Роль пользователя {user_id} изменена на {role}")
    except Exception:
        bot.send_message(message.chat.id, "Использование: /setrole <telegram_id> <role>")

@bot.message_handler(commands=['deleteuser'])
@authorized_only
def delete_user(message):
    if get_user_role(message.chat.id) != 'admin':
        bot.send_message(message.chat.id, "Доступ запрещён.")
        return
    try:
        _, user_id = message.text.split()
        if str(user_id) == str(message.chat.id):
            bot.send_message(message.chat.id, "Нельзя удалить самого себя.")
            return
        from utils import delete_user_by_id
        if delete_user_by_id(user_id):
            bot.send_message(message.chat.id, f"Пользователь {user_id} удалён.")
        else:
            bot.send_message(message.chat.id, f"Пользователь {user_id} не найден.")
    except Exception:
        bot.send_message(message.chat.id, "Использование: /deleteuser <telegram_id>")

@bot.message_handler(commands=['status'])
@authorized_only
def send_status(message):
    rutracker_status = check_rutracker_status()
    jellyfin_status = check_jellyfin_status()
    status_text = (
        f"Статус подключения:\n"
        f"RuTracker: {'✅ Подключено' if rutracker_status else '❌ Нет подключения'}\n"
        f"Jellyfin: {'✅ Подключено' if jellyfin_status else '❌ Нет подключения'}"
    )
    bot.send_message(message.chat.id, status_text)

@bot.message_handler(commands=['help'])
@authorized_only
def send_help(message):
    role = get_user_role(message.chat.id)
    if role == 'admin':
        help_text = (
            "Доступные команды для администратора:\n"
            "/start — приветствие и меню\n"
            "/f <название> — поиск и скачивание фильма\n"
            "/info — статистика пользователей\n"
            "/users — список пользователей\n"
            "/setrole <telegram_id> <role> — сменить роль пользователя (user/admin)\n"
            "/deleteuser <telegram_id> — удалить пользователя\n"
            "/status — статус подключения к RuTracker и Jellyfin\n"
            "/help — показать это сообщение\n"
        )
    else:
        help_text = (
            "Доступные команды:\n"
            "/start — приветствие и меню\n"
            "/f <название> — поиск и скачивание фильма\n"
            "/info — статистика пользователей\n"
            "/status — статус подключения к RuTracker и Jellyfin\n"
            "/help — показать это сообщение\n"
        )
    bot.send_message(message.chat.id, help_text)

@bot.callback_query_handler(func=lambda call: call.data == "search_prompt")
@authorized_only_callback
def search_prompt(call):
    msg = bot.send_message(call.message.chat.id, "Введите название фильма для поиска:")
    bot.register_next_step_handler(msg, process_search_step, msg.message_id)

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel_search"))
    bot.send_message(call.message.chat.id, "Вы можете отменить поиск, нажав кнопку ниже.", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "get_url")
@authorized_only_callback
def get_url_prompt(call):
    msg = bot.send_message(call.message.chat.id, "Отправьте ссылку для загрузки торрент-файла:")

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel_search"))
    bot.send_message(call.message.chat.id, "Вы можете отменить загрузку, нажав кнопку ниже.", reply_markup=keyboard)

    bot.register_next_step_handler(msg, process_get_url_step)

def process_search_step(message, prompt_message_id):
    if not check_access(message.chat.id):
        return
    if message.text.startswith('/'):
        send_message_with_search_button(message.chat.id, "Пожалуйста, укажите название фильма без команды.")
        return
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)
    search_movie_internal(message, message.text)

def process_get_url_step(message):
    if not check_access(message.chat.id):
        return
    if message.text.startswith('/'):
        send_message_with_search_button(message.chat.id, "Пожалуйста, отправьте ссылку без команды.")
        return
    url = message.text
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    status_message = bot.send_message(message.chat.id, "⏳ Загружаю торрент-файл... Пожалуйста, подождите.")
    try:
        torrent_content = rutracker_api.download_torrent_by_url(url)
        if torrent_content:
            topic_id_match = re.search(r't=(\d+)', url)
            if topic_id_match:
                topic_id = topic_id_match.group(1)
                file_path = os.path.join(SAVE_DIRECTORY, f"{topic_id}.torrent")
                with open(file_path, 'wb') as f:
                    f.write(torrent_content)
                os.chmod(file_path, 0o755)
                bot.delete_message(chat_id=message.chat.id, message_id=status_message.message_id)

                title = rutracker_api.get_title_from_url(url)
                title_display = title.split('/')[0].strip() if title else f"Торрент {topic_id}"

                # Проверка через Jellyfin
                if title and is_movie_in_jellyfin(title_display):
                    bot.send_message(message.chat.id, "😆 Файл уже есть на Plex/Jellyfin. Торрент не будет загружен.")
                    return

                bot.send_document(
                    message.chat.id,
                    torrent_content,
                    visible_file_name=f"{topic_id}.torrent",
                    caption=f"✅ Вот ваш торрент-файл: \"{title_display}\"\n\nБольше ничего делать не надо - всё само скачается и скоро появится на нашем Plex"
                )

                logging.info(f"Торрент-файл загружен: {file_path}")
                send_message_with_search_button(message.chat.id, "Вы можете начать новый поиск или загрузить другой файл.")
            else:
                bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text="❌ Не удалось извлечь id топика из ссылки.")
        else:
            raise ValueError("Ошибка при загрузке торрент-файла")
    except Exception as e:
        logging.error(f"Ошибка при загрузке торрент-файла: {e}")
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel_search"))
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text="❌ Ошибка при загрузке торрент-файла. Пожалуйста, попробуйте ещё раз позже.", reply_markup=keyboard)

@bot.message_handler(commands=['f'])
@authorized_only
def search_movie(message):
    query = message.text.replace('/f', '').strip()
    if not query:
        send_message_with_search_button(message.chat.id, "Пожалуйста, укажите название фильма. Например: /f Матрица")
        return
    search_movie_internal(message, query)

def search_movie_internal(message, query):
    if not check_access(message.chat.id):
        return
    # Проверка через Jellyfin
    if is_movie_in_jellyfin(query):
        send_message_with_search_button(message.chat.id, "Файл уже есть на сервере (Jellyfin).")
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

    results = sorted(results, key=lambda x: (x.get('seeders_count', 0), x.get('size_value', 0)), reverse=True)[:max_results]
    result_text = f"Найдено {len(results)} результатов по запросу '{query}' ({min_file_size_gb}-{max_file_size_gb} ГБ):\n\n"
    for idx, result in enumerate(results, 1):
        seeders_display = result.get('seeders_count', 0)
        if seeders_display == 0 and 'seeders' in result and result['seeders'] != "0":
            try:
                seeders_clean = re.sub(r'[^\d]', '', result['seeders'])
                seeders_display = int(seeders_clean) if seeders_clean else 0
            except:
                seeders_display = 0

        result_text += f"{idx}. {result['title']}\n   Размер: {result['size']}, Сиды: {seeders_display}\n\n"

    markup = InlineKeyboardMarkup()
    for idx, result in enumerate(results, 1):
        seeders_display = result.get('seeders_count', 0)
        if seeders_display == 0 and 'seeders' in result and result['seeders'] != "0":
            try:
                seeders_clean = re.sub(r'[^\d]', '', result['seeders'])
                seeders_display = int(seeders_clean) if seeders_clean else 0
            except:
                seeders_display = 0

        markup.add(InlineKeyboardButton(
            f"#{idx} [Размер: {result['size']}, Сиды: {seeders_display}]",
            callback_data=f"download_{result['topic_id']}_{query}"
        ))

    markup.add(InlineKeyboardButton("Отмена", callback_data="cancel_search"))

    bot.edit_message_text(chat_id=message.chat.id, message_id=status_message.message_id, text=result_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('download_'))
@authorized_only_callback
def download_torrent(call):
    data = call.data.replace('download_', '').split('_')
    topic_id, query = data[0], '_'.join(data[1:])

    # Проверка через Jellyfin
    if is_movie_in_jellyfin(query):
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="❗️ Этот торрент уже был загружен ранее (Jellyfin).")
        return

    search_result = rutracker_api.search_movie(query)
    title_display = query

    for result in search_result["results"]:
        if result["topic_id"] == topic_id:
            title = result["title"].split('/')[0].strip()
            title_display = title
            if is_movie_in_jellyfin(title_display):
                bot.send_message(call.message.chat.id, "😆 Файл уже есть на Plex/Jellyfin. Торрент не будет загружен.")
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
            bot.send_document(
                call.message.chat.id,
                torrent_data,
                visible_file_name=f"rutracker_{topic_id}.torrent",
                caption=f"✅ Вот ваш торрент-файл: \"{title_display}\"\n\nБольше ничего делать не надо - всё само скачается и скоро появится на нашем Plex"
            )

            logging.info(f"Торрент-файл загружен: {file_path}")

            send_message_with_search_button(call.message.chat.id, "Вы можете начать новый поиск или загрузить другой файл.")
        else:
            raise ValueError("Ошибка при загрузке торрент-файла")
    except Exception as e:
        logging.error(f"Ошибка при загрузке торрент-файла: {e}")
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Отмена", callback_data="cancel_search"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="❌ Не удалось скачать торрент-файл. Пожалуйста, попробуйте ещё раз позже.", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_search")
@authorized_only_callback
def cancel_search(call):
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    send_message_with_search_button(call.message.chat.id, "Поиск отменён. Используйте команду /start для нового поиска.")

# Запуск бота
if __name__ == "__main__":
    logging.info("Бот запущен")
    bot.polling(none_stop=True)