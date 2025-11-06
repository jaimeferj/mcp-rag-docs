"""Text chunking utility for splitting documents into smaller pieces."""

import re
from typing import List


class TextChunker:
    """Split text into overlapping chunks for better retrieval."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the text chunker.

        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        """
        Split text into chunks with overlap.

        Args:
            text: The text to split

        Returns:
            List of text chunks
        """
        if not text or len(text) == 0:
            return []

        # If text is shorter than chunk size, return as single chunk
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0
        prev_start = -1

        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size

            # If this is not the last chunk, try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings near the chunk boundary
                chunk_text = text[start:end]

                # Try to find the last sentence ending
                sentence_endings = [
                    m.end() for m in re.finditer(r'[.!?]\s+', chunk_text)
                ]

                if sentence_endings:
                    # Use the last sentence ending as the break point
                    end = start + sentence_endings[-1]
                else:
                    # If no sentence ending, try to break at word boundary
                    remaining_text = text[start:end]
                    last_space = remaining_text.rfind(' ')
                    if last_space > 0:
                        end = start + last_space

            # Extract chunk
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            new_start = end - self.chunk_overlap

            # Ensure we make progress even with small chunks
            if new_start <= prev_start:
                new_start = end

            prev_start = start
            start = new_start

        return chunks

    def chunk_with_metadata(
        self, text: str, doc_id: str, metadata: dict = None
    ) -> List[dict]:
        """
        Split text into chunks with metadata.

        Args:
            text: The text to split
            doc_id: Document identifier
            metadata: Additional metadata to include

        Returns:
            List of dictionaries with chunk text and metadata
        """
        chunks = self.split_text(text)
        metadata = metadata or {}

        return [
            {
                "text": chunk,
                "doc_id": doc_id,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                **metadata,
            }
            for idx, chunk in enumerate(chunks)
        ]
