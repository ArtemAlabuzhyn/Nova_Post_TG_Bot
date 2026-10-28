import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from nova_post_bot.core.exceptions import ObjectAlreadyExistsError
from nova_post_bot.core.exceptions import ObjectNotFoundError
from nova_post_bot.enums.recipient_audit import RecipientAuditAction
from nova_post_bot.enums.recipient_audit import SaveStatus
from nova_post_bot.models.recipient import Recipient
from nova_post_bot.services.recipient import normalize_phone, RecipientService, normalize_recipient_name


def test_normalize_phone():
    correct_phone = "  0671234567  "

    phone = normalize_phone(correct_phone)
    assert phone == "380671234567"
    assert len(phone) == 12


def test_normalize_phone_rejects_short_number():
    incorrect_phone = "067123456"
    with pytest.raises(ValueError, match="exactly 10 digits"):
        normalize_phone(incorrect_phone)


@pytest.mark.parametrize(("value", "expected"),
                         [
                             ("  Іван  ", "Іван"),
                             ("Анна-Марія", "Анна-Марія"),
                             ("O’Connor", "O'Connor"),
                             ("Лукʼян", "Лук'ян"),
                             ("McDonald", "McDonald"),
                             ("іван", "іван"),
                         ])
def test_normalize_recipient_name_accepts_valid_name(value, expected):
    assert normalize_recipient_name(value) == expected


@pytest.mark.parametrize(("value"),
                         [None,
                          123,
                          "",
                          "   ",
                          "Іван123",
                          "Іван🙂",
                          "Іван Петро",
                          "-Іван",
                          "Іван-",
                          "'Іван",
                          "Іван'",
                          "Анна--Марія",
                          "O''Connor",
                          "Анна-'Марія"])
def test_normalize_recipient_name_rejects_invalid_name(value):
    with pytest.raises(ValueError):
        normalize_recipient_name(value)


@pytest.mark.parametrize(("phone"),
                         [None,
                          123,
                          "",
                          "   ",
                          "067123456",
                          "06712345678",
                          "1671234567",
                          "067123456a",
                          "+380671234567",
                          "380671234567",
                          "067 1234567",
                          "０６７１２３４５６７"])
def test_normalize_recipient_phone_rejects_invalid_number(phone):
    with pytest.raises(ValueError):
        normalize_phone(phone)


@pytest.mark.asyncio
async def test_create_recipient_handles_unique_violation(recipient_uow):
    recipient_service = RecipientService(uow=recipient_uow)

    cause = Exception("Unique violation")
    cause.sqlstate = "23505"
    cause.constraint_name = "uq_recipients_name_phone"

    original_error = Exception("Database driver error")
    original_error.__cause__ = cause

    db_error = IntegrityError(
        statement="INSERT INTO recipients",
        params={},
        orig=original_error,
    )

    recipient_uow.recipients.add_recipient.side_effect = db_error

    with pytest.raises(ObjectAlreadyExistsError):
        await recipient_service.create_recipient(
            first_name="John",
            last_name="Doe",
            phone="0671234567",
            created_by_telegram_id=123,
            created_by_name="Test User"
        )
    recipient_uow.recipients.add_recipient.assert_awaited_once()
    recipient_uow.rollback.assert_awaited_once()
    recipient_uow.recipient_audit.add_audit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_recipient_reraises_other_integrity_error(recipient_uow):
    recipient_service = RecipientService(uow=recipient_uow)

    cause = Exception("Unique violation")
    cause.sqlstate = "23505"
    cause.constraint_name = "another_unique_constraint"

    original_error = Exception("Database driver error")
    original_error.__cause__ = cause

    db_error = IntegrityError(
        statement="INSERT INTO recipients",
        params={},
        orig=original_error,
    )

    recipient_uow.recipients.add_recipient.side_effect = db_error

    with pytest.raises(IntegrityError):
        await recipient_service.create_recipient(
            first_name="John",
            last_name="Doe",
            phone="0671234567",
            created_by_telegram_id=123,
            created_by_name="Test User"
        )
    recipient_uow.recipients.add_recipient.assert_awaited_once()
    recipient_uow.rollback.assert_awaited_once()
    recipient_uow.recipient_audit.add_audit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_recipient_returns_existing_active_recipient(recipient_uow, existing_recipient):
    recipient_uow.recipients.find_duplicate.return_value = existing_recipient
    recipient_service = RecipientService(uow=recipient_uow)
    recipient, save_status = await recipient_service.create_recipient(
        first_name="John",
        last_name="Doe",
        phone="0671234567",
        created_by_telegram_id=123,
        created_by_name="Test User",
    )
    assert recipient is existing_recipient
    assert save_status == SaveStatus.EXISTING
    recipient_uow.recipients.find_duplicate.assert_awaited_once_with(
        first_name="John",
        last_name="Doe",
        phone="380671234567",
    )
    recipient_uow.recipients.add_recipient.assert_not_awaited()
    recipient_uow.recipient_audit.add_audit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_recipient_restores_archived_recipient(recipient_uow, existing_recipient):
    existing_recipient.is_active = False
    recipient_uow.recipients.find_duplicate.return_value = existing_recipient
    recipient_service = RecipientService(uow=recipient_uow)
    recipient, save_status = await recipient_service.create_recipient(
        first_name="John",
        last_name="Doe",
        phone="0671234567",
        created_by_telegram_id=456,
        created_by_name="Restoring user",
    )
    assert recipient is existing_recipient
    assert save_status == SaveStatus.RESTORED
    assert recipient.is_active is True
    assert recipient.created_by_name == "Original Author"
    assert recipient.created_by_telegram_id == 123
    recipient_uow.recipients.add_recipient.assert_not_awaited()
    recipient_uow.recipient_audit.add_audit.assert_awaited_once()

    audit = recipient_uow.recipient_audit.add_audit.await_args.kwargs["audit"]

    assert audit.recipient_id == existing_recipient.id
    assert audit.actor_telegram_id == 456
    assert audit.actor_name == "Restoring user"
    assert audit.action == RecipientAuditAction.RESTORED.value
    assert audit.old_values == {"is_active": False}
    assert audit.new_values == {"is_active": True}


