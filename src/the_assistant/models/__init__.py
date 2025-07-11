"""
Shared data models for The Assistant.

This module provides models that are actually used in the codebase,
specifically for activity inputs and outputs.
"""

# Activity input models
# Activity output models
from .activity_models import (
    NoteDetail,
    NoteSummary,
    NoteWithPendingTasks,
    TripNote,
)
from .google import CalendarEvent
from .obsidian import NoteFilters

__all__ = [
    # Input models
    "NoteFilters",
    # Output models
    "CalendarEvent",
    "NoteDetail",
    "NoteSummary",
    "NoteWithPendingTasks",
    "TripNote",
]
