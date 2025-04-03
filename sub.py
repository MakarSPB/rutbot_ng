import logging
from telebot import TeleBot

subscribers_file = 'subscribers.txt'

# Загрузка подписчиков из файла
def load_subscribers():
    with open(subscribers_file, 'r') as f:
        subscribers = set(line.strip() for line in f if line.strip())
    save_subscribers(subscribers)  # Сохранение для удаления дубликатов
    return subscribers

# Сохранение подписчиков в файл
def save_subscribers(subscribers):
    with open(subscribers_file, 'w') as f:
        for subscriber in subscribers:
            f.write(f"{subscriber}\n")

# Проверка статуса подписок
def check_subscriptions(bot: TeleBot, subscribers):
    for subscriber in list(subscribers):
        try:
            bot.send_message(subscriber, "Проверка статуса подписки.")
        except Exception as e:
            logging.error(f"Ошибка при проверке статуса подписки для {subscriber}: {e}")
            subscribers.discard(subscriber)
    save_subscribers(subscribers)
