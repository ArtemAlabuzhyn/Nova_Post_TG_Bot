from unittest.mock import MagicMock, AsyncMock

import pytest

from nova_post_bot.core.exceptions import NovaPostValidationError
from nova_post_bot.services.tracking import TrackingService


@pytest.mark.asyncio
async def test_validation_tracking():

    nova_post_client = MagicMock()
    nova_post_client.get_tracking_info = AsyncMock()
    tracking_service = TrackingService(nova_post_client=nova_post_client)

    with pytest.raises(NovaPostValidationError):
        await tracking_service.get_tracking_info(number="abc")

    nova_post_client.get_tracking_info.assert_not_awaited()

@pytest.mark.asyncio
async def test_tracking_strips():
    nova_post_client = MagicMock()
    nova_post_client.get_tracking_info = AsyncMock(return_value=[])
    tracking_service = TrackingService(nova_post_client=nova_post_client)
    result = await tracking_service.get_tracking_info(number="  20451562251482  ")
    nova_post_client.get_tracking_info.assert_awaited_once_with(number="20451562251482")
    assert result == []

