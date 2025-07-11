"""
Unit tests for ObsidianClient note CRUD operations.

Tests note creation, modification, appending, and metadata handling
using the example vault notes as test data.
"""

import shutil
import tempfile
from datetime import date
from pathlib import Path

import pytest

from the_assistant.integrations.obsidian.models import (
    NoteNotFoundError,
    ObsidianClientError,
    VaultNotFoundError,
)
from the_assistant.integrations.obsidian.obsidian_client import ObsidianClient


class TestObsidianClientCRUD:
    """Test suite for ObsidianClient CRUD operations."""

    @pytest.fixture
    def temp_vault_path(self):
        """Create a temporary vault directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def example_vault_path(self):
        """Path to the example vault for testing."""
        return Path("obsidian_vault")

    @pytest.fixture
    async def client_with_temp_vault(self, temp_vault_path):
        """ObsidianClient instance with temporary vault."""
        return ObsidianClient(temp_vault_path, user_id=1)

    @pytest.fixture
    async def client_with_example_vault(self, example_vault_path):
        """ObsidianClient instance with example vault."""
        return ObsidianClient(example_vault_path, user_id=1)

    # Note Creation Tests

    async def test_create_note_basic(self, client_with_temp_vault):
        """Test basic note creation with title and content."""
        title = "Test Note"
        content = "This is a test note with some content."

        created_note = await client_with_temp_vault.create_note(title, content)

        assert created_note.title == title
        assert created_note.content == content
        assert created_note.path.name == "Test Note.md"
        assert created_note.metadata == {}
        assert created_note.tags == []

    async def test_create_note_with_metadata(self, client_with_temp_vault):
        """Test note creation with YAML frontmatter metadata."""
        title = "Note with Metadata"
        content = "Content with metadata."
        metadata = {
            "tags": ["test", "example"],
            "start_date": "2024-01-15",
            "status": "active",
            "priority": 1,
        }

        created_note = await client_with_temp_vault.create_note(
            title, content, metadata
        )

        assert created_note.title == title
        assert created_note.content == content
        assert "test" in created_note.tags
        assert "example" in created_note.tags
        assert created_note.metadata["status"] == "active"
        assert created_note.metadata["priority"] == 1
        assert created_note.start_date == date(2024, 1, 15)

    async def test_create_note_with_custom_path(self, client_with_temp_vault):
        """Test note creation with custom file path."""
        title = "Custom Path Note"
        content = "Note with custom path."
        custom_path = "subfolder/custom-note.md"

        created_note = await client_with_temp_vault.create_note(
            title, content, path=custom_path
        )

        assert (
            created_note.title == "custom-note"
        )  # Title comes from filename when custom path is used
        assert created_note.path.name == "custom-note.md"
        assert "subfolder" in str(created_note.path)

    async def test_create_note_sanitizes_filename(self, client_with_temp_vault):
        """Test that invalid filename characters are sanitized."""
        title = 'Invalid<>:"/\\|?*Filename'
        content = "Content for invalid filename."

        created_note = await client_with_temp_vault.create_note(title, content)

        # Should sanitize invalid characters
        assert "<" not in created_note.path.name
        assert ">" not in created_note.path.name
        assert ":" not in created_note.path.name
        assert "_" in created_note.path.name  # Replaced with underscores

    async def test_create_note_duplicate_path_fails(self, client_with_temp_vault):
        """Test that creating a note with existing path fails."""
        title = "Duplicate Note"
        content = "First note."

        # Create first note
        await client_with_temp_vault.create_note(title, content)

        # Attempt to create duplicate should fail
        with pytest.raises(ObsidianClientError, match="Note already exists"):
            await client_with_temp_vault.create_note(title, content)

    async def test_create_note_with_tasks(self, client_with_temp_vault):
        """Test creating a note with task items in content."""
        title = "Note with Tasks"
        content = """# Todo List

