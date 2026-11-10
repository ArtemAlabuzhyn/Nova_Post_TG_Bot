from unittest.mock import MagicMock, AsyncMock

import pytest

from nova_post_bot.services.shipment import ShipmentService


@pytest.mark.asyncio
async def test_get_recipient_contact_ref_finds_contact_on_second_page():
    client = MagicMock()
    client.get_counterparty_contact_persons = AsyncMock(
        side_effect=[
            [{"Phones": "380501111111", "Ref": "other-ref", "FirstName": "Іван", "LastName": "Петренченко"}],
            [{"Phones": "380501111111", "Ref": "target-ref", "FirstName": "Іван", "LastName": "Петренко"}],
            []
        ]
    )
    shipment_service = ShipmentService(uow=MagicMock())
    result = await shipment_service.get_recipient_contact_ref(client, recipient_ref="test-ref",
                                                              recipient_phone="380501111111",
                                                              first_name="Іван", last_name="Петренко")
    assert result == "target-ref"


@pytest.mark.asyncio
async def test_get_recipient_contact_ref_rejects_ambiguous_phone():
    client = MagicMock()
    client.get_counterparty_contact_persons = AsyncMock(
        side_effect=[
            [{"Phones": "380501111111", "Ref": "first-ref", "FirstName": "Іван", "LastName": "Петренко"}],
            [{"Phones": "380501111111", "Ref": "second-ref", "FirstName": "Іван", "LastName": "Петренко"}],
            []
        ]
    )
    shipment_service = ShipmentService(uow=MagicMock())
    with pytest.raises(ValueError, match="Multiple Nova Post contacts"):
        await shipment_service.get_recipient_contact_ref(client, recipient_ref="test-ref",
                                                         recipient_phone="380501111111",
                                                         first_name="Іван", last_name="Петренко")

def test_find_recipient_contact_ref():
    shipment_service = ShipmentService(uow=MagicMock())
    contacts = [
        {
            "Phones": "380501111111",
            "Ref": "contact-ref",
            "FirstName": "Іван",
            "LastName": "Петренко",
        }
    ]
    result = shipment_service.find_recipient_contact_ref(
        contacts=contacts, recipient_phone="380501111111",
        first_name="Іван", last_name="Іваненко"
    )
    assert result is None