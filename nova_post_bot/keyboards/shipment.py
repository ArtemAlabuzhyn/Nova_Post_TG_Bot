from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from nova_post_bot.models.recipient import Recipient
from nova_post_bot.models.recipient_address import RecipientAddress
from nova_post_bot.schemas.city import CityInfo
from nova_post_bot.schemas.warehouse import WarehouseInfo
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def shipment_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Документы", callback_data="shipment_type:documents")
    builder.adjust(1)
    return builder.as_markup()


def sender_cities_keyboard(
        cities: list[CityInfo],
        page: int = 0,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    page_size = 10
    start = page * page_size
    end = start + page_size

    for city in cities[start:end]:
        builder.button(
            text=f"{city.settlement_type} {city.name}, {city.area_name} обл.",
            callback_data=f"sender_city:{city.ref}",
        )

    builder.adjust(1)

    navigation = []
    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"sender_city_page:{page - 1}",
            )
        )

    if end < len(cities):
        navigation.append(
            InlineKeyboardButton(
                text="Далее ➡️",
                callback_data=f"sender_city_page:{page + 1}",
            )
        )

    if navigation:
        builder.row(*navigation)

    return builder.as_markup()


def sender_warehouse_keyboard(warehouses: list[WarehouseInfo],
                              page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    page_size = 10
    start = page * page_size
    end = start + page_size
    for warehouse in warehouses[start:end]:
        builder.button(
            text=warehouse.name,
            callback_data=f"sender_warehouse:{warehouse.ref}",
        )
    builder.adjust(1)
    navigation = []
    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"sender_warehouse_page:{page - 1}"
            )
        )
    if end < len(warehouses):
        navigation.append(
            InlineKeyboardButton(
                text="Далее ➡️",
                callback_data=f"sender_warehouse_page:{page + 1}"
            )
        )
    if navigation:
        builder.row(*navigation)
    builder.row(InlineKeyboardButton(text="Изменить город отправки", callback_data="sender_city_change"))
    return builder.as_markup()


def shipment_recipient_keyboard(
        recipients: list[Recipient],
        page: int,
        has_next: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for recipient in recipients:
        builder.button(
            text=f"{recipient.first_name} {recipient.last_name}",
            callback_data=f"shipment_recipient:{recipient.id}",
        )
    builder.adjust(1)
    navigation = []
    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"shipment_recipients_page:{page - 1}"
            )
        )
    if has_next:
        navigation.append(
            InlineKeyboardButton(
                text="Далее ➡️",
                callback_data=f"shipment_recipients_page:{page + 1}"
            )
        )
    if navigation:
        builder.row(*navigation)

    builder.row(
        InlineKeyboardButton(
            text="Найти по фамилии",
            callback_data="shipment_recipient_search"
        )
    )
    builder.row(InlineKeyboardButton(
        text="Создать получателя",
        callback_data="shipment_recipient_create"
    ))
    return builder.as_markup()


sender_warehouse_query_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Изменить город отправки")],
        [KeyboardButton(text="Передумал")]
    ],
    resize_keyboard=True
)

shipment_recipient_action_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Изменить город отправки")],
        [KeyboardButton(text="Изменить отделение отправки")],
        [KeyboardButton(text="Передумал")],
    ],
    resize_keyboard=True
)


def shipment_recipient_addresses_keyboard(
        addresses: list[RecipientAddress]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for address in addresses:
        builder.button(text=f"📍{address.label}",
                       callback_data=f"shipment_address:{address.id}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="Указать другой адрес",
                                     callback_data="shipment_address_create"))
    return builder.as_markup()


def shipment_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Создать накладную", callback_data="shipment_confirm")
    builder.button(text="Отмена", callback_data="shipment_cancel")
    builder.adjust(1)
    return builder.as_markup()


def shipment_recipient_matches_keyboard(
        recipients: list[Recipient]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for recipient in recipients:
        builder.button(
            text=f"{recipient.first_name} {recipient.last_name}",
            callback_data=f"shipment_recipient:{recipient.id}",
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(
        text="Продолжить создание",
        callback_data="shipment_recipient_create_continue"
    ))
    return builder.as_markup()
