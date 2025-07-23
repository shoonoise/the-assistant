"""Database utilities for The Assistant."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from the_assistant.settings import get_settings

database_url = get_settings().database_url
engine = create_async_engine(database_url, echo=False)

AsyncSessionMaker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Provide a SQLAlchemy session dependency."""
    async with AsyncSessionMaker() as session:
        yield session
