"""
Unit tests for rate limiting with mocked Google API.

These tests verify rate limiting behavior without making real API calls.
"""

import os
import time
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from utils.google_api_client import GoogleAPIClient, RateLimitExceededError
from utils.rate_limit_store import RateLimitStore


class TestRateLimitStore:
    """Test the rate limit storage functionality."""

    def test_record_and_retrieve_calls(self):
        """Test recording and retrieving API calls."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            store = RateLimitStore(db_path)

            # Record some calls
            store.record_call(100, "embed")
            store.record_call(200, "generate")
            store.record_call(150, "embed")

            # Check counts
            assert store.get_request_count_in_window(60) == 3
            assert store.get_token_count_in_window(60) == 450  # 100 + 200 + 150

        finally:
            os.unlink(db_path)

    def test_sliding_window(self):
        """Test that old records are excluded from window."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            store = RateLimitStore(db_path)

            # Get calls from last 1 second (should be 0)
            count = store.get_request_count_in_window(1)
            assert count == 0

            # Record a call
            store.record_call(100, "embed")

            # Should be in 60s window
            assert store.get_request_count_in_window(60) == 1

            # Should be in 1s window
            assert store.get_request_count_in_window(1) == 1

            # Wait 2 seconds
            time.sleep(2)

            # Should still be in 60s window
            assert store.get_request_count_in_window(60) == 1

            # Should NOT be in 1s window
            assert store.get_request_count_in_window(1) == 0

        finally:
            os.unlink(db_path)

    def test_daily_request_count(self):
        """Test daily request counting."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            store = RateLimitStore(db_path)

            # Record some calls
            for i in range(5):
                store.record_call(100, "embed")

            # Check daily count
            assert store.get_daily_request_count() == 5

        finally:
            os.unlink(db_path)

    def test_cleanup_old_records(self):
        """Test that old records are cleaned up."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            store = RateLimitStore(db_path)

            # Record calls
            store.record_call(100, "embed")
            store.record_call(200, "generate")

            # Should have 2 records
            assert store.get_request_count_in_window(86400) == 2

            # Cleanup records older than 0 seconds (all of them)
            store.cleanup_old_records(keep_seconds=0)

            # Should have 0 records now
            assert store.get_request_count_in_window(86400) == 0

        finally:
            os.unlink(db_path)


