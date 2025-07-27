from datetime import UTC, datetime

import pytest

from the_assistant.integrations.agent_tools import get_default_tools
from the_assistant.models.google import CalendarEvent, GmailMessage


@pytest.mark.asyncio
async def test_send_message_tool(monkeypatch):
    called = False

    class DummyClient:
        def __init__(self, user_id=None):
            self.user_id = user_id

        async def send_message(self, text: str, parse_mode: str = "Markdown"):
            nonlocal called
            called = True
            assert text == "hi"

    async def mock_get_mcp_tools():
        return []

    monkeypatch.setattr(
        "the_assistant.integrations.agent_tools.TelegramClient",
        DummyClient,
    )
    monkeypatch.setattr(
        "the_assistant.integrations.agent_tools.get_mcp_tools",
        mock_get_mcp_tools,
    )

    tools = await get_default_tools(1)
    send_tool = next(t for t in tools if t.name == "send_message")
    await send_tool.arun("hi")
    assert called


@pytest.mark.asyncio
async def test_get_event_tool(monkeypatch):
    dt = datetime.now(UTC)
    event = CalendarEvent(
        id="e1",
        summary="s",
        description="",
        start_time=dt,
        end_time=dt,
        location="",
    )

    class DummyClient:
        def __init__(self, user_id=None, account=None):
            pass

        async def get_event(self, event_id: str, calendar_id: str = "primary"):
            assert event_id == "e1"
            return event

    async def mock_get_mcp_tools():
        return []

    monkeypatch.setattr(
        "the_assistant.integrations.agent_tools.GoogleClient",
        DummyClient,
    )
    monkeypatch.setattr(
        "the_assistant.integrations.agent_tools.get_mcp_tools",
        mock_get_mcp_tools,
    )

    tools = await get_default_tools(1)
    tool_obj = next(t for t in tools if t.name == "get_event")
    result = await tool_obj.arun("e1")
    assert result["id"] == "e1"


@pytest.mark.asyncio
async def test_get_email_tool(monkeypatch):
    email = GmailMessage(
        id="m1",
        thread_id="t",
        snippet="",
        subject="",
        sender="",
        to="",
        date=None,
        body="",
    )

    class DummyClient:
        def __init__(self, user_id=None, account=None):
            pass

        async def get_email(self, email_id: str):
            assert email_id == "m1"
            return email

    async def mock_get_mcp_tools():
        return []

    monkeypatch.setattr(
        "the_assistant.integrations.agent_tools.GoogleClient",
        DummyClient,
    )
    monkeypatch.setattr(
        "the_assistant.integrations.agent_tools.get_mcp_tools",
        mock_get_mcp_tools,
    )

    tools = await get_default_tools(1)
    tool_obj = next(t for t in tools if t.name == "get_email")
    result = await tool_obj.arun("m1")
    assert result["id"] == "m1"
