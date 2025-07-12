import os
import threading
import asyncio
import json
import logging
from flask import Flask

# --- [ВАЖНО] Настройка логирования в файл ---
# Все, что происходит, будет записано в файл app.log в той же папке
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path), # Запись в файл
        logging.StreamHandler()             # Вывод в консоль (если Timeweb все же его поймает)
    ]
)

logging.info("--- СКРИПТ НАЧАЛ ВЫПОЛНЯТЬСЯ ---")

# --- Безопасная инициализация с логированием ---
try:
    logging.info("[1/4] Инициализация OpenAI...")
    from openai import OpenAI
    client_gpt = OpenAI(api_key=os.environ["MyKey2"])

    logging.info("[2/4] Инициализация Google Sheets...")
    from oauth2client.service_account import ServiceAccountCredentials
    import gspread
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json_str = os.environ['GCP_CREDENTIALS_JSON']
    creds_dict = json.loads(creds_json_str )
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client_gs = gspread.authorize(creds)
    SPREADSHEET_ID = os.environ["sheets_id"]
    sheet = client_gs.open_by_key(SPREADSHEET_ID).sheet1
    records = sheet.get_all_records()

    logging.info("[3/4] Инициализация Telegram Bot...")
    from telegram import Update
    from telegram.ext import Application, MessageHandler, ContextTypes, filters
    TELEGRAM_BOT_TOKEN = os.environ["Telegram_Bot_Token"]
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    logging.info("[4/4] Все модули успешно инициализированы.")

except Exception as e:
    # Записываем любую ошибку при инициализации в лог
    logging.critical(f"!!! КРИТИЧЕСКАЯ ОШИБКА ПРИ ИНИЦИАЛИЗАЦИИ: {e}", exc_info=True)
    raise # Все равно останавливаем приложение, но ошибка будет в файле

# --- Логика бота (без изменений) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... ваш код обработки сообщений ...
    pass # Я временно убрал код, чтобы не загромождать пример

# application.add_handler(...) # Ваш обработчик

# --- Flask-приложение ---
app = Flask(__name__)
@app.route("/")
def home():
    logging.info("Обработан GET-запрос к /")
    return "Сервер работает."

def run_bot():
    try:
        logging.info("Поток для бота: запускаю polling...")
        application.run_polling()
    except Exception as e:
        logging.critical(f"!!! БОТ УПАЛ С ОШИБКОЙ: {e}", exc_info=True)

@app.before_request
def start_bot_thread():
    if not any(t.name == 'telegram_bot_thread' for t in threading.enumerate()):
        logging.info("Поток для бота не найден. Создаю и запускаю.")
        bot_thread = threading.Thread(target=run_bot, name='telegram_bot_thread', daemon=True)
        bot_thread.start()

logging.info("--- Скрипт main.py полностью загружен. Приложение Flask 'app' готово к запуску. ---")

