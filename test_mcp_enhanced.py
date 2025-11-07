"""Test enhanced MCP query tool."""

import asyncio
from mcp_server.server import call_tool

async def test_enhanced_mcp():
    """Test the enhanced query MCP tool."""
    print("=" * 80)
    print("Testing Enhanced MCP Query Tool")
    print("=" * 80)

    result = await call_tool(
        "query_rag_enhanced",
        {
            "question": "how should I use asset automation to update an asset everytime the upstream is updated",
            "top_k": 5,
            "max_followups": 2
        }
    )

    print("\nMCP Tool Response:")
    print("=" * 80)
    for item in result:
        print(item.text)

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_enhanced_mcp())
