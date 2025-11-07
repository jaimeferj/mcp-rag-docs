"""
Rate limit tracking store using SQLite for persistence.

This module provides a thread-safe SQLite-backed store for tracking API calls
and their token usage over time, enabling accurate rate limit enforcement.
"""

import sqlite3
import time
import threading
from typing import List, Tuple
from pathlib import Path


class RateLimitStore:
    """
    Thread-safe SQLite store for tracking API call history and token usage.

    Maintains a rolling window of API calls with timestamps and token counts
    to enable accurate rate limit checking across application restarts.
    """

    def __init__(self, db_path: str):
        """
        Initialize the rate limit store.

        Args:
            db_path: Path to SQLite database file (will be created if not exists)
        """
        self.db_path = Path(db_path)
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Create database schema if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    tokens_used INTEGER NOT NULL,
                    call_type TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON api_calls(timestamp)
            """)
            conn.commit()

    def record_call(self, tokens_used: int, call_type: str):
        """
        Record an API call with timestamp and token usage.

        Args:
            tokens_used: Number of tokens consumed by this call
            call_type: Type of API call (e.g., 'embed', 'generate')
        """
        with self.lock:
            timestamp = time.time()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO api_calls (timestamp, tokens_used, call_type) VALUES (?, ?, ?)",
                    (timestamp, tokens_used, call_type)
                )
                conn.commit()

    def get_calls_in_window(self, window_seconds: int = 60) -> List[Tuple[float, int, str]]:
        """
        Get all API calls within the specified time window.

        Args:
            window_seconds: Size of time window in seconds (default: 60)

        Returns:
            List of tuples: (timestamp, tokens_used, call_type)
        """
        with self.lock:
            cutoff_time = time.time() - window_seconds
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT timestamp, tokens_used, call_type FROM api_calls WHERE timestamp > ?",
                    (cutoff_time,)
                )
                return cursor.fetchall()

    def get_request_count_in_window(self, window_seconds: int = 60) -> int:
        """
        Count API requests in the last window_seconds.

        Args:
            window_seconds: Size of time window in seconds (default: 60)

        Returns:
            Number of requests in the window
        """
        calls = self.get_calls_in_window(window_seconds)
        return len(calls)

    def get_token_count_in_window(self, window_seconds: int = 60) -> int:
        """
        Sum token usage in the last window_seconds.

        Args:
            window_seconds: Size of time window in seconds (default: 60)

        Returns:
            Total tokens used in the window
        """
        calls = self.get_calls_in_window(window_seconds)
        return sum(tokens for _, tokens, _ in calls)

    def cleanup_old_records(self, keep_seconds: int = 86400):
        """
        Remove old records to prevent database bloat.

        Args:
            keep_seconds: Keep records newer than this (default: 86400 = 24 hours)
        """
        with self.lock:
            cutoff_time = time.time() - keep_seconds
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM api_calls WHERE timestamp < ?", (cutoff_time,))
                conn.commit()

    def get_oldest_call_timestamp(self, window_seconds: int = 60) -> float | None:
        """
        Get timestamp of oldest call in the window.

        Args:
            window_seconds: Size of time window in seconds (default: 60)

        Returns:
            Timestamp of oldest call, or None if no calls in window
        """
        calls = self.get_calls_in_window(window_seconds)
        if not calls:
            return None
        return min(timestamp for timestamp, _, _ in calls)

    def get_daily_request_count(self) -> int:
        """
        Get the number of requests in the last 24 hours.

        Returns:
            Number of requests in the last 24 hours
        """
        return self.get_request_count_in_window(86400)
