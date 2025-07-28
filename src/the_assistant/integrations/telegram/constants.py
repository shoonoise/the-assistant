from enum import Enum, IntEnum


class ConversationState(IntEnum):
    """States for the update settings conversation."""

    SELECT_SETTING = 0
    ENTER_VALUE = 1
    SELECT_MEMORY_TO_DELETE = 2

    # New states for dialog mode commands
    MEMORY_INPUT = 3
    TASK_INPUT = 4
    COUNTDOWN_INPUT = 5
    EMAIL_PATTERN_INPUT = 6


class SettingKey(str, Enum):
    """Names of supported user settings."""

    GREET = "greet"
    BRIEFING_TIME = "briefing_time"
    ABOUT_ME = "about_me"
    LOCATION = "location"
    IGNORE_EMAILS = "ignore_emails"
    MEMORIES = "memories"


SETTINGS_LABEL_MAP: dict[str, SettingKey] = {
    "How to greet": SettingKey.GREET,
    "Briefing time": SettingKey.BRIEFING_TIME,
    "About me": SettingKey.ABOUT_ME,
    "Location": SettingKey.LOCATION,
    "Ignored email senders": SettingKey.IGNORE_EMAILS,
}

# Reverse lookup map for displaying setting labels
SETTINGS_LABEL_LOOKUP: dict[SettingKey, str] = {
    v: k for k, v in SETTINGS_LABEL_MAP.items()
}


# Keyboard button to command mapping dictionary
KEYBOARD_COMMAND_MAP: dict[str, str] = {
    "📊 Briefing": "briefing",
    "📅 Schedule Task": "add_task",
    "⏰ Add Countdown": "add_countdown",
    "📈 Track Habit": "track_habit",
    "🧠 Memories": "memory",
    "⚙️ Settings": "update_settings",
}
