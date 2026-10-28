import uuid

import pytest

from nova_post_bot.core.exceptions import ObjectAlreadyExistsError, ObjectNotFoundError
from nova_post_bot.enums.recipient_audit import SaveStatus, RecipientAuditAction
from nova_post_bot.services.recipient_address import RecipientAddressService


@pytest.mark.asyncio
async def test_add_address_returns_existing_active_address(address_uow,
                                                           existing_recipient,
                                                           existing_address):
    address_uow.recipients.get_by_id.return_value = existing_recipient
    address_uow.recipient_addresses.get_by_location.return_value = existing_address

    address_service = RecipientAddressService(uow=address_uow)
    address, save_status = await address_service.add_address(recipient_id=existing_recipient.id,
                                                             label="Новое название",
                                                             city_ref="test-city-ref",
                                                             city_name="Полтава",
                                                             warehouse_ref="test-warehouse-ref",
                                                             warehouse_name="Відділення №5",
                                                             actor_telegram_id=123,
                                                             actor_name="Test Actor",
                                                             )
    assert address is existing_address
    assert save_status == SaveStatus.EXISTING
    assert address.label == "Возле дома"

    address_uow.recipient_addresses.get_by_location.assert_awaited_once_with(
        recipient_id=existing_recipient.id,
        city_ref="test-city-ref",
        warehouse_ref="test-warehouse-ref",
    )

    address_uow.recipient_addresses.add_address.assert_not_awaited()
    address_uow.recipient_audit.add_audit.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_address_restores_archived_address(address_uow,
                                                     existing_recipient,
                                                     existing_address):
    existing_address.is_active = False
    address_uow.recipients.get_by_id.return_value = existing_recipient
    address_uow.recipient_addresses.get_by_location.return_value = existing_address

    address_service = RecipientAddressService(uow=address_uow)
    address, save_status = await address_service.add_address(recipient_id=existing_recipient.id,
                                                             label="Новое название",
                                                             city_ref="test-city-ref",
                                                             city_name="Полтава",
                                                             warehouse_ref="test-warehouse-ref",
                                                             warehouse_name="Відділення №5",
                                                             actor_telegram_id=123,
                                                             actor_name="Test Actor",
                                                             )

    assert address is existing_address
    assert save_status == SaveStatus.RESTORED
    assert address.is_active is True
    assert address.label == "Возле дома"
    address_uow.recipient_addresses.add_address.assert_not_awaited()
    address_uow.recipient_audit.add_audit.assert_awaited_once()

    audit = address_uow.recipient_audit.add_audit.await_args.kwargs["audit"]
    assert audit.recipient_id == existing_recipient.id
    assert audit.recipient_address_id == address.id
    assert audit.actor_telegram_id == 123
    assert audit.actor_name == "Test Actor"
    assert audit.action == RecipientAuditAction.RESTORED.value
    assert audit.old_values == {"is_active": False}
    assert audit.new_values == {"is_active": True}

