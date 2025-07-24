"""Database service utilities for user management."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .models import User, UserSetting


class UserService:
    """High level service for working with :class:`User` records."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self._session_maker = session_maker

    async def create_user(self, **data: Any) -> User:
        """Create and persist a new user."""
        async with self._session_maker() as session:
            user = User(**data)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Retrieve a user by primary key."""
        async with self._session_maker() as session:
            return await session.get(User, user_id)

    async def get_user_by_telegram_chat_id(self, telegram_chat_id: int) -> User | None:
        """Retrieve a user by Telegram chat ID."""
        async with self._session_maker() as session:
            stmt = select(User).where(User.telegram_chat_id == telegram_chat_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def set_google_credentials(
        self, user_id: int, credentials_enc: str | None
    ) -> None:
        """Store encrypted Google credentials for a user."""
        async with self._session_maker() as session:
            user = await session.get(User, user_id)
            if user is None:
                return
            user.google_credentials_enc = credentials_enc
            user.google_creds_updated_at = (
                datetime.now(UTC) if credentials_enc else None
            )
            await session.commit()

    async def get_google_credentials(self, user_id: int) -> str | None:
        """Return encrypted Google credentials for a user."""
        async with self._session_maker() as session:
            user = await session.get(User, user_id)
            return user.google_credentials_enc if user else None

    async def update_user(self, user_id: int, **data: Any) -> User | None:
        """Update a user's fields and return the updated record."""
        async with self._session_maker() as session:
            user = await session.get(User, user_id)
            if user is None:
                return None
            for field, value in data.items():
                setattr(user, field, value)
            await session.commit()
            await session.refresh(user)
            return user

    async def set_setting(self, user_id: int, key: str, value: Any) -> None:
        """Set or update a user setting."""
        async with self._session_maker() as session:
            stmt = select(UserSetting).where(
                UserSetting.user_id == user_id, UserSetting.key == key
            )
            result = await session.execute(stmt)
            setting = result.scalar_one_or_none()
            if setting:
                setting.value_json = json.dumps(value)
            else:
                setting = UserSetting(
                    user_id=user_id, key=key, value_json=json.dumps(value)
                )
                session.add(setting)
            await session.commit()

    async def get_setting(self, user_id: int, key: str) -> Any | None:
        """Return a single user setting value or ``None`` if missing."""
        async with self._session_maker() as session:
            stmt = select(UserSetting.value_json).where(
                UserSetting.user_id == user_id, UserSetting.key == key
            )
            result = await session.execute(stmt)
            value_json = result.scalar_one_or_none()
            if value_json is None:
                return None
            return json.loads(value_json)

    async def get_all_settings(self, user_id: int) -> dict[str, Any]:
        """Return all settings for the given user."""
        async with self._session_maker() as session:
            stmt = select(UserSetting.key, UserSetting.value_json).where(
                UserSetting.user_id == user_id
            )
            result = await session.execute(stmt)
            rows = result.all()
            return {
                key: json.loads(value_json) if value_json is not None else None
                for key, value_json in rows
            }

    async def unset_setting(self, user_id: int, key: str) -> None:
        """Remove a setting for the given user."""
        async with self._session_maker() as session:
            stmt = delete(UserSetting).where(
                UserSetting.user_id == user_id, UserSetting.key == key
            )
            await session.execute(stmt)
            await session.commit()