@pytest.mark.asyncio
async def test_archive_recipient_create_audit(recipient_uow, existing_recipient):
    recipient_uow.recipients.get_by_id.return_value = existing_recipient
    recipient_service = RecipientService(uow=recipient_uow)
    recipient = await recipient_service.archive_recipient(recipient_id=existing_recipient.id,
                                                          actor_telegram_id=456,
                                                          actor_name="Archived Author")
    assert recipient is existing_recipient
    assert existing_recipient.is_active is False

    recipient_uow.recipient_audit.add_audit.assert_awaited_once()
    audit = recipient_uow.recipient_audit.add_audit.await_args.kwargs["audit"]

    assert audit.recipient_id == existing_recipient.id
    assert audit.actor_telegram_id == 456
    assert audit.actor_name == "Archived Author"
    assert audit.action == RecipientAuditAction.ARCHIVED.value
    assert audit.old_values == {"is_active": True}
    assert audit.new_values == {"is_active": False}

    recipient_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_archive_recipient_skips_already_archived(recipient_uow, existing_recipient):
    existing_recipient.is_active = False
    recipient_uow.recipients.get_by_id.return_value = existing_recipient
    recipient_service = RecipientService(uow=recipient_uow)
    recipient = await recipient_service.archive_recipient(recipient_id=existing_recipient.id,
                                                          actor_telegram_id=456,
                                                          actor_name="Archived Author")
    assert recipient is existing_recipient
    assert existing_recipient.is_active is False
    recipient_uow.recipient_audit.add_audit.assert_not_awaited()
    recipient_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_archive_recipient_reject_archive_non_existing_recipient(recipient_uow):
    recipient_id = uuid.uuid4()

    recipient_service = RecipientService(uow=recipient_uow)
    with pytest.raises(ObjectNotFoundError):
        await recipient_service.archive_recipient(recipient_id=recipient_id,
                                                  actor_telegram_id=456,
                                                  actor_name="Archived Author")
    recipient_uow.recipients.get_by_id.assert_awaited_once_with(recipient_id=recipient_id, )
    recipient_uow.recipient_audit.add_audit.assert_not_awaited()
    recipient_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_recipient_and_audit(recipient_uow):
    generated_id = uuid.uuid4()

    async def assign_id(recipient):
        recipient.id = generated_id
        return recipient

    recipient_uow.recipients.add_recipient.side_effect = assign_id
    recipient_service = RecipientService(uow=recipient_uow)
    recipient, save_status = await recipient_service.create_recipient(
        first_name="  John  ",
        last_name="  Doe  ",
        phone="  0671234567",
        created_by_telegram_id=123,
        created_by_name="Original Author",
    )
    assert save_status == SaveStatus.CREATED
    assert recipient.id == generated_id
    assert recipient.first_name == "John"
    assert recipient.last_name == "Doe"
    assert recipient.phone == "380671234567"
    assert recipient.created_by_telegram_id == 123
    assert recipient.created_by_name == "Original Author"
    recipient_uow.recipients.find_duplicate.assert_awaited_once_with(first_name="John",
                                                                     last_name="Doe",
                                                                     phone="380671234567")
    recipient_uow.recipients.add_recipient.assert_awaited_once_with(recipient)
    recipient_uow.recipient_audit.add_audit.assert_awaited_once()

    audit = recipient_uow.recipient_audit.add_audit.await_args.args[0]

    assert audit.recipient_id == generated_id
    assert audit.actor_telegram_id == 123
    assert audit.actor_name == "Original Author"
    assert audit.action == RecipientAuditAction.CREATED.value
    assert audit.old_values is None
    assert audit.new_values == {"first_name": "John",
                                "last_name": "Doe",
                                "phone": "380671234567"}
    recipient_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(("field_name", "new_value", "old_value", "expected_value"),
                         [("first_name", "  Jane  ", "John", "Jane"),
                          ("last_name", "  O’Connor  ", "Doe", "O'Connor"),
                          ("phone", " 380501234567  ", "380671234567", "380501234567")])
