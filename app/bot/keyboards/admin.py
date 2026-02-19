from __future__ import annotations

from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models import Booking, CarType, Service
from app.utils.callbacks import AdminActionCb, AdminBlockCb, AdminBookingCb, AdminCarCb, AdminServiceCb


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Все записи", callback_data=AdminActionCb(action="all_bookings").pack()))
    builder.row(InlineKeyboardButton(text="📅 Записи на сегодня", callback_data=AdminActionCb(action="today_bookings").pack()))
    builder.row(InlineKeyboardButton(text="➕ Добавить услугу", callback_data=AdminActionCb(action="add_service").pack()))
    builder.row(InlineKeyboardButton(text="✏️ Редактировать услугу", callback_data=AdminActionCb(action="edit_service").pack()))
    builder.row(InlineKeyboardButton(text="❌ Деактивировать услугу", callback_data=AdminActionCb(action="deactivate_service").pack()))
    builder.row(InlineKeyboardButton(text="🚗 Управление типами авто", callback_data=AdminActionCb(action="cars_menu").pack()))
    builder.row(InlineKeyboardButton(text="⛔ Закрыть дату/время", callback_data=AdminActionCb(action="close_slot").pack()))
    builder.row(InlineKeyboardButton(text="🟢 Открыть закрытый слот", callback_data=AdminActionCb(action="open_slot").pack()))
    builder.row(InlineKeyboardButton(text="🔄 Перенести запись", callback_data=AdminActionCb(action="move_booking").pack()))
    builder.row(InlineKeyboardButton(text="❌ Отменить запись", callback_data=AdminActionCb(action="cancel_booking").pack()))
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data=AdminActionCb(action="stats").pack()))
    return builder.as_markup()


def services_manage_keyboard(services: Sequence[Service], action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.row(
            InlineKeyboardButton(
                text=f"{service.name} ({'активна' if service.is_active else 'неактивна'})",
                callback_data=AdminServiceCb(service_id=service.id, action=action).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Админ-меню", callback_data=AdminActionCb(action="menu").pack()))
    return builder.as_markup()


def service_edit_fields_keyboard(service_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for field, title in [
        ("name", "Название"),
        ("description", "Описание"),
        ("duration", "Длительность"),
        ("price", "Цена"),
        ("active", "Активность"),
    ]:
        builder.row(
            InlineKeyboardButton(
                text=title,
                callback_data=AdminServiceCb(service_id=service_id, action=f"field_{field}").pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ К списку", callback_data=AdminActionCb(action="edit_service").pack()))
    return builder.as_markup()


def cars_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить тип авто", callback_data=AdminActionCb(action="add_car").pack()))
    builder.row(InlineKeyboardButton(text="✏️ Редактировать тип авто", callback_data=AdminActionCb(action="edit_car").pack()))
    builder.row(InlineKeyboardButton(text="❌ Деактивировать тип авто", callback_data=AdminActionCb(action="deactivate_car").pack()))
    builder.row(InlineKeyboardButton(text="⬅️ Админ-меню", callback_data=AdminActionCb(action="menu").pack()))
    return builder.as_markup()


def cars_manage_keyboard(car_types: Sequence[CarType], action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for car in car_types:
        builder.row(
            InlineKeyboardButton(
                text=f"{car.name} x{car.price_multiplier} ({'активен' if car.is_active else 'неактивен'})",
                callback_data=AdminCarCb(car_type_id=car.id, action=action).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminActionCb(action="cars_menu").pack()))
    return builder.as_markup()


def car_edit_fields_keyboard(car_type_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Название", callback_data=AdminCarCb(car_type_id=car_type_id, action="field_name").pack())
    )
    builder.row(
        InlineKeyboardButton(
            text="Множитель",
            callback_data=AdminCarCb(car_type_id=car_type_id, action="field_multiplier").pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Активность",
            callback_data=AdminCarCb(car_type_id=car_type_id, action="field_active").pack(),
        )
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminActionCb(action="edit_car").pack()))
    return builder.as_markup()


def bookings_manage_keyboard(bookings: Sequence[Booking], action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for booking in bookings:
        builder.row(
            InlineKeyboardButton(
                text=f"#{booking.id} {booking.booking_start:%d.%m %H:%M}",
                callback_data=AdminBookingCb(booking_id=booking.id, action=action).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Админ-меню", callback_data=AdminActionCb(action="menu").pack()))
    return builder.as_markup()


def blocked_slots_keyboard(blocks: Sequence, action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for block in blocks:
        builder.row(
            InlineKeyboardButton(
                text=f"#{block.id} {block.start_datetime:%d.%m %H:%M}-{block.end_datetime:%H:%M}",
                callback_data=AdminBlockCb(block_id=block.id, action=action).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Админ-меню", callback_data=AdminActionCb(action="menu").pack()))
    return builder.as_markup()


def booking_list_keyboard(items: Sequence[tuple[int, str]], action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for booking_id, label in items:
        builder.row(
            InlineKeyboardButton(
                text=label,
                callback_data=AdminBookingCb(booking_id=booking_id, action=action).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Админ-меню", callback_data=AdminActionCb(action="menu").pack()))
    return builder.as_markup()


def booking_details_keyboard(booking_id: int, source: str, can_cancel: bool) -> InlineKeyboardMarkup:
    source_action = "today_bookings" if source == "today" else "all_bookings"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📞 Контакты клиента",
            callback_data=AdminBookingCb(booking_id=booking_id, action=f"card_contacts_{source}").pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📝 Комментарий",
            callback_data=AdminBookingCb(booking_id=booking_id, action=f"card_note_{source}").pack(),
        )
    )
    if can_cancel:
        builder.row(
            InlineKeyboardButton(
                text="❌ Отменить запись",
                callback_data=AdminBookingCb(booking_id=booking_id, action=f"card_cancel_{source}").pack(),
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data=AdminBookingCb(booking_id=booking_id, action=f"card_{source}").pack(),
        )
    )
    builder.row(InlineKeyboardButton(text="⬅️ К списку", callback_data=AdminActionCb(action=source_action).pack()))
    builder.row(InlineKeyboardButton(text="⬅️ Админ-меню", callback_data=AdminActionCb(action="menu").pack()))
    return builder.as_markup()


def booking_cancel_reason_keyboard(booking_id: int, source: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🚫 Без причины",
            callback_data=AdminBookingCb(booking_id=booking_id, action=f"card_cancel_skip_{source}").pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К записи",
            callback_data=AdminBookingCb(booking_id=booking_id, action=f"card_{source}").pack(),
        )
    )
    return builder.as_markup()


def booking_back_to_card_keyboard(booking_id: int, source: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К записи",
            callback_data=AdminBookingCb(booking_id=booking_id, action=f"card_{source}").pack(),
        )
    )
    return builder.as_markup()
