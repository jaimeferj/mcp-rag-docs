"""Storage and retrieval for code index using SQLite."""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict
from contextlib import contextmanager

from utils.code_indexer import CodeObject


class CodeIndexStore:
    """SQLite-based storage for code index."""

    def __init__(self, db_path: str = "./code_index.db"):
        """
        Initialize the code index store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS code_objects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    qualified_name TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_number INTEGER NOT NULL,
                    end_line_number INTEGER NOT NULL,
                    repo_name TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    docstring TEXT,
                    parent_class TEXT,
                    decorators TEXT,
                    is_private INTEGER NOT NULL
                )
            """)

            # Create indices for fast lookup
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_name ON code_objects(name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_qualified_name ON code_objects(qualified_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_repo_name ON code_objects(repo_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_type ON code_objects(type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_parent_class ON code_objects(parent_class)"
            )

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def add_object(self, obj: CodeObject):
        """
        Add a code object to the store.

        Args:
            obj: CodeObject to store
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO code_objects
                (name, qualified_name, type, file_path, line_number, end_line_number,
                 repo_name, relative_path, docstring, parent_class, decorators, is_private)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    obj.name,
                    obj.qualified_name,
                    obj.type,
                    obj.file_path,
                    obj.line_number,
                    obj.end_line_number,
                    obj.repo_name,
                    obj.relative_path,
                    obj.docstring,
                    obj.parent_class,
                    json.dumps(obj.decorators),
                    1 if obj.is_private else 0,
                ),
            )
            conn.commit()

    def add_objects_batch(self, objects: List[CodeObject]):
        """
        Add multiple code objects in batch.

        Args:
            objects: List of CodeObjects to store
        """
        with self._get_connection() as conn:
            data = [
                (
                    obj.name,
                    obj.qualified_name,
                    obj.type,
                    obj.file_path,
                    obj.line_number,
                    obj.end_line_number,
                    obj.repo_name,
                    obj.relative_path,
                    obj.docstring,
                    obj.parent_class,
                    json.dumps(obj.decorators),
                    1 if obj.is_private else 0,
                )
                for obj in objects
            ]

            conn.executemany(
                """
                INSERT OR REPLACE INTO code_objects
                (name, qualified_name, type, file_path, line_number, end_line_number,
                 repo_name, relative_path, docstring, parent_class, decorators, is_private)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data,
            )
            conn.commit()

    def get_by_name(self, name: str, repo_name: Optional[str] = None) -> List[CodeObject]:
        """
        Get all objects with the given name.

        Args:
            name: Simple name to search for
            repo_name: Optional repository filter

        Returns:
            List of matching CodeObjects
        """
        with self._get_connection() as conn:
            if repo_name:
                cursor = conn.execute(
                    "SELECT * FROM code_objects WHERE name = ? AND repo_name = ?",
                    (name, repo_name),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM code_objects WHERE name = ?", (name,)
                )

            return [self._row_to_object(row) for row in cursor.fetchall()]

    def get_by_qualified_name(self, qualified_name: str) -> Optional[CodeObject]:
        """
        Get object by fully qualified name.

        Args:
            qualified_name: Full dotted name

        Returns:
            CodeObject or None
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM code_objects WHERE qualified_name = ?",
                (qualified_name,),
            )
            row = cursor.fetchone()
            return self._row_to_object(row) if row else None

    def search_by_name_pattern(
        self, pattern: str, repo_name: Optional[str] = None, limit: int = 50
    ) -> List[CodeObject]:
        """
        Search for objects whose name matches pattern.

        Args:
            pattern: SQL LIKE pattern (use % as wildcard)
            repo_name: Optional repository filter
            limit: Maximum number of results

        Returns:
            List of matching CodeObjects
        """
        with self._get_connection() as conn:
            if repo_name:
                cursor = conn.execute(
                    "SELECT * FROM code_objects WHERE name LIKE ? AND repo_name = ? LIMIT ?",
                    (pattern, repo_name, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM code_objects WHERE name LIKE ? LIMIT ?",
                    (pattern, limit),
                )

            return [self._row_to_object(row) for row in cursor.fetchall()]

    def search_by_qualified_name_pattern(
        self, pattern: str, repo_name: Optional[str] = None, limit: int = 50
    ) -> List[CodeObject]:
        """
        Search for objects whose qualified name matches pattern.

        Args:
            pattern: SQL LIKE pattern (use % as wildcard)
            repo_name: Optional repository filter
            limit: Maximum number of results

        Returns:
            List of matching CodeObjects
        """
        with self._get_connection() as conn:
            if repo_name:
                cursor = conn.execute(
                    "SELECT * FROM code_objects WHERE qualified_name LIKE ? AND repo_name = ? LIMIT ?",
                    (pattern, repo_name, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM code_objects WHERE qualified_name LIKE ? LIMIT ?",
                    (pattern, limit),
                )

            return [self._row_to_object(row) for row in cursor.fetchall()]

    def get_by_type(
        self, obj_type: str, repo_name: Optional[str] = None, limit: int = 100
    ) -> List[CodeObject]:
        """
        Get objects by type.

        Args:
            obj_type: Type of object ('class', 'function', 'method', etc.)
            repo_name: Optional repository filter
            limit: Maximum number of results

        Returns:
            List of matching CodeObjects
        """
        with self._get_connection() as conn:
            if repo_name:
                cursor = conn.execute(
                    "SELECT * FROM code_objects WHERE type = ? AND repo_name = ? LIMIT ?",
                    (obj_type, repo_name, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM code_objects WHERE type = ? LIMIT ?",
                    (obj_type, limit),
                )

            return [self._row_to_object(row) for row in cursor.fetchall()]

    def get_class_methods(self, class_name: str, repo_name: Optional[str] = None) -> List[CodeObject]:
        """
        Get all methods of a class.

        Args:
            class_name: Name of the parent class
            repo_name: Optional repository filter

        Returns:
            List of method CodeObjects
        """
        with self._get_connection() as conn:
            if repo_name:
                cursor = conn.execute(
                    "SELECT * FROM code_objects WHERE parent_class = ? AND repo_name = ?",
                    (class_name, repo_name),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM code_objects WHERE parent_class = ?",
                    (class_name,),
                )

            return [self._row_to_object(row) for row in cursor.fetchall()]

    def get_by_repo(self, repo_name: str) -> List[CodeObject]:
        """
        Get all objects from a repository.

        Args:
            repo_name: Repository name

        Returns:
            List of CodeObjects
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM code_objects WHERE repo_name = ?", (repo_name,)
            )
            return [self._row_to_object(row) for row in cursor.fetchall()]

    def delete_by_repo(self, repo_name: str) -> int:
        """
        Delete all objects from a repository.

        Args:
            repo_name: Repository name

        Returns:
            Number of objects deleted
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM code_objects WHERE repo_name = ?", (repo_name,)
            )
            conn.commit()
            return cursor.rowcount

    def clear(self):
        """Clear all objects from the store."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM code_objects")
            conn.commit()

    def get_stats(self) -> Dict:
        """
        Get statistics about the code index.

        Returns:
            Dictionary with statistics
        """
        with self._get_connection() as conn:
            # Total objects
            cursor = conn.execute("SELECT COUNT(*) FROM code_objects")
            total = cursor.fetchone()[0]

            # Objects by type
            cursor = conn.execute(
                "SELECT type, COUNT(*) as count FROM code_objects GROUP BY type"
            )
            type_counts = {row['type']: row['count'] for row in cursor.fetchall()}

            # Objects by repo
            cursor = conn.execute(
                "SELECT repo_name, COUNT(*) as count FROM code_objects GROUP BY repo_name"
            )
            repo_counts = {row['repo_name']: row['count'] for row in cursor.fetchall()}

            return {
                'total_objects': total,
                'type_counts': type_counts,
                'repo_counts': repo_counts,
            }

    def list_repos(self) -> List[str]:
        """
        Get list of all indexed repositories.

        Returns:
            List of repository names
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT DISTINCT repo_name FROM code_objects")
            return [row['repo_name'] for row in cursor.fetchall()]

    def _row_to_object(self, row: sqlite3.Row) -> CodeObject:
        """Convert database row to CodeObject."""
        return CodeObject(
            name=row['name'],
            qualified_name=row['qualified_name'],
            type=row['type'],
            file_path=row['file_path'],
            line_number=row['line_number'],
            end_line_number=row['end_line_number'],
            repo_name=row['repo_name'],
            relative_path=row['relative_path'],
            docstring=row['docstring'],
            parent_class=row['parent_class'],
            decorators=json.loads(row['decorators']),
            is_private=bool(row['is_private']),
        )
