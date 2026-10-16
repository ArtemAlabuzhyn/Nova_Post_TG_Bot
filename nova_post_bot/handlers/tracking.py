from aiogram import F, Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from nova_post_bot.clients.nova_post import NovaPostClient
from nova_post_bot.core.exceptions import NovaPostAPIError
from nova_post_bot.states.tracking import TrackingStates

router = Router()

PAYER_LABELS = {"Sender": "Отправитель", "Recipient": "Получатель"}
PAYMENT_METHOD_LABELS = {"NonCash": "Безналичный расчет"}

@router.message(F.text == "Отследить ТТН")
async def tracking(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(TrackingStates.waiting_for_number)
    await message.answer("Введите номер ТТН:")


@router.message(TrackingStates.waiting_for_number, F.text)
async def process_tracking_number(message: Message, state: FSMContext,
                                  nova_post_client: NovaPostClient):
    number = message.text.strip()
    if number == "":
        await message.answer("Номер ТТН не может быть пустым. Пожалуйста, введите номер ТТН:")
        return

    try:
        tracking_items = await nova_post_client.get_tracking_info(number=number)

    except NovaPostAPIError:
        await message.answer("Не удалось получить статус. Попробуйте позже или проверьте номер ТТН")
        return

    await state.clear()
    if tracking_items == []:
        await message.answer("Информация по этой ТТН не найдена.")
        return


    for tracking_item in tracking_items:
        payer_label = PAYER_LABELS.get(tracking_item.payer_type, "Не определен")
        payment_method = PAYMENT_METHOD_LABELS.get(tracking_item.payment_method, "Не определен")
        cost_label = f"{tracking_item.document_cost:.2f} грн" \
            if tracking_item.document_cost is not None else "Не указана"
        await message.answer(
            f"Номер ТТН: {tracking_item.number}\n"
            f"Статус: {tracking_item.status}\n"
            f"Описание: {tracking_item.cargo_description or "Не указано"}\n"
            f"Город отправки: {tracking_item.sender_city or "Не указано"}\n"
            f"Отделение отправки: {tracking_item.sender_warehouse or "Не указано"}\n"
            f"Город получения: {tracking_item.recipient_city or "Не указано"}\n"
            f"Отделение получения: {tracking_item.recipient_warehouse or "Не указано"}\n"
            f"Получатель: {tracking_item.recipient_full_name 
                           or tracking_item.recipient_full_name_ew 
                           or "Не указано"}\n"
            f"Плательщик: {payer_label}\n"
            f"Способ расчета: {payment_method}\n"
            f"Стоимость доставки: {cost_label}\n"
        )
