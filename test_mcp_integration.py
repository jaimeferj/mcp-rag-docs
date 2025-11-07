"""Test MCP server integration by simulating tool calls."""

import asyncio
import json
from mcp_server.server import call_tool

async def test_mcp_tools():
    """Test MCP tools by calling them directly."""
    print("=" * 80)
    print("MCP Server Integration Test")
    print("=" * 80)

    # Test 1: Query RAG
    print("\n[Test 1] Testing query_rag tool")
    print("-" * 80)

    result = await call_tool(
        "query_rag",
        {
            "question": "how should I use asset automation to update an asset everytime the upstream is updated",
            "top_k": 5
        }
    )

    print("Response:")
    for item in result:
        print(item.text)

    # Test 2: Get RAG stats
    print("\n[Test 2] Testing get_rag_stats tool")
    print("-" * 80)

    result = await call_tool("get_rag_stats", {})

    print("Response:")
    for item in result:
        print(item.text)

    # Test 3: Get tags
    print("\n[Test 3] Testing get_tags tool")
    print("-" * 80)

    result = await call_tool("get_tags", {})

    print("Response:")
    for item in result:
        print(item.text)

    # Test 4: Source code retrieval with a known Dagster URL
    print("\n[Test 4] Testing get_source_code tool")
    print("-" * 80)

    result = await call_tool(
        "get_source_code",
        {
            "github_url": "https://github.com/dagster-io/dagster/blob/master/python_modules/dagster/dagster/_core/definitions/decorators/asset_decorator.py#L130",
            "context_lines": 10
        }
    )

    print("Response:")
    for item in result:
        # Print first 1000 chars to avoid too much output
        text = item.text
        if len(text) > 1000:
            print(text[:1000] + "\n... (truncated)")
        else:
            print(text)

    # Test 5: List documents
    print("\n[Test 5] Testing list_documents tool")
    print("-" * 80)

    result = await call_tool("list_documents", {})

    print("Response:")
    for item in result:
        # Print first 1000 chars
        text = item.text
        if len(text) > 1000:
            print(text[:1000] + "\n... (truncated)")
        else:
            print(text)

    print("\n" + "=" * 80)
    print("All MCP Integration Tests Complete!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())
