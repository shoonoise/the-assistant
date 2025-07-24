"""Database utilities for The Assistant."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import cast

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from the_assistant.settings import get_settings

from .service import UserService


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Provide a SQLAlchemy session dependency."""
    database_url = get_settings().database_url
    engine = create_async_engine(database_url, echo=False)

    AsyncSessionMaker = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSessionMaker() as session:
        yield session


_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return a cached ``async_sessionmaker`` instance."""
    global _engine, _session_maker
    if _session_maker is None:
        database_url = get_settings().database_url
        _engine = create_async_engine(database_url, echo=False)
        _session_maker = async_sessionmaker(_engine, expire_on_commit=False)

    assert _session_maker is not None
    return cast(async_sessionmaker[AsyncSession], _session_maker)


def get_user_service() -> UserService:
    """Return a :class:`UserService` instance using the default session maker."""

    return UserService(get_session_maker())
