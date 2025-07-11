"""
MarkdownParser for comprehensive Obsidian note content analysis.

This module provides functionality to parse Markdown content using marko AST,
extracting tasks, headings, links, and other structural elements from Obsidian notes.
"""

import re
from typing import Any

from marko import Markdown
from marko.block import (
    Document,
)
from marko.block import (
    Heading as MarkoHeading,
)
from marko.inline import CodeSpan, RawText
from marko.inline import Link as MarkoLink

from .models import Heading, Link, TaskItem


class MarkdownParser:
    """
    Handles parsing of Markdown content using marko AST for structural analysis.

    Provides methods to extract tasks, headings, links, and other elements
    from Obsidian note content with proper context and hierarchy tracking.
    """

    def __init__(self):
        """Initialize the MarkdownParser with marko configuration."""
        # Configure marko for Obsidian-style parsing
        self.markdown = Markdown()

        # Regex patterns for additional parsing
        self.task_pattern = re.compile(r"^(\s*)- \[([ xX])\] (.+)$", re.MULTILINE)
        self.internal_link_pattern = re.compile(r"\[\[([^\]]+)\]\]")
        self.tag_pattern = re.compile(r"#([a-zA-Z0-9_-]+)")

    def parse_content(
        self, content: str
    ) -> tuple[list[TaskItem], list[Heading], list[Link]]:
        """
        Parse markdown content and extract all structural elements.

        Args:
            content: Markdown content to parse

        Returns:
            Tuple of (tasks, headings, links)
        """
        if not content or not content.strip():
            return [], [], []

        # Parse with marko
        doc = self.markdown.parse(content)

        # Extract elements
        tasks = self._extract_tasks(content, doc)
        headings = self._extract_headings(doc)
        links = self._extract_links(content, doc)

        return tasks, headings, links

    def _extract_tasks(self, content: str, doc: Document) -> list[TaskItem]:
        """
        Extract task items from markdown content with enhanced hierarchy support.

        Args:
            content: Raw markdown content
            doc: Parsed marko document

        Returns:
            List of TaskItem objects with context information
        """
        tasks = []
        lines = content.split("\n")
        current_heading = None
        heading_stack = []  # Stack to track nested headings

        # Enhanced task pattern to handle various formats and indentation
        enhanced_task_pattern = re.compile(
            r"^(\s*)[-*+] \[([ xX])\] (.+)$", re.MULTILINE
        )

        # Track current heading context with hierarchy
        for i, line in enumerate(lines):
            # Check if this line is a heading
            if line.strip().startswith("#"):
                heading_match = re.match(r"^(#+)\s+(.+)$", line.strip())
                if heading_match:
                    level = len(heading_match.group(1))
                    heading_text = heading_match.group(2).strip()

                    # Update heading stack for hierarchy
                    # Remove headings at same or deeper level
                    heading_stack = [h for h in heading_stack if h["level"] < level]

                    # Add current heading
                    heading_stack.append(
                        {"level": level, "text": heading_text, "line": i + 1}
                    )

                    # Set current heading (most recent)
                    current_heading = heading_text

            # Check if this line is a task
            task_match = enhanced_task_pattern.match(line)
            if task_match:
                indent = task_match.group(1)
                status = task_match.group(2)
                text = task_match.group(3).strip()

                # Determine completion status
                completed = status.lower() in ("x", "X")

                # Calculate indentation level for nested tasks
                indent_level = len(indent)

                # Create task item with enhanced context
                task = TaskItem(
                    text=text,
                    completed=completed,
                    line_number=i + 1,  # 1-based line numbering
                    parent_heading=current_heading,
                    indent_level=indent_level,
                    heading_hierarchy=[h["text"] for h in heading_stack],
                )
                tasks.append(task)

        return tasks

    def _extract_headings(self, doc: Document) -> list[Heading]:
        """
        Extract heading elements from the document AST.

        Args:
            doc: Parsed marko document

        Returns:
            List of Heading objects with level and hierarchy information
        """
        headings = []

        def visit_node(node: Any, line_number: int = 1) -> int:
            """Recursively visit AST nodes to find headings."""
            if isinstance(node, MarkoHeading):
                # Extract heading text
                heading_text = self._extract_text_from_node(node)

                heading = Heading(
                    level=node.level, text=heading_text.strip(), line_number=line_number
                )
                headings.append(heading)

            # Visit children and track line numbers
            if hasattr(node, "children") and node.children:
                for child in node.children:
                    line_number = visit_node(child, line_number)

            # Estimate line increment (rough approximation)
            if hasattr(node, "children") and node.children:
                line_number += 1

            return line_number

        visit_node(doc)
        return headings

    def _extract_links(self, content: str, doc: Document) -> list[Link]:
        """
        Extract both internal and external links from content.

        Args:
            content: Raw markdown content
            doc: Parsed marko document

        Returns:
            List of Link objects with type information
        """
        links = []

        # Extract internal links (Obsidian-style [[links]])
        internal_matches = self.internal_link_pattern.findall(content)
        for match in internal_matches:
            # Handle [[link|display text]] format
            if "|" in match:
                url, text = match.split("|", 1)
                url = url.strip()
                text = text.strip()
            else:
                url = text = match.strip()

            link = Link(text=text, url=url, is_internal=True)
            links.append(link)

        # Extract external links from AST
        def visit_node(node: Any):
            """Recursively visit AST nodes to find external links."""
            if isinstance(node, MarkoLink):
                link_text = self._extract_text_from_node(node)

                link = Link(text=link_text.strip(), url=node.dest, is_internal=False)
                links.append(link)

            # Visit children
            if hasattr(node, "children") and node.children:
                for child in node.children:
                    visit_node(child)

        visit_node(doc)

        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in links:
            link_key = (link.text, link.url, link.is_internal)
            if link_key not in seen:
                unique_links.append(link)
                seen.add(link_key)

        return unique_links

    def _extract_text_from_node(self, node: Any) -> str:
        """
        Extract plain text content from an AST node.

        Args:
            node: AST node to extract text from

        Returns:
            Plain text content
        """
        if isinstance(node, RawText):
            return node.children
        elif isinstance(node, CodeSpan):
            return node.children
        elif hasattr(node, "children") and node.children:
            # Recursively extract text from children
            text_parts = []
            for child in node.children:
                if isinstance(child, str):
                    text_parts.append(child)
                else:
                    text_parts.append(self._extract_text_from_node(child))
            return "".join(text_parts)
        else:
            return str(node) if node else ""

    def extract_tasks_only(self, content: str) -> list[TaskItem]:
        """
        Extract only task items from content (optimized method).

        Args:
            content: Markdown content to parse

        Returns:
            List of TaskItem objects
        """
        tasks, _, _ = self.parse_content(content)
        return tasks

    def extract_headings_only(self, content: str) -> list[Heading]:
        """
        Extract only headings from content (optimized method).

        Args:
            content: Markdown content to parse

        Returns:
            List of Heading objects
        """
        _, headings, _ = self.parse_content(content)
        return headings

    def extract_links_only(self, content: str) -> list[Link]:
        """
        Extract only links from content (optimized method).

        Args:
            content: Markdown content to parse

        Returns:
            List of Link objects
        """
        _, _, links = self.parse_content(content)
        return links

    def get_task_completion_stats(self, content: str) -> dict:
        """
        Get task completion statistics from content.

        Args:
            content: Markdown content to analyze

        Returns:
            Dictionary with completion statistics
        """
        tasks = self.extract_tasks_only(content)

        if not tasks:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "pending_tasks": 0,
                "completion_ratio": 0.0,
            }

        completed = sum(1 for task in tasks if task.completed)
        pending = len(tasks) - completed

        return {
            "total_tasks": len(tasks),
            "completed_tasks": completed,
            "pending_tasks": pending,
            "completion_ratio": completed / len(tasks) if tasks else 0.0,
        }

    def get_heading_hierarchy(self, content: str) -> list[dict]:
        """
        Get heading hierarchy with nesting information.

        Args:
            content: Markdown content to analyze

        Returns:
            List of heading dictionaries with hierarchy info
        """
        headings = self.extract_headings_only(content)
        hierarchy = []

        for heading in headings:
            hierarchy.append(
                {
                    "level": heading.level,
                    "text": heading.text,
                    "line_number": heading.line_number,
                    "children": [],  # Could be expanded for nested hierarchy
                }
            )

        return hierarchy

    def find_tasks_under_heading(
        self, content: str, heading_text: str
    ) -> list[TaskItem]:
        """
        Find all tasks that appear under a specific heading.

        Args:
            content: Markdown content to search
            heading_text: Text of the heading to search under

        Returns:
            List of tasks under the specified heading
        """
        tasks = self.extract_tasks_only(content)
        return [task for task in tasks if task.parent_heading == heading_text]
