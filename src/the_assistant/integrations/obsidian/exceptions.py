"""
Custom exceptions for the Obsidian client.

This module contains all exception classes used by the Obsidian integration.
"""


class ObsidianClientError(Exception):
    """Base exception for all Obsidian client errors."""

    pass


class VaultNotFoundError(ObsidianClientError):
    """Raised when the specified vault directory cannot be found."""

    pass


class NoteNotFoundError(ObsidianClientError):
    """Raised when a requested note cannot be found in the vault."""

    pass


class MetadataParsingError(ObsidianClientError):
    """Raised when YAML frontmatter cannot be parsed properly."""

    pass


class TaskUpdateError(ObsidianClientError):
    """Raised when a task status cannot be updated in a note."""

    pass
