from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role, User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    full_name: str | None,
    is_admin: bool,
) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    role = Role.ADMIN if is_admin else Role.USER

    if user is None:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    changed = False
    if full_name and user.full_name != full_name:
        user.full_name = full_name
        changed = True
    if user.role != role:
        user.role = role
        changed = True
    if changed:
        await session.commit()
        await session.refresh(user)
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()
