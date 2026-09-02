#!/usr/bin/env python3
from dotenv import load_dotenv
import os, requests, sys

# Загрузить .env из проекта
load_dotenv('/home/makar/rutbot_ng/.env')

TOKEN = os.getenv('TELEGRAM_TOKEN')
API_TEMPLATE = os.getenv('TELEGRAM_API_URL')

if not TOKEN or not API_TEMPLATE:
    print('ERROR: TELEGRAM_TOKEN or TELEGRAM_API_URL missing', file=sys.stderr)
    sys.exit(2)

api = API_TEMPLATE.format(TOKEN)
url = api + 'getMe'
print('request URL:', url)

try:
    r = requests.get(url, timeout=15)
    print('status:', r.status_code)
    print('body:', r.text)
except Exception as e:
    print('request error:', e, file=sys.stderr)
    sys.exit(1)
