import uuid
from html import escape

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from nova_post_bot.enums.recipient_audit import SaveStatus
from nova_post_bot.core.config import settings
from nova_post_bot.core.exceptions import ObjectNotFoundError, ObjectAlreadyExistsError
from nova_post_bot.db.uow import UnitOfWork
from nova_post_bot.handlers.helpers.recipient import get_active_recipient_from_callback
from nova_post_bot.keyboards.cancel import cancel_keyboard
from nova_post_bot.keyboards.main_menu import main_menu
from nova_post_bot.keyboards.recipients import recipients_keyboard, recipient_confirmation_keyboard, \
    recipient_card_keyboard, recipient_edit_keyboard, recipient_edit_confirm_keyboard, \
    recipient_archive_confirmation_keyboard, recipient_draft_edit_keyboard
from nova_post_bot.services.recipient import RecipientService, normalize_phone, normalize_recipient_name
from nova_post_bot.services.recipient_address import RecipientAddressService
from nova_post_bot.states.recipient import RecipientStates, RecipientEditStates, RecipientArchiveStates
from nova_post_bot.states.recipient_address import RecipientAddressStates

router = Router()


@router.message(F.text == "Получатели")
async def choose_recipient(message: Message, state: FSMContext, uow: UnitOfWork):
    await state.clear()
    recipient_service = RecipientService(uow=uow)
    list_of_recipients = await recipient_service.list_recipients()
    if not list_of_recipients:
        await message.answer("Получателей пока нет", reply_markup=recipients_keyboard(list_of_recipients))
        return
    await message.answer("Выберите получателя",
                         reply_markup=recipients_keyboard(list_of_recipients))


@router.callback_query(F.data.startswith("recipient:"))
async def show_recipient(callback: CallbackQuery, uow: UnitOfWork):
    recipient = await get_active_recipient_from_callback(callback, uow)
    if recipient is None:
        return
    await callback.answer()
    address_service = RecipientAddressService(uow=uow)
    addresses = await address_service.list_addresses(recipient_id=recipient.id)
    lines = [
        f"Получатель: {recipient.first_name}, {recipient.last_name}, "
        f"{recipient.phone}",
        "",
        "Адреса: ",
    ]
    if not addresses:
        lines.append("Адресов пока нет")
    else:
        for index, address in enumerate(addresses, start=1):
            lines.append(
                f"{index}. {address.label}\n"
                f"{address.city_name} — {address.warehouse_name}\n"
            )

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=recipient_card_keyboard(
            recipient_id=recipient.id,
            addresses=addresses,
        ),
    )


