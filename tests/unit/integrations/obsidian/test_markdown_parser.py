"""
Unit tests for MarkdownParser functionality.

Tests the parsing of Markdown content using marko AST, including task extraction,
heading parsing, and link detection using the example vault notes.
"""

import unittest
from pathlib import Path

from the_assistant.integrations.obsidian import MarkdownParser


class TestMarkdownParser(unittest.TestCase):
    """Test cases for MarkdownParser functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = MarkdownParser()
        self.vault_path = Path("obsidian_vault")

    def test_parse_trip_note_tasks(self):
        """Test task extraction from Trip to Paris note."""
        with open(self.vault_path / "Trip to Paris.md") as f:
            content = f.read()

        # Remove frontmatter for content parsing
        content_lines = content.split("\n")
        if content_lines[0].strip() == "---":
            # Find end of frontmatter
            for i, line in enumerate(content_lines[1:], 1):
                if line.strip() == "---":
                    content = "\n".join(content_lines[i + 1 :])
                    break

        tasks = self.parser.extract_tasks_only(content)

        # Should find 5 tasks
        self.assertEqual(len(tasks), 5)

        # Check specific tasks
        task_texts = [task.text for task in tasks]
        self.assertIn("Book airport transfer", task_texts)
        self.assertIn("Pack winter clothes", task_texts)
        self.assertIn("Download offline maps", task_texts)
        self.assertIn("Confirm hotel reservation", task_texts)
        self.assertIn("Exchange currency", task_texts)

        # Check completion status
        completed_tasks = [task for task in tasks if task.completed]
        self.assertEqual(len(completed_tasks), 1)
        self.assertEqual(completed_tasks[0].text, "Confirm hotel reservation")

        # Check parent heading context
        tasks_under_tasks_heading = [
            task for task in tasks if task.parent_heading == "Tasks"
        ]
        self.assertEqual(len(tasks_under_tasks_heading), 5)

    def test_parse_french_lesson_tasks(self):
        """Test task extraction from French Lesson Notes."""
        with open(self.vault_path / "French Lesson Notes.md") as f:
            content = f.read()

        # Remove frontmatter
        content_lines = content.split("\n")
        if content_lines[0].strip() == "---":
            for i, line in enumerate(content_lines[1:], 1):
                if line.strip() == "---":
                    content = "\n".join(content_lines[i + 1 :])
                    break

        tasks = self.parser.extract_tasks_only(content)

        # Should find 4 tasks
        self.assertEqual(len(tasks), 4)

        # Check completion status
        completed_tasks = [task for task in tasks if task.completed]
        pending_tasks = [task for task in tasks if not task.completed]

        self.assertEqual(len(completed_tasks), 1)
        self.assertEqual(len(pending_tasks), 3)

        # Check specific completed task
        self.assertEqual(completed_tasks[0].text, "Review last week's vocabulary")

        # Check parent heading
        homework_tasks = [task for task in tasks if task.parent_heading == "Homework"]
        self.assertEqual(len(homework_tasks), 4)

    def test_parse_work_project_tasks(self):
        """Test task extraction from Work Project Alpha note."""
        with open(self.vault_path / "Work Project Alpha.md") as f:
            content = f.read()

        # Remove frontmatter
        content_lines = content.split("\n")
        if content_lines[0].strip() == "---":
            for i, line in enumerate(content_lines[1:], 1):
                if line.strip() == "---":
                    content = "\n".join(content_lines[i + 1 :])
                    break

        tasks = self.parser.extract_tasks_only(content)

        # Should find 6 tasks
        self.assertEqual(len(tasks), 6)

        # Check completion status
        completed_tasks = [task for task in tasks if task.completed]
        pending_tasks = [task for task in tasks if not task.completed]

        self.assertEqual(len(completed_tasks), 2)
        self.assertEqual(len(pending_tasks), 4)

        # Check specific tasks
        completed_texts = [task.text for task in completed_tasks]
        self.assertIn("Requirements gathering", completed_texts)
        self.assertIn("UI/UX design mockups", completed_texts)

    def test_extract_headings(self):
        """Test heading extraction from markdown content."""
        content = """# Main Title

## Section 1
Some content here.

### Subsection 1.1
More content.

