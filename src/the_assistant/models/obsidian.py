"""
Obsidian-related data models using Pydantic v2.

This module contains all data structures for Obsidian integration,
including notes, tasks, headings, links, and filtering options.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, computed_field, field_validator

from .base import BaseAssistantModel


class TaskItem(BaseAssistantModel):
    """Represents a checkbox task item extracted from note content."""

    text: str = Field(description="Task text content")
    completed: bool = Field(description="Whether the task is completed")
    line_number: int = Field(description="Line number in the source file")
    parent_heading: str | None = Field(default=None, description="Parent heading text")
    indent_level: int = Field(default=0, description="Indentation level (spaces/tabs)")
    heading_hierarchy: list[str] = Field(
        default_factory=list, description="Full heading path"
    )
    note_title: str | None = Field(default=None, description="Title of containing note")

    @computed_field
    @property
    def is_nested(self) -> bool:
        """Check if this task is nested (indented)."""
        return self.indent_level > 0

    @computed_field
    @property
    def nesting_level(self) -> int:
        """Get the nesting level based on indentation (0-based)."""
        return self.indent_level // 2 if self.indent_level > 0 else 0

    def __str__(self) -> str:
        status = "x" if self.completed else " "
        indent = " " * self.indent_level
        return f"{indent}- [{status}] {self.text}"


class Heading(BaseAssistantModel):
    """Represents a heading extracted from note content."""

    level: int = Field(ge=1, le=6, description="Heading level (1-6 for H1-H6)")
    text: str = Field(description="Heading text content")
    line_number: int = Field(description="Line number in the source file")

    def __str__(self) -> str:
        return f"{'#' * self.level} {self.text}"


class Link(BaseAssistantModel):
    """Represents a link extracted from note content."""

    text: str = Field(description="Link display text")
    url: str = Field(description="Link URL or internal reference")
    is_internal: bool = Field(
        description="True for [[internal links]], False for external"
    )

    def __str__(self) -> str:
        if self.is_internal:
            return (
                f"[[{self.url}|{self.text}]]"
                if self.text != self.url
                else f"[[{self.url}]]"
            )
        else:
            return f"[{self.text}]({self.url})"


class NoteFilters(BaseAssistantModel):
    """Filtering criteria for note queries."""

    tags: list[str] | None = Field(default=None, description="Tags to filter by")
    tag_operator: Literal["AND", "OR"] = Field(
        default="OR", description="How to combine multiple tags"
    )
    date_range: tuple[date, date] | None = Field(
        default=None, description="Date range filter (start, end)"
    )
    properties: dict[str, Any] | None = Field(
        default=None, description="Metadata properties to match"
    )
    has_pending_tasks: bool | None = Field(
        default=None, description="Filter by presence of pending tasks"
    )

    @field_validator("date_range")
    @classmethod
    def validate_date_range(cls, v):
        if v is not None and len(v) != 2:
            raise ValueError("date_range must be a tuple of (start_date, end_date)")
        return v


class ObsidianNote(BaseAssistantModel):
    """
    Comprehensive representation of an Obsidian note with parsed content and metadata.

    This class provides both raw and parsed representations of note content,
    along with computed properties for common operations.
    """

    title: str = Field(description="Note title")
    path: Path = Field(description="File path to the note")
    content: str = Field(description="Markdown content without frontmatter")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="YAML frontmatter metadata"
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags from content and metadata"
    )
    tasks: list[TaskItem] = Field(default_factory=list, description="Extracted tasks")
    headings: list[Heading] = Field(
        default_factory=list, description="Extracted headings"
    )
    links: list[Link] = Field(default_factory=list, description="Extracted links")
    raw_content: str | None = Field(
        default=None, description="Original file content including frontmatter"
    )
    created_date: datetime | None = Field(
        default=None, description="File creation date"
    )
    modified_date: datetime | None = Field(
        default=None, description="File modification date"
    )

    @computed_field
    @property
    def start_date(self) -> date | None:
        """Extract start_date from metadata, supporting various formats."""
        return self._parse_date_property("start_date")

    @computed_field
    @property
    def end_date(self) -> date | None:
        """Extract end_date from metadata, supporting various formats."""
        return self._parse_date_property("end_date")

    @computed_field
    @property
    def pending_tasks(self) -> list[TaskItem]:
        """Return all incomplete tasks from the note."""
        return [task for task in self.tasks if not task.completed]

    @computed_field
    @property
    def completed_tasks(self) -> list[TaskItem]:
        """Return all completed tasks from the note."""
        return [task for task in self.tasks if task.completed]

    @computed_field
    @property
    def has_pending_tasks(self) -> bool:
        """Check if the note has any incomplete tasks."""
        return len(self.pending_tasks) > 0

    @computed_field
    @property
    def task_completion_ratio(self) -> float:
        """Calculate the ratio of completed tasks to total tasks."""
        if not self.tasks:
            return 0.0
        return len(self.completed_tasks) / len(self.tasks)

    def _parse_date_property(self, property_name: str) -> date | None:
        """Parse a date property from metadata, handling various formats."""
        if property_name not in self.metadata:
            return None

        value = self.metadata[property_name]

        # Handle different input types
        if isinstance(value, date):
            return value
        elif isinstance(value, datetime):
            return value.date()
        elif isinstance(value, str):
            return self._parse_date_string(value)
        else:
            return None

    def _parse_date_string(self, date_str: str) -> date | None:
        """Parse a date string using common formats."""
        # Common date formats to try
        formats = [
            "%Y-%m-%d",  # 2024-01-15
            "%m/%d/%Y",  # 01/15/2024
            "%d/%m/%Y",  # 15/01/2024
            "%Y/%m/%d",  # 2024/01/15
            "%d-%m-%Y",  # 15-01-2024
            "%m-%d-%Y",  # 01-15-2024
            "%B %d, %Y",  # January 15, 2024
            "%b %d, %Y",  # Jan 15, 2024
            "%d %B %Y",  # 15 January 2024
            "%d %b %Y",  # 15 Jan 2024
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return None

    def get_tag_list(self) -> list[str]:
        """Get a normalized list of all tags from both metadata and content."""
        all_tags = set()

        # Add tags from metadata
        all_tags.update(tag.lower().lstrip("#") for tag in self.tags)

        # Add tags from metadata 'tags' field if it exists
        if "tags" in self.metadata:
            metadata_tags = self.metadata["tags"]
            if isinstance(metadata_tags, list):
                all_tags.update(tag.lower().lstrip("#") for tag in metadata_tags)
            elif isinstance(metadata_tags, str):
                # Handle comma-separated tags
                all_tags.update(
                    tag.strip().lower().lstrip("#") for tag in metadata_tags.split(",")
                )

        return sorted(all_tags)

    def matches_filters(self, filters: NoteFilters) -> bool:
        """Check if this note matches the provided filters."""
        # Tag filtering
        if filters.tags:
            note_tags = set(self.get_tag_list())
            filter_tags = {tag.lower().lstrip("#") for tag in filters.tags}

            if filters.tag_operator == "AND":
                if not filter_tags.issubset(note_tags):
                    return False
            else:  # OR
                if not filter_tags.intersection(note_tags):
                    return False

        # Date range filtering
        if filters.date_range:
            start_filter, end_filter = filters.date_range
            note_start = self.start_date
            note_end = self.end_date

            # Note must have at least one date in the range
            if not note_start and not note_end:
                return False

            # Check if any note date falls within the filter range
            dates_in_range = []
            if note_start:
                dates_in_range.append(start_filter <= note_start <= end_filter)
            if note_end:
                dates_in_range.append(start_filter <= note_end <= end_filter)

            if not any(dates_in_range):
                return False

        # Property filtering
        if filters.properties:
            for key, expected_value in filters.properties.items():
                if key not in self.metadata or self.metadata[key] != expected_value:
                    return False

        # Pending tasks filtering
        if filters.has_pending_tasks is not None:
            if filters.has_pending_tasks != self.has_pending_tasks:
                return False

        return True

    def get_tasks_by_heading(self, heading_text: str) -> list[TaskItem]:
        """Get all tasks that appear under a specific heading."""
        return [task for task in self.tasks if task.parent_heading == heading_text]


# Type aliases for convenience
NoteList = list[ObsidianNote]
TaskList = list[TaskItem]
HeadingList = list[Heading]
LinkList = list[Link]
MetadataDict = dict[str, Any]
