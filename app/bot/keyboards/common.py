from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.callbacks import MenuActionCb


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ В меню",
            callback_data=MenuActionCb(action="main").pack(),
        )
    )
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=MenuActionCb(action="main").pack()))
    return builder.as_markup()
