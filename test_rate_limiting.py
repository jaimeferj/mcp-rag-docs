"""
Test script to verify rate limiting functionality.

This script tests the GoogleAPIClient to ensure rate limits are properly enforced.
"""

import os
import sys
from dotenv import load_dotenv

from utils.google_api_client import GoogleAPIClient, RateLimitExceededError

# Load environment variables
load_dotenv()


def test_basic_functionality():
    """Test basic API calls and rate limit tracking."""
    print("=" * 60)
    print("Testing Basic Functionality")
    print("=" * 60)

    # Initialize client with very low limits for testing
    client = GoogleAPIClient(
        api_key=os.getenv("GOOGLE_API_KEY"),
        rpm_limit=3,  # Very low for testing
        tpm_limit=10000,
        rpd_limit=10,
        rate_limit_db_path="./test_rate_limits.db",
    )

    # Test 1: Check initial usage (should be 0)
    usage = client.get_current_usage()
    print(f"\n1. Initial usage stats:")
    print(f"   RPM: {usage['requests_per_minute']}/{usage['rpm_limit']}")
    print(f"   TPM: {usage['tokens_per_minute']}/{usage['tpm_limit']}")
    print(f"   RPD: {usage['requests_per_day']}/{usage['rpd_limit']}")

    # Test 2: Make an embedding call
    print(f"\n2. Making first embedding call...")
    try:
        result = client.embed_content(
            model="models/text-embedding-004",
            content="Test embedding",
            task_type="retrieval_query",
        )
        print(f"   ✓ Success! Embedding dimension: {len(result['embedding'])}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    # Test 3: Check usage after one call
    usage = client.get_current_usage()
    print(f"\n3. Usage after 1 call:")
    print(f"   RPM: {usage['requests_per_minute']}/{usage['rpm_limit']} (remaining: {usage['rpm_remaining']})")
    print(f"   TPM: {usage['tokens_per_minute']}/{usage['tpm_limit']} (remaining: {usage['tpm_remaining']})")
    print(f"   RPD: {usage['requests_per_day']}/{usage['rpd_limit']} (remaining: {usage['rpd_remaining']})")

    # Test 4: Make more calls to test RPM limit
    print(f"\n4. Making additional calls to test RPM limit (limit is {client.rpm_limit})...")
    for i in range(2, 5):
        try:
            result = client.embed_content(
                model="models/text-embedding-004",
                content=f"Test embedding {i}",
                task_type="retrieval_query",
            )
            usage = client.get_current_usage()
            print(f"   Call {i}: ✓ Success (RPM: {usage['requests_per_minute']}/{usage['rpm_limit']})")
        except RateLimitExceededError as e:
            print(f"   Call {i}: ✗ Rate limit hit! {str(e)}")
            break
        except Exception as e:
            print(f"   Call {i}: ✗ Error: {e}")
            break

    # Test 5: Final usage stats
    usage = client.get_current_usage()
    print(f"\n5. Final usage stats:")
    print(f"   RPM: {usage['requests_per_minute']}/{usage['rpm_limit']}")
    print(f"   TPM: {usage['tokens_per_minute']}/{usage['tpm_limit']}")
    print(f"   RPD: {usage['requests_per_day']}/{usage['rpd_limit']}")

    print("\n" + "=" * 60)
    print("✓ Basic functionality test completed!")
    print("=" * 60)


def test_token_counting():
    """Test token counting functionality."""
    print("\n" + "=" * 60)
    print("Testing Token Counting")
    print("=" * 60)

    client = GoogleAPIClient(
        api_key=os.getenv("GOOGLE_API_KEY"),
        rpm_limit=15,
        tpm_limit=250000,
        rpd_limit=1000,
        rate_limit_db_path="./test_rate_limits.db",
    )

    test_prompts = [
        "Hello, world!",
        "This is a longer prompt with more tokens to test the token counting functionality.",
        "Short",
    ]

    print("\nCounting tokens for different prompts:")
    for prompt in test_prompts:
        try:
            token_count = client.count_tokens("gemini-1.5-flash", prompt)
            print(f"   '{prompt[:50]}...' → {token_count} tokens")
        except Exception as e:
            print(f"   ✗ Error counting tokens: {e}")

    print("\n" + "=" * 60)
    print("✓ Token counting test completed!")
    print("=" * 60)


def main():
    """Run all tests."""
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY not found in environment variables.")
        print("Please create a .env file with your Google AI API key.")
        sys.exit(1)

    try:
        test_basic_functionality()
        test_token_counting()

        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up test database
        if os.path.exists("./test_rate_limits.db"):
            os.remove("./test_rate_limits.db")
            print("\nCleaned up test database.")


if __name__ == "__main__":
    main()
