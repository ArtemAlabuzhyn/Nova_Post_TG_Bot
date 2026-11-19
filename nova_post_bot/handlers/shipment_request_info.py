from zoneinfo import ZoneInfo
from html import escape

from aiogram import Router, F
from aiogram.fsm.context import FSMContext

from nova_post_bot.core.config import settings
from aiogram.types import Message

from nova_post_bot.core.exceptions import ObjectNotFoundError
from nova_post_bot.db.uow import UnitOfWork
from nova_post_bot.keyboards.cancel import cancel_keyboard
from nova_post_bot.keyboards.main_menu import build_main_menu
from nova_post_bot.services.shipment import ShipmentService
from nova_post_bot.states.shipment_request_info import ShipmentRequestInfoStates

router = Router()


def can_view_request_info(user_id: int) -> bool:
    return (
            user_id in settings.allowed_telegram_ids
            and user_id in settings.shipment_request_info_allowed_ids
    )


@router.message(F.text == "Кто запросил")
async def start_request_info_search(message: Message, state: FSMContext):
    if not can_view_request_info(message.from_user.id):
        await message.answer("У вас нет доступа к этой функции")
        return

    await state.clear()
    await state.set_state(ShipmentRequestInfoStates.waiting_for_number)
    await message.answer("Введите номер ТТН:",
                         reply_markup=cancel_keyboard)


@router.message(ShipmentRequestInfoStates.waiting_for_number, F.text)
async def process_request_info_number(message: Message, state: FSMContext,
                                      uow: UnitOfWork):
    if not can_view_request_info(message.from_user.id):
        await state.clear()
        await message.answer("У вас нет доступа к этой функции",
                             reply_markup=build_main_menu())
        return

    shipment_service = ShipmentService(uow=uow)

    try:
        shipment = await shipment_service.get_by_document_number(
            document_number=message.text
        )
    except ValueError:
        await message.answer(
            "Введите номер ТТН: 14 цифр.",
            reply_markup=cancel_keyboard,
        )
        return
    except ObjectNotFoundError:
        await state.clear()
        await message.answer("Накладная не найдена в истории бота. "
                             "Возможно, она была создана вне бота.",
                             reply_markup=build_main_menu(show_request_info=True))
        return

    requested_at = shipment.created_at.astimezone(ZoneInfo("Europe/Kyiv"))

    await state.clear()
    await message.answer(
        f"Накладная №<code>{escape(shipment.document_number)}</code>\n"
        f"Кто запросил: {escape(shipment.requested_by_name)}\n"
        f"Дата записи в боте: {requested_at:%d.%m.%Y %H:%M}",
        parse_mode="HTML",
        reply_markup=build_main_menu(show_request_info=True)
    )


@router.message(ShipmentRequestInfoStates.waiting_for_number, ~F.text)
async def process_request_info_non_text(message: Message, state: FSMContext):
    if not can_view_request_info(message.from_user.id):
        await state.clear()
        await message.answer("У вас нет доступа к этой функции",
                             reply_markup=build_main_menu())
        return

    await message.answer("Введите номер ТТН текстом 14 цифр. "
                         "Для отмены нажмите 'Передумал' или отправьте /cancel",
                         reply_markup=cancel_keyboard)