@router.callback_query(F.data == 'recipient_create')
async def add_recipient(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(RecipientStates.waiting_for_first_name)
    await callback.message.answer("Введите имя получателя:",
                                  reply_markup=cancel_keyboard)


@router.message(RecipientStates.waiting_for_first_name, F.text)
async def process_recipient_first_name(message: Message, state: FSMContext):
    try:
        first_name = normalize_recipient_name(message.text)
    except ValueError:
        await message.answer("Некорректное имя. Имя должно содержать только буквы и не быть пустым. "
                             "Дефис и апостроф допускаются только между буквами")
        return
    await state.update_data(first_name=first_name)
    await state.set_state(RecipientStates.waiting_for_last_name)
    await message.answer("Введите фамилию получателя:",
                         reply_markup=cancel_keyboard)


@router.message(RecipientStates.waiting_for_last_name, F.text)
async def process_recipient_last_name(message: Message, state: FSMContext):
    try:
        last_name = normalize_recipient_name(message.text)
    except ValueError:
        await message.answer("Некорректная фамилия. Фамилия должна содержать только буквы и не быть пустой. "
                             "Дефис и апостроф допускаются только между буквами")
        return
    await state.update_data(last_name=last_name)
    await state.set_state(RecipientStates.waiting_for_phone)
    await message.answer("Введите номер телефона получателя в формате 0XXXXXXXXX:",
                         reply_markup=cancel_keyboard)


@router.message(RecipientStates.waiting_for_phone, F.text)
async def process_recipient_phone(message: Message, state: FSMContext):
    phone_text = message.text.strip()

    try:
        normalized_phone = normalize_phone(phone_text)
    except ValueError:
        await message.answer("Некорректный телефон. Введите 10 цифр, начиная с 0.")
        return
    await state.update_data(phone=phone_text)
    data = await state.get_data()
    confirmation_message = await message.answer(f"Пожалуйста, подтвердите данные:\n"
                                                f"Имя: {data['first_name']}\n"
                                                f"Фамилия: {data['last_name']}\n"
                                                f"Телефон: {normalized_phone}\n"
                                                f"Если всё верно, нажмите: 'Сохранить'. \n"
                                                f"Если хотите сразу добавить адрес получателю, нажмите: 'Сохранить и добавить адрес'.\n"
                                                f"Если заметили опечатку, нажмите 'Редактировать'\n"
                                                f"Чтобы отменить создание, нажмите: 'Отмена'.\n",
                                                reply_markup=recipient_confirmation_keyboard())
    await state.update_data(confirmation_message_id=confirmation_message.message_id)
    await state.set_state(RecipientStates.waiting_for_confirmation)


@router.callback_query(
    RecipientStates.waiting_for_confirmation,
    F.data == "recipient_cancel"
)
async def cancel_recipient_creation(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Создание получателя отменено.", reply_markup=main_menu)


@router.callback_query(
    RecipientStates.waiting_for_confirmation,
    F.data.in_({
        'recipient_confirm',
        'recipient_confirm_with_address'
    })
)
async def confirm_recipient_creation(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    await callback.answer()
    add_address_after_save = (callback.data == "recipient_confirm_with_address")
    data = await state.get_data()
    recipient_service = RecipientService(uow=uow)
    actor_telegram_id = callback.from_user.id
    actor_name = settings.allowed_telegram_ids[actor_telegram_id]
    try:
        recipient, save_status = await recipient_service.create_recipient(first_name=data['first_name'],
                                                                          last_name=data['last_name'],
                                                                          phone=data['phone'],
                                                                          created_by_telegram_id=actor_telegram_id,
                                                                          created_by_name=actor_name)
    except ObjectAlreadyExistsError:
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Получатель с такими данными уже существует.",
                                      reply_markup=main_menu)
        return

    if save_status != SaveStatus.EXISTING:
        await uow.commit()

    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    if save_status == SaveStatus.CREATED:
        result_text = "Получатель сохранен"
    elif save_status == SaveStatus.RESTORED:
        result_text = "Получателя достали из архива и отряхнули от пыли"
    else:
        result_text = "Получатель с такими данными уже существует"

    recipient_text = (f"{result_text}\n"
                      f"{recipient.first_name} {recipient.last_name} ")
    if add_address_after_save:
        await state.update_data(recipient_id=str(recipient.id))
        await state.set_state(RecipientAddressStates.waiting_for_city_query)
        await callback.message.answer(f"{recipient_text}.\n\n"
                                      f" Введите название города или его начало:",
                                      reply_markup=cancel_keyboard)
        return
    await callback.message.answer(recipient_text,
                                  reply_markup=main_menu)


@router.callback_query(F.data.startswith("recipient_edit:"))
async def start_recipient_edit(
        callback: CallbackQuery,
        state: FSMContext,
        uow: UnitOfWork):
    recipient = await get_active_recipient_from_callback(callback, uow)
    if recipient is None:
        return
    await callback.answer()
    await state.clear()
    await state.update_data(recipient_id=str(recipient.id))
    await state.set_state(RecipientEditStates.choosing_field)

    await callback.message.answer(f"Редактирование получателя: {recipient.first_name} "
                                  f"{recipient.last_name}",
                                  reply_markup=cancel_keyboard)

    selection_message = await callback.message.answer("Что хотите изменить?",
                                                      reply_markup=recipient_edit_keyboard(recipient.id))
    await state.update_data(confirmation_message_id=selection_message.message_id)


@router.callback_query(RecipientEditStates.choosing_field,
                       F.data.startswith("edit_field:"))
async def choose_recipient_edit_field(
        callback: CallbackQuery,
        state: FSMContext):
    parts = callback.data.split(":", 2)
    if len(parts) != 3:
        await callback.answer("Некорректная кнопка", show_alert=True)
        return

    _, field_name, recipient_id_text = parts
    data = await state.get_data()
    allowed_edit_fields = ["first_name", "last_name", "phone"]
    if field_name not in allowed_edit_fields:
        await callback.answer("Разрешено менять только имя, фамилию или телефон",
                                      show_alert=True)
        return

    if recipient_id_text != data.get("recipient_id"):
        await callback.answer("Эта кнопка относится к другому получателю. Используйте актуальное меню",
                                      show_alert=True)
        return
    await callback.answer()

    await state.update_data(edit_field=field_name)
    await state.set_state(RecipientEditStates.waiting_for_value)
    await callback.message.edit_reply_markup(reply_markup=None)
    prompts = {
        "first_name": "Введите новое имя получателя",
        "last_name": "Введите новую фамилию получателя",
        "phone": "Введите новый телефон в формате 0ХХХХХХХХХ"
    }
    await callback.message.answer(prompts[field_name], reply_markup=cancel_keyboard)


@router.message(RecipientEditStates.waiting_for_value, F.text)
async def process_recipient_edit_value(
        message: Message,
        state: FSMContext):
    data = await state.get_data()
    field_name = data["edit_field"]
    try:
        new_value = normalize_recipient_field(field_name, message.text)
    except ValueError:
        if field_name == "phone":
            await message.answer("Некорректный телефон. Введите 10 цифр, начиная с 0 в формате 0ХХХХХХХХХ")
        else:
            await message.answer("Имя/фамилия не могут быть пустыми. Допускаются только буквы, "
                                 "дефис и апостроф между буквами")
        return

    await state.update_data(edit_value=new_value)
    field_labels = {
        "first_name": "Имя",
        "last_name": "Фамилия",
        "phone": "Телефон"
    }
    confirmation_message = await message.answer(
        f"Проверьте изменения: \n"
        f"Поле: {field_labels[field_name]}\n"
        f"Новое значение: {new_value}",
        reply_markup=recipient_edit_confirm_keyboard()
    )
    await state.update_data(confirmation_message_id=confirmation_message.message_id)
    await state.set_state(RecipientEditStates.waiting_for_confirmation)


@router.callback_query(StateFilter(RecipientEditStates), F.data == "recipient_edit_cancel")
async def cancel_recipient_edit(
        callback: CallbackQuery,
        state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Редактирование получателя отменено",
                                  reply_markup=main_menu)


@router.callback_query(RecipientEditStates.waiting_for_confirmation,
                       F.data == "recipient_edit_confirm")
async def confirm_recipient_edit(
        callback: CallbackQuery,
        state: FSMContext,
        uow: UnitOfWork):
    await callback.answer()
    data = await state.get_data()

    recipient_service = RecipientService(uow=uow)
    actor_telegram_id = callback.from_user.id
    actor_name = settings.allowed_telegram_ids[actor_telegram_id]

    try:
        recipient = await recipient_service.update_recipient_field(
            recipient_id=uuid.UUID(data['recipient_id']),
            field_name=data['edit_field'],
            new_value=data["edit_value"],
            actor_telegram_id=actor_telegram_id,
            actor_name=actor_name
        )
    except ObjectAlreadyExistsError:
        await callback.message.edit_reply_markup(reply_markup=None)
        await state.set_state(RecipientEditStates.waiting_for_value)
        await callback.message.answer(
            "Получатель с такими данными уже существует.\n"
            "Введите другое значение выбраного поля или нажмите 'Передумал'",
            reply_markup=cancel_keyboard
        )
        return
    except ObjectNotFoundError:
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Получатель не найден, откройте список получателей заново",
            reply_markup=main_menu
        )
        return
    except ValueError:
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Не удалось изменить данные: получатель архивирован "
                                      "или новое значение не корректно. Начните редактирование заново",
                                      reply_markup=main_menu)
        return
    await uow.commit()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Новые данные получателя сохранены:\n"
                                  f"Имя: {recipient.first_name}\n"
                                  f"Фамилия: {recipient.last_name}\n"
                                  f"Телефон: {recipient.phone}",
                                  reply_markup=main_menu)


