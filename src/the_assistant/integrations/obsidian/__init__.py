"""
Obsidian integration module for The Assistant.

This module provides comprehensive Obsidian vault parsing and manipulation
capabilities, including YAML frontmatter extraction, task parsing, and
note filtering functionality.
"""

# Import all public classes and functions for clean external imports
from .filter_engine import FilterEngine
from .markdown_parser import MarkdownParser
from .metadata_extractor import MetadataExtractor
from .models import (
    Heading,
    HeadingList,
    Link,
    LinkList,
    MetadataDict,
    MetadataParsingError,
    NoteFilters,
    # Type Aliases
    NoteList,
    NoteNotFoundError,
    # Exceptions
    ObsidianClientError,
    # Data Models
    ObsidianNote,
    TaskItem,
    TaskList,
    TaskUpdateError,
    VaultNotFoundError,
)
from .obsidian_client import ObsidianClient
from .vault_manager import VaultManager

# Define what gets imported with "from obsidian import *"
__all__ = [
    # Main Client
    "ObsidianClient",
    # Data Models
    "ObsidianNote",
    "TaskItem",
    "Heading",
    "Link",
    "NoteFilters",
    # Type Aliases
    "NoteList",
    "TaskList",
    "HeadingList",
    "LinkList",
    "MetadataDict",
    # Exceptions
    "ObsidianClientError",
    "VaultNotFoundError",
    "NoteNotFoundError",
    "MetadataParsingError",
    "TaskUpdateError",
    # Components
    "MetadataExtractor",
    "MarkdownParser",
    "FilterEngine",
    "VaultManager",
]
