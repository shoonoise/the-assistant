"""
ObsidianClient - Main interface for Obsidian vault operations.

This module provides the primary interface for interacting with Obsidian vaults,
integrating all components (VaultManager, MarkdownParser, MetadataExtractor, FilterEngine)
to provide a comprehensive API for note management, filtering, and task operations.
"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .filter_engine import FilterEngine
from .markdown_parser import MarkdownParser
from .metadata_extractor import MetadataExtractor
from .models import (
    NoteFilters,
    NoteNotFoundError,
    ObsidianClientError,
    ObsidianNote,
    TaskItem,
    TaskUpdateError,
)
from .vault_manager import VaultManager


class ObsidianClient:
    """
    Main interface for Obsidian vault operations.

    Provides a comprehensive API for reading, writing, filtering, and managing
    Obsidian notes with full support for YAML frontmatter, task extraction,
    and advanced filtering capabilities.
    """

    def __init__(self, vault_path: str | Path, user_id: int):
        """
        Initialize the ObsidianClient with a vault path.

        Args:
            vault_path: Path to the Obsidian vault directory
            user_id: User ID for user-specific operations

        Raises:
            VaultNotFoundError: If the vault directory doesn't exist
        """
        self.vault_path = Path(vault_path).expanduser().resolve()
        self.user_id = user_id
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.vault_manager = VaultManager(self.vault_path)
        self.markdown_parser = MarkdownParser()
        self.metadata_extractor = MetadataExtractor()
        self.filter_engine = FilterEngine()

        # Cache for loaded notes to improve performance
        self._note_cache: dict[Path, ObsidianNote] = {}
        self._cache_timestamp: datetime | None = None
        self._cache_ttl_seconds = 300  # 5 minutes cache TTL

        user_context = f" (user_id={self.user_id})" if self.user_id else ""
        self.logger.info(
            f"Initialized ObsidianClient for vault: {self.vault_path}{user_context}"
        )

    async def get_notes(self, filters: NoteFilters | None = None) -> list[ObsidianNote]:
        """
        Get all notes from the vault with optional filtering.

        Args:
            filters: Optional filtering criteria to apply

        Returns:
            List of ObsidianNote objects matching the filters
        """
        # Load all notes from vault
        all_notes = await self._load_all_notes()

        # Apply filters if provided
        if filters:
            return self.filter_engine.filter_notes(all_notes, filters)

        return all_notes

    async def get_note(self, path: str | Path) -> ObsidianNote | None:
        """
        Get a specific note by path.

        Args:
            path: Path to the note (absolute or relative to vault)

        Returns:
            ObsidianNote object or None if not found
        """
        # Resolve path
        full_path = self.vault_manager._resolve_path(path)

        # Check cache first
        if self._is_cache_valid() and full_path in self._note_cache:
            return self._note_cache[full_path]

        # Load note from file
        if not await self.vault_manager.note_exists(path):
            return None

        note = await self._load_single_note(full_path)

        # Update cache
        self._note_cache[full_path] = note

        return note

    async def create_note(
        self,
        title: str,
        content: str = "",
        metadata: dict[str, Any] | None = None,
        path: str | Path | None = None,
    ) -> ObsidianNote:
        """
        Create a new note in the vault.

        Args:
            title: Title of the note
            content: Markdown content (without frontmatter)
            metadata: Optional metadata dictionary for YAML frontmatter
            path: Optional custom path for the note (defaults to title-based path)

        Returns:
            Created ObsidianNote object
        """
        # Generate path if not provided
        if path is None:
            # Sanitize title for filename
            safe_title = self._sanitize_filename(title)
            path = f"{safe_title}.md"

        full_path = self.vault_manager._resolve_path(path)

        # Check if note already exists
        if await self.vault_manager.note_exists(path):
            raise ObsidianClientError(f"Note already exists: {path}")

        # Build note content with frontmatter
        note_content = self._build_note_content(content, metadata or {})

        # Save note to vault
        success = await self.vault_manager.save_note(path, note_content)
        if not success:
            raise ObsidianClientError(f"Failed to save note: {path}")

        # Load and return the created note
        created_note = await self._load_single_note(full_path)

        # Update cache
        self._note_cache[full_path] = created_note

        self.logger.info(f"Created note: {path}")
        return created_note

    async def update_note(
        self,
        path: str | Path,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Update an existing note's content and/or metadata.

        Args:
            path: Path to the note to update
            content: New content (if None, existing content is preserved)
            metadata: New metadata (merged with existing metadata)

        Returns:
            True if successful, False otherwise
        """
        # Load existing note
        existing_note = await self.get_note(path)
        if not existing_note:
            raise NoteNotFoundError(f"Note not found: {path}")

        # Use existing content if not provided
        new_content = content if content is not None else existing_note.content

        # Merge metadata if provided
        new_metadata = existing_note.metadata.copy()
        if metadata:
            new_metadata = self.metadata_extractor.merge_metadata(
                new_metadata, metadata
            )

        # Build updated note content
        updated_content = self._build_note_content(new_content, new_metadata)

        # Save updated note
        success = await self.vault_manager.save_note(path, updated_content)
        if not success:
            raise ObsidianClientError(f"Failed to save updated note: {path}")

        # Invalidate cache for this note
        full_path = self.vault_manager._resolve_path(path)
        if full_path in self._note_cache:
            del self._note_cache[full_path]

        self.logger.info(f"Updated note: {path}")
        return True

    async def append_to_note(
        self, path: str | Path, content: str, separator: str = "\n\n"
    ) -> bool:
        """
        Append content to an existing note while maintaining formatting.

        Args:
            path: Path to the note to append to
            content: Content to append
            separator: Separator between existing content and new content

        Returns:
            True if successful, False otherwise
        """
        # Load existing note
        existing_note = await self.get_note(path)
        if not existing_note:
            raise NoteNotFoundError(f"Note not found: {path}")

        # Append content with separator
        new_content = existing_note.content.rstrip() + separator + content.lstrip()

        # Update the note with new content (preserving metadata)
        return await self.update_note(path, content=new_content)

    async def prepend_to_note(
        self, path: str | Path, content: str, separator: str = "\n\n"
    ) -> bool:
        """
        Prepend content to an existing note while maintaining formatting.

        Args:
            path: Path to the note to prepend to
            content: Content to prepend
            separator: Separator between new content and existing content

        Returns:
            True if successful, False otherwise
        """
        # Load existing note
        existing_note = await self.get_note(path)
        if not existing_note:
            raise NoteNotFoundError(f"Note not found: {path}")

        # Prepend content with separator
        new_content = content.rstrip() + separator + existing_note.content.lstrip()

        # Update the note with new content (preserving metadata)
        return await self.update_note(path, content=new_content)

    # Filtering Methods - Use get_notes(filters) for all filtering operations

    # Task Management Methods

    async def get_pending_tasks(
        self, tag_filter: list[str] | None = None
    ) -> list[TaskItem]:
        """
        Get all pending tasks from notes, optionally filtered by tags.

        Args:
            tag_filter: Optional list of tags to filter notes by

        Returns:
            List of pending TaskItem objects
        """
        # Get notes (filtered by tags if specified)
        if tag_filter:
            filters = NoteFilters(tags=tag_filter, tag_operator="OR")
            notes = await self.get_notes(filters)
        else:
            notes = await self.get_notes()

        # Extract all pending tasks
        pending_tasks = []
        for note in notes:
            for task in note.pending_tasks:
                # Add note_title attribute to each task
                task.note_title = note.title
                pending_tasks.append(task)

        return pending_tasks

    async def mark_task_complete(self, note_path: str | Path, task_text: str) -> bool:
        """
        Mark a specific task as complete in a note.

        Args:
            note_path: Path to the note containing the task
            task_text: Text of the task to mark complete

        Returns:
            True if successful, False otherwise

        Raises:
            NoteNotFoundError: If the note doesn't exist
            TaskUpdateError: If the task cannot be found or updated
        """
        return await self.update_task_status(note_path, task_text, True)

    async def mark_task_incomplete(self, note_path: str | Path, task_text: str) -> bool:
        """
        Mark a specific task as incomplete in a note.

        Args:
            note_path: Path to the note containing the task
            task_text: Text of the task to mark incomplete

        Returns:
            True if successful, False otherwise

        Raises:
            NoteNotFoundError: If the note doesn't exist
            TaskUpdateError: If the task cannot be found or updated
        """
        return await self.update_task_status(note_path, task_text, False)

    async def update_task_status(
        self, note_path: str | Path, task_text: str, completed: bool
    ) -> bool:
        """
        Update a specific task's completion status in a note.

        Args:
            note_path: Path to the note containing the task
            task_text: Text of the task to update
            completed: True to mark complete, False to mark incomplete

        Returns:
            True if successful, False otherwise
        """
        # Load the note
        note = await self.get_note(note_path)
        if not note:
            raise NoteNotFoundError(f"Note not found: {note_path}")

        # Find the task to update
        target_task = None
        for task in note.tasks:
            if task.text.strip() == task_text.strip():
                # Only update if status is different
                if task.completed != completed:
                    target_task = task
                    break

        if not target_task:
            status_text = "completed" if completed else "incomplete"
            raise TaskUpdateError(
                f"Task not found or already {status_text}: {task_text}"
            )

        # Update task status in content
        updated_content = self._update_task_status_in_content(
            note.raw_content, task_text, completed
        )

        # Save updated note
        success = await self.vault_manager.save_note(note_path, updated_content)
        if not success:
            raise TaskUpdateError("Failed to save updated task status")

        # Invalidate cache
        full_path = self.vault_manager._resolve_path(note_path)
        if full_path in self._note_cache:
            del self._note_cache[full_path]

        status_text = "complete" if completed else "incomplete"
        self.logger.info(f"Marked task {status_text} in {note_path}: {task_text}")
        return True

    async def get_task_by_line_number(
        self, note_path: str | Path, line_number: int
    ) -> TaskItem | None:
        """
        Get a task by its line number in a note.

        Args:
            note_path: Path to the note containing the task
            line_number: Line number of the task (1-based)

        Returns:
            TaskItem object or None if not found

        Raises:
            NoteNotFoundError: If the note doesn't exist
        """
        note = await self.get_note(note_path)
        if not note:
            raise NoteNotFoundError(f"Note not found: {note_path}")

        for task in note.tasks:
            if task.line_number == line_number:
                return task

        return None

    async def get_tasks_under_heading(
        self, note_path: str | Path, heading_text: str
    ) -> list[TaskItem]:
        """
        Get all tasks that appear under a specific heading in a note.

        Args:
            note_path: Path to the note
            heading_text: Text of the heading to search under

        Returns:
            List of TaskItem objects under the specified heading

        Raises:
            NoteNotFoundError: If the note doesn't exist
        """
        note = await self.get_note(note_path)
        if not note:
            raise NoteNotFoundError(f"Note not found: {note_path}")

        return note.get_tasks_by_heading(heading_text)

    async def get_task_completion_stats(self, note_path: str | Path) -> dict[str, Any]:
        """
        Get task completion statistics for a specific note.

        Args:
            note_path: Path to the note

        Returns:
            Dictionary with completion statistics

        Raises:
            NoteNotFoundError: If the note doesn't exist
        """
        note = await self.get_note(note_path)
        if not note:
            raise NoteNotFoundError(f"Note not found: {note_path}")

        total_tasks = len(note.tasks)
        completed_tasks = len(note.completed_tasks)
        pending_tasks = len(note.pending_tasks)

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "completion_ratio": note.task_completion_ratio,
            "has_pending_tasks": note.has_pending_tasks,
        }

    async def get_all_task_completion_stats(self) -> dict[str, Any]:
        """
        Get task completion statistics across all notes in the vault.

        Returns:
            Dictionary with vault-wide completion statistics
        """
        all_notes = await self.get_notes()

        total_tasks = 0
        completed_tasks = 0
        notes_with_tasks = 0
        notes_with_pending_tasks = 0

        for note in all_notes:
            if note.tasks:
                notes_with_tasks += 1
                total_tasks += len(note.tasks)
                completed_tasks += len(note.completed_tasks)

                if note.has_pending_tasks:
                    notes_with_pending_tasks += 1

        return {
            "total_notes": len(all_notes),
            "notes_with_tasks": notes_with_tasks,
            "notes_with_pending_tasks": notes_with_pending_tasks,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": total_tasks - completed_tasks,
            "completion_ratio": completed_tasks / total_tasks
            if total_tasks > 0
            else 0.0,
        }

    # Private Helper Methods

    async def _load_all_notes(self) -> list[ObsidianNote]:
        """Load all notes from the vault with caching."""
        # Check if cache is valid
        if self._is_cache_valid() and self._note_cache:
            return list(self._note_cache.values())

        # Clear cache and reload
        self._note_cache.clear()

        # Scan vault for note files
        note_paths = await self.vault_manager.scan_vault()

        # Load notes concurrently for better performance
        tasks = [self._load_single_note(path) for path in note_paths]
        notes = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and update cache
        valid_notes = []
        for i, result in enumerate(notes):
            if isinstance(result, Exception):
                self.logger.warning(f"Failed to load note {note_paths[i]}: {result}")
            else:
                valid_notes.append(result)
                self._note_cache[note_paths[i]] = result

        # Update cache timestamp
        self._cache_timestamp = datetime.now()

        self.logger.info(f"Loaded {len(valid_notes)} notes from vault")
        return valid_notes

    async def _load_single_note(self, path: Path) -> ObsidianNote:
        """Load a single note from file and parse all components."""
        # Load raw content
        raw_content = await self.vault_manager.load_note_raw(path)

        # Extract metadata and content
        metadata, content = self.metadata_extractor.extract_frontmatter(raw_content)

        # Parse content structure
        tasks, headings, links = self.markdown_parser.parse_content(content)

        # Get file stats
        stats = await self.vault_manager.get_note_stats(path)

        # Extract title (from metadata or filename)
        title = metadata.get("title", path.stem)

        # Extract tags from metadata
        tags = self.metadata_extractor.extract_tags(metadata)

        # Create ObsidianNote object
        note = ObsidianNote(
            title=title,
            path=path,
            content=content,
            raw_content=raw_content,
            metadata=metadata,
            tags=tags,
            tasks=tasks,
            headings=headings,
            links=links,
            created_date=stats.get("created"),
            modified_date=stats.get("modified"),
        )

        return note

    def _is_cache_valid(self) -> bool:
        """Check if the note cache is still valid."""
        if not self._cache_timestamp:
            return False

        age = datetime.now() - self._cache_timestamp
        return age.total_seconds() < self._cache_ttl_seconds

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a string for use as a filename."""
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")

        # Remove leading/trailing whitespace and dots
        filename = filename.strip(" .")

        # Limit length
        if len(filename) > 100:
            filename = filename[:100]

        return filename or "untitled"

    def _build_note_content(self, content: str, metadata: dict[str, Any]) -> str:
        """Build complete note content with YAML frontmatter."""
        if not metadata:
            return content

        # Build YAML frontmatter
        yaml_content = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)

        # Combine frontmatter and content
        return f"---\n{yaml_content}---\n\n{content}"

    def _update_task_status_in_content(
        self, content: str, task_text: str, completed: bool
    ) -> str:
        """Update task completion status in raw content while preserving formatting."""

        # Pattern to match the specific task with flexible whitespace and formatting
        escaped_text = re.escape(task_text.strip())

        if completed:
            # Change [ ] to [x] - match various checkbox formats
            patterns = [
                rf"^(\s*)- \[ \] ({escaped_text})(.*)$",  # Standard format
                rf"^(\s*)- \[\s\] ({escaped_text})(.*)$",  # Space variations
                rf"^(\s*)\* \[ \] ({escaped_text})(.*)$",  # Asterisk bullets
                rf"^(\s*)\* \[\s\] ({escaped_text})(.*)$",  # Asterisk with space
            ]
            replacement = r"\1- [x] \2\3"
        else:
            # Change [x] to [ ] - match various completed formats
            patterns = [
                rf"^(\s*)- \[x\] ({escaped_text})(.*)$",  # Standard x
                rf"^(\s*)- \[X\] ({escaped_text})(.*)$",  # Capital X
                rf"^(\s*)\* \[x\] ({escaped_text})(.*)$",  # Asterisk with x
                rf"^(\s*)\* \[X\] ({escaped_text})(.*)$",  # Asterisk with X
            ]
            replacement = r"\1- [ ] \2\3"

        updated_content = content
        for pattern in patterns:
            updated_content = re.sub(
                pattern, replacement, updated_content, flags=re.MULTILINE
            )
            # If we found and replaced the task, break
            if updated_content != content:
                break
            content = updated_content

        return updated_content

    # Additional Utility Methods

    async def get_vault_stats(self) -> dict[str, Any]:
        """Get statistics about the vault."""
        return await self.vault_manager.get_vault_stats()

    async def refresh_cache(self) -> None:
        """Force refresh of the note cache."""
        self._note_cache.clear()
        self._cache_timestamp = None
        await self._load_all_notes()

    def set_cache_ttl(self, seconds: int) -> None:
        """Set the cache time-to-live in seconds."""
        self._cache_ttl_seconds = max(0, seconds)


if __name__ == "__main__":

    async def main():
        client = ObsidianClient("~/dev/the_assistant/obsidian_vault", user_id=1)
        notes = await client.get_notes(NoteFilters(tags=["work"]))
        print(notes)

    asyncio.run(main())
