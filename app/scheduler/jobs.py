from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler


def build_scheduler(notification_service, timezone) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=timezone)
    scheduler.add_job(
        notification_service.process_reminders,
        trigger="interval",
        minutes=10,
        id="booking_reminders",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
    )
    return scheduler
