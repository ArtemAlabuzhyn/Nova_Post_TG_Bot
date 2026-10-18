from nova_post_bot.schemas.tracking import TrackingInfo
from html import escape


PAYER_LABELS = {"Sender": "Отправитель", "Recipient": "Получатель"}
PAYMENT_METHOD_LABELS = {"NonCash": "Безналичный расчет"}

def format_tracking_info(tracking_info: TrackingInfo) -> str:
    cost_label = (
        f"{tracking_info.document_cost:.2f} грн"
        if tracking_info.document_cost is not None else "Не указана"
    )
    payer_label = PAYER_LABELS.get(tracking_info.payer_type, "Не определен")
    payment_method = PAYMENT_METHOD_LABELS.get(tracking_info.payment_method, "Не определен")
    recipient_name = (
            tracking_info.recipient_full_name
            or tracking_info.recipient_full_name_ew
            or "Не указано"
    )

    return ("<b>📦 Основное</b>\n"
            f"Номер ТТН: <code>{tracking_info.number}</code>\n"
            f"Статус: {escape(tracking_info.status)}\n"
            f"Описание: {escape(tracking_info.cargo_description or 'Не указано')}\n\n"
            "<b>🚚 Маршрут</b>\n"
            f"Город отправки: {tracking_info.sender_city or "Не указано"}\n"
            f"Отделение отправки: {tracking_info.sender_warehouse or "Не указано"}\n"
            f"Город получения: {tracking_info.recipient_city or "Не указано"}\n"
            f"Отделение получения: {tracking_info.recipient_warehouse or "Не указано"}\n\n"
            "<b>👤 Получатель</b>\n"
            f"Получатель: {escape(recipient_name)}\n\n"
            "<b>💳 Оплата</b>\n"
            f"Плательщик: {payer_label}\n"
            f"Способ расчета: {payment_method}\n"
            f"Стоимость доставки: {cost_label}\n")
