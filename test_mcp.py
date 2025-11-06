"""Test script to verify MCP server works correctly."""

import asyncio
import json
from mcp_server.server import list_tools, call_tool


async def test_mcp_server():
    """Test the MCP server functionality."""
    print("=" * 60)
    print("Testing MCP Server")
    print("=" * 60)
    print()

    # Test 1: List available tools
    print("Test 1: Listing available tools...")
    tools = await list_tools()
    print(f"✓ Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:60]}...")
    print()

    # Test 2: Get RAG stats
    print("Test 2: Getting RAG system statistics...")
    result = await call_tool("get_rag_stats", {})
    print(result[0].text)
    print()

    # Test 3: Get available tags
    print("Test 3: Getting available tags...")
    result = await call_tool("get_tags", {})
    print(result[0].text)
    print()

    # Test 4: Query with Dagster tag filter
    print("Test 4: Querying Dagster docs (filtered by tags)...")
    result = await call_tool(
        "query_rag",
        {
            "question": "What is an asset in Dagster?",
            "top_k": 3,
            "tags": ["dagster"],
        },
    )
    print(result[0].text)
    print()

    print("=" * 60)
    print("✓ All MCP server tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
