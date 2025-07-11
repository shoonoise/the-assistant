"""
Unit tests for the FilterEngine class.

These tests verify the functionality of the FilterEngine class for
filtering and searching Obsidian notes based on various criteria.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from the_assistant.integrations.obsidian.filter_engine import FilterEngine
from the_assistant.integrations.obsidian.models import (
    NoteFilters,
    ObsidianNote,
    TaskItem,
)


@pytest.fixture
def filter_engine():
    """Fixture providing a FilterEngine instance."""
    return FilterEngine()


@pytest.fixture
def sample_notes():
    """Fixture providing a list of sample notes for testing."""
    # Create a set of test notes with different properties

    # Paris trip note
    paris_note = ObsidianNote(
        title="Trip to Paris",
        path=Path("Trip to Paris.md"),
        content="# Trip to Paris\n\n## Tasks\n- [ ] Book airport transfer\n- [x] Confirm hotel",
        raw_content="---\ntags:\n  - trip\n  - france\nstart_date: 2025-03-15\nend_date: 2025-03-22\n---\n# Trip to Paris",
        metadata={
            "tags": ["trip", "france"],
            "start_date": "2025-03-15",
            "end_date": "2025-03-22",
            "destination": "Paris",
            "status": "planning",
        },
        tags=["trip", "france"],
        tasks=[
            TaskItem(text="Book airport transfer", completed=False, line_number=4),
            TaskItem(text="Confirm hotel", completed=True, line_number=5),
        ],
        headings=[],
        links=[],
        created_date=datetime(2025, 1, 15),
        modified_date=datetime(2025, 1, 15),
    )
    # Set computed properties
    paris_note._parse_date_property = MagicMock()  # type: ignore[method-assign]
    paris_note._parse_date_property.side_effect = lambda prop: {  # type: ignore[attr-defined]
        "start_date": date(2025, 3, 15),
        "end_date": date(2025, 3, 22),
    }.get(prop)

    # Tokyo trip note
    tokyo_note = ObsidianNote(
        title="Business Trip to Tokyo",
        path=Path("Business Trip to Tokyo.md"),
        content="# Business Trip to Tokyo\n\n## Tasks\n- [ ] Prepare presentation\n- [x] Register",
        raw_content="---\ntags:\n  - trip\n  - business\n  - japan\nstart_date: 2025-02-10\nend_date: 2025-02-17\n---\n# Business Trip to Tokyo",
        metadata={
            "tags": ["trip", "business", "japan"],
            "start_date": "2025-02-10",
            "end_date": "2025-02-17",
            "destination": "Tokyo",
            "status": "booked",
            "trip_type": "business",
        },
        tags=["trip", "business", "japan"],
        tasks=[
            TaskItem(text="Prepare presentation", completed=False, line_number=4),
            TaskItem(text="Register", completed=True, line_number=5),
        ],
        headings=[],
        links=[],
        created_date=datetime(2025, 1, 10),
        modified_date=datetime(2025, 1, 12),
    )
    # Set computed properties
    tokyo_note._parse_date_property = MagicMock()  # type: ignore[method-assign]
    tokyo_note._parse_date_property.side_effect = lambda prop: {  # type: ignore[attr-defined]
        "start_date": date(2025, 2, 10),
        "end_date": date(2025, 2, 17),
    }.get(prop)

    # French lesson note
    french_note = ObsidianNote(
        title="French Lesson Notes",
        path=Path("French Lesson Notes.md"),
        content="# French Lesson Notes\n\n## Vocabulary\n- Bonjour\n- Merci",
        raw_content="---\ntags:\n  - french-lesson\n  - language\ndate: 2025-01-10\n---\n# French Lesson Notes",
        metadata={
            "tags": ["french-lesson", "language"],
            "date": "2025-01-10",
            "status": "completed",
        },
        tags=["french-lesson", "language"],
        tasks=[],  # No tasks
        headings=[],
        links=[],
        created_date=datetime(2025, 1, 10),
        modified_date=datetime(2025, 1, 10),
    )
    # Set computed properties
    french_note._parse_date_property = MagicMock()  # type: ignore[method-assign]
    french_note._parse_date_property.side_effect = (  # type: ignore[attr-defined]
        lambda prop: None
    )  # No start/end dates

    # Work project note
    work_note = ObsidianNote(
        title="Work Project Alpha",
        path=Path("Work Project Alpha.md"),
        content="# Work Project Alpha\n\n## Tasks\n- [ ] Complete phase 1\n- [ ] Review with team",
        raw_content="---\ntags:\n  - work\n  - project\ndue_date: 2025-02-28\n---\n# Work Project Alpha",
        metadata={
            "tags": ["work", "project"],
            "due_date": "2025-02-28",
            "priority": "high",
            "status": "in-progress",
        },
        tags=["work", "project"],
        tasks=[
            TaskItem(text="Complete phase 1", completed=False, line_number=4),
            TaskItem(text="Review with team", completed=False, line_number=5),
        ],
        headings=[],
        links=[],
        created_date=datetime(2025, 1, 5),
        modified_date=datetime(2025, 1, 14),
    )
    # Set computed properties
    work_note._parse_date_property = MagicMock()  # type: ignore[method-assign]
    work_note._parse_date_property.side_effect = lambda prop: {  # type: ignore[attr-defined]
        "due_date": date(2025, 2, 28)
    }.get(prop)

    return [paris_note, tokyo_note, french_note, work_note]


class TestFilterEngine:
    """Tests for the FilterEngine class."""

    def test_filter_by_tags_or(self, filter_engine, sample_notes):
        """Test filtering notes by tags with OR operator."""
        # Filter for notes with either 'trip' or 'work' tag
        filtered = filter_engine.filter_by_tags(sample_notes, ["trip", "work"], "OR")

        # Should include Paris, Tokyo, and Work notes (3 total)
        assert len(filtered) == 3
        assert "Trip to Paris" in [note.title for note in filtered]
        assert "Business Trip to Tokyo" in [note.title for note in filtered]
        assert "Work Project Alpha" in [note.title for note in filtered]
        assert "French Lesson Notes" not in [note.title for note in filtered]

    def test_filter_by_tags_and(self, filter_engine, sample_notes):
        """Test filtering notes by tags with AND operator."""
        # Filter for notes with both 'trip' and 'business' tags
        filtered = filter_engine.filter_by_tags(
            sample_notes, ["trip", "business"], "AND"
        )

        # Should only include Tokyo note
        assert len(filtered) == 1
        assert filtered[0].title == "Business Trip to Tokyo"

    def test_filter_by_tags_empty(self, filter_engine, sample_notes):
        """Test filtering with empty tag list."""
        # Empty tag list should return all notes
        filtered = filter_engine.filter_by_tags(sample_notes, [], "OR")
        assert len(filtered) == len(sample_notes)

    def test_filter_by_tags_invalid_operator(self, filter_engine, sample_notes):
        """Test filtering with invalid operator."""
        # Invalid operator should raise ValueError
        with pytest.raises(ValueError):
            filter_engine.filter_by_tags(sample_notes, ["trip"], "INVALID")

    def test_filter_by_date_range(self, filter_engine, sample_notes):
        """Test filtering notes by date range."""
        # Filter for notes with dates in February 2025
        start = date(2025, 2, 1)
        end = date(2025, 2, 28)
        filtered = filter_engine.filter_by_date_range(sample_notes, start, end)

        # Should include Tokyo and Work notes
        assert len(filtered) == 2
        assert "Business Trip to Tokyo" in [note.title for note in filtered]
        assert "Work Project Alpha" in [note.title for note in filtered]

    def test_filter_by_date_range_empty(self, filter_engine, sample_notes):
        """Test filtering with empty date range."""
        # None dates should return all notes
        filtered = filter_engine.filter_by_date_range(sample_notes, None, None)
        assert len(filtered) == len(sample_notes)

    def test_filter_by_property(self, filter_engine, sample_notes):
        """Test filtering notes by a specific property."""
        # Filter for notes with status 'planning'
        filtered = filter_engine.filter_by_property(sample_notes, "status", "planning")

        # Should only include Paris note
        assert len(filtered) == 1
        assert filtered[0].title == "Trip to Paris"

    def test_filter_by_properties(self, filter_engine, sample_notes):
        """Test filtering notes by multiple properties."""
        # Filter for notes with trip_type 'business' and destination 'Tokyo'
        properties = {"trip_type": "business", "destination": "Tokyo"}
        filtered = filter_engine.filter_by_properties(sample_notes, properties)

        # Should only include Tokyo note
        assert len(filtered) == 1
        assert filtered[0].title == "Business Trip to Tokyo"

    def test_filter_by_properties_empty(self, filter_engine, sample_notes):
        """Test filtering with empty properties dict."""
        # Empty properties should return all notes
        filtered = filter_engine.filter_by_properties(sample_notes, {})
        assert len(filtered) == len(sample_notes)

    def test_get_upcoming_notes(self, filter_engine, sample_notes):
        """Test getting upcoming notes."""
        # Use a fixed reference date for testing
        reference_date = date(2025, 2, 1)

        # Get notes starting in the next 30 days from reference date
        upcoming = filter_engine.get_upcoming_notes(sample_notes, 30, reference_date)

        # Should only include Tokyo note (starts Feb 10)
        assert len(upcoming) == 1
        assert upcoming[0].title == "Business Trip to Tokyo"

        # Test with 60 days ahead (should include Paris note too)
        upcoming_60 = filter_engine.get_upcoming_notes(sample_notes, 60, reference_date)
        assert len(upcoming_60) == 2
        assert "Business Trip to Tokyo" in [note.title for note in upcoming_60]
        assert "Trip to Paris" in [note.title for note in upcoming_60]

        # Verify sorting by start_date
        assert upcoming_60[0].title == "Business Trip to Tokyo"  # Feb 10
        assert upcoming_60[1].title == "Trip to Paris"  # Mar 15

    def test_filter_by_pending_tasks(self, filter_engine, sample_notes):
        """Test filtering notes by pending task status."""
        # Filter for notes with pending tasks
        with_tasks = filter_engine.filter_by_pending_tasks(sample_notes, True)

        # Should include Paris, Tokyo, and Work notes (all have pending tasks)
        assert len(with_tasks) == 3
        assert "French Lesson Notes" not in [note.title for note in with_tasks]

        # Filter for notes without pending tasks
        without_tasks = filter_engine.filter_by_pending_tasks(sample_notes, False)

        # Should only include French note
        assert len(without_tasks) == 1
        assert without_tasks[0].title == "French Lesson Notes"

    def test_search_by_content(self, filter_engine, sample_notes):
        """Test searching notes by content."""
        # Search for 'Paris' in content
        results = filter_engine.search_by_content(sample_notes, "Paris")

        # Should only include Paris note
        assert len(results) == 1
        assert results[0].title == "Trip to Paris"

        # Search for 'trip' (case-insensitive)
        results = filter_engine.search_by_content(sample_notes, "trip")

        # Should include Paris and Tokyo notes
        assert len(results) == 2
        assert "Trip to Paris" in [note.title for note in results]
        assert "Business Trip to Tokyo" in [note.title for note in results]

        # Search with case sensitivity
        results = filter_engine.search_by_content(
            sample_notes, "trip", case_sensitive=True
        )

        # Should include no notes (as 'trip' is capitalized in titles)
        assert len(results) == 0

    def test_sort_notes(self, filter_engine, sample_notes):
        """Test sorting notes by different attributes."""
        # Sort by title (ascending)
        sorted_by_title = filter_engine.sort_notes(sample_notes, "title")
        assert sorted_by_title[0].title == "Business Trip to Tokyo"
        assert sorted_by_title[-1].title == "Work Project Alpha"

        # Sort by start_date (ascending)
        sorted_by_date = filter_engine.sort_notes(sample_notes, "start_date")

        # Notes with start_dates should come first (Tokyo then Paris)
        assert sorted_by_date[0].title == "Business Trip to Tokyo"  # Feb 10
        assert sorted_by_date[1].title == "Trip to Paris"  # Mar 15

        # Sort by modified_date (descending)
        # Update the sample notes to ensure the modified dates are in the expected order
        for note in sample_notes:
            if note.title == "Work Project Alpha":
                note.modified_date = datetime(2025, 1, 14)
            elif note.title == "Business Trip to Tokyo":
                note.modified_date = datetime(2025, 1, 12)
            elif note.title == "Trip to Paris":
                note.modified_date = datetime(2025, 1, 10)
            elif note.title == "French Lesson Notes":
                note.modified_date = datetime(2025, 1, 8)

        sorted_by_modified = filter_engine.sort_notes(
            sample_notes, "modified_date", reverse=True
        )
        assert sorted_by_modified[0].title == "Work Project Alpha"  # Jan 14
        assert sorted_by_modified[1].title == "Business Trip to Tokyo"  # Jan 12

    def test_sort_notes_invalid_field(self, filter_engine, sample_notes):
        """Test sorting with invalid field."""
        # Invalid sort field should raise ValueError
        with pytest.raises(ValueError):
            filter_engine.sort_notes(sample_notes, "invalid_field")

    def test_apply_filters_with_note_filters(self, filter_engine, sample_notes):
        """Test applying filters using NoteFilters object."""
        # Create a NoteFilters object
        filters = NoteFilters(
            tags=["trip"], tag_operator="AND", properties={"status": "booked"}
        )

        # Apply filters
        filtered = filter_engine.apply_filters(sample_notes, filters)

        # Should only include Tokyo note
        assert len(filtered) == 1
        assert filtered[0].title == "Business Trip to Tokyo"

    def test_apply_filters_with_kwargs(self, filter_engine, sample_notes):
        """Test applying filters using keyword arguments."""
        # Reference date for testing
        reference_date = date(2025, 2, 1)

        # Apply multiple filters with kwargs
        filtered = filter_engine.apply_filters(
            sample_notes,
            tags=["trip"],
            date_range=(reference_date, reference_date + timedelta(days=30)),
            has_pending_tasks=True,
            sort_by="title",
        )

        # Should only include Tokyo note
        assert len(filtered) == 1
        assert filtered[0].title == "Business Trip to Tokyo"

    def test_apply_filters_combined(self, filter_engine, sample_notes):
        """Test applying both NoteFilters and kwargs."""
        # Create a NoteFilters object
        filters = NoteFilters(tags=["trip"])

        # Apply both filters object and kwargs
        filtered = filter_engine.apply_filters(
            sample_notes, filters, properties={"destination": "Paris"}, sort_by="title"
        )

        # Should only include Paris note
        assert len(filtered) == 1
        assert filtered[0].title == "Trip to Paris"

    def test_filter_notes_method(self, filter_engine, sample_notes):
        """Test the filter_notes method directly."""
        # Create a NoteFilters object
        filters = NoteFilters(tags=["work"], has_pending_tasks=True)

        # Apply filters
        filtered = filter_engine.filter_notes(sample_notes, filters)

        # Should only include Work note
        assert len(filtered) == 1
        assert filtered[0].title == "Work Project Alpha"
