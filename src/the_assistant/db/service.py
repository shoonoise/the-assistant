"""Database service utilities for user management."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from the_assistant.integrations.telegram.constants import SettingKey
from the_assistant.user_settings import SETTING_SCHEMAS

from .models import ThirdPartyAccount, User, UserSetting


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

    async def _set_third_party_credentials(
        self,
        user_id: int,
        provider: str,
        credentials_enc: str | None,
        account: str | None,
    ) -> None:
        """Create or update credentials for an external account."""
        async with self._session_maker() as session:
            stmt = (
                insert(ThirdPartyAccount)
                .values(
                    user_id=user_id,
                    provider=provider,
                    account=account,
                    credentials_enc=credentials_enc,
                    creds_updated_at=(datetime.now(UTC) if credentials_enc else None),
                )
                .on_conflict_do_update(
                    index_elements=[
                        ThirdPartyAccount.user_id,
                        ThirdPartyAccount.provider,
                        ThirdPartyAccount.account,
                    ],
                    set_={
                        "credentials_enc": credentials_enc,
                        "creds_updated_at": datetime.now(UTC)
                        if credentials_enc
                        else None,
                    },
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def _get_third_party_credentials(
        self, user_id: int, provider: str, account: str | None
    ) -> str | None:
        """Return credentials for an external account."""
        async with self._session_maker() as session:
            stmt = select(ThirdPartyAccount.credentials_enc).where(
                ThirdPartyAccount.user_id == user_id,
                ThirdPartyAccount.provider == provider,
                ThirdPartyAccount.account == account,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def set_google_credentials(
        self,
        user_id: int,
        credentials_enc: str | None,
        account: str | None = None,
    ) -> None:
        """Store encrypted Google credentials for a user.

        When ``account`` is provided the credentials are stored in the
        ``third_party_accounts`` table with provider ``"google"``. The original
        ``users.google_credentials_enc`` column is still used when ``account`` is
        ``None`` for backwards compatibility.
        """
        if account:
            await self._set_third_party_credentials(
                user_id, "google", credentials_enc, account
            )
            return

        async with self._session_maker() as session:
            user = await session.get(User, user_id)
            if user is None:
                return
            user.google_credentials_enc = credentials_enc
            user.google_creds_updated_at = (
                datetime.now(UTC) if credentials_enc else None
            )
            await session.commit()

    async def get_google_credentials(
        self, user_id: int, account: str | None = None
    ) -> str | None:
        """Return encrypted Google credentials for a user."""
        if account:
            return await self._get_third_party_credentials(user_id, "google", account)

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

    async def set_setting(self, user_id: int, key: SettingKey, value: Any) -> None:
        """Set or update a user setting with validation."""
        schema = cast(Any, SETTING_SCHEMAS[key])
        validated = schema.model_validate(value)
        payload = validated.model_dump()

        async with self._session_maker() as session:
            stmt = select(UserSetting).where(
                UserSetting.user_id == user_id, UserSetting.key == key.value
            )
            result = await session.execute(stmt)
            setting = result.scalar_one_or_none()
            if setting:
                setting.value_json = json.dumps(payload)
            else:
                setting = UserSetting(
                    user_id=user_id,
                    key=key.value,
                    value_json=json.dumps(payload),
                )
                session.add(setting)
            await session.commit()

    async def get_setting(self, user_id: int, key: SettingKey) -> Any | None:
        """Return a single user setting value or ``None`` if missing."""
        schema = cast(Any, SETTING_SCHEMAS[key])

        async with self._session_maker() as session:
            stmt = select(UserSetting.value_json).where(
                UserSetting.user_id == user_id, UserSetting.key == key.value
            )
            result = await session.execute(stmt)
            value_json = result.scalar_one_or_none()
            if value_json is None:
                return None
            data = json.loads(value_json)
            model = schema.model_validate(data)
            return model.to_python()

    async def get_all_settings(self, user_id: int) -> dict[str, Any]:
        """Return all settings for the given user with validation."""
        async with self._session_maker() as session:
            stmt = select(UserSetting.key, UserSetting.value_json).where(
                UserSetting.user_id == user_id
            )
            result = await session.execute(stmt)
            rows = result.all()
            data: dict[str, Any] = {}
            for key, value_json in rows:
                key_enum = SettingKey(key)
                schema = cast(Any, SETTING_SCHEMAS[key_enum])
                value = json.loads(value_json) if value_json is not None else None
                model = schema.model_validate(value)
                data[key] = model.to_python()
            return data

    async def unset_setting(self, user_id: int, key: SettingKey) -> None:
        """Remove a setting for the given user."""
        async with self._session_maker() as session:
            stmt = delete(UserSetting).where(
                UserSetting.user_id == user_id, UserSetting.key == key.value
            )
            await session.execute(stmt)
            await session.commit()
