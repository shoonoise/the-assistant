"""Activities package for The Assistant."""

# Import all activities for easy access
from .google_activities import (
    get_calendar_events,
    get_events_by_date,
    get_today_events,
    get_upcoming_events,
)
from .obsidian_activities import (
    scan_vault_notes,
)
from .telegram_activities import (
    send_formatted_message,
    send_message,
)

__all__ = [
    # Google activities
    "get_calendar_events",
    "get_events_by_date",
    "get_today_events",
    "get_upcoming_events",
    # Obsidian activities
    "scan_vault_notes",
    # Telegram activities
    "build_daily_briefing",
    "send_formatted_message",
    "send_message",
]
