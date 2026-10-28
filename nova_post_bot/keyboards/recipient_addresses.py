import uuid

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from nova_post_bot.schemas.city import CityInfo
from nova_post_bot.schemas.warehouse import WarehouseInfo


def cities_keyboard(cities: list[CityInfo]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in cities:
        builder.button(
            text=f"{city.settlement_type} {city.name}, {city.area_name} обл.",
            callback_data=f"recipient_city:{city.ref}")
    builder.adjust(1)
    return builder.as_markup()

def warehouse_keyboard(warehouses: list[WarehouseInfo],
                       page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    page_size = 10
    start = page * page_size
    end = start + page_size
    for warehouse in warehouses[start:end]:
        builder.button(
            text=warehouse.name,
            callback_data=f"recipient_warehouse:{warehouse.ref}"
        )
    builder.adjust(1)
    navigation = []
    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"warehouse_page:{page-1}"
            )
        )
    if end < len(warehouses):
        navigation.append(
            InlineKeyboardButton(
                text="Далее ➡️",
                callback_data=f"warehouse_page:{page+1}"
            )
        )
    if navigation:
        builder.row(*navigation)
    return builder.as_markup()

def address_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text='Сохранить адрес', callback_data='recipient_address_confirmation')
    builder.button(text="Отмена", callback_data='recipient_address_cancel')
    builder.adjust(2)
    return builder.as_markup()

def recipient_address_card_keyboard(address_id: uuid.UUID) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Переименовать", callback_data=f"address_rename:{address_id}")
    builder.button(text="Архивировать адрес", callback_data=f"address_archive:{address_id}")
    builder.adjust(1)
    return builder.as_markup()

def recipient_edit_address_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Сохранить", callback_data="address_rename_confirm")
    builder.button(text="Отменить", callback_data="address_rename_cancel")
    builder.adjust(2)
    return builder.as_markup()

def recipient_address_archive_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Архивировать", callback_data="address_archive_confirm")
    builder.button(text="Отмена", callback_data="address_archive_cancel")
    builder.adjust(2)
    return builder.as_markup()