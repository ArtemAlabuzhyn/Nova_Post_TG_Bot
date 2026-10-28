import uuid

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from nova_post_bot.models.recipient import Recipient
from nova_post_bot.models.recipient_address import RecipientAddress


def recipients_keyboard(recipients: list[Recipient]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for recipient in recipients:
        builder.button(text=f"{recipient.last_name}, {recipient.first_name}",
                       callback_data=f"recipient:{recipient.id}")

    builder.button(text="Добавить получателя", callback_data="recipient_create")

    builder.adjust(1)
    return builder.as_markup()

def recipient_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="Сохранить", callback_data="recipient_confirm")
    builder.button(text="Сохранить и добавить адрес", callback_data="recipient_confirm_with_address")
    builder.button(text="Редактировать", callback_data="recipient_draft_edit")
    builder.button(text="Отмена", callback_data="recipient_cancel")
    builder.adjust(1)
    return builder.as_markup()

def recipient_card_keyboard(recipient_id: uuid.UUID,
                            addresses: list[RecipientAddress]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for address in addresses:
        builder.button(text=f"📍 {address.label}",
                       callback_data=f"recipient_address:{address.id}")
    builder.button(text="Добавить адрес", callback_data=f"recipient_address_add:{recipient_id}")
    builder.button(text="Редактировать данные",
                   callback_data=f"recipient_edit:{recipient_id}")
    builder.button(text="Архивировать получателя",
                   callback_data=f"recipient_archive:{recipient_id}")
    builder.adjust(1)
    return builder.as_markup()

def recipient_edit_keyboard(recipient_id: uuid.UUID) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Имя", callback_data=f"edit_field:first_name:{recipient_id}")
    builder.button(text="Фамилия", callback_data=f"edit_field:last_name:{recipient_id}")
    builder.button(text="Телефон", callback_data=f"edit_field:phone:{recipient_id}")
    builder.button(text="Отмена", callback_data="recipient_edit_cancel")
    builder.adjust(1)
    return builder.as_markup()

def recipient_edit_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Сохранить изменения", callback_data="recipient_edit_confirm")
    builder.button(text="Отмена", callback_data="recipient_edit_cancel")
    builder.adjust(2)
    return builder.as_markup()

def recipient_archive_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Да архивировать", callback_data="recipient_archive_confirm")
    builder.button(text="Отмена", callback_data="recipient_archive_cancel")
    builder.adjust(2)
    return builder.as_markup()

def recipient_draft_edit_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Имя", callback_data="draft_field:first_name")
    builder.button(text="Фамилия", callback_data="draft_field:last_name")
    builder.button(text="Телефон", callback_data="draft_field:phone"),
    builder.button(text="Отмена", callback_data="recipient_draft_back")
    builder.adjust(1)
    return builder.as_markup()
