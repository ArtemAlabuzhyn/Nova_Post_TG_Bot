from unittest.mock import AsyncMock, MagicMock

import pytest

from nova_post_bot.handlers.start import start_handler


@pytest.mark.asyncio
async def test_start_creates_new_user():
    message = MagicMock()
    message.from_user.id = 123456
    message.from_user.username = 'testuser'
    message.from_user.first_name = 'test'
    message.answer = AsyncMock()

    uow = MagicMock()
    uow.users.get_by_telegram_id = AsyncMock(return_value=None)
    uow.users.add_user = AsyncMock()
    uow.commit = AsyncMock()

    await start_handler(message=message, uow=uow)
    uow.users.add_user.assert_awaited_once()

    create_user = uow.users.add_user.await_args.args[0]
    assert create_user.telegram_id == 123456
    assert create_user.username == 'testuser'
    assert create_user.first_name == 'test'
    assert create_user.last_activity_at is not None

    uow.users.get_by_telegram_id.assert_awaited_once_with(123456)
    uow.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_start_updates_existing_user():
    message = MagicMock()
    message.from_user.id = 123456
    message.from_user.username = 'testuser'
    message.from_user.first_name = 'test'
    message.answer = AsyncMock()

    existing_user = MagicMock()
    uow = MagicMock()
    uow.users.update_user = AsyncMock()
    uow.users.get_by_telegram_id = AsyncMock(return_value=existing_user)
    uow.users.add_user = AsyncMock()
    uow.commit = AsyncMock()

    await start_handler(message=message, uow=uow)

    uow.users.get_by_telegram_id.assert_awaited_once_with(123456)
    uow.users.add_user.assert_not_awaited()
    uow.users.update_user.assert_awaited_once()
    uow.commit.assert_awaited_once()

    update_call = uow.users.update_user.await_args
    assert update_call.kwargs['user'] == existing_user
    assert update_call.kwargs['username'] == 'testuser'
    assert update_call.kwargs['first_name'] == 'test'
    assert update_call.kwargs['last_activity_at'] is not None