@pytest.mark.asyncio
async def test_add_address_creates_address_and_audit(address_uow, existing_recipient):
    address_uow.recipients.get_by_id.return_value = existing_recipient
    generated_id = uuid.uuid4()
    async def assign_id(address):
        address.id = generated_id
        return address

    address_uow.recipient_addresses.add_address.side_effect = assign_id
    address_service = RecipientAddressService(uow=address_uow)

    address, save_status = await address_service.add_address(recipient_id=existing_recipient.id,
                                                             label="  новый адрес  ",
                                                             city_ref="  test-city-ref  ",
                                                             city_name=" Полтава ",
                                                             warehouse_ref="  test-warehouse-ref  ",
                                                             warehouse_name=" Відділення №4 ",
                                                             actor_telegram_id=123,
                                                             actor_name="Test Actor")
    assert save_status == SaveStatus.CREATED
    assert address.id == generated_id
    assert address.recipient_id == existing_recipient.id
    assert address.label == "новый адрес"
    assert address.city_ref == "test-city-ref"
    assert address.city_name == "Полтава"
    assert address.warehouse_ref == "test-warehouse-ref"
    assert address.warehouse_name == "Відділення №4"

    address_uow.recipient_addresses.add_address.assert_awaited_once_with(address=address)

    address_uow.recipient_addresses.get_by_location.assert_awaited_once_with(
        recipient_id=existing_recipient.id,
        city_ref="test-city-ref",
        warehouse_ref="test-warehouse-ref",
    )
    address_uow.recipient_audit.add_audit.assert_awaited_once()
    audit = address_uow.recipient_audit.add_audit.await_args.kwargs["audit"]

    assert audit.new_values == {"label": "новый адрес",
                                "city_ref": "test-city-ref",
                                "city_name": "Полтава",
                                "warehouse_ref": "test-warehouse-ref",
                                "warehouse_name": "Відділення №4"}
    assert audit.actor_telegram_id == 123
    assert audit.recipient_id == existing_recipient.id
    assert audit.recipient_address_id == generated_id
    assert audit.actor_name == "Test Actor"
    assert audit.action == RecipientAuditAction.CREATED.value
    assert audit.old_values is None

@pytest.mark.asyncio
async def test_rename_address_updates_label_and_audit(address_uow,
                                                      existing_recipient,
                                                      existing_address):
    address_uow.recipients.get_by_id.return_value = existing_recipient
    address_uow.recipient_addresses.get_by_id.return_value = existing_address
    address_service = RecipientAddressService(uow=address_uow)

    address = await address_service.rename_address_label(address_id=existing_address.id,
                                                                      new_label="  Возле работы  ",
                                                                      actor_telegram_id=456,
                                                                      actor_name="Editor")

    assert address is existing_address
    assert address.label == "Возле работы"
    assert address.city_ref == "test-city-ref"
    assert address.city_name == "Полтава"
    assert address.warehouse_ref == "test-warehouse-ref"
    assert address.warehouse_name == "Відділення №5"
    assert address.recipient_id == existing_recipient.id

    address_uow.recipient_addresses.get_by_id.assert_awaited_once_with(
        address_id=existing_address.id,
    )
    address_uow.recipients.get_by_id.assert_awaited_once_with(
        recipient_id=existing_recipient.id,
    )
    address_uow.recipient_audit.add_audit.assert_awaited_once()
    audit = address_uow.recipient_audit.add_audit.await_args.kwargs["audit"]
    assert audit.recipient_id == existing_recipient.id
    assert audit.recipient_address_id == existing_address.id
    assert audit.actor_telegram_id == 456
    assert audit.actor_name == "Editor"
    assert audit.action == RecipientAuditAction.UPDATED.value
    assert audit.old_values == {"label": "Возле дома"}
    assert audit.new_values == {"label": "Возле работы"}

    address_uow.recipient_addresses.add_address.assert_not_awaited()


@pytest.mark.asyncio
async def test_rename_address_skips_unchanged_label(address_uow,
                                                    existing_recipient,
                                                    existing_address):
    address_uow.recipients.get_by_id.return_value = existing_recipient
    address_uow.recipient_addresses.get_by_id.return_value = existing_address
    address_service = RecipientAddressService(uow=address_uow)

    address = await address_service.rename_address_label(address_id=existing_address.id,
                                                         new_label="  Возле дома  ",
                                                         actor_telegram_id=456,
                                                         actor_name="Editor")

    assert address is existing_address
    assert address.label == "Возле дома"
    address_uow.recipient_audit.add_audit.assert_not_awaited()
    address_uow.recipient_addresses.add_address.assert_not_awaited()

