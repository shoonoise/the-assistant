"""Unit tests for Pydantic settings."""

from pathlib import Path
from unittest.mock import patch

import pytest

from the_assistant.settings import Settings


@pytest.fixture
def minimal_env():
    with patch.dict(
        "os.environ",
        {
            "TELEGRAM_TOKEN": "token",
            "DB_ENCRYPTION_KEY": "key",
            "JWT_SECRET": "secret",
            "OBSIDIAN_VAULT_PATH": "/vault",
        },
        clear=True,
    ):
        yield


def test_env_overrides():
    with patch.dict(
        "os.environ",
        {
            "TELEGRAM_TOKEN": "token",
            "DB_ENCRYPTION_KEY": "key",
            "JWT_SECRET": "secret",
            "OBSIDIAN_VAULT_PATH": "/vault",
            "TEMPORAL_HOST": "test:7233",
            "GOOGLE_CREDENTIALS_PATH": "test/google.json",
        },
        clear=True,
    ):
        settings = Settings()
        assert settings.temporal_host == "test:7233"
        assert settings.google_credentials_path == Path("test/google.json")
        assert settings.google_oauth_scopes == [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar.events.readonly",
        ]
