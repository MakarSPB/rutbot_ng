#!/usr/bin/env python3
from dotenv import load_dotenv
import os

load_dotenv('/home/makar/rutbot_ng/.env')
import telebot.apihelper

TOKEN = os.getenv('TELEGRAM_TOKEN')
API_TEMPLATE = os.getenv('TELEGRAM_API_URL')

print('ENV TELEGRAM_API_URL =', API_TEMPLATE)
print('telebot.apihelper.API_URL =', telebot.apihelper.API_URL)

# Если в окружении задан TELEGRAM_API_URL, установим его в telebot.apihelper
if API_TEMPLATE:
    try:
        telebot.apihelper.API_URL = API_TEMPLATE
        print('telebot.apihelper.API_URL set to', telebot.apihelper.API_URL)
    except Exception as e:
        print('Failed to set telebot.apihelper.API_URL:', e)

if not TOKEN or not API_TEMPLATE:
    print('Missing TELEGRAM_TOKEN or TELEGRAM_API_URL')
    raise SystemExit(2)

url = telebot.apihelper.API_URL.format(TOKEN) + 'getMe'
print('built URL =', url)

# use telebot session to perform the same request
sess = telebot.apihelper._get_req_session()
resp = sess.get(url, timeout=15)
print('status =', resp.status_code)
print('resp headers =', dict(resp.headers))
print('resp body =', resp.text)
