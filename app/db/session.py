from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base


engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    global engine, SessionLocal
    engine = create_async_engine(database_url, future=True, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    return engine, SessionLocal


async def create_tables() -> None:
    if engine is None:
        raise RuntimeError("Engine is not initialized")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
