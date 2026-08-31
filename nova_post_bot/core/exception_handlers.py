import logging

from aiogram.types import ErrorEvent


async def global_exception_handler(event: ErrorEvent):
    exc = event.exception
    logging.error(
        "Unhandled exception",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    if event.update.message:
        await event.update.message.answer("Something went wrong. Try again later.")
