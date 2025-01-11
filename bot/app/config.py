import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
SECRETS_DIR = BASE_DIR / 'secrets'
SECRETS_DIR.mkdir(exist_ok=True)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "your telegram token") # your telegram token
GOOGLE_CREDS_PATH = SECRETS_DIR / 'google_creds.json'
WHATSAPP_REDIRECT = "your number" # your number
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/bot.db')

# Добавим настройки для админ-бота
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", " your admin bot telegram token") #admin bot
AUTHORIZED_OPERATORS = [
    123456789,  # User ID allowed to admin bot
]

# API между ботами
MAIN_BOT_URL = os.getenv('MAIN_BOT_URL', 'http://silkway-bot:8000')
SECRET_KEY = os.getenv("SECRET_KEY", "silkway-super-secret-key-2024")

# Настройки для job-queue
JOB_QUEUE_INTERVAL = 30  # интервал проверки в секундах

# Количество сообщений в истории чата
CHAT_HISTORY_LIMIT = 5