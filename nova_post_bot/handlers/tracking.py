from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from nova_post_bot.core.exceptions import NovaPostAPIError, NovaPostValidationError, NovaPostTimeoutError
from nova_post_bot.formatters.tracking import format_tracking_info
from nova_post_bot.keyboards.cancel import cancel_keyboard
from nova_post_bot.keyboards.main_menu import main_menu
from nova_post_bot.services.tracking import TrackingService
from nova_post_bot.states.tracking import TrackingStates

router = Router()


@router.message(F.text == "Отследить ТТН")
async def tracking(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(TrackingStates.waiting_for_number)
    await message.answer("Введите номер ТТН:", reply_markup=cancel_keyboard)


@router.message(TrackingStates.waiting_for_number, F.text)
async def process_tracking_number(message: Message, state: FSMContext,
                                  tracking_service: TrackingService):
    try:
        tracking_items = await tracking_service.get_tracking_info(number=message.text)

    except NovaPostValidationError:
        await message.answer("Некорректный номер ТТН. Проверьте номер: он должен содержать 14 цифр.")
        return
    except NovaPostTimeoutError:
        await message.answer("НП в данный момент не отвечает. Попробуйте позже.")
        return

    except NovaPostAPIError:
        await message.answer("Не удалось получить статус. Попробуйте позже или проверьте номер ТТН")
        return

    await state.clear()
    if tracking_items == []:
        await message.answer("Информация по этой ТТН не найдена.", reply_markup=main_menu)
        return

    for tracking_item in tracking_items:
        text = format_tracking_info(tracking_item)
        await message.answer(text, parse_mode="HTML", reply_markup=main_menu)

@router.message(TrackingStates.waiting_for_number, ~F.text)
async def process_tracking_non_text(message: Message):
    await message.answer("Пожалуйста, введите номер ТТН (14 цифр) или нажмите 'Передумал' для отмены.")