async def test_edit_recipient_field_creates_audit(existing_recipient, recipient_uow,
                                                  field_name, new_value, old_value, expected_value):
    recipient_uow.recipients.get_by_id.return_value = existing_recipient
    expected_data = {
        "first_name": existing_recipient.first_name,
        "last_name": existing_recipient.last_name,
        "phone": existing_recipient.phone,
    }
    expected_data[field_name] = expected_value
    recipient_service = RecipientService(uow=recipient_uow)
    recipient = await recipient_service.update_recipient_field(
        recipient_id=existing_recipient.id,
        field_name=field_name,
        new_value=new_value,
        actor_telegram_id=456,
        actor_name="Editor",
    )
    assert recipient is existing_recipient
    assert getattr(recipient, field_name) == expected_value
    assert {"first_name": recipient.first_name,
            "last_name": recipient.last_name,
            "phone": recipient.phone} == expected_data

    recipient_uow.recipients.find_duplicate.assert_awaited_once_with(**expected_data)
    recipient_uow.recipient_audit.add_audit.assert_awaited_once()
    audit = recipient_uow.recipient_audit.add_audit.await_args.kwargs["audit"]

    assert audit.recipient_id == existing_recipient.id
    assert audit.actor_telegram_id == 456
    assert audit.actor_name == "Editor"
    assert audit.action == RecipientAuditAction.UPDATED.value
    assert audit.old_values == {field_name: old_value}
    assert audit.new_values == {field_name: expected_value}

    recipient_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(("field_name", "new_value"),
                         [("is_active", "True"),
                          ("first_name", ""),
                          ("first_name", "John123"),
                          ("last_name", "Doe-$"),
                          ("phone", None),
                          ("phone", "380671234567f"),
                          ("phone", "0671234567"),
                          ("phone", "390671234567")])
