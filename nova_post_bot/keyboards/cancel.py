from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

cancel_button = KeyboardButton(text="Передумал")

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [cancel_button],
    ],
    resize_keyboard=True
)
