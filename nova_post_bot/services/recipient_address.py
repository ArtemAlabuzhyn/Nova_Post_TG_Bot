import uuid

from nova_post_bot.core.exceptions import ObjectNotFoundError
from nova_post_bot.db.uow import UnitOfWork
from nova_post_bot.enums.recipient_audit import RecipientAuditAction, SaveStatus
from nova_post_bot.models.recipient_address import RecipientAddress
from nova_post_bot.models.recipient_audit import RecipientAudit


class RecipientAddressService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def add_address(self, recipient_id: uuid.UUID,
                          label: str,
                          city_ref: str, city_name: str,
                          warehouse_ref: str, warehouse_name: str,
                          actor_telegram_id: int, actor_name: str) -> tuple[RecipientAddress, SaveStatus]:
        recipient = await self.uow.recipients.get_by_id(recipient_id=recipient_id)
        if recipient is None:
            raise ObjectNotFoundError(object_id=recipient_id, object_name='Recipient')
        if not recipient.is_active:
            raise ValueError("Cannot add an address to an archived recipient")

        label = self._normalize_required_string(label, "label")
        city_ref = self._normalize_required_string(city_ref, "city_ref")
        city_name = self._normalize_required_string(city_name, "city_name")
        warehouse_ref = self._normalize_required_string(warehouse_ref, "warehouse_ref")
        warehouse_name = self._normalize_required_string(warehouse_name, "warehouse_name")

        existing_address = await self.uow.recipient_addresses.get_by_location(recipient_id=recipient_id,
                                                                              city_ref=city_ref,
                                                                              warehouse_ref=warehouse_ref)
        if existing_address is not None:
            if existing_address.is_active:
                return existing_address, SaveStatus.EXISTING

            existing_address.is_active = True

            audit = RecipientAudit(recipient_id=recipient_id,
                                   recipient_address_id=existing_address.id,
                                   actor_telegram_id=actor_telegram_id, actor_name=actor_name,
                                   action=RecipientAuditAction.RESTORED.value,
                                   old_values={"is_active": False},
                                   new_values={"is_active": True})
            await self.uow.recipient_audit.add_audit(audit=audit)
            return existing_address, SaveStatus.RESTORED
        address = RecipientAddress(recipient_id=recipient_id,
                                   label=label,
                                   city_ref=city_ref, city_name=city_name,
                                   warehouse_ref=warehouse_ref, warehouse_name=warehouse_name)
        await self.uow.recipient_addresses.add_address(address=address)

        audit = RecipientAudit(recipient_id=recipient_id,
                               recipient_address_id=address.id,
                               actor_telegram_id=actor_telegram_id, actor_name=actor_name,
                               action=RecipientAuditAction.CREATED.value,
                               old_values=None,
                               new_values=dict(label=label,
                                               city_ref=city_ref, city_name=city_name,
                                               warehouse_ref=warehouse_ref, warehouse_name=warehouse_name))
        await self.uow.recipient_audit.add_audit(audit=audit)
        return address, SaveStatus.CREATED

    async def list_addresses(self, recipient_id: uuid.UUID) -> list[RecipientAddress]:
        return await self.uow.recipient_addresses.list_by_recipient_id(
            recipient_id=recipient_id
        )

    async def rename_address_label(self, address_id: uuid.UUID,
                                   new_label: str,
                                   actor_telegram_id: int,
                                   actor_name: str) -> RecipientAddress:
        new_label = self._normalize_required_string(new_label, "new_label")
        address = await self.get_by_id(address_id=address_id)
        if not address.is_active:
            raise ValueError("Cannot rename an archived address")
        recipient = await self.uow.recipients.get_by_id(recipient_id=address.recipient_id)
        if recipient is None:
            raise ObjectNotFoundError(object_id=address.recipient_id, object_name='Recipient')
        if not recipient.is_active:
            raise ValueError("Cannot rename an address of an archived recipient")
        old_label = address.label
        if old_label == new_label:
            return address
        address.label = new_label
        audit = RecipientAudit(recipient_id=address.recipient_id,
                               recipient_address_id=address.id,
                               actor_telegram_id=actor_telegram_id,
                               actor_name=actor_name,
                               action=RecipientAuditAction.UPDATED.value,
                               old_values={"label": old_label},
                               new_values={"label": new_label})
        await self.uow.recipient_audit.add_audit(audit=audit)
        return address

    async def archive_recipient_address(self, address_id: uuid.UUID,
                                        actor_telegram_id: int,
                                        actor_name: str) -> RecipientAddress:
        address = await self.get_by_id(address_id=address_id)
        if not address.is_active:
            return address

        recipient = await self.uow.recipients.get_by_id(recipient_id=address.recipient_id)
        if recipient is None:
            raise ObjectNotFoundError(object_id=address.recipient_id, object_name='Recipient')
        if not recipient.is_active:
            raise ValueError("Cannot archive an address of an archived recipient")

        address.is_active = False

        audit = RecipientAudit(recipient_id=address.recipient_id,
                               recipient_address_id=address.id,
                               actor_telegram_id=actor_telegram_id,
                               actor_name=actor_name,
                               action=RecipientAuditAction.ARCHIVED.value,
                               old_values={"is_active": True},
                               new_values={"is_active": False})
        await self.uow.recipient_audit.add_audit(audit=audit)
        return address

    async def get_by_id(self, address_id: uuid.UUID) -> RecipientAddress:
        address = await self.uow.recipient_addresses.get_by_id(address_id=address_id)
        if address is None:
            raise ObjectNotFoundError(object_id=address_id, object_name='RecipientAddress')
        return address

    @staticmethod
    def _normalize_required_string(value: str, field_name: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string")

        value = value.strip()
        if not value:
            raise ValueError(f"{field_name} cannot be empty ")
        return value
