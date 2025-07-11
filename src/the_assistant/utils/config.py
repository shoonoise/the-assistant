"""
Configuration utilities for The Assistant.

This module centralizes all environment variable access with proper type hints,
validation, and default values. It provides a single source of truth for all
configuration values used throughout the application.
"""

import logging
import os
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

# Type variable for generic config getter functions
T = TypeVar("T")


def get_env(
    key: str,
    default: str | None = None,
    required: bool = False,
) -> str | None:
    """Get an environment variable with validation.

    Args:
        key: The environment variable name
        default: Default value if not set
        required: Whether the variable is required

    Returns:
        The environment variable value or default

    Raises:
        ValueError: If the variable is required but not set
    """
    value = os.environ.get(key, default)
    if required and value is None:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


def get_env_bool(key: str, default: bool = False) -> bool:
    """Get a boolean environment variable.

    Args:
        key: The environment variable name
        default: Default value if not set

    Returns:
        The boolean value of the environment variable
    """
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "y", "t")


def get_env_int(
    key: str, default: int | None = None, required: bool = False
) -> int | None:
    """Get an integer environment variable.

    Args:
        key: The environment variable name
        default: Default value if not set
        required: Whether the variable is required

    Returns:
        The integer value of the environment variable or default

    Raises:
        ValueError: If the variable is required but not set or not a valid integer
    """
    value = os.environ.get(key)
    if value is None:
        if required:
            raise ValueError(f"Required environment variable {key} is not set")
        return default

    try:
        return int(value)
    except ValueError as err:
        if required:
            raise ValueError(
                f"Environment variable {key} is not a valid integer: {value}"
            ) from err
        return default


def get_env_list(
    key: str,
    separator: str = ",",
    default: list[str] | None = None,
) -> list[str]:
    """Get a list from a comma-separated environment variable.

    Args:
        key: The environment variable name
        separator: The separator character (default: comma)
        default: Default value if not set

    Returns:
        List of values from the environment variable
    """
    value = os.environ.get(key)
    if not value:
        return default or []
    return [item.strip() for item in value.split(separator) if item.strip()]


def get_env_path(
    key: str,
    default: str | Path | None = None,
    required: bool = False,
    must_exist: bool = False,
) -> Path | None:
    """Get a file path from an environment variable.

    Args:
        key: The environment variable name
        default: Default path if not set
        required: Whether the variable is required
        must_exist: Whether the path must exist

    Returns:
        Path object or None

    Raises:
        ValueError: If the variable is required but not set
        FileNotFoundError: If must_exist is True but the path doesn't exist
    """
    value = os.environ.get(key)

    if value is None:
        if required:
            raise ValueError(f"Required environment variable {key} is not set")
        if default is None:
            return None
        path = Path(default)
    else:
        path = Path(value)

    # Expand user directory (~/...)
    path = path.expanduser()

    if must_exist and not path.exists():
        raise FileNotFoundError(
            f"Path from environment variable {key} does not exist: {path}"
        )

    return path


# Telegram Configuration


def get_telegram_token() -> str:
    """Get the Telegram bot token from environment variables.

    Returns:
        str: The Telegram bot token.

    Raises:
        ValueError: If the token is not set in environment variables.
    """
    result = get_env("TELEGRAM_TOKEN", required=True)
    assert result is not None  # This will always be true because required=True
    return result


def get_telegram_test_token() -> str | None:
    """Get the Telegram test bot token from environment variables.

    Used for integration tests.

    Returns:
        str | None: The Telegram test bot token or None if not set.
    """
    return get_env("TELEGRAM_TEST_BOT_TOKEN")


def get_telegram_test_chat_id() -> int | None:
    """Get the Telegram test chat ID from environment variables.

    Used for integration tests.

    Returns:
        int | None: The Telegram test chat ID or None if not set.
    """
    chat_id = get_env("TELEGRAM_TEST_CHAT_ID")
    if chat_id is not None:
        try:
            return int(chat_id)
        except ValueError:
            logger.warning("Invalid Telegram test chat ID")
    return None


