from aiogram.fsm.state import StatesGroup, State


class TrackingStates(StatesGroup):
    waiting_for_number = State()
