import os
import sqlite3

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_db_path():
    return os.getenv('SQLITE_DB_FILE', 'db/bot_users.db')

def get_db_connection():
    db_path = get_db_path()
    ensure_directory_exists(os.path.dirname(db_path))
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    ''')
    conn.commit()
    conn.close()

# --- Работа с пользователями ---

def add_user(telegram_id, role='user'):
    conn = get_db_connection()
    try:
        conn.execute('INSERT OR IGNORE INTO users (telegram_id, role) VALUES (?, ?)', (str(telegram_id), role))
        conn.commit()
    finally:
        conn.close()

def is_user_allowed(telegram_id):
    conn = get_db_connection()
    cur = conn.execute('SELECT 1 FROM users WHERE telegram_id = ?', (str(telegram_id),))
    allowed = cur.fetchone() is not None
    conn.close()
    return allowed

def get_user_count():
    conn = get_db_connection()
    cur = conn.execute('SELECT COUNT(*) FROM users')
    count = cur.fetchone()[0]
    conn.close()
    return count

def get_user_role(telegram_id):
    conn = get_db_connection()
    cur = conn.execute('SELECT role FROM users WHERE telegram_id = ?', (str(telegram_id),))
    row = cur.fetchone()
    conn.close()
    return row['role'] if row else None

def set_user_role(telegram_id, role):
    conn = get_db_connection()
    conn.execute('UPDATE users SET role = ? WHERE telegram_id = ?', (role, str(telegram_id)))
    conn.commit()
    conn.close()

# --- Работа с фильмами ---

def add_movie(title):
    conn = get_db_connection()
    try:
        conn.execute('INSERT OR IGNORE INTO movies (title) VALUES (?)', (title.strip(),))
        conn.commit()
    finally:
        conn.close()

def is_movie_exists(title):
    conn = get_db_connection()
    cur = conn.execute('SELECT 1 FROM movies WHERE title = ?', (title.strip(),))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def get_movie_count():
    conn = get_db_connection()
    cur = conn.execute('SELECT COUNT(*) FROM movies')
    count = cur.fetchone()[0]
    conn.close()
    return count

# --- Совместимость с прежними функциями ---

def log_search_result(title, forbidden_words, forbidden_patterns):
    title = title.split('/')[0].strip().lower()
    if any(word.lower() in title for word in forbidden_words):
        return False
    if is_movie_exists(title):
        return False
    add_movie(title)
    return True

def is_query_already_searched(query):
    query = query.strip().lower()
    return is_movie_exists(query)

def is_title_already_logged(title):
    title = title.strip().lower()
    return is_movie_exists(title)

# --- Инициализация базы при запуске ---
init_db()