
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from openai import OpenAI
from rapidfuzz import fuzz
from flask import Flask, request

app = Flask(__name__)

# Инициализация OpenAI
client_gpt = OpenAI(api_key=os.environ["MyKey2"])

# Настройка Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client_gs = gspread.authorize(creds)

SPREADSHEET_ID = os.environ["sheets_id"]
sheet = client_gs.open_by_key(SPREADSHEET_ID).sheet1
records = sheet.get_all_records()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    print(f"\nПОЛУЧЕН ВОПРОС: {user_message}")

    max_score = 0
    best_answer = None

    for record in records:
        score = fuzz.token_set_ratio(user_message.lower(), record["question"].lower())
        if score > max_score:
            max_score = score
            best_answer = record["answer"]

    if max_score >= 70:
        print(f"✅ Найдено похожее совпадение в базе, score={max_score}")
        await update.message.reply_text(best_answer)
        return

    prompt = f"""
Ты — помощник по пожарной безопасности в РФ. Отвечай развернуто (3-4 предложения), с ссылками на применимые ФЗ, ГОСТ, СНиП, ППБ, если это уместно. Пиши понятно, деловым языком.

Вопрос пользователя: "{user_message}"

Ответ:
"""

    print("🔄 Отправляем запрос в GPT для генерации ответа...")

    response = client_gpt.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "Ты профессиональный консультант по пожарной безопасности."},
                  {"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.3
    )

    gpt_answer = response.choices[0].message.content.strip()
    print(f"✅ ОТВЕТ GPT: {gpt_answer[:300]}...")

    await update.message.reply_text(gpt_answer)

async def main():
    TELEGRAM_BOT_TOKEN = os.environ["Telegram_Bot_Token"]
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("🚀 Бот запущен и готов к работе.")
    await application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=os.environ["WEBHOOK_URL"]
    )

if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
