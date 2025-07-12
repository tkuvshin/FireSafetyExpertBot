import os
import gspread
import threading
import asyncio
import json
from flask import Flask

# --- Обертка для безопасной инициализации ---
try:
    print("--- [1/4] Инициализация OpenAI ---")
    from openai import OpenAI
    client_gpt = OpenAI(api_key=os.environ["MyKey2"])

    print("--- [2/4] Инициализация Google Sheets ---")
    from oauth2client.service_account import ServiceAccountCredentials
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json_str = os.environ['GCP_CREDENTIALS_JSON']
    creds_dict = json.loads(creds_json_str )
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client_gs = gspread.authorize(creds)
    SPREADSHEET_ID = os.environ["sheets_id"]
    sheet = client_gs.open_by_key(SPREADSHEET_ID).sheet1
    records = sheet.get_all_records()

    print("--- [3/4] Инициализация Telegram Bot ---")
    from telegram import Update
    from telegram.ext import Application, MessageHandler, ContextTypes, filters
    TELEGRAM_BOT_TOKEN = os.environ["Telegram_Bot_Token"]
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    print("--- [4/4] Все модули успешно инициализированы ---")

except KeyError as e:
    print(f"!!! КРИТИЧЕСКАЯ ОШИБКА: Переменная окружения не найдена: {e}")
    raise
except Exception as e:
    print(f"!!! КРИТИЧЕСКАЯ ОШИБКА при инициализации: {e}")
    raise

# --- Логика бота (без изменений) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    # ... (весь ваш код для обработки сообщения остается здесь)
    for record in records:
        if record["question"].strip().lower() == user_message.strip().lower():
            await update.message.reply_text(record["answer"])
            return
    prompt = f'...' # Ваш длинный промпт
    response = client_gpt.chat.completions.create(...) # Ваш запрос к GPT
    gpt_answer = response.choices[0].message.content.strip()
    await update.message.reply_text(gpt_answer)

application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# --- Flask-приложение ---
app = Flask(__name__)
@app.route("/")
def home():
    return "Сервер работает. Бот в фоновом режиме."

def run_bot():
    print("Поток для бота: запускаю polling...")
    application.run_polling()

@app.before_request
def start_bot_thread():
    if not any(t.name == 'telegram_bot_thread' for t in threading.enumerate()):
        print("Поток для бота не найден. Создаю и запускаю.")
        bot_thread = threading.Thread(target=run_bot, name='telegram_bot_thread', daemon=True)
        bot_thread.start()

print("--- Скрипт main.py полностью загружен. Приложение Flask 'app' готово к запуску сервером Gunicorn. ---")

