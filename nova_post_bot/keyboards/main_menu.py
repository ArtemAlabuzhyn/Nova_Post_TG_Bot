from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


track_button = KeyboardButton(text="Отследить ТТН")
shipments_button = KeyboardButton(text="Мои отправки")
create_shipment_button = KeyboardButton(text="Создать накладную")
recipients = KeyboardButton(text="Получатели")

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [track_button],
        [shipments_button],
        [create_shipment_button],
        [recipients]
    ],
    resize_keyboard=True
)