from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.helpers import edit_or_answer
from app.bot.keyboards.user import (
    car_types_keyboard,
    confirm_keyboard,
    dates_keyboard,
    main_menu_keyboard,
    services_keyboard,
    times_keyboard,
)
from app.bot.states import BookingStates
from app.config import Settings
from app.services.user_service import get_or_create_user
from app.utils.callbacks import CarTypeSelectCb, ConfirmCb, DateSelectCb, MenuActionCb, ServiceSelectCb, TimeSelectCb
from app.utils.datetime_utils import format_dt, from_iso_day


router = Router(name="user")
logger = logging.getLogger(__name__)


async def _show_services(query: CallbackQuery, state: FSMContext, booking_service, session: AsyncSession) -> None:
    services = await booking_service.get_active_services(session)
    if not services:
        await edit_or_answer(query, "Активных услуг пока нет.", main_menu_keyboard())
        return
    await state.set_state(BookingStates.choosing_service)
    await edit_or_answer(query, "Выберите услугу", services_keyboard(services))


async def _show_car_types(query: CallbackQuery, state: FSMContext, booking_service, session: AsyncSession) -> None:
    car_types = await booking_service.get_active_car_types(session)
    if not car_types:
        await edit_or_answer(query, "Нет активных типов авто.", main_menu_keyboard())
        return
    await state.set_state(BookingStates.choosing_car_type)
    await edit_or_answer(query, "Выберите тип автомобиля", car_types_keyboard(car_types))


async def _show_available_dates(
    query: CallbackQuery,
    state: FSMContext,
    schedule_service,
    booking_service,
    session: AsyncSession,
    settings: Settings,
) -> None:
    data = await state.get_data()
    service_id = data.get("service_id")
    if not service_id:
        await _show_services(query, state, booking_service, session)
        return

    service = await booking_service.get_service(session, service_id)
    if service is None:
        await edit_or_answer(query, "Услуга не найдена.", main_menu_keyboard())
        return

    today = datetime.now(settings.timezone).date()
    days = await schedule_service.get_available_days(session, today, service.duration_minutes, horizon_days=14)
    if not days:
        await edit_or_answer(query, "Нет доступных дат в ближайшие 14 дней.", main_menu_keyboard())
        return

    await state.set_state(BookingStates.choosing_date)
    await edit_or_answer(query, "Выберите дату", dates_keyboard(days))


async def _show_available_times(
    query: CallbackQuery,
    state: FSMContext,
    schedule_service,
    booking_service,
    session: AsyncSession,
    settings: Settings,
) -> None:
    data = await state.get_data()
    service_id = data.get("service_id")
    selected_day = data.get("selected_day")
    if not service_id or not selected_day:
        await _show_available_dates(query, state, schedule_service, booking_service, session, settings)
        return

    service = await booking_service.get_service(session, service_id)
    if service is None:
        await edit_or_answer(query, "Услуга не найдена.", main_menu_keyboard())
        return

    day = from_iso_day(selected_day)
    slots = await schedule_service.get_available_slots(session, day, service.duration_minutes)
    if not slots:
        await edit_or_answer(query, "На эту дату свободных слотов нет. Выберите другую.")
        return

    await state.set_state(BookingStates.choosing_time)
    await edit_or_answer(query, "Выберите время", times_keyboard(slots))


@router.callback_query(MenuActionCb.filter(F.action == "book"))
async def booking_start(query: CallbackQuery, state: FSMContext, booking_service, session: AsyncSession) -> None:
    await state.clear()
    await _show_services(query, state, booking_service, session)
    await query.answer()


@router.callback_query(ServiceSelectCb.filter(), BookingStates.choosing_service)
async def service_selected(
    query: CallbackQuery,
    callback_data: ServiceSelectCb,
    state: FSMContext,
    booking_service,
    session: AsyncSession,
) -> None:
    service = await booking_service.get_service(session, callback_data.service_id)
    if service is None or not service.is_active:
        await query.answer("Услуга недоступна", show_alert=True)
        return

    await state.update_data(service_id=service.id)
    await _show_car_types(query, state, booking_service, session)
    await query.answer()


@router.callback_query(MenuActionCb.filter(F.action == "back_services"), BookingStates.choosing_car_type)
async def back_to_services(query: CallbackQuery, state: FSMContext, booking_service, session: AsyncSession) -> None:
    await _show_services(query, state, booking_service, session)
    await query.answer()


@router.callback_query(CarTypeSelectCb.filter(), BookingStates.choosing_car_type)
async def car_type_selected(
    query: CallbackQuery,
    callback_data: CarTypeSelectCb,
    state: FSMContext,
    booking_service,
    schedule_service,
    session: AsyncSession,
    settings: Settings,
) -> None:
    car_type = await booking_service.get_car_type(session, callback_data.car_type_id)
    if car_type is None or not car_type.is_active:
        await query.answer("Тип авто недоступен", show_alert=True)
        return

    data = await state.get_data()
    service = await booking_service.get_service(session, data["service_id"])
    if service is None:
        await query.answer("Услуга недоступна", show_alert=True)
        return

    price = booking_service.calculate_price(service.base_price, car_type.price_multiplier)
    await state.update_data(car_type_id=car_type.id, final_price=str(price))
    await _show_available_dates(query, state, schedule_service, booking_service, session, settings)
    await query.answer()


