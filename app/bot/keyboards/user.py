from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models import CarType, Service
from app.utils.callbacks import CarTypeSelectCb, ConfirmCb, DateSelectCb, MenuActionCb, ServiceSelectCb, TimeSelectCb
from app.utils.datetime_utils import to_iso_day


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Записаться", callback_data=MenuActionCb(action="book").pack()))
    builder.row(InlineKeyboardButton(text="💰 Прайс", callback_data=MenuActionCb(action="price").pack()))
    builder.row(InlineKeyboardButton(text="📸 Наши работы", callback_data=MenuActionCb(action="works").pack()))
    builder.row(InlineKeyboardButton(text="🎁 Акции", callback_data=MenuActionCb(action="promotions").pack()))
    builder.row(InlineKeyboardButton(text="📍 Контакты", callback_data=MenuActionCb(action="contacts").pack()))
    builder.row(
        InlineKeyboardButton(
            text="👨‍💼 Связаться с администратором",
            callback_data=MenuActionCb(action="contact_admin").pack(),
        )
    )
    return builder.as_markup()


def services_keyboard(services: Sequence[Service]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.row(InlineKeyboardButton(text=service.name, callback_data=ServiceSelectCb(service_id=service.id).pack()))
    builder.row(InlineKeyboardButton(text="⬅️ В меню", callback_data=MenuActionCb(action="main").pack()))
    return builder.as_markup()


def car_types_keyboard(car_types: Sequence[CarType]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for car_type in car_types:
        builder.row(
            InlineKeyboardButton(
                text=f"{car_type.name} x{car_type.price_multiplier}",
                callback_data=CarTypeSelectCb(car_type_id=car_type.id).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=MenuActionCb(action="back_services").pack()))
    return builder.as_markup()


def dates_keyboard(days: Sequence[date]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for day in days:
        builder.button(text=day.strftime("%d.%m (%a)"), callback_data=DateSelectCb(day=to_iso_day(day)).pack())
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=MenuActionCb(action="back_car_types").pack()))
    return builder.as_markup()


def times_keyboard(slots: Sequence[datetime]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(text=slot.strftime("%H:%M"), callback_data=TimeSelectCb(ts=int(slot.timestamp())).pack())
    builder.adjust(4)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=MenuActionCb(action="back_dates").pack()))
    return builder.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Подтвердить", callback_data=ConfirmCb(action="book").pack()))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=MenuActionCb(action="back_times").pack()))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=MenuActionCb(action="main").pack()))
    return builder.as_markup()
