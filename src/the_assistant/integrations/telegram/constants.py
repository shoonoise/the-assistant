from enum import Enum, IntEnum


class ConversationState(IntEnum):
    """States for the update settings conversation."""

    SELECT_SETTING = 0
    ENTER_VALUE = 1


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
