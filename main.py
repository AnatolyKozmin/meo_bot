import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, API_PORT
from database import init_db
from handlers import user_router, admin_router
from api import create_app


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
    
    # Создаём API сервер
    api_app = create_app()
    runner = web.AppRunner(api_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", API_PORT)
    await site.start()
    logger.info(f"API сервер запущен на порту {API_PORT}")
    
    # Запускаем бота
    logger.info("Бот запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
