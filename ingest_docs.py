"""Script to batch-ingest documentation into the RAG system."""

import asyncio
import sys
from pathlib import Path

from rag_server.rag_system import RAGSystem


async def ingest_directory(
    rag_system: RAGSystem,
    docs_dir: str | Path,
    base_path: str | Path,
    tags: list[str] = None,
    pattern: str = "**/*.md",
):
    """
    Recursively ingest all markdown files from a directory.

    Args:
        rag_system: RAG system instance
        docs_dir: Directory containing documentation files
        base_path: Base path to extract relative structure from
        tags: Tags to apply to all documents
        pattern: Glob pattern for files to ingest (default: **/*.md)
    """
    docs_path = Path(docs_dir).expanduser().resolve()
    base = Path(base_path).expanduser().resolve()
    tags = tags or []

    if not docs_path.exists():
        print(f"Error: Directory not found: {docs_path}")
        return

    # Find all markdown files
    md_files = list(docs_path.glob(pattern))

    if not md_files:
        print(f"No files matching pattern '{pattern}' found in {docs_path}")
        return

    print(f"Found {len(md_files)} files to ingest...")
    print(f"Base path: {base}")
    print(f"Tags: {', '.join(tags) if tags else 'none'}")
    print()

    successful = 0
    failed = 0

    for i, file_path in enumerate(md_files, 1):
        try:
            # Get relative path for display
            try:
                rel_path = file_path.relative_to(base)
            except ValueError:
                rel_path = file_path

            print(f"[{i}/{len(md_files)}] Processing: {rel_path}")

            # Add document to RAG system
            result = await rag_system.add_document(
                file_path,
                tags=tags,
                base_path=base,
            )

            print(f"  ✓ Added: {result['num_chunks']} chunks")
            print(f"    Doc ID: {result['doc_id']}")
            successful += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1

        print()

    print("=" * 60)
    print(f"Ingestion complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(md_files)}")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python ingest_docs.py <docs_directory> [base_path] [tags]")
        print()
        print("Example:")
        print("  python ingest_docs.py ~/dagster/docs/docs")
        print("  python ingest_docs.py ~/dagster/docs/docs ~/dagster/docs/docs dagster,docs")
        sys.exit(1)

    docs_dir = sys.argv[1]
    base_path = sys.argv[2] if len(sys.argv) > 2 else docs_dir
    tags = sys.argv[3].split(",") if len(sys.argv) > 3 else ["dagster", "docs"]

    print("RAG Documentation Ingestion Tool")
    print("=" * 60)
    print()

    # Initialize RAG system
    print("Initializing RAG system...")
    rag_system = RAGSystem()
    print("✓ RAG system initialized")
    print()

    # Ingest documents
    await ingest_directory(
        rag_system=rag_system,
        docs_dir=docs_dir,
        base_path=base_path,
        tags=tags,
    )

    # Show final stats
    stats = rag_system.get_stats()
    print()
    print("RAG System Statistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total chunks: {stats['total_chunks']}")


if __name__ == "__main__":
    asyncio.run(main())
