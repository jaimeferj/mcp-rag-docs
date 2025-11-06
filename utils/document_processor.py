"""Document processor for handling text and markdown files."""

import hashlib
from pathlib import Path
from typing import Optional

import aiofiles


class DocumentProcessor:
    """Process and extract content from documents."""

    SUPPORTED_EXTENSIONS = {".txt", ".md"}

    @staticmethod
    def is_supported(file_path: str | Path) -> bool:
        """Check if the file extension is supported."""
        path = Path(file_path)
        return path.suffix.lower() in DocumentProcessor.SUPPORTED_EXTENSIONS

    @staticmethod
    async def read_file(file_path: str | Path) -> str:
        """Read file content asynchronously."""
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            return await f.read()

    @staticmethod
    def generate_doc_id(content: str, filename: str) -> str:
        """Generate a unique document ID based on content and filename."""
        hash_input = f"{filename}:{content}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    @staticmethod
    def extract_metadata(file_path: str | Path, base_path: Optional[str | Path] = None) -> dict[str, str]:
        """
        Extract metadata from the file.

        Args:
            file_path: Path to the document file
            base_path: Optional base path to extract relative path from

        Returns:
            Dictionary with metadata including filesystem path
        """
        path = Path(file_path).resolve()

        # Extract filesystem path structure
        path_structure = None
        if base_path:
            base = Path(base_path).resolve()
            try:
                # Get relative path from base
                rel_path = path.relative_to(base)
                # Convert to breadcrumb format (without filename)
                parts = list(rel_path.parts[:-1])  # Exclude filename
                if parts:
                    path_structure = " > ".join(parts)
            except ValueError:
                # File is not relative to base_path, skip path structure
                pass

        return {
            "filename": path.name,
            "extension": path.suffix.lower(),
            "file_type": "text" if path.suffix == ".txt" else "markdown",
            "path_structure": path_structure,
        }

    async def process_document(
        self, file_path: str | Path, content: Optional[str] = None, base_path: Optional[str | Path] = None
    ) -> dict[str, str]:
        """
        Process a document and return its content with metadata.

        Args:
            file_path: Path to the document file
            content: Optional pre-loaded content (if None, will read from file)
            base_path: Optional base path to extract relative path structure from

        Returns:
            Dictionary with 'content', 'doc_id', and metadata fields
        """
        if not self.is_supported(file_path):
            raise ValueError(
                f"Unsupported file type. Supported: {self.SUPPORTED_EXTENSIONS}"
            )

        # Read content if not provided
        if content is None:
            content = await self.read_file(file_path)

        # Extract metadata with path structure
        metadata = self.extract_metadata(file_path, base_path)
        doc_id = self.generate_doc_id(content, metadata["filename"])

        return {
            "doc_id": doc_id,
            "content": content,
            **metadata,
        }