## Section 2
Final content.
"""

        headings = self.parser.extract_headings_only(content)

        # Should find 4 headings
        self.assertEqual(len(headings), 4)

        # Check heading levels and text
        self.assertEqual(headings[0].level, 1)
        self.assertEqual(headings[0].text, "Main Title")

        self.assertEqual(headings[1].level, 2)
        self.assertEqual(headings[1].text, "Section 1")

        self.assertEqual(headings[2].level, 3)
        self.assertEqual(headings[2].text, "Subsection 1.1")

        self.assertEqual(headings[3].level, 2)
        self.assertEqual(headings[3].text, "Section 2")

    def test_extract_links(self):
        """Test link extraction from markdown content."""
        content = """# Test Links

Here's an [[Internal Link]] and another [[Link with|Display Text]].

Also check out [External Link](https://example.com) and [Google](https://google.com).

More internal links: [[Another Note]] and [[Final Link]].
"""

        links = self.parser.extract_links_only(content)

        # Should find both internal and external links
        internal_links = [link for link in links if link.is_internal]
        external_links = [link for link in links if not link.is_internal]

        self.assertEqual(len(internal_links), 4)
        self.assertEqual(len(external_links), 2)

        # Check specific internal links
        internal_texts = [link.text for link in internal_links]
        self.assertIn("Internal Link", internal_texts)
        self.assertIn("Display Text", internal_texts)
        self.assertIn("Another Note", internal_texts)
        self.assertIn("Final Link", internal_texts)

        # Check external links
        external_urls = [link.url for link in external_links]
        self.assertIn("https://example.com", external_urls)
        self.assertIn("https://google.com", external_urls)

    def test_task_completion_stats(self):
        """Test task completion statistics calculation."""
        content = """# Test Tasks

## Todo List
- [x] Completed task 1
- [ ] Pending task 1
- [x] Completed task 2
- [ ] Pending task 2
- [ ] Pending task 3
"""

        stats = self.parser.get_task_completion_stats(content)

        self.assertEqual(stats["total_tasks"], 5)
        self.assertEqual(stats["completed_tasks"], 2)
        self.assertEqual(stats["pending_tasks"], 3)
        self.assertEqual(stats["completion_ratio"], 0.4)

    def test_find_tasks_under_heading(self):
        """Test finding tasks under specific headings."""
        content = """# Main Title

## Shopping List
- [ ] Buy milk
- [x] Buy bread
- [ ] Buy eggs

## Work Tasks
- [ ] Finish report
- [ ] Send emails

## Personal
- [x] Call mom
"""

        shopping_tasks = self.parser.find_tasks_under_heading(content, "Shopping List")
        work_tasks = self.parser.find_tasks_under_heading(content, "Work Tasks")
        personal_tasks = self.parser.find_tasks_under_heading(content, "Personal")

        self.assertEqual(len(shopping_tasks), 3)
        self.assertEqual(len(work_tasks), 2)
        self.assertEqual(len(personal_tasks), 1)

        # Check specific tasks
        shopping_texts = [task.text for task in shopping_tasks]
        self.assertIn("Buy milk", shopping_texts)
        self.assertIn("Buy bread", shopping_texts)
        self.assertIn("Buy eggs", shopping_texts)

    def test_empty_content(self):
        """Test parsing empty or whitespace-only content."""
        empty_tasks = self.parser.extract_tasks_only("")
        empty_headings = self.parser.extract_headings_only("   ")
        empty_links = self.parser.extract_links_only("\n\n")

        self.assertEqual(len(empty_tasks), 0)
        self.assertEqual(len(empty_headings), 0)
        self.assertEqual(len(empty_links), 0)

    def test_parse_content_integration(self):
        """Test the main parse_content method integration."""
        content = """# Test Note

## Tasks
- [x] Done task
- [ ] Todo task

## Links
Check out [[Internal Link]] and [External](https://example.com).
"""

        tasks, headings, links = self.parser.parse_content(content)

        self.assertEqual(len(tasks), 2)
        self.assertEqual(len(headings), 3)
        self.assertEqual(len(links), 2)

        # Verify integration
        self.assertEqual(headings[0].text, "Test Note")
        self.assertEqual(headings[1].text, "Tasks")
        self.assertEqual(headings[2].text, "Links")

        self.assertTrue(tasks[0].completed)
        self.assertFalse(tasks[1].completed)

        self.assertTrue(links[0].is_internal)
        self.assertFalse(links[1].is_internal)


if __name__ == "__main__":
    unittest.main()
