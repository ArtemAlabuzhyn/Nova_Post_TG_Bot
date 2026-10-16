from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

class AccessMiddleware(BaseMiddleware):

    def __init__(self, allowed_telegram_ids: set[int]):
        self.allowed_telegram_ids = allowed_telegram_ids

    async def __call__(self,
                       handle: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject,
                       data: dict[str, Any]) -> Any:
        user = data.get('event_from_user')
        if user is None or user.id not in self.allowed_telegram_ids:
            if isinstance(event, Update) and event.message is not None:
                await event.message.answer("Bot only for testers")
                if user is not None:
                    await event.message.answer(f'Your TG ID is {user.id}')
            return
        return await handle(event, data)