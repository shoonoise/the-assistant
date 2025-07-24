"""Database utilities for The Assistant."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from the_assistant.settings import get_settings

from .service import UserService


class DatabaseManager:
    """Manages database connections and sessions without global state."""

    def __init__(self, database_url: str | None = None):
        """Initialize the database manager with optional database URL."""
        self._database_url = database_url or get_settings().database_url
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker[AsyncSession] | None = None

    def _ensure_initialized(self) -> None:
        """Ensure engine and session maker are initialized."""
        if self._session_maker is None:
            self._engine = create_async_engine(self._database_url, echo=False)
            self._session_maker = async_sessionmaker(
                self._engine, expire_on_commit=False
            )

    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        """Provide a SQLAlchemy session dependency."""
        self._ensure_initialized()
        assert self._session_maker is not None

        async with self._session_maker() as session:
            yield session

    def get_session_maker(self) -> async_sessionmaker[AsyncSession]:
        """Return the session maker instance."""
        self._ensure_initialized()
        assert self._session_maker is not None
        return self._session_maker

    def get_user_service(self) -> UserService:
        """Return a UserService instance using this database manager."""
        return UserService(self.get_session_maker())

    async def close(self) -> None:
        """Close the database engine if it exists."""
        if self._engine is not None:
            await self._engine.dispose()


class _DefaultDatabaseManager:
    """Singleton holder for the default database manager."""

    _instance: DatabaseManager | None = None

    @classmethod
    def get_instance(cls) -> DatabaseManager:
        """Get the singleton database manager instance."""
        if cls._instance is None:
            cls._instance = DatabaseManager()
        return cls._instance


def get_database_manager() -> DatabaseManager:
    """Get the default database manager instance."""
    return _DefaultDatabaseManager.get_instance()


# Backward compatibility functions
async def get_session() -> AsyncGenerator[AsyncSession]:
    """Provide a SQLAlchemy session dependency."""
    db_manager = get_database_manager()
    async for session in db_manager.get_session():
        yield session


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return a cached async_sessionmaker instance."""
    return get_database_manager().get_session_maker()


def get_user_service() -> UserService:
    """Return a UserService instance using the default session maker."""
    return get_database_manager().get_user_service()
