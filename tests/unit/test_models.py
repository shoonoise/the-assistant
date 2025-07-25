"""Unit tests for shared data models.

These tests verify the functionality of the shared data models in utils/models.py.
"""

from datetime import date, datetime, timedelta
from pathlib import Path

# Import UTC timezone
try:
    from datetime import UTC
except ImportError:
    # For Python < 3.11

    UTC = UTC

from the_assistant.models.google import CalendarEvent, GmailMessage
from the_assistant.models.obsidian import (
    Heading,
    Link,
    ObsidianNote,
    TaskItem,
)


def test_calendar_event_properties():
    """Test CalendarEvent model properties."""
    # Create a calendar event in the future to ensure is_upcoming is True
    future_time = datetime.now(UTC) + timedelta(minutes=30)
    event = CalendarEvent(
        id="event123",
        summary="Team Meeting",
        start_time=future_time,
        end_time=future_time + timedelta(hours=1),
        calendar_id="primary",
        description="Weekly team sync",
        location="Conference Room A",
        is_all_day=False,
    )

    # Test properties
    assert event.duration == timedelta(hours=1)
    assert event.is_upcoming is True  # Since start_time is in the future
    assert event.is_today is True  # Since start_time is today


def test_task_item_properties():
    """Test TaskItem model properties."""
    # Create task items with different indentation levels
    task1 = TaskItem(
        text="Root task",
        completed=False,
        line_number=10,
        indent_level=0,
    )

    task2 = TaskItem(
        text="Nested task",
        completed=True,
        line_number=11,
        indent_level=2,
        parent_heading="Heading",
    )

    task3 = TaskItem(
        text="Deeply nested task",
        completed=False,
        line_number=12,
        indent_level=4,
    )

    # Test properties
    assert task1.is_nested is False
    assert task1.nesting_level == 0
    assert str(task1) == "- [ ] Root task"

    assert task2.is_nested is True
    assert task2.nesting_level == 1
    assert str(task2) == "  - [x] Nested task"

    assert task3.is_nested is True
    assert task3.nesting_level == 2
    assert str(task3) == "    - [ ] Deeply nested task"


def test_heading_str_representation():
    """Test Heading model string representation."""
    h1 = Heading(level=1, text="Title", line_number=1)
    h2 = Heading(level=2, text="Subtitle", line_number=3)
    h3 = Heading(level=3, text="Section", line_number=5)

    assert str(h1) == "# Title"
    assert str(h2) == "## Subtitle"
    assert str(h3) == "### Section"


def test_link_str_representation():
    """Test Link model string representation."""
    internal_link = Link(text="Note", url="Note", is_internal=True)
    internal_link_with_alias = Link(text="Alias", url="Note", is_internal=True)
    external_link = Link(text="Google", url="https://google.com", is_internal=False)

    assert str(internal_link) == "[[Note]]"
    assert str(internal_link_with_alias) == "[[Note|Alias]]"
    assert str(external_link) == "[Google](https://google.com)"


def test_obsidian_note_properties():
    """Test ObsidianNote model properties."""
    # Create tasks
    task1 = TaskItem(text="Task 1", completed=False, line_number=10)
    task2 = TaskItem(text="Task 2", completed=True, line_number=11)
    task3 = TaskItem(text="Task 3", completed=False, line_number=12)

    # Create a note
    note = ObsidianNote(
        title="Test Note",
        path=Path("test_note.md"),
        content="Note content",
        metadata={
            "title": "Test Note",
            "start_date": "2024-07-20",
            "end_date": "2024-07-25",
        },
        tags=["tag1", "tag2"],
        tasks=[task1, task2, task3],
    )

    # Test properties
    assert note.pending_tasks == [task1, task3]
    assert note.completed_tasks == [task2]
    assert note.has_pending_tasks is True
    assert note.task_completion_ratio == 1 / 3

    # Test date parsing
    assert note.start_date == date(2024, 7, 20)
    assert note.end_date == date(2024, 7, 25)


def test_obsidian_note_date_parsing():
    """Test ObsidianNote date parsing with different formats."""
    # Create notes with different date formats
    formats = [
        ("2024-07-15", date(2024, 7, 15)),  # ISO format
        ("07/15/2024", date(2024, 7, 15)),  # US format
        ("15/07/2024", date(2024, 7, 15)),  # European format
        ("2024/07/15", date(2024, 7, 15)),  # Alternative ISO
        ("15-07-2024", date(2024, 7, 15)),  # European with dashes
        ("07-15-2024", date(2024, 7, 15)),  # US with dashes
        ("July 15, 2024", date(2024, 7, 15)),  # Long format
        ("Jul 15, 2024", date(2024, 7, 15)),  # Short month
        ("15 July 2024", date(2024, 7, 15)),  # European long
        ("15 Jul 2024", date(2024, 7, 15)),  # European short
    ]

    for date_str, expected_date in formats:
        note = ObsidianNote(
            title="Date Test",
            path=Path("test.md"),
            content="Content",
            metadata={"start_date": date_str},
        )
        assert note.start_date == expected_date, f"Failed to parse {date_str}"


def test_gmail_message_formatted_date():
    """GmailMessage formats dates without timezone or seconds."""
    dt = datetime(2025, 4, 1, 13, 0, tzinfo=UTC)
    msg = GmailMessage(id="1", thread_id="t", snippet="", date=dt)
    assert msg.formatted_date == "1 April 2025 13:00"


# TripInfo and TripNotification models were removed as they weren't actually used
# Tests for these models have been removed
