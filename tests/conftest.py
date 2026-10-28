import uuid
from unittest.mock import MagicMock, AsyncMock

import pytest

from nova_post_bot.models.recipient import Recipient
from nova_post_bot.models.recipient_address import RecipientAddress


@pytest.fixture
def recipient_uow():
    uow = MagicMock()
    uow.recipients.find_duplicate = AsyncMock(return_value=None)
    uow.recipients.get_by_id = AsyncMock(return_value=None)
    uow.recipients.add_recipient = AsyncMock()
    uow.recipient_audit.add_audit = AsyncMock()
    uow.rollback = AsyncMock()
    return uow


@pytest.fixture
def existing_recipient():
    return Recipient(
        id=uuid.uuid4(),
        first_name="John",
        last_name="Doe",
        phone="380671234567",
        created_by_telegram_id=123,
        created_by_name="Original Author",
        is_active=True,
    )


@pytest.fixture
def address_uow(recipient_uow):
    recipient_uow.recipient_addresses.get_by_id = AsyncMock(return_value=None)
    recipient_uow.recipient_addresses.get_by_location = AsyncMock(return_value=None)
    recipient_uow.recipient_addresses.add_address = AsyncMock()
    recipient_uow.recipient_addresses.list_by_recipient_id = AsyncMock(return_value=[])
    return recipient_uow


@pytest.fixture
def existing_address(existing_recipient):
    return RecipientAddress(
        id=uuid.uuid4(),
        recipient_id=existing_recipient.id,
        label="Возле дома",
        city_ref="test-city-ref",
        city_name="Полтава",
        warehouse_ref="test-warehouse-ref",
        warehouse_name="Відділення №5",
        is_active=True,
    )
