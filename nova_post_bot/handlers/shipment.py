import uuid

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from nova_post_bot.clients.nova_post import NovaPostClient
from nova_post_bot.core.config import settings
from nova_post_bot.core.exceptions import NovaPostTimeoutError, NovaPostAPIError, NovaPostValidationError, \
    NovaPostUnexpectedResponseError, ObjectNotFoundError
from nova_post_bot.db import uow
from nova_post_bot.db.uow import UnitOfWork
from nova_post_bot.handlers.helpers.recipient import get_active_recipient_from_callback, \
    get_active_recipient_address_from_callback
from nova_post_bot.handlers.helpers.shipment import show_shipment_confirmation
from nova_post_bot.keyboards.cancel import cancel_keyboard
from nova_post_bot.keyboards.main_menu import main_menu
from nova_post_bot.keyboards.shipment import (
    shipment_recipient_keyboard,
    shipment_recipient_action_keyboard, shipment_recipient_addresses_keyboard,
)
from nova_post_bot.keyboards.shipment import shipment_type_keyboard, sender_cities_keyboard, sender_warehouse_keyboard, \
    sender_warehouse_query_keyboard
from nova_post_bot.schemas.city import CityInfo
from nova_post_bot.schemas.warehouse import WarehouseInfo
from nova_post_bot.services.recipient import RecipientService
from nova_post_bot.services.recipient_address import RecipientAddressService
from nova_post_bot.services.shipment import ShipmentService
from nova_post_bot.states.recipient_address import RecipientAddressStates
from nova_post_bot.states.shipment import ShipmentStates

router = Router()


