"""Test script for code indexing functionality."""

from pathlib import Path
from utils.code_indexer import CodeIndexer
from utils.code_index_store import CodeIndexStore


def test_index_this_repo():
    """Test indexing this RAG repository itself."""
    print("=" * 70)
    print("Testing Code Indexing on RAG Repository")
    print("=" * 70)
    print()

    # Index this repository
    repo_root = Path(__file__).parent
    print(f"Repository root: {repo_root}")
    print()

    # Initialize indexer
    print("1. Initializing indexer...")
    indexer = CodeIndexer(repo_name="rag", repo_root=repo_root)

    # Index the repository (exclude test files for cleaner output)
    print("2. Indexing repository...")
    count = indexer.index_repository(
        include_patterns=["**/*.py"],
        exclude_patterns=[
            "**/test_*.py",
            "**/*_test.py",
            "**/tests/**",
            "**/__pycache__/**",
        ],
        include_private=False,
    )
    print(f"   Found {count} code objects")
    print()

    # Get statistics
    stats = indexer.get_stats()
    print("3. Index statistics:")
    print(f"   Total objects: {stats['total_objects']}")
    print(f"   Unique names: {stats['unique_names']}")
    print(f"   Qualified names: {stats['qualified_names']}")
    print()
    print("   Objects by type:")
    for obj_type, obj_count in stats['type_counts'].items():
        print(f"     {obj_type}: {obj_count}")
    print()

    # Test searching
    print("4. Testing search functionality...")
    print()

    # Search for RAGSystem class
    print("   Searching for 'RAGSystem':")
    results = indexer.get_by_name("RAGSystem")
    for obj in results:
        print(f"     - {obj.qualified_name} at {obj.relative_path}:{obj.line_number}")
    print()

    # Search for query method
    print("   Searching for 'query' (should find multiple):")
    results = indexer.get_by_name("query")
    for obj in results[:5]:  # Show first 5
        print(f"     - {obj.qualified_name} [{obj.type}] at {obj.relative_path}:{obj.line_number}")
    if len(results) > 5:
        print(f"     ... and {len(results) - 5} more")
    print()

    # Test store
    print("5. Testing database storage...")
    store = CodeIndexStore(db_path="./test_code_index.db")

    # Store objects
    all_objects = indexer.get_all_objects()
    store.add_objects_batch(all_objects)
    print(f"   Stored {len(all_objects)} objects")
    print()

    # Test retrieval
    print("6. Testing database retrieval...")
    rag_system_objects = store.get_by_name("RAGSystem")
    print(f"   Found {len(rag_system_objects)} object(s) named 'RAGSystem'")
    if rag_system_objects:
        obj = rag_system_objects[0]
        print(f"     - {obj.qualified_name}")
        print(f"     - Type: {obj.type}")
        print(f"     - File: {obj.file_path}:{obj.line_number}")
        print(f"     - Docstring: {obj.docstring}")
    print()

    # Test pattern search
    print("7. Testing pattern search...")
    results = store.search_by_name_pattern("Code%", limit=5)
    print(f"   Found {len(results)} objects starting with 'Code':")
    for obj in results:
        print(f"     - {obj.qualified_name} [{obj.type}]")
    print()

    # Test getting class methods
    print("8. Testing class methods retrieval...")
    methods = store.get_class_methods("RAGSystem")
    print(f"   Found {len(methods)} methods in RAGSystem:")
    for method in methods[:10]:  # Show first 10
        print(f"     - {method.name}() at line {method.line_number}")
    if len(methods) > 10:
        print(f"     ... and {len(methods) - 10} more")
    print()

    # Get database stats
    db_stats = store.get_stats()
    print("9. Database statistics:")
    print(f"   Total objects: {db_stats['total_objects']}")
    print(f"   Repositories: {', '.join(db_stats['repo_counts'].keys())}")
    print()

    print("=" * 70)
    print("Code indexing test completed successfully!")
    print("=" * 70)
    print()
    print("You can now:")
    print("  - Use the code index in queries")
    print("  - Search for code objects directly")
    print("  - Get source code without needing GitHub URLs")
    print()
    print("Test database created at: ./test_code_index.db")
    print("(You can delete this file after testing)")


if __name__ == "__main__":
    test_index_this_repo()
