from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from nova_post_bot.db.uow import UnitOfWork


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(self,
                      handle: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
                      event: TelegramObject,
                      data: dict[str, Any]) -> Any:
        async with UnitOfWork() as uow:
            data['uow'] = uow
            return await handle(event, data)