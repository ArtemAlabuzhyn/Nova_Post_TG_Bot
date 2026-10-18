from unittest.mock import AsyncMock, MagicMock

import pytest

from nova_post_bot.core.exceptions import NovaPostTimeoutError
from nova_post_bot.handlers.tracking import process_tracking_number


@pytest.mark.asyncio
async def test_tracking_timeout_state():
    message = MagicMock()
    message.text = "20451562251482"
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    tracking_service = MagicMock()
    tracking_service.get_tracking_info = AsyncMock(side_effect=NovaPostTimeoutError("Test timeout"))

    await process_tracking_number(message=message, state=state, tracking_service=tracking_service)

    message.answer.assert_awaited_once_with("НП в данный момент не отвечает. Попробуйте позже.")
    state.clear.assert_not_awaited()


