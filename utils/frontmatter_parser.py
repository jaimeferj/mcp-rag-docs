"""YAML frontmatter parser for extracting metadata from markdown files."""

import re
from typing import Optional


class FrontmatterParser:
    """Parse YAML frontmatter from markdown documents."""

    # Regex to match YAML frontmatter at the start of a file
    FRONTMATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n',
        re.DOTALL | re.MULTILINE
    )

    @staticmethod
    def parse(markdown_text: str) -> tuple[dict, str]:
        """
        Parse frontmatter from markdown text.

        Args:
            markdown_text: The markdown document text

        Returns:
            Tuple of (metadata_dict, content_without_frontmatter)
        """
        match = FrontmatterParser.FRONTMATTER_PATTERN.match(markdown_text)

        if not match:
            # No frontmatter found
            return {}, markdown_text

        frontmatter_text = match.group(1)
        content = markdown_text[match.end():]

        # Parse YAML frontmatter into dict
        metadata = FrontmatterParser._parse_yaml(frontmatter_text)

        return metadata, content

    @staticmethod
    def _parse_yaml(yaml_text: str) -> dict:
        """
        Simple YAML parser for frontmatter.

        Handles basic key-value pairs. For complex YAML, consider using PyYAML library.

        Args:
            yaml_text: YAML frontmatter text

        Returns:
            Dictionary of metadata
        """
        metadata = {}

        # Split into lines and parse key-value pairs
        for line in yaml_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Match key: value pattern
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                # Handle boolean values
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                # Handle numeric values
                elif value.isdigit():
                    value = int(value)

                metadata[key] = value

        return metadata

    @staticmethod
    def get_title(metadata: dict) -> Optional[str]:
        """
        Extract the title from frontmatter metadata.

        Tries multiple common title fields in order of preference.

        Args:
            metadata: Parsed frontmatter metadata

        Returns:
            Title string or None if not found
        """
        # Try different title fields in order of preference
        title_fields = ['title', 'sidebar_label', 'name', 'heading']

        for field in title_fields:
            if field in metadata and metadata[field]:
                return str(metadata[field])

        return None
