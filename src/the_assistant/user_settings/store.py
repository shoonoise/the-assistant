import json
from typing import Any

import asyncpg


class UserSettingsStore:
    """Persistence layer for user settings using Postgres."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    async def get(self, user_id: int, key: str) -> Any | None:
        """Retrieve a single setting value for a user."""
        conn = await asyncpg.connect(self.database_url)
        try:
            row = await conn.fetchrow(
                "SELECT value_json FROM user_settings WHERE user_id = $1 AND key = $2",
                user_id,
                key,
            )
            if row:
                return json.loads(row["value_json"])
            return None
        finally:
            await conn.close()

    async def get_all(self, user_id: int) -> dict[str, Any]:
        """Get all settings for a user as a dictionary."""
        conn = await asyncpg.connect(self.database_url)
        try:
            rows = await conn.fetch(
                "SELECT key, value_json FROM user_settings WHERE user_id = $1",
                user_id,
            )
            return {row["key"]: json.loads(row["value_json"]) for row in rows}
        finally:
            await conn.close()

    async def list_keys(self) -> list[str]:
        """Return all distinct setting keys available."""
        conn = await asyncpg.connect(self.database_url)
        try:
            rows = await conn.fetch(
                "SELECT DISTINCT key FROM user_settings ORDER BY key"
            )
            return [row["key"] for row in rows]
        finally:
            await conn.close()

    async def set(self, user_id: int, key: str, value: Any) -> None:
        """Set a setting value for a user."""
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(
                """
                INSERT INTO user_settings (user_id, key, value_json, created_at, updated_at)
                VALUES ($1, $2, $3, now(), now())
                ON CONFLICT (user_id, key) DO UPDATE
                SET value_json = EXCLUDED.value_json, updated_at = now()
                """,
                user_id,
                key,
                json.dumps(value),
            )
        finally:
            await conn.close()

    async def unset(self, user_id: int, key: str) -> None:
        """Remove a setting for a user."""
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(
                "DELETE FROM user_settings WHERE user_id = $1 AND key = $2",
                user_id,
                key,
            )
        finally:
            await conn.close()
