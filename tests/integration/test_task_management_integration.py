"""
Integration tests for task management functionality using the example vault.

These tests verify that task management works correctly with real Obsidian notes
from the obsidian_vault directory, testing the complete process from parsing
to task status updates.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from the_assistant.integrations.obsidian.models import (
    TaskUpdateError,
)
from the_assistant.integrations.obsidian.obsidian_client import ObsidianClient


class TestTaskManagementIntegration:
    """Integration tests for task management with real vault notes."""

    @pytest.fixture
    def temp_vault_path(self):
        """Create a temporary copy of the example vault for testing."""
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp())

        # Copy example vault to temp directory
        source_vault = Path("obsidian_vault")
        if source_vault.exists():
            shutil.copytree(source_vault, temp_dir / "vault")
            yield temp_dir / "vault"
        else:
            # If obsidian_vault doesn't exist, create minimal test structure
            vault_dir = temp_dir / "vault"
            vault_dir.mkdir()

            # Create a test note with tasks
            test_note = vault_dir / "Test Tasks.md"
            test_note.write_text("""---
tags:
  - test
  - tasks
date: 2025-01-15
---

# Test Tasks

## To Do
- [ ] First task
- [ ] Second task
- [x] Completed task
- [ ] Fourth task

## Notes
Some additional content here.
""")
            yield vault_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    async def client(self, temp_vault_path):
        """Create ObsidianClient instance with temporary vault."""
        return ObsidianClient(temp_vault_path, user_id=1)

    @pytest.mark.asyncio
    async def test_parse_tasks_from_real_notes(self, client):
        """Test parsing tasks from real vault notes."""
        # Get all notes
        notes = await client.get_notes()

        # Should have at least one note
        assert len(notes) > 0

        # Find notes with tasks
        notes_with_tasks = [note for note in notes if note.tasks]

        # Should have at least one note with tasks
        assert len(notes_with_tasks) > 0

        # Verify task parsing
        for note in notes_with_tasks:
            print(f"Note: {note.title}")
            print(f"Tasks: {len(note.tasks)}")
            for task in note.tasks:
                print(
                    f"  - [{('x' if task.completed else ' ')}] {task.text} (line {task.line_number})"
                )

            # Verify task properties
            for task in note.tasks:
                assert isinstance(task.text, str)
                assert isinstance(task.completed, bool)
                assert isinstance(task.line_number, int)
                assert task.line_number > 0

    @pytest.mark.asyncio
    async def test_get_pending_tasks_from_vault(self, client):
        """Test getting pending tasks from the entire vault."""
        pending_tasks = await client.get_pending_tasks()

        # Should have some pending tasks
        assert len(pending_tasks) > 0

        # All returned tasks should be incomplete
        for task in pending_tasks:
            assert not task.completed
            assert isinstance(task.text, str)
            assert len(task.text.strip()) > 0

    @pytest.mark.asyncio
    async def test_task_completion_stats(self, client):
        """Test getting task completion statistics."""
        # Get vault-wide stats
        vault_stats = await client.get_all_task_completion_stats()

        assert "total_notes" in vault_stats
        assert "notes_with_tasks" in vault_stats
        assert "total_tasks" in vault_stats
        assert "completed_tasks" in vault_stats
        assert "pending_tasks" in vault_stats
        assert "completion_ratio" in vault_stats

        # Verify consistency
        assert (
            vault_stats["total_tasks"]
            == vault_stats["completed_tasks"] + vault_stats["pending_tasks"]
        )

        if vault_stats["total_tasks"] > 0:
            expected_ratio = vault_stats["completed_tasks"] / vault_stats["total_tasks"]
            assert abs(vault_stats["completion_ratio"] - expected_ratio) < 0.001

    @pytest.mark.asyncio
    async def test_mark_task_complete_integration(self, client):
        """Test marking a task complete in a real note."""
        # Get a note with pending tasks
        notes = await client.get_notes()
        note_with_pending = None
        pending_task = None

        for note in notes:
            if note.pending_tasks:
                note_with_pending = note
                pending_task = note.pending_tasks[0]
                break

        if not note_with_pending or not pending_task:
            pytest.skip("No notes with pending tasks found")

        # Mark the task complete
        success = await client.mark_task_complete(
            note_with_pending.path, pending_task.text
        )

        assert success is True

        # Reload the note and verify the task is now complete
        updated_note = await client.get_note(note_with_pending.path)

        # Find the updated task
        updated_task = None
        for task in updated_note.tasks:
            if task.text.strip() == pending_task.text.strip():
                updated_task = task
                break

        assert updated_task is not None
        assert updated_task.completed is True

    @pytest.mark.asyncio
    async def test_mark_task_incomplete_integration(self, client):
        """Test marking a task incomplete in a real note."""
        # Get a note with completed tasks
        notes = await client.get_notes()
        note_with_completed = None
        completed_task = None

        for note in notes:
            if note.completed_tasks:
                note_with_completed = note
                completed_task = note.completed_tasks[0]
                break

        if not note_with_completed or not completed_task:
            pytest.skip("No notes with completed tasks found")

        # Mark the task incomplete
        success = await client.mark_task_incomplete(
            note_with_completed.path, completed_task.text
        )

        assert success is True

        # Reload the note and verify the task is now incomplete
        updated_note = await client.get_note(note_with_completed.path)

        # Find the updated task
        updated_task = None
        for task in updated_note.tasks:
            if task.text.strip() == completed_task.text.strip():
                updated_task = task
                break

        assert updated_task is not None
        assert updated_task.completed is False

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, client):
        """Test error handling with real vault operations."""
        from the_assistant.integrations.obsidian.models import NoteNotFoundError

        # Test with non-existent note
        with pytest.raises(NoteNotFoundError):
            await client.update_task_status("nonexistent.md", "Some task", True)

        # Test with non-existent task in existing note
        notes = await client.get_notes()
        if notes:
            first_note = notes[0]
            with pytest.raises(TaskUpdateError):
                await client.update_task_status(
                    first_note.path, "This task definitely does not exist", True
                )
