from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from the_assistant.integrations.ticktick.ticktick_client import TickTickClient


class DummyStore:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def get(self, user_id: int) -> str | None:  # noqa: D401 - simple return
        return "token"


@pytest.fixture
def mock_settings(monkeypatch):
    settings = SimpleNamespace(db_encryption_key="key", ticktick_access_token=None)
    monkeypatch.setattr(
        "the_assistant.integrations.ticktick.ticktick_client.get_settings",
        lambda: settings,
    )
    return settings


@pytest.mark.asyncio
async def test_get_tasks_for_date(monkeypatch, mock_settings):
    async def fake_request(self, path, params):  # noqa: D401 - simple return
        return [
            {
                "id": "1",
                "title": "A",
                "dueDate": params["startDate"] + "T00:00:00Z",
                "status": 0,
                "list": {"name": "Inbox"},
                "tags": [],
            }
        ]

    monkeypatch.setattr(
        "the_assistant.integrations.ticktick.ticktick_client.TickTickTokenStore",
        DummyStore,
    )
    monkeypatch.setattr(
        "the_assistant.integrations.ticktick.ticktick_client.get_user_service",
        lambda: None,
    )
    monkeypatch.setattr(
        "the_assistant.integrations.ticktick.ticktick_client.TickTickClient._request",
        fake_request,
    )

    client = TickTickClient(user_id=1)
    tasks = await client.get_tasks_for_date(date.today())
    assert len(tasks) == 1
    assert tasks[0].title == "A"


@pytest.mark.asyncio
async def test_get_tasks_ahead(monkeypatch, mock_settings):
    async def fake_request(self, path, params):  # noqa: D401 - simple return
        start = date.fromisoformat(params["startDate"])
        end = date.fromisoformat(params["endDate"])
        payload = []
        current = start
        while current <= end:
            payload.append(
                {
                    "id": current.isoformat(),
                    "title": current.isoformat(),
                    "dueDate": current.isoformat() + "T00:00:00Z",
                    "status": 0,
                }
            )
            current += timedelta(days=1)
        return payload

    monkeypatch.setattr(
        "the_assistant.integrations.ticktick.ticktick_client.TickTickTokenStore",
        DummyStore,
    )
    monkeypatch.setattr(
        "the_assistant.integrations.ticktick.ticktick_client.get_user_service",
        lambda: None,
    )
    monkeypatch.setattr(
        "the_assistant.integrations.ticktick.ticktick_client.TickTickClient._request",
        fake_request,
    )

    client = TickTickClient(user_id=1)
    tasks = await client.get_tasks_ahead(2)
    assert len(tasks) == 2
