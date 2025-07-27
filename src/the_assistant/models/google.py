"""
Google-related data models using Pydantic v2.

This module contains data structures for Google Calendar integration,
specifically for activity return types.
"""

from datetime import datetime, timedelta
from typing import Any

from pydantic import Field, computed_field

from .base import BaseAssistantModel


class CalendarEvent(BaseAssistantModel):
    """Represents a calendar event returned from Google Calendar activities."""

    id: str = Field(description="Event ID")
    summary: str = Field(description="Event title/summary")
    description: str = Field(default="", description="Event description")
    start_time: datetime = Field(description="Event start time")
    end_time: datetime = Field(description="Event end time")
    location: str = Field(default="", description="Event location")
    calendar_id: str = Field(
        default="primary", description="Calendar ID containing this event"
    )
    is_all_day: bool = Field(
        default=False, description="Whether this is an all-day event"
    )
    attendees: list[dict[str, Any]] = Field(
        default_factory=list, description="Event attendees (raw data)"
    )
    created_time: datetime | None = Field(
        default=None, description="Event creation time"
    )
    updated_time: datetime | None = Field(default=None, description="Last update time")
    is_recurring: bool = Field(
        default=False, description="Whether this event is part of a recurring series"
    )
    recurrence_rules: list[str] = Field(
        default_factory=list, description="RRULE strings defining recurrence pattern"
    )
    recurring_event_id: str | None = Field(
        default=None, description="ID of the recurring event series (if applicable)"
    )
    raw_data: dict[str, Any] | None = Field(
        default=None, description="Original API response data"
    )
    account: str | None = Field(default=None, description="Google account identifier")

    @computed_field
    @property
    def duration(self) -> timedelta:
        """Calculate the duration of the event."""
        return self.end_time - self.start_time

    @computed_field
    @property
    def is_upcoming(self) -> bool:
        """Check if the event is in the future."""
        return self.start_time > datetime.now(self.start_time.tzinfo)

    @computed_field
    @property
    def is_today(self) -> bool:
        """Check if the event is today."""
        today = datetime.now(self.start_time.tzinfo).date()
        return self.start_time.date() == today

    @computed_field
    @property
    def recurrence_description(self) -> str:
        """Get a human-readable description of the recurrence pattern."""
        if not self.is_recurring or not self.recurrence_rules:
            return ""

        # Parse the first RRULE for basic description
        rrule = self.recurrence_rules[0]
        if not rrule.startswith("RRULE:"):
            return rrule

        # Extract frequency and interval from RRULE
        parts = rrule[6:].split(";")  # Remove "RRULE:" prefix
        freq_map = {
            "DAILY": "daily",
            "WEEKLY": "weekly",
            "MONTHLY": "monthly",
            "YEARLY": "yearly",
        }

        freq = None
        interval = 1

        for part in parts:
            if part.startswith("FREQ="):
                freq = freq_map.get(part[5:], part[5:].lower())
            elif part.startswith("INTERVAL="):
                interval = int(part[9:])

        if not freq:
            return "recurring"

        if interval == 1:
            return freq
        else:
            return f"every {interval} {freq.rstrip('ly')}{'ly' if freq.endswith('ly') else 's'}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalendarEvent":
        """Create CalendarEvent from raw dictionary data."""
        return cls.model_validate(data)

    @classmethod
    def from_dict_list(cls, data_list: list[dict[str, Any]]) -> list["CalendarEvent"]:
        """Create list of CalendarEvent from raw dictionary list."""
        return [cls.from_dict(item) for item in data_list]


class GmailMessage(BaseAssistantModel):
    """Represents a message returned from Gmail."""

    id: str = Field(description="Message ID")
    thread_id: str = Field(description="Thread ID")
    snippet: str = Field(description="Message snippet")
    subject: str = Field(default="", description="Email subject")
    sender: str = Field(default="", description="Sender email")
    to: str = Field(default="", description="Recipient email")
    date: datetime | None = Field(default=None, description="Message date")
    body: str = Field(default="", description="Plain text body")
    unread: bool = Field(default=False, description="Whether the message is unread")
    raw_data: dict[str, Any] | None = Field(
        default=None, description="Original API response data"
    )
    account: str | None = Field(default=None, description="Google account identifier")

    @computed_field
    @property
    def participants(self) -> list[str]:
        """Return all message participants from sender, to, and cc fields."""
        parts: list[str] = []
        if self.sender:
            parts.extend([p.strip() for p in self.sender.split(",") if p.strip()])
        if self.to:
            parts.extend([p.strip() for p in self.to.split(",") if p.strip()])
        if self.raw_data:
            headers = {
                h["name"].lower(): h["value"]
                for h in self.raw_data.get("payload", {}).get("headers", [])
            }
            cc = headers.get("cc")
            if cc:
                parts.extend([p.strip() for p in cc.split(",") if p.strip()])
        return list(dict.fromkeys(parts))

    @computed_field
    @property
    def is_unread(self) -> bool:
        """Return the unread status."""
        return self.unread

    @computed_field
    @property
    def formatted_date(self) -> str | None:
        """Return the message date formatted without seconds or timezone."""
        if not self.date:
            return None
        return f"{self.date.day} {self.date.strftime('%B %Y %H:%M')}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GmailMessage":
        """Create GmailMessage from raw dictionary data."""
        return cls.model_validate(data)

    @classmethod
    def from_dict_list(cls, data_list: list[dict[str, Any]]) -> list["GmailMessage"]:
        """Create list of GmailMessage from raw dictionary list."""
        return [cls.from_dict(item) for item in data_list]
