"""AST-based code indexer for Python repositories."""

import ast
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict


@dataclass
class CodeObject:
    """Represents an indexed code object (class, function, method)."""

    name: str  # Simple name (e.g., "eager")
    qualified_name: str  # Full dotted name (e.g., "dagster.AutomationCondition.eager")
    type: str  # 'class', 'function', 'method', 'async_function', 'async_method'
    file_path: str  # Absolute path to file
    line_number: int  # Starting line number
    end_line_number: int  # Ending line number
    repo_name: str  # Repository name (e.g., "dagster", "pyiceberg")
    relative_path: str  # Path relative to repo root
    docstring: Optional[str] = None  # First line of docstring
    parent_class: Optional[str] = None  # Parent class for methods
    decorators: List[str] = None  # List of decorator names
    is_private: bool = False  # Starts with underscore

    def __post_init__(self):
        if self.decorators is None:
            self.decorators = []

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class CodeIndexer:
    """Index Python code objects in a repository."""

    def __init__(self, repo_name: str, repo_root: Path):
        """
        Initialize the code indexer.

        Args:
            repo_name: Name of the repository (e.g., "dagster")
            repo_root: Root directory of the repository
        """
        self.repo_name = repo_name
        self.repo_root = Path(repo_root).resolve()
        self.index: Dict[str, List[CodeObject]] = {}  # name -> [CodeObject]
        self.qualified_index: Dict[str, CodeObject] = {}  # qualified_name -> CodeObject

    def index_repository(
        self,
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
        include_private: bool = False,
    ) -> int:
        """
        Index all Python files in the repository.

        Args:
            include_patterns: Glob patterns to include (default: ["**/*.py"])
            exclude_patterns: Glob patterns to exclude (default: tests, __pycache__)
            include_private: Whether to index private objects (starting with _)

        Returns:
            Number of objects indexed
        """
        include_patterns = include_patterns or ["**/*.py"]
        exclude_patterns = exclude_patterns or [
            "**/test_*.py",
            "**/*_test.py",
            "**/tests/**",
            "**/__pycache__/**",
            "**/.*/**",  # Hidden directories
        ]

        # Find all Python files
        python_files = set()
        for pattern in include_patterns:
            python_files.update(self.repo_root.glob(pattern))

        # Exclude files based on exclude patterns
        for pattern in exclude_patterns:
            exclude_files = set(self.repo_root.glob(pattern))
            python_files -= exclude_files

        # Index each file
        total_objects = 0
        for file_path in sorted(python_files):
            try:
                objects = self._index_file(file_path, include_private)
                total_objects += len(objects)
            except Exception as e:
                # Skip files that can't be parsed
                print(f"Warning: Could not index {file_path}: {e}")
                continue

        return total_objects

    def _index_file(self, file_path: Path, include_private: bool) -> List[CodeObject]:
        """
        Index all code objects in a single file.

        Args:
            file_path: Path to Python file
            include_private: Whether to include private objects

        Returns:
            List of indexed objects
        """
        objects = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except Exception:
            return objects

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return objects

        # Get relative path for module name inference
        try:
            relative_path = file_path.relative_to(self.repo_root)
        except ValueError:
            return objects

        # Infer module path from file path
        module_parts = list(relative_path.parts[:-1])  # Exclude filename
        if relative_path.stem != '__init__':
            module_parts.append(relative_path.stem)
        module_prefix = '.'.join(module_parts) if module_parts else ''

        # Walk AST and extract definitions
        for node in ast.walk(tree):
            obj = None

            if isinstance(node, ast.ClassDef):
                obj = self._extract_class(node, file_path, relative_path, module_prefix)
                if obj and (include_private or not obj.is_private):
                    objects.append(obj)

                    # Also index methods of the class
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            method_obj = self._extract_method(
                                item, node, file_path, relative_path, module_prefix
                            )
                            if method_obj and (include_private or not method_obj.is_private):
                                objects.append(method_obj)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only index top-level functions (not methods)
                # Methods are handled within ClassDef
                if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                    obj = self._extract_function(node, file_path, relative_path, module_prefix)
                    if obj and (include_private or not obj.is_private):
                        objects.append(obj)

        # Add objects to indices
        for obj in objects:
            # Add to name index (allows duplicates)
            if obj.name not in self.index:
                self.index[obj.name] = []
            self.index[obj.name].append(obj)

            # Add to qualified name index (unique)
            self.qualified_index[obj.qualified_name] = obj

        return objects

    def _extract_class(
        self,
        node: ast.ClassDef,
        file_path: Path,
        relative_path: Path,
        module_prefix: str,
    ) -> CodeObject:
        """Extract class definition."""
        qualified_name = f"{module_prefix}.{node.name}" if module_prefix else node.name

        return CodeObject(
            name=node.name,
            qualified_name=qualified_name,
            type='class',
            file_path=str(file_path),
            line_number=node.lineno,
            end_line_number=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
            repo_name=self.repo_name,
            relative_path=str(relative_path),
            docstring=self._get_docstring_preview(node),
            decorators=self._get_decorator_names(node),
            is_private=node.name.startswith('_'),
        )

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: Path,
        relative_path: Path,
        module_prefix: str,
    ) -> CodeObject:
        """Extract top-level function definition."""
        qualified_name = f"{module_prefix}.{node.name}" if module_prefix else node.name
        obj_type = 'async_function' if isinstance(node, ast.AsyncFunctionDef) else 'function'

        return CodeObject(
            name=node.name,
            qualified_name=qualified_name,
            type=obj_type,
            file_path=str(file_path),
            line_number=node.lineno,
            end_line_number=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
            repo_name=self.repo_name,
            relative_path=str(relative_path),
            docstring=self._get_docstring_preview(node),
            decorators=self._get_decorator_names(node),
            is_private=node.name.startswith('_'),
        )

    def _extract_method(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        class_node: ast.ClassDef,
        file_path: Path,
        relative_path: Path,
        module_prefix: str,
    ) -> CodeObject:
        """Extract method definition from a class."""
        class_qualified = f"{module_prefix}.{class_node.name}" if module_prefix else class_node.name
        qualified_name = f"{class_qualified}.{node.name}"
        obj_type = 'async_method' if isinstance(node, ast.AsyncFunctionDef) else 'method'

        return CodeObject(
            name=node.name,
            qualified_name=qualified_name,
            type=obj_type,
            file_path=str(file_path),
            line_number=node.lineno,
            end_line_number=node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
            repo_name=self.repo_name,
            relative_path=str(relative_path),
            docstring=self._get_docstring_preview(node),
            parent_class=class_node.name,
            decorators=self._get_decorator_names(node),
            is_private=node.name.startswith('_'),
        )

    def _get_docstring_preview(self, node: ast.AST, max_length: int = 100) -> Optional[str]:
        """Get first line of docstring."""
        docstring = ast.get_docstring(node)
        if docstring:
            first_line = docstring.split('\n')[0].strip()
            if len(first_line) > max_length:
                return first_line[:max_length] + "..."
            return first_line
        return None

    def _get_decorator_names(self, node: ast.AST) -> List[str]:
        """Extract decorator names from a node."""
        decorators = []
        if hasattr(node, 'decorator_list'):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name):
                    decorators.append(dec.id)
                elif isinstance(dec, ast.Attribute):
                    decorators.append(dec.attr)
                elif isinstance(dec, ast.Call):
                    if isinstance(dec.func, ast.Name):
                        decorators.append(dec.func.id)
                    elif isinstance(dec.func, ast.Attribute):
                        decorators.append(dec.func.attr)
        return decorators

    def get_by_name(self, name: str) -> List[CodeObject]:
        """
        Get all objects with the given name.

        Args:
            name: Simple name to search for

        Returns:
            List of matching objects (may have multiple results)
        """
        return self.index.get(name, [])

    def get_by_qualified_name(self, qualified_name: str) -> Optional[CodeObject]:
        """
        Get object by fully qualified name.

        Args:
            qualified_name: Full dotted name (e.g., "dagster.AutomationCondition.eager")

        Returns:
            CodeObject or None
        """
        return self.qualified_index.get(qualified_name)

    def search_prefix(self, prefix: str, limit: int = 50) -> List[CodeObject]:
        """
        Search for objects whose name starts with prefix.

        Args:
            prefix: Name prefix to search
            limit: Maximum number of results

        Returns:
            List of matching objects
        """
        results = []
        for name, objects in self.index.items():
            if name.startswith(prefix):
                results.extend(objects)
                if len(results) >= limit:
                    break
        return results[:limit]

    def get_all_objects(self) -> List[CodeObject]:
        """Get all indexed objects."""
        all_objects = []
        for objects in self.index.values():
            all_objects.extend(objects)
        return all_objects

    def get_stats(self) -> dict:
        """Get indexing statistics."""
        all_objects = self.get_all_objects()

        type_counts = {}
        for obj in all_objects:
            type_counts[obj.type] = type_counts.get(obj.type, 0) + 1

        return {
            'repo_name': self.repo_name,
            'total_objects': len(all_objects),
            'unique_names': len(self.index),
            'qualified_names': len(self.qualified_index),
            'type_counts': type_counts,
        }
