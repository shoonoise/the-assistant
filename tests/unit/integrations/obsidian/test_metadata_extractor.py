"""
Unit tests for MetadataExtractor using example vault notes.

Tests the robust YAML frontmatter parsing, date handling, tag normalization,
and error handling capabilities of the MetadataExtractor class.
"""

from datetime import date, datetime
from pathlib import Path

import pytest

from the_assistant.integrations.obsidian import MetadataExtractor


class TestMetadataExtractor:
    """Test suite for MetadataExtractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create a MetadataExtractor instance for testing."""
        return MetadataExtractor()

    @pytest.fixture
    def vault_path(self):
        """Path to the test vault directory."""
        return Path("obsidian_vault")

    def test_extract_trip_note_metadata(self, extractor, vault_path):
        """Test extracting metadata from Tokyo trip note."""
        tokyo_note_path = vault_path / "Business Trip to Tokyo.md"
        with open(tokyo_note_path) as f:
            content = f.read()

        metadata, remaining_content = extractor.extract_frontmatter(content)

        # Verify metadata extraction
        assert "tags" in metadata
        assert "trip" in metadata["tags"]
        assert "business" in metadata["tags"]
        assert "travel" in metadata["tags"]
        assert "japan" in metadata["tags"]

        # Verify date parsing
        assert metadata["date"] == date(2025, 1, 15)
        assert metadata["start_date"] == date(2025, 2, 10)
        assert metadata["end_date"] == date(2025, 2, 17)

        # Verify other properties
        assert metadata["destination"] == "Tokyo"
        assert metadata["status"] == "booked"
        assert metadata["trip_type"] == "business"
        assert metadata["company"] == "TechCorp Inc"

        # Verify content separation
        assert remaining_content.strip().startswith("# Business Trip to Tokyo")
        assert "---" not in remaining_content

    def test_extract_paris_note_metadata(self, extractor, vault_path):
        """Test extracting metadata from Paris trip note."""
        paris_note_path = vault_path / "Trip to Paris.md"
        with open(paris_note_path) as f:
            content = f.read()

        metadata, remaining_content = extractor.extract_frontmatter(content)

        # Verify tags
        assert "tags" in metadata
        expected_tags = {"trip", "travel", "france"}
        assert set(metadata["tags"]) == expected_tags

        # Verify dates
        assert metadata["date"] == date(2025, 1, 15)
        assert metadata["start_date"] == date(2025, 3, 15)
        assert metadata["end_date"] == date(2025, 3, 22)

        # Verify properties
        assert metadata["status"] == "planning"
        assert metadata["destination"] == "Paris"

    def test_extract_french_lesson_metadata(self, extractor, vault_path):
        """Test extracting metadata from French lesson note."""
        lesson_note_path = vault_path / "French Lesson Notes.md"
        with open(lesson_note_path) as f:
            content = f.read()

        metadata, remaining_content = extractor.extract_frontmatter(content)

        # Verify tags
        assert "tags" in metadata
        expected_tags = {"french-lesson", "language", "learning"}
        assert set(metadata["tags"]) == expected_tags

        # Verify dates
        assert metadata["date"] == date(2025, 1, 15)
        assert metadata["next_lesson"] == date(2025, 1, 20)

        # Verify properties
        assert metadata["teacher"] == "Marie Dubois"
        assert metadata["topic"] == "passé composé"
        assert metadata["status"] == "active"

    def test_extract_work_project_metadata(self, extractor, vault_path):
        """Test extracting metadata from work project note."""
        work_note_path = vault_path / "Work Project Alpha.md"
        with open(work_note_path) as f:
            content = f.read()

        metadata, remaining_content = extractor.extract_frontmatter(content)

        # Verify tags
        assert "tags" in metadata
        expected_tags = {"work", "project", "deadline"}
        assert set(metadata["tags"]) == expected_tags

        # Verify dates
        assert metadata["date"] == date(2025, 1, 15)
        assert metadata["start_date"] == date(2025, 1, 10)
        assert metadata["deadline"] == date(2025, 3, 1)

        # Verify properties
        assert metadata["project_name"] == "Customer Dashboard"
        assert metadata["status"] == "in_progress"
        assert metadata["priority"] == "high"

    def test_extract_daily_journal_metadata(self, extractor, vault_path):
        """Test extracting metadata from daily journal note."""
        journal_note_path = vault_path / "Daily Journal - Jan 15.md"
        with open(journal_note_path) as f:
            content = f.read()

        metadata, remaining_content = extractor.extract_frontmatter(content)

        # Verify tags
        assert "tags" in metadata
        expected_tags = {"journal", "daily", "personal"}
        assert set(metadata["tags"]) == expected_tags

        # Verify date
        assert metadata["date"] == date(2025, 1, 15)

        # Verify properties
        assert metadata["mood"] == "productive"
        assert metadata["weather"] == "sunny"

    def test_parse_various_date_formats(self, extractor):
        """Test parsing different date formats."""
        test_cases = [
            ("2025-01-15", date(2025, 1, 15)),
            ("01/15/2025", date(2025, 1, 15)),
            ("15/01/2025", date(2025, 1, 15)),
            ("January 15, 2025", date(2025, 1, 15)),
            ("Jan 15, 2025", date(2025, 1, 15)),
            ("15 January 2025", date(2025, 1, 15)),
            ("15 Jan 2025", date(2025, 1, 15)),
            ("2025/01/15", date(2025, 1, 15)),
            ("15-01-2025", date(2025, 1, 15)),
        ]

        for date_str, expected_date in test_cases:
            parsed_date = extractor.parse_date_property(date_str)
            assert parsed_date == expected_date, f"Failed to parse {date_str}"

    def test_parse_invalid_dates(self, extractor):
        """Test handling of invalid date formats."""
        invalid_dates = [
            "not a date",
            "2025-13-45",  # Invalid month/day
            "",
            None,
            "sometime in 2025",
        ]

        for invalid_date in invalid_dates:
            parsed_date = extractor.parse_date_property(invalid_date)
            assert parsed_date is None, f"Should not parse invalid date: {invalid_date}"

    def test_tag_normalization(self, extractor):
        """Test tag extraction and normalization."""
        test_cases = [
            # List format
            ({"tags": ["Trip", "TRAVEL", "#france"]}, ["trip", "travel", "france"]),
            # String format
            ({"tags": "work, project, #deadline"}, ["work", "project", "deadline"]),
            # Single tag
            ({"tag": "#french-lesson"}, ["french-lesson"]),
            # Mixed case and whitespace
            (
                {"tags": [" WORK ", "#Project", "DeadLine "]},
                ["work", "project", "deadline"],
            ),
        ]

        for metadata_input, expected_tags in test_cases:
            extracted_tags = extractor.extract_tags(metadata_input)
            assert set(extracted_tags) == set(expected_tags)

    def test_malformed_frontmatter_handling(self, extractor):
        """Test handling of malformed YAML frontmatter."""
        malformed_content = """---
tags:
  - trip
  - travel
date: 2025-01-15
status: planning
# Missing closing ---

# This is the content
Some note content here.
"""

        # Should handle gracefully - since there's no closing ---, treat as no frontmatter
        metadata, remaining_content = extractor.extract_frontmatter(malformed_content)

        # Should return empty metadata and original content since no closing ---
        assert metadata == {}
        assert remaining_content == malformed_content

    def test_no_frontmatter(self, extractor):
        """Test handling content without frontmatter."""
        content_without_frontmatter = """# Regular Note

This note has no frontmatter.

## Section
Some content here.
"""

        metadata, remaining_content = extractor.extract_frontmatter(
            content_without_frontmatter
        )

        assert metadata == {}
        assert remaining_content == content_without_frontmatter

    def test_empty_frontmatter(self, extractor):
        """Test handling empty frontmatter."""
        content_with_empty_frontmatter = """---
---

# Note with Empty Frontmatter

Content goes here.
"""

        metadata, remaining_content = extractor.extract_frontmatter(
            content_with_empty_frontmatter
        )

        assert metadata == {}
        assert remaining_content.strip().startswith("# Note with Empty Frontmatter")

    def test_metadata_merging(self, extractor):
        """Test merging metadata dictionaries."""
        existing = {
            "tags": ["work", "project"],
            "status": "in_progress",
            "priority": "medium",
        }

        updates = {
            "tags": ["deadline", "urgent"],
            "status": "completed",
            "assignee": "John Doe",
        }

        merged = extractor.merge_metadata(existing, updates)

        # Tags should be combined and deduplicated
        expected_tags = {"work", "project", "deadline", "urgent"}
        assert set(merged["tags"]) == expected_tags

        # Other fields should be updated
        assert merged["status"] == "completed"
        assert merged["priority"] == "medium"  # Preserved from existing
        assert merged["assignee"] == "John Doe"  # Added from updates

    def test_date_property_types(self, extractor):
        """Test parsing different date property input types."""
        # Test with actual date object
        test_date = date(2025, 1, 15)
        assert extractor.parse_date_property(test_date) == test_date

        # Test with datetime object
        test_datetime = datetime(2025, 1, 15, 14, 30)
        assert extractor.parse_date_property(test_datetime) == test_date

        # Test with string
        assert extractor.parse_date_property("2025-01-15") == test_date

        # Test with None
        assert extractor.parse_date_property(None) is None

    def test_partial_yaml_extraction(self, extractor):
        """Test extraction from partially valid YAML."""
        partial_yaml_content = """---
tags:
  - trip
  - travel
date: 2025-01-15
status: planning
invalid_yaml: [unclosed list
destination: Paris
---

# Content starts here
"""

        metadata, remaining_content = extractor.extract_frontmatter(
            partial_yaml_content
        )

        # Should extract valid parts
        assert "date" in metadata
        assert metadata["date"] == date(2025, 1, 15)
        assert "destination" in metadata
        assert metadata["destination"] == "Paris"

        # Content should be properly separated
        assert remaining_content.strip().startswith("# Content starts here")


if __name__ == "__main__":
    pytest.main([__file__])
