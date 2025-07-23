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
            "GOOGLE_OAUTH_SCOPES": '["scope"]',
        },
        clear=True,
    ):
        yield


def test_defaults(minimal_env):
    settings = Settings()
    assert settings.temporal_host == "localhost:7233"
    assert settings.google_calendar_id == "primary"
    assert settings.google_oauth_redirect_uri.startswith("http://localhost")


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
            "GOOGLE_OAUTH_SCOPES": '["a", "b"]',
        },
        clear=True,
    ):
        settings = Settings()
        assert settings.temporal_host == "test:7233"
        assert settings.google_credentials_path == Path("test/google.json")
        assert settings.google_oauth_scopes == ["a", "b"]


def test_missing_required():
    from pydantic import ValidationError

    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValidationError):
            Settings()
