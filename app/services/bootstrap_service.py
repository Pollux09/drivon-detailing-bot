from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CarType, Service


async def seed_reference_data(session: AsyncSession) -> None:
    services_count = await session.scalar(select(func.count(Service.id)))
    if not services_count:
        session.add_all(
            [
                Service(
                    name="Комплексная мойка",
                    description="Кузов, салон, стекла",
                    duration_minutes=120,
                    base_price=Decimal("3500.00"),
                    is_active=True,
                ),
                Service(
                    name="Полировка",
                    description="Восстановительная полировка кузова",
                    duration_minutes=240,
                    base_price=Decimal("12000.00"),
                    is_active=True,
                ),
            ]
        )

    car_types_count = await session.scalar(select(func.count(CarType.id)))
    if not car_types_count:
        session.add_all(
            [
                CarType(name="Седан", price_multiplier=Decimal("1.00"), is_active=True),
                CarType(name="Кроссовер", price_multiplier=Decimal("1.20"), is_active=True),
                CarType(name="Внедорожник", price_multiplier=Decimal("1.35"), is_active=True),
            ]
        )

    await session.commit()
