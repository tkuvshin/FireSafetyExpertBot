import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from openai import OpenAI
import asyncio
from fastapi import FastAPI

# --- 1. Инициализация и настройки (все как у вас) ---
# Инициализация OpenAI
client_gpt = OpenAI(api_key=os.environ["MyKey2"])

# Настройка Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope )
client_gs = gspread.authorize(creds)

SPREADSHEET_ID = os.environ["sheets_id"]
sheet = client_gs.open_by_key(SPREADSHEET_ID).sheet1

# Загрузка данных из таблицы
records = sheet.get_all_records()

# --- 2. Создаем приложение FastAPI СРАЗУ ---
# Это будет основной точкой входа для uvicorn
app = FastAPI()

# --- 3. Настраиваем Telegram-бота ---
# Получаем токен
TELEGRAM_BOT_TOKEN = os.environ["Telegram_Bot_Token"]
# Создаем объект Application, но пока НЕ ЗАПУСКАЕМ его
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# --- 4. Логика обработки сообщений (без изменений) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    print(f"\nПОЛУЧЕН ВОПРОС: {user_message}")

    # Проверяем наличие точного совпадения
    for record in records:
        if record["question"].strip().lower() == user_message.strip().lower():
            print("✅ Найдено точное совпадение в базе")
            await update.message.reply_text(record["answer"])
            return

    # Если точного совпадения нет, отправляем в GPT
    prompt = f"""
Ты-помощник по пожарной безопасности в Российской федерации, пожарный инспектор на вашей стороне
Отвечай развернуто (3-4 предложения) 
Легенда и модель поведения:
Профессионализм и опыт: 
"Я — цифровой ассистент, созданный на основе многолетнего 
опыта действующих инспекторов МЧС и экспертов по пожарной безопасности. 
Моя база знаний включает все актуальные законы, ГОСТы и Своды Правил. 
Я знаю, на что инспектор обращает внимание в первую очередь."
Спокойствие и уверенность: 
В общении бот должен быть не пугающим, а успокаивающим. 
Он не угрожает штрафами, а помогает их избежать. 
Вместо "Если вы это не сделаете, вас оштрафуют на 400 тысяч", он говорит: 
"Чтобы избежать штрафов и обеспечить безопасность, необходимо выполнить три простых шага: первое..., второе..., третье...".
Простота и понятность: Бот избегает сложных терминов. 
Вместо "требования к эвакуационным путям согласно СП 1.13130.2020" он скажет:
 "Проходы к выходу должны быть свободными, шириной не менее 1.2 метра. 
На них нельзя ставить мебель или хранить товары". Ссылку на документ он 
предоставит, но только если это диалог с
 "Профессионалом".
Практическая направленность: Бот всегда ориентирован на действие. 
На вопрос "Что делать?" он дает четкий чек-лист. 
Он может напомнить о сроках (например, "Не забудьте перезарядить огнетушители до конца года").
Эмпатия: Бот должен "понимать" стресс пользователя. 
В диалогах можно использовать фразы вроде: 
"Понимаю, что в этом легко запутаться. Давайте разберемся по порядку", 
"Это частый вопрос, не переживайте. Вот что нужно сделать
.

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

# Добавляем обработчик сообщений в приложение бота
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))


# --- 5. Интеграция бота в жизненный цикл FastAPI ---

@app.on_event("startup")
async def startup_event():
    """Эта функция будет выполнена при старте веб-сервера."""
    # Запускаем инициализацию бота (проверка токена и т.д.)
    await application.initialize()
    # Устанавливаем вебхук (более производительный способ для хостинга)
    # или запускаем polling в фоновом режиме. Для простоты оставим polling.
    
    # Запускаем бота в фоновой задаче, чтобы он не блокировал веб-сервер
    asyncio.create_task(application.run_polling())
    print("🚀 Telegram-бот запущен в фоновом режиме.")

@app.on_event("shutdown")
async def shutdown_event():
    """Эта функция будет выполнена при остановке веб-сервера."""
    await application.stop()
    print("Бот остановлен.")

# --- 6. Роут для проверки работы веб-сервера ---
# Timeweb будет обращаться к этому роуту, чтобы проверить, что ваше приложение работает
@app.get("/")
def read_root():
    return {"status": "Веб-сервер работает, бот запущен в фоновом режиме"}

# Блок if __name__ == "__main__" больше не нужен для деплоя,
# так как uvicorn запускается через Procfile. Можете его удалить или оставить для локальных тестов.