@pytest.mark.asyncio
async def test_archive_address_creates_audit(address_uow,
                                             existing_recipient,
                                             existing_address):
    address_uow.recipients.get_by_id.return_value = existing_recipient
    address_uow.recipient_addresses.get_by_id.return_value = existing_address
    address_service = RecipientAddressService(uow=address_uow)
    address = await address_service.archive_recipient_address(address_id=existing_address.id,
                                                              actor_telegram_id=456,
                                                              actor_name="Editor")

    assert address is existing_address
    assert address.is_active is False
    address_uow.recipient_audit.add_audit.assert_awaited_once()
    address_uow.recipient_addresses.add_address.assert_not_awaited()

    audit = address_uow.recipient_audit.add_audit.await_args.kwargs["audit"]
    assert audit.recipient_id == existing_recipient.id
    assert audit.recipient_address_id == existing_address.id
    assert audit.action == RecipientAuditAction.ARCHIVED.value
    assert audit.actor_telegram_id == 456
    assert audit.actor_name == "Editor"
    assert audit.old_values == {"is_active": True}
    assert audit.new_values == {"is_active": False}

@pytest.mark.asyncio
async def test_archive_address_skips_already_archived(address_uow,
                                                      existing_address):
    existing_address.is_active = False
    address_uow.recipient_addresses.get_by_id.return_value = existing_address

    address_service = RecipientAddressService(uow=address_uow)
    address = await address_service.archive_recipient_address(address_id=existing_address.id,
                                                              actor_telegram_id=456,
                                                              actor_name="Editor")
    assert address is existing_address
    assert address.is_active is False
    address_uow.recipients.get_by_id.assert_not_awaited()
    address_uow.recipient_audit.add_audit.assert_not_awaited()
    address_uow.recipient_addresses.add_address.assert_not_awaited()

@pytest.mark.asyncio
async def test_rename_address_rejects_archived_address(address_uow,
                                                       existing_address):
    existing_address.is_active = False
    address_uow.recipient_addresses.get_by_id.return_value = existing_address

    address_service = RecipientAddressService(uow=address_uow)

    with pytest.raises(ValueError, match="Cannot rename an archived address"):
        await address_service.rename_address_label(address_id=existing_address.id,
                                                   new_label="TestArchivedAddress",
                                                   actor_telegram_id=456,
                                                   actor_name="Editor")
    assert existing_address.label == "Возле дома"
    assert existing_address.is_active is False

    address_uow.recipients.get_by_id.assert_not_awaited()
    address_uow.recipient_audit.add_audit.assert_not_awaited()
    address_uow.recipient_addresses.add_address.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize("operation",
                         ["rename", "archive"])
async def test_address_operation_rejects_missing_address(address_uow, operation):
    address_id = uuid.uuid4()
    address_service = RecipientAddressService(uow=address_uow)
    with pytest.raises(ObjectNotFoundError):
        if operation == "rename":
            await address_service.rename_address_label(address_id=address_id,
                                                       new_label="Возле работы",
                                                       actor_telegram_id=456,
                                                       actor_name="Editor")
        else:
            await address_service.archive_recipient_address(address_id=address_id,
                                                            actor_telegram_id=456,
                                                            actor_name="Editor")

    address_uow.recipient_addresses.get_by_id.assert_awaited_once_with(address_id=address_id)
    address_uow.recipients.get_by_id.assert_not_awaited()
    address_uow.recipient_audit.add_audit.assert_not_awaited()
    address_uow.recipient_addresses.add_address.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["add", "archive", "rename"])
async def test_address_operation_rejects_archived_recipient(address_uow,
                                                            existing_address,
                                                            existing_recipient, operation):
    existing_recipient.is_active = False
    address_uow.recipients.get_by_id.return_value = existing_recipient
    address_uow.recipient_addresses.get_by_id.return_value = existing_address

    address_service = RecipientAddressService(uow=address_uow)
    with pytest.raises(ValueError, match="archived recipient"):
        if operation == "add":
            await address_service.add_address(recipient_id=existing_recipient.id,
                                              label="Возле дома",
                                              city_ref="test-city-ref",
                                              city_name="Полтава",
                                              warehouse_ref="test-warehouse-ref",
                                              warehouse_name="Відділення №5",
                                              actor_telegram_id=456,
                                              actor_name="Original Author")
        elif operation == "rename":
            await address_service.rename_address_label(address_id=existing_address.id,
                                                       new_label="Возле работы",
                                                       actor_telegram_id=456,
                                                       actor_name="Original Author")
        else:
            await address_service.archive_recipient_address(address_id=existing_address.id,
                                                            actor_telegram_id=456,
                                                            actor_name="Original Author")

    assert existing_address.is_active is True
    assert existing_address.label == "Возле дома"
    address_uow.recipients.get_by_id.assert_awaited_once_with(recipient_id=existing_recipient.id)
    address_uow.recipient_addresses.get_by_location.assert_not_awaited()
    address_uow.recipient_addresses.add_address.assert_not_awaited()
    address_uow.recipient_audit.add_audit.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["add", "archive", "rename"])
