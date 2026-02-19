from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Booking, BookingAdminNote, BookingStatus, CarType, Service, User
from app.services.schedule_service import ScheduleService


booking_logger = logging.getLogger("booking_events")


class BookingService:
    def __init__(self, schedule_service: ScheduleService) -> None:
        self.schedule_service = schedule_service

    async def get_active_services(self, session: AsyncSession) -> list[Service]:
        result = await session.execute(select(Service).where(Service.is_active.is_(True)).order_by(Service.name.asc()))
        return list(result.scalars().all())

    async def get_all_services(self, session: AsyncSession) -> list[Service]:
        result = await session.execute(select(Service).order_by(Service.created_at.desc()))
        return list(result.scalars().all())

    async def get_service(self, session: AsyncSession, service_id: int) -> Service | None:
        result = await session.execute(select(Service).where(Service.id == service_id))
        return result.scalar_one_or_none()

    async def get_active_car_types(self, session: AsyncSession) -> list[CarType]:
        result = await session.execute(select(CarType).where(CarType.is_active.is_(True)).order_by(CarType.name.asc()))
        return list(result.scalars().all())

    async def get_all_car_types(self, session: AsyncSession) -> list[CarType]:
        result = await session.execute(select(CarType).order_by(CarType.name.asc()))
        return list(result.scalars().all())

    async def get_car_type(self, session: AsyncSession, car_type_id: int) -> CarType | None:
        result = await session.execute(select(CarType).where(CarType.id == car_type_id))
        return result.scalar_one_or_none()

    @staticmethod
    def calculate_price(base_price: Decimal, multiplier: Decimal) -> Decimal:
        return (base_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def create_booking(
        self,
        session: AsyncSession,
        user: User,
        service: Service,
        car_type: CarType,
        booking_start: datetime,
    ) -> Booking:
        duration = service.duration_minutes
        booking_end = booking_start + timedelta(minutes=duration)

        in_schedule = await self.schedule_service.is_slot_available(session, booking_start, duration)
        if not in_schedule:
            raise ValueError("slot_not_available")

        # Final availability re-check with row lock to avoid double booking race.
        overlap = await self.schedule_service.get_overlapping_bookings(
            session,
            booking_start,
            booking_end,
            for_update=True,
        )
        blocks = await self.schedule_service.get_active_blocks(session, booking_start, booking_end)
        if blocks or len(overlap) >= self.schedule_service.max_posts:
            raise ValueError("slot_not_available")

        post_id = await self.schedule_service.assign_post_id(
            session,
            booking_start,
            booking_end,
            for_update=True,
        )
        if post_id is None:
            raise ValueError("slot_not_available")

        final_price = self.calculate_price(service.base_price, car_type.price_multiplier)

        booking = Booking(
            user_id=user.id,
            service_id=service.id,
            car_type_id=car_type.id,
            post_id=post_id,
            booking_start=booking_start,
            booking_end=booking_end,
            final_price=final_price,
            status=BookingStatus.CONFIRMED,
            reminder_24h_sent=False,
            reminder_2h_sent=False,
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)

        booking_logger.info(
            "booking_created booking_id=%s user_tg=%s service_id=%s start=%s end=%s",
            booking.id,
            user.telegram_id,
            service.id,
            booking_start.isoformat(),
            booking_end.isoformat(),
        )
        return booking

    async def get_user_confirmed_bookings(self, session: AsyncSession, user_id: int, limit: int = 10) -> list[Booking]:
        result = await session.execute(
            select(Booking)
            .where(Booking.user_id == user_id, Booking.status == BookingStatus.CONFIRMED)
            .order_by(Booking.booking_start.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_booking(self, session: AsyncSession, booking_id: int) -> Booking | None:
        result = await session.execute(
            select(Booking)
            .options(
                selectinload(Booking.user),
                selectinload(Booking.service),
                selectinload(Booking.car_type),
            )
            .where(Booking.id == booking_id)
        )
        return result.scalar_one_or_none()

    async def list_bookings(self, session: AsyncSession, limit: int = 50) -> list[Booking]:
        result = await session.execute(select(Booking).order_by(Booking.booking_start.desc()).limit(limit))
        return list(result.scalars().all())

    async def list_today_bookings(self, session: AsyncSession, timezone, limit: int = 50) -> list[Booking]:
        now = datetime.now(timezone)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        result = await session.execute(
            select(Booking)
            .where(Booking.booking_start >= start, Booking.booking_start < end)
            .order_by(Booking.booking_start.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_booking_admin_notes(
        self,
        session: AsyncSession,
        booking_id: int,
        limit: int = 5,
    ) -> list[BookingAdminNote]:
        result = await session.execute(
            select(BookingAdminNote)
            .where(BookingAdminNote.booking_id == booking_id)
            .order_by(BookingAdminNote.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_admin_note(
        self,
        session: AsyncSession,
        booking: Booking,
        admin_telegram_id: int,
        text: str,
    ) -> BookingAdminNote:
        note = BookingAdminNote(
            booking_id=booking.id,
            admin_telegram_id=admin_telegram_id,
            text=text,
        )
        session.add(note)
        await session.commit()
        await session.refresh(note)
        return note

    async def cancel_booking(self, session: AsyncSession, booking: Booking, reason: str | None = None) -> Booking:
        booking.status = BookingStatus.CANCELLED
        await session.commit()
        booking_logger.info("booking_cancelled booking_id=%s reason=%s", booking.id, reason or "n/a")
        return booking

    async def move_booking(self, session: AsyncSession, booking: Booking, new_start: datetime, duration_minutes: int) -> Booking:
        new_end = new_start + timedelta(minutes=duration_minutes)
        is_available = await self.schedule_service.is_slot_available(
            session,
            new_start,
            duration_minutes,
            exclude_booking_id=booking.id,
        )
        if not is_available:
            raise ValueError("slot_not_available")

        post_id = await self.schedule_service.assign_post_id(
            session,
            new_start,
            new_end,
            exclude_booking_id=booking.id,
            for_update=True,
        )
        if post_id is None:
            raise ValueError("slot_not_available")

        booking.booking_start = new_start
        booking.booking_end = new_end
        booking.post_id = post_id
        booking.reminder_24h_sent = False
        booking.reminder_2h_sent = False
        await session.commit()
        booking_logger.info("booking_moved booking_id=%s new_start=%s", booking.id, new_start.isoformat())
        return booking

    async def get_stats(self, session: AsyncSession) -> dict[str, int | Decimal]:
        total_bookings = await session.scalar(select(func.count(Booking.id)))
        confirmed = await session.scalar(select(func.count(Booking.id)).where(Booking.status == BookingStatus.CONFIRMED))
        cancelled = await session.scalar(select(func.count(Booking.id)).where(Booking.status == BookingStatus.CANCELLED))
        completed = await session.scalar(select(func.count(Booking.id)).where(Booking.status == BookingStatus.COMPLETED))
        revenue = await session.scalar(
            select(func.coalesce(func.sum(Booking.final_price), 0)).where(Booking.status == BookingStatus.COMPLETED)
        )
        return {
            "total": int(total_bookings or 0),
            "confirmed": int(confirmed or 0),
            "cancelled": int(cancelled or 0),
            "completed": int(completed or 0),
            "revenue": revenue,
        }
