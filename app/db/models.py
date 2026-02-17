from __future__ import annotations

import enum
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Role(enum.StrEnum):
    USER = "user"
    ADMIN = "admin"


class BookingStatus(enum.StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), default=Role.USER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")


class Service(Base, TimestampMixin):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="service")


class CarType(Base):
    __tablename__ = "car_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    price_multiplier: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=1.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    bookings: Mapped[list["Booking"]] = relationship(back_populates="car_type")


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False)
    car_type_id: Mapped[int] = mapped_column(ForeignKey("car_types.id"), nullable=False)

    post_id: Mapped[int] = mapped_column(default=1, nullable=False)
    booking_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    booking_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

    final_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"),
        default=BookingStatus.CONFIRMED,
        nullable=False,
    )

    reminder_24h_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_2h_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="bookings")
    service: Mapped["Service"] = relationship(back_populates="bookings")
    car_type: Mapped["CarType"] = relationship(back_populates="bookings")


class WorkSchedule(Base):
    __tablename__ = "work_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    day_of_week: Mapped[int] = mapped_column(nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BlockedSlot(Base):
    __tablename__ = "blocked_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


Index("ix_work_schedule_day_active", WorkSchedule.day_of_week, WorkSchedule.is_active)
Index("ix_booking_status_start", Booking.status, Booking.booking_start)
