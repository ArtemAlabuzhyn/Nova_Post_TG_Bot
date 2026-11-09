import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from types import SimpleNamespace

import pytest

from nova_post_bot.models.recipient import Recipient
from nova_post_bot.models.recipient_address import RecipientAddress
from nova_post_bot.schemas.shipment import CreatedShipmentInfo


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
def shipment_handler_context():
    with (
        patch("nova_post_bot.handlers.shipment.ShipmentService") as shipment_cls,
        patch("nova_post_bot.handlers.shipment.RecipientService") as recipient_cls,
        patch("nova_post_bot.handlers.shipment.RecipientAddressService") as address_cls,
        patch(
            "nova_post_bot.handlers.shipment.settings.allowed_telegram_ids",
            {123: "Тестовый пользователь"},
        ),
    ):
        shipment_service = shipment_cls.return_value
        recipient_service = recipient_cls.return_value
        address_service = address_cls.return_value
        callback = MagicMock()
        callback.answer = AsyncMock()
        callback.message.answer = AsyncMock()
        callback.message.edit_reply_markup = AsyncMock()
        state = MagicMock()
        state.clear = AsyncMock()
        state.get_data = AsyncMock()
        uow = MagicMock()
        uow.commit = AsyncMock()

        shipment_id = uuid.uuid4()
        recipient_id = uuid.uuid4()
        recipient_address_id = uuid.uuid4()
        state.get_data.return_value = {
            "shipment_id": str(shipment_id),
            "recipient_id": str(recipient_id),
            "recipient_address_id": str(recipient_address_id),
            "requested_by_name": "Test",
            "shipment_type": "documents",
            "sender_city_ref": "sender_city_ref",
            "sender_city_name": "Полтава",
            "sender_warehouse_ref": "sender_warehouse_ref",
            "sender_warehouse_name": "Відділення №4"
        }
        callback.from_user.id = 123

        shipment = MagicMock(
            id=shipment_id,
            recipient_id=recipient_id,
            recipient_address_id=recipient_address_id,
            sender_city_name="Полтава"
        )
        shipment_service.prepare_shipment = AsyncMock(return_value=shipment)
        shipment_service.try_start_creation = AsyncMock(return_value=True)
        shipment_service.mark_created = AsyncMock(return_value=shipment)
        shipment_service.mark_creation_error = AsyncMock()

        recipient = MagicMock(
            id=recipient_id,
            first_name="Test",
            last_name="Test",
            phone="380501111111",

        )
        address = MagicMock(
            id=recipient_address_id,
            recipient_id=recipient_id,
            city_name="Николаев"
        )
        recipient_service.get_by_id = AsyncMock(return_value=recipient)
        address_service.get_by_id = AsyncMock(return_value=address)
        shipment_service.resolve_recipient_refs = AsyncMock(return_value=("recipient_ref", "contact_ref"))
        shipment_service.build_document_properties = MagicMock(
            return_value={"CargoType": "Documents"}
        )

        created_info = CreatedShipmentInfo.model_validate({
            "Ref": "document_ref",
            "IntDocNumber": "20400000000000",
            "CostOnSite": "62.30"
        })
        nova_post_client = MagicMock()
        nova_post_client.create_shipment = AsyncMock(return_value=created_info)
        yield SimpleNamespace(
            callback=callback,
            state=state,
            uow=uow,
            shipment_service=shipment_service,
            recipient_service=recipient_service,
            address_service=address_service,
            nova_post_client=nova_post_client,
            shipment_id=shipment_id,
            created_info=created_info,
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
