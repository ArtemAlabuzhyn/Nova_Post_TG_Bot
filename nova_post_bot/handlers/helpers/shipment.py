import uuid
from html import escape

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from nova_post_bot.core.exceptions import ObjectNotFoundError
from nova_post_bot.db.uow import UnitOfWork
from nova_post_bot.keyboards.shipment import shipment_confirmation_keyboard
from nova_post_bot.services.recipient import RecipientService
from nova_post_bot.services.recipient_address import RecipientAddressService
from nova_post_bot.states.shipment import ShipmentStates


async def show_shipment_confirmation(message: Message, state: FSMContext, uow: UnitOfWork):
    data = await state.get_data()

    if not data.get("shipment_id"):
        shipment_id = uuid.uuid4()
        await state.update_data(shipment_id=str(shipment_id))
    try:
        recipient_id = uuid.UUID(data['recipient_id'])
        recipient_address_id = uuid.UUID(data['recipient_address_id'])

    except (KeyError, ValueError) as exs:
        raise ValueError("Не удалось загрузить данные накладной. Начните создание заново") from exs
    recipient_service = RecipientService(uow=uow)
    address_service = RecipientAddressService(uow=uow)
    try:
        recipient = await recipient_service.get_by_id(recipient_id=recipient_id)
        address = await address_service.get_by_id(address_id=recipient_address_id)
    except ObjectNotFoundError as exs:
        raise ValueError("Ошибка: получатель или адрес не доступны. Пожалуйста, начните заново.") from exs

    if not recipient.is_active:
        raise ValueError("Получатель архивирован. Выберите другого получателя")

    if not address.is_active:
        raise ValueError("Адрес архивирован. Выберите другой адрес")
    if recipient.id != address.recipient_id:
        raise ValueError("Адрес не принадлежит выбранному получателю. Выберите адрес заново")

    lines = [
        "Тип отправления: Документы",
        f"Кто запросил накладную: {escape(data['requested_by_name'])}",
        f"Адрес отправки: {escape(data["sender_city_name"])} {escape(data['sender_warehouse_name'])}",
        f"Получатель: {escape(recipient.first_name)} {escape(recipient.last_name)} {escape(recipient.phone)}",
        f"Адрес получения: {escape(address.city_name)} — {escape(address.warehouse_name)}"
    ]
    confirmation_message = await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=shipment_confirmation_keyboard())
    await state.update_data(confirmation_message_id=confirmation_message.message_id)
    await state.set_state(ShipmentStates.waiting_for_confirmation)
