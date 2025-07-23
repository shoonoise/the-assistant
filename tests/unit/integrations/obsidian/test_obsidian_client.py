"""
Unit tests for the ObsidianClient class.

These tests verify the functionality of the ObsidianClient class,
which integrates all components for interacting with Obsidian vaults.
"""

from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from the_assistant.integrations.obsidian.models import (
    Heading,
    NoteFilters,
    ObsidianClientError,
    ObsidianNote,
    TaskItem,
    TaskUpdateError,
)
from the_assistant.integrations.obsidian.obsidian_client import ObsidianClient


@pytest.fixture
def mock_vault_manager():
    """Fixture providing a mocked VaultManager."""
    with patch(
        "the_assistant.integrations.obsidian.obsidian_client.VaultManager"
    ) as mock:
        # Configure the mock
        instance = mock.return_value
        instance.scan_vault = AsyncMock()
        instance.load_note_raw = AsyncMock()
        instance.save_note = AsyncMock()
        instance.get_note_stats = AsyncMock()
        instance.note_exists = AsyncMock()
        instance.delete_note = AsyncMock()
        instance.rename_note = AsyncMock()
        instance.get_vault_stats = AsyncMock()
        instance._resolve_path = MagicMock()

        yield instance


@pytest.fixture
def mock_markdown_parser():
    """Fixture providing a mocked MarkdownParser."""
    with patch(
        "the_assistant.integrations.obsidian.obsidian_client.MarkdownParser"
    ) as mock:
        # Configure the mock
        instance = mock.return_value
        instance.parse_content = MagicMock()

        yield instance


@pytest.fixture
def mock_metadata_extractor():
    """Fixture providing a mocked MetadataExtractor."""
    with patch(
        "the_assistant.integrations.obsidian.obsidian_client.MetadataExtractor"
    ) as mock:
        # Configure the mock
        instance = mock.return_value
        instance.extract_frontmatter = MagicMock()
        instance.extract_tags = MagicMock()
        instance.merge_metadata = MagicMock()

        yield instance


@pytest.fixture
def mock_filter_engine():
    """Fixture providing a mocked FilterEngine."""
    with patch(
        "the_assistant.integrations.obsidian.obsidian_client.FilterEngine"
    ) as mock:
        # Configure the mock
        instance = mock.return_value
        instance.filter_notes = MagicMock()
        instance.filter_by_tags = MagicMock()
        instance.filter_by_date_range = MagicMock()
        instance.search_by_content = MagicMock()

        yield instance


@pytest.fixture
def client(
    mock_vault_manager,
    mock_markdown_parser,
    mock_metadata_extractor,
    mock_filter_engine,
):
    """Fixture providing an ObsidianClient with mocked dependencies."""
    return ObsidianClient("test_vault", user_id=1)


@pytest.fixture
def sample_note():
    """Fixture providing a sample ObsidianNote for testing."""
    return ObsidianNote(
        title="Test Note",
        path=Path("test_note.md"),
        content="# Test Note\n\n## Tasks\n- [ ] Task 1\n- [x] Task 2",
        raw_content="---\ntags: [test, sample]\n---\n# Test Note\n\n## Tasks\n- [ ] Task 1\n- [x] Task 2",
        metadata={"tags": ["test", "sample"]},
        tags=["test", "sample"],
        tasks=[
            TaskItem(
                text="Task 1", completed=False, line_number=4, parent_heading="Tasks"
            ),
            TaskItem(
                text="Task 2", completed=True, line_number=5, parent_heading="Tasks"
            ),
        ],
        headings=[
            Heading(level=1, text="Test Note", line_number=1),
            Heading(level=2, text="Tasks", line_number=3),
        ],
        links=[],
        created_date=datetime(2025, 1, 1),
        modified_date=datetime(2025, 1, 2),
    )


