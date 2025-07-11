"""
VaultManager for Obsidian vault file system operations.

This module provides functionality to scan, load, and save Obsidian notes
using direct file system operations with proper encoding, error handling,
and metadata tracking.
"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .exceptions import NoteNotFoundError, VaultNotFoundError


class VaultManager:
    """
    Handles file system operations for Obsidian vault using direct file operations.

    Provides methods for scanning vault contents, loading and saving notes,
    and tracking metadata about vault files. Uses native Python file operations
    for reliable vault management without external dependencies.
    """

    def __init__(self, vault_path: str | Path):
        """
        Initialize the VaultManager with a vault path.

        Args:
            vault_path: Path to the Obsidian vault directory

        Raises:
            VaultNotFoundError: If the vault directory doesn't exist
        """
        self.vault_path = Path(vault_path).expanduser().resolve()
        self.logger = logging.getLogger(__name__)

        # Validate vault path
        if not self.vault_path.exists():
            raise VaultNotFoundError(f"Vault directory not found: {self.vault_path}")

        if not self.vault_path.is_dir():
            raise VaultNotFoundError(
                f"Vault path is not a directory: {self.vault_path}"
            )

        self.logger.info(
            f"Initialized vault at {self.vault_path} using direct file operations"
        )

        # Cache for file stats to avoid repeated file system access
        self._stats_cache: dict[Path, dict[str, Any]] = {}

        # Set of ignored directories (e.g., .git, .obsidian)
        self._ignored_dirs: set[str] = {".git", ".obsidian", ".trash"}

    async def scan_vault(self) -> list[Path]:
        """
        Scan the vault directory for Markdown files.

        Returns:
            List of paths to Markdown files in the vault
        """
        self.logger.info("Scanning vault for markdown files")
        note_paths = []

        for root, dirs, files in os.walk(self.vault_path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in self._ignored_dirs]

            for file in files:
                if file.endswith(".md"):
                    full_path = Path(root) / file
                    note_paths.append(full_path)

        self.logger.info(f"Found {len(note_paths)} notes in vault")
        return note_paths

    async def load_note_raw(self, path: Path | str) -> str:
        """
        Load raw content of a note file with proper encoding.

        Args:
            path: Path to the note file (absolute or relative to vault)

        Returns:
            Raw content of the note as string
        """
        full_path = self._resolve_path(path)

        if not full_path.exists():
            raise NoteNotFoundError(f"Note not found: {path}")

        try:
            # Try UTF-8 first (most common)
            with open(full_path, encoding="utf-8") as f:
                content = f.read()

            # Update stats cache
            self._update_stats_cache(full_path)

            return content
        except UnicodeDecodeError:
            # Try alternative encodings for files not in UTF-8
            for encoding in ["latin-1", "cp1252", "iso-8859-1"]:
                try:
                    with open(full_path, encoding=encoding) as f:
                        content = f.read()

                    self.logger.info(f"Note {path} loaded with {encoding} encoding")
                    return content
                except UnicodeDecodeError:
                    continue

            # If all encodings fail, try binary and decode with error replacement
            with open(full_path, "rb") as f:
                binary_content = f.read()

            self.logger.warning(f"Using error-tolerant encoding for {path}")
            return binary_content.decode("utf-8", errors="replace")

    async def save_note(self, path: Path | str, content: str) -> bool:
        """
        Save content to a note file with proper encoding.

        Args:
            path: Path to the note file (absolute or relative to vault)
            content: Content to write to the file

        Returns:
            True if successful, False otherwise
        """
        full_path = self._resolve_path(path)

        # Ensure parent directory exists
        os.makedirs(full_path.parent, exist_ok=True)

        # Create backup before writing
        if full_path.exists():
            await self._create_backup(full_path)

        # Write content with UTF-8 encoding
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Update stats cache
        self._update_stats_cache(full_path)

        self.logger.info(f"Saved note to {path}")
        return True

    async def _create_backup(self, path: Path) -> Path:
        """
        Create a backup of a note file before modifying it.

        Args:
            path: Path to the note file

        Returns:
            Path to the backup file
        """
        backup_path = self._get_backup_path(path)

        try:
            shutil.copy2(path, backup_path)
            return backup_path
        except Exception as e:
            self.logger.error(f"Failed to create backup for {path}: {e}")
            return path  # Return original path if backup fails

    def _get_backup_path(self, path: Path) -> Path:
        """
        Get the path for a backup file.

        Args:
            path: Original file path

        Returns:
            Path for the backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return path.with_name(f"{path.stem}.{timestamp}.bak")

    def _resolve_path(self, path: Path | str) -> Path:
        """
        Resolve a note path to an absolute path.

        Args:
            path: Path to resolve (absolute or relative to vault)

        Returns:
            Absolute Path object
        """
        path_obj = Path(path)

        # If path is already absolute and within vault, use it
        if path_obj.is_absolute() and self.vault_path in path_obj.parents:
            return path_obj

        # If path is relative to vault root
        return self.vault_path / path_obj

    async def get_note_stats(self, path: Path | str) -> dict[str, Any]:
        """
        Get file statistics for a note.

        Args:
            path: Path to the note file

        Returns:
            Dictionary with file statistics

        Raises:
            NoteNotFoundError: If the note file doesn't exist
        """
        full_path = self._resolve_path(path)

        if not full_path.exists():
            raise NoteNotFoundError(f"Note not found: {path}")

        # Check cache first
        if full_path in self._stats_cache:
            return self._stats_cache[full_path]

        # Get stats and update cache
        return self._update_stats_cache(full_path)

    def _update_stats_cache(self, path: Path) -> dict[str, Any]:
        """
        Update the stats cache for a file.

        Args:
            path: Path to the file

        Returns:
            Dictionary with file statistics
        """
        try:
            stat_result = path.stat()

            stats = {
                "size": stat_result.st_size,
                "created": datetime.fromtimestamp(stat_result.st_ctime),
                "modified": datetime.fromtimestamp(stat_result.st_mtime),
                "accessed": datetime.fromtimestamp(stat_result.st_atime),
                "is_empty": stat_result.st_size == 0,
                "relative_path": path.relative_to(self.vault_path),
                "filename": path.name,
                "extension": path.suffix,
            }

            # Cache the result
            self._stats_cache[path] = stats

            return stats
        except Exception as e:
            self.logger.error(f"Error getting stats for {path}: {e}")

            # Return minimal stats on error
            return {
                "size": 0,
                "created": datetime.now(),
                "modified": datetime.now(),
                "accessed": datetime.now(),
                "is_empty": True,
                "relative_path": str(path),
                "filename": path.name if isinstance(path, Path) else str(path),
                "extension": ".md",
                "error": str(e),
            }

    async def get_vault_stats(self) -> dict[str, Any]:
        """
        Get statistics about the entire vault.

        Returns:
            Dictionary with vault statistics
        """
        note_paths = await self.scan_vault()

        # Calculate statistics
        total_notes = len(note_paths)
        total_size = 0
        newest_note = None
        newest_time = 0

        for path in note_paths:
            stats = await self.get_note_stats(path)
            total_size += stats["size"]

            # Track newest note
            mod_time = stats["modified"].timestamp()
            if mod_time > newest_time:
                newest_time = mod_time
                newest_note = path

        return {
            "total_notes": total_notes,
            "total_size_bytes": total_size,
            "newest_note": newest_note,
            "newest_note_time": datetime.fromtimestamp(newest_time)
            if newest_time
            else None,
            "vault_path": str(self.vault_path),
        }

    async def note_exists(self, path: Path | str) -> bool:
        """
        Check if a note exists in the vault.

        Args:
            path: Path to the note file

        Returns:
            True if the note exists, False otherwise
        """
        try:
            full_path = self._resolve_path(path)
            return full_path.exists() and full_path.is_file()
        except Exception:
            return False

    async def create_directory(self, path: Path | str) -> bool:
        """
        Create a directory in the vault.

        Args:
            path: Path to the directory

        Returns:
            True if successful, False otherwise
        """
        try:
            full_path = self._resolve_path(path)
            os.makedirs(full_path, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Error creating directory {path}: {e}")
            return False
