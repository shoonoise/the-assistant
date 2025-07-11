"""
Unit tests for the VaultManager class.

These tests verify the functionality of the VaultManager class for
file system operations on Obsidian vaults.
"""

import os
from datetime import datetime
from pathlib import Path

import pytest

from the_assistant.integrations.obsidian.models import (
    NoteNotFoundError,
    VaultNotFoundError,
)

# VaultManager uses direct file operations for reliable vault management
from the_assistant.integrations.obsidian.vault_manager import VaultManager


@pytest.fixture
def test_vault_path():
    """Fixture providing the path to the test vault."""
    return Path("obsidian_vault")


@pytest.fixture
def vault_manager(test_vault_path):
    """Fixture providing a VaultManager instance."""
    return VaultManager(test_vault_path)


class TestVaultManager:
    """Tests for the VaultManager class."""

    def test_init_with_valid_path(self, test_vault_path):
        """Test initialization with a valid vault path."""
        manager = VaultManager(test_vault_path)
        assert manager.vault_path == test_vault_path.expanduser().resolve()

    def test_init_with_invalid_path(self):
        """Test initialization with an invalid vault path."""
        with pytest.raises(VaultNotFoundError):
            VaultManager("nonexistent_vault")

    @pytest.mark.asyncio
    async def test_scan_vault(self, vault_manager):
        """Test scanning the vault for Markdown files."""
        note_paths = await vault_manager.scan_vault()

        # Verify we found some notes
        assert len(note_paths) > 0

        # Verify all paths are .md files
        for path in note_paths:
            assert path.suffix == ".md"

    @pytest.mark.asyncio
    async def test_load_note_raw(self, vault_manager):
        """Test loading raw content of a note."""
        # Use a known note from the test vault
        content = await vault_manager.load_note_raw("Trip to Paris.md")

        # Verify content was loaded
        assert content
        assert "Trip to Paris" in content
        assert "tags:" in content
        assert "france" in content

    @pytest.mark.asyncio
    async def test_load_nonexistent_note(self, vault_manager):
        """Test loading a note that doesn't exist."""
        with pytest.raises(NoteNotFoundError):
            await vault_manager.load_note_raw("NonexistentNote.md")

    @pytest.mark.asyncio
    async def test_get_note_stats(self, vault_manager):
        """Test getting statistics for a note."""
        # Use a known note from the test vault
        stats = await vault_manager.get_note_stats("Trip to Paris.md")

        # Verify stats were retrieved
        assert stats
        assert "size" in stats
        assert stats["size"] > 0
        assert "created" in stats
        assert isinstance(stats["created"], datetime)
        assert "modified" in stats
        assert isinstance(stats["modified"], datetime)
        assert "filename" in stats
        assert stats["filename"] == "Trip to Paris.md"

    @pytest.mark.asyncio
    async def test_note_exists(self, vault_manager):
        """Test checking if a note exists."""
        # Test with existing note
        assert await vault_manager.note_exists("Trip to Paris.md")

        # Test with nonexistent note
        assert not await vault_manager.note_exists("NonexistentNote.md")

    @pytest.mark.asyncio
    async def test_get_vault_stats(self, vault_manager):
        """Test getting statistics for the entire vault."""
        stats = await vault_manager.get_vault_stats()

        # Verify stats were retrieved
        assert stats
        assert "total_notes" in stats
        assert stats["total_notes"] > 0
        assert "total_size_bytes" in stats
        assert stats["total_size_bytes"] > 0
        assert "vault_path" in stats

    @pytest.mark.asyncio
    async def test_create_directory(self, vault_manager):
        """Test creating a directory in the vault."""
        test_dir = "test_directory_temp"

        try:
            # Create directory
            success = await vault_manager.create_directory(test_dir)
            assert success

            # Verify directory exists
            dir_path = vault_manager._resolve_path(test_dir)
            assert dir_path.exists()
            assert dir_path.is_dir()

        finally:
            # Clean up
            dir_path = vault_manager._resolve_path(test_dir)
            if dir_path.exists():
                os.rmdir(dir_path)