@router.callback_query(F.data.startswith("recipient_archive:"))
async def start_recipient_archive(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    recipient = await get_active_recipient_from_callback(callback, uow)
    if recipient is None:
        return
    await callback.answer()
    await state.clear()
    await state.update_data(recipient_id=str(recipient.id))
    await state.set_state(RecipientArchiveStates.waiting_for_confirmation)
    await callback.message.answer("Для выхода без изменений нажмите 'Передумал' или отправьте '/cancel'",
                                  reply_markup=cancel_keyboard)
    full_name = escape(f"{recipient.first_name} {recipient.last_name}")
    confirmation_message = await callback.message.answer(
        "📦 <b>Архивирование получателя</b>\n\n"
        f"👤 <b><u>{full_name}</u></b>\n\n"
        "Получатель исчезнет из активного списка.\n"
        "Его адреса и история сохранятся.\n\n"
        "Подтвердить архивирование?",
        parse_mode="HTML",
        reply_markup=recipient_archive_confirmation_keyboard(),
    )
    await state.update_data(confirmation_message_id=confirmation_message.message_id)


@router.callback_query(RecipientArchiveStates.waiting_for_confirmation,
                       F.data.startswith("recipient_archive_cancel"))
async def cancel_recipient_archive(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Архивирование получателя отменено",
        reply_markup=main_menu
    )


@router.callback_query(RecipientArchiveStates.waiting_for_confirmation,
                       F.data.startswith("recipient_archive_confirm"))
async def confirm_recipient_archive(callback: CallbackQuery, state: FSMContext, uow: UnitOfWork):
    await callback.answer()
    data = await state.get_data()
    recipient_service = RecipientService(uow=uow)
    actor_telegram_id = callback.from_user.id
    actor_name = settings.allowed_telegram_ids[actor_telegram_id]
    try:
        recipient = await recipient_service.archive_recipient(
            recipient_id=uuid.UUID(data['recipient_id']),
            actor_telegram_id=actor_telegram_id,
            actor_name=actor_name
        )
    except ObjectNotFoundError:
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "Получатель не найден",
            reply_markup=main_menu
        )
        return
    await uow.commit()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"Получатель {recipient.first_name} {recipient.last_name} \n"
        f"архивирован",
        reply_markup=main_menu
    )


