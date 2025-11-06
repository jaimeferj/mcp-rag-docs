"""Hierarchical chunker that preserves markdown document structure."""

import re
from typing import List, Optional

from utils.frontmatter_parser import FrontmatterParser
from utils.markdown_parser import MarkdownParser
from utils.text_chunker import TextChunker


class HierarchicalChunker:
    """Chunk documents while preserving hierarchical structure."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the hierarchical chunker.

        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_chunker = TextChunker(chunk_size, chunk_overlap)

    def chunk_markdown(
        self, markdown_text: str, path_prefix: Optional[str] = None
    ) -> List[dict]:
        """
        Chunk markdown text while preserving section hierarchy.

        Args:
            markdown_text: The markdown document text
            path_prefix: Optional filesystem path prefix to prepend to section paths

        Returns:
            List of dicts with 'text', 'section_path', 'section_level'
        """
        if not markdown_text or not markdown_text.strip():
            return []

        # Parse frontmatter
        frontmatter, content = FrontmatterParser.parse(markdown_text)
        frontmatter_title = FrontmatterParser.get_title(frontmatter)

        # Parse markdown structure from content (without frontmatter)
        sections = MarkdownParser.parse(content)

        if not sections:
            # Fallback to basic text chunking
            chunks = self.text_chunker.split_text(content)

            # Build path with filesystem + frontmatter
            base_path = self._build_base_path(path_prefix, frontmatter_title)

            return [
                {
                    "text": chunk,
                    "section_path": base_path,
                    "section_level": 0,
                }
                for chunk in chunks
            ]

        result_chunks = []

        for section in sections:
            # Build full section path: filesystem > frontmatter > markdown headers
            full_section_path = self._build_full_section_path(
                path_prefix, frontmatter_title, section.breadcrumb
            )

            # Get full section text including header
            section_header = "#" * section.level + " " + section.title
            section_full_text = section_header + "\n\n" + section.content

            # Check if section fits in one chunk
            if len(section_full_text) <= self.chunk_size:
                result_chunks.append(
                    {
                        "text": section_full_text.strip(),
                        "section_path": full_section_path,
                        "section_level": section.level,
                    }
                )
            else:
                # Section is too large, need to split it
                # Split content while keeping section context
                content_chunks = self._split_large_section(
                    section_header, section.content, full_section_path, section.level
                )
                result_chunks.extend(content_chunks)

        return result_chunks

    def _build_base_path(
        self, path_prefix: Optional[str], frontmatter_title: Optional[str]
    ) -> str:
        """Build base path from filesystem and frontmatter."""
        parts = []
        if path_prefix:
            parts.append(path_prefix)
        if frontmatter_title:
            parts.append(frontmatter_title)

        return " > ".join(parts) if parts else "Document"

    def _build_full_section_path(
        self,
        path_prefix: Optional[str],
        frontmatter_title: Optional[str],
        section_breadcrumb: str,
    ) -> str:
        """Build full section path combining all levels of hierarchy."""
        parts = []

        # Add filesystem path
        if path_prefix:
            parts.append(path_prefix)

        # Add frontmatter title (if it's not redundant with first section)
        if frontmatter_title:
            # Check if section breadcrumb starts with frontmatter title
            # to avoid redundancy like "Quickstart > Quickstart > Prerequisites"
            first_section = section_breadcrumb.split(" > ")[0]
            if frontmatter_title.lower() != first_section.lower():
                parts.append(frontmatter_title)

        # Add markdown section breadcrumb
        parts.append(section_breadcrumb)

        return " > ".join(parts)

    def _split_large_section(
        self, header: str, content: str, breadcrumb: str, level: int
    ) -> List[dict]:
        """
        Split a large section into multiple chunks while maintaining context.

        Args:
            header: Section header text (e.g., "## Installation")
            content: Section content
            breadcrumb: Full section path
            level: Header level

        Returns:
            List of chunk dictionaries
        """
        chunks = []

        # Calculate space available for content (reserve space for header)
        header_with_spacing = header + "\n\n"
        available_size = self.chunk_size - len(header_with_spacing)

        if available_size <= 0:
            # Header itself is too long, just split the content
            content_chunks = self.text_chunker.split_text(content)
            return [
                {
                    "text": chunk,
                    "section_path": breadcrumb,
                    "section_level": level,
                }
                for chunk in content_chunks
            ]

        # Split content into smaller pieces
        content_parts = self.text_chunker.split_text(content)

        for part in content_parts:
            # Prepend header to each chunk for context
            chunk_text = header_with_spacing + part
            chunks.append(
                {
                    "text": chunk_text.strip(),
                    "section_path": breadcrumb,
                    "section_level": level,
                }
            )

        return chunks

    def chunk_with_metadata(
        self, text: str, doc_id: str, is_markdown: bool = True, extra_metadata: dict = None
    ) -> List[dict]:
        """
        Chunk text with full metadata.

        Args:
            text: The text to chunk
            doc_id: Document identifier
            is_markdown: Whether to use markdown-aware chunking
            extra_metadata: Additional metadata to include (should include 'path_structure')

        Returns:
            List of dictionaries with chunk text and metadata
        """
        extra_metadata = extra_metadata or {}

        # Extract filesystem path structure from metadata
        path_structure = extra_metadata.get("path_structure")

        if is_markdown:
            chunks = self.chunk_markdown(text, path_prefix=path_structure)
        else:
            # Fallback to basic text chunking for non-markdown
            text_chunks = self.text_chunker.split_text(text)
            base_path = path_structure if path_structure else "Document"
            chunks = [
                {
                    "text": chunk,
                    "section_path": base_path,
                    "section_level": 0,
                }
                for chunk in text_chunks
            ]

        # Add full metadata to each chunk
        return [
            {
                "text": chunk["text"],
                "doc_id": doc_id,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "section_path": chunk["section_path"],
                "section_level": chunk["section_level"],
                **extra_metadata,
            }
            for idx, chunk in enumerate(chunks)
        ]
