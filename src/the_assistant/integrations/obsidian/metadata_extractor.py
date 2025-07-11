"""
MetadataExtractor for robust YAML frontmatter parsing.

This module provides functionality to extract and parse YAML frontmatter from
Obsidian notes, with error handling for malformed content and support for
various date formats and tag normalization.
"""

import re
from datetime import date, datetime
from typing import Any

import yaml
from dateutil import parser as date_parser

from .exceptions import MetadataParsingError


class MetadataExtractor:
    """
    Handles extraction and parsing of YAML frontmatter from Obsidian notes.

    Provides robust parsing with graceful error handling for malformed content,
    date parsing supporting multiple formats, and tag normalization.
    """

    def __init__(self):
        """Initialize the MetadataExtractor."""
        # Regex pattern to match YAML frontmatter
        self.frontmatter_pattern = re.compile(
            r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE
        )

        # Common date property names to automatically parse
        self.date_properties = {
            "date",
            "start_date",
            "end_date",
            "created",
            "modified",
            "due_date",
            "deadline",
            "next_lesson",
            "created_at",
            "updated_at",
        }

    def extract_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """
        Extract YAML frontmatter from note content.

        Args:
            content: Raw note content including potential frontmatter

        Returns:
            Tuple of (metadata_dict, content_without_frontmatter)
        """
        if not content or not content.strip():
            return {}, content

        # Check if content starts with frontmatter
        if not content.strip().startswith("---"):
            return {}, content

        # Extract frontmatter using regex
        match = self.frontmatter_pattern.match(content)
        if not match:
            # Malformed frontmatter - try to extract what we can
            return self._extract_malformed_frontmatter(content)

        yaml_content = match.group(1)
        remaining_content = content[match.end() :]

        try:
            # Parse YAML content
            metadata = yaml.safe_load(yaml_content) or {}

            # Ensure metadata is a dictionary
            if not isinstance(metadata, dict):
                raise MetadataParsingError(
                    f"Frontmatter must be a dictionary, got {type(metadata)}"
                )

            # Process and normalize metadata
            processed_metadata = self._process_metadata(metadata)

            return processed_metadata, remaining_content

        except yaml.YAMLError as e:
            # Try to extract partial metadata
            partial_metadata = self._extract_partial_yaml(yaml_content)
            if partial_metadata:
                return partial_metadata, remaining_content
            else:
                raise MetadataParsingError(
                    f"Failed to parse YAML frontmatter: {e}"
                ) from e

    def _extract_malformed_frontmatter(
        self, content: str
    ) -> tuple[dict[str, Any], str]:
        """
        Attempt to extract metadata from malformed frontmatter.

        Args:
            content: Raw content with potentially malformed frontmatter

        Returns:
            Tuple of (partial_metadata, remaining_content)
        """
        lines = content.split("\n")
        metadata = {}
        content_start_idx = 0

        # Look for the first --- and try to find the closing ---
        if lines and lines[0].strip() == "---":
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    # Found closing marker
                    yaml_lines = lines[1:i]
                    content_start_idx = i + 1
                    break
            else:
                # No closing marker found, treat everything as content
                return {}, content

            # Try to parse individual lines as key-value pairs
            for line in yaml_lines:
                if ":" in line:
                    try:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()

                        # Try to parse the value
                        parsed_value = self._parse_yaml_value(value)
                        metadata[key] = parsed_value
                    except Exception:
                        # Skip malformed lines
                        continue

        remaining_content = "\n".join(lines[content_start_idx:])
        return self._process_metadata(metadata), remaining_content

    def _extract_partial_yaml(self, yaml_content: str) -> dict[str, Any]:
        """
        Extract what we can from partially valid YAML.

        Args:
            yaml_content: YAML string that failed to parse

        Returns:
            Dictionary with successfully parsed key-value pairs
        """
        metadata = {}

        # Try to parse line by line
        for line in yaml_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" in line:
                try:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    # Try to parse the value
                    parsed_value = self._parse_yaml_value(value)
                    metadata[key] = parsed_value
                except Exception:
                    continue

        return self._process_metadata(metadata) if metadata else {}

    def _parse_yaml_value(self, value: str) -> Any:
        """
        Parse a YAML value string into appropriate Python type.

        Args:
            value: String value to parse

        Returns:
            Parsed value (str, int, float, bool, list, etc.)
        """
        if not value:
            return ""

        # Remove quotes if present
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]

        # Try to parse as YAML
        try:
            return yaml.safe_load(value)
        except yaml.YAMLError:
            return value

    def _process_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Process and normalize metadata after extraction.

        Args:
            metadata: Raw metadata dictionary

        Returns:
            Processed metadata with normalized values
        """
        processed = {}

        for key, value in metadata.items():
            # Normalize key
            normalized_key = key.lower().strip()

            # Process value based on key type
            if normalized_key in self.date_properties:
                processed[normalized_key] = self.parse_date_property(value)
            elif normalized_key in ("tags", "tag"):
                processed["tags"] = self.extract_tags({normalized_key: value})
            else:
                processed[normalized_key] = value

        return processed

    def parse_date_property(self, value: Any) -> date | None:
        """
        Parse a date property supporting multiple date formats.

        Args:
            value: Date value in various formats (str, date, datetime)

        Returns:
            Parsed date object or None if parsing fails
        """
        if value is None:
            return None

        # Handle different input types
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        elif isinstance(value, datetime):
            return value.date()
        elif isinstance(value, str):
            return self._parse_date_string(value)
        else:
            # Try to convert to string and parse
            try:
                return self._parse_date_string(str(value))
            except Exception:
                return None

    def _parse_date_string(self, date_str: str) -> date | None:
        """
        Parse a date string using multiple strategies.

        Args:
            date_str: String representation of a date

        Returns:
            Parsed date object or None if parsing fails
        """
        if not date_str or not date_str.strip():
            return None

        date_str = date_str.strip()

        # First try dateutil parser (handles many formats automatically)
        try:
            parsed_dt = date_parser.parse(date_str)
            return parsed_dt.date()
        except (ValueError, TypeError):
            pass

        # Try manual format parsing with common date formats
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
            "%Y%m%d",  # 20240115
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def extract_tags(self, metadata: dict[str, Any]) -> list[str]:
        """
        Extract and normalize tags from metadata.

        Supports various tag formats:
        - tags: [tag1, tag2, tag3]
        - tags: tag1, tag2, tag3
        - tag: single_tag

        Args:
            metadata: Metadata dictionary potentially containing tags

        Returns:
            List of normalized tag strings
        """
        tags = []

        # Check for 'tags' field
        if "tags" in metadata:
            tags_value = metadata["tags"]
            tags.extend(self._normalize_tag_value(tags_value))

        # Check for 'tag' field (singular)
        if "tag" in metadata:
            tag_value = metadata["tag"]
            tags.extend(self._normalize_tag_value(tag_value))

        # Remove duplicates and normalize
        normalized_tags = []
        seen = set()

        for tag in tags:
            normalized = self._normalize_tag(tag)
            if normalized and normalized not in seen:
                normalized_tags.append(normalized)
                seen.add(normalized)

        return normalized_tags

    def _normalize_tag_value(self, value: Any) -> list[str]:
        """
        Normalize a tag value into a list of strings.

        Args:
            value: Tag value (string, list, or other)

        Returns:
            List of tag strings
        """
        if not value:
            return []

        if isinstance(value, list):
            return [str(tag) for tag in value if tag]
        elif isinstance(value, str):
            # Handle comma-separated tags
            if "," in value:
                return [tag.strip() for tag in value.split(",") if tag.strip()]
            else:
                return [value]
        else:
            return [str(value)]

    def _normalize_tag(self, tag: str) -> str:
        """
        Normalize a single tag string.

        Args:
            tag: Raw tag string

        Returns:
            Normalized tag string
        """
        if not tag:
            return ""

        # Convert to string and strip whitespace
        normalized = str(tag).strip()

        # Remove leading # if present
        if normalized.startswith("#"):
            normalized = normalized[1:]

        # Convert to lowercase for consistency
        normalized = normalized.lower()

        # Remove any remaining whitespace
        normalized = normalized.strip()

        return normalized

    def merge_metadata(
        self, existing: dict[str, Any], updates: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge metadata dictionaries with intelligent handling of different value types.

        Args:
            existing: Current metadata dictionary
            updates: New metadata to merge in

        Returns:
            Merged metadata dictionary
        """
        merged = existing.copy()

        for key, value in updates.items():
            if key in merged:
                # Special handling for tags - merge lists
                if (
                    key == "tags"
                    and isinstance(merged[key], list)
                    and isinstance(value, list)
                ):
                    # Combine and deduplicate tags
                    combined_tags = merged[key] + value
                    unique_tags = []
                    seen = set()
                    for tag in combined_tags:
                        normalized = self._normalize_tag(tag)
                        if normalized and normalized not in seen:
                            unique_tags.append(normalized)
                            seen.add(normalized)
                    merged[key] = unique_tags
                else:
                    # For other fields, updates override existing
                    merged[key] = value
            else:
                merged[key] = value

        return merged