@router.callback_query(RecipientStates.waiting_for_confirmation,
                       F.data == "recipient_draft_edit")
async def start_recipient_draft_edit(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(RecipientStates.choosing_edit_field)
    await callback.message.edit_text("Что хотите изменить?",
                                     reply_markup=recipient_draft_edit_keyboard())


@router.callback_query(RecipientStates.choosing_edit_field,
                       F.data.startswith("draft_field:"))
async def choose_recipient_draft_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":", 1)[1]
    allowed_fields = ["first_name", "last_name", "phone"]
    if field not in allowed_fields:
        await callback.answer("Разрешено редактировать только имя, фамилию или телефон",
                              show_alert=True)
        return
    await callback.answer()
    await state.update_data(edit_field=field)
    await state.set_state(RecipientStates.waiting_for_edit_value)
    prompts = {
        "first_name": "Введите новое имя получателя",
        "last_name": "Введите новую фамилию получателя",
        "phone": "Введите новый телефон в формате 0ХХХХХХХХХ"
    }
    await callback.message.edit_text(prompts[field], reply_markup=None)


@router.message(RecipientStates.waiting_for_edit_value, F.text)
async def process_edit_draft_field(message: Message, state: FSMContext):
    data = await state.get_data()
    field_name = data["edit_field"]
    try:
        new_value = normalize_recipient_field(field_name, message.text)
    except ValueError:
        if field_name == "phone":
            await message.answer("Некорректный телефон. Введите 10 цифр, начиная с 0 в формате 0ХХХХХХХХХ")
        else:
            await message.answer("Имя/фамилия не могут быть пустыми. Допускаются только буквы, "
                                 "дефис и апостроф между буквами")
        return

    if field_name == "phone":
        new_value = message.text.strip()

    await state.update_data({field_name: new_value})

    data = await state.get_data()
    confirmation_message = await message.answer("Проверьте данные получателя: "
                                                f"Имя: {data['first_name']} "
                                                f"Фамилия: {data['last_name']}, "
                                                f"Телефон: {data['phone']}",
                                                reply_markup=recipient_confirmation_keyboard())
    await state.update_data(confirmation_message_id=confirmation_message.message_id)
    await state.set_state(RecipientStates.waiting_for_confirmation)


@router.callback_query(RecipientStates.choosing_edit_field,
                       F.data == "recipient_draft_back")
async def return_to_recipient_confirmation(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await callback.message.edit_text(f"Пожалуйста, подтвердите данные:\n"
                                     f"Имя: {data['first_name']}\n"
                                     f"Фамилия: {data['last_name']}\n"
                                     f"Телефон: {normalize_phone(data['phone'])}\n"
                                     f"Если всё верно, нажмите: 'Сохранить'. \n"
                                     f"Если хотите сразу добавить адрес получателю, нажмите: 'Сохранить и добавить адрес'.\n"
                                     f"Если заметили опечатку, нажмите 'Редактировать'\n"
                                     f"Чтобы отменить создание, нажмите: 'Отмена'.\n",
                                     reply_markup=recipient_confirmation_keyboard())
    await state.set_state(RecipientStates.waiting_for_confirmation)


def normalize_recipient_field(field_name: str, value: str) -> str:
    if field_name == "phone":
        return normalize_phone(value)

    if field_name in ["first_name", "last_name"]:
        return normalize_recipient_name(value)

    raise ValueError("Unknown recipient field name")
