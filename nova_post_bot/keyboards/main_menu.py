from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def build_main_menu(*, show_request_info: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="Отследить ТТН")],
        [KeyboardButton(text="Мои отправки")],
        [KeyboardButton(text="Создать накладную")],
        [KeyboardButton(text="Получатели")]
    ]
    if show_request_info:
        keyboard.append([KeyboardButton(text="Кто запросил")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,)