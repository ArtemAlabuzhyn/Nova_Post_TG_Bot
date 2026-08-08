import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from nova_post_bot.config import settings

bot = Bot(token=settings.telegram_bot_token)

dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer('Bot is working')

async def main():
    logging.basicConfig(level=settings.log_level)
    logging.info('Bot started')
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('Bot stopped')