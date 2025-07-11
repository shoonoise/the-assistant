"""Unit tests for the configuration module.

These tests verify the functionality of the centralized configuration utilities.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from the_assistant.utils.config import (
    get_env,
    get_env_bool,
    get_env_int,
    get_env_list,
    get_env_path,
    get_google_calendar_id,
    get_google_credentials_path,
    get_google_token_path,
    get_log_level,
    get_morning_briefing_chat_id,
    get_obsidian_vault_path,
    get_telegram_allowed_user_ids,
    get_telegram_token,
    get_temporal_host,
)


@pytest.fixture
def mock_env():
    """Set up mock environment variables for testing."""
    with patch.dict(
        os.environ,
        {
            "TEST_VAR": "test_value",
            "TEST_BOOL_TRUE": "true",
            "TEST_BOOL_FALSE": "false",
            "TEST_INT": "42",
            "TEST_LIST": "item1,item2,item3",
            "TEST_PATH": "/path/to/file",
            "TELEGRAM_TOKEN": "test_telegram_token",
            "TELEGRAM_ALLOWED_USER_IDS": "123456,789012",
            "GOOGLE_CREDENTIALS_PATH": "test/google.json",
            "GOOGLE_TOKEN_PATH": "test/token.json",
            "GOOGLE_CALENDAR_ID": "test_calendar",
            "OBSIDIAN_VAULT_PATH": "test/vault",
            "TEMPORAL_HOST": "test:7233",
            "LOG_LEVEL": "DEBUG",
            "MORNING_BRIEFING_CHAT_ID": "123456",
        },
        clear=True,
    ):
        yield


def test_get_env(mock_env):
    """Test get_env function."""
    # Test existing variable
    assert get_env("TEST_VAR") == "test_value"

    # Test non-existent variable with default
    assert get_env("NON_EXISTENT", default="default_value") == "default_value"

    # Test non-existent variable without default
    assert get_env("NON_EXISTENT") is None

    # Test required variable that exists
    assert get_env("TEST_VAR", required=True) == "test_value"

    # Test required variable that doesn't exist
    with pytest.raises(ValueError):
        get_env("NON_EXISTENT", required=True)


def test_get_env_bool(mock_env):
    """Test get_env_bool function."""
    # Test true values
    assert get_env_bool("TEST_BOOL_TRUE") is True

    # Test false values
    assert get_env_bool("TEST_BOOL_FALSE") is False

    # Test non-existent variable
    assert get_env_bool("NON_EXISTENT") is False

    # Test non-existent variable with default
    assert get_env_bool("NON_EXISTENT", default=True) is True

    # Test with other truthy values
    with patch.dict(
        os.environ,
        {
            "TEST_BOOL_YES": "yes",
            "TEST_BOOL_Y": "y",
            "TEST_BOOL_1": "1",
            "TEST_BOOL_T": "t",
        },
    ):
        assert get_env_bool("TEST_BOOL_YES") is True
        assert get_env_bool("TEST_BOOL_Y") is True
        assert get_env_bool("TEST_BOOL_1") is True
        assert get_env_bool("TEST_BOOL_T") is True


def test_get_env_int(mock_env):
    """Test get_env_int function."""
    # Test valid integer
    assert get_env_int("TEST_INT") == 42

    # Test non-existent variable with default
    assert get_env_int("NON_EXISTENT", default=10) == 10

    # Test non-existent variable without default
    assert get_env_int("NON_EXISTENT") is None

    # Test required variable that exists
    assert get_env_int("TEST_INT", required=True) == 42

    # Test required variable that doesn't exist
    with pytest.raises(ValueError):
        get_env_int("NON_EXISTENT", required=True)

    # Test invalid integer
    with patch.dict(os.environ, {"INVALID_INT": "not_an_int"}):
        # Non-required should return default
        assert get_env_int("INVALID_INT", default=10) == 10

        # Required should raise error
        with pytest.raises(ValueError):
            get_env_int("INVALID_INT", required=True)


def test_get_env_list(mock_env):
    """Test get_env_list function."""
    # Test comma-separated list
    assert get_env_list("TEST_LIST") == ["item1", "item2", "item3"]

    # Test non-existent variable
    assert get_env_list("NON_EXISTENT") == []

    # Test non-existent variable with default
    assert get_env_list("NON_EXISTENT", default=["default"]) == ["default"]

    # Test with custom separator
    with patch.dict(os.environ, {"TEST_LIST_SEMICOLON": "item1;item2;item3"}):
        assert get_env_list("TEST_LIST_SEMICOLON", separator=";") == [
            "item1",
            "item2",
            "item3",
        ]

    # Test with empty string
    with patch.dict(os.environ, {"TEST_LIST_EMPTY": ""}):
        assert get_env_list("TEST_LIST_EMPTY") == []


def test_get_env_path(mock_env):
    """Test get_env_path function."""
    # Test valid path
    path = get_env_path("TEST_PATH")
    assert isinstance(path, Path)
    assert str(path) == "/path/to/file"

    # Test non-existent variable with default
    path = get_env_path("NON_EXISTENT", default="/default/path")
    assert str(path) == "/default/path"

    # Test non-existent variable without default
    assert get_env_path("NON_EXISTENT") is None

    # Test required variable that exists
    path = get_env_path("TEST_PATH", required=True)
    assert str(path) == "/path/to/file"

    # Test required variable that doesn't exist
    with pytest.raises(ValueError):
        get_env_path("NON_EXISTENT", required=True)

    # Test must_exist (mocking Path.exists)
    with patch.object(Path, "exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            get_env_path("TEST_PATH", must_exist=True)

    # Test with Path expansion
    with patch.dict(os.environ, {"TEST_PATH_TILDE": "~/file"}):
        with patch.object(Path, "expanduser", return_value=Path("/home/user/file")):
            path = get_env_path("TEST_PATH_TILDE")
            assert str(path) == "/home/user/file"


def test_telegram_config(mock_env):
    """Test Telegram configuration functions."""
    assert get_telegram_token() == "test_telegram_token"
    assert get_telegram_allowed_user_ids() == [123456, 789012]

    # Test with invalid user IDs
    with patch.dict(os.environ, {"TELEGRAM_ALLOWED_USER_IDS": "123456,not_an_id"}):
        # Should skip invalid IDs
        assert get_telegram_allowed_user_ids() == [123456]


def test_google_config(mock_env):
    """Test Google configuration functions."""
    # Mock Path.exists to return True for the test paths
    with patch.object(Path, "exists", return_value=True):
        assert str(get_google_credentials_path()) == "test/google.json"
        assert str(get_google_token_path()) == "test/token.json"
        assert get_google_calendar_id() == "test_calendar"

        # Test with missing credentials path
        with patch.dict(os.environ, {}, clear=True):
            # Should use default
            assert str(get_google_token_path()) == "secrets/token.json"
            assert get_google_calendar_id() == "primary"


def test_obsidian_config(mock_env):
    """Test Obsidian configuration functions."""
    with patch.object(Path, "exists", return_value=True):
        assert str(get_obsidian_vault_path()) == "test/vault"

    # Test with missing vault path
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError):
            get_obsidian_vault_path()


def test_temporal_config(mock_env):
    """Test Temporal configuration functions."""
    assert get_temporal_host() == "test:7233"

    # Test with missing host
    with patch.dict(os.environ, {}, clear=True):
        # Should use default
        assert get_temporal_host() == "localhost:7233"


def test_morning_briefing_config(mock_env):
    """Test morning briefing configuration functions."""
    assert get_morning_briefing_chat_id() == 123456

    # Test with invalid chat ID
    with patch.dict(os.environ, {"MORNING_BRIEFING_CHAT_ID": "not_an_id"}):
        assert get_morning_briefing_chat_id() is None

    # Test with missing chat ID
    with patch.dict(os.environ, {}, clear=True):
        assert get_morning_briefing_chat_id() is None


def test_log_level(mock_env):
    """Test log level configuration function."""
    import logging

    assert get_log_level() == logging.DEBUG

    # Test with missing log level
    with patch.dict(os.environ, {}, clear=True):
        # Should use default (INFO)
        assert get_log_level() == logging.INFO

    # Test with invalid log level
    with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
        # Should use default (INFO)
        assert get_log_level() == logging.INFO
