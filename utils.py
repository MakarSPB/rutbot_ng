import os
import csv

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def ensure_file_exists(file_path, default_content=""):
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(default_content)

def load_whitelist(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def get_user_count(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return sum(1 for line in f if line.strip())

def load_movies(file_path):
    movies = set()
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            movies.add(row['title'].strip().lower())
    return movies

def save_movie(file_path, title, forbidden):
    with open(file_path, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([title, forbidden])


