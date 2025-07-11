import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import OpenAI
from flask import Flask
import threading
import asyncio

# --- 1. Инициализация и настройки (без изменений) ---
# OpenAI
client_gpt = OpenAI(api_key=os.environ["MyKey2"])

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope )
client_gs = gspread.authorize(creds)

SPREADSHEET_ID = os.environ["sheets_id"]
sheet = client_gs.open_by_key(SPREADSHEET_ID).sheet1
records = sheet.get_all_records()

# Telegram
TELEGRAM_BOT_TOKEN = os.environ["Telegram_Bot_Token"]
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# --- 2. Логика обработки сообщений (без изменений) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    print(f"\nПОЛУЧЕН ВОПРОС: {user_message}")

    # Проверяем наличие точного совпадения
    for record in records:
        if record["question"].strip().lower() == user_message.strip().lower():
            print("✅ Найдено точное совпадение в базе")
            await update.message.reply_text(record["answer"])
            return

    # GPT
    prompt = f"""
Ты-помощник по пожарной безопасности в Российской федерации, пожарный инспектор на вашей стороне...
Вопрос пользователя: "{user_message}"
Ответ:
"""
    print("🔄 Отправляем запрос в GPT...")
    response = client_gpt.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты профессиональный консультант по пожарной безопасности."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.3
    )
    gpt_answer = response.choices[0].message.content.strip()
    print(f"✅ ОТВЕТ GPT: {gpt_answer[:300]}...")
    await update.message.reply_text(gpt_answer)

application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# --- 3. Flask-приложение ---
# ИСПРАВЛЕНО: Создаем приложение Flask и используем ОДНО И ТО ЖЕ имя переменной `app`
app = Flask(__name__)

@app.route("/")
def home():
    # Этот роут нужен, чтобы хостинг мог проверить, что веб-сервер работает
    return "Flask-сервер работает. Бот запущен в фоновом режиме."

# --- 4. Функция для запуска бота ---
# ИСПРАВЛЕНО: Упрощенная и корректная функция запуска бота
def run_bot():
    # Создаем новый цикл событий для потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    print("🚀 Запускаю polling телеграм-бота...")
    # run_polling сам выполняет initialize и start
    application.run_polling()
    print("Бот остановлен.")

# --- 5. Запуск бота в отдельном потоке ПЕРЕД первым запросом ---
# Это специальная конструкция Flask, которая гарантирует, что бот запустится
# один раз при старте производственного сервера (например, Gunicorn)
@app.before_request
def start_bot_thread():
    # Проверяем, запущен ли уже поток, чтобы не создавать дубликаты
    if not any(t.name == 'telegram_bot_thread' for t in threading.enumerate()):
        print("Создаю и запускаю поток для бота...")
        bot_thread = threading.Thread(target=run_bot, name='telegram_bot_thread', daemon=True)
        bot_thread.start()

# Блок if __name__ == "__main__" используется ТОЛЬКО для локального тестирования на вашем компьютере.
# На сервере Timeweb он выполняться НЕ БУДЕТ.
if __name__ == "__main__":
    print("Запуск в режиме локальной разработки...")
    # Запускаем Flask со встроенным сервером, который не подходит для хостинга
    app.run(host="0.0.0.0", port=8000, debug=True)