def get_telegram_allowed_user_ids() -> list[int]:
    """Get the list of allowed Telegram user IDs.

    Returns:
        list[int]: List of allowed user IDs, or empty list if none specified.
    """
    user_ids_str = get_env_list("TELEGRAM_ALLOWED_USER_IDS")
    valid_ids = []
    for user_id in user_ids_str:
        if user_id:
            try:
                valid_ids.append(int(user_id))
            except ValueError:
                logger.warning(f"Invalid Telegram user ID found: {user_id}")
    return valid_ids


# Google Configuration


def get_google_credentials_path() -> Path:
    """Get the path to the Google credentials file.

    Returns:
        Path: Path to the Google credentials file.

    Raises:
        ValueError: If the path is not set.
    """
    result = get_env_path(
        "GOOGLE_CREDENTIALS_PATH", default="secrets/google.json", must_exist=True
    )
    assert result is not None  # This will always be true with default value
    return result


def get_google_token_path() -> Path:
    """Get the path to the Google token file.

    Returns:
        Path: Path to the Google token file.
    """
    result = get_env_path("GOOGLE_TOKEN_PATH", default="secrets/token.json")
    assert result is not None  # This will always be true with default value
    return result


def get_google_calendar_id() -> str:
    """Get the Google Calendar ID.

    Returns:
        str: The calendar ID, defaults to 'primary'.
    """
    result = get_env("GOOGLE_CALENDAR_ID", default="primary")
    assert result is not None  # This will always be true with default value
    return result


# Obsidian Configuration


def get_obsidian_vault_path() -> Path:
    """Get the path to the Obsidian vault.

    Returns:
        Path: Path to the Obsidian vault.

    Raises:
        ValueError: If the path is not set.
        FileNotFoundError: If the path doesn't exist.
    """
    result = get_env_path("OBSIDIAN_VAULT_PATH", required=True, must_exist=True)
    assert result is not None  # This will always be true because required=True
    return result


# Temporal Configuration


def get_temporal_host() -> str:
    """Get the Temporal server host address.

    Returns:
        str: The Temporal server host address.
    """
    result = get_env("TEMPORAL_HOST", default="localhost:7233")
    assert result is not None  # This will always be true with default value
    return result


def get_temporal_task_queue() -> str:
    """Get the Temporal task queue name.

    Returns:
        str: The Temporal task queue name.
    """
    result = get_env("TEMPORAL_TASK_QUEUE", default="the-assistant")
    assert result is not None  # This will always be true with default value
    return result


def get_temporal_namespace() -> str:
    """Get the Temporal namespace.

    Returns:
        str: The Temporal namespace.
    """
    result = get_env("TEMPORAL_NAMESPACE", default="default")
    assert result is not None  # This will always be true with default value
    return result


# Trip Monitor Configuration


# Trip monitor functions removed - not used in any workflows


# Morning Briefing Configuration


def get_morning_briefing_enabled() -> bool:
    """Check if morning briefing is enabled.

    Returns:
        bool: True if morning briefing is enabled, False otherwise.
    """
    return get_env_bool("MORNING_BRIEFING_ENABLED", default=True)


def get_morning_briefing_schedule() -> str:
    """Get the morning briefing schedule cron expression.

    Returns:
        str: Cron expression for morning briefing schedule.
    """
    result = get_env("MORNING_BRIEFING_SCHEDULE", default="0 8 * * *")
    assert result is not None  # This will always be true with default value
    return result


def get_morning_briefing_chat_id() -> int | None:
    """Get the chat ID for morning briefing messages.

    Returns:
        int | None: The chat ID or None if not set.
    """
    chat_id = get_env("MORNING_BRIEFING_CHAT_ID")
    if chat_id is not None:
        try:
            return int(chat_id)
        except ValueError:
            logger.warning("Invalid morning briefing chat ID")
    return None


# Task Reminder Configuration


