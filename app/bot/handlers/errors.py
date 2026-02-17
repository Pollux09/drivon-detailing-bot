from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent


router = Router(name="errors")
logger = logging.getLogger(__name__)


@router.error()
async def error_handler(event: ErrorEvent) -> bool:
    logger.exception("Unhandled exception", exc_info=event.exception)

    update = event.update
    if update is None:
        return True

    if update.callback_query and update.callback_query.message:
        try:
            await update.callback_query.answer("Произошла ошибка. Попробуйте снова.", show_alert=True)
        except Exception:
            logger.exception("Failed to answer callback error")

    if update.message:
        try:
            await update.message.answer("Произошла ошибка. Попробуйте снова.")
        except Exception:
            logger.exception("Failed to send message error")

    return True
