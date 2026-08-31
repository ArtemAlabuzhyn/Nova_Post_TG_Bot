from unittest.mock import AsyncMock, MagicMock

import pytest

from nova_post_bot.handlers.menu import menu_handler


@pytest.mark.asyncio
async def test_menu_handler():
    message = MagicMock()
    message.answer = AsyncMock()
    await menu_handler(message=message)

    message.answer.assert_awaited_once_with("Function coming soon")