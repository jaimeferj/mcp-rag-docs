"""Extract Python object references from documentation text."""

import re
from typing import List, Set, Dict


class PythonReferenceExtractor:
    """Extract Python class, function, and module references from text."""

    # Patterns for Python references
    PATTERNS = {
        # Class.method() or Class.attribute
        'class_method': re.compile(r'\b([A-Z][a-zA-Z0-9_]*\.[a-z_][a-zA-Z0-9_]*)\(\)?'),
        # module.Class or module.function
        'module_object': re.compile(r'\b([a-z_][a-z0-9_]*\.[A-Z][a-zA-Z0-9_]*(?:\.[a-z_][a-zA-Z0-9_]*)?)\b'),
        # @decorator
        'decorator': re.compile(r'@([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*)'),
        # function_name() with backticks
        'function': re.compile(r'`([a-z_][a-z0-9_]*)\(\)`'),
        # Class name with backticks
        'class': re.compile(r'`([A-Z][a-zA-Z0-9_]*)`'),
        # Full qualified names like dagster.AutomationCondition
        'qualified_name': re.compile(r'\b(dagster(?:\.[a-z_][a-z0-9_]*)*\.[A-Z][a-zA-Z0-9_]*(?:\.[a-z_][a-zA-Z0-9_]*)?)\b'),
    }

    # GitHub URL pattern
    GITHUB_URL_PATTERN = re.compile(
        r'https://github\.com/dagster-io/dagster/blob/master/python_modules/[^\s\)\]]+(?:#L\d+)?'
    )

    def extract_references(self, text: str) -> Dict[str, Set[str]]:
        """
        Extract Python object references from text.

        Args:
            text: Text to extract references from

        Returns:
            Dictionary with categorized references:
            {
                'class_method': {'AutomationCondition.eager', ...},
                'module_object': {...},
                'decorator': {'asset', 'op', ...},
                'function': {...},
                'class': {'AutomationCondition', ...},
                'qualified_name': {'dagster.AutomationCondition.eager', ...},
                'all': set of all unique references
            }
        """
        references = {
            'class_method': set(),
            'module_object': set(),
            'decorator': set(),
            'function': set(),
            'class': set(),
            'qualified_name': set(),
        }

        # Extract each pattern type
        for pattern_name, pattern in self.PATTERNS.items():
            matches = pattern.findall(text)
            references[pattern_name].update(matches)

        # Create combined set of all references
        all_refs = set()
        for refs in references.values():
            all_refs.update(refs)

        references['all'] = all_refs

        return references

    def extract_github_urls(self, text: str) -> List[str]:
        """
        Extract GitHub URLs from text.

        Args:
            text: Text to extract URLs from

        Returns:
            List of GitHub URLs
        """
        return self.GITHUB_URL_PATTERN.findall(text)

    def prioritize_references(self, references: Dict[str, Set[str]], max_refs: int = 3) -> List[str]:
        """
        Prioritize which references to follow up on.

        Args:
            references: Dictionary of categorized references
            max_refs: Maximum number of references to return

        Returns:
            List of prioritized reference strings to query
        """
        prioritized = []

        # Priority order: qualified_name > class_method > class > module_object
        # These are most likely to have detailed documentation

        # 1. Qualified names (most specific)
        for ref in references['qualified_name']:
            if len(prioritized) >= max_refs:
                break
            prioritized.append(ref)

        # 2. Class methods (e.g., AutomationCondition.eager)
        if len(prioritized) < max_refs:
            for ref in references['class_method']:
                if len(prioritized) >= max_refs:
                    break
                # Skip if we already have the qualified version
                if not any(ref in p for p in prioritized):
                    prioritized.append(ref)

        # 3. Classes (e.g., AutomationCondition)
        if len(prioritized) < max_refs:
            for ref in references['class']:
                if len(prioritized) >= max_refs:
                    break
                # Skip if we already have this as part of a method/qualified name
                if not any(ref in p for p in prioritized):
                    prioritized.append(ref)

        # 4. Module objects
        if len(prioritized) < max_refs:
            for ref in references['module_object']:
                if len(prioritized) >= max_refs:
                    break
                if not any(ref in p for p in prioritized):
                    prioritized.append(ref)

        # 5. Decorators (common ones like @asset, @op)
        if len(prioritized) < max_refs:
            for ref in references['decorator']:
                if len(prioritized) >= max_refs:
                    break
                if not any(ref in p for p in prioritized):
                    prioritized.append(f"@{ref}")

        return prioritized

    def format_reference_for_query(self, reference: str) -> str:
        """
        Format a reference into a query string.

        Args:
            reference: Python reference (e.g., 'AutomationCondition.eager')

        Returns:
            Query string for RAG system
        """
        # Remove common prefixes if present
        ref = reference.replace('dagster.', '')

        # Format as a question
        if '.' in ref:
            parts = ref.split('.')
            if ref.startswith('@'):
                return f"what is the {ref} decorator"
            else:
                return f"what is {parts[0]} {parts[1]}"
        else:
            if ref.startswith('@'):
                return f"what is the {ref} decorator"
            else:
                return f"what is {ref}"
