from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from nova_post_bot.enums.shipment import ShipmentStatus
from nova_post_bot.handlers.shipment import confirm_shipment_creation
from nova_post_bot.core.exceptions import NovaPostTimeoutError, NovaPostRejectedError


@pytest.mark.asyncio
async def test_confirm_shipment_creation_success(shipment_handler_context):
    ctx = shipment_handler_context
    method_properties = {
        "CargoType": "Documents",
        "DateTime": "09.11.2026",
    }
    ctx.shipment_service.build_document_properties.return_value = method_properties
    ctx.nova_post_client.get_shipment_pdf = AsyncMock(
        return_value=b"%PDF-1.4\n"
    )
    ctx.callback.message.answer_document = AsyncMock()

    await confirm_shipment_creation(callback=ctx.callback,
                                    state=ctx.state,
                                    uow=ctx.uow,
                                    nova_post_client=ctx.nova_post_client)

    ctx.nova_post_client.create_shipment.assert_awaited_once_with(
        method_properties=method_properties,
    )
    ctx.shipment_service.mark_created.assert_awaited_once_with(
        shipment_id=ctx.shipment_id,
        created_info=ctx.created_info,
    )
    ctx.shipment_service.mark_creation_error.assert_not_awaited()
    ctx.state.clear.assert_awaited_once()
    ctx.callback.message.edit_reply_markup.assert_awaited_once_with(reply_markup=None)
    ctx.nova_post_client.get_shipment_pdf.assert_awaited_once_with(
        ctx.created_info.document_ref,
    )
    ctx.callback.message.answer_document.assert_awaited_once()

    sent_document = ctx.callback.message.answer_document.await_args.kwargs
    assert sent_document["document"].filename == "Полтава-Николаев (Test) 09.11.pdf"
    assert sent_document.get("caption") is None

    ctx.callback.message.answer.assert_awaited_once()
    sent_message = ctx.callback.message.answer.await_args
    assert f"<code>{ctx.created_info.document_number}</code>" in sent_message.args[0]
    assert sent_message.kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_confirm_shipment_creation_marks_unknown_on_timeout(shipment_handler_context):
    ctx = shipment_handler_context
    ctx.nova_post_client.create_shipment.side_effect = NovaPostTimeoutError(
        "Request timed out"
    )
    await confirm_shipment_creation(callback=ctx.callback,
                                    state=ctx.state,
                                    uow=ctx.uow,
                                    nova_post_client=ctx.nova_post_client)

    ctx.shipment_service.mark_creation_error.assert_awaited_once_with(shipment_id=ctx.shipment_id,
                                                                      status=ShipmentStatus.UNKNOWN)

    ctx.nova_post_client.create_shipment.assert_awaited_once_with(
        method_properties={"CargoType": "Documents"},
    )
    ctx.shipment_service.mark_created.assert_not_awaited()
    ctx.state.clear.assert_awaited_once()
    send_text = ctx.callback.message.answer.call_args.args[0]
    assert "Накладная могла быть создана" in send_text

@pytest.mark.asyncio
async def test_confirm_shipment_creation_skips_already_started(shipment_handler_context):
    ctx = shipment_handler_context
    ctx.shipment_service.try_start_creation.return_value = False
    await confirm_shipment_creation(callback=ctx.callback,
                                    state=ctx.state,
                                    uow=ctx.uow,
                                    nova_post_client=ctx.nova_post_client)
    ctx.nova_post_client.create_shipment.assert_not_awaited()
    ctx.shipment_service.resolve_recipient_refs.assert_not_awaited()
    ctx.shipment_service.mark_created.assert_not_awaited()
    ctx.shipment_service.mark_creation_error.assert_not_awaited()
    ctx.state.clear.assert_not_awaited()
    send_text = ctx.callback.message.answer.call_args.args[0]
    assert "Повторный запрос не отправлен" in send_text


@pytest.mark.asyncio
async def test_confirm_shipment_creation_marks_failed_on_rejection(shipment_handler_context):
    ctx = shipment_handler_context
    ctx.nova_post_client.create_shipment.side_effect = NovaPostRejectedError(
        "Nova Post rejected the shipment"
    )
    await confirm_shipment_creation(callback=ctx.callback,
                                    state=ctx.state,
                                    uow=ctx.uow,
                                    nova_post_client=ctx.nova_post_client)
    ctx.shipment_service.mark_creation_error.assert_awaited_once_with(
        shipment_id=ctx.shipment_id,
        status=ShipmentStatus.FAILED,
    )
    ctx.shipment_service.mark_created.assert_not_awaited()
    ctx.state.clear.assert_awaited_once()
    ctx.nova_post_client.create_shipment.assert_awaited_once()
    send_text = ctx.callback.message.answer.call_args.args[0]
    assert "Новая почта отклонила создание накладной" in send_text

@pytest.mark.asyncio
async def test_confirm_shipment_creation_reports_number_on_save_error(shipment_handler_context):
    ctx = shipment_handler_context
    ctx.shipment_service.mark_created.side_effect = SQLAlchemyError(
        "Couldn't save shipment"
    )
    ctx.uow.rollback = AsyncMock()
    await confirm_shipment_creation(callback=ctx.callback,
                                    state=ctx.state,
                                    uow=ctx.uow,
                                    nova_post_client=ctx.nova_post_client)
    ctx.nova_post_client.create_shipment.assert_awaited_once()
    ctx.shipment_service.mark_created.assert_awaited_once_with(
        shipment_id=ctx.shipment_id,
        created_info=ctx.created_info,
    )
    ctx.uow.rollback.assert_awaited_once()
    ctx.shipment_service.mark_creation_error.assert_not_awaited()
    ctx.state.clear.assert_awaited_once()
    send_text = ctx.callback.message.answer.call_args.args[0]
    assert ctx.created_info.document_number in send_text
    assert "Не удалось сохранить" in send_text
