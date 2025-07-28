"""Activities package for The Assistant."""

# Import all activities for easy access
from .google_activities import (
    get_calendar_events,
    get_emails,
    get_events_by_date,
    get_today_events,
    get_upcoming_events,
)
from .messages_activities import (
    build_briefing_prompt,
    build_briefing_summary,
    build_daily_briefing,
    get_user_settings,
)
from .obsidian_activities import (
    scan_vault_notes,
)
from .telegram_activities import (
    send_formatted_message,
    send_message,
)
from .ticktick_activities import (
    get_tasks_for_date,
    get_tasks_next_days,
)
from .user_activities import (
    get_user_accounts,
)
from .weather_activities import get_weather_forecast

__all__ = [
    # Google activities
    "get_calendar_events",
    "get_events_by_date",
    "get_today_events",
    "get_upcoming_events",
    "get_emails",
    # Obsidian activities
    "scan_vault_notes",
    # User activities
    "get_user_accounts",
    # Weather activities
    "get_weather_forecast",
    "get_tasks_for_date",
    "get_tasks_next_days",
    # Telegram activities
    "build_daily_briefing",
    "build_briefing_summary",
    "build_briefing_prompt",
    "get_user_settings",
    "send_formatted_message",
    "send_message",
]
