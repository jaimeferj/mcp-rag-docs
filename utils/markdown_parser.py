"""Markdown structure parser for extracting hierarchical information."""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MarkdownSection:
    """Represents a section in a markdown document."""

    level: int  # Heading level (1-6 for h1-h6)
    title: str  # Section title
    content: str  # Content under this section
    start_pos: int  # Start position in original text
    end_pos: int  # End position in original text
    breadcrumb: str  # Full path (e.g., "Installation > Prerequisites > Python")
    parent: Optional["MarkdownSection"] = None


class MarkdownParser:
    """Parse markdown documents to extract hierarchical structure."""

    # Regex for markdown headers (# Header, ## Header, etc.)
    HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)(?:\s*\{[^}]*\})?\s*$", re.MULTILINE)

    @staticmethod
    def parse(markdown_text: str) -> List[MarkdownSection]:
        """
        Parse markdown text and return list of sections with hierarchy.

        Args:
            markdown_text: The markdown document text

        Returns:
            List of MarkdownSection objects with hierarchical information
        """
        if not markdown_text or not markdown_text.strip():
            return []

        sections = []
        header_stack = []  # Stack to track current hierarchy

        # Find all headers
        headers = list(MarkdownParser.HEADER_PATTERN.finditer(markdown_text))

        if not headers:
            # No headers found, treat entire document as single section
            return [
                MarkdownSection(
                    level=0,
                    title="Document",
                    content=markdown_text,
                    start_pos=0,
                    end_pos=len(markdown_text),
                    breadcrumb="Document",
                    parent=None,
                )
            ]

        for i, header_match in enumerate(headers):
            level = len(header_match.group(1))  # Count # characters
            title = header_match.group(2).strip()
            start_pos = header_match.start()

            # Determine end position (start of next header or end of document)
            if i + 1 < len(headers):
                end_pos = headers[i + 1].start()
            else:
                end_pos = len(markdown_text)

            # Extract content (everything after this header until next header)
            content = markdown_text[header_match.end() : end_pos].strip()

            # Build breadcrumb by managing header stack
            # Pop headers from stack that are same level or deeper
            while header_stack and header_stack[-1]["level"] >= level:
                header_stack.pop()

            # Build breadcrumb path
            breadcrumb_parts = [h["title"] for h in header_stack] + [title]
            breadcrumb = " > ".join(breadcrumb_parts)

            # Get parent section
            parent = header_stack[-1]["section"] if header_stack else None

            # Create section
            section = MarkdownSection(
                level=level,
                title=title,
                content=content,
                start_pos=start_pos,
                end_pos=end_pos,
                breadcrumb=breadcrumb,
                parent=parent,
            )

            sections.append(section)

            # Add to stack for future sections
            header_stack.append({"level": level, "title": title, "section": section})

        return sections

    @staticmethod
    def get_section_boundaries(markdown_text: str) -> List[tuple[int, int, int, str]]:
        """
        Get section boundaries for chunking.

        Returns:
            List of tuples: (start_pos, end_pos, level, breadcrumb)
        """
        sections = MarkdownParser.parse(markdown_text)
        return [
            (section.start_pos, section.end_pos, section.level, section.breadcrumb)
            for section in sections
        ]

    @staticmethod
    def extract_toc(markdown_text: str) -> List[dict]:
        """
        Extract table of contents from markdown.

        Returns:
            List of dicts with 'level', 'title', and 'breadcrumb'
        """
        sections = MarkdownParser.parse(markdown_text)
        return [
            {
                "level": section.level,
                "title": section.title,
                "breadcrumb": section.breadcrumb,
            }
            for section in sections
        ]
