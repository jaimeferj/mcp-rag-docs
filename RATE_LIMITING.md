# Rate Limiting Implementation

This document describes the global rate-limited interface for Google Gemini API calls.

## Overview

The rate limiting system enforces three types of limits:
- **RPM (Requests Per Minute)**: Default 15 requests/minute
- **TPM (Tokens Per Minute)**: Default 250K tokens/minute
- **RPD (Requests Per Day)**: Default 1000 requests/day

Rate limits are tracked in a persistent SQLite database, ensuring accuracy across application restarts.

## Architecture

### Components

1. **`RateLimitStore`** (`utils/rate_limit_store.py`)
   - SQLite-backed persistence for API call tracking
   - Thread-safe operations with locking
   - Tracks timestamp, tokens used, and call type for each API call
   - Provides sliding window queries (1 minute, 24 hours)

2. **`GoogleAPIClient`** (`utils/google_api_client.py`)
   - Wrapper around Google Generative AI SDK
   - Enforces rate limits before each API call
   - Throws `RateLimitExceededError` immediately when limits exceeded
   - Methods: `embed_content()`, `generate_content()`, `count_tokens()`, `get_current_usage()`

3. **`GoogleEmbeddingService`** (`utils/embeddings.py`)
   - Updated to use `GoogleAPIClient` for all embeddings
   - Supports dependency injection of shared client

4. **`RAGSystem`** (`rag_server/rag_system.py`)
   - Creates shared `GoogleAPIClient` instance
   - Uses it for both embeddings and generation

## Configuration

Add these settings to your `.env` file:

```bash
# Rate Limiting Configuration
# For gemini-2.5-flash-lite: 15 RPM, 250K TPM, 1000 RPD (free tier)
# For gemini-1.5-flash: 15 RPM, 1M TPM, 1500 RPD (free tier)
GOOGLE_API_RPM_LIMIT=15
GOOGLE_API_TPM_LIMIT=250000
GOOGLE_API_RPD_LIMIT=1000
RATE_LIMIT_DB_PATH=./rate_limits.db
```

## Usage

### Basic Usage

```python
from utils.google_api_client import GoogleAPIClient, RateLimitExceededError
from config.settings import settings

# Initialize the client
client = GoogleAPIClient(
    api_key=settings.google_api_key,
    rpm_limit=settings.google_api_rpm_limit,
    tpm_limit=settings.google_api_tpm_limit,
    rpd_limit=settings.google_api_rpd_limit,
    rate_limit_db_path=settings.rate_limit_db_path,
)

# Make API calls
try:
    # Embedding
    result = client.embed_content(
        model="models/text-embedding-004",
        content="Your text here",
        task_type="retrieval_query"
    )

    # Generation
    response = client.generate_content(
        model_name="gemini-1.5-flash",
        prompt="Your prompt here"
    )

except RateLimitExceededError as e:
    print(f"Rate limit exceeded: {e}")
    print(f"Rate limit will reset at: {e.reset_time}")
```

### Checking Current Usage

```python
usage = client.get_current_usage()
print(f"RPM: {usage['requests_per_minute']}/{usage['rpm_limit']}")
print(f"TPM: {usage['tokens_per_minute']}/{usage['tpm_limit']}")
print(f"RPD: {usage['requests_per_day']}/{usage['rpd_limit']}")
print(f"Remaining requests today: {usage['rpd_remaining']}")
```

### Shared Client Pattern (Recommended)

```python
# In RAGSystem, a single client is shared across all services
class RAGSystem:
    def __init__(self):
        # Create one client
        self.api_client = GoogleAPIClient(...)

        # Share it with embedding service
        self.embedding_service = GoogleEmbeddingService(
            api_key=settings.google_api_key,
            api_client=self.api_client  # Shared client
        )

        # Use directly for generation
        response = self.api_client.generate_content(...)
```

## Error Handling

When rate limits are exceeded, a `RateLimitExceededError` is raised with:
- Descriptive error message
- Which limit was exceeded (RPM, TPM, or RPD)
- Time until the limit resets

```python
try:
    result = client.embed_content(...)
except RateLimitExceededError as e:
    # Error message includes reset time
    print(str(e))
    # Example: "RPM limit exceeded: 15/15 requests in last 60s. Rate limit will reset in 23.5 seconds."

    # Access reset timestamp programmatically
    wait_time = e.reset_time - time.time()
    print(f"Wait {wait_time:.1f} seconds")
```

## Token Counting

The client uses Google's official token counting API for accuracy:

```python
# Count tokens before generation
token_count = client.count_tokens(
    model_name="gemini-1.5-flash",
    content="Your prompt text"
)

# For embeddings, tokens are estimated (1 token ≈ 4 characters)
# For generation, actual token counts are retrieved from response metadata
```

## Database Maintenance

The system automatically cleans up old records:
- Cleanup happens every ~20 API calls
- Records older than 24 hours are removed
- Database file: `./rate_limits.db` (configurable)

## Rate Limit Behavior

### Sliding Window

Rate limits use a **sliding window** approach:
- RPM: Counts requests in the last 60 seconds
- TPD: Counts requests in the last 24 hours
- As old requests age out of the window, capacity becomes available

### Check Order

Limits are checked in this order:
1. **RPD** (Requests Per Day) - checked first
2. **RPM** (Requests Per Minute)
3. **TPM** (Tokens Per Minute)

### Token Estimation

- **Embeddings**: Estimated at ~1 token per 4 characters
- **Generation (input)**: Uses Google's `count_tokens()` API
- **Generation (output)**: Estimated as 2× input tokens, then replaced with actual count from response metadata

## Testing

Run the test script to verify rate limiting:

```bash
# Make sure GOOGLE_API_KEY is set in .env
uv run test_rate_limiting.py
```

The test will:
1. Make API calls with very low limits
2. Verify rate limit enforcement
3. Test token counting
4. Display usage statistics

## Integration Points

The rate limiting is integrated at these points:

1. **`utils/embeddings.py`**: All embedding calls go through `GoogleAPIClient`
2. **`rag_server/rag_system.py`**: Generation calls use `api_client.generate_content()`
3. **Configuration**: Rate limits loaded from `config/settings.py` (from env vars)

## Performance Considerations

- **Thread-safe**: Uses locks for concurrent requests
- **Minimal overhead**: Database queries use indexes on timestamp
- **Auto-cleanup**: Old records automatically purged
- **Persistent**: Survives application restarts

## Customization

To adjust limits for different Google AI tiers:

```python
# Pay-as-you-go tier (example)
client = GoogleAPIClient(
    api_key=api_key,
    rpm_limit=2000,      # Higher limit
    tpm_limit=4_000_000, # 4M tokens/min
    rpd_limit=50_000,    # 50k requests/day
)
```

See Google AI pricing docs for your tier's limits:
https://ai.google.dev/pricing
