from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import httpx

from the_assistant.db import get_user_service
from the_assistant.integrations.ticktick.token_store import TickTickTokenStore
from the_assistant.models.ticktick import TickTask
from the_assistant.settings import get_settings

logger = logging.getLogger(__name__)


class TickTickClient:
    """Minimal client for the TickTick Open API."""

    BASE_URL = "https://api.ticktick.com/open/v1"

    def __init__(self, user_id: int, account: str | None = None) -> None:
        self.user_id = user_id
        self.account = account or "default"
        settings = get_settings()
        self._token_store = TickTickTokenStore(
            encryption_key=settings.db_encryption_key,
            account=self.account,
            user_service=get_user_service(),
        )
        self._fallback_token = settings.ticktick_access_token

    async def _get_token(self) -> str:
        token = await self._token_store.get(self.user_id)
        if token:
            return token
        if self._fallback_token:
            return self._fallback_token
        raise ValueError("TickTick access token not configured")

    async def _request(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}{path}", params=params, headers=headers
            )
            resp.raise_for_status()
            return resp.json()

    async def get_tasks_for_date(self, day: date) -> list[TickTask]:
        payload = await self._request(
            "/task",
            {"startDate": day.isoformat(), "endDate": day.isoformat()},
        )
        return [TickTask.from_ticktask(item) for item in payload]

    async def get_tasks_ahead(self, days: int = 7) -> list[TickTask]:
        start = date.today()
        end = start + timedelta(days=days - 1)
        payload = await self._request(
            "/task",
            {"startDate": start.isoformat(), "endDate": end.isoformat()},
        )
        return [TickTask.from_ticktask(item) for item in payload]