def get_task_reminder_enabled() -> bool:
    """Check if task reminders are enabled.

    Returns:
        bool: True if task reminders are enabled, False otherwise.
    """
    return get_env_bool("TASK_REMINDER_ENABLED", default=True)


def get_task_reminder_schedule() -> str:
    """Get the task reminder schedule cron expression.

    Returns:
        str: Cron expression for task reminder schedule.
    """
    result = get_env("TASK_REMINDER_SCHEDULE", default="0 20 * * *")
    assert result is not None  # This will always be true with default value
    return result


def get_task_reminder_chat_id() -> int | None:
    """Get the chat ID for task reminder messages.

    Returns:
        int | None: The chat ID or None if not set.
    """
    chat_id = get_env("TASK_REMINDER_CHAT_ID")
    if chat_id is not None:
        try:
            return int(chat_id)
        except ValueError:
            logger.warning("Invalid task reminder chat ID")
    return None


# Application Configuration


def get_log_level() -> int:
    """Get the logging level.

    Returns:
        int: The logging level as an integer.
    """
    level_name = get_env("LOG_LEVEL", default="INFO")
    if level_name is None:
        return logging.INFO
    return getattr(logging, level_name.upper(), logging.INFO)


def get_run_mode() -> str:
    """Get the application run mode.

    Returns:
        str: The run mode ('web', 'worker', or 'both').
    """
    result = get_env("RUN_MODE", default="both")
    assert result is not None  # This will always be true with default value
    return result


def get_user_registry_path() -> Path:
    """Get the path to the user registry file.

    Returns:
        Path: Path to the user registry file.
    """
    result = get_env_path("USER_REGISTRY_PATH", default="user_registry.json")
    assert result is not None  # This will always be true with default value
    return result


def get_webhook_enabled() -> bool:
    """Check if webhooks are enabled.

    Returns:
        bool: True if webhooks are enabled, False otherwise.
    """
    return get_env_bool("WEBHOOK_ENABLED", default=False)


def get_webhook_url() -> str | None:
    """Get the webhook URL.

    Returns:
        str | None: The webhook URL or None if not set.
    """
    return get_env("WEBHOOK_URL")


def get_webhook_port() -> int:
    """Get the webhook port.

    Returns:
        int: The webhook port.
    """
    result = get_env_int("WEBHOOK_PORT", default=8080)
    assert result is not None  # This will always be true with default value
    return result


# Helper function to get all configuration as a dictionary
def get_all_config() -> dict[str, Any]:
    """Get all configuration values as a dictionary.

    Returns:
        dict: Dictionary of all configuration values.
    """
    return {
        "telegram": {
            "token": "***REDACTED***" if get_env("TELEGRAM_TOKEN") else None,
            "allowed_user_ids": get_telegram_allowed_user_ids(),
            "test_token": "***REDACTED***" if get_telegram_test_token() else None,
            "test_chat_id": get_telegram_test_chat_id(),
        },
        "google": {
            "credentials_path": str(get_google_credentials_path()),
            "token_path": str(get_google_token_path()),
            "calendar_id": get_google_calendar_id(),
        },
        "obsidian": {
            "vault_path": str(get_obsidian_vault_path()),
        },
        "temporal": {
            "host": get_temporal_host(),
            "task_queue": get_temporal_task_queue(),
            "namespace": get_temporal_namespace(),
        },
        "morning_briefing": {
            "enabled": get_morning_briefing_enabled(),
            "schedule": get_morning_briefing_schedule(),
            "chat_id": get_morning_briefing_chat_id(),
        },
        "task_reminder": {
            "enabled": get_task_reminder_enabled(),
            "schedule": get_task_reminder_schedule(),
            "chat_id": get_task_reminder_chat_id(),
        },
        "app": {
            "log_level": logging.getLevelName(get_log_level()),
            "run_mode": get_run_mode(),
            "user_registry_path": str(get_user_registry_path()),
            "webhook_enabled": get_webhook_enabled(),
            "webhook_url": get_webhook_url(),
            "webhook_port": get_webhook_port(),
        },
    }