async def test_edit_recipient_rejects_invalid_input(existing_recipient, recipient_uow,
                                                    field_name, new_value):
    recipient_uow.recipients.get_by_id.return_value = existing_recipient
    recipient_service = RecipientService(uow=recipient_uow)
    with pytest.raises(ValueError):
        await recipient_service.update_recipient_field(
            recipient_id=existing_recipient.id,
            field_name=field_name,
            new_value=new_value,
            actor_telegram_id=456,
            actor_name="Editor")
    assert existing_recipient.first_name == "John"
    assert existing_recipient.last_name == "Doe"
    assert existing_recipient.phone == "380671234567"
    assert existing_recipient.is_active is True
    recipient_uow.recipients.find_duplicate.assert_not_awaited()
    recipient_uow.recipient_audit.add_audit.assert_not_awaited()
    recipient_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_recipient_skips_unchanged_value(existing_recipient, recipient_uow):
    recipient_uow.recipients.get_by_id.return_value = existing_recipient
    recipient_uow.recipients.find_duplicate.return_value = existing_recipient

    recipient_service = RecipientService(uow=recipient_uow)
    recipient = await recipient_service.update_recipient_field(recipient_id=existing_recipient.id,
                                                               field_name="first_name",
                                                               new_value="  John ",
                                                               actor_telegram_id=123,
                                                               actor_name="Original Author",
                                                               )
    assert recipient is existing_recipient
    assert recipient.first_name == "John"
    recipient_uow.recipient_audit.add_audit.assert_not_awaited()
    recipient_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_recipient_rejects_duplicate(existing_recipient, recipient_uow):
    recipient_service = RecipientService(uow=recipient_uow)
    duplicate = Recipient(id=uuid.uuid4(),
                          first_name="Jane",
                          last_name="Doe",
                          phone="380671234567",
                          created_by_telegram_id=123,
                          created_by_name="Original Author", )
    recipient_uow.recipients.get_by_id.return_value = existing_recipient
    recipient_uow.recipients.find_duplicate.return_value = duplicate
    with pytest.raises(ObjectAlreadyExistsError):
        await recipient_service.update_recipient_field(recipient_id=existing_recipient.id,
                                                       field_name="first_name",
                                                       new_value="Jane",
                                                       actor_telegram_id=123,
                                                       actor_name="Original Author", )
    assert existing_recipient.first_name == "John"
    assert duplicate.first_name == "Jane"

    recipient_uow.recipients.get_by_id.assert_awaited_once_with(recipient_id=existing_recipient.id, )
    recipient_uow.recipients.find_duplicate.assert_awaited_once_with(first_name="Jane",
                                                                     last_name="Doe",
                                                                     phone="380671234567")
    recipient_uow.recipient_audit.add_audit.assert_not_awaited()
    recipient_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_recipient_rejects_archived_recipient(existing_recipient, recipient_uow):
    existing_recipient.is_active = False
    recipient_uow.recipients.get_by_id.return_value = existing_recipient

    recipient_service = RecipientService(uow=recipient_uow)
    with pytest.raises(ValueError, match="Allowed to change only active recipient"):
        await recipient_service.update_recipient_field(recipient_id=existing_recipient.id,
                                                       field_name="first_name",
                                                       new_value="Jane",
                                                       actor_telegram_id=123,
                                                       actor_name="Original Author")
    assert existing_recipient.first_name == "John"
    assert existing_recipient.is_active is False
    recipient_uow.recipients.get_by_id.assert_awaited_once_with(recipient_id=existing_recipient.id)
    recipient_uow.recipients.find_duplicate.assert_not_awaited()
    recipient_uow.recipient_audit.add_audit.assert_not_awaited()
    recipient_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_recipient_rejects_missing_recipient(recipient_uow):
    recipient_service = RecipientService(uow=recipient_uow)
    recipient_id = uuid.uuid4()
    with pytest.raises(ObjectNotFoundError):
        await recipient_service.update_recipient_field(recipient_id=recipient_id,
                                                       field_name="first_name",
                                                       new_value="Jane",
                                                       actor_telegram_id=123,
                                                       actor_name="Original Author")
    recipient_uow.recipients.get_by_id.assert_awaited_once_with(recipient_id=recipient_id)
    recipient_uow.recipients.find_duplicate.assert_not_awaited()
    recipient_uow.recipient_audit.add_audit.assert_not_awaited()
    recipient_uow.rollback.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(("constraint_name", "expected_error"),
                         [("uq_recipients_name_phone", ObjectAlreadyExistsError),
                          ("another_unique_constraint", IntegrityError)])
async def test_edit_recipient_handles_integrity_error(recipient_uow, existing_recipient,
                                                      constraint_name, expected_error):
    recipient_uow.recipients.get_by_id.return_value = existing_recipient
    recipient_service = RecipientService(uow=recipient_uow)

    cause = Exception("Unique violation")
    cause.sqlstate = "23505"
    cause.constraint_name = constraint_name

    original_error = Exception("Database driver error")
    original_error.__cause__ = cause

    db_error = IntegrityError(
        statement="UPDATE recipients",
        params={},
        orig=original_error,
    )
    recipient_uow.recipient_audit.add_audit.side_effect = db_error

    with pytest.raises(expected_error) as error:
        await recipient_service.update_recipient_field(recipient_id=existing_recipient.id,
                                                       field_name="first_name",
                                                       new_value="Jane",
                                                       actor_telegram_id=456,
                                                       actor_name="Editor")
    recipient_uow.recipients.find_duplicate.assert_awaited_once_with(
        first_name="Jane",
        last_name="Doe",
        phone="380671234567"
    )
    recipient_uow.recipient_audit.add_audit.assert_awaited_once()
    recipient_uow.rollback.assert_awaited_once()
    if expected_error is IntegrityError:
        assert error.value is db_error
    else:
        assert error.value.__cause__ is db_error
