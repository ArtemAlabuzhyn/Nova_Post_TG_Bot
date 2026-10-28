import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from html import escape

from nova_post_bot.clients.nova_post import NovaPostClient
from nova_post_bot.core.config import settings
from nova_post_bot.core.exceptions import NovaPostTimeoutError, NovaPostAPIError, NovaPostValidationError, \
    ObjectNotFoundError
from nova_post_bot.db.uow import UnitOfWork
from nova_post_bot.enums.recipient_audit import SaveStatus
from nova_post_bot.handlers.helpers.recipient import get_active_recipient_address_from_callback
from nova_post_bot.keyboards.cancel import cancel_keyboard
from nova_post_bot.keyboards.main_menu import main_menu
from nova_post_bot.keyboards.recipient_addresses import cities_keyboard, warehouse_keyboard, \
    address_confirmation_keyboard, recipient_address_card_keyboard, recipient_address_archive_confirmation_keyboard
from nova_post_bot.schemas.warehouse import WarehouseInfo
from nova_post_bot.services.recipient import RecipientService
from nova_post_bot.services.recipient_address import RecipientAddressService
from nova_post_bot.states.recipient_address import RecipientAddressStates, RecipientAddressEditStates

router = Router()


@router.message(RecipientAddressStates.waiting_for_city_query, F.text)
async def choose_recipient_city(message: Message,
                                state: FSMContext,
                                nova_post_client: NovaPostClient):
    query = message.text.strip()
    if not query:
        await message.answer("Введите название города или его начало")
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

    await state.update_data(city_options=[city.model_dump() for city in cities])
    await state.set_state(RecipientAddressStates.waiting_for_city_selection)
    await message.answer("Выберите населенный пункт:",
                         reply_markup=cities_keyboard(cities))


@router.callback_query(
    RecipientAddressStates.waiting_for_city_selection,
    F.data.startswith("recipient_city:")
)
async def select_recipient_city(callback: CallbackQuery, state: FSMContext):
    city_ref = callback.data.split(":", 1)[1]
    data = await state.get_data()
    city_options = data.get("city_options", [])
    selected_city = None
    for city in city_options:
        if city["ref"] == city_ref:
            selected_city = city
            break
    if selected_city is None:
        await callback.answer("Этот вариант больше недоступен. Повторите поиск города",
                              show_alert=True)
        await state.set_state(RecipientAddressStates.waiting_for_city_query)
        await callback.message.edit_text("Введите название города или его начало")
        return

    await callback.answer()
    await state.update_data(
        city_ref=selected_city["ref"],
        city_name=selected_city["name"],
    )
    await state.set_state(RecipientAddressStates.waiting_for_warehouse_query)
    await callback.message.edit_text(f"Выбран город: {selected_city['name']}.")
    await callback.message.answer("Введите номер отделения/почтомата или его начало только цифрами, без №",
                                  reply_markup=cancel_keyboard)


@router.message(RecipientAddressStates.waiting_for_warehouse_query, F.text)
async def choose_recipient_warehouse(message: Message, state: FSMContext, nova_post_client: NovaPostClient):
    query = message.text.strip()
    if not query:
        await message.answer("Введите номер отделения или почтомата")
        return
    data = await state.get_data()
    city_ref = data["city_ref"]
    try:
        warehouses = await nova_post_client.search_warehouses(city_ref=city_ref, query=query)
    except NovaPostValidationError:
        await message.answer("Введите номер отделения или почтомата только цифрами, без символа №")
        return

    except NovaPostTimeoutError:
        await message.answer("НП в данный момент не отвечает. Попробуйте позже.")
        return

    except NovaPostAPIError:
        await message.answer("Не удалось загрузить отделения и почтоматы. Попробуйте позже")
        return

    if not warehouses:
        await message.answer("Отделение/почтомат не найден. Проверьте номер или введите его начало")
        return
    await state.update_data(warehouse_options=[wh.model_dump() for wh in warehouses])
    await message.answer("Выберите отделение/почтомат:",
                         reply_markup=warehouse_keyboard(warehouses))
    await state.set_state(RecipientAddressStates.waiting_for_warehouse_selection)


@router.callback_query(RecipientAddressStates.waiting_for_warehouse_selection,
                       F.data.startswith("recipient_warehouse:"))
