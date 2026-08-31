from unittest.mock import AsyncMock, MagicMock

import pytest

from nova_post_bot.handlers.fallback import fallback_handler


@pytest.mark.asyncio
async def test_fallback_handler():
    message = MagicMock()
    message.answer = AsyncMock()
    await fallback_handler(message=message)

    message.answer.assert_awaited_once_with("Неизвестная команда. Используй /help")