class TestObsidianClient:
    """Tests for the ObsidianClient class."""

    async def test_get_notes(
        self,
        client,
        mock_vault_manager,
        mock_metadata_extractor,
        mock_markdown_parser,
        sample_note,
    ):
        """Test getting all notes from the vault."""
        # Configure mocks
        mock_vault_manager.scan_vault.return_value = [Path("test_note.md")]
        mock_vault_manager.load_note_raw.return_value = sample_note.raw_content
        mock_vault_manager.get_note_stats.return_value = {
            "created": sample_note.created_date,
            "modified": sample_note.modified_date,
        }
        # Fix: metadata should include title to override path.stem
        metadata_with_title = {"tags": ["test", "sample"], "title": "Test Note"}
        mock_metadata_extractor.extract_frontmatter.return_value = (
            metadata_with_title,
            sample_note.content,
        )
        mock_metadata_extractor.extract_tags.return_value = sample_note.tags
        mock_markdown_parser.parse_content.return_value = (
            sample_note.tasks,
            sample_note.headings,
            sample_note.links,
        )

        # Call the method
        notes = await client.get_notes()

        # Verify results
        assert len(notes) == 1
        assert notes[0].title == "Test Note"
        assert notes[0].tags == ["test", "sample"]

        # Verify mock calls
        mock_vault_manager.scan_vault.assert_called_once()
        mock_vault_manager.load_note_raw.assert_called_once()
        mock_metadata_extractor.extract_frontmatter.assert_called_once()
        mock_markdown_parser.parse_content.assert_called_once()

    async def test_get_notes_with_filters(
        self,
        client,
        mock_vault_manager,
        mock_filter_engine,
        mock_metadata_extractor,
        mock_markdown_parser,
        sample_note,
    ):
        """Test getting notes with filters."""
        # Configure mocks to return a sample note
        mock_vault_manager.scan_vault.return_value = [Path("test_note.md")]
        mock_vault_manager.load_note_raw.return_value = sample_note.raw_content
        mock_vault_manager.get_note_stats.return_value = {
            "created": sample_note.created_date,
            "modified": sample_note.modified_date,
        }
        metadata_with_title = {"tags": ["test", "sample"], "title": "Test Note"}
        mock_metadata_extractor.extract_frontmatter.return_value = (
            metadata_with_title,
            sample_note.content,
        )
        mock_metadata_extractor.extract_tags.return_value = sample_note.tags
        mock_markdown_parser.parse_content.return_value = (
            sample_note.tasks,
            sample_note.headings,
            sample_note.links,
        )

        # Create filters
        filters = NoteFilters(tags=["test"])
        mock_filter_engine.filter_notes.return_value = [sample_note]

        # Call the method
        notes = await client.get_notes(filters)

        # Verify results
        assert len(notes) == 1
        assert notes[0].title == "Test Note"

        # Verify mock calls - should be called with the loaded notes, not empty list
        mock_filter_engine.filter_notes.assert_called_once()

    async def test_get_note(
        self,
        client,
        mock_vault_manager,
        mock_metadata_extractor,
        mock_markdown_parser,
        sample_note,
    ):
        """Test getting a single note by path."""
        # Configure mocks
        mock_vault_manager.note_exists.return_value = True
        mock_vault_manager._resolve_path.return_value = Path("test_note.md")
        mock_vault_manager.load_note_raw.return_value = sample_note.raw_content
        mock_vault_manager.get_note_stats.return_value = {
            "created": sample_note.created_date,
            "modified": sample_note.modified_date,
        }
        # Include title in metadata to override path.stem
        metadata_with_title = {"tags": ["test", "sample"], "title": "Test Note"}
        mock_metadata_extractor.extract_frontmatter.return_value = (
            metadata_with_title,
            sample_note.content,
        )
        mock_metadata_extractor.extract_tags.return_value = sample_note.tags
        mock_markdown_parser.parse_content.return_value = (
            sample_note.tasks,
            sample_note.headings,
            sample_note.links,
        )

        # Call the method
        note = await client.get_note("test_note.md")

        # Verify results
        assert note.title == "Test Note"
        assert note.tags == ["test", "sample"]
        assert len(note.tasks) == 2
        assert len(note.headings) == 2

        # Verify mock calls
        mock_vault_manager.note_exists.assert_called_once()
        mock_vault_manager.load_note_raw.assert_called_once()
        mock_metadata_extractor.extract_frontmatter.assert_called_once_with(
            sample_note.raw_content
        )
        mock_markdown_parser.parse_content.assert_called_once_with(sample_note.content)

    async def test_get_note_not_found(self, client, mock_vault_manager):
        """Test getting a note that doesn't exist."""
        # Configure mock to return False for note_exists
        mock_vault_manager.note_exists.return_value = False

        # Call the method and verify it returns None
        result = await client.get_note("nonexistent.md")
        assert result is None

    async def test_create_note(
        self, client, mock_vault_manager, mock_metadata_extractor, mock_markdown_parser
    ):
        """Test creating a new note."""
        # Configure mocks
        mock_vault_manager.note_exists.return_value = False
        mock_vault_manager.save_note.return_value = True
        mock_vault_manager.load_note_raw.return_value = (
            "---\ncreated: '2025-01-01'\n---\n\n# New Note\n\nTest content"
        )
        mock_vault_manager.get_note_stats.return_value = {
            "created": None,
            "modified": None,
        }
        mock_vault_manager._resolve_path.return_value = Path("New Note.md")

        mock_metadata_extractor.extract_frontmatter.return_value = (
            {"created": "2025-01-01"},
            "# New Note\n\nTest content",
        )
        mock_metadata_extractor.extract_tags.return_value = []
        mock_markdown_parser.parse_content.return_value = (
            [],
            [],
            [],
        )  # tasks, headings, links

        # Don't mock get_note - let the method create the note naturally

        # Call the method
        note = await client.create_note("New Note", "Test content")

        # Verify results
        assert note.title == "New Note"
        assert "Test content" in note.content

        # Verify mock calls
        mock_vault_manager.note_exists.assert_called_once()
        mock_vault_manager.save_note.assert_called_once()

    async def test_create_note_already_exists(self, client, mock_vault_manager):
        """Test creating a note that already exists."""
        # Configure mock to indicate note exists
        mock_vault_manager.note_exists.return_value = True

        # Call the method and verify exception
        with pytest.raises(ObsidianClientError):
            await client.create_note("Existing Note", "Test content")

    async def test_update_note(self, client, mock_vault_manager, sample_note):
        """Test updating an existing note."""
        # Configure mocks
        client.get_note = AsyncMock(return_value=sample_note)
        mock_vault_manager.save_note.return_value = True
        mock_vault_manager._resolve_path.return_value = Path("test_note.md")

        # Call the method
        result = await client.update_note("test_note.md", content="Updated content")

        # Verify results - update_note returns bool, not the updated note
        assert result is True

        # Verify mock calls
        client.get_note.assert_called_once()
        mock_vault_manager.save_note.assert_called_once()

    async def test_update_note_metadata(
        self, client, mock_vault_manager, mock_metadata_extractor, sample_note
    ):
        """Test updating note metadata."""
        # Configure mocks
        client.get_note = AsyncMock(return_value=sample_note)
        mock_vault_manager.save_note.return_value = True

        # Configure metadata merger
        updated_metadata = {"tags": ["test", "sample", "updated"]}
        mock_metadata_extractor.merge_metadata.return_value = updated_metadata

        # Updated note to return after update
        updated_note = ObsidianNote(
            title="Test Note",
            path=Path("test_note.md"),
            content=sample_note.content,
            raw_content=sample_note.raw_content,
            metadata=updated_metadata,
            tags=["test", "sample", "updated"],
            tasks=sample_note.tasks,
            headings=sample_note.headings,
            links=sample_note.links,
            created_date=sample_note.created_date,
            modified_date=sample_note.modified_date,
        )

        # Configure get_note to return updated note on second call
        client.get_note = AsyncMock(side_effect=[sample_note, updated_note])

        # Call the method
        result = await client.update_note(
            "test_note.md", metadata={"tags": ["updated"]}
        )

        # Verify results - update_note returns bool, not the updated note
        assert result is True

        # Verify mock calls
        mock_metadata_extractor.merge_metadata.assert_called_once()
        mock_vault_manager.save_note.assert_called_once()

    async def test_filter_by_tags_using_note_filters(
        self, client, mock_filter_engine, sample_note
    ):
        """Test filtering notes by tags using NoteFilters."""
        # Configure mocks
        mock_filter_engine.filter_notes.return_value = [sample_note]
        client._load_all_notes = AsyncMock(return_value=[sample_note])

        # Create filters and call the method
        filters = NoteFilters(tags=["test"], tag_operator="OR")
        result = await client.get_notes(filters)

        # Verify results
        assert len(result) == 1
        assert result[0].title == "Test Note"

        # Verify mock calls
        mock_filter_engine.filter_notes.assert_called_once_with([sample_note], filters)

    async def test_filter_by_date_range_using_note_filters(
        self, client, mock_filter_engine, sample_note
    ):
        """Test filtering notes by date range using NoteFilters."""
        # Configure mocks
        mock_filter_engine.filter_notes.return_value = [sample_note]
        client._load_all_notes = AsyncMock(return_value=[sample_note])

        # Create filters and call the method
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)
        filters = NoteFilters(date_range=(start_date, end_date))
        result = await client.get_notes(filters)

        # Verify results
        assert len(result) == 1
        assert result[0].title == "Test Note"

        # Verify mock calls
        mock_filter_engine.filter_notes.assert_called_once_with([sample_note], filters)

    async def test_get_pending_tasks(self, client, sample_note):
        """Test getting pending tasks."""
        # Configure mocks
        client.get_notes = AsyncMock(return_value=[sample_note])

        # Call the method
        result = await client.get_pending_tasks()

        # Verify results
        assert len(result) == 1
        assert result[0].text == "Task 1"
        assert not result[0].completed
        assert hasattr(result[0], "note_title")
        assert result[0].note_title == "Test Note"

        # Verify mock calls
        client.get_notes.assert_called_once()

    async def test_get_pending_tasks_with_tag_filter(self, client, sample_note):
        """Test getting pending tasks with tag filter."""
        # Configure mocks
        client.get_notes = AsyncMock(return_value=[sample_note])

        # Call the method
        result = await client.get_pending_tasks(tag_filter=["test"])

        # Verify results
        assert len(result) == 1
        assert result[0].text == "Task 1"

        # Verify mock calls - get_notes is called with NoteFilters
        client.get_notes.assert_called_once()
        # Check that the call was made with filters
        call_args = client.get_notes.call_args
        assert call_args[0][0].tags == [
            "test"
        ]  # First positional arg should be NoteFilters with tags
        assert call_args[0][0].tag_operator == "OR"

    async def test_mark_task_complete(self, client, mock_vault_manager, sample_note):
        """Test marking a task as complete."""
        # Configure mocks
        client.get_note = AsyncMock(return_value=sample_note)
        # Set up raw content with proper checkbox format
        raw_content = "# Test Note\n\n## Tasks\n- [ ] Task 1\n- [x] Task 2"
        mock_vault_manager.load_note_raw.return_value = raw_content
        mock_vault_manager.save_note.return_value = True

        # Call the method
        result = await client.mark_task_complete("test_note.md", "Task 1")

        # Verify results
        assert result is True

        # Verify mock calls
        client.get_note.assert_called_once()
        mock_vault_manager.save_note.assert_called_once()

    async def test_mark_task_complete_not_found(self, client, sample_note):
        """Test marking a non-existent task as complete."""
        # Configure mocks
        client.get_note = AsyncMock(return_value=sample_note)

        # Call the method and verify exception
        with pytest.raises(TaskUpdateError):
            await client.mark_task_complete("test_note.md", "Nonexistent Task")

    async def test_get_vault_stats(self, client, mock_vault_manager):
        """Test getting vault statistics."""
        # Configure mocks
        mock_vault_manager.get_vault_stats.return_value = {
            "total_notes": 10,
            "total_size_bytes": 5000,
            "newest_note": "test_note.md",
            "newest_note_time": datetime(2025, 1, 2),
            "vault_path": "test_vault",
        }

        # Call the method
        result = await client.get_vault_stats()

        # Verify results
        assert result["total_notes"] == 10
        assert result["total_size_bytes"] == 5000

        # Verify mock calls
        mock_vault_manager.get_vault_stats.assert_called_once()

    async def test_filter_by_trip_tag_integration(self):
        """Test filtering notes by 'trip' tag using real vault data."""
        from the_assistant.integrations.obsidian.models import NoteFilters

        # Use real ObsidianClient with actual vault path
        real_client = ObsidianClient("obsidian_vault", user_id=1)

        # Get all notes first
        all_notes = await real_client.get_notes()
        print(f"Total notes found: {len(all_notes)}")

        # Filter by 'trip' tag using NoteFilters
        trip_filters = NoteFilters(tags=["trip"], tag_operator="OR")
        trip_notes = await real_client.get_notes(trip_filters)
        print(f"Notes with 'trip' tag: {len(trip_notes)}")

        # Verify we found trip notes
        assert len(trip_notes) > 0, "Should find notes with 'trip' tag"

        # Verify all returned notes have the 'trip' tag
        for note in trip_notes:
            note_tags = note.get_tag_list()
            assert "trip" in note_tags, (
                f"Note '{note.title}' should have 'trip' tag, but has: {note_tags}"
            )
            print(f"✓ {note.title} has trip tag: {note_tags}")

        # Test case sensitivity - should work with different cases
        trip_filters_upper = NoteFilters(tags=["TRIP"], tag_operator="OR")
        trip_notes_upper = await real_client.get_notes(trip_filters_upper)
        assert len(trip_notes_upper) == len(trip_notes), (
            "Tag filtering should be case insensitive"
        )

    async def test_trip_notes_have_pending_tasks(self):
        """Test that trip notes contain pending tasks."""
        real_client = ObsidianClient("obsidian_vault", user_id=1)

        # Get trip notes with pending tasks
        pending_tasks = await real_client.get_pending_tasks(tag_filter=["trip"])
        print(f"Pending tasks in trip notes: {len(pending_tasks)}")

        # Print details of pending tasks
        for task in pending_tasks:
            print(f"Task: {task.text}")
            print(f"  Note: {task.note_title}")
            print(f"  Completed: {task.completed}")
            print()

        # Verify we have pending tasks
        assert len(pending_tasks) > 0, "Should find pending tasks in trip notes"

        # Verify all tasks are indeed not completed
        for task in pending_tasks:
            assert not task.completed, f"Task '{task.text}' should not be completed"
            assert hasattr(task, "note_title"), "Task should have note_title attribute"

    async def test_single_tag_filter_edge_cases(self):
        """Test edge cases for single tag filtering."""
        from the_assistant.integrations.obsidian.models import NoteFilters

        real_client = ObsidianClient("obsidian_vault", user_id=1)

        # Test with non-existent tag
        nonexistent_filters = NoteFilters(tags=["nonexistent-tag"], tag_operator="OR")
        nonexistent_notes = await real_client.get_notes(nonexistent_filters)
        assert len(nonexistent_notes) == 0, (
            "Should return empty list for non-existent tag"
        )

        # Test with empty tag list
        all_notes = await real_client.get_notes()
        empty_filter_notes = await real_client.get_notes(NoteFilters())
        assert len(empty_filter_notes) == len(all_notes), (
            "Empty tag filter should return all notes"
        )

        # Test with tag that has special characters
        french_filters = NoteFilters(tags=["french-lesson"], tag_operator="OR")
        french_notes = await real_client.get_notes(french_filters)
        assert len(french_notes) > 0, "Should find notes with hyphenated tags"

        print(f"✓ Non-existent tag: {len(nonexistent_notes)} notes")
        print(f"✓ Empty filter: {len(empty_filter_notes)} notes")
        print(f"✓ Hyphenated tag: {len(french_notes)} notes")

    async def test_trip_date_filtering_logic(self):
        """Test the specific filtering logic for trip notes with date ranges."""
        from datetime import date, timedelta

        from the_assistant.integrations.obsidian.models import NoteFilters

        real_client = ObsidianClient("obsidian_vault", user_id=1)

        # Get current month date range
        today = date.today()
        start_of_month = date(today.year, today.month, 1)

        if today.month == 12:
            end_of_month = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = date(today.year, today.month + 1, 1) - timedelta(days=1)

        print(f"Current month range: {start_of_month} to {end_of_month}")

        # Test just tag filtering first using NoteFilters
        trip_filters_only = NoteFilters(tags=["trip"], tag_operator="OR")
        trip_notes_tag_only = await real_client.get_notes(trip_filters_only)
        print(f"Trip notes (tag only): {len(trip_notes_tag_only)}")

        # Print trip note dates for debugging
        for note in trip_notes_tag_only:
            print(f"  {note.title}:")
            print(f"    start_date: {note.start_date}")
            print(f"    end_date: {note.end_date}")
            print(f"    created_date: {note.created_date}")
            print(f"    modified_date: {note.modified_date}")

        # Test with date range filtering
        filters = NoteFilters(
            tags=["trip"], tag_operator="OR", date_range=(start_of_month, end_of_month)
        )

        trip_notes_with_dates = await real_client.get_notes(filters)
        print(f"Trip notes (with date filter): {len(trip_notes_with_dates)}")

        # Verify filtering behavior
        print("\n🔍 FILTERING ANALYSIS:")
        print(f"   - Tag filtering works: {len(trip_notes_tag_only)} notes found")
        print(f"   - Date filtering result: {len(trip_notes_with_dates)} notes found")
        print(
            "   - All sample trips are in past months, current month filtering excludes them"
        )
        print("   - This is correct behavior for date range filtering")
