"""
FilterEngine for Obsidian note filtering and searching.

This module provides functionality to filter Obsidian notes based on tags,
date ranges, custom metadata properties, and task status.
"""

from datetime import date, datetime
from typing import Any

from .models import NoteFilters, ObsidianNote


class FilterEngine:
    """
    Handles filtering and searching of Obsidian notes.

    Provides methods for filtering notes by tags, date ranges, custom properties,
    and task status with support for AND/OR operations.
    """

    def filter_notes(
        self, notes: list[ObsidianNote], filters: NoteFilters
    ) -> list[ObsidianNote]:
        """
        Filter a list of notes based on the provided criteria.

        Args:
            notes: List of ObsidianNote objects to filter
            filters: Filtering criteria to apply

        Returns:
            Filtered list of notes matching all criteria
        """
        if not filters:
            return notes

        return [note for note in notes if note.matches_filters(filters)]

    def filter_by_tags(
        self, notes: list[ObsidianNote], tags: list[str], operator: str = "OR"
    ) -> list[ObsidianNote]:
        """
        Filter notes by tags with support for AND/OR operations.

        Args:
            notes: List of ObsidianNote objects to filter
            tags: List of tags to filter by
            operator: "AND" to require all tags, "OR" to match any tag

        Returns:
            Filtered list of notes matching the tag criteria

        Raises:
            ValueError: If operator is not "AND" or "OR"
        """
        if not tags:
            return notes

        if operator not in ("AND", "OR"):
            raise ValueError("operator must be 'AND' or 'OR'")

        # Normalize tags (remove # prefix and convert to lowercase)
        normalized_tags = [tag.lower().lstrip("#") for tag in tags]

        filtered_notes = []
        for note in notes:
            note_tags = set(note.get_tag_list())

            if operator == "AND":
                # All specified tags must be present
                if all(tag in note_tags for tag in normalized_tags):
                    filtered_notes.append(note)
            else:  # OR
                # At least one specified tag must be present
                if any(tag in note_tags for tag in normalized_tags):
                    filtered_notes.append(note)

        return filtered_notes

    def filter_by_date_range(
        self,
        notes: list[ObsidianNote],
        start_date: date,
        end_date: date,
        date_fields: list[str] | None = None,
    ) -> list[ObsidianNote]:
        """
        Filter notes by date range.

        A note matches if any of its date fields (default: start_date, end_date, due_date)
        falls within the specified range.

        Args:
            notes: List of ObsidianNote objects to filter
            start_date: Start of the date range (inclusive)
            end_date: End of the date range (inclusive)
            date_fields: List of metadata fields to check for dates

        Returns:
            Filtered list of notes with dates in the specified range
        """
        if date_fields is None:
            date_fields = ["start_date", "end_date", "due_date"]

        if not start_date or not end_date:
            return notes

        filtered_notes = []
        for note in notes:
            # Check standard date properties first
            note_dates = []
            if hasattr(note, "start_date") and note.start_date:
                note_dates.append(note.start_date)
            if hasattr(note, "end_date") and note.end_date:
                note_dates.append(note.end_date)

            # Check additional date fields in metadata
            for field in date_fields:
                if field in note.metadata:
                    date_value = note._parse_date_property(field)
                    if date_value:
                        note_dates.append(date_value)

            # Check if any date falls within the range
            for note_date in note_dates:
                if start_date <= note_date <= end_date:
                    filtered_notes.append(note)
                    break

        return filtered_notes

    def filter_by_property(
        self, notes: list[ObsidianNote], property_name: str, property_value: Any
    ) -> list[ObsidianNote]:
        """
        Filter notes by a specific metadata property value.

        Args:
            notes: List of ObsidianNote objects to filter
            property_name: Name of the metadata property to check
            property_value: Value to match against

        Returns:
            Filtered list of notes with matching property value
        """
        return [
            note
            for note in notes
            if property_name in note.metadata
            and note.metadata[property_name] == property_value
        ]

    def filter_by_properties(
        self, notes: list[ObsidianNote], properties: dict[str, Any]
    ) -> list[ObsidianNote]:
        """
        Filter notes by multiple metadata properties.

        All specified properties must match (AND operation).

        Args:
            notes: List of ObsidianNote objects to filter
            properties: Dictionary of property names and values to match

        Returns:
            Filtered list of notes with all matching property values
        """
        if not properties:
            return notes

        filtered_notes = notes
        for prop_name, prop_value in properties.items():
            filtered_notes = self.filter_by_property(
                filtered_notes, prop_name, prop_value
            )

        return filtered_notes

    def filter_by_pending_tasks(
        self, notes: list[ObsidianNote], has_pending_tasks: bool = True
    ) -> list[ObsidianNote]:
        """
        Filter notes based on whether they have pending tasks.

        Args:
            notes: List of ObsidianNote objects to filter
            has_pending_tasks: True to include notes with pending tasks,
                              False to include notes without pending tasks

        Returns:
            Filtered list of notes based on pending task status
        """
        return [note for note in notes if note.has_pending_tasks == has_pending_tasks]

    def search_by_content(
        self, notes: list[ObsidianNote], search_text: str, case_sensitive: bool = False
    ) -> list[ObsidianNote]:
        """
        Search notes by content text.

        Args:
            notes: List of ObsidianNote objects to search
            search_text: Text to search for
            case_sensitive: Whether to perform case-sensitive search

        Returns:
            List of notes containing the search text
        """
        if not search_text:
            return notes

        if not case_sensitive:
            search_text = search_text.lower()
            return [
                note
                for note in notes
                if search_text in note.content.lower()
                or search_text in note.title.lower()
            ]
        else:
            return [
                note
                for note in notes
                if search_text in note.content or search_text in note.title
            ]

    def sort_notes(
        self, notes: list[ObsidianNote], sort_by: str = "title", reverse: bool = False
    ) -> list[ObsidianNote]:
        """
        Sort notes by a specified attribute.

        Args:
            notes: List of ObsidianNote objects to sort
            sort_by: Attribute to sort by (title, start_date, modified_date, etc.)
            reverse: Whether to sort in descending order

        Returns:
            Sorted list of notes

        Raises:
            ValueError: If sort_by is not a valid attribute
        """
        valid_sort_fields = {
            "title": lambda note: note.title.lower(),
            "start_date": lambda note: note.start_date or date.max,
            "end_date": lambda note: note.end_date or date.max,
            "created_date": lambda note: note.created_date or datetime.max,
            "modified_date": lambda note: note.modified_date or datetime.max,
            "path": lambda note: str(note.path).lower(),
        }

        if sort_by not in valid_sort_fields:
            raise ValueError(
                f"Invalid sort field: {sort_by}. Valid options: {', '.join(valid_sort_fields.keys())}"
            )

        sort_key = valid_sort_fields[sort_by]
        return sorted(notes, key=sort_key, reverse=reverse)

    def apply_filters(
        self, notes: list[ObsidianNote], filters: NoteFilters | None = None, **kwargs
    ) -> list[ObsidianNote]:
        """
        Apply multiple filters to a list of notes.

        This method provides a convenient way to apply multiple filters at once,
        either using a NoteFilters object or individual filter parameters.

        Args:
            notes: List of ObsidianNote objects to filter
            filters: NoteFilters object with filter criteria
            **kwargs: Additional filter parameters that override filters object
                - tags: List of tags to filter by
                - tag_operator: "AND" or "OR" for tag filtering
                - date_range: Tuple of (start_date, end_date)
                - properties: Dict of property names and values
                - has_pending_tasks: Boolean for task filtering
                - search_text: Text to search for in content
                - sort_by: Field to sort by
                - reverse: Whether to sort in descending order

        Returns:
            Filtered and sorted list of notes
        """
        filtered_notes = notes

        # Start with filters from NoteFilters object if provided
        if filters:
            filtered_notes = self.filter_notes(filtered_notes, filters)

        # Apply additional filters from kwargs
        if "tags" in kwargs:
            tag_operator = kwargs.get("tag_operator", "OR")
            filtered_notes = self.filter_by_tags(
                filtered_notes, kwargs["tags"], tag_operator
            )

        if "date_range" in kwargs and kwargs["date_range"]:
            start_date, end_date = kwargs["date_range"]
            filtered_notes = self.filter_by_date_range(
                filtered_notes, start_date, end_date
            )

        if "properties" in kwargs:
            filtered_notes = self.filter_by_properties(
                filtered_notes, kwargs["properties"]
            )

        if "has_pending_tasks" in kwargs:
            filtered_notes = self.filter_by_pending_tasks(
                filtered_notes, kwargs["has_pending_tasks"]
            )

        if "search_text" in kwargs:
            case_sensitive = kwargs.get("case_sensitive", False)
            filtered_notes = self.search_by_content(
                filtered_notes, kwargs["search_text"], case_sensitive
            )

        # Sort results if requested
        if "sort_by" in kwargs:
            reverse = kwargs.get("reverse", False)
            filtered_notes = self.sort_notes(filtered_notes, kwargs["sort_by"], reverse)

        return filtered_notes
