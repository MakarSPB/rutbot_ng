import os
import sqlite3

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_db_path():
    return os.getenv('SQLITE_DB_FILE', 'db/bot_users.db')

def get_db_connection():
    db_path = get_db_path()
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path))
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
    ''')
    conn.commit()
    conn.close()

def add_user(telegram_id):
    conn = get_db_connection()
    cur = conn.execute('SELECT COUNT(*) FROM users')
    count = cur.fetchone()[0]
    if count == 0:
        # Первый пользователь — admin
        conn.execute('INSERT OR IGNORE INTO users (telegram_id, role) VALUES (?, ?)', (str(telegram_id), 'admin'))
    else:
        conn.execute('INSERT OR IGNORE INTO users (telegram_id, role) VALUES (?, ?)', (str(telegram_id), 'user'))
    conn.commit()
    conn.close()

def delete_user_by_id(telegram_id):
    conn = get_db_connection()
    cur = conn.execute('DELETE FROM users WHERE telegram_id = ?', (str(telegram_id),))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted

def is_user_allowed(telegram_id):
    return get_user_role(telegram_id) is not None

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

def get_all_users():
    conn = get_db_connection()
    cur = conn.execute('SELECT telegram_id, role FROM users')
    users = cur.fetchall()
    conn.close()
    return users

init_db()