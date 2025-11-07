# Rate Limiting Test Coverage

This document describes what each test verifies to ensure rate limiting works correctly.

## Test Suite Summary

**Total Tests: 12**
**Status: ✅ All Passing**

## RateLimitStore Tests (4 tests)

### 1. `test_record_and_retrieve_calls`
**What it verifies:**
- Records are properly stored in SQLite database
- Request counts are accurate (3 calls → count = 3)
- Token counts are accurately summed (100 + 200 + 150 = 450)

**Assertions:**
```python
assert store.get_request_count_in_window(60) == 3
assert store.get_token_count_in_window(60) == 450
```

### 2. `test_sliding_window`
**What it verifies:**
- Sliding window correctly includes/excludes records based on time
- Recent calls (within 1 second) are counted
- Old calls (after 2 seconds) are excluded from 1-second window
- But old calls are still in 60-second window

**Assertions:**
```python
# Immediately after recording
assert store.get_request_count_in_window(1) == 1
# After 2 seconds
assert store.get_request_count_in_window(1) == 0  # NOT in 1s window
assert store.get_request_count_in_window(60) == 1  # Still in 60s window
```

### 3. `test_daily_request_count`
**What it verifies:**
- Daily (24-hour) request counting works correctly
- 5 calls → daily count = 5

**Assertions:**
```python
assert store.get_daily_request_count() == 5
```

### 4. `test_cleanup_old_records`
**What it verifies:**
- Old records are properly deleted from database
- Cleanup with keep_seconds=0 removes all records

**Assertions:**
```python
# Before cleanup
assert store.get_request_count_in_window(86400) == 2
# After cleanup
assert store.get_request_count_in_window(86400) == 0
```

---

## GoogleAPIClient Tests (8 tests)

### 5. `test_rpm_limit_enforcement` ⭐ CRITICAL
**What it verifies:**
- RPM limit is strictly enforced
- Exactly N calls succeed when limit is N
- Call N+1 fails with `RateLimitExceededError`
- **Rate limit check happens BEFORE calling Google API** (no wasted API calls)
- Usage statistics accurately track requests
- Remaining capacity decreases correctly

**Key Assertions:**
```python
# Initial state
assert usage["requests_per_minute"] == 0
assert usage["rpm_remaining"] == 3

# After each call, verify tracking
for i in range(3):
    # Make call
    assert usage["requests_per_minute"] == i + 1
    assert usage["rpm_remaining"] == 3 - (i + 1)

# At limit
assert usage["requests_per_minute"] == 3
assert usage["rpm_remaining"] == 0

# 4th call fails BEFORE calling API
call_count_before = mock_genai.embed_content.call_count
# Try to make 4th call → RateLimitExceededError
assert mock_genai.embed_content.call_count == call_count_before  # NOT incremented!

# Error message verification
assert "RPM limit exceeded" in str(exc_info.value)
assert "3/3 requests" in str(exc_info.value)
```

### 6. `test_rpd_limit_enforcement` ⭐ CRITICAL
**What it verifies:**
- Daily (RPD) limit is strictly enforced
- 5 calls succeed with limit of 5
- 6th call fails with error
- **Rate limit check happens BEFORE calling Google API**
- Daily usage is tracked accurately

**Key Assertions:**
```python
# Verify daily tracking after each call
for i in range(5):
    assert usage["requests_per_day"] == i + 1
    assert usage["rpd_remaining"] == 5 - (i + 1)

# 6th call fails BEFORE calling API
call_count_before = mock_genai.embed_content.call_count
# Try 6th call → RateLimitExceededError
assert mock_genai.embed_content.call_count == call_count_before

# Error message verification
assert "RPD limit exceeded" in str(exc_info.value)
assert "5/5 requests" in str(exc_info.value)
```

### 7. `test_tpm_limit_enforcement` ⭐ CRITICAL
**What it verifies:**
- Token (TPM) limit is strictly enforced
- Current token usage is tracked
- Request that would exceed limit is rejected
- Token estimation works correctly (1 token ≈ 4 chars)
- **Rate limit check happens BEFORE calling Google API**