async def test_address_operation_rejects_missing_recipient(address_uow, existing_recipient,
                                                           existing_address, operation):
    address_uow.recipients.get_by_id.return_value = None
    address_uow.recipient_addresses.get_by_id.return_value = existing_address

    address_service = RecipientAddressService(uow=address_uow)
    with pytest.raises(ObjectNotFoundError):
        if operation == "add":
            await address_service.add_address(recipient_id=existing_recipient.id,
                                              label="Возле дома",
                                              city_ref="test-city-ref",
                                              city_name="Полтава",
                                              warehouse_ref="test-warehouse-ref",
                                              warehouse_name="Відділення №5",
                                              actor_telegram_id=456,
                                              actor_name="Original Author")
        elif operation == "rename":
            await address_service.rename_address_label(address_id=existing_address.id,
                                                       new_label="Возле работы",
                                                       actor_telegram_id=456,
                                                       actor_name="Original Author")
        else:
            await address_service.archive_recipient_address(address_id=existing_address.id,
                                                            actor_telegram_id=456,
                                                            actor_name="Original Author")

    assert existing_address.is_active is True
    assert existing_address.label == "Возле дома"
    address_uow.recipients.get_by_id.assert_awaited_once_with(recipient_id=existing_recipient.id)
    address_uow.recipient_addresses.get_by_location.assert_not_awaited()
    address_uow.recipient_addresses.add_address.assert_not_awaited()
    address_uow.recipient_audit.add_audit.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize("field_name",
                         ["label", "city_ref", "city_name", "warehouse_ref", "warehouse_name"])
@pytest.mark.parametrize("invalid_value",
                         [None, 123, "", "   "])
async def test_add_address_rejects_invalid_strings(address_uow, field_name, invalid_value,
                                                   existing_recipient):
    address_uow.recipients.get_by_id.return_value = existing_recipient

    address_data = {
        "label": "Возле дома",
        "city_ref": "test-city-ref",
        "city_name": "Полтава",
        "warehouse_ref": "test-warehouse-ref",
        "warehouse_name": "Відділення №5"
    }
    address_data[field_name] = invalid_value
    address_service = RecipientAddressService(uow=address_uow)

    with pytest.raises(ValueError):
        await address_service.add_address(recipient_id=existing_recipient.id,
                                          actor_telegram_id=456,
                                          actor_name="Editor",
                                          **address_data)
    address_uow.recipient_addresses.get_by_location.assert_not_awaited()
    address_uow.recipient_addresses.add_address.assert_not_awaited()
    address_uow.recipient_audit.add_audit.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize("new_label", [None, 123, "", "   "])
async def test_rename_address_rejects_invalid_labels(address_uow, new_label,
                                                     existing_address):
    address_service = RecipientAddressService(uow=address_uow)
    with pytest.raises(ValueError):
        await address_service.rename_address_label(address_id=existing_address.id,
                                                   new_label=new_label,
                                                   actor_telegram_id=456,
                                                   actor_name="Editor")
    assert existing_address.label == "Возле дома"
    address_uow.recipient_addresses.get_by_id.assert_not_awaited()
    address_uow.recipients.get_by_id.assert_not_awaited()
    address_uow.recipient_audit.add_audit.assert_not_awaited()
    address_uow.recipient_addresses.add_address.assert_not_awaited()



