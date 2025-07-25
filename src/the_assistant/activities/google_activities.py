"""
Google Calendar activities for Temporal workflows.

This module provides Temporal activities for interacting with Google Calendar API.
Activities are atomic, idempotent operations that can be retried by Temporal.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from temporalio import activity

from the_assistant.integrations.google.client import GoogleClient
from the_assistant.models.google import CalendarEvent, GmailMessage
from the_assistant.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class GetCalendarEventsInput:
    user_id: int
    account: str | None = None
    calendar_id: str = "primary"
    time_min: datetime | None = None
    time_max: datetime | None = None
    max_results: int = 10


@dataclass
class GetUpcomingEventsInput:
    user_id: int
    account: str | None = None
    days_ahead: int = 30
    calendar_id: str = "primary"


@dataclass
class GetEventsByDateInput:
    user_id: int
    target_date: datetime
    account: str | None = None
    calendar_id: str | None = None


@dataclass
class GetTodayEventsInput:
    user_id: int
    account: str | None = None
    calendar_id: str = "primary"


@dataclass
class GetEmailsInput:
    user_id: int
    account: str | None = None
    unread_only: bool = True
    sender: str | None = None
    max_results: int = 5
    ignored_senders: list[str] | None = None


@dataclass
class GetImportantEmailsInput:
    user_id: int
    account: str | None = None
    max_full: int = 10
    max_snippets: int = 10
    ignored_senders: list[str] | None = None


@dataclass
class ImportantEmailsResult:
    emails_full: list[GmailMessage]
    emails_snippets: list[GmailMessage]
    total: int


@dataclass
class GetUpcomingEventsAccountsInput:
    """Input for fetching upcoming events from multiple accounts."""

    user_id: int
    accounts: list[str]
    days_ahead: int = 30
    calendar_id: str = "primary"


@dataclass
class GetImportantEmailsAccountsInput:
    """Input for fetching important emails from multiple accounts."""

    user_id: int
    accounts: list[str]
    max_full: int = 10
    max_snippets: int = 10
    ignored_senders: list[str] | None = None


def get_google_client(user_id: int, account: str | None = None) -> GoogleClient:
    """Get a configured Google client for the user."""

    logger.info(f"Creating Google client for user {user_id} account {account}")

    return GoogleClient(user_id=user_id, account=account)


@activity.defn
async def get_calendar_events(input: GetCalendarEventsInput) -> list[CalendarEvent]:
    """
    Activity to retrieve calendar events from Google Calendar.

    Args:
        input: Input parameters containing user_id, calendar_id, time constraints, and max_results

    Returns:
        List of calendar events

    Raises:
        Exception: If authentication or calendar operation fails
    """
    logger.info(
        f"Fetching calendar events from {input.calendar_id} for user {input.user_id}"
    )

    client = get_google_client(input.user_id, input.account)

    # Check if user is authenticated
    if not await client.is_authenticated():
        raise ValueError(f"User {input.user_id} is not authenticated with Google")

    # Let Temporal handle retries if this fails
    events = await client.get_calendar_events(
        calendar_id=input.calendar_id,
        time_min=input.time_min,
        time_max=input.time_max,
        max_results=input.max_results,
    )

    logger.info(f"Retrieved {len(events)} events from calendar {input.calendar_id}")
    return events


@activity.defn
async def get_upcoming_events(input: GetUpcomingEventsInput) -> list[CalendarEvent]:
    """
    Activity to get upcoming events within the specified number of days.

    Args:
        input: Input parameters containing user_id, days_ahead, and calendar_id

    Returns:
        List of upcoming calendar events

    Raises:
        Exception: If authentication or calendar operation fails
    """
    logger.info(
        f"Fetching upcoming events for next {input.days_ahead} days for user {input.user_id}"
    )

    client = get_google_client(input.user_id, input.account)

    # Check if user is authenticated
    if not await client.is_authenticated():
        raise ValueError(f"User {input.user_id} is not authenticated with Google")

    # Let Temporal handle retries if this fails
    events = await client.get_upcoming_events(
        days_ahead=input.days_ahead,
        calendar_id=input.calendar_id,
    )

    logger.info(f"Retrieved {len(events)} upcoming events")
    return events


@activity.defn
async def get_events_by_date(input: GetEventsByDateInput) -> list[CalendarEvent]:
    """
    Activity to retrieve events for a specific date.

    Args:
        input: Input parameters containing user_id, target_date, and optional calendar_id

    Returns:
        List of calendar events for the specified date

    Raises:
        Exception: If authentication or calendar operation fails
    """
    settings = get_settings()
    calendar_id = input.calendar_id
    if calendar_id is None:
        calendar_id = settings.google_calendar_id

    logger.info(
        f"Fetching events for date {input.target_date.date()} from calendar {calendar_id} for user {input.user_id}"
    )

    client = get_google_client(input.user_id, input.account)

    # Check if user is authenticated
    if not await client.is_authenticated():
        raise ValueError(f"User {input.user_id} is not authenticated with Google")

    # Let Temporal handle retries if this fails
    events = await client.get_events_by_date(
        target_date=input.target_date,
        calendar_id=calendar_id,
    )

    logger.info(f"Retrieved {len(events)} events for {input.target_date.date()}")
    return events


@activity.defn
async def get_today_events(input: GetTodayEventsInput) -> list[CalendarEvent]:
    """
    Activity to get today's calendar events.

    Args:
        input: Input parameters containing user_id and calendar_id

    Returns:
        List of today's calendar events

    Raises:
        Exception: If authentication or calendar operation fails
    """
    today = datetime.now(UTC)
    return await get_events_by_date(
        GetEventsByDateInput(
            user_id=input.user_id,
            target_date=today,
            calendar_id=input.calendar_id,
            account=input.account,
        )
    )


@activity.defn
async def get_emails(input: GetEmailsInput) -> list[GmailMessage]:
    """Retrieve Gmail messages."""
    logger.info(f"Fetching emails for user {input.user_id}")

    client = get_google_client(input.user_id, input.account)

    if not await client.is_authenticated():
        raise ValueError(f"User {input.user_id} is not authenticated with Google")

    emails = await client.get_emails(
        unread_only=input.unread_only,
        sender=input.sender,
        max_results=input.max_results,
        ignored_senders=input.ignored_senders,
    )

    logger.info(f"Retrieved {len(emails)} emails")
    return emails


@activity.defn
async def get_important_emails(
    input: GetImportantEmailsInput,
) -> ImportantEmailsResult:
    """Retrieve important Gmail messages with total inbox count."""
    logger.info(f"Fetching important emails for user {input.user_id}")

    client = get_google_client(input.user_id, input.account)

    if not await client.is_authenticated():
        raise ValueError(f"User {input.user_id} is not authenticated with Google")

    emails, total = await client.get_important_emails(
        max_results=input.max_full + input.max_snippets,
        include_body=True,
        ignored_senders=input.ignored_senders,
    )

    emails_full = emails[: input.max_full]
    emails_snippets = emails[input.max_full : input.max_full + input.max_snippets]

    logger.info("Retrieved %s important emails (total %s)", len(emails), total)
    return ImportantEmailsResult(
        emails_full=emails_full,
        emails_snippets=emails_snippets,
        total=total,
    )


@activity.defn
async def get_upcoming_events_accounts(
    input: GetUpcomingEventsAccountsInput,
) -> list[CalendarEvent]:
    """Fetch upcoming events for multiple accounts."""

    tasks = [
        get_upcoming_events(
            GetUpcomingEventsInput(
                user_id=input.user_id,
                days_ahead=input.days_ahead,
                calendar_id=input.calendar_id,
                account=account,
            )
        )
        for account in input.accounts
    ]
    events = await asyncio.gather(*tasks)
    return [event for sublist in events for event in sublist]

    return events


@activity.defn
async def get_important_emails_accounts(
    input: GetImportantEmailsAccountsInput,
) -> ImportantEmailsResult:
    """Fetch important emails aggregated from multiple accounts."""

    emails_full: list[GmailMessage] = []
    emails_snippets: list[GmailMessage] = []
    total = 0

    tasks = [
        get_important_emails(
            GetImportantEmailsInput(
                user_id=input.user_id,
                max_full=input.max_full,
                max_snippets=input.max_snippets,
                account=account,
                ignored_senders=input.ignored_senders,
            )
        )
        for account in input.accounts
    ]
    results = await asyncio.gather(*tasks)

    emails_full = []
    emails_snippets = []
    total = 0
    for result in results:
        emails_full.extend(result.emails_full)
        emails_snippets.extend(result.emails_snippets)
        total += result.total

    return ImportantEmailsResult(
        emails_full=emails_full,
        emails_snippets=emails_snippets,
        total=total,
    )