async def select_recipient_warehouse(callback: CallbackQuery, state: FSMContext):
    warehouse_ref = callback.data.split(":", 1)[1]
    data = await state.get_data()
    warehouse_options = data.get("warehouse_options", [])
    selected_warehouse = None
    for warehouse in warehouse_options:
        if warehouse["ref"] == warehouse_ref and warehouse["city_ref"] == data.get("city_ref"):
            selected_warehouse = warehouse
            break
    if selected_warehouse is None:
        await callback.answer("Этот вариант больше не доступен, повторите поиск отделения/почтомата",
                              show_alert=True)
        await state.set_state(RecipientAddressStates.waiting_for_warehouse_query)
        await callback.message.edit_text("Введите номер отделения/почтомата или его начало только цифрами, без №")
        return
    await callback.answer()
    await state.update_data(
        warehouse_ref=selected_warehouse["ref"],
        warehouse_name=selected_warehouse["name"],
    )
    await state.set_state(RecipientAddressStates.waiting_for_label)
    await callback.message.edit_text(f"Выбрано: {selected_warehouse['name']}.")
    await callback.message.answer("Как хотите назвать этот шаблон чтобы проще было выбирать из списка?\n"
                                  "Например 'Возле дома', 'Почтомат (номер)'",
                                  reply_markup=cancel_keyboard)


@router.message(RecipientAddressStates.waiting_for_label, F.text)
async def process_recipient_address_label(message: Message, state: FSMContext):
    label = message.text.strip()
    if not label:
        await message.answer("Просьба ввести название шаблона")
        return
    await state.update_data(label=label)
    data = await state.get_data()
    confirmation_message = await message.answer(
        f"Проверьте адрес:\n"
        f"Название: {data['label']}\n"
        f"Город: {data['city_name']}\n"
        f"Отделение/почтомат: {data['warehouse_name']}",
        reply_markup=address_confirmation_keyboard()
    )
    await state.update_data(confirmation_message_id=confirmation_message.message_id)
    await state.set_state(RecipientAddressStates.waiting_for_confirmation)


@router.callback_query(RecipientAddressStates.waiting_for_confirmation,
                       F.data == "recipient_address_cancel")
async def cancel_recipient_address_creation(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Добавление адреса отменено", reply_markup=main_menu)


@router.callback_query(RecipientAddressStates.waiting_for_confirmation,
                       F.data == "recipient_address_confirmation")
async def confirm_recipient_address_creation(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    await callback.answer()
    data = await state.get_data()
    address_service = RecipientAddressService(uow=uow)
    actor_telegram_id = callback.from_user.id
    actor_name = settings.allowed_telegram_ids[actor_telegram_id]
    try:
        address, save_status = await address_service.add_address(recipient_id=uuid.UUID(data['recipient_id']),
                                                                 label=data['label'],
                                                                 city_ref=data['city_ref'],
                                                                 city_name=data['city_name'],
                                                                 warehouse_ref=data['warehouse_ref'],
                                                                 warehouse_name=data['warehouse_name'],
                                                                 actor_telegram_id=actor_telegram_id,
                                                                 actor_name=actor_name)
    except ObjectNotFoundError:
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(f"Получатель не найден. Откройте список получателей заново",
                                      reply_markup=main_menu)
        return
    except ValueError:
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Не удалось сохранить адрес: данные некорректны "
            "или получатель архивирован. Начните добавление адреса заново",
            reply_markup=main_menu
        )
        return
    await uow.commit()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)

    if save_status == SaveStatus.CREATED:
        result_text = "Адрес сохранен"
    elif save_status == SaveStatus.RESTORED:
        result_text = "Адрес восстановлен из архива"
    else:
        result_text = "Этот адрес уже есть у получателя"
    await callback.message.answer(
        f"{result_text}\n"
        f"Название шаблона: {address.label}\n"
        f"Город: {address.city_name}\n"
        f"Отделение/почтомат: {address.warehouse_name}",
        reply_markup=main_menu
    )


@router.callback_query(RecipientAddressStates.waiting_for_warehouse_selection, F.data.startswith("warehouse_page:"))
async def change_warehouse_page(callback: CallbackQuery, state: FSMContext):
    page = callback.data.split(":", 1)[1]
    try:
        page = int(page)
    except ValueError:
        await callback.answer("Некорректная страница", show_alert=True)
        return
    data = await state.get_data()
    warehouse_options = data.get("warehouse_options", [])

    page_size = 10
    if page < 0 or page * page_size >= len(warehouse_options):
        await callback.answer("Эта страница не доступна", show_alert=True)
        return
    warehouses = [
        WarehouseInfo.model_validate(item, by_name=True)
        for item in warehouse_options
    ]
    await callback.answer()
    await callback.message.edit_reply_markup(
        reply_markup=warehouse_keyboard(warehouses, page=page)
    )


