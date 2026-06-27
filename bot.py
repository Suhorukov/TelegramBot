import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()

DOG_API_URL = "https://dog.ceo/api/breeds/image/random"
SHOW_DOG_BUTTON = "Show me a photo of a dog"

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "bot.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(SHOW_DOG_BUTTON)]],
        resize_keyboard=True,
    )


async def fetch_random_dog_image() -> str:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(DOG_API_URL)
        response.raise_for_status()
        data = response.json()

    if data.get("status") != "success":
        raise ValueError("Dog API returned unsuccessful status")

    image_url = data.get("message")
    if not image_url:
        raise ValueError("Dog API returned empty image URL")

    return image_url


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("Команда /start от user_id=%s", user.id)
    await update.effective_message.reply_text(
        f"Hi, {user.first_name}! 🐶\nPress the button to get a random dog photo.",
        reply_markup=main_keyboard(),
    )


async def show_dog_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("Запрос фото собаки от user_id=%s", user.id)

    try:
        image_url = await fetch_random_dog_image()
    except Exception:
        logger.exception("Ошибка при запросе к Dog API")
        await update.effective_message.reply_text(
            "Could not load a dog photo. Please try again."
        )
        return

    await update.effective_message.reply_photo(photo=image_url, caption="🐶 Random dog!")


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN не найден в .env")
        raise SystemExit("Set BOT_TOKEN in .env file")

    logger.info("Инициализация бота, лог-файл: %s", LOG_FILE)

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.Regex(f"^{SHOW_DOG_BUTTON}$"), show_dog_photo)
    )

    logger.info("Бот запущен, ожидание сообщений...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