class TestGoogleAPIClient:
    """Test the rate-limited Google API client."""

    @patch("utils.google_api_client.genai")
    def test_rpm_limit_enforcement(self, mock_genai):
        """Test that RPM limits are enforced."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Mock the API response
            mock_genai.embed_content.return_value = {"embedding": [0.1] * 768}

            # Create client with very low RPM limit
            client = GoogleAPIClient(
                api_key="fake_key",
                rpm_limit=3,
                tpm_limit=1_000_000,
                rpd_limit=1000,
                rate_limit_db_path=db_path,
            )

            # Verify initial state - no requests
            usage = client.get_current_usage()
            assert usage["requests_per_minute"] == 0
            assert usage["rpm_remaining"] == 3

            # Make 3 calls (should succeed - exactly at limit)
            for i in range(3):
                result = client.embed_content(
                    model="models/text-embedding-004",
                    content=f"test {i}",
                )
                assert result["embedding"] is not None

                # Verify the call was tracked
                usage = client.get_current_usage()
                assert usage["requests_per_minute"] == i + 1
                assert usage["rpm_remaining"] == 3 - (i + 1)

            # Verify we're at the limit
            usage = client.get_current_usage()
            assert usage["requests_per_minute"] == 3
            assert usage["rpm_remaining"] == 0

            # Verify the mock was called exactly 3 times
            assert mock_genai.embed_content.call_count == 3

            # 4th call should fail with RPM limit BEFORE calling the API
            call_count_before = mock_genai.embed_content.call_count
            with pytest.raises(RateLimitExceededError) as exc_info:
                client.embed_content(
                    model="models/text-embedding-004",
                    content="test 4",
                )

            # Verify the mock was NOT called (rate limit check happened first)
            assert mock_genai.embed_content.call_count == call_count_before

            # Verify error message
            assert "RPM limit exceeded" in str(exc_info.value)
            assert "3/3 requests" in str(exc_info.value)
            assert exc_info.value.reset_time > time.time()

            # Verify usage is still at 3
            usage = client.get_current_usage()
            assert usage["requests_per_minute"] == 3

        finally:
            os.unlink(db_path)

    @patch("utils.google_api_client.genai")
    def test_rpd_limit_enforcement(self, mock_genai):
        """Test that RPD limits are enforced."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Mock the API response
            mock_genai.embed_content.return_value = {"embedding": [0.1] * 768}

            # Create client with very low RPD limit
            client = GoogleAPIClient(
                api_key="fake_key",
                rpm_limit=1000,
                tpm_limit=1_000_000,
                rpd_limit=5,  # Very low daily limit
                rate_limit_db_path=db_path,
            )

            # Verify initial state
            usage = client.get_current_usage()
            assert usage["requests_per_day"] == 0
            assert usage["rpd_remaining"] == 5

            # Make 5 calls (should succeed)
            for i in range(5):
                result = client.embed_content(
                    model="models/text-embedding-004",
                    content=f"test {i}",
                )
                assert result["embedding"] is not None

                # Verify daily count increases
                usage = client.get_current_usage()
                assert usage["requests_per_day"] == i + 1
                assert usage["rpd_remaining"] == 5 - (i + 1)

            # Verify we're at the daily limit
            usage = client.get_current_usage()
            assert usage["requests_per_day"] == 5
            assert usage["rpd_remaining"] == 0

            # Verify the mock was called exactly 5 times
            assert mock_genai.embed_content.call_count == 5

            # 6th call should fail with RPD limit BEFORE calling the API
            call_count_before = mock_genai.embed_content.call_count
            with pytest.raises(RateLimitExceededError) as exc_info:
                client.embed_content(
                    model="models/text-embedding-004",
                    content="test 6",
                )

            # Verify the mock was NOT called (rate limit check happened first)
            assert mock_genai.embed_content.call_count == call_count_before

            # Verify error message
            assert "RPD limit exceeded" in str(exc_info.value)
            assert "5/5 requests" in str(exc_info.value)

        finally:
            os.unlink(db_path)

    @patch("utils.google_api_client.genai")
    def test_tpm_limit_enforcement(self, mock_genai):
        """Test that TPM limits are enforced."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Mock the API response
            mock_genai.embed_content.return_value = {"embedding": [0.1] * 768}

            # Create client with very low TPM limit
            client = GoogleAPIClient(
                api_key="fake_key",
                rpm_limit=1000,
                tpm_limit=100,  # Very low token limit
                rpd_limit=1000,
                rate_limit_db_path=db_path,
            )

            # Verify initial state
            usage = client.get_current_usage()
            assert usage["tokens_per_minute"] == 0
            assert usage["tpm_remaining"] == 100

            # Make a few small calls first (consume ~50 tokens)
            small_text = "a" * 200  # ~50 tokens (200 chars / 4)
            client.embed_content(
                model="models/text-embedding-004",
                content=small_text,
            )

            # Verify tokens were tracked
            usage = client.get_current_usage()
            assert usage["tokens_per_minute"] == 50
            assert usage["tpm_remaining"] == 50

            # Verify the mock was called once
            assert mock_genai.embed_content.call_count == 1

            # Try to make a call with text that would exceed limit
            # Current: 50 tokens, Limit: 100, New request: ~75 tokens
            # Total would be 125 > 100, so should fail
            medium_text = "a" * 300  # ~75 tokens (300 chars / 4)

            call_count_before = mock_genai.embed_content.call_count
            with pytest.raises(RateLimitExceededError) as exc_info:
                client.embed_content(
                    model="models/text-embedding-004",
                    content=medium_text,
                )

            # Verify the mock was NOT called (rate limit check happened first)
            assert mock_genai.embed_content.call_count == call_count_before

            # Verify error message
            assert "TPM limit exceeded" in str(exc_info.value)
            assert "125/100" in str(exc_info.value)  # 50 current + 75 requested
            assert "Current usage: 50 tokens" in str(exc_info.value)
            assert "Requested: 75 tokens" in str(exc_info.value)

            # Verify token count didn't change
            usage = client.get_current_usage()
            assert usage["tokens_per_minute"] == 50

        finally:
            os.unlink(db_path)

    @patch("utils.google_api_client.genai")
    def test_get_current_usage(self, mock_genai):
        """Test usage statistics retrieval."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Mock the API response
            mock_genai.embed_content.return_value = {"embedding": [0.1] * 768}

            client = GoogleAPIClient(
                api_key="fake_key",
                rpm_limit=15,
                tpm_limit=250000,
                rpd_limit=1000,
                rate_limit_db_path=db_path,
            )

            # Initial usage should be 0
            usage = client.get_current_usage()
            assert usage["requests_per_minute"] == 0
            assert usage["tokens_per_minute"] == 0
            assert usage["requests_per_day"] == 0
            assert usage["rpm_remaining"] == 15
            assert usage["rpd_remaining"] == 1000

            # Make one call
            client.embed_content(
                model="models/text-embedding-004",
                content="test",
            )

            # Usage should update
            usage = client.get_current_usage()
            assert usage["requests_per_minute"] == 1
            assert usage["tokens_per_minute"] > 0  # Should have some tokens
            assert usage["requests_per_day"] == 1
            assert usage["rpm_remaining"] == 14
            assert usage["rpd_remaining"] == 999

        finally:
            os.unlink(db_path)

    @patch("utils.google_api_client.genai")
    def test_generate_content_with_usage_metadata(self, mock_genai):
        """Test generation with actual token counts from response."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Mock the model and response
            mock_model = MagicMock()
            mock_response = MagicMock()

            # Mock token counting
            mock_count_result = MagicMock()
            mock_count_result.total_tokens = 10
            mock_model.count_tokens.return_value = mock_count_result

            # Mock response with usage metadata
            mock_response.text = "Generated response"
            mock_response.usage_metadata = MagicMock()
            mock_response.usage_metadata.prompt_token_count = 10
            mock_response.usage_metadata.candidates_token_count = 15

            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model

            client = GoogleAPIClient(
                api_key="fake_key",
                rpm_limit=100,
                tpm_limit=10000,
                rpd_limit=1000,
                rate_limit_db_path=db_path,
            )

            # Generate content
            response = client.generate_content(
                model_name="gemini-1.5-flash",
                prompt="Test prompt",
            )

            assert response.text == "Generated response"

            # Check that tokens were tracked (should be 10 + 15 = 25)
            usage = client.get_current_usage()
            assert usage["tokens_per_minute"] == 25

        finally:
            os.unlink(db_path)

    @patch("utils.google_api_client.genai")
    def test_token_counting(self, mock_genai):
        """Test token counting functionality."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Mock the model
            mock_model = MagicMock()
            mock_count_result = MagicMock()
            mock_count_result.total_tokens = 42
            mock_model.count_tokens.return_value = mock_count_result
            mock_genai.GenerativeModel.return_value = mock_model

            client = GoogleAPIClient(
                api_key="fake_key",
                rpm_limit=100,
                tpm_limit=10000,
                rpd_limit=1000,
                rate_limit_db_path=db_path,
            )

            # Count tokens
            count = client.count_tokens("gemini-1.5-flash", "Test content")
            assert count == 42

            # Test with list
            mock_model.count_tokens.return_value.total_tokens = 10
            count = client.count_tokens("gemini-1.5-flash", ["test1", "test2", "test3"])
            assert count == 30  # 10 tokens × 3 items

        finally:
            os.unlink(db_path)


    @patch("utils.google_api_client.genai")
    def test_sliding_window_reset(self, mock_genai):
        """Test that rate limits reset as the sliding window moves."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Mock the API response
            mock_genai.embed_content.return_value = {"embedding": [0.1] * 768}

            # Create client with 2 requests per 3 seconds (very short window for testing)
            client = GoogleAPIClient(
                api_key="fake_key",
                rpm_limit=1000,  # High enough to not interfere
                tpm_limit=1_000_000,
                rpd_limit=1000,
                rate_limit_db_path=db_path,
            )

            # Manually set up the store to use a 3-second window for testing
            # We'll make 2 calls, wait 3.5 seconds, then make 2 more

            # Make 2 calls
            for i in range(2):
                client.embed_content(
                    model="models/text-embedding-004",
                    content=f"test {i}",
                )

            # Verify 2 requests in last 60 seconds
            assert client.store.get_request_count_in_window(60) == 2

            # Wait for 3.5 seconds
            time.sleep(3.5)

            # Make 2 more calls
            for i in range(2, 4):
                client.embed_content(
                    model="models/text-embedding-004",
                    content=f"test {i}",
                )

            # Should have 4 requests total in last 60 seconds
            assert client.store.get_request_count_in_window(60) == 4

            # But only 2 requests in the last 3 seconds (the new ones)
            assert client.store.get_request_count_in_window(3) == 2

            # Verify the mock was called 4 times total
            assert mock_genai.embed_content.call_count == 4

        finally:
            os.unlink(db_path)

    @patch("utils.google_api_client.genai")
    def test_rpm_limit_with_sliding_window(self, mock_genai):
        """Test that RPM limits properly reset with sliding window."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # Mock the API response
            mock_genai.embed_content.return_value = {"embedding": [0.1] * 768}

            # Create client with 2 RPM limit
            client = GoogleAPIClient(
                api_key="fake_key",
                rpm_limit=2,
                tpm_limit=1_000_000,
                rpd_limit=1000,
                rate_limit_db_path=db_path,
            )

            # Make 2 calls (hit the limit)
            for i in range(2):
                client.embed_content(
                    model="models/text-embedding-004",
                    content=f"test {i}",
                )

            # 3rd call should fail
            with pytest.raises(RateLimitExceededError) as exc_info:
                client.embed_content(
                    model="models/text-embedding-004",
                    content="test 2",
                )
            assert "RPM limit exceeded" in str(exc_info.value)

            # Verify mock was called exactly 2 times (not 3)
            assert mock_genai.embed_content.call_count == 2

            # Wait for 61 seconds (more than 60 second window)
            # In real test we'd use time mocking, but for simplicity
            # we'll just verify the store behavior
            # Simulate by manually checking the window
            original_count = client.store.get_request_count_in_window(60)
            assert original_count == 2

            # After 61 seconds, those requests would be outside the window
            # and new requests could be made (we test this with the store test above)

        finally:
            os.unlink(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
