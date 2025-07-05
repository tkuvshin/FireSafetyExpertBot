import os
import json
from flask import Flask, request
import telegram
from telegram.ext import Dispatcher, MessageHandler, filters
from openai import OpenAI
import gspread
from google.oauth2.service_account import Credentials

# OpenAI
client_gpt = OpenAI(api_key=os.environ["MyKey2"])

# Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.environ["GOOGLE_CREDS_JSON"]
creds_dict = json.loads(creds_json)
credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
client_gs = gspread.authorize(credentials)
SPREADSHEET_ID = os.environ["sheets_id"]
sheet = client_gs.open_by_key(SPREADSHEET_ID).sheet1
records = sheet.get_all_records()

# Flask
app = Flask(__name__)

# Telegram
bot = telegram.Bot(token=os.environ["Telegram_Bot_Token"])
dispatcher = Dispatcher(bot, None, workers=0)

# Обработка сообщений
def handle_message(update, context):
    user_message = update.message.text.strip()
    print(f"ПОЛУЧЕН ВОПРОС: {user_message}")

    for record in records:
        if record["question"].strip().lower() == user_message.lower():
            print("✅ Найдено точное совпадение в базе")
            update.message.reply_text(record["answer"])
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
    update.message.reply_text(gpt_answer)

dispatcher.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# Webhook
@app.route("/", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# Запуск сервера
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
