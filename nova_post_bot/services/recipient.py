import uuid

from sqlalchemy.exc import IntegrityError

from nova_post_bot.core.exceptions import ObjectNotFoundError, \
    ObjectAlreadyExistsError
from nova_post_bot.db.uow import UnitOfWork
from nova_post_bot.enums.recipient_audit import RecipientAuditAction
from nova_post_bot.models.recipient import Recipient
from nova_post_bot.models.recipient_audit import RecipientAudit
from nova_post_bot.enums.recipient_audit import SaveStatus



class RecipientService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def list_recipients(self, limit: int = 10, offset: int = 0) -> list[Recipient]:
        return await self.uow.recipients.list_recipients(limit=limit, offset=offset)

    async def get_by_id(self, recipient_id: uuid.UUID) -> Recipient:
        recipient = await self.uow.recipients.get_by_id(recipient_id=recipient_id)
        if recipient is None:
            raise ObjectNotFoundError(object_id=recipient_id, object_name="Recipient")
        return recipient

    async def create_recipient(self, first_name: str,
                               last_name: str,
                               phone: str,
                               created_by_telegram_id: int,
                               created_by_name: str) -> tuple[Recipient, SaveStatus]:
        normalized_phone = normalize_phone(phone)

        first_name = normalize_recipient_name(first_name)
        last_name = normalize_recipient_name(last_name)

        existing_recipient = await self.uow.recipients.find_duplicate(first_name=first_name,
                                                                      last_name=last_name,
                                                                      phone=normalized_phone)
        if existing_recipient is not None:
            if existing_recipient.is_active:
                return existing_recipient, SaveStatus.EXISTING

            existing_recipient.is_active = True

            audit = RecipientAudit(
                recipient_id=existing_recipient.id,
                actor_telegram_id=created_by_telegram_id,
                actor_name=created_by_name,
                action=RecipientAuditAction.RESTORED.value,
                old_values={"is_active": False},
                new_values={"is_active": True},
            )
            await self.uow.recipient_audit.add_audit(audit=audit)
            return existing_recipient, SaveStatus.RESTORED

        recipient = Recipient(first_name=first_name,
                              last_name=last_name,
                              phone=normalized_phone,
                              created_by_telegram_id=created_by_telegram_id,
                              created_by_name=created_by_name)
        try:
            await self.uow.recipients.add_recipient(recipient)
        except IntegrityError as exc:
            await self.uow.rollback()
            if self._is_recipient_duplicate_error(exc):
                raise ObjectAlreadyExistsError(object_name="Recipient") from exc
            raise

        recipient_audit = RecipientAudit(recipient_id=recipient.id,
                                         actor_telegram_id=created_by_telegram_id,
                                         actor_name=created_by_name,
                                         action=RecipientAuditAction.CREATED.value,
                                         old_values=None,
                                         new_values=dict(first_name=first_name,
                                                         last_name=last_name,
                                                         phone=normalized_phone))
        await self.uow.recipient_audit.add_audit(recipient_audit)
        return recipient, SaveStatus.CREATED

    async def update_recipient_field(self,
                                     recipient_id: uuid.UUID,
                                     field_name: str,
                                     new_value: str,
                                     actor_telegram_id: int,
                                     actor_name: str, ) -> Recipient:
        allowed_fields = ["first_name", "last_name", "phone"]
        if field_name not in allowed_fields:
            raise ValueError("Allowed to change only first/last name or phone number")
        recipient = await self.get_by_id(recipient_id=recipient_id)
        if not recipient.is_active:
            raise ValueError("Allowed to change only active recipient")

        if field_name == "first_name" or field_name == "last_name":
            new_value = normalize_recipient_name(new_value)
        elif field_name == "phone":
            if not isinstance(new_value, str):
                raise ValueError("Phone number must be a string")

            new_value = new_value.strip()

            if not new_value.isdigit() or not new_value.isascii():
                raise ValueError("Phone number must contain only digits")
            if len(new_value) != 12:
                raise ValueError("Phone number must contain exactly 12 digits")
            if not new_value.startswith("380"):
                raise ValueError("Phone number must start with 380")
        updated_data = {
            "first_name": recipient.first_name,
            "last_name": recipient.last_name,
            "phone": recipient.phone
        }
        updated_data[field_name] = new_value
        existing_recipient = await self.uow.recipients.find_duplicate(first_name=updated_data["first_name"],
                                                                      last_name=updated_data["last_name"],
                                                                      phone=updated_data["phone"])
        if existing_recipient is not None and existing_recipient.id != recipient_id:
            raise ObjectAlreadyExistsError(object_name="Recipient")

        old_value = getattr(recipient, field_name)
        if old_value == new_value:
            return recipient
        setattr(recipient, field_name, new_value)

        audit = RecipientAudit(recipient_id=recipient.id,
                               actor_telegram_id=actor_telegram_id,
                               actor_name=actor_name,
                               action=RecipientAuditAction.UPDATED.value,
                               old_values={field_name: old_value},
                               new_values={field_name: new_value})
        try:
            await self.uow.recipient_audit.add_audit(audit=audit)
        except IntegrityError as exc:
            await self.uow.rollback()
            if self._is_recipient_duplicate_error(exc):
                raise ObjectAlreadyExistsError(object_name="Recipient") from exc
            raise
        return recipient

    async def archive_recipient(self,
                                 recipient_id: uuid.UUID,
                                 actor_telegram_id: int,
                                 actor_name: str) -> Recipient:
        recipient = await self.get_by_id(recipient_id=recipient_id)
        if not recipient.is_active:
            return recipient
        recipient.is_active = False
        recipient_audit = RecipientAudit(recipient_id=recipient_id,
                                         actor_telegram_id=actor_telegram_id,
                                         actor_name=actor_name,
                                         action=RecipientAuditAction.ARCHIVED.value,
                                         old_values={"is_active": True},
                                         new_values={"is_active": False})
        await self.uow.recipient_audit.add_audit(audit=recipient_audit)
        return recipient

    @staticmethod
    def _is_recipient_duplicate_error(exc: IntegrityError) -> bool:
        cause = exc.orig.__cause__
        return (
                getattr(cause, "sqlstate", None) == "23505"
                and getattr(cause, "constraint_name", None) == "uq_recipients_name_phone"
        )


def normalize_phone(phone: str) -> str:
    prefix_to_add = "38"
    if not isinstance(phone, str):
        raise ValueError("Phone number must be a string")
    phone = phone.strip()
    if not phone.isdigit() or not phone.isascii():
        raise ValueError("Phone number must contain only digits")
    if len(phone) != 10:
        raise ValueError("Phone number must contain exactly 10 digits")
    if not phone.startswith("0"):
        raise ValueError("Phone number must start with 0")
    return prefix_to_add + phone


def normalize_recipient_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Recipient name must be a string")
    value = value.strip()
    if not value:
        raise ValueError("Recipient name cannot be empty")

    value = value.replace("’", "'").replace("ʼ", "'")
    parts = value.replace("-", "'").split("'")
    for part in parts:
        if not part.isalpha():
            raise ValueError("Recipient name must contain only letters or hyphens or/and apostrophes between letters")
    return value
