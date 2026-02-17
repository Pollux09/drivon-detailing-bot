from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.filters import IsAdminFilter
from app.bot.handlers.helpers import edit_or_answer
from app.bot.keyboards.admin import (
    admin_menu_keyboard,
    blocked_slots_keyboard,
    bookings_manage_keyboard,
    car_edit_fields_keyboard,
    cars_manage_keyboard,
    cars_menu_keyboard,
    service_edit_fields_keyboard,
    services_manage_keyboard,
)
from app.bot.states import (
    AdminCarCreateStates,
    AdminCarEditStates,
    AdminCloseSlotStates,
    AdminMoveBookingStates,
    AdminServiceCreateStates,
    AdminServiceEditStates,
)
from app.config import Settings
from app.db.models import BookingStatus
from app.utils.callbacks import (
    AdminActionCb,
    AdminBlockCb,
    AdminBookingCb,
    AdminCarCb,
    AdminServiceCb,
    AdminTimeSelectCb,
)


router = Router(name="admin")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


def _time_choice_keyboard(slots: list[datetime]):
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(text=slot.strftime("%H:%M"), callback_data=AdminTimeSelectCb(ts=int(slot.timestamp())).pack())
    builder.adjust(4)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=AdminActionCb(action="menu").pack()))
    return builder.as_markup()


@router.callback_query(AdminActionCb.filter(F.action == "all_bookings"))
async def all_bookings(query: CallbackQuery, booking_service, session: AsyncSession, settings: Settings) -> None:
    bookings = await booking_service.list_bookings(session, limit=50)
    if not bookings:
        text = "Записей нет."
    else:
        lines = ["📋 Все записи:"]
        for booking in bookings[:30]:
            start = booking.booking_start.astimezone(settings.timezone)
            lines.append(f"#{booking.id} {start:%d.%m %H:%M} [{booking.status.value}]")
        text = "\n".join(lines)
    await edit_or_answer(query, text, admin_menu_keyboard())
    await query.answer()


@router.callback_query(AdminActionCb.filter(F.action == "today_bookings"))
async def today_bookings(query: CallbackQuery, booking_service, session: AsyncSession, settings: Settings) -> None:
    bookings = await booking_service.list_today_bookings(session, settings.timezone, limit=50)
    if not bookings:
        text = "На сегодня записей нет."
    else:
        lines = ["📅 Записи на сегодня:"]
        for booking in bookings:
            start = booking.booking_start.astimezone(settings.timezone)
            lines.append(f"#{booking.id} {start:%H:%M} [{booking.status.value}]")
        text = "\n".join(lines)
    await edit_or_answer(query, text, admin_menu_keyboard())
    await query.answer()


@router.callback_query(AdminActionCb.filter(F.action == "add_service"))
async def add_service_start(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AdminServiceCreateStates.waiting_name)
    await edit_or_answer(query, "Введите название услуги")
    await query.answer()


