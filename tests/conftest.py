"""
Shared pytest configuration and fixtures for the test suite.

This module provides common fixtures, test markers, and configuration
for all test categories (unit, integration, obsidian-specific).
"""

import asyncio
import os
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from the_assistant.integrations.obsidian import MarkdownParser, MetadataExtractor

# Ensure JWT_SECRET is available for tests
os.environ.setdefault("JWT_SECRET", "test-secret")


@pytest.fixture(scope="function", autouse=True)
def mock_settings(monkeypatch):
    """Mock application settings for each test function."""
    mock_settings_obj = MagicMock()
    mock_settings_obj.db_encryption_key = "test-key"
    mock_settings_obj.jwt_secret = "test-secret"

    monkeypatch.setattr(
        "the_assistant.settings.get_settings", lambda: mock_settings_obj
    )


# Test markers for categorization and filtering
pytest_plugins = ["pytester"]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (slower, external deps)",
    )
    config.addinivalue_line("markers", "obsidian: marks tests as obsidian-specific")
    config.addinivalue_line("markers", "slow: marks tests as slow-running")
    config.addinivalue_line(
        "markers", "google: marks tests that interact with Google APIs"
    )
    config.addinivalue_line(
        "markers", "telegram: marks tests that interact with Telegram"
    )


# Shared fixtures for all tests
@pytest.fixture
def vault_path():
    """Shared fixture for test vault path."""
    return Path("obsidian_vault")


@pytest.fixture
def sample_markdown_content():
    """Shared fixture for markdown test content."""
    return """# Test Note

## Tasks
- [x] Completed task
- [ ] Pending task

## Links
Check out [[Internal Link]] and [External](https://example.com).

## Notes
Some additional content here.
"""


@pytest.fixture
def sample_frontmatter_content():
    """Shared fixture for content with YAML frontmatter."""
    return """---
tags:
  - test
  - sample
date: 2025-01-15
status: active
priority: medium
---

# Test Note with Frontmatter

This is the content after the frontmatter.
"""


@pytest.fixture
def markdown_parser():
    """Shared fixture for MarkdownParser instance."""
    return MarkdownParser()


@pytest.fixture
def metadata_extractor():
    """Shared fixture for MetadataExtractor instance."""
    return MetadataExtractor()


# Mock fixtures for external services
@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot for testing."""
    mock_bot = MagicMock()
    mock_bot.send_message.return_value = MagicMock()
    return mock_bot


@pytest.fixture
def mock_google_service():
    """Mock Google Calendar service for testing."""
    mock_service = MagicMock()
    mock_service.events().list().execute.return_value = {"items": []}
    return mock_service


@pytest.fixture
def mock_obsidian_notes():
    """Mock Obsidian notes collection for testing."""
    mock_notes = MagicMock()
    mock_notes.filter.return_value = []
    return mock_notes


# Test data fixtures
@pytest.fixture
def sample_task_content():
    """Sample markdown content with various task formats."""
    return """# Project Tasks

## Todo
- [ ] Task 1
- [x] Completed task
- [ ] Task 2

## In Progress
- [ ] Active task
- [ ] Another active task

## Done
- [x] Finished task 1
- [x] Finished task 2
"""


@pytest.fixture
def sample_metadata():
    """Sample metadata dictionary for testing."""
    return {
        "tags": ["test", "sample", "fixture"],
        "date": date(2025, 1, 15),
        "status": "active",
        "priority": "medium",
        "created": datetime(2025, 1, 15, 10, 30),
    }


@pytest.fixture
def sample_links_content():
    """Sample markdown content with various link formats."""
    return """# Links Test

Internal links: [[Note 1]], [[Note 2|Display Text]]

External links: [Google](https://google.com), [Example](https://example.com)

More internal: [[Another Note]]
"""


# Environment and configuration fixtures
@pytest.fixture
def test_env_vars(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "test_token")
    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", "/secrets/google.json")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "obsidian_vault")
    monkeypatch.setenv("TEMPORAL_HOST", "localhost:7233")


@pytest.fixture
def temp_vault_path(tmp_path):
    """Create a temporary vault directory for testing."""
    vault_dir = tmp_path / "test_vault"
    vault_dir.mkdir()

    # Create sample test files
    (vault_dir / "test_note.md").write_text("""---
tags: [test]
date: 2025-01-15
---

# Test Note

- [ ] Test task
""")

    return vault_dir


# Async test utilities
@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Test categories and execution control
def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark tests based on directory structure
        if "/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark tests based on specific integrations
        if "/obsidian/" in str(item.fspath):
            item.add_marker(pytest.mark.obsidian)
        if "google" in str(item.fspath):
            item.add_marker(pytest.mark.google)
        if "telegram" in str(item.fspath):
            item.add_marker(pytest.mark.telegram)

        # Mark slow tests based on name patterns or location
        if any(keyword in item.name.lower() for keyword in ["slow"]):
            item.add_marker(pytest.mark.slow)

        # Integration tests are generally slower
        if "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.slow)


# Custom test utilities
class TestHelpers:
    """Helper utilities for tests."""

    @staticmethod
    def create_test_note(content: str, frontmatter: dict | None = None) -> str:
        """Create a test note with optional frontmatter."""
        if frontmatter:
            frontmatter_str = yaml.dump(frontmatter, default_flow_style=False)
            return f"---\n{frontmatter_str}---\n\n{content}"
        return content

    @staticmethod
    def assert_task_properties(
        task,
        text: str | None = None,
        completed: bool | None = None,
        parent_heading: str | None = None,
    ):
        """Assert task properties with optional checks."""
        if text is not None:
            assert task.text == text
        if completed is not None:
            assert task.completed == completed
        if parent_heading is not None:
            assert task.parent_heading == parent_heading


@pytest.fixture
def test_helpers():
    """Provide test helper utilities."""
    return TestHelpers
