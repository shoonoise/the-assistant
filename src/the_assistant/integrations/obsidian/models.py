"""
Data models and type definitions for the Obsidian client.

This module re-exports the consolidated models from the main models package
and provides the custom exceptions for the Obsidian integration.
"""

# Import consolidated models from main models package
# Import activity-specific view models
from ...models.activity_models import (
    NoteDetail,
    NoteSummary,
    NoteWithPendingTasks,
    # Type aliases for backward compatibility
    TripNote,
)
from ...models.obsidian import (
    Heading,
    HeadingList,
    Link,
    LinkList,
    MetadataDict,
    NoteFilters,
    NoteList,
    ObsidianNote,
    TaskItem,
    TaskList,
)

# Import exceptions
from .exceptions import (
    MetadataParsingError,
    NoteNotFoundError,
    ObsidianClientError,
    TaskUpdateError,
    VaultNotFoundError,
)

# Re-export everything for backward compatibility
__all__ = [
    # Core models
    "Heading",
    "HeadingList",
    "Link",
    "LinkList",
    "MetadataDict",
    "NoteFilters",
    "NoteList",
    "ObsidianNote",
    "TaskItem",
    "TaskList",
    # Activity view models
    "NoteSummary",
    # Type aliases (now point to ObsidianNote)
    "TripNote",
    "NoteDetail",
    "NoteWithPendingTasks",
    # Exceptions
    "MetadataParsingError",
    "NoteNotFoundError",
    "ObsidianClientError",
    "TaskUpdateError",
    "VaultNotFoundError",
]
