from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

cancel_button = KeyboardButton(text="Передумал")

tracking_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [cancel_button],
    ],
    resize_keyboard=True
)
