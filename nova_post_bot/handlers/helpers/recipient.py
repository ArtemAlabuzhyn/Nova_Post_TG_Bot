import uuid

from aiogram.types import CallbackQuery

from nova_post_bot.core.exceptions import ObjectNotFoundError
from nova_post_bot.db.uow import UnitOfWork
from nova_post_bot.models.recipient import Recipient
from nova_post_bot.models.recipient_address import RecipientAddress
from nova_post_bot.services.recipient import RecipientService
from nova_post_bot.services.recipient_address import RecipientAddressService


async def get_active_recipient_from_callback(callback: CallbackQuery,
                                             uow: UnitOfWork) -> Recipient | None:
    parts = (callback.data or "").split(":", 1)
    if len(parts) != 2:
        await callback.answer("Некорректный ID получателя", show_alert=True)
        return None

    try:
        recipient_id = uuid.UUID(parts[1])
    except ValueError:
        await callback.answer("Некорректный ID получателя", show_alert=True)
        return None

    recipient_service = RecipientService(uow=uow)

    try:
        recipient = await recipient_service.get_by_id(recipient_id=recipient_id)
    except ObjectNotFoundError:
        await callback.answer("Получатель не найден", show_alert=True)
        return None
    if not recipient.is_active:
        await callback.answer("Получатель архивирован", show_alert=True)
        return None
    return recipient

async def get_active_recipient_address_from_callback(callback: CallbackQuery,
                                                     uow: UnitOfWork) -> RecipientAddress | None:
    parts = (callback.data or "").split(":", 1)
    if len(parts) != 2:
        await callback.answer("Некорректный ID адреса", show_alert=True)
        return None

    try:
        address_id = uuid.UUID(parts[1])
    except ValueError:
        await callback.answer("Некорректный ID адреса", show_alert=True)
        return None

    address_service = RecipientAddressService(uow=uow)
    try:
        address = await address_service.get_by_id(address_id=address_id)
    except ObjectNotFoundError:
        await callback.answer("Адрес не найден", show_alert=True)
        return None
    if not address.is_active:
        await callback.answer("Адрес архивирован", show_alert=True)
        return None
    recipient = address.recipient_id
    if recipient is None:
        return None

    recipient_service = RecipientService(uow=uow)

    try:
        recipient = await recipient_service.get_by_id(recipient_id=address.recipient_id)
    except ObjectNotFoundError:
        await callback.answer("Получатель не найден", show_alert=True)
        return None
    if not recipient.is_active:
        await callback.answer("Получатель архивирован", show_alert=True)
        return None
    return address