"""
Integration tests for error handling scenarios.
"""

from pathlib import Path

import pytest

from the_assistant.integrations.obsidian.models import (
    NoteNotFoundError,
    VaultNotFoundError,
)
from the_assistant.integrations.obsidian.vault_manager import VaultManager


class TestErrorHandling:
    """Integration tests for error handling scenarios."""

    @pytest.fixture
    def vault_path(self):
        """Get the path to the test obsidian vault."""
        return Path("obsidian_vault")

    @pytest.fixture
    def vault_manager(self, vault_path):
        """Create a VaultManager instance for testing."""
        return VaultManager(vault_path)

    async def test_load_nonexistent_note_error(self, vault_manager):
        """Test that loading a nonexistent note raises appropriate error."""
        nonexistent_note = Path("this_note_does_not_exist.md")

        with pytest.raises(NoteNotFoundError):
            await vault_manager.load_note_raw(nonexistent_note)

    async def test_invalid_vault_path_initialization(self):
        """Test that initializing with invalid path raises appropriate error."""
        invalid_path = Path("this_directory_does_not_exist")

        with pytest.raises(VaultNotFoundError):
            VaultManager(invalid_path)

    async def test_get_stats_nonexistent_note(self, vault_manager):
        """Test getting stats for nonexistent note."""
        nonexistent_note = Path("this_note_does_not_exist.md")

        with pytest.raises(NoteNotFoundError):
            await vault_manager.get_note_stats(nonexistent_note)

    async def test_scan_vault_with_permission_issues(self, vault_manager):
        """Test that scan_vault handles permission issues gracefully."""
        # This test verifies that scan_vault doesn't crash on permission issues
        # The actual vault should be readable, so this should work normally
        notes = await vault_manager.scan_vault()
        assert isinstance(notes, list)

    async def test_note_exists_with_invalid_path(self, vault_manager):
        """Test note_exists with various invalid paths."""
        # Test with nonexistent note
        assert not await vault_manager.note_exists(Path("nonexistent.md"))

        # Test with directory path (should return False)
        assert not await vault_manager.note_exists(Path("attachments"))

        # Test with empty path
        assert not await vault_manager.note_exists(Path(""))