- [ ] First task
- [x] Completed task
- [ ] Another pending task
"""

        created_note = await client_with_temp_vault.create_note(title, content)

        assert len(created_note.tasks) == 3
        assert len(created_note.pending_tasks) == 2
        assert len(created_note.completed_tasks) == 1
        assert created_note.tasks[0].text == "First task"
        assert not created_note.tasks[0].completed
        assert created_note.tasks[1].completed

    # Note Update Tests

    async def test_update_note_content_only(self, client_with_temp_vault):
        """Test updating note content while preserving metadata."""
        # Create initial note
        title = "Update Test"
        initial_content = "Initial content."
        metadata = {"tags": ["test"], "status": "draft"}

        created_note = await client_with_temp_vault.create_note(
            title, initial_content, metadata
        )

        # Update content
        new_content = "Updated content with more information."
        success = await client_with_temp_vault.update_note(
            created_note.path, content=new_content
        )

        assert success

        # Verify update
        updated_note = await client_with_temp_vault.get_note(created_note.path)
        assert updated_note.content == new_content
        assert updated_note.metadata["status"] == "draft"  # Metadata preserved
        assert "test" in updated_note.tags

    async def test_update_note_metadata_only(self, client_with_temp_vault):
        """Test updating note metadata while preserving content."""
        # Create initial note
        title = "Metadata Update Test"
        content = "Content that should remain unchanged."
        initial_metadata = {"status": "draft", "priority": 1}

        created_note = await client_with_temp_vault.create_note(
            title, content, initial_metadata
        )

        # Update metadata
        metadata_updates = {"status": "published", "tags": ["updated"]}
        success = await client_with_temp_vault.update_note(
            created_note.path, metadata=metadata_updates
        )

        assert success

        # Verify update
        updated_note = await client_with_temp_vault.get_note(created_note.path)
        assert updated_note.content == content  # Content preserved
        assert updated_note.metadata["status"] == "published"  # Updated
        assert updated_note.metadata["priority"] == 1  # Preserved
        assert "updated" in updated_note.tags

    async def test_update_note_both_content_and_metadata(self, client_with_temp_vault):
        """Test updating both content and metadata simultaneously."""
        # Create initial note
        title = "Full Update Test"
        initial_content = "Initial content."
        initial_metadata = {"status": "draft"}

        created_note = await client_with_temp_vault.create_note(
            title, initial_content, initial_metadata
        )

        # Update both
        new_content = "Completely new content."
        metadata_updates = {"status": "published", "tags": ["updated", "complete"]}
        success = await client_with_temp_vault.update_note(
            created_note.path, content=new_content, metadata=metadata_updates
        )

        assert success

        # Verify update
        updated_note = await client_with_temp_vault.get_note(created_note.path)
        assert updated_note.content == new_content
        assert updated_note.metadata["status"] == "published"
        assert "updated" in updated_note.tags
        assert "complete" in updated_note.tags

    async def test_update_nonexistent_note_fails(self, client_with_temp_vault):
        """Test that updating a non-existent note fails."""
        with pytest.raises(NoteNotFoundError, match="Note not found"):
            await client_with_temp_vault.update_note(
                "nonexistent.md", content="New content"
            )

    # Content Appending Tests

    async def test_append_to_note(self, client_with_temp_vault):
        """Test appending content to an existing note."""
        # Create initial note
        title = "Append Test"
        initial_content = "Initial content."

        created_note = await client_with_temp_vault.create_note(title, initial_content)

        # Append content
        append_content = "This is appended content."
        success = await client_with_temp_vault.append_to_note(
            created_note.path, append_content
        )

        assert success

        # Verify append
        updated_note = await client_with_temp_vault.get_note(created_note.path)
        expected_content = "Initial content.\n\nThis is appended content."
        assert updated_note.content == expected_content

    async def test_append_with_custom_separator(self, client_with_temp_vault):
        """Test appending content with custom separator."""
        # Create initial note
        title = "Custom Separator Test"
        initial_content = "Line 1"

        created_note = await client_with_temp_vault.create_note(title, initial_content)

        # Append with custom separator
        append_content = "Line 2"
        success = await client_with_temp_vault.append_to_note(
            created_note.path, append_content, separator="\n"
        )

        assert success

        # Verify append
        updated_note = await client_with_temp_vault.get_note(created_note.path)
        expected_content = "Line 1\nLine 2"
        assert updated_note.content == expected_content

    async def test_prepend_to_note(self, client_with_temp_vault):
        """Test prepending content to an existing note."""
        # Create initial note
        title = "Prepend Test"
        initial_content = "Original content."

        created_note = await client_with_temp_vault.create_note(title, initial_content)

        # Prepend content
        prepend_content = "This comes first."
        success = await client_with_temp_vault.prepend_to_note(
            created_note.path, prepend_content
        )

        assert success

        # Verify prepend
        updated_note = await client_with_temp_vault.get_note(created_note.path)
        expected_content = "This comes first.\n\nOriginal content."
        assert updated_note.content == expected_content

    async def test_append_preserves_metadata(self, client_with_temp_vault):
        """Test that appending content preserves existing metadata."""
        # Create note with metadata
        title = "Metadata Preservation Test"
        initial_content = "Initial content."
        metadata = {"tags": ["important"], "status": "active"}

        created_note = await client_with_temp_vault.create_note(
            title, initial_content, metadata
        )

        # Append content
        append_content = "Additional content."
        success = await client_with_temp_vault.append_to_note(
            created_note.path, append_content
        )

        assert success

        # Verify metadata is preserved
        updated_note = await client_with_temp_vault.get_note(created_note.path)
        assert updated_note.metadata["status"] == "active"
        assert "important" in updated_note.tags
        assert "Initial content." in updated_note.content
        assert "Additional content." in updated_note.content

    # Metadata Merging Tests

    async def test_metadata_merge_adds_new_fields(self, client_with_temp_vault):
        """Test that metadata merging adds new fields."""
        # Create note with initial metadata
        title = "Merge Test"
        content = "Content for merge test."
        initial_metadata = {"status": "draft", "priority": 1}

        created_note = await client_with_temp_vault.create_note(
            title, content, initial_metadata
        )

        # Update with additional metadata
        new_metadata = {"author": "Test User", "category": "testing"}
        success = await client_with_temp_vault.update_note(
            created_note.path, metadata=new_metadata
        )

        assert success

        # Verify merge
        updated_note = await client_with_temp_vault.get_note(created_note.path)
        assert updated_note.metadata["status"] == "draft"  # Preserved
        assert updated_note.metadata["priority"] == 1  # Preserved
        assert updated_note.metadata["author"] == "Test User"  # Added
        assert updated_note.metadata["category"] == "testing"  # Added

    async def test_metadata_merge_overwrites_existing_fields(
        self, client_with_temp_vault
    ):
        """Test that metadata merging overwrites existing fields."""
        # Create note with initial metadata
        title = "Overwrite Test"
        content = "Content for overwrite test."
        initial_metadata = {"status": "draft", "priority": 1}

        created_note = await client_with_temp_vault.create_note(
            title, content, initial_metadata
        )

        # Update existing fields
        new_metadata = {"status": "published", "priority": 5}
        success = await client_with_temp_vault.update_note(
            created_note.path, metadata=new_metadata
        )

        assert success

        # Verify overwrite
        updated_note = await client_with_temp_vault.get_note(created_note.path)
        assert updated_note.metadata["status"] == "published"  # Overwritten
        assert updated_note.metadata["priority"] == 5  # Overwritten

    async def test_metadata_merge_combines_tags(self, client_with_temp_vault):
        """Test that metadata merging combines tag lists."""
        # Create note with initial tags
        title = "Tag Merge Test"
        content = "Content for tag merge test."
        initial_metadata = {"tags": ["initial", "test"]}

        created_note = await client_with_temp_vault.create_note(
            title, content, initial_metadata
        )

        # Add more tags
        new_metadata = {"tags": ["additional", "merged"]}
        success = await client_with_temp_vault.update_note(
            created_note.path, metadata=new_metadata
        )

        assert success

        # Verify tag combination
        updated_note = await client_with_temp_vault.get_note(created_note.path)
        expected_tags = {"initial", "test", "additional", "merged"}
        assert set(updated_note.tags) == expected_tags

    # Error Handling Tests

    async def test_create_note_invalid_vault_path(self):
        """Test that invalid vault path raises appropriate error."""
        with pytest.raises(VaultNotFoundError):
            ObsidianClient("/nonexistent/vault/path", user_id=1)

    async def test_append_to_nonexistent_note_fails(self, client_with_temp_vault):
        """Test that appending to non-existent note fails."""
        with pytest.raises(NoteNotFoundError, match="Note not found"):
            await client_with_temp_vault.append_to_note("nonexistent.md", "Content")

    async def test_prepend_to_nonexistent_note_fails(self, client_with_temp_vault):
        """Test that prepending to non-existent note fails."""
        with pytest.raises(NoteNotFoundError, match="Note not found"):
            await client_with_temp_vault.prepend_to_note("nonexistent.md", "Content")

    # Integration Tests with Example Vault

    async def test_read_existing_note_from_example_vault(
        self, client_with_example_vault
    ):
        """Test reading an existing note from the example vault."""
        # Try to read a known note from the example vault
        note = await client_with_example_vault.get_note("Trip to Paris.md")

        if note:  # Only test if the note exists
            assert note.title == "Trip to Paris"
            assert note.path.name == "Trip to Paris.md"
            assert isinstance(note.metadata, dict)
            assert isinstance(note.tags, list)

    async def test_create_note_in_example_vault_temp_copy(self, temp_vault_path):
        """Test creating a note in a copy of the example vault."""
        # Copy example vault to temp location for testing
        example_vault = Path("obsidian_vault")
        if example_vault.exists():
            shutil.copytree(example_vault, temp_vault_path / "vault_copy")

            client = ObsidianClient(temp_vault_path / "vault_copy", user_id=1)

            # Create a new note
            title = "Test Note in Copy"
            content = "This is a test note created in the vault copy."
            metadata = {"tags": ["test"], "created_by": "unit_test"}

            created_note = await client.create_note(title, content, metadata)

            assert created_note.title == title
            assert created_note.content == content
            assert "test" in created_note.tags
            assert created_note.metadata["created_by"] == "unit_test"

    # Performance and Edge Case Tests

    async def test_create_note_empty_content(self, client_with_temp_vault):
        """Test creating a note with empty content."""
        title = "Empty Note"
        content = ""

        created_note = await client_with_temp_vault.create_note(title, content)

        assert created_note.title == title
        assert created_note.content == ""
        assert created_note.path.name == "Empty Note.md"

    async def test_create_note_only_metadata(self, client_with_temp_vault):
        """Test creating a note with only metadata and no content."""
        title = "Metadata Only"
        metadata = {"type": "template", "tags": ["empty"]}

        created_note = await client_with_temp_vault.create_note(title, "", metadata)

        assert created_note.title == title
        assert created_note.content == ""
        assert created_note.metadata["type"] == "template"
        assert "empty" in created_note.tags

    async def test_update_note_with_special_characters(self, client_with_temp_vault):
        """Test updating note content with special characters and unicode."""
        # Create initial note
        title = "Unicode Test"
        initial_content = "Initial content."

        created_note = await client_with_temp_vault.create_note(title, initial_content)

        # Update with special characters
        new_content = "Content with émojis 🚀 and spëcial chäractërs: ñ, ü, ß"
        success = await client_with_temp_vault.update_note(
            created_note.path, content=new_content
        )

        assert success

        # Verify special characters are preserved
        updated_note = await client_with_temp_vault.get_note(created_note.path)
        assert updated_note.content == new_content
        assert "🚀" in updated_note.content
        assert "émojis" in updated_note.content
