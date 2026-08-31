from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


track_button = KeyboardButton(text="Отследить ТТН")
shipments_button = KeyboardButton(text="Мои отправки")
create_shipment_button = KeyboardButton(text="Создать накладную")

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [track_button],
        [shipments_button],
        [create_shipment_button]
    ],
    resize_keyboard=True
)