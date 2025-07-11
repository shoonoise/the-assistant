"""
Activity-specific data models using Pydantic v2.

This module contains lightweight view models for activity return types,
leveraging the main Obsidian models for consistency and reducing redundancy.
"""

from pathlib import Path
from typing import Any

from pydantic import Field, computed_field

from .base import BaseAssistantModel
from .obsidian import ObsidianNote


class NoteSummary(BaseAssistantModel):
    """Lightweight summary view of a note for activity returns."""

    title: str = Field(description="Note title")
    path: Path = Field(description="File path to the note")
    tags: list[str] = Field(default_factory=list, description="Note tags")
    task_count: int = Field(description="Total number of tasks")
    pending_task_count: int = Field(description="Number of pending tasks")
    has_pending_tasks: bool = Field(description="Whether note has pending tasks")
    created_date: str | None = Field(
        default=None, description="File creation date (ISO format)"
    )
    modified_date: str | None = Field(
        default=None, description="File modification date (ISO format)"
    )

    @computed_field
    @property
    def completed_task_count(self) -> int:
        """Number of completed tasks."""
        return self.task_count - self.pending_task_count

    @computed_field
    @property
    def task_completion_ratio(self) -> float:
        """Task completion ratio (0.0 to 1.0)."""
        return (
            (self.task_count - self.pending_task_count) / self.task_count
            if self.task_count > 0
            else 0.0
        )

    @classmethod
    def from_obsidian_note(cls, note: ObsidianNote) -> "NoteSummary":
        """Create NoteSummary from ObsidianNote."""
        return cls(
            title=note.title,
            path=note.path,
            tags=note.get_tag_list(),
            task_count=len(note.tasks),
            pending_task_count=len(note.pending_tasks),
            has_pending_tasks=note.has_pending_tasks,
            created_date=note.created_date.isoformat() if note.created_date else None,
            modified_date=note.modified_date.isoformat()
            if note.modified_date
            else None,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NoteSummary":
        """Create NoteSummary from raw dictionary data."""
        return cls.model_validate(data)

    @classmethod
    def from_dict_list(cls, data_list: list[dict[str, Any]]) -> list["NoteSummary"]:
        """Create list of NoteSummary from raw dictionary list."""
        return [cls.from_dict(item) for item in data_list]


# Type aliases for common activity return types
# These leverage the main ObsidianNote model instead of creating redundant models
TripNote = ObsidianNote  # Trip notes are just ObsidianNote with trip-specific metadata
NoteDetail = ObsidianNote  # Note details are the full ObsidianNote
NoteWithPendingTasks = ObsidianNote  # Use ObsidianNote.pending_tasks property
