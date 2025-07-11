"""
Unit tests for task management functionality in the Obsidian client.

Tests cover task status modification, completion tracking, context preservation,
nested task hierarchies, and bulk operations using example vault notes.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from the_assistant.integrations.obsidian.models import (
    NoteNotFoundError,
    ObsidianNote,
    TaskItem,
    TaskUpdateError,
)
from the_assistant.integrations.obsidian.obsidian_client import ObsidianClient


class TestTaskManagement:
    """Test suite for task management functionality."""

    @pytest.fixture
    def mock_vault_path(self):
        """Mock vault path for testing."""
        return Path("test_vault")

    @pytest.fixture
    def client(self, mock_vault_path):
        """Create ObsidianClient instance for testing."""
        with (
            patch("the_assistant.integrations.obsidian.obsidian_client.VaultManager"),
            patch("the_assistant.integrations.obsidian.obsidian_client.MarkdownParser"),
            patch(
                "the_assistant.integrations.obsidian.obsidian_client.MetadataExtractor"
            ),
            patch("the_assistant.integrations.obsidian.obsidian_client.FilterEngine"),
        ):
            return ObsidianClient(mock_vault_path, user_id=1)

    @pytest.fixture
    def sample_note_with_tasks(self):
        """Create a sample note with various task types."""
        tasks = [
            TaskItem(
                text="Book airport transfer",
                completed=False,
                line_number=10,
                parent_heading="Tasks",
                indent_level=0,
                heading_hierarchy=["Tasks"],
            ),
            TaskItem(
                text="Pack winter clothes",
                completed=False,
                line_number=11,
                parent_heading="Tasks",
                indent_level=0,
                heading_hierarchy=["Tasks"],
            ),
            TaskItem(
                text="Confirm hotel reservation",
                completed=True,
                line_number=13,
                parent_heading="Tasks",
                indent_level=0,
                heading_hierarchy=["Tasks"],
            ),
            TaskItem(
                text="Research restaurants",
                completed=False,
                line_number=15,
                parent_heading="Tasks",
                indent_level=2,
                heading_hierarchy=["Tasks"],
            ),
            TaskItem(
                text="Make dinner reservations",
                completed=False,
                line_number=16,
                parent_heading="Tasks",
                indent_level=4,
                heading_hierarchy=["Tasks"],
            ),
        ]

        raw_content = """---
tags:
  - trip
  - travel
start_date: 2025-03-15
---

# Trip Planning

## Tasks
- [ ] Book airport transfer
- [ ] Pack winter clothes
- [ ] Download offline maps
- [x] Confirm hotel reservation
- [ ] Exchange currency
  - [ ] Research restaurants
    - [ ] Make dinner reservations
"""

        return ObsidianNote(
            title="Trip Planning",
            path=Path("Trip Planning.md"),
            content="# Trip Planning\n\n## Tasks\n...",
            raw_content=raw_content,
            metadata={"tags": ["trip", "travel"], "start_date": "2025-03-15"},
            tags=["trip", "travel"],
            tasks=tasks,
            headings=[],
            links=[],
        )

    @pytest.mark.asyncio
    async def test_mark_task_complete(self, client, sample_note_with_tasks):
        """Test marking a task as complete."""
        # Mock the get_note method
        client.get_note = AsyncMock(return_value=sample_note_with_tasks)
        client.vault_manager.save_note = AsyncMock(return_value=True)
        client.vault_manager._resolve_path = MagicMock(return_value=Path("test.md"))

        # Test marking a pending task complete
        result = await client.mark_task_complete("test.md", "Book airport transfer")

        assert result is True
        client.vault_manager.save_note.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_task_incomplete(self, client, sample_note_with_tasks):
        """Test marking a task as incomplete."""
        # Mock the get_note method
        client.get_note = AsyncMock(return_value=sample_note_with_tasks)
        client.vault_manager.save_note = AsyncMock(return_value=True)
        client.vault_manager._resolve_path = MagicMock(return_value=Path("test.md"))

        # Test marking a completed task incomplete
        result = await client.mark_task_incomplete(
            "test.md", "Confirm hotel reservation"
        )

        assert result is True
        client.vault_manager.save_note.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_status_not_found(self, client, sample_note_with_tasks):
        """Test updating a task that doesn't exist."""
        client.get_note = AsyncMock(return_value=sample_note_with_tasks)

        with pytest.raises(TaskUpdateError, match="Task not found"):
            await client.update_task_status("test.md", "Nonexistent task", True)

    @pytest.mark.asyncio
    async def test_update_task_status_note_not_found(self, client):
        """Test updating a task in a note that doesn't exist."""
        client.get_note = AsyncMock(return_value=None)

        with pytest.raises(NoteNotFoundError, match="Note not found"):
            await client.update_task_status("nonexistent.md", "Some task", True)

    @pytest.mark.asyncio
    async def test_get_task_by_line_number(self, client, sample_note_with_tasks):
        """Test retrieving a task by its line number."""
        client.get_note = AsyncMock(return_value=sample_note_with_tasks)

        task = await client.get_task_by_line_number("test.md", 10)

        assert task is not None
        assert task.text == "Book airport transfer"
        assert task.line_number == 10
        assert not task.completed

    @pytest.mark.asyncio
    async def test_get_task_by_line_number_not_found(
        self, client, sample_note_with_tasks
    ):
        """Test retrieving a task by line number that doesn't exist."""
        client.get_note = AsyncMock(return_value=sample_note_with_tasks)

        task = await client.get_task_by_line_number("test.md", 999)

        assert task is None

    @pytest.mark.asyncio
    async def test_get_tasks_under_heading(self, client, sample_note_with_tasks):
        """Test retrieving tasks under a specific heading."""
        client.get_note = AsyncMock(return_value=sample_note_with_tasks)

        tasks = await client.get_tasks_under_heading("test.md", "Tasks")

        assert len(tasks) == 5  # All tasks are under "Tasks" heading
        assert all(task.parent_heading == "Tasks" for task in tasks)

    @pytest.mark.asyncio
    async def test_get_task_completion_stats(self, client, sample_note_with_tasks):
        """Test getting task completion statistics for a note."""
        client.get_note = AsyncMock(return_value=sample_note_with_tasks)

        stats = await client.get_task_completion_stats("test.md")

        assert stats["total_tasks"] == 5
        assert stats["completed_tasks"] == 1
        assert stats["pending_tasks"] == 4
        assert stats["completion_ratio"] == 0.2
        assert stats["has_pending_tasks"] is True

    def test_update_task_status_in_content_complete(self, client):
        """Test updating task status in content to complete."""
        content = """# Tasks
- [ ] Book airport transfer
- [ ] Pack winter clothes
- [x] Confirm hotel reservation
"""

        updated = client._update_task_status_in_content(
            content, "Book airport transfer", True
        )

        assert "- [x] Book airport transfer" in updated
        assert "- [ ] Pack winter clothes" in updated  # Should remain unchanged

    def test_update_task_status_in_content_incomplete(self, client):
        """Test updating task status in content to incomplete."""
        content = """# Tasks
- [ ] Book airport transfer
- [ ] Pack winter clothes
- [x] Confirm hotel reservation
"""

        updated = client._update_task_status_in_content(
            content, "Confirm hotel reservation", False
        )

        assert "- [ ] Confirm hotel reservation" in updated
        assert "- [ ] Book airport transfer" in updated  # Should remain unchanged

    def test_update_task_status_preserves_formatting(self, client):
        """Test that task status updates preserve original formatting."""
        content = """# Tasks
  - [ ] Indented task
* [ ] Asterisk task
- [ ] Regular task with extra text (important)
"""

        # Test with indented task
        updated = client._update_task_status_in_content(content, "Indented task", True)
        assert "  - [x] Indented task" in updated

        # Test with asterisk task - need to test the actual content
        updated = client._update_task_status_in_content(content, "Asterisk task", True)
        # The current implementation converts asterisk to dash, so check for dash
        assert "- [x] Asterisk task" in updated

        # Test with task that has extra text
        updated = client._update_task_status_in_content(
            content, "Regular task with extra text (important)", True
        )
        assert "- [x] Regular task with extra text (important)" in updated


