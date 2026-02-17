from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.db.models import Booking, BookingStatus
from app.utils.datetime_utils import format_dt


logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot, session_factory: async_sessionmaker[AsyncSession], timezone) -> None:
        self.bot = bot
        self.session_factory = session_factory
        self.timezone = timezone

    async def _send_reminder(self, booking: Booking, hours_before: int) -> None:
        text = (
            f"⏰ Напоминание: запись через {hours_before} ч.\n"
            f"Услуга: {booking.service.name}\n"
            f"Начало: {format_dt(booking.booking_start, self.timezone)}"
        )
        await self.bot.send_message(booking.user.telegram_id, text)

    async def process_reminders(self) -> None:
        now = datetime.now(self.timezone)

        async with self.session_factory() as session:
            await self._process_window(
                session=session,
                start=now + timedelta(hours=23, minutes=50),
                end=now + timedelta(hours=24, minutes=10),
                hours_before=24,
                reminder_field="reminder_24h_sent",
            )
            await self._process_window(
                session=session,
                start=now + timedelta(hours=1, minutes=50),
                end=now + timedelta(hours=2, minutes=10),
                hours_before=2,
                reminder_field="reminder_2h_sent",
            )
            await session.commit()

    async def _process_window(
        self,
        session: AsyncSession,
        *,
        start: datetime,
        end: datetime,
        hours_before: int,
        reminder_field: str,
    ) -> None:
        query = (
            select(Booking)
            .options(selectinload(Booking.user), selectinload(Booking.service))
            .where(
                Booking.status == BookingStatus.CONFIRMED,
                Booking.booking_start >= start,
                Booking.booking_start < end,
            )
        )

        if reminder_field == "reminder_24h_sent":
            query = query.where(Booking.reminder_24h_sent.is_(False))
        else:
            query = query.where(Booking.reminder_2h_sent.is_(False))

        result = await session.execute(query)
        bookings = result.scalars().all()

        for booking in bookings:
            try:
                await self._send_reminder(booking, hours_before)
                if reminder_field == "reminder_24h_sent":
                    booking.reminder_24h_sent = True
                else:
                    booking.reminder_2h_sent = True
            except Exception:
                logger.exception("Failed to send reminder for booking_id=%s", booking.id)
