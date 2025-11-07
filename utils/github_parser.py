"""Parse GitHub URLs from Dagster documentation and map to local files."""

import re
from pathlib import Path
from typing import Optional


class GitHubURLParser:
    """Parser for Dagster documentation GitHub URLs."""

    # GitHub URL pattern for Dagster repository
    # Line number is optional - captures with or without #L123
    GITHUB_URL_PATTERN = re.compile(
        r'https://github\.com/dagster-io/dagster/blob/master/python_modules/(.+?)(?:#L(\d+))?$'
    )

    def __init__(self, repo_root: str = "/home/ubuntu/dagster"):
        """
        Initialize the GitHub URL parser.

        Args:
            repo_root: Root directory of the local Dagster repository
        """
        self.repo_root = Path(repo_root)

    def parse_url(self, github_url: str) -> Optional[dict]:
        """
        Parse a GitHub URL and extract components.

        Args:
            github_url: Full GitHub URL with line number

        Returns:
            Dictionary with parsed components or None if invalid:
            {
                'repo_base': 'https://github.com/dagster-io/dagster',
                'branch': 'master',
                'relative_path': 'python_modules/dagster/dagster/_core/...',
                'line_number': 130,
                'local_path': Path('/home/ubuntu/dagster/python_modules/...')
            }
        """
        match = self.GITHUB_URL_PATTERN.match(github_url)
        if not match:
            return None

        relative_path_after_python_modules = match.group(1)
        line_number_str = match.group(2)

        # Default to line 1 if no line number specified
        line_number = int(line_number_str) if line_number_str else 1

        relative_path = f"python_modules/{relative_path_after_python_modules}"
        local_path = self.repo_root / relative_path

        return {
            'repo_base': 'https://github.com/dagster-io/dagster',
            'branch': 'master',
            'relative_path': relative_path,
            'line_number': line_number,
            'local_path': local_path,
        }

    def github_url_to_local_path(self, github_url: str) -> Optional[tuple[Path, int]]:
        """
        Convert GitHub URL to local file path and line number.

        Args:
            github_url: Full GitHub URL with line number

        Returns:
            Tuple of (local_file_path, line_number) or (None, None) if invalid
        """
        parsed = self.parse_url(github_url)
        if parsed:
            return (parsed['local_path'], parsed['line_number'])
        return (None, None)

    def local_path_to_github_url(self, local_path: Path, line_number: int) -> Optional[str]:
        """
        Convert local file path to GitHub URL.

        Args:
            local_path: Absolute path to local file
            line_number: Line number in file

        Returns:
            GitHub URL with line reference or None if path is not in repository
        """
        try:
            relative_path = local_path.relative_to(self.repo_root)
            base_url = 'https://github.com/dagster-io/dagster/blob/master'
            return f'{base_url}/{relative_path}#L{line_number}'
        except ValueError:
            # Path is not relative to repo root
            return None

    def validate_local_path(self, local_path: Path) -> bool:
        """
        Check if the local file path exists.

        Args:
            local_path: Path to check

        Returns:
            True if file exists, False otherwise
        """
        return local_path.exists() and local_path.is_file()

    def extract_github_urls(self, text: str) -> list[str]:
        """
        Extract all Dagster GitHub URLs from text.

        Args:
            text: Text to search for URLs

        Returns:
            List of GitHub URLs found in text
        """
        return self.GITHUB_URL_PATTERN.findall(text)
