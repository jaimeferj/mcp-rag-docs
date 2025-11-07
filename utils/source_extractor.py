"""Extract Python source code definitions from files."""

import ast
from pathlib import Path
from typing import Optional, List


class SourceCodeExtractor:
    """Extract function and class definitions from Python source files."""

    def __init__(self):
        """Initialize the source code extractor."""
        pass

    def extract_at_line(
        self,
        file_path: Path,
        line_number: int,
        context_lines: int = 20,
    ) -> Optional[dict]:
        """
        Extract source code at a specific line number.

        This method attempts to find and extract the complete definition
        (function or class) that starts at or near the specified line.

        Args:
            file_path: Path to the Python source file
            line_number: Target line number (1-indexed)
            context_lines: Number of context lines to include if AST fails

        Returns:
            Dictionary with extracted code and metadata:
            {
                'code': 'def function_name(...):\\n    ...',
                'name': 'function_name',
                'type': 'function' | 'class' | 'context',
                'start_line': 130,
                'end_line': 150,
                'file_path': '/path/to/file.py',
                'docstring': 'Function docstring...',
            }
        """
        if not file_path.exists():
            return None

        try:
            # Read the entire file
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
                lines = source_code.splitlines()

            # Try to parse with AST
            try:
                tree = ast.parse(source_code)
                result = self._extract_with_ast(tree, lines, line_number)
                if result:
                    result['file_path'] = str(file_path)
                    return result
            except SyntaxError:
                # If AST parsing fails, fall back to context extraction
                pass

            # Fallback: Extract context lines around the target
            return self._extract_context(lines, line_number, context_lines, file_path)

        except Exception as e:
            return {
                'error': f'Failed to extract source code: {str(e)}',
                'file_path': str(file_path),
                'line_number': line_number,
            }

    def _extract_with_ast(
        self,
        tree: ast.AST,
        lines: list[str],
        target_line: int,
    ) -> Optional[dict]:
        """
        Extract definition using AST parsing.

        Args:
            tree: Parsed AST tree
            lines: Source code lines
            target_line: Target line number (1-indexed)

        Returns:
            Dictionary with extracted code or None
        """
        # Find the node that contains or starts at the target line
        target_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if hasattr(node, 'lineno') and node.lineno == target_line:
                    target_node = node
                    break
                # Also check if target line is within the node
                elif (hasattr(node, 'lineno') and hasattr(node, 'end_lineno') and
                      node.lineno <= target_line <= node.end_lineno):
                    target_node = node

        if target_node:
            return self._extract_node(target_node, lines)

        return None

    def _extract_node(self, node: ast.AST, lines: list[str]) -> dict:
        """
        Extract code from an AST node.

        Args:
            node: AST node (FunctionDef, ClassDef, etc.)
            lines: Source code lines

        Returns:
            Dictionary with extracted information
        """
        start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1

        # Extract the code
        code_lines = lines[start_line - 1:end_line]
        code = '\n'.join(code_lines)

        # Determine node type and name
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node_type = 'function'
            name = node.name
        elif isinstance(node, ast.ClassDef):
            node_type = 'class'
            name = node.name
        else:
            node_type = 'other'
            name = None

        # Extract docstring
        docstring = ast.get_docstring(node)

        return {
            'code': code,
            'name': name,
            'type': node_type,
            'start_line': start_line,
            'end_line': end_line,
            'docstring': docstring,
        }

    def _extract_context(
        self,
        lines: list[str],
        target_line: int,
        context_lines: int,
        file_path: Path,
    ) -> dict:
        """
        Extract context lines around target line.

        Args:
            lines: Source code lines
            target_line: Target line number (1-indexed)
            context_lines: Number of lines before and after
            file_path: Path to the file

        Returns:
            Dictionary with context code
        """
        start_line = max(1, target_line - context_lines)
        end_line = min(len(lines), target_line + context_lines)

        code_lines = lines[start_line - 1:end_line]
        code = '\n'.join(code_lines)

        return {
            'code': code,
            'name': None,
            'type': 'context',
            'start_line': start_line,
            'end_line': end_line,
            'file_path': str(file_path),
            'docstring': None,
            'note': f'Context extraction: lines {start_line}-{end_line} (AST parsing failed)',
        }

    def extract_definition_at_line(
        self,
        file_path: Path,
        line_number: int,
    ) -> Optional[dict]:
        """
        Extract just the function/class definition starting at line number.

        This is more aggressive and tries to find the definition even if
        the line number is not exact.

        Args:
            file_path: Path to the Python source file
            line_number: Target line number (1-indexed)

        Returns:
            Dictionary with extracted code and metadata
        """
        return self.extract_at_line(file_path, line_number, context_lines=50)

    def extract_signature(
        self,
        file_path: Path,
        line_number: int,
    ) -> Optional[dict]:
        """
        Extract only the signature (def/class line) without implementation.

        Args:
            file_path: Path to the Python source file
            line_number: Target line number (1-indexed)

        Returns:
            Dictionary with signature and metadata
        """
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
                lines = source_code.splitlines()

            # Try AST parsing
            try:
                tree = ast.parse(source_code)
                node = self._find_node_at_line(tree, line_number)
                if node:
                    signature = self._extract_signature_from_node(node, lines)
                    return {
                        'code': signature,
                        'name': node.name if hasattr(node, 'name') else None,
                        'type': 'function' if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else 'class',
                        'start_line': node.lineno,
                        'end_line': node.lineno,
                        'file_path': str(file_path),
                        'mode': 'signature',
                    }
            except SyntaxError:
                pass

            # Fallback: just return the line
            if 0 < line_number <= len(lines):
                return {
                    'code': lines[line_number - 1],
                    'name': None,
                    'type': 'signature',
                    'start_line': line_number,
                    'end_line': line_number,
                    'file_path': str(file_path),
                    'mode': 'signature',
                }

        except Exception as e:
            return {'error': f'Failed to extract signature: {str(e)}'}

        return None

    def extract_class_outline(
        self,
        file_path: Path,
        line_number: int,
    ) -> Optional[dict]:
        """
        Extract class with method signatures only (no implementation).

        Args:
            file_path: Path to the Python source file
            line_number: Target line number (1-indexed)

        Returns:
            Dictionary with class outline and metadata
        """
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
                lines = source_code.splitlines()

            tree = ast.parse(source_code)
            node = self._find_node_at_line(tree, line_number)

            if node and isinstance(node, ast.ClassDef):
                outline = self._create_class_outline(node, lines)
                return {
                    'code': outline,
                    'name': node.name,
                    'type': 'class',
                    'start_line': node.lineno,
                    'end_line': node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                    'file_path': str(file_path),
                    'mode': 'outline',
                    'method_count': len([m for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]),
                }
            else:
                # If not a class, return signature
                return self.extract_signature(file_path, line_number)

        except Exception as e:
            return {'error': f'Failed to extract class outline: {str(e)}'}

        return None

    def extract_class_methods_list(
        self,
        file_path: Path,
        line_number: int,
    ) -> Optional[dict]:
        """
        Extract class with just method names listed (minimal).

        Args:
            file_path: Path to the Python source file
            line_number: Target line number (1-indexed)

        Returns:
            Dictionary with class methods list and metadata
        """
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
                lines = source_code.splitlines()

            tree = ast.parse(source_code)
            node = self._find_node_at_line(tree, line_number)

            if node and isinstance(node, ast.ClassDef):
                methods = self._get_class_methods(node)
                class_def = lines[node.lineno - 1]

                # Build methods list
                methods_text = '\n'.join([f'    - {name}' for name in methods])
                code = f"{class_def}\n{methods_text}"

                return {
                    'code': code,
                    'name': node.name,
                    'type': 'class',
                    'start_line': node.lineno,
                    'end_line': node.lineno,
                    'file_path': str(file_path),
                    'mode': 'methods_list',
                    'methods': methods,
                    'method_count': len(methods),
                }
            else:
                return self.extract_signature(file_path, line_number)

        except Exception as e:
            return {'error': f'Failed to extract methods list: {str(e)}'}

        return None

    def extract_class_method(
        self,
        file_path: Path,
        class_line: int,
        method_name: str,
    ) -> Optional[dict]:
        """
        Extract a specific method from a class.

        Args:
            file_path: Path to the Python source file
            class_line: Line number where the class is defined
            method_name: Name of the method to extract

        Returns:
            Dictionary with method code and metadata
        """
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
                lines = source_code.splitlines()

            tree = ast.parse(source_code)
            class_node = self._find_node_at_line(tree, class_line)

            if class_node and isinstance(class_node, ast.ClassDef):
                method_node = self._find_method_in_class(class_node, method_name)
                if method_node:
                    result = self._extract_node(method_node, lines)
                    result['file_path'] = str(file_path)
                    result['mode'] = 'method'
                    result['method_name'] = method_name
                    result['class_name'] = class_node.name
                    return result

            return {'error': f"Method '{method_name}' not found in class"}

        except Exception as e:
            return {'error': f'Failed to extract method: {str(e)}'}

        return None

    def _find_node_at_line(self, tree: ast.AST, target_line: int) -> Optional[ast.AST]:
        """Find the AST node at the specified line."""
        target_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if hasattr(node, 'lineno') and node.lineno == target_line:
                    return node
                # Also check if target line is within the node
                elif (hasattr(node, 'lineno') and hasattr(node, 'end_lineno') and
                      node.lineno <= target_line <= node.end_lineno):
                    target_node = node
        return target_node

    def _extract_signature_from_node(self, node: ast.AST, lines: List[str]) -> str:
        """Extract just the signature line(s) from a node."""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # For functions, we need the def line and any decorators
            start = node.lineno
            # Find where the actual parameters end (might span multiple lines)
            # We'll look for the colon that ends the signature
            for i in range(node.lineno - 1, min(len(lines), node.lineno + 10)):
                if ':' in lines[i]:
                    return '\n'.join(lines[node.lineno - 1:i + 1])
            return lines[node.lineno - 1]
        elif isinstance(node, ast.ClassDef):
            # For classes, return the class definition line
            return lines[node.lineno - 1]
        return ''

    def _create_class_outline(self, class_node: ast.ClassDef, lines: List[str]) -> str:
        """Create a class outline with method signatures."""
        outline_lines = []

        # Class definition
        class_def = lines[class_node.lineno - 1]
        outline_lines.append(class_def)

        # Get docstring if exists
        docstring = ast.get_docstring(class_node)
        if docstring:
            outline_lines.append(f'    """{docstring[:100]}{"..." if len(docstring) > 100 else ""}"""')

        # Extract method signatures
        for item in class_node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Get method signature
                method_sig = self._extract_signature_from_node(item, lines)
                # Ensure proper indentation
                if not method_sig.startswith('    '):
                    method_sig = '    ' + method_sig
                outline_lines.append(method_sig + ' ...')

        return '\n'.join(outline_lines)

    def _get_class_methods(self, class_node: ast.ClassDef) -> List[str]:
        """Get list of method names in a class."""
        methods = []
        for item in class_node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)
        return methods

    def _find_method_in_class(self, class_node: ast.ClassDef, method_name: str) -> Optional[ast.AST]:
        """Find a specific method in a class node."""
        for item in class_node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name == method_name:
                    return item
        return None
