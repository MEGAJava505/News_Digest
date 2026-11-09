# bot.py
# Telegram бот для отправки новостной рассылки kun.uz
# Отправьте "О" или "о" чтобы запустить рассылку

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Импортируем main() из нашего скрипта рассылки
from main import main as send_newsletter

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ─────────────────────────────────────────────
# Команда /start
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! Men kun.uz yangiliklar botiman.\n\n"
        "Buyruqlar:\n"
        "  О — Yangiliklar jo'natish\n"
        "  /start — Boshlash\n"
        "  /status — Holat tekshirish\n\n"
        "\"О\" harfini yuboring va men barcha foydalanuvchilarga "
        "yangiliklar jo'nataman!"
    )


# ─────────────────────────────────────────────
# Команда /status
# ─────────────────────────────────────────────
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = os.getenv("SENDER_EMAIL", "???")
    await update.message.reply_text(
        f"Bot ishlayapti!\n"
        f"Email: {sender}\n"
        f"Manba: kun.uz\n"
        f"Tayyor — \"О\" yuboring!"
    )


# ─────────────────────────────────────────────
# Обработка сообщения "О"
# ─────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Проверяем: "О", "о", "O", "o" (кириллица и латиница)
    if text.lower() in ("о", "o"):
        await update.message.reply_text(
            "Yangiliklar jo'natish boshlandi...\n"
            "Iltimos, kuting..."
        )

        try:
            # Запускаем рассылку
            result = send_newsletter()
            await update.message.reply_text(
                "Tayyor! Yangiliklar muvaffaqiyatli jo'natildi!\n"
                "Emaillarni tekshiring."
            )
        except Exception as e:
            await update.message.reply_text(
                f"Xatolik yuz berdi:\n{str(e)}"
            )
    else:
        await update.message.reply_text(
            "Noto'g'ri buyruq.\n"
            "Yangiliklar jo'natish uchun \"О\" yuboring."
        )


import socket
import sys

# Глобальная переменная для удержания порта
_instance_socket = None

def enforce_single_instance():
    """Проверяет, не запущен ли уже бот, занимая локальный порт."""
    global _instance_socket
    _instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Пытаемся занять порт. Если он занят — бот уже запущен.
        _instance_socket.bind(("127.0.0.1", 54321))
    except socket.error:
        print("\n[XATO] Bot allaqachon ishga tushirilgan! Iltimos, boshqa terminal yoki fondagi botni yoping.\n")
        sys.exit(1)

# ─────────────────────────────────────────────
# Запуск бота
# ─────────────────────────────────────────────
def run_bot():
    # Защита от двойного запуска
    enforce_single_instance()
    
    token = os.getenv("TG_BOT_TOKEN")
    if not token:
        print("[XATO] TG_BOT_TOKEN .env faylida topilmadi!")
        return

    print("=" * 50)
    print("  KUN.UZ NEWSLETTER BOT")
    print("=" * 50)
    print(f"  Bot: @megajava505_bot")
    print(f"  Buyruq: О — jo'natish")
    print(f"  Bot ishga tushdi... (Ctrl+C to'xtatish)")
    print("=" * 50)

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    run_bot()
