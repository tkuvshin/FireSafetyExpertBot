import os
import threading
import asyncio
import json
import logging
import base64  # <--- ДОБАВЛЕН ВАЖНЫЙ ИМПОРТ
from flask import Flask

# --- Настройка логирования (без изменений) ---
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

logging.info("--- СКРИПТ НАЧАЛ ВЫПОЛНЯТЬСЯ ---")

# --- Безопасная инициализация с логированием ---
try:
    logging.info("[1/4] Инициализация OpenAI...")
    from openai import OpenAI
    client_gpt = OpenAI(api_key=os.environ["MyKey2"])

    # --- [ИЗМЕНЕНО] Блок инициализации Google Sheets ---
    logging.info("[2/4] Инициализация Google Sheets...")
    from oauth2client.service_account import ServiceAccountCredentials
    import gspread
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    # 1. Получаем безопасную Base64-строку из переменной окружения
    base64_creds_str = os.environ['GCP_CREDENTIALS_JSON']
    logging.info("Переменная GCP_CREDENTIALS_JSON (Base64 ) получена.")

    # 2. Декодируем ее обратно в обычную JSON-строку
    creds_json_str_decoded = base64.b64decode(base64_creds_str).decode('utf-8')
    logging.info("Строка успешно декодирована из Base64.")

    # 3. Превращаем строку в JSON-объект
    creds_dict = json.loads(creds_json_str_decoded)
    logging.info("Строка успешно преобразована в JSON-объект.")

    # 4. Авторизуемся, используя словарь
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client_gs = gspread.authorize(creds)
    SPREADSHEET_ID = os.environ["sheets_id"]
    sheet = client_gs.open_by_key(SPREADSHEET_ID).sheet1
    records = sheet.get_all_records()
    logging.info("Авторизация в Google Sheets прошла успешно.")
    # --- КОНЕЦ ИЗМЕНЕННОГО БЛОКА ---

    logging.info("[3/4] Инициализация Telegram Bot...")
    from telegram import Update
    from telegram.ext import Application, MessageHandler, ContextTypes, filters
    TELEGRAM_BOT_TOKEN = os.environ["Telegram_Bot_Token"]
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    logging.info("[4/4] Все модули успешно инициализированы.")

except Exception as e:
    logging.critical(f"!!! КРИТИЧЕСКАЯ ОШИБКА ПРИ ИНИЦИАЛИЗАЦИИ: {e}", exc_info=True)
    raise

# --- [ВОЗВРАЩЕНО] Логика бота ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    logging.info(f"Получен вопрос: {user_message}")

    for record in records:
        if record["question"].strip().lower() == user_message.strip().lower():
            logging.info("Найдено точное совпадение в базе.")
            await update.message.reply_text(record["answer"])
            return

    prompt = f"""
Ты-помощник по пожарной безопасности в Российской федерации, пожарный инспектор на вашей стороне
Отвечай развернуто (3-4 предложения)
... (весь ваш длинный промпт) ...
Вопрос пользователя: "{user_message}"
Ответ:
"""
    logging.info("Отправляем запрос в GPT...")
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
    logging.info(f"Получен ответ от GPT.")
    await update.message.reply_text(gpt_answer)

# [ВОЗВРАЩЕНО] Добавляем обработчик сообщений
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# --- Flask-приложение (без изменений) ---
app = Flask(__name__)
@app.route("/")
def home():
    logging.info("Обработан GET-запрос к /")
    return "Сервер работает. Бот запущен в фоновом режиме."

def run_bot():
    """
    Эта функция запускается в отдельном потоке.
    Она создает новый цикл событий asyncio для этого потока
    и запускает в нем бота с отключенной обработкой сигналов.
    """
    try:
        logging.info("Поток для бота: создаю новый цикл событий asyncio...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        logging.info("Поток для бота: запускаю polling с отключенными сигналами...")
        # 1. Запускаем бота, сказав ему не слушать системные сигналы.
        # Это решает ошибку "set_wakeup_fd only works in main thread".
        application.run_polling(stop_signals=None)

    except Exception as e:
        logging.critical(f"!!! БОТ УПАЛ С ОШИБКОЙ: {e}", exc_info=True)

    except Exception as e:
        logging.critical(f"!!! БОТ УПАЛ С ОШИБКОЙ: {e}", exc_info=True)

@app.before_request
def start_bot_thread():
    if not any(t.name == 'telegram_bot_thread' for t in threading.enumerate()):
        logging.info("Поток для бота не найден. Создаю и запускаю.")
        bot_thread = threading.Thread(target=run_bot, name='telegram_bot_thread', daemon=True)
        bot_thread.start()

logging.info("--- Скрипт main.py полностью загружен. Приложение Flask 'app' готово к запуску. ---")
