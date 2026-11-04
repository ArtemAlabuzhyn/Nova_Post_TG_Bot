from zoneinfo import ZoneInfo
from datetime import datetime


from nova_post_bot.schemas.tracking import TrackingInfo
from html import escape
from decimal import Decimal



PAYER_LABELS = {"Sender": "Отправитель", "Recipient": "Получатель"}
PAYMENT_METHOD_LABELS = {"NonCash": "Безналичный расчет",
                         "Cash": "Наличный расчет"}

def format_money(value: Decimal) -> str:
    return f"{value:.2f}".replace(".", ",") + " грн"

def format_recipient_phone(value: str | None) -> str | None:
    if value is None:
        return None

    phone = value.strip()
    if not phone:
        return None

    if (len(phone) == 12
        and phone.isascii()
        and phone.isdigit()
        and phone.startswith("380")):
        return phone[2:]

    return phone


def format_tracking_info(tracking_info: TrackingInfo) -> str:
    cost_label = (
        format_money(tracking_info.document_cost) if tracking_info.document_cost is not None else "Не указана"
    )
    payer_label = PAYER_LABELS.get(tracking_info.payer_type, "Не определен")
    payment_method = PAYMENT_METHOD_LABELS.get(tracking_info.payment_method, "Не определен")
    recipient_name = (
            tracking_info.recipient_full_name
            or tracking_info.recipient_full_name_ew
            or "Не указано"
    )
    recipient_phone = format_recipient_phone(tracking_info.recipient_phone)

    lines = [
        "<b>📦 Основное</b>",
        f"Номер ТТН: <code>{escape(tracking_info.number)}</code>",
        f"Статус: {escape(tracking_info.status)}",
        f"Описание: {escape(tracking_info.cargo_description or 'Не указано')}",
        "",
        "<b>🚚 Маршрут</b>",
        f"Город отправки: {escape(tracking_info.sender_city or 'Не указано')}",
        f"Отделение отправки: {escape(tracking_info.sender_warehouse or 'Не указано')}",
        f"Город получения: {escape(tracking_info.recipient_city or 'Не указано')}",
        f"Отделение получения: {escape(tracking_info.recipient_warehouse or 'Не указано')}",
        "",
        "<b>👤 Получатель</b>",
        f"Получатель: {escape(recipient_name)}",
    ]

    if recipient_phone is not None:
        lines.append(
            f"Телефон: <code>{escape(recipient_phone)}</code>"
        )

    lines.extend(
        [
            "",
            "<b>💳 Оплата</b>",
            f"Плательщик: {payer_label}",
            f"Способ расчета: {payment_method}",
            f"Стоимость доставки: {cost_label}",
        ]
    )

    today = datetime.now(ZoneInfo("Europe/Kyiv")).date()
    storage_price = tracking_info.storage_price
    storage_date = tracking_info.storage_start_date

    storage_has_started = (storage_date is not None and storage_date <= today)
    has_storage_charge = (storage_price is not None and storage_price > 0)
    if storage_has_started or has_storage_charge:
        lines.extend(
            [
                "",
                "<b>⚠️ Платное хранение</b>",
            ]
        )

        if storage_date is not None:
            lines.append(
                f"Начало платного хранения: {storage_date:%d.%m.%Y}"
            )

        storage_cost_label = (
            format_money(storage_price)
            if storage_price is not None
            else "Нет данных"
        )
        lines.append(
            f"Стоимость хранения: {storage_cost_label}"
        )

    return "\n".join(lines)
