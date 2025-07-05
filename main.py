import os
import json
import asyncio
from flask import Flask, request
import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials

# Инициализация OpenAI
client_gpt = OpenAI(api_key=os.environ["MyKey2"])

# Настройка Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.environ["GOOGLE_CREDS_JSON"]
creds_dict = json.loads(creds_json)
credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
client_gs = gspread.authorize(credentials)
SPREADSHEET_ID = os.environ["sheets_id"]
sheet = client_gs.open_by_key(SPREADSHEET_ID).sheet1

# Flask
app = Flask(__name__)

# Telegram Application
bot_token = os.environ["Telegram_Bot_Token"]
application = ApplicationBuilder().token(bot_token).build()

# Асинхронный обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    print(f"ПОЛУЧЕН ВОПРОС: {user_message}")

    records = sheet.get_all_records()

    for record in records:
        if record["question"].strip().lower() == user_message.lower():
            print("✅ Найдено точное совпадение в базе")
            await update.message.reply_text(record["answer"])
            return

    prompt = f"""
Ты — помощник по пожарной безопасности в РФ. Отвечай развернуто (3-4 предложения), с ссылками на применимые ФЗ, ГОСТ, СНиП, ППБ, если это уместно. Пиши понятно, деловым языком.

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
    print(f"✅ ОТВЕТ GPT: {gpt_answer[:200]}...")
    await update.message.reply_text(gpt_answer)

# Регистрируем обработчик
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# Webhook для Telegram через Flask
@app.route("/", methods=["POST"])
async def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"

# Запуск бота и Flask
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.create_task(application.initialize())
    loop.create_task(application.start())
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

