from langchain_core.tools import BaseTool, tool

from .google.client import GoogleClient
from .telegram.telegram_client import TelegramClient


async def _send_message(user_id: int, text: str) -> str:
    client = TelegramClient(user_id=user_id)
    await client.send_message(text=text)
    return "Message sent"


async def _get_event(
    user_id: int,
    event_id: str,
    calendar_id: str = "primary",
    account: str | None = None,
) -> dict:
    client = GoogleClient(user_id=user_id, account=account)
    event = await client.get_event(event_id=event_id, calendar_id=calendar_id)
    return event.model_dump()


async def _get_email(user_id: int, email_id: str, account: str | None = None) -> dict:
    client = GoogleClient(user_id=user_id, account=account)
    email = await client.get_email(email_id)
    return email.model_dump()


def get_default_tools(user_id: int) -> list[BaseTool]:
    """Return default agent tools bound to the given user."""

    @tool
    async def send_message(text: str) -> str:
        """Send a Telegram message to the current user."""
        return await _send_message(user_id, text)

    @tool
    async def get_event(
        event_id: str, calendar_id: str = "primary", account: str | None = None
    ) -> dict:
        """Get a Google Calendar event by ID."""
        return await _get_event(user_id, event_id, calendar_id, account)

    @tool
    async def get_email(email_id: str, account: str | None = None) -> dict:
        """Get a full Gmail message by ID."""
        return await _get_email(user_id, email_id, account)

    return [send_message, get_event, get_email]
