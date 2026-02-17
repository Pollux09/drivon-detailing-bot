from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from app.bot.handlers import admin, common, errors, user
from app.bot.middlewares.db import DbSessionMiddleware
from app.config import get_settings
from app.db.session import create_tables, init_engine
from app.logging_config import configure_logging
from app.scheduler.jobs import build_scheduler
from app.services.admin_service import AdminService
from app.services.booking_service import BookingService
from app.services.bootstrap_service import seed_reference_data
from app.services.notification_service import NotificationService
from app.services.schedule_service import ScheduleService


logger = logging.getLogger(__name__)


async def _run_with_retries(
    operation: Callable[[], Awaitable[None]],
    *,
    attempts: int = 15,
    delay_seconds: float = 2.0,
    title: str = "operation",
) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            await operation()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == attempts:
                break
            logger.warning(
                "%s failed (attempt %s/%s), retry in %.1fs",
                title,
                attempt,
                attempts,
                delay_seconds,
            )
            await asyncio.sleep(delay_seconds)
    assert last_error is not None
    raise last_error


async def main() -> None:
    configure_logging()
    settings = get_settings()

    _, session_factory = init_engine(settings.database_url)
    await _run_with_retries(create_tables, title="create_tables")

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    schedule_service = ScheduleService(timezone=settings.timezone, max_posts=settings.max_posts)
    booking_service = BookingService(schedule_service=schedule_service)
    admin_service = AdminService()

    async def init_reference_data() -> None:
        async with session_factory() as session:
            await schedule_service.ensure_default_schedule(session)
            await seed_reference_data(session)

    await _run_with_retries(init_reference_data, title="bootstrap_data")

    notification_service = NotificationService(bot=bot, session_factory=session_factory, timezone=settings.timezone)
    scheduler = build_scheduler(notification_service, settings.timezone)
    scheduler.start()

    dp.update.middleware(DbSessionMiddleware(session_factory))

    dp["settings"] = settings
    dp["schedule_service"] = schedule_service
    dp["booking_service"] = booking_service
    dp["admin_service"] = admin_service

    dp.include_router(common.router)
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(errors.router)

    logger.info("Bot is starting polling")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
