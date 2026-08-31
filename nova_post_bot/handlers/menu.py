from aiogram import F, Router
from aiogram.types import Message

router = Router()

@router.message(F.text.in_([
    "Отследить ТТН",
    "Мои отправки",
    "Создать накладную"]))
async def menu_handler(message: Message):
    await message.answer("Function coming soon")
