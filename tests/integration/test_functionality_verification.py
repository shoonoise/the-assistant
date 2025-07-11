"""
Comprehensive functionality verification tests to ensure all vault operations
work correctly with the simplified VaultManager implementation.
"""

from pathlib import Path

import pytest

from the_assistant.integrations.obsidian.vault_manager import VaultManager


class TestFunctionalityVerification:
    """Comprehensive tests to verify all vault operations work identically."""

    @pytest.fixture
    def vault_path(self):
        """Get the path to the test obsidian vault."""
        return Path("obsidian_vault")

    @pytest.fixture
    def vault_manager(self, vault_path):
        """Create a VaultManager instance for testing."""
        return VaultManager(vault_path)

    async def test_complete_vault_operations(self, vault_manager):
        """Test a complete set of vault operations."""
        # 1. Scan vault to get all notes
        notes = await vault_manager.scan_vault()
        assert len(notes) > 0, "Should find notes in the vault"

        # 2. Load each note and verify content
        for note_path in notes:
            content = await vault_manager.load_note_raw(note_path)
            assert isinstance(content, str), f"Content should be string for {note_path}"
            assert len(content) > 0, f"Content should not be empty for {note_path}"

            # 3. Get stats for each note
            stats = await vault_manager.get_note_stats(note_path)
            assert isinstance(stats, dict), f"Stats should be dict for {note_path}"
            assert "size" in stats, f"Stats should have size for {note_path}"
            assert "created" in stats, f"Stats should have created date for {note_path}"
            assert "modified" in stats, (
                f"Stats should have modified date for {note_path}"
            )

            # 4. Verify note exists
            assert await vault_manager.note_exists(note_path), (
                f"Note should exist: {note_path}"
            )

        # 5. Get overall vault stats
        vault_stats = await vault_manager.get_vault_stats()
        assert isinstance(vault_stats, dict), "Vault stats should be a dict"
        assert vault_stats["total_notes"] == len(notes), (
            "Total notes should match scan results"
        )
        assert vault_stats["total_size_bytes"] > 0, "Total size should be positive"

    async def test_vault_operations_consistency(self, vault_manager):
        """Test that vault operations are consistent across multiple calls."""
        # Scan vault multiple times and verify consistency
        scan1 = await vault_manager.scan_vault()
        scan2 = await vault_manager.scan_vault()

        assert len(scan1) == len(scan2), (
            "Multiple scans should return same number of notes"
        )
        assert set(scan1) == set(scan2), "Multiple scans should return same notes"

        # Get vault stats multiple times and verify consistency
        stats1 = await vault_manager.get_vault_stats()
        stats2 = await vault_manager.get_vault_stats()

        assert stats1["total_notes"] == stats2["total_notes"], (
            "Stats should be consistent"
        )
        assert stats1["total_size_bytes"] == stats2["total_size_bytes"], (
            "Stats should be consistent"
        )

    async def test_file_operations_work_correctly(self, vault_manager):
        """Test that file operations work correctly with direct file system operations."""
        # Create a temporary test note
        test_note_path = Path("test_functionality_verification.md")
        test_content = (
            "# Test Note\n\nThis is a test note for functionality verification."
        )

        try:
            # Save the test note
            await vault_manager.save_note(test_note_path, test_content)

            # Verify it exists
            assert await vault_manager.note_exists(test_note_path), (
                "Test note should exist after saving"
            )

            # Load and verify content
            loaded_content = await vault_manager.load_note_raw(test_note_path)
            assert loaded_content == test_content, (
                "Loaded content should match saved content"
            )

            # Get stats for the test note
            stats = await vault_manager.get_note_stats(test_note_path)
            assert stats["size"] > 0, "Test note should have positive size"

            # Test that the note exists
            assert await vault_manager.note_exists(test_note_path), (
                "Test note should exist after creation"
            )

        except Exception as e:
            # Clean up in case of error - just log the error since delete_note doesn't exist
            print(f"Error in test cleanup: {e}")
            raise e

    async def test_directory_operations(self, vault_manager):
        """Test directory operations work correctly."""
        test_dir = Path("test_directory")

        try:
            # Create directory
            await vault_manager.create_directory(test_dir)

            # Verify directory exists
            full_path = vault_manager.vault_path / test_dir
            assert full_path.exists(), "Directory should exist after creation"
            assert full_path.is_dir(), "Created path should be a directory"

            # Verify directory was created successfully
            assert full_path.exists(), "Directory should exist after creation"

        finally:
            # Clean up
            full_path = vault_manager.vault_path / test_dir
            if full_path.exists():
                full_path.rmdir()

    async def test_error_handling_unchanged(self, vault_manager):
        """Test that error handling behavior is unchanged."""
        from the_assistant.integrations.obsidian.models import NoteNotFoundError

        # Test loading nonexistent note
        with pytest.raises(NoteNotFoundError):
            await vault_manager.load_note_raw(Path("nonexistent_note.md"))

        # Test getting stats for nonexistent note
        with pytest.raises(NoteNotFoundError):
            await vault_manager.get_note_stats(Path("nonexistent_note.md"))

        # Test that note_exists returns False for nonexistent notes
        assert not await vault_manager.note_exists(Path("nonexistent_note.md"))

        # Test that scan_vault handles empty directories gracefully
        # (This should not raise an exception)
        notes = await vault_manager.scan_vault()
        assert isinstance(notes, list), "Scan should always return a list"
