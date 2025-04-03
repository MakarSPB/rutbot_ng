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
        whitelist = set(line.strip() for line in f if line.strip())
    print(f"Загружен белый список: {whitelist}")
    return whitelist

def get_user_count(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return sum(1 for line in f if line.strip())

def get_movie_count(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return sum(1 for row in reader)

def log_search_result(file_path, title, forbidden_words, forbidden_patterns):
    title = title.split('/')[0].strip().lower()
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['title'].strip().lower() == title:
                return False

    with open(file_path, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([f'"{title}"'])
    return True

def is_query_already_searched(file_path, query):
    query = query.strip().lower()
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['title'].strip().lower() == query:
                return True
    return False

def is_title_already_logged(file_path, title):
    title = title.strip().lower()
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['title'].strip().lower() == title:
                return True
    return False