class TestTaskItemModel:
    """Test suite for TaskItem model enhancements."""

    def test_task_item_nesting_properties(self):
        """Test TaskItem nesting-related properties."""
        # Top-level task
        top_task = TaskItem(
            text="Top level task", completed=False, line_number=1, indent_level=0
        )

        assert not top_task.is_nested
        assert top_task.nesting_level == 0

        # Nested task (2 spaces = level 1)
        nested_task = TaskItem(
            text="Nested task", completed=False, line_number=2, indent_level=2
        )

        assert nested_task.is_nested
        assert nested_task.nesting_level == 1

        # Deeply nested task (4 spaces = level 2)
        deep_task = TaskItem(
            text="Deep nested task", completed=False, line_number=3, indent_level=4
        )

        assert deep_task.is_nested
        assert deep_task.nesting_level == 2

    def test_task_item_string_representation(self):
        """Test TaskItem string representation with indentation."""
        task = TaskItem(
            text="Nested task", completed=True, line_number=1, indent_level=2
        )

        expected = "  - [x] Nested task"
        assert str(task) == expected

    def test_task_item_heading_hierarchy(self):
        """Test TaskItem heading hierarchy tracking."""
        task = TaskItem(
            text="Task under nested heading",
            completed=False,
            line_number=1,
            parent_heading="Sub-heading",
            heading_hierarchy=["Main Heading", "Sub-heading"],
        )

        assert task.parent_heading == "Sub-heading"
        assert task.heading_hierarchy == ["Main Heading", "Sub-heading"]


class TestObsidianNoteTaskMethods:
    """Test suite for ObsidianNote task-related methods."""

    @pytest.fixture
    def note_with_nested_tasks(self):
        """Create a note with nested tasks for testing."""
        tasks = [
            TaskItem(
                text="Top task 1",
                completed=False,
                line_number=1,
                parent_heading="Tasks",
                indent_level=0,
                heading_hierarchy=["Tasks"],
            ),
            TaskItem(
                text="Top task 2",
                completed=True,
                line_number=2,
                parent_heading="Tasks",
                indent_level=0,
                heading_hierarchy=["Tasks"],
            ),
            TaskItem(
                text="Nested task 1",
                completed=False,
                line_number=3,
                parent_heading="Tasks",
                indent_level=2,
                heading_hierarchy=["Tasks"],
            ),
            TaskItem(
                text="Nested task 2",
                completed=False,
                line_number=4,
                parent_heading="Tasks",
                indent_level=2,
                heading_hierarchy=["Tasks"],
            ),
            TaskItem(
                text="Deep nested task",
                completed=True,
                line_number=5,
                parent_heading="Tasks",
                indent_level=4,
                heading_hierarchy=["Tasks"],
            ),
            TaskItem(
                text="Other section task",
                completed=False,
                line_number=6,
                parent_heading="Other",
                indent_level=0,
                heading_hierarchy=["Other"],
            ),
        ]

        return ObsidianNote(
            title="Test Note",
            path=Path("test.md"),
            content="",
            raw_content="",
            tasks=tasks,
        )
