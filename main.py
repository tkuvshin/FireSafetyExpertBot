import os
from flask import Flask, request
import telegram
from telegram.ext import Dispatcher, MessageHandler, filters
from openai import OpenAI

# Инициализация OpenAI
client_gpt = OpenAI(api_key=os.environ["MyKey2"])

# Инициализация Flask
app = Flask(__name__)

# Инициализация Telegram
bot = telegram.Bot(token=os.environ["Telegram_Bot_Token"])
dispatcher = Dispatcher(bot, None, workers=0)

# Обработчик сообщений
def handle_message(update, context):
    user_message = update.message.text.strip()
    print(f"ПОЛУЧЕН ВОПРОС: {user_message}")

    prompt = f"""
Ты — помощник по пожарной безопасности в РФ. Отвечай развернуто (3-4 предложения), с ссылками на применимые ФЗ, ГОСТ, СНиП, ППБ, если это уместно. Пиши понятно, деловым языком.

Вопрос пользователя: "{user_message}"

Ответ:
"""
    print("🔄 Отправляем запрос в GPT для генерации ответа...")

    response = client_gpt.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Ты профессиональный консультант по пожарной безопасности."},
                  {"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.3
    )
    gpt_answer = response.choices[0].message.content.strip()
    print(f"✅ ОТВЕТ GPT: {gpt_answer[:300]}...")
    update.message.reply_text(gpt_answer)

dispatcher.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# Flask route для webhook
@app.route("/", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# Установка webhook при запуске
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    webhook_url = os.environ.get("WEBHOOK_URL")

    if webhook_url:
        bot.set_webhook(url=webhook_url)
        print(f"Webhook установлен: {webhook_url}")
    else:
        print("⚠️ WEBHOOK_URL не установлен в переменных окружения")

    app.run(host="0.0.0.0", port=port)

