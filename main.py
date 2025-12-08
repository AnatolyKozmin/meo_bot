import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from database import init_db
from handlers import user_router, admin_router


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Точка входа."""
    # Проверяем токен
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не указан! Создайте .env файл с токеном.")
        return
    
    # Инициализируем базу данных
    await init_db()
    logger.info("База данных инициализирована")
    
    # Создаём бота и диспетчер
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрируем роутеры
    dp.include_router(admin_router)  # Админ роутер первый для приоритета
    dp.include_router(user_router)
    
    # Запускаем бота
    logger.info("Бот запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

