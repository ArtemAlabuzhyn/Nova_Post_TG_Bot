from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from nova_post_bot.clients.nova_post import NovaPostClient
from nova_post_bot.core.exceptions import NovaPostValidationError, NovaPostTimeoutError, NovaPostAPIError, \
    NovaPostUnexpectedResponseError
from nova_post_bot.schemas.tracking import TrackingInfo


@pytest.mark.asyncio
async def test_tracking_reject_blank_number():
    client = NovaPostClient(api_key="test_key", base_url="https://example.com/", timeout=10)

    client.http_client.post = AsyncMock()

    try:
        with pytest.raises(NovaPostValidationError):
            await client.get_tracking_info(number=" ")

        client.http_client.post.assert_not_awaited()
    finally:
        await client.close()

@pytest.mark.asyncio
async def test_tracking_success():
    client = NovaPostClient(api_key="test_key", base_url="https://example.com/", timeout=10)

    response = MagicMock()
    response.json.return_value = {
        "success": True,
        "data": [
            {"Number": "20400000000000", "Status": "В пути"}
        ]
    }
    client.http_client.post = AsyncMock(return_value=response)
    try:
        result = await client.get_tracking_info(number="20400000000000")
        assert len(result) == 1
        assert isinstance(result[0], TrackingInfo)
        assert result[0].number == "20400000000000"
        assert result[0].status == "В пути"
        client.http_client.post.assert_awaited_once()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_tracking_timeout():
    client = NovaPostClient(api_key="test_key", base_url="https://example.com/", timeout=10)
    client.http_client.post = AsyncMock(side_effect=httpx.ReadTimeout("Test timeout"))

    try:
        with pytest.raises(NovaPostTimeoutError):
            await client.get_tracking_info(number="20400000000000")
        client.http_client.post.assert_awaited_once()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_tracking_empty_result():
    client = NovaPostClient(api_key="test_key", base_url="https://example.com/", timeout=10)

    response = MagicMock()
    response.json.return_value = {
        "success": True,
        "data": []
    }
    client.http_client.post = AsyncMock(return_value=response)
    try:
        result = await client.get_tracking_info(number="20400000000000")
        assert result == []
        client.http_client.post.assert_awaited_once()
    finally:
        await client.close()

@pytest.mark.asyncio
async def test_tracking_http_error():
    client = NovaPostClient(api_key="test_key", base_url="https://example.com/", timeout=10)
    request = httpx.Request("POST", "https://example.com/")
    response = httpx.Response(500, request=request)

    client.http_client.post = AsyncMock(return_value=response)
    try:
        with pytest.raises(NovaPostAPIError, match="HTTP 500"):
            await client.get_tracking_info(number="20400000000000")
        client.http_client.post.assert_awaited_once()
    finally:
        await client.close()

@pytest.mark.asyncio
async def test_tracking_invalid_response():
    client = NovaPostClient(api_key="test_key", base_url="https://example.com/", timeout=10)

    response = MagicMock()
    response.json.return_value = {
        "success": True,
        "data": [
            {"Number": "20400000000000"}
        ]
    }
    client.http_client.post = AsyncMock(return_value=response)

    try:
        with pytest.raises(NovaPostUnexpectedResponseError, match="Invalid tracking response"):
            await client.get_tracking_info(number="20400000000000")
        client.http_client.post.assert_awaited_once()
    finally:
        await client.close()
