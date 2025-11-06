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
    def extract_metadata(file_path: str | Path) -> dict[str, str]:
        """Extract metadata from the file."""
        path = Path(file_path)
        return {
            "filename": path.name,
            "extension": path.suffix.lower(),
            "file_type": "text" if path.suffix == ".txt" else "markdown",
        }

    async def process_document(
        self, file_path: str | Path, content: Optional[str] = None
    ) -> dict[str, str]:
        """
        Process a document and return its content with metadata.

        Args:
            file_path: Path to the document file
            content: Optional pre-loaded content (if None, will read from file)

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

        # Extract metadata
        metadata = self.extract_metadata(file_path)
        doc_id = self.generate_doc_id(content, metadata["filename"])

        return {
            "doc_id": doc_id,
            "content": content,
            **metadata,
        }
