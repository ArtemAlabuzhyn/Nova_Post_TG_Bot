from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from nova_post_bot.keyboards.main_menu import main_menu
from nova_post_bot.states.recipient import RecipientStates, RecipientEditStates, RecipientArchiveStates
from nova_post_bot.states.recipient_address import RecipientAddressStates, RecipientAddressEditStates
from nova_post_bot.states.tracking import TrackingStates

router = Router()


@router.message(TrackingStates.waiting_for_number, Command("cancel"))
@router.message(TrackingStates.waiting_for_number, F.text == "Передумал")
@router.message(StateFilter(RecipientStates), Command("cancel"))
@router.message(StateFilter(RecipientStates), F.text == "Передумал")
@router.message(StateFilter(RecipientAddressStates), Command("cancel"))
@router.message(StateFilter(RecipientAddressStates), F.text == "Передумал")
@router.message(StateFilter(RecipientEditStates), Command("cancel"))
@router.message(StateFilter(RecipientEditStates), F.text == "Передумал")
@router.message(StateFilter(RecipientArchiveStates), Command("cancel"))
@router.message(StateFilter(RecipientArchiveStates), F.text == "Передумал")
@router.message(StateFilter(RecipientAddressEditStates), Command("cancel"))
@router.message(StateFilter(RecipientAddressEditStates), F.text == "Передумал")
async def cancel_current_action(message: Message, state: FSMContext):
    data = await state.get_data()
    confirmation_message_id = data.get("confirmation_message_id")
    if confirmation_message_id is not None:
        try:
            await message.bot.edit_message_reply_markup(
                chat_id=message.chat.id,
                message_id=confirmation_message_id,
                reply_markup=None)
        except TelegramBadRequest:
            pass
    await state.clear()
    await message.answer("Ну и ... ладно", reply_markup=main_menu)
