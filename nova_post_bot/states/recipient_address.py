from aiogram.fsm.state import StatesGroup, State


class RecipientAddressStates(StatesGroup):
    waiting_for_city_query = State()
    waiting_for_city_selection = State()
    waiting_for_warehouse_query = State()
    waiting_for_warehouse_selection = State()
    waiting_for_label = State()
    waiting_for_confirmation = State()
    waiting_for_archive_confirmation = State()

class RecipientAddressEditStates(StatesGroup):
    waiting_for_label = State()

