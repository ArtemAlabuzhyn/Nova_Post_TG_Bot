from aiogram.fsm.state import StatesGroup, State


class ShipmentRequestInfoStates(StatesGroup):
    waiting_for_number = State()