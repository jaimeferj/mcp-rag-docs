"""Test that MCP tool descriptions are properly detailed."""

import asyncio
from mcp_server.server import list_tools

async def test_tool_descriptions():
    """Test tool descriptions."""
    print("=" * 80)
    print("MCP Tool Descriptions")
    print("=" * 80)

    tools = await list_tools()

    for tool in tools:
        print(f"\n{'=' * 80}")
        print(f"Tool: {tool.name}")
        print(f"{'=' * 80}")
        print(f"\nDescription:")
        print(tool.description)

        if tool.name == "get_source_code_advanced":
            print("\n[Key Features Highlighted]")
            desc = tool.description
            if "MODE DETAILS" in desc:
                print("✓ Contains MODE DETAILS section")
            if "signature" in desc and "~1-2 lines" in desc:
                print("✓ Explains signature mode with line count")
            if "methods_list" in desc and "~10-30 lines" in desc:
                print("✓ Explains methods_list mode with line count")
            if "outline" in desc and "~50-200 lines" in desc:
                print("✓ Explains outline mode with line count")
            if "full" in desc and "~100-1000+ lines" in desc:
                print("✓ Explains full mode with line count")
            if "DECISION GUIDE" in desc:
                print("✓ Contains DECISION GUIDE section")
            if "What is X?" in desc:
                print("✓ Contains usage examples")

        print("\nInput Schema:")
        for prop_name, prop_info in tool.inputSchema.get("properties", {}).items():
            required = "required" if prop_name in tool.inputSchema.get("required", []) else "optional"
            print(f"  - {prop_name} ({required}): {prop_info.get('description', 'No description')[:80]}...")

    print("\n" + "=" * 80)
    print(f"Total tools: {len(tools)}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_tool_descriptions())
