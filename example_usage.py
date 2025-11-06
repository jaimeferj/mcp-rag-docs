"""Example script demonstrating how to use the RAG system programmatically."""

import asyncio
from pathlib import Path

from rag_server.rag_system import RAGSystem


async def main():
    """Demonstrate RAG system usage."""
    print("RAG System Example Usage")
    print("=" * 50)
    print()

    # Initialize RAG system
    print("Initializing RAG system...")
    rag = RAGSystem()
    print("✓ RAG system initialized\n")

    # Check if example document exists
    example_doc = Path("example_document.md")
    if not example_doc.exists():
        print("✗ example_document.md not found")
        print("Please ensure example_document.md exists in the current directory")
        return

    # Add a document
    print(f"Adding document: {example_doc}")
    result = await rag.add_document(example_doc)
    print(f"✓ Document added successfully!")
    print(f"  - Doc ID: {result['doc_id']}")
    print(f"  - Filename: {result['filename']}")
    print(f"  - Chunks: {result['num_chunks']}")
    print()

    # List documents
    print("Listing all documents...")
    documents = rag.list_documents()
    print(f"✓ Found {len(documents)} document(s)")
    for doc in documents:
        print(f"  - {doc['filename']} (ID: {doc['doc_id']})")
    print()

    # Get stats
    print("System statistics...")
    stats = rag.get_stats()
    print(f"  - Total documents: {stats['total_documents']}")
    print(f"  - Total chunks: {stats['total_chunks']}")
    print()

    # Query the RAG system
    questions = [
        "What is RAG?",
        "What file formats are supported?",
        "What models does this system use?",
    ]

    for question in questions:
        print(f"Question: {question}")
        print("-" * 50)

        result = rag.query(question, top_k=3)

        print(f"Answer: {result['answer']}\n")
        print(f"Sources ({len(result['sources'])}):")
        for source in result["sources"]:
            print(
                f"  - {source['filename']} (chunk {source['chunk_index']}, score: {source['score']:.4f})"
            )
        print("\n")

    # Optional: Delete the document
    print("Cleaning up...")
    chunks_deleted = rag.delete_document(result['doc_id'] if result else documents[0]['doc_id'])
    print(f"✓ Deleted document ({chunks_deleted} chunks removed)")
    print()

    print("=" * 50)
    print("Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
