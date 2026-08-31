import datetime

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from nova_post_bot.db.uow import UnitOfWork
from nova_post_bot.models.user import User
from nova_post_bot.keyboards.main_menu import main_menu

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message, uow: UnitOfWork):
    tg_user = message.from_user
    user = await uow.users.get_by_telegram_id(tg_user.id)
    now = datetime.datetime.now(datetime.UTC)

    if user is None:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_activity_at=now
        )
        await uow.users.add_user(user)
    else:
        await uow.users.update_user(user=user,
                                    username=tg_user.username,
                                    first_name=tg_user.first_name,
                                    last_activity_at=now)
    await uow.commit()
    await message.answer(f"Hello, {tg_user.first_name}!", reply_markup=main_menu)