from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from ticktick import TickTick

from the_assistant.models.ticktick import TickTask
from the_assistant.settings import get_settings

logger = logging.getLogger(__name__)


class TickTickClient:
    """Simple asynchronous wrapper around the ``ticktick`` library."""

    def __init__(self):
        settings = get_settings()
        if not settings.ticktick_username or not settings.ticktick_password:
            raise ValueError("TickTick credentials are not configured")
        self.username = settings.ticktick_username
        self.password = settings.ticktick_password
        self._client: TickTick | None = None

    def _create_client(self) -> None:
        logger.info("Logging in to TickTick as %s", self.username)
        self._client = TickTick(self.username, self.password)

    async def ensure_client(self) -> TickTick:
        if self._client is None:
            await asyncio.to_thread(self._create_client)
        return self._client  # type: ignore[return-value]

    async def _fetch_tasks(self) -> list[TickTask]:
        client = await self.ensure_client()
        await asyncio.to_thread(client.fetch)
        return [TickTask.from_ticktask(t) for t in getattr(client, "tasks", [])]

    async def get_tasks_for_date(self, day: date) -> list[TickTask]:
        tasks = await self._fetch_tasks()
        return [
            t
            for t in tasks
            if (t.due_date or t.start_date)
            and (t.due_date or t.start_date).date() == day
            and not t.completed
        ]

    async def get_tasks_ahead(self, days: int = 7) -> list[TickTask]:
        start = date.today()
        end = start + timedelta(days=days - 1)
        tasks = await self._fetch_tasks()
        result = []
        for t in tasks:
            d = t.due_date or t.start_date
            if d and start <= d.date() <= end and not t.completed:
                result.append(t)
        return result
