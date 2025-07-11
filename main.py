import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import OpenAI
from flask import Flask
import threading
import asyncio

# --- 1. Инициализация и настройки ---
# OpenAI
client_gpt = OpenAI(api_key=os.environ["MyKey2"])

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client_gs = gspread.authorize(creds)

SPREADSHEET_ID = os.environ["sheets_id"]
sheet = client_gs.open_by_key(SPREADSHEET_ID).sheet1
records = sheet.get_all_records()

# Telegram
TELEGRAM_BOT_TOKEN = os.environ["Telegram_Bot_Token"]
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# --- 2. Логика обработки сообщений ---
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

# --- 3. Flask-приложение для обхода ошибки порта ---
app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ Flask работает, бот запущен в фоне."

# --- 4. Запуск бота в отдельном потоке ---
def run_bot():
    asyncio.run(application.initialize())
    asyncio.run(application.start())
    print("🚀 Бот запущен.")
    asyncio.run(application.run_polling())

# --- 5. Запуск Flask ---
if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    threading.Thread(target=run_bot).start()
    
    # Запускаем Flask на порту из переменной окружения (Timeweb)
    port = int(os.environ.get("PORT", 8000))
    flask_app.run(host="0.0.0.0", port=port)


