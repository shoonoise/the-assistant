from enum import Enum, IntEnum


class ConversationState(IntEnum):
    """States for the update settings conversation."""

    SELECT_SETTING = 0
    ENTER_VALUE = 1
    SELECT_MEMORY_TO_DELETE = 2


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

SETTINGS_DESCRIPTIONS: dict[SettingKey, str] = {
    SettingKey.GREET: "How the bot should address you (first_name, username, or custom)",
    SettingKey.BRIEFING_TIME: "Preferred time for daily briefings (e.g., 08:00)",
    SettingKey.ABOUT_ME: "Personal information to help customize responses",
    SettingKey.LOCATION: "Your location for weather and local information",
    SettingKey.IGNORE_EMAILS: "Email patterns to ignore in notifications",
}
