from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CarType, Service


admin_logger = logging.getLogger("admin_actions")


class AdminService:
    async def create_service(
        self,
        session: AsyncSession,
        *,
        name: str,
        description: str,
        duration_minutes: int,
        base_price: Decimal,
        admin_tg_id: int,
    ) -> Service:
        service = Service(
            name=name,
            description=description,
            duration_minutes=duration_minutes,
            base_price=base_price,
            is_active=True,
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)
        admin_logger.info("service_create admin=%s service_id=%s", admin_tg_id, service.id)
        return service

    async def update_service_field(
        self,
        session: AsyncSession,
        service: Service,
        field: str,
        value,
        admin_tg_id: int,
    ) -> Service:
        if field == "name":
            service.name = str(value)
        elif field == "description":
            service.description = str(value)
        elif field == "duration":
            service.duration_minutes = int(value)
        elif field == "price":
            service.base_price = Decimal(str(value))
        elif field == "active":
            service.is_active = bool(value)
        else:
            raise ValueError("unknown_field")

        await session.commit()
        await session.refresh(service)
        admin_logger.info("service_update admin=%s service_id=%s field=%s", admin_tg_id, service.id, field)
        return service

    async def set_service_active(
        self,
        session: AsyncSession,
        service: Service,
        active: bool,
        admin_tg_id: int,
    ) -> Service:
        service.is_active = active
        await session.commit()
        await session.refresh(service)
        admin_logger.info("service_toggle admin=%s service_id=%s active=%s", admin_tg_id, service.id, active)
        return service

    async def create_car_type(
        self,
        session: AsyncSession,
        *,
        name: str,
        multiplier: Decimal,
        admin_tg_id: int,
    ) -> CarType:
        car = CarType(
            name=name,
            price_multiplier=multiplier,
            is_active=True,
        )
        session.add(car)
        await session.commit()
        await session.refresh(car)
        admin_logger.info("car_type_create admin=%s car_id=%s", admin_tg_id, car.id)
        return car

    async def update_car_field(
        self,
        session: AsyncSession,
        car_type: CarType,
        field: str,
        value,
        admin_tg_id: int,
    ) -> CarType:
        if field == "name":
            car_type.name = str(value)
        elif field == "multiplier":
            car_type.price_multiplier = Decimal(str(value))
        elif field == "active":
            car_type.is_active = bool(value)
        else:
            raise ValueError("unknown_field")

        await session.commit()
        await session.refresh(car_type)
        admin_logger.info("car_type_update admin=%s car_id=%s field=%s", admin_tg_id, car_type.id, field)
        return car_type

    async def set_car_type_active(
        self,
        session: AsyncSession,
        car_type: CarType,
        active: bool,
        admin_tg_id: int,
    ) -> CarType:
        car_type.is_active = active
        await session.commit()
        await session.refresh(car_type)
        admin_logger.info("car_type_toggle admin=%s car_id=%s active=%s", admin_tg_id, car_type.id, active)
        return car_type

    async def list_services(self, session: AsyncSession) -> list[Service]:
        result = await session.execute(select(Service).order_by(Service.created_at.desc()))
        return list(result.scalars().all())

    async def list_car_types(self, session: AsyncSession) -> list[CarType]:
        result = await session.execute(select(CarType).order_by(CarType.name.asc()))
        return list(result.scalars().all())
