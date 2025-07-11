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
    raw_data: dict[str, Any] = Field(
        default_factory=dict, description="Original API response data"
    )

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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalendarEvent":
        """Create CalendarEvent from raw dictionary data."""
        return cls.model_validate(data)

    @classmethod
    def from_dict_list(cls, data_list: list[dict[str, Any]]) -> list["CalendarEvent"]:
        """Create list of CalendarEvent from raw dictionary list."""
        return [cls.from_dict(item) for item in data_list]