@router.callback_query(MenuActionCb.filter(F.action == "back_car_types"), BookingStates.choosing_date)
async def back_to_car_types(query: CallbackQuery, state: FSMContext, booking_service, session: AsyncSession) -> None:
    await _show_car_types(query, state, booking_service, session)
    await query.answer()


@router.callback_query(DateSelectCb.filter(), BookingStates.choosing_date)
async def date_selected(
    query: CallbackQuery,
    callback_data: DateSelectCb,
    state: FSMContext,
    booking_service,
    schedule_service,
    session: AsyncSession,
    settings: Settings,
) -> None:
    await state.update_data(selected_day=callback_data.day)
    await _show_available_times(query, state, schedule_service, booking_service, session, settings)
    await query.answer()


@router.callback_query(MenuActionCb.filter(F.action == "back_dates"), BookingStates.choosing_time)
async def back_to_dates(
    query: CallbackQuery,
    state: FSMContext,
    booking_service,
    schedule_service,
    session: AsyncSession,
    settings: Settings,
) -> None:
    await _show_available_dates(query, state, schedule_service, booking_service, session, settings)
    await query.answer()


@router.callback_query(TimeSelectCb.filter(), BookingStates.choosing_time)
async def time_selected(
    query: CallbackQuery,
    callback_data: TimeSelectCb,
    state: FSMContext,
    booking_service,
    session: AsyncSession,
    settings: Settings,
) -> None:
    data = await state.get_data()
    service = await booking_service.get_service(session, data["service_id"])
    car_type = await booking_service.get_car_type(session, data["car_type_id"])
    if service is None or car_type is None:
        await query.answer("Ошибка данных", show_alert=True)
        return

    booking_start = datetime.fromtimestamp(callback_data.ts, tz=settings.timezone)
    booking_end = booking_start + timedelta(minutes=service.duration_minutes)
    price = booking_service.calculate_price(service.base_price, car_type.price_multiplier)

    summary = (
        "Проверьте запись:\n"
        f"Услуга: {service.name}\n"
        f"Авто: {car_type.name}\n"
        f"Начало: {format_dt(booking_start, settings.timezone)}\n"
        f"Окончание: {format_dt(booking_end, settings.timezone)}\n"
        f"Итог: {price} ₽"
    )

    await state.update_data(booking_ts=callback_data.ts)
    await state.set_state(BookingStates.confirming)
    await edit_or_answer(query, summary, confirm_keyboard())
    await query.answer()


@router.callback_query(MenuActionCb.filter(F.action == "back_times"), BookingStates.confirming)
async def back_to_times(
    query: CallbackQuery,
    state: FSMContext,
    booking_service,
    schedule_service,
    session: AsyncSession,
    settings: Settings,
) -> None:
    await _show_available_times(query, state, schedule_service, booking_service, session, settings)
    await query.answer()


@router.callback_query(ConfirmCb.filter(F.action == "book"), BookingStates.confirming)
async def confirm_booking(
    query: CallbackQuery,
    state: FSMContext,
    booking_service,
    schedule_service,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if query.from_user is None:
        await query.answer("Ошибка пользователя", show_alert=True)
        return

    data = await state.get_data()
    service = await booking_service.get_service(session, data["service_id"])
    car_type = await booking_service.get_car_type(session, data["car_type_id"])
    booking_start = datetime.fromtimestamp(data["booking_ts"], tz=settings.timezone)
    if service is None or car_type is None:
        await query.answer("Услуга/тип авто недоступны", show_alert=True)
        return

    is_available = await schedule_service.is_slot_available(session, booking_start, service.duration_minutes)
    if not is_available:
        await edit_or_answer(query, "Слот уже занят. Выберите другое время.")
        await _show_available_times(query, state, schedule_service, booking_service, session, settings)
        await query.answer()
        return

    user = await get_or_create_user(
        session,
        telegram_id=query.from_user.id,
        full_name=query.from_user.full_name,
        is_admin=query.from_user.id in settings.admin_ids,
    )

    try:
        booking = await booking_service.create_booking(session, user, service, car_type, booking_start)
    except ValueError:
        await edit_or_answer(query, "Не удалось подтвердить запись: слот уже занят.")
        await _show_available_times(query, state, schedule_service, booking_service, session, settings)
        await query.answer()
        return
    except Exception:
        logger.exception("Failed to create booking")
        await query.answer("Ошибка сохранения", show_alert=True)
        return

    await state.clear()

    success_text = (
        "✅ Запись подтверждена\n"
        f"Номер: #{booking.id}\n"
        f"{service.name}\n"
        f"{format_dt(booking.booking_start, settings.timezone)}"
    )
    await edit_or_answer(query, success_text, main_menu_keyboard())

    admin_text = (
        "🆕 Новая запись\n"
        f"#{booking.id}\n"
        f"Клиент: {query.from_user.full_name} ({query.from_user.id})\n"
        f"Услуга: {service.name}\n"
        f"Авто: {car_type.name}\n"
        f"Время: {format_dt(booking.booking_start, settings.timezone)}"
    )
    for admin_id in settings.admin_ids:
        try:
            await query.bot.send_message(admin_id, admin_text)
        except Exception:
            logger.exception("Failed to notify admin=%s", admin_id)

    await query.answer("Запись создана")
