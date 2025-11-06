"""CLI script to build code index for a Python repository."""

import sys
import argparse
from pathlib import Path
from utils.code_indexer import CodeIndexer
from utils.code_index_store import CodeIndexStore


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build a searchable index of Python code objects in a repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Index Dagster repository
  python build_code_index.py --repo dagster --path /home/ubuntu/dagster

  # Index with custom database location
  python build_code_index.py --repo dagster --path /home/ubuntu/dagster --db ./my_index.db

  # Include private objects (starting with _)
  python build_code_index.py --repo dagster --path /home/ubuntu/dagster --include-private

  # Re-index (replace existing data for this repo)
  python build_code_index.py --repo dagster --path /home/ubuntu/dagster --replace
        """,
    )

    parser.add_argument(
        "--repo",
        type=str,
        required=True,
        help="Repository name (e.g., 'dagster', 'pyiceberg')",
    )
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Path to repository root directory",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="./code_index.db",
        help="Path to SQLite database file (default: ./code_index.db)",
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include private objects (names starting with _)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing index for this repository",
    )
    parser.add_argument(
        "--include",
        type=str,
        nargs="+",
        default=["**/*.py"],
        help="Glob patterns to include (default: **/*.py)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        nargs="+",
        default=[
            "**/test_*.py",
            "**/*_test.py",
            "**/tests/**",
            "**/__pycache__/**",
            "**/.*/**",
        ],
        help="Glob patterns to exclude",
    )

    args = parser.parse_args()

    # Validate repository path
    repo_path = Path(args.path).expanduser().resolve()
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}")
        sys.exit(1)

    if not repo_path.is_dir():
        print(f"Error: Repository path is not a directory: {repo_path}")
        sys.exit(1)

    print("=" * 70)
    print("Code Index Builder")
    print("=" * 70)
    print(f"Repository: {args.repo}")
    print(f"Path: {repo_path}")
    print(f"Database: {args.db}")
    print(f"Include private: {args.include_private}")
    print(f"Replace existing: {args.replace}")
    print()

    # Initialize store
    print("Initializing code index store...")
    store = CodeIndexStore(db_path=args.db)

    # Check if repo already exists
    existing_repos = store.list_repos()
    if args.repo in existing_repos:
        if args.replace:
            print(f"Removing existing index for '{args.repo}'...")
            deleted = store.delete_by_repo(args.repo)
            print(f"  Deleted {deleted} objects")
        else:
            print(f"Warning: Repository '{args.repo}' is already indexed.")
            print("Use --replace to re-index, or use a different repo name.")
            sys.exit(1)

    print()

    # Initialize indexer
    print("Indexing repository...")
    indexer = CodeIndexer(repo_name=args.repo, repo_root=repo_path)

    # Index the repository
    try:
        count = indexer.index_repository(
            include_patterns=args.include,
            exclude_patterns=args.exclude,
            include_private=args.include_private,
        )
        print(f"  Found {count} code objects")
    except Exception as e:
        print(f"Error during indexing: {e}")
        sys.exit(1)

    print()

    # Get statistics from indexer
    stats = indexer.get_stats()
    print("Index Statistics:")
    print(f"  Total objects: {stats['total_objects']}")
    print(f"  Unique names: {stats['unique_names']}")
    print(f"  Qualified names: {stats['qualified_names']}")
    print()
    print("  Objects by type:")
    for obj_type, count in stats['type_counts'].items():
        print(f"    {obj_type}: {count}")

    print()

    # Store in database
    print("Storing index in database...")
    all_objects = indexer.get_all_objects()
    store.add_objects_batch(all_objects)
    print(f"  Stored {len(all_objects)} objects")

    print()

    # Show overall database stats
    db_stats = store.get_stats()
    print("Database Statistics:")
    print(f"  Total objects: {db_stats['total_objects']}")
    print()
    print("  Objects by repository:")
    for repo, count in db_stats['repo_counts'].items():
        print(f"    {repo}: {count}")
    print()
    print("  Objects by type:")
    for obj_type, count in db_stats['type_counts'].items():
        print(f"    {obj_type}: {count}")

    print()
    print("=" * 70)
    print("Indexing complete!")
    print("=" * 70)
    print()
    print("You can now use the code index for fast code lookups:")
    print(f"  - Query by name: store.get_by_name('AutomationCondition')")
    print(f"  - Query by qualified name: store.get_by_qualified_name('dagster.AutomationCondition.eager')")
    print(f"  - Search pattern: store.search_by_name_pattern('Automation%')")


if __name__ == "__main__":
    main()
