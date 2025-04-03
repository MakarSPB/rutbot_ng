import os
import csv
import sqlite3
from dotenv import load_dotenv
from sql import init_db, add_movie

# Загрузка переменных окружения
load_dotenv()

# Получение пути к базе данных из переменных окружения
db_path = os.getenv('DB_PATH')
csv_file_path = 'base.csv'  # Путь к файлу base.csv

# Инициализация базы данных
init_db(db_path)

def import_csv_to_db(db_path, csv_file_path):
    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            title = row['title']
            forbidden = 0  # Установите значение forbidden по умолчанию
            add_movie(db_path, title, forbidden)
            print(f"Импортирован фильм: {title}")

if __name__ == "__main__":
    if not os.path.exists(csv_file_path):
        print(f"Файл {csv_file_path} не найден.")
    else:
        import_csv_to_db(db_path, csv_file_path)
        print("Импорт завершен.")

