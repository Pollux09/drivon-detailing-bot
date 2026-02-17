from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BlockedSlot, Booking, BookingStatus, WorkSchedule
from app.utils.datetime_utils import combine_local


class ScheduleService:
    def __init__(self, timezone, max_posts: int = 1) -> None:
        self.timezone = timezone
        self.max_posts = max_posts

    async def ensure_default_schedule(self, session: AsyncSession) -> None:
        count = await session.scalar(select(WorkSchedule.id).limit(1))
        if count:
            return

        rows: list[WorkSchedule] = []
        for day in range(7):
            if day < 5:
                rows.append(WorkSchedule(day_of_week=day, start_time=time(0, 0), end_time=time(23, 59), is_active=True))
            else:
                rows.append(WorkSchedule(day_of_week=day, start_time=time(9, 0), end_time=time(23, 0), is_active=True))
        session.add_all(rows)
        await session.commit()

    async def get_day_window(self, session: AsyncSession, day: date) -> tuple[datetime, datetime] | None:
        day_of_week = day.weekday()
        result = await session.execute(
            select(WorkSchedule)
            .where(WorkSchedule.day_of_week == day_of_week, WorkSchedule.is_active.is_(True))
            .order_by(WorkSchedule.id.desc())
            .limit(1)
        )
        schedule = result.scalar_one_or_none()

        if schedule is None:
            # Fallback to requested business rule.
            if day_of_week < 5:
                start_time = time(0, 0)
                end_time = time(23, 59)
            else:
                start_time = time(9, 0)
                end_time = time(23, 0)
        else:
            start_time = schedule.start_time
            end_time = schedule.end_time

        start_dt = combine_local(day, start_time, self.timezone)
        if end_time.hour == 23 and end_time.minute == 59:
            end_dt = combine_local(day + timedelta(days=1), time(0, 0), self.timezone)
        else:
            end_dt = combine_local(day, end_time, self.timezone)

        if end_dt <= start_dt:
            return None
        return start_dt, end_dt

    async def get_overlapping_bookings(
        self,
        session: AsyncSession,
        start: datetime,
        end: datetime,
        *,
        for_update: bool = False,
        exclude_booking_id: int | None = None,
    ) -> list[Booking]:
        query = select(Booking).where(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.booking_end > start,
            Booking.booking_start < end,
        )
        if exclude_booking_id is not None:
            query = query.where(Booking.id != exclude_booking_id)
        if for_update:
            query = query.with_for_update()
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_active_blocks(
        self,
        session: AsyncSession,
        start: datetime,
        end: datetime,
    ) -> list[BlockedSlot]:
        result = await session.execute(
            select(BlockedSlot).where(
                BlockedSlot.is_active.is_(True),
                BlockedSlot.end_datetime > start,
                BlockedSlot.start_datetime < end,
            )
        )
        return list(result.scalars().all())

    async def is_slot_available(
        self,
        session: AsyncSession,
        start: datetime,
        duration_minutes: int,
        *,
        exclude_booking_id: int | None = None,
    ) -> bool:
        end = start + timedelta(minutes=duration_minutes)
        window = await self.get_day_window(session, start.astimezone(self.timezone).date())
        if window is None:
            return False

        day_start, day_end = window
        if start < day_start or end > day_end:
            return False

        blocks = await self.get_active_blocks(session, start, end)
        if blocks:
            return False

        overlaps = await self.get_overlapping_bookings(session, start, end, exclude_booking_id=exclude_booking_id)
        return len(overlaps) < self.max_posts

    async def assign_post_id(
        self,
        session: AsyncSession,
        start: datetime,
        end: datetime,
        *,
        exclude_booking_id: int | None = None,
        for_update: bool = False,
    ) -> int | None:
        overlaps = await self.get_overlapping_bookings(
            session,
            start,
            end,
            for_update=for_update,
            exclude_booking_id=exclude_booking_id,
        )
        used = {booking.post_id for booking in overlaps}
        for post_id in range(1, self.max_posts + 1):
            if post_id not in used:
                return post_id
        return None

    async def get_available_slots(
        self,
        session: AsyncSession,
        day: date,
        duration_minutes: int,
        *,
        exclude_booking_id: int | None = None,
        limit: int | None = None,
    ) -> list[datetime]:
        window = await self.get_day_window(session, day)
        if window is None:
            return []

        day_start, day_end = window
        now = datetime.now(self.timezone)
        cursor = day_start.replace(minute=0, second=0, microsecond=0)
        if cursor < day_start:
            cursor += timedelta(hours=1)

        slots: list[datetime] = []
        while cursor + timedelta(minutes=duration_minutes) <= day_end:
            if cursor >= now:
                available = await self.is_slot_available(
                    session,
                    cursor,
                    duration_minutes,
                    exclude_booking_id=exclude_booking_id,
                )
                if available:
                    slots.append(cursor)
                    if limit and len(slots) >= limit:
                        break
            cursor += timedelta(hours=1)

        return slots

    async def get_available_days(
        self,
        session: AsyncSession,
        start_day: date,
        duration_minutes: int,
        horizon_days: int = 14,
        exclude_booking_id: int | None = None,
    ) -> list[date]:
        days: list[date] = []
        for offset in range(horizon_days):
            day = start_day + timedelta(days=offset)
            slots = await self.get_available_slots(
                session,
                day,
                duration_minutes,
                exclude_booking_id=exclude_booking_id,
                limit=1,
            )
            if slots:
                days.append(day)
        return days

    async def close_slot(
        self,
        session: AsyncSession,
        start: datetime,
        end: datetime,
        telegram_id: int,
        note: str | None = None,
    ) -> BlockedSlot:
        blocked = BlockedSlot(
            start_datetime=start,
            end_datetime=end,
            is_active=True,
            note=note,
            created_by_telegram_id=telegram_id,
        )
        session.add(blocked)
        await session.commit()
        await session.refresh(blocked)
        return blocked

    async def reopen_slot(self, session: AsyncSession, block_id: int) -> bool:
        result = await session.execute(select(BlockedSlot).where(BlockedSlot.id == block_id))
        block = result.scalar_one_or_none()
        if block is None:
            return False
        block.is_active = False
        await session.commit()
        return True

    async def list_active_blocks(self, session: AsyncSession, limit: int = 20) -> list[BlockedSlot]:
        result = await session.execute(
            select(BlockedSlot)
            .where(BlockedSlot.is_active.is_(True))
            .order_by(BlockedSlot.start_datetime.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
