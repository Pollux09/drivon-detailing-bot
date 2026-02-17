from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup


async def edit_or_answer(query: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    if query.message is None:
        return
    try:
        await query.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        await query.message.answer(text, reply_markup=reply_markup)
