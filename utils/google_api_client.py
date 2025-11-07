"""
Rate-limited Google AI API client.

This module provides a wrapper around the Google Generative AI SDK that enforces
rate limits (RPM and TPM) and tracks usage across application restarts.
"""

import time
from typing import Any, Dict, List

import google.generativeai as genai

from utils.rate_limit_store import RateLimitStore


class RateLimitExceededError(Exception):
    """
    Exception raised when API rate limits are exceeded.

    Attributes:
        message: Error message describing which limit was exceeded
        reset_time: Unix timestamp when the rate limit will reset
    """

    def __init__(self, message: str, reset_time: float):
        """
        Initialize the exception.

        Args:
            message: Error message
            reset_time: Unix timestamp when rate limit resets
        """
        super().__init__(message)
        self.reset_time = reset_time


class GoogleAPIClient:
    """
    Thread-safe Google AI client with RPM and TPM rate limiting.

    This client wraps the Google Generative AI SDK and enforces rate limits
    by tracking API calls and token usage in a persistent SQLite database.

    Rate limits are checked before each API call. If a limit would be exceeded,
    a RateLimitExceededError is raised immediately.
    """

    def __init__(
        self,
        api_key: str,
        rpm_limit: int = 15,
        tpm_limit: int = 250000,
        rpd_limit: int = 1000,
        rate_limit_db_path: str = "./rate_limits.db",
    ):
        """
        Initialize the rate-limited Google AI client.

        Args:
            api_key: Google AI Studio API key
            rpm_limit: Requests per minute limit (default: 15)
            tpm_limit: Tokens per minute limit (default: 250000)
            rpd_limit: Requests per day limit (default: 1000)
            rate_limit_db_path: Path to SQLite database for tracking
        """
        genai.configure(api_key=api_key)
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.rpd_limit = rpd_limit
        self.store = RateLimitStore(rate_limit_db_path)

    def _check_rate_limits(self, estimated_tokens: int):
        """
        Check if making an API call would exceed rate limits.

        Args:
            estimated_tokens: Number of tokens this call will consume

        Raises:
            RateLimitExceededError: If RPM, TPM, or RPD limits would be exceeded
        """
        current_requests = self.store.get_request_count_in_window(60)
        current_tokens = self.store.get_token_count_in_window(60)
        daily_requests = self.store.get_daily_request_count()

        # Check RPD (Requests Per Day) first
        if daily_requests >= self.rpd_limit:
            oldest_timestamp = self.store.get_oldest_call_timestamp(86400)
            reset_time = oldest_timestamp + 86400 if oldest_timestamp else time.time() + 86400
            wait_seconds = max(0, reset_time - time.time())
            wait_hours = wait_seconds / 3600
            raise RateLimitExceededError(
                f"RPD limit exceeded: {daily_requests}/{self.rpd_limit} requests in last 24h. "
                f"Rate limit will reset in {wait_hours:.1f} hours.",
                reset_time,
            )

        # Check RPM (Requests Per Minute)
        if current_requests >= self.rpm_limit:
            oldest_timestamp = self.store.get_oldest_call_timestamp(60)
            reset_time = oldest_timestamp + 60 if oldest_timestamp else time.time() + 60
            wait_seconds = max(0, reset_time - time.time())
            raise RateLimitExceededError(
                f"RPM limit exceeded: {current_requests}/{self.rpm_limit} requests in last 60s. "
                f"Rate limit will reset in {wait_seconds:.1f} seconds.",
                reset_time,
            )

        # Check TPM (Tokens Per Minute)
        if current_tokens + estimated_tokens > self.tpm_limit:
            oldest_timestamp = self.store.get_oldest_call_timestamp(60)
            reset_time = oldest_timestamp + 60 if oldest_timestamp else time.time() + 60
            wait_seconds = max(0, reset_time - time.time())
            raise RateLimitExceededError(
                f"TPM limit exceeded: {current_tokens + estimated_tokens}/{self.tpm_limit} tokens. "
                f"Current usage: {current_tokens} tokens, Requested: {estimated_tokens} tokens. "
                f"Rate limit will reset in {wait_seconds:.1f} seconds.",
                reset_time,
            )

    def count_tokens(self, model_name: str, content: str | List[str]) -> int:
        """
        Count tokens for content using Google's token counting API.

        Args:
            model_name: Name of the model (e.g., "gemini-1.5-flash")
            content: Text content or list of texts to count tokens for

        Returns:
            Total number of tokens
        """
        model = genai.GenerativeModel(model_name)

        if isinstance(content, str):
            result = model.count_tokens(content)
            return result.total_tokens
        else:
            # For lists, count each item and sum
            total = 0
            for item in content:
                result = model.count_tokens(item)
                total += result.total_tokens
            return total

    def embed_content(
        self,
        model: str,
        content: str,
        task_type: str = "retrieval_document",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate embeddings with rate limiting.

        Args:
            model: Model name (e.g., "models/text-embedding-004")
            content: Text to embed
            task_type: Task type for embedding (e.g., "retrieval_document", "retrieval_query")
            **kwargs: Additional arguments passed to genai.embed_content

        Returns:
            Embedding result dictionary from Google AI API

        Raises:
            RateLimitExceededError: If rate limits would be exceeded
        """
        # Estimate tokens for embeddings (rough approximation: 1 token ≈ 4 characters)
        # Google's embedding API doesn't return token counts, so we estimate
        estimated_tokens = max(1, len(content) // 4)

        # Check rate limits before making the call
        self._check_rate_limits(estimated_tokens)

        # Make the API call
        result = genai.embed_content(
            model=model,
            content=content,
            task_type=task_type,
            **kwargs,
        )

        # Record the call with estimated tokens
        self.store.record_call(estimated_tokens, "embed")

        # Periodically cleanup old records (every ~20 calls)
        if self.store.get_request_count_in_window(60) % 20 == 0:
            self.store.cleanup_old_records()

        return result

    def generate_content(
        self,
        model_name: str,
        prompt: str,
        **kwargs,
    ) -> Any:
        """
        Generate content with rate limiting.

        Args:
            model_name: Model name (e.g., "gemini-1.5-flash")
            prompt: Text prompt for generation
            **kwargs: Additional arguments passed to model.generate_content

        Returns:
            Generation result from Google AI API

        Raises:
            RateLimitExceededError: If rate limits would be exceeded
        """
        # Count tokens in the prompt using Google's token counting API
        model = genai.GenerativeModel(model_name)
        token_count_result = model.count_tokens(prompt)
        input_tokens = token_count_result.total_tokens

        # Estimate total tokens including output
        # Conservative estimate: assume output is similar size to input
        estimated_tokens = input_tokens * 2

        # Check rate limits before making the call
        self._check_rate_limits(estimated_tokens)

        # Make the API call
        response = model.generate_content(prompt, **kwargs)

        # Try to get actual token usage from response metadata
        actual_tokens = estimated_tokens
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            # Google AI returns usage_metadata with accurate token counts
            actual_tokens = (
                response.usage_metadata.prompt_token_count
                + response.usage_metadata.candidates_token_count
            )

        # Record the call with actual token usage
        self.store.record_call(actual_tokens, "generate")

        # Periodically cleanup old records
        if self.store.get_request_count_in_window(60) % 20 == 0:
            self.store.cleanup_old_records()

        return response

    def get_current_usage(self) -> Dict[str, Any]:
        """
        Get current rate limit usage statistics.

        Returns:
            Dictionary with current RPM, TPM, and RPD usage:
            {
                'requests_per_minute': int,
                'rpm_limit': int,
                'tokens_per_minute': int,
                'tpm_limit': int,
                'requests_per_day': int,
                'rpd_limit': int,
                'rpm_remaining': int,
                'tpm_remaining': int,
                'rpd_remaining': int
            }
        """
        requests = self.store.get_request_count_in_window(60)
        tokens = self.store.get_token_count_in_window(60)
        daily_requests = self.store.get_daily_request_count()

        return {
            "requests_per_minute": requests,
            "rpm_limit": self.rpm_limit,
            "tokens_per_minute": tokens,
            "tpm_limit": self.tpm_limit,
            "requests_per_day": daily_requests,
            "rpd_limit": self.rpd_limit,
            "rpm_remaining": max(0, self.rpm_limit - requests),
            "tpm_remaining": max(0, self.tpm_limit - tokens),
            "rpd_remaining": max(0, self.rpd_limit - daily_requests),
        }