@router.callback_query(F.data.startswith("recipient_address_add:"))
async def start_recipient_address_creation(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    recipient_id_text = callback.data.split(":", 1)[1]

    try:
        recipient_id = uuid.UUID(recipient_id_text)
    except ValueError:
        await callback.answer("Некорректный ID получателя", show_alert=True)
        return

    recipient_service = RecipientService(uow=uow)
    try:
        recipient = await recipient_service.get_by_id(recipient_id=recipient_id)
    except ObjectNotFoundError:
        await callback.answer("Получатель не найден", show_alert=True)
        return
    if not recipient.is_active:
        await callback.answer("Получатель архивирован", show_alert=True)
        return

    await callback.answer()
    await state.clear()
    await state.update_data(recipient_id=str(recipient_id))
    await state.set_state(RecipientAddressStates.waiting_for_city_query)
    await callback.message.answer("Введите название города или его начало",
                                  reply_markup=cancel_keyboard)


@router.callback_query(F.data.startswith("recipient_address:"))
async def show_recipient_address(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    address = await get_active_recipient_address_from_callback(callback, uow)
    if address is None:
        return

    await callback.answer()
    await callback.message.answer(
        f"Название шаблона: {address.label}\n"
        f"Город: {address.city_name}\n"
        f"Отделение/почтомат: {address.warehouse_name}",
        reply_markup=recipient_address_card_keyboard(address.id)
    )


@router.callback_query(F.data.startswith("address_rename:"))
async def start_recipient_address_rename(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    address = await get_active_recipient_address_from_callback(callback, uow)
    if address is None:
        return

    await callback.answer()
    await state.clear()
    await state.update_data(address_id=str(address.id), old_label=address.label)
    await state.set_state(RecipientAddressEditStates.waiting_for_label)
    await callback.message.answer(f"Текущее название шаблона: {address.label}\n\n"
                                  f"Введите новое название",
                                  reply_markup=cancel_keyboard)


@router.message(RecipientAddressEditStates.waiting_for_label, F.text)
async def edit_address_label(message: Message, state: FSMContext, uow: UnitOfWork):
    label = message.text.strip()
    if not label:
        await message.answer("Название шаблона не может быть пустым")
        return
    data = await state.get_data()
    address_id = uuid.UUID(data["address_id"])
    address_service = RecipientAddressService(uow=uow)

    actor_telegram_id = message.from_user.id
    actor_name = settings.allowed_telegram_ids[actor_telegram_id]

    try:
        address = await address_service.get_by_id(address_id=address_id)
        old_label = address.label

        address = await address_service.rename_address_label(
            address_id=address_id,
            new_label=label,
            actor_telegram_id=actor_telegram_id,
            actor_name=actor_name)
    except ObjectNotFoundError:
        await state.clear()
        await message.answer("Адрес или получатель не найден. Откройте список получателей заново",
                             reply_markup=main_menu)
        return
    except ValueError:
        await state.clear()
        await message.answer(
            "Не удалось переименовать шаблон. Адрес или получатель архивированы",
            reply_markup=main_menu)
        return

    if old_label == address.label:
        await state.clear()
        await message.answer("Название не изменилось, шаблон уже так и называется", reply_markup=main_menu)
        return

    await uow.commit()
    await state.clear()

    await message.answer(f"Название шаблона изменено на: \n\n"
                         f"<b><u> {escape(address.label)}</u></b>",
                         parse_mode="HTML",
                         reply_markup=main_menu)


@router.callback_query(F.data.startswith("address_archive:"))
async def start_recipient_address_archive(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    address = await get_active_recipient_address_from_callback(callback, uow)
    if address is None:
        return
    await callback.answer()
    await state.clear()
    await state.update_data(address_id=str(address.id))
    await state.set_state(RecipientAddressStates.waiting_for_archive_confirmation)

    await callback.message.answer(
        "Подтвердите архивирование или нажмите передумал",
        reply_markup=cancel_keyboard
    )
    confirmation_message = await callback.message.answer(
        f"Архивировать шаблон <b>{escape(address.label)}</b>?\n\n"
        f"Город: {escape(address.city_name)}\n"
        f"Отделение/почтомат: {escape(address.warehouse_name)}\n\n"
        "Он исчезнет из списка активных адресов. История сохранится.",
        parse_mode="HTML",
        reply_markup=recipient_address_archive_confirmation_keyboard(),
    )

    await state.update_data(confirmation_message_id=confirmation_message.message_id)


@router.callback_query(RecipientAddressStates.waiting_for_archive_confirmation,
                       F.data == "address_archive_cancel")
async def cancel_recipient_address_archive(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Архивирование адреса отменено", reply_markup=main_menu)


@router.callback_query(RecipientAddressStates.waiting_for_archive_confirmation,
                       F.data == "address_archive_confirm")
async def confirm_recipient_address_archive(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    await callback.answer()
    data = await state.get_data()
    address_service = RecipientAddressService(uow=uow)
    actor_telegram_id = callback.from_user.id
    actor_name = settings.allowed_telegram_ids[actor_telegram_id]
    try:
        address = await address_service.archive_recipient_address(
            address_id=uuid.UUID(data["address_id"]),
            actor_telegram_id=actor_telegram_id,
            actor_name=actor_name
        )
    except ObjectNotFoundError:
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Адрес получателя не найден", reply_markup=main_menu)
        return
    except ValueError:
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Нельзя архивировать адрес архивного получателя",
                                      reply_markup=main_menu)
        return
    await uow.commit()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"Шаблон <b><u>{escape(address.label)}</u></b> архивирован.",
                                  parse_mode="HTML",
                                  reply_markup=main_menu)
