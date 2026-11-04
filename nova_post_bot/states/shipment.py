from aiogram.fsm.state import StatesGroup, State


class ShipmentStates(StatesGroup):
    waiting_for_requester = State()
    choosing_type = State()
    waiting_for_sender_city_query = State()
    waiting_for_sender_city_selection = State()
    waiting_for_sender_warehouse_query = State()
    waiting_for_sender_warehouse_selection = State()
    choosing_recipient = State()
    choosing_recipient_address = State()
    waiting_for_confirmation = State()
    waiting_for_recipient_search_query = State()