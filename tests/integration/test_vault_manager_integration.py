"""
Integration tests for VaultManager with actual obsidian_vault directory.
"""

from pathlib import Path

import pytest

from the_assistant.integrations.obsidian.vault_manager import VaultManager


class TestVaultManagerIntegration:
    """Integration tests for VaultManager using the actual obsidian_vault directory."""

    @pytest.fixture
    def vault_path(self):
        """Get the path to the test obsidian vault."""
        return Path("obsidian_vault")

    @pytest.fixture
    def vault_manager(self, vault_path):
        """Create a VaultManager instance for testing."""
        return VaultManager(vault_path)

    async def test_scan_vault_with_real_files(self, vault_manager):
        """Test scanning the actual vault directory."""
        notes = await vault_manager.scan_vault()

        # Should find markdown files
        assert len(notes) > 0

        # All returned items should be Path objects
        for note in notes:
            assert isinstance(note, Path)
            assert note.suffix == ".md"

    async def test_load_existing_note(self, vault_manager):
        """Test loading an existing note from the vault."""
        # First scan to get available notes
        notes = await vault_manager.scan_vault()
        assert len(notes) > 0

        # Load the first note
        first_note = notes[0]
        content = await vault_manager.load_note_raw(first_note)

        # Should return string content
        assert isinstance(content, str)
        assert len(content) > 0

    async def test_get_note_stats(self, vault_manager):
        """Test getting statistics for an existing note."""
        # First scan to get available notes
        notes = await vault_manager.scan_vault()
        assert len(notes) > 0

        # Get stats for the first note
        first_note = notes[0]
        stats = await vault_manager.get_note_stats(first_note)

        # Should return a dictionary with expected keys
        assert isinstance(stats, dict)
        assert "size" in stats
        assert "created" in stats
        assert "modified" in stats

    async def test_note_exists(self, vault_manager):
        """Test checking if notes exist."""
        # First scan to get available notes
        notes = await vault_manager.scan_vault()
        assert len(notes) > 0

        # Check that existing note exists
        first_note = notes[0]
        assert await vault_manager.note_exists(first_note)

        # Check that non-existent note doesn't exist
        fake_note = Path("nonexistent_note.md")
        assert not await vault_manager.note_exists(fake_note)

    async def test_get_vault_stats(self, vault_manager):
        """Test getting overall vault statistics."""
        stats = await vault_manager.get_vault_stats()

        # Should return a dictionary with expected structure
        assert isinstance(stats, dict)
        assert "total_notes" in stats
        assert "total_size_bytes" in stats
        assert stats["total_notes"] > 0
        assert stats["total_size_bytes"] > 0
