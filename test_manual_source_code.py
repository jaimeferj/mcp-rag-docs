"""Test enhanced query by manually adding a query that we know has source code."""

import asyncio
from mcp_server.server import call_tool

async def test_manual():
    """Test with a manual insertion of a query response that includes a GitHub URL."""
    print("=" * 80)
    print("Testing Complete Enhanced Query Flow")
    print("=" * 80)

    # First, let's do a query and show what we get
    print("\n[Test 1] Regular query about asset decorator")
    print("-" * 80)

    result1 = await call_tool(
        "query_rag",
        {"question": "what is @asset decorator", "top_k": 3}
    )

    print("Regular query response (truncated):")
    for item in result1:
        text = item.text
        print(text[:600] + "..." if len(text) > 600 else text)

    # Now test the enhanced version
    print("\n\n[Test 2] Enhanced query about asset decorator")
    print("-" * 80)

    result2 = await call_tool(
        "query_rag_enhanced",
        {"question": "what is @asset decorator", "top_k": 3, "max_followups": 1}
    )

    print("\nEnhanced query response:")
    for item in result2:
        print(item.text)

    # Test with source code tool directly
    print("\n\n[Test 3] Direct source code retrieval")
    print("-" * 80)

    result3 = await call_tool(
        "get_source_code",
        {
            "github_url": "https://github.com/dagster-io/dagster/blob/master/python_modules/dagster/dagster/_core/definitions/decorators/asset_decorator.py#L130",
            "context_lines": 15
        }
    )

    print("Source code retrieval response (truncated):")
    for item in result3:
        text = item.text
        print(text[:1000] + "..." if len(text) > 1000 else text)

    print("\n" + "=" * 80)
    print("All tests complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_manual())
