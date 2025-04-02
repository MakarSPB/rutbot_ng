import os
import logging

def ensure_directory_exists(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logging.info(f"Создание {directory}")
    except Exception as e:
        logging.error(f"Ошибка при создании директории {directory}: {e}")

def ensure_file_exists(file_path, default_content="0"):
    try:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as file:
                file.write(default_content)
            logging.info(f"Создание файла {file_path} с содержимым по умолчанию: {default_content}")
    except Exception as e:
        logging.error(f"Ошибка при создании файла {file_path}: {e}")

def load_whitelist(whitelist_file):
    try:
        if not os.path.exists(whitelist_file):
            logging.error(f"Файл {whitelist_file} не найден")
            return set()
        with open(whitelist_file, 'r') as file:
            content = file.read().strip()
            if not content:
                return set()
            return {int(line.strip()) for line in content.splitlines()}
    except Exception as e:
        logging.error(f"Ошибка при загрузке белого списка: {e}")
        return set()