@router.message(AdminServiceCreateStates.waiting_name)
async def add_service_name(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Нужно текстовое название")
        return
    await state.update_data(new_service_name=message.text.strip())
    await state.set_state(AdminServiceCreateStates.waiting_description)
    await message.answer("Введите описание")


@router.message(AdminServiceCreateStates.waiting_description)
async def add_service_description(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Нужно текстовое описание")
        return
    await state.update_data(new_service_description=message.text.strip())
    await state.set_state(AdminServiceCreateStates.waiting_duration)
    await message.answer("Введите длительность (минуты)")


@router.message(AdminServiceCreateStates.waiting_duration)
async def add_service_duration(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Введите целое число минут")
        return
    await state.update_data(new_service_duration=int(message.text))
    await state.set_state(AdminServiceCreateStates.waiting_price)
    await message.answer("Введите базовую цену")


@router.message(AdminServiceCreateStates.waiting_price)
async def add_service_price(
    message: Message,
    state: FSMContext,
    admin_service,
    session: AsyncSession,
) -> None:
    if message.from_user is None or not message.text:
        return
    try:
        price = Decimal(message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("Введите корректную цену")
        return

    data = await state.get_data()
    service = await admin_service.create_service(
        session,
        name=data["new_service_name"],
        description=data["new_service_description"],
        duration_minutes=data["new_service_duration"],
        base_price=price,
        admin_tg_id=message.from_user.id,
    )
    await state.clear()
    await message.answer(f"✅ Услуга создана: {service.name}", reply_markup=admin_menu_keyboard())


@router.callback_query(AdminActionCb.filter(F.action == "edit_service"))
async def edit_service_menu(query: CallbackQuery, admin_service, session: AsyncSession) -> None:
    services = await admin_service.list_services(session)
    if not services:
        await edit_or_answer(query, "Услуг нет.", admin_menu_keyboard())
        await query.answer()
        return
    await edit_or_answer(query, "Выберите услугу", services_manage_keyboard(services, action="edit"))
    await query.answer()


@router.callback_query(AdminServiceCb.filter(F.action == "edit"))
async def edit_service_fields(query: CallbackQuery, callback_data: AdminServiceCb, booking_service, session: AsyncSession) -> None:
    service = await booking_service.get_service(session, callback_data.service_id)
    if service is None:
        await query.answer("Услуга не найдена", show_alert=True)
        return
    text = (
        f"{service.name}\n"
        f"{service.description}\n"
        f"Длительность: {service.duration_minutes} мин\n"
        f"Цена: {service.base_price} ₽\n"
        f"Активна: {'да' if service.is_active else 'нет'}"
    )
    await edit_or_answer(query, text, service_edit_fields_keyboard(service.id))
    await query.answer()


@router.callback_query(AdminServiceCb.filter(F.action.startswith("field_")))
async def service_field_selected(
    query: CallbackQuery,
    callback_data: AdminServiceCb,
    state: FSMContext,
    booking_service,
    admin_service,
    session: AsyncSession,
) -> None:
    field = callback_data.action.removeprefix("field_")
    service = await booking_service.get_service(session, callback_data.service_id)
    if service is None:
        await query.answer("Услуга не найдена", show_alert=True)
        return

    if field == "active":
        updated = await admin_service.update_service_field(
            session,
            service=service,
            field="active",
            value=not service.is_active,
            admin_tg_id=query.from_user.id,
        )
        await edit_or_answer(
            query,
            f"Активность обновлена: {'да' if updated.is_active else 'нет'}",
            service_edit_fields_keyboard(updated.id),
        )
        await query.answer()
        return

    await state.set_state(AdminServiceEditStates.waiting_value)
    await state.update_data(edit_service_id=service.id, edit_service_field=field)
    prompts = {
        "name": "Введите новое название",
        "description": "Введите новое описание",
        "duration": "Введите длительность в минутах",
        "price": "Введите новую цену",
    }
    await edit_or_answer(query, prompts.get(field, "Введите новое значение"))
    await query.answer()


@router.message(AdminServiceEditStates.waiting_value)
async def service_field_value(
    message: Message,
    state: FSMContext,
    booking_service,
    admin_service,
    session: AsyncSession,
) -> None:
    if message.from_user is None or not message.text:
        return
    data = await state.get_data()
    service = await booking_service.get_service(session, data["edit_service_id"])
    if service is None:
        await message.answer("Услуга не найдена", reply_markup=admin_menu_keyboard())
        await state.clear()
        return

    field = data["edit_service_field"]
    value = message.text.strip()

    try:
        if field == "duration":
            parsed = int(value)
            if parsed <= 0:
                raise ValueError
            value = parsed
        elif field == "price":
            parsed_price = Decimal(value.replace(",", "."))
            if parsed_price <= 0:
                raise ValueError
            value = parsed_price
        updated = await admin_service.update_service_field(
            session,
            service=service,
            field=field,
            value=value,
            admin_tg_id=message.from_user.id,
        )
    except (ValueError, InvalidOperation):
        await message.answer("Некорректное значение")
        return

    await state.clear()
    await message.answer(f"✅ Обновлено: {updated.name}", reply_markup=service_edit_fields_keyboard(updated.id))


@router.callback_query(AdminActionCb.filter(F.action == "deactivate_service"))
async def deactivate_service_menu(query: CallbackQuery, admin_service, session: AsyncSession) -> None:
    services = await admin_service.list_services(session)
    if not services:
        await edit_or_answer(query, "Услуг нет.", admin_menu_keyboard())
        await query.answer()
        return
    await edit_or_answer(query, "Выберите услугу для деактивации", services_manage_keyboard(services, action="deactivate"))
    await query.answer()


@router.callback_query(AdminServiceCb.filter(F.action == "deactivate"))
async def deactivate_service_action(
    query: CallbackQuery,
    callback_data: AdminServiceCb,
    booking_service,
    admin_service,
    session: AsyncSession,
) -> None:
    service = await booking_service.get_service(session, callback_data.service_id)
    if service is None:
        await query.answer("Услуга не найдена", show_alert=True)
        return
    await admin_service.set_service_active(session, service, False, query.from_user.id)
    await edit_or_answer(query, f"❌ Услуга деактивирована: {service.name}", admin_menu_keyboard())
    await query.answer()


@router.callback_query(AdminActionCb.filter(F.action == "cars_menu"))
async def cars_menu(query: CallbackQuery) -> None:
    await edit_or_answer(query, "Управление типами авто", cars_menu_keyboard())
    await query.answer()


@router.callback_query(AdminActionCb.filter(F.action == "add_car"))
async def add_car_start(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AdminCarCreateStates.waiting_name)
    await edit_or_answer(query, "Введите название типа авто")
    await query.answer()


@router.message(AdminCarCreateStates.waiting_name)
async def add_car_name(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Нужно название")
        return
    await state.update_data(new_car_name=message.text.strip())
    await state.set_state(AdminCarCreateStates.waiting_multiplier)
    await message.answer("Введите множитель (например 1.25)")


@router.message(AdminCarCreateStates.waiting_multiplier)
async def add_car_multiplier(message: Message, state: FSMContext, admin_service, session: AsyncSession) -> None:
    if message.from_user is None or not message.text:
        return
    try:
        multiplier = Decimal(message.text.strip().replace(",", "."))
        if multiplier <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("Введите корректный множитель")
        return

    data = await state.get_data()
    try:
        car_type = await admin_service.create_car_type(
            session,
            name=data["new_car_name"],
            multiplier=multiplier,
            admin_tg_id=message.from_user.id,
        )
    except Exception:
        await message.answer("Не удалось создать тип авто (проверьте уникальность имени)")
        return

    await state.clear()
    await message.answer(f"✅ Тип авто создан: {car_type.name}", reply_markup=cars_menu_keyboard())


@router.callback_query(AdminActionCb.filter(F.action == "edit_car"))
async def edit_car_menu(query: CallbackQuery, admin_service, session: AsyncSession) -> None:
    cars = await admin_service.list_car_types(session)
    if not cars:
        await edit_or_answer(query, "Типов авто нет.", cars_menu_keyboard())
        await query.answer()
        return
    await edit_or_answer(query, "Выберите тип авто", cars_manage_keyboard(cars, action="edit"))
    await query.answer()


@router.callback_query(AdminCarCb.filter(F.action == "edit"))
async def edit_car_fields(query: CallbackQuery, callback_data: AdminCarCb, booking_service, session: AsyncSession) -> None:
    car_type = await booking_service.get_car_type(session, callback_data.car_type_id)
    if car_type is None:
        await query.answer("Тип авто не найден", show_alert=True)
        return
    await edit_or_answer(
        query,
        f"{car_type.name}\nМножитель: {car_type.price_multiplier}\nАктивен: {'да' if car_type.is_active else 'нет'}",
        car_edit_fields_keyboard(car_type.id),
    )
    await query.answer()


@router.callback_query(AdminCarCb.filter(F.action.startswith("field_")))
async def car_field_selected(
    query: CallbackQuery,
    callback_data: AdminCarCb,
    state: FSMContext,
    booking_service,
    admin_service,
    session: AsyncSession,
) -> None:
    field = callback_data.action.removeprefix("field_")
    car_type = await booking_service.get_car_type(session, callback_data.car_type_id)
    if car_type is None:
        await query.answer("Тип авто не найден", show_alert=True)
        return

    if field == "active":
        updated = await admin_service.update_car_field(
            session,
            car_type=car_type,
            field="active",
            value=not car_type.is_active,
            admin_tg_id=query.from_user.id,
        )
        await edit_or_answer(query, f"Активность: {'да' if updated.is_active else 'нет'}", car_edit_fields_keyboard(updated.id))
        await query.answer()
        return

    await state.set_state(AdminCarEditStates.waiting_value)
    await state.update_data(edit_car_id=car_type.id, edit_car_field=field)
    prompts = {
        "name": "Введите новое название",
        "multiplier": "Введите новый множитель",
    }
    await edit_or_answer(query, prompts.get(field, "Введите новое значение"))
    await query.answer()


@router.message(AdminCarEditStates.waiting_value)
async def car_field_value(message: Message, state: FSMContext, booking_service, admin_service, session: AsyncSession) -> None:
    if message.from_user is None or not message.text:
        return

    data = await state.get_data()
    car_type = await booking_service.get_car_type(session, data["edit_car_id"])
    if car_type is None:
        await state.clear()
        await message.answer("Тип авто не найден", reply_markup=cars_menu_keyboard())
        return

    field = data["edit_car_field"]
    value = message.text.strip()
    try:
        if field == "multiplier":
            parsed = Decimal(value.replace(",", "."))
            if parsed <= 0:
                raise ValueError
            value = parsed
        updated = await admin_service.update_car_field(
            session,
            car_type=car_type,
            field=field,
            value=value,
            admin_tg_id=message.from_user.id,
        )
    except (InvalidOperation, ValueError):
        await message.answer("Некорректное значение")
        return

    await state.clear()
    await message.answer(f"✅ Обновлено: {updated.name}", reply_markup=car_edit_fields_keyboard(updated.id))


@router.callback_query(AdminActionCb.filter(F.action == "deactivate_car"))
async def deactivate_car_menu(query: CallbackQuery, admin_service, session: AsyncSession) -> None:
    cars = await admin_service.list_car_types(session)
    if not cars:
        await edit_or_answer(query, "Типов авто нет.", cars_menu_keyboard())
        await query.answer()
        return
    await edit_or_answer(query, "Выберите тип авто для деактивации", cars_manage_keyboard(cars, action="deactivate"))
    await query.answer()


@router.callback_query(AdminCarCb.filter(F.action == "deactivate"))
async def deactivate_car_action(
    query: CallbackQuery,
    callback_data: AdminCarCb,
    booking_service,
    admin_service,
    session: AsyncSession,
) -> None:
    car_type = await booking_service.get_car_type(session, callback_data.car_type_id)
    if car_type is None:
        await query.answer("Тип авто не найден", show_alert=True)
        return
    await admin_service.set_car_type_active(session, car_type, False, query.from_user.id)
    await edit_or_answer(query, f"❌ Тип авто деактивирован: {car_type.name}", cars_menu_keyboard())
    await query.answer()


@router.callback_query(AdminActionCb.filter(F.action == "close_slot"))
async def close_slot_start(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AdminCloseSlotStates.waiting_date)
    await edit_or_answer(query, "Введите дату закрытия в формате YYYY-MM-DD")
    await query.answer()


@router.message(AdminCloseSlotStates.waiting_date)
async def close_slot_date(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    try:
        day = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
    except ValueError:
        await message.answer("Неверный формат. Пример: 2026-02-20")
        return
    await state.update_data(close_day=day.isoformat())
    await state.set_state(AdminCloseSlotStates.waiting_start_hour)
    await message.answer("Введите время начала HH:MM (или 00:00 для целого дня)")


@router.message(AdminCloseSlotStates.waiting_start_hour)
async def close_slot_start_hour(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    try:
        parsed = datetime.strptime(message.text.strip(), "%H:%M").time()
    except ValueError:
        await message.answer("Неверный формат. Пример: 14:00")
        return
    await state.update_data(close_start=parsed.strftime("%H:%M"))
    await state.set_state(AdminCloseSlotStates.waiting_duration)
    await message.answer("Введите длительность в часах (1-24)")


@router.message(AdminCloseSlotStates.waiting_duration)
async def close_slot_duration(
    message: Message,
    state: FSMContext,
    schedule_service,
    settings: Settings,
    session: AsyncSession,
) -> None:
    if message.from_user is None or not message.text:
        return
    if not message.text.isdigit():
        await message.answer("Введите целое число часов")
        return

    hours = int(message.text)
    if hours < 1 or hours > 24:
        await message.answer("Допустимо от 1 до 24")
        return

    data = await state.get_data()
    day = datetime.strptime(data["close_day"], "%Y-%m-%d").date()
    start_time = datetime.strptime(data["close_start"], "%H:%M").time()
    start = datetime.combine(day, start_time).replace(tzinfo=settings.timezone)
    end = start + timedelta(hours=hours)

    block = await schedule_service.close_slot(
        session,
        start=start,
        end=end,
        telegram_id=message.from_user.id,
        note="manual_close",
    )

    await state.clear()
    await message.answer(
        f"✅ Слот закрыт: #{block.id} {block.start_datetime:%d.%m %H:%M}-{block.end_datetime:%H:%M}",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(AdminActionCb.filter(F.action == "open_slot"))
async def open_slot_menu(query: CallbackQuery, schedule_service, session: AsyncSession) -> None:
    blocks = await schedule_service.list_active_blocks(session, limit=30)
    if not blocks:
        await edit_or_answer(query, "Нет активных блокировок.", admin_menu_keyboard())
        await query.answer()
        return
    await edit_or_answer(query, "Выберите блок для открытия", blocked_slots_keyboard(blocks, action="open"))
    await query.answer()


@router.callback_query(AdminBlockCb.filter(F.action == "open"))
async def open_slot_action(query: CallbackQuery, callback_data: AdminBlockCb, schedule_service, session: AsyncSession) -> None:
    ok = await schedule_service.reopen_slot(session, callback_data.block_id)
    if not ok:
        await query.answer("Блок не найден", show_alert=True)
        return
    await edit_or_answer(query, "🟢 Слот снова открыт", admin_menu_keyboard())
    await query.answer()


@router.callback_query(AdminActionCb.filter(F.action == "move_booking"))
async def move_booking_menu(query: CallbackQuery, booking_service, session: AsyncSession) -> None:
    bookings = await booking_service.list_bookings(session, limit=50)
    confirmed = [b for b in bookings if b.status == BookingStatus.CONFIRMED]
    if not confirmed:
        await edit_or_answer(query, "Нет подтвержденных записей.", admin_menu_keyboard())
        await query.answer()
        return
    await edit_or_answer(query, "Выберите запись для переноса", bookings_manage_keyboard(confirmed, action="move"))
    await query.answer()


@router.callback_query(AdminBookingCb.filter(F.action == "move"))
async def move_booking_selected(
    query: CallbackQuery,
    callback_data: AdminBookingCb,
    state: FSMContext,
    booking_service,
    session: AsyncSession,
) -> None:
    booking = await booking_service.get_booking(session, callback_data.booking_id)
    if booking is None or booking.status != BookingStatus.CONFIRMED:
        await query.answer("Запись недоступна", show_alert=True)
        return
    await state.clear()
    await state.update_data(move_booking_id=booking.id)
    await state.set_state(AdminMoveBookingStates.waiting_date)
    await edit_or_answer(query, "Введите новую дату в формате YYYY-MM-DD")
    await query.answer()


@router.message(AdminMoveBookingStates.waiting_date)
async def move_booking_date(
    message: Message,
    state: FSMContext,
    booking_service,
    schedule_service,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if not message.text:
        return

    try:
        day = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
    except ValueError:
        await message.answer("Неверный формат. Пример: 2026-02-20")
        return

    data = await state.get_data()
    booking = await booking_service.get_booking(session, data["move_booking_id"])
    if booking is None:
        await state.clear()
        await message.answer("Запись не найдена", reply_markup=admin_menu_keyboard())
        return

    slots = await schedule_service.get_available_slots(
        session,
        day,
        booking.service.duration_minutes,
        exclude_booking_id=booking.id,
    )
    if not slots:
        await message.answer("На эту дату нет свободного времени. Введите другую дату.")
        return

    await state.update_data(move_day=day.isoformat())
    await state.set_state(AdminMoveBookingStates.waiting_time)
    await message.answer("Выберите новое время", reply_markup=_time_choice_keyboard(slots))


@router.callback_query(AdminTimeSelectCb.filter(), AdminMoveBookingStates.waiting_time)
async def move_booking_time(
    query: CallbackQuery,
    callback_data: AdminTimeSelectCb,
    state: FSMContext,
    booking_service,
    session: AsyncSession,
    settings: Settings,
) -> None:
    data = await state.get_data()
    booking = await booking_service.get_booking(session, data["move_booking_id"])
    if booking is None:
        await state.clear()
        await query.answer("Запись не найдена", show_alert=True)
        return

    new_start = datetime.fromtimestamp(callback_data.ts, tz=settings.timezone)
    try:
        await booking_service.move_booking(
            session,
            booking,
            new_start,
            booking.service.duration_minutes,
        )
    except ValueError:
        await query.answer("Слот занят", show_alert=True)
        return

    await state.clear()
    await edit_or_answer(query, f"✅ Запись #{booking.id} перенесена", admin_menu_keyboard())
    await query.answer()


@router.callback_query(AdminActionCb.filter(F.action == "cancel_booking"))
async def cancel_booking_menu(query: CallbackQuery, booking_service, session: AsyncSession) -> None:
    bookings = await booking_service.list_bookings(session, limit=50)
    confirmed = [b for b in bookings if b.status == BookingStatus.CONFIRMED]
    if not confirmed:
        await edit_or_answer(query, "Нет подтвержденных записей.", admin_menu_keyboard())
        await query.answer()
        return
    await edit_or_answer(query, "Выберите запись для отмены", bookings_manage_keyboard(confirmed, action="cancel"))
    await query.answer()


@router.callback_query(AdminBookingCb.filter(F.action == "cancel"))
async def cancel_booking_action(
    query: CallbackQuery,
    callback_data: AdminBookingCb,
    booking_service,
    session: AsyncSession,
    settings: Settings,
) -> None:
    booking = await booking_service.get_booking(session, callback_data.booking_id)
    if booking is None or booking.status != BookingStatus.CONFIRMED:
        await query.answer("Запись недоступна", show_alert=True)
        return

    await booking_service.cancel_booking(session, booking, reason="admin_cancel")

    try:
        await query.bot.send_message(
            booking.user.telegram_id,
            (
                "❌ Ваша запись отменена администратором\n"
                f"#{booking.id} {booking.booking_start.astimezone(settings.timezone):%d.%m %H:%M}"
            ),
        )
    except Exception:
        pass

    await edit_or_answer(query, f"❌ Запись #{booking.id} отменена", admin_menu_keyboard())
    await query.answer()


@router.callback_query(AdminActionCb.filter(F.action == "stats"))
async def stats_action(query: CallbackQuery, booking_service, session: AsyncSession) -> None:
    stats = await booking_service.get_stats(session)
    text = (
        "📊 Статистика:\n"
        f"Всего записей: {stats['total']}\n"
        f"Подтверждено: {stats['confirmed']}\n"
        f"Отменено: {stats['cancelled']}\n"
        f"Завершено: {stats['completed']}\n"
        f"Выручка (completed): {stats['revenue']} ₽"
    )
    await edit_or_answer(query, text, admin_menu_keyboard())
    await query.answer()
