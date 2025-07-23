"""Database utilities for The Assistant."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# TODO: use the new settings module
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://temporal:temporal@postgresql:5432/the_assistant",
)

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionMaker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Provide a SQLAlchemy session dependency."""
    async with AsyncSessionMaker() as session:
        yield session