@router.message(F.text == "Создать накладную")
async def start_creating_shipment(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if user_id in settings.shipment_requester_input_ids:
        await state.set_state(ShipmentStates.waiting_for_requester)
        await message.answer("Кто запросил накладную?", reply_markup=cancel_keyboard)
        return

    requested_by_name = settings.allowed_telegram_ids[user_id]
    await state.update_data(requested_by_name=requested_by_name)
    await state.set_state(ShipmentStates.choosing_type)

    await message.answer("Начинаем создания накладной",
                         reply_markup=cancel_keyboard)

    selection_message = await message.answer("Выберите тип отправления", reply_markup=shipment_type_keyboard())

    await state.update_data(confirmation_message_id=selection_message.message_id)


@router.message(ShipmentStates.waiting_for_requester, F.text)
async def process_shipment_requester(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "":
        await message.answer("Не может быть пустая строка", reply_markup=cancel_keyboard)
        return
    await state.update_data(requested_by_name=text)
    await state.set_state(ShipmentStates.choosing_type)
    selection_message = await message.answer("Выберите тип отправления", reply_markup=shipment_type_keyboard())
    await state.update_data(confirmation_message_id=selection_message.message_id)


@router.callback_query(
    ShipmentStates.choosing_type,
    F.data == "shipment_type:documents"
)
async def choose_document_shipment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(shipment_type="documents")
    await state.set_state(ShipmentStates.waiting_for_sender_city_query)
    await callback.message.edit_text("Тип отправления: Документы",
                                     reply_markup=None)
    await callback.message.answer("Введите название города или его начало",
                                  reply_markup=cancel_keyboard)


@router.message(ShipmentStates.waiting_for_sender_city_query, F.text)
async def search_sender_city(message: Message, state: FSMContext, nova_post_client: NovaPostClient):
    query = message.text.strip()
    if not query:
        await message.answer("Название города не может быть пустым")
        return
    try:
        cities = await nova_post_client.search_cities(query)
    except NovaPostTimeoutError:
        await message.answer("НП в данный момент не отвечает. Попробуйте позже.")
        return
    except NovaPostAPIError:
        await message.answer("Не удалось загрузить города. Попробуйте позже")
        return

    if not cities:
        await message.answer("Населенный пункт не найден. Проверьте название или введите его начало")
        return

    await state.update_data(sender_city_options=[city.model_dump() for city in cities])
    await state.set_state(ShipmentStates.waiting_for_sender_city_selection)
    confirmation_message = await message.answer("Выберите населенный пункт:",
                                                reply_markup=sender_cities_keyboard(cities))
    await state.update_data(confirmation_message_id=confirmation_message.message_id)


@router.callback_query(ShipmentStates.waiting_for_sender_city_selection,
                       F.data.startswith("sender_city:"))
async def select_sender_city(callback: CallbackQuery, state: FSMContext):
    city_ref = callback.data.split(":", 1)[1]
    data = await state.get_data()
    sender_city_options = data.get("sender_city_options", [])
    selected_city = None
    for city in sender_city_options:
        if city["ref"] == city_ref:
            selected_city = city
            break
    if selected_city is None:
        await callback.answer("Этот вариант больше недоступен. Повторите поиск города",
                              show_alert=True)
        await state.set_state(ShipmentStates.waiting_for_sender_city_query)
        await callback.message.edit_text("Введите название города или его начало", reply_markup=None)
        return
    await callback.answer()
    await state.update_data(sender_city_ref=selected_city["ref"],
                            sender_city_name=selected_city["name"])
    await state.set_state(ShipmentStates.waiting_for_sender_warehouse_query)
    await callback.message.edit_text(f"Выбран город: {selected_city['name']}.", reply_markup=None)
    await callback.message.answer("Введите номер отделения или его начало только цифрами без '№'",
                                  reply_markup=sender_warehouse_query_keyboard)


@router.callback_query(ShipmentStates.waiting_for_sender_warehouse_selection,
                       F.data.startswith("sender_warehouse:"))
async def select_sender_warehouse(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    warehouse_ref = callback.data.split(":", 1)[1]
    data = await state.get_data()
    warehouse_options = data.get("sender_warehouse_options", [])
    selected_warehouse = None
    for warehouse in warehouse_options:
        if warehouse["ref"] == warehouse_ref and warehouse["city_ref"] == data.get("sender_city_ref") \
                and warehouse["category"] == "Branch":
            selected_warehouse = warehouse
            break
    if selected_warehouse is None:
        await callback.answer("Этот вариант больше не доступен, повторите поиск отделения",
                              show_alert=True)
        await state.set_state(ShipmentStates.waiting_for_sender_warehouse_query)
        await callback.message.edit_text("Введите номер отделения только цифрами, без символа №",
                                         reply_markup=None)
        return
    await callback.answer()
    await state.update_data(
        sender_warehouse_ref=selected_warehouse["ref"],
        sender_warehouse_name=selected_warehouse["name"],
    )
    await state.set_state(ShipmentStates.choosing_recipient)
    await callback.message.edit_text(f"Отделение отправки выбрано:\n{selected_warehouse['name']}",
                                     reply_markup=None)
    recipient_service = RecipientService(uow=uow)
    recipients = await recipient_service.list_recipients(limit=11, offset=0)

    await callback.message.answer("Получателя можно выбрать из списка, найти по фамилии "
                                  "или создать нового",
                                  reply_markup=shipment_recipient_action_keyboard)
    selection_message = await callback.message.answer("Выберите получателя" if recipients
                                                      else "Получателей пока нет. Создайте нового получателя",
                                                      reply_markup=shipment_recipient_keyboard(
                                                          recipients=recipients[:10],
                                                          page=0,
                                                          has_next=len(recipients) > 10,
                                                      ))

    await state.update_data(confirmation_message_id=selection_message.message_id, recipient_page=0,
                            recipient_search_query=None)


@router.callback_query(ShipmentStates.waiting_for_sender_warehouse_selection,
                       F.data.startswith("sender_warehouse_page:"))
async def change_sender_warehouse_page(callback: CallbackQuery, state: FSMContext):
    page = callback.data.split(":", 1)[1]
    try:
        page = int(page)
    except ValueError:
        await callback.answer("Некорректная страница", show_alert=True)
        return
    data = await state.get_data()
    warehouse_options = data.get("sender_warehouse_options", [])

    page_size = 10

    if page < 0 or page * page_size >= len(warehouse_options):
        await callback.answer("Эта страница не доступна", show_alert=True)
        return
    warehouses = [
        WarehouseInfo.model_validate(item, by_name=True) for item in warehouse_options
    ]
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=sender_warehouse_keyboard(warehouses, page=page))


async def reset_sender_location(state: FSMContext):
    data = await state.get_data()

    keys_to_remove = ("sender_city_ref",
                      "sender_city_name",
                      "sender_city_options",
                      "sender_warehouse_ref",
                      "sender_warehouse_name",
                      "sender_warehouse_options",
                      "confirmation_message_id")

    for key in keys_to_remove:
        data.pop(key, None)
    await state.set_data(data)
    await state.set_state(ShipmentStates.waiting_for_sender_city_query)


async def reset_sender_warehouse(state: FSMContext):
    data = await state.get_data()

    keys_to_remove = ("sender_warehouse_ref",
                      "sender_warehouse_name",
                      "sender_warehouse_options",
                      "confirmation_message_id")

    for key in keys_to_remove:
        data.pop(key, None)
    await state.set_data(data)
    await state.set_state(ShipmentStates.waiting_for_sender_warehouse_query)


@router.message(StateFilter(
    ShipmentStates.waiting_for_sender_warehouse_query,
    ShipmentStates.waiting_for_sender_warehouse_selection
), F.text == "Изменить город отправки")
@router.message(ShipmentStates.choosing_recipient,
                F.text.in_({
                    "Изменить город отправки",
                    "Изменить отделение отправки"
                }))
async def change_sender_location_from_message(message: Message, state: FSMContext):
    data = await state.get_data()
    confirmation_message_id = data.get("confirmation_message_id")
    if confirmation_message_id is not None:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=confirmation_message_id,
                reply_markup=None
            )
        except TelegramBadRequest:
            pass
    if message.text == "Изменить город отправки":
        await reset_sender_location(state)
        await message.answer("Введите название города или его начало",
                             reply_markup=cancel_keyboard)
    else:
        await reset_sender_warehouse(state)
        await message.answer("Введите номер отделения только цифрами, без символа №",
                             reply_markup=sender_warehouse_query_keyboard)


@router.callback_query(ShipmentStates.waiting_for_sender_warehouse_selection,
                       F.data == "sender_city_change")
async def change_sender_city_from_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await reset_sender_location(state)
    await callback.message.answer("Введите название города или его начало",
                                  reply_markup=cancel_keyboard)


@router.message(ShipmentStates.waiting_for_sender_warehouse_query, F.text)
async def search_sender_warehouses(message: Message, state: FSMContext,
                                   nova_post_client: NovaPostClient):
    query = message.text.strip()
    if not query:
        await message.answer("Введите номер отделения только цифрами без '№'")
        return
    data = await state.get_data()
    city_ref = data["sender_city_ref"]
    try:
        warehouses = await nova_post_client.search_sender_warehouses(city_ref, query=query)
    except NovaPostValidationError:
        await message.answer("Введите номер отделения только цифрами, без символа №")
        return

    except NovaPostTimeoutError:
        await message.answer("НП в данный момент не отвечает. Попробуйте позже")
        return
    except NovaPostAPIError:
        await message.answer("Не удалось загрузить отделения. Попробуйте позже")
        return
    if not warehouses:
        await message.answer("Отделение не найдено. Проверьте номер или введите его начало")
        return

    await state.update_data(sender_warehouse_options=[wh.model_dump() for wh in warehouses])
    confirmation_message = await message.answer("Выберите отделение",
                                                reply_markup=sender_warehouse_keyboard(warehouses))
    await state.set_state(ShipmentStates.waiting_for_sender_warehouse_selection)
    await state.update_data(confirmation_message_id=confirmation_message.message_id)


@router.callback_query(ShipmentStates.choosing_recipient,
                       F.data.startswith("shipment_recipients_page:"))
async def change_shipment_recipient_page(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    page = callback.data.split(":", 1)[1]
    data = await state.get_data()
    try:
        page = int(page)
    except ValueError:
        await callback.answer("Некорректная страница", show_alert=True)
        return
    if page < 0:
        await callback.answer("Некорректная страница", show_alert=True)
        return

    page_size = 10
    recipient_service = RecipientService(uow=uow)
    recipients = await recipient_service.list_recipients(limit=page_size + 1,
                                                         offset=page * page_size,
                                                         last_name_query=data.get("recipient_search_query"))

    if not recipients:
        await callback.answer("Эта страница не доступна", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=shipment_recipient_keyboard(
        recipients=recipients[:page_size],
        page=page,
        has_next=len(recipients) > page_size,
    ))

    await state.update_data(recipient_page=page)


@router.callback_query(
    ShipmentStates.waiting_for_sender_city_selection,
    F.data.startswith("sender_city_page:"),
)
async def change_sender_city_page(
        callback: CallbackQuery,
        state: FSMContext,
):
    try:
        page = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Некорректная страница.", show_alert=True)
        return

    data = await state.get_data()
    city_options = data.get("sender_city_options", [])

    page_size = 10
    if page < 0 or page * page_size >= len(city_options):
        await callback.answer("Эта страница недоступна.", show_alert=True)
        return

    cities = [
        CityInfo.model_validate(item, by_name=True)
        for item in city_options
    ]

    await callback.answer()
    await callback.message.edit_reply_markup(
        reply_markup=sender_cities_keyboard(cities, page=page),
    )


@router.callback_query(ShipmentStates.choosing_recipient,
                       F.data.startswith("shipment_recipient:"))
async def select_shipment_recipient(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    recipient = await get_active_recipient_from_callback(callback, uow)
    if recipient is None:
        return
    await callback.answer()
    await state.update_data(recipient_id=str(recipient.id))

    address_service = RecipientAddressService(uow=uow)
    addresses = await address_service.list_addresses(recipient_id=recipient.id)

    await callback.message.edit_reply_markup(reply_markup=None)
    if not addresses:
        await state.update_data(address_creation_origin="shipment")
        await state.set_state(RecipientAddressStates.waiting_for_city_query)
        await callback.message.answer(f"Получатель: {recipient.last_name}, {recipient.first_name}\n\n"
                                      f"Сохраненных адресов пока нет\n"
                                      f"Введите город получения или его начало",
                                      reply_markup=cancel_keyboard)
        return

    await callback.message.answer("Выберите сохраненный адрес или укажите другой", reply_markup=cancel_keyboard)

    lines = [
        f"Получатель: {recipient.last_name}, {recipient.first_name}",
        "",
        "Адреса:"
    ]
    for index, address in enumerate(addresses, start=1):
        lines.append(
            f"{index}. {address.label}\n"
            f"{address.city_name} — {address.warehouse_name}"
        )

    selection_message = await callback.message.answer("\n".join(lines),
                                                      reply_markup=shipment_recipient_addresses_keyboard(addresses))
    await state.update_data(confirmation_message_id=selection_message.message_id)
    await state.set_state(ShipmentStates.choosing_recipient_address)


@router.callback_query(ShipmentStates.choosing_recipient_address,
                       F.data.startswith("shipment_address:"))
async def select_shipment_address(
        callback: CallbackQuery,
        state: FSMContext,
        uow: UnitOfWork):
    address = await get_active_recipient_address_from_callback(callback, uow)
    if address is None:
        return
    data = await state.get_data()
    if str(address.recipient_id) != data.get("recipient_id"):
        await callback.answer("Этот адрес относится к другому получателю.", show_alert=True)
        return
    await callback.answer()
    await state.update_data(recipient_address_id=str(address.id))
    await callback.message.edit_reply_markup(reply_markup=None)
    try:
        await show_shipment_confirmation(callback.message, state, uow)
    except ValueError as exs:
        await state.clear()
        await callback.message.answer(f"{str(exs)}", reply_markup=main_menu)


@router.callback_query(ShipmentStates.choosing_recipient_address,
                       F.data == "shipment_address_create")
async def select_shipment_address_create(
        callback: CallbackQuery,
        state: FSMContext):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.update_data(address_creation_origin="shipment")
    await state.set_state(RecipientAddressStates.waiting_for_city_query)
    await callback.message.answer("Введите город получения или его начало",
                                  reply_markup=cancel_keyboard)


@router.callback_query(ShipmentStates.waiting_for_confirmation,
                       F.data == "shipment_cancel")
async def cancel_shipment_confirmation(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.clear()
    await callback.message.answer("Создание накладной отменено", reply_markup=main_menu)


@router.callback_query(ShipmentStates.choosing_recipient,
                       F.data == "shipment_recipient_search")
async def shipment_recipient_search(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await state.set_state(ShipmentStates.waiting_for_recipient_search_query)
    await callback.message.answer("Введите фамилию получателя или её начало", reply_markup=cancel_keyboard)


@router.message(ShipmentStates.waiting_for_recipient_search_query,
                F.text)
async def shipment_confirmation_search(message: Message, state: FSMContext, uow: UnitOfWork):
    query = message.text.strip()
    recipient_service = RecipientService(uow=uow)
    try:
        recipients = await recipient_service.list_recipients(limit=11, offset=0, last_name_query=query)
    except ValueError:
        await message.answer("Фамилия не может быть пустой. Введите фамилию или её начало")
        return

    if not recipients:
        await message.answer("Получатель не найден")
        return

    selection_message = await message.answer("Выберите получателя",
                                             reply_markup=shipment_recipient_keyboard(recipients[:10], page=0,
                                                                                      has_next=len(recipients) > 10))
    await state.update_data(recipient_search_query=query, recipient_page=0,
                            confirmation_message_id=selection_message.message_id)
    await state.set_state(ShipmentStates.choosing_recipient)


@router.callback_query(ShipmentStates.waiting_for_confirmation, F.data == "shipment_confirm")
async def confirm_shipment_creation(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    await callback.answer()
    data = await state.get_data()
    user_id = callback.from_user.id
    user_name = settings.allowed_telegram_ids[user_id]
    shipment_service = ShipmentService(uow=uow)
    try:
        shipment = await shipment_service.prepare_shipment(shipment_id=uuid.UUID(data['shipment_id']),
                                                           recipient_id=uuid.UUID(data['recipient_id']),
                                                           recipient_address_id=uuid.UUID(data['recipient_address_id']),
                                                           created_by_telegram_id=user_id,
                                                           created_by_name=user_name,
                                                           requested_by_name=data['requested_by_name'],
                                                           shipment_type=data['shipment_type'],
                                                           sender_city_ref=data['sender_city_ref'],
                                                           sender_city_name=data['sender_city_name'],
                                                           sender_warehouse_ref=data['sender_warehouse_ref'],
                                                           sender_warehouse_name=data['sender_warehouse_name'],
                                                           )
    except (KeyError, ValueError, ObjectNotFoundError):
        await callback.message.edit_reply_markup(reply_markup=None)
        await state.clear()
        await callback.message.answer("Не удалось подготовить накладную: данные отсутствуют или больше недоступны. "
                                      "Начните создание заново.", reply_markup=main_menu)
        return

    await uow.commit()
    started = await shipment_service.try_start_creation(shipment_id=shipment.id)
    await uow.commit()
    if not started:
        await callback.message.answer("Создание накладной уже запускалось. Повторный запрос не отправлен")
        return
