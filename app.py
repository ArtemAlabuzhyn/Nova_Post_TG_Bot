import asyncio
import logging

from aiogram import Bot, Dispatcher

from nova_post_bot.core.config import settings
from nova_post_bot.core.exception_handlers import global_exception_handler
from nova_post_bot.handlers.start import router as start_router
from nova_post_bot.handlers.help import router as help_router
from nova_post_bot.handlers.menu import router as menu_router
from nova_post_bot.middlewares.db import DatabaseMiddleware
from nova_post_bot.handlers.fallback import router as fallback_router

bot = Bot(token=settings.telegram_bot_token)

dp = Dispatcher()
dp.update.outer_middleware(DatabaseMiddleware())
dp.errors.register(global_exception_handler)

dp.include_router(start_router)
dp.include_router(help_router)
dp.include_router(menu_router)
dp.include_router(fallback_router)



async def main():
    logging.basicConfig(level=settings.log_level)
    logging.info('Bot started')
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('Bot stopped')