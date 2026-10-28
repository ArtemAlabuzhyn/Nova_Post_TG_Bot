from aiogram.fsm.state import StatesGroup, State


class RecipientStates(StatesGroup):
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_phone = State()
    waiting_for_confirmation = State()
    choosing_edit_field = State()
    waiting_for_edit_value = State()

class RecipientEditStates(StatesGroup):
    choosing_field = State()
    waiting_for_value = State()
    waiting_for_confirmation = State()


class RecipientArchiveStates(StatesGroup):
    waiting_for_confirmation = State()
