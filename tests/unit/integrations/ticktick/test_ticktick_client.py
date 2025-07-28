from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from the_assistant.integrations.ticktick.ticktick_client import TickTickClient


class DummyList:
    def __init__(self, name: str):
        self.name = name


class DummyTask:
    def __init__(self, id: str, title: str, due: datetime | None, status: int = 0):
        self.id = id
        self.title = title
        self.dueDate = due
        self.startDate = None
        self.status = status
        self.list = DummyList("Inbox")
        self.tags = []

    @property
    def is_completed(self) -> bool:
        return self.status > 0


class DummyTickTick:
    def __init__(self, *args, **kwargs):
        self.tasks = []

    def fetch(self):
        pass


@pytest.fixture
def mock_settings(monkeypatch):
    settings = SimpleNamespace(
        ticktick_username="user",
        ticktick_password="pass",
    )
    monkeypatch.setattr(
        "the_assistant.integrations.ticktick.ticktick_client.get_settings",
        lambda: settings,
    )
    return settings


@pytest.mark.asyncio
async def test_missing_credentials(monkeypatch):
    monkeypatch.setattr(
        "the_assistant.integrations.ticktick.ticktick_client.get_settings",
        lambda: SimpleNamespace(ticktick_username=None, ticktick_password=None),
    )
    with pytest.raises(ValueError):
        TickTickClient()


@pytest.mark.asyncio
async def test_get_tasks_for_date(monkeypatch, mock_settings):
    dummy = DummyTickTick()
    today = date.today()
    tomorrow = today + timedelta(days=1)
    dummy.tasks = [
        DummyTask("1", "A", datetime.combine(today, datetime.min.time()), 0),
        DummyTask("2", "B", datetime.combine(tomorrow, datetime.min.time()), 0),
    ]
    monkeypatch.setattr(
        "the_assistant.integrations.ticktick.ticktick_client.TickTick",
        lambda u, p: dummy,
    )

    client = TickTickClient()
    tasks = await client.get_tasks_for_date(today)
    assert len(tasks) == 1
    assert tasks[0].title == "A"


@pytest.mark.asyncio
async def test_get_tasks_ahead(monkeypatch, mock_settings):
    dummy = DummyTickTick()
    start = date.today()
    dummy.tasks = [
        DummyTask(
            "1",
            "A",
            datetime.combine(start + timedelta(days=i), datetime.min.time()),
            0,
        )
        for i in range(3)
    ]
    monkeypatch.setattr(
        "the_assistant.integrations.ticktick.ticktick_client.TickTick",
        lambda u, p: dummy,
    )
    client = TickTickClient()
    tasks = await client.get_tasks_ahead(2)
    assert len(tasks) == 2
