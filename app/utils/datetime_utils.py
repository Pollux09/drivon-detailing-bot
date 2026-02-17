from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def combine_local(day: date, hour_minute: time, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, hour_minute).replace(tzinfo=tz)


def to_iso_day(value: date) -> str:
    return value.strftime("%Y-%m-%d")


def from_iso_day(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_dt(value: datetime, tz: ZoneInfo) -> str:
    local = value.astimezone(tz)
    return local.strftime("%d.%m.%Y %H:%M")


def daterange(start: date, days: int) -> list[date]:
    return [start + timedelta(days=i) for i in range(days)]
