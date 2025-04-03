import sqlite3

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            forbidden INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_movie(db_path, title, forbidden):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO movies (title, forbidden) VALUES (?, ?)', (title, forbidden))
    conn.commit()
    conn.close()

def is_movie_in_db(db_path, title):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM movies WHERE title = ?', (title.strip(),))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_movie_count(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM movies')
    count = cursor.fetchone()[0]
    conn.close()
    return count