**Key Assertions:**
```python
# After 50 tokens consumed
assert usage["tokens_per_minute"] == 50
assert usage["tpm_remaining"] == 50

# Try to add 75 more tokens (would exceed 100 limit)
# 50 current + 75 new = 125 > 100 → should fail

call_count_before = mock_genai.embed_content.call_count
# Try call → RateLimitExceededError
assert mock_genai.embed_content.call_count == call_count_before

# Detailed error message verification
assert "TPM limit exceeded" in str(exc_info.value)
assert "125/100" in str(exc_info.value)
assert "Current usage: 50 tokens" in str(exc_info.value)
assert "Requested: 75 tokens" in str(exc_info.value)

# Token count unchanged
assert usage["tokens_per_minute"] == 50
```

### 8. `test_get_current_usage`
**What it verifies:**
- Usage statistics API returns accurate data
- All three limits (RPM, TPM, RPD) are tracked
- Remaining capacity is calculated correctly

**Assertions:**
```python
# Initial state
assert usage["requests_per_minute"] == 0
assert usage["tokens_per_minute"] == 0
assert usage["requests_per_day"] == 0

# After one call
assert usage["requests_per_minute"] == 1
assert usage["tokens_per_minute"] > 0
assert usage["requests_per_day"] == 1
assert usage["rpm_remaining"] == 14
assert usage["rpd_remaining"] == 999
```

### 9. `test_generate_content_with_usage_metadata`
**What it verifies:**
- Text generation calls work with rate limiting
- Actual token counts from API response are used (not estimates)
- Usage metadata (prompt_token_count + candidates_token_count) is tracked

**Assertions:**
```python
# Mock response with 10 input + 15 output = 25 total tokens
response = client.generate_content(...)
assert response.text == "Generated response"

# Verify actual tokens tracked
usage = client.get_current_usage()
assert usage["tokens_per_minute"] == 25  # Not estimated, actual from API
```

### 10. `test_token_counting`
**What it verifies:**
- Token counting API works correctly
- Single text returns correct count
- List of texts returns sum of counts

**Assertions:**
```python
count = client.count_tokens("gemini-1.5-flash", "Test content")
assert count == 42  # From mock

count = client.count_tokens("gemini-1.5-flash", ["test1", "test2", "test3"])
assert count == 30  # 10 tokens × 3 items
```

### 11. `test_sliding_window_reset`
**What it verifies:**
- Sliding window properly handles time progression
- Old requests fall out of window as time passes
- New requests are tracked separately

**Assertions:**
```python
# Make 2 calls
assert client.store.get_request_count_in_window(60) == 2

# Wait 3.5 seconds
time.sleep(3.5)

# Make 2 more calls
# 4 total in 60s window
assert client.store.get_request_count_in_window(60) == 4
# But only 2 in last 3 seconds (old ones fell off)
assert client.store.get_request_count_in_window(3) == 2
```

### 12. `test_rpm_limit_with_sliding_window`
**What it verifies:**
- Rate limits properly block calls when limit is reached
- Conceptually verifies that after window expires, new calls could be made

**Assertions:**
```python
# Hit limit with 2 calls
for i in range(2):
    client.embed_content(...)

# 3rd call fails
with pytest.raises(RateLimitExceededError):
    client.embed_content(...)

# Mock was NOT called for failed attempt
assert mock_genai.embed_content.call_count == 2  # Not 3!
```

---

## Key Testing Principles

### ✅ What We're Testing

1. **Rate limits are enforced correctly** - Exactly N calls allowed when limit is N
2. **No wasted API calls** - Rate limit checks happen BEFORE calling Google API
3. **Accurate tracking** - Requests, tokens, and daily counts are precise
4. **Persistence works** - SQLite storage correctly records and retrieves data
5. **Sliding window works** - Old requests properly fall out of time windows
6. **Error messages are clear** - Exceptions include limit details and reset times
7. **Token counting** - Both estimation (embeddings) and actual counts (generation)

### 🎯 Critical Test Features

- **Mock verification**: Tests confirm Google API is NOT called when rate limited
- **State verification**: Usage statistics checked before AND after each call
- **Error validation**: Exception messages verified for accuracy
- **Time-based behavior**: Sliding window tested with actual time delays
- **Edge cases**: Testing exactly at limit, exceeding by small amounts

### 📊 Test Execution

Run all tests:
```bash
uv run pytest test_rate_limiting_mock.py -v
```

Expected output:
```
12 passed in ~6 seconds
```

The tests use real time delays (2-3 seconds) to verify sliding window behavior, which is why they take a few seconds to complete.
