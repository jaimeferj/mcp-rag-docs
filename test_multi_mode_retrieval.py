"""Test multi-mode source code retrieval."""

import asyncio
from mcp_server.server import call_tool

async def test_all_modes():
    """Test all retrieval modes."""
    print("=" * 80)
    print("Testing Multi-Mode Source Code Retrieval")
    print("=" * 80)

    # Test URL - AutomationCondition class
    test_url = "https://github.com/dagster-io/dagster/blob/master/python_modules/dagster/dagster/_core/definitions/decorators/asset_decorator.py#L130"

    # Test 1: Signature only
    print("\n[Test 1] Mode: signature")
    print("-" * 80)
    result1 = await call_tool(
        "get_source_code_advanced",
        {"github_url": test_url, "mode": "signature"}
    )
    for item in result1:
        print(item.text)

    # Test 2: Full implementation (default)
    print("\n\n[Test 2] Mode: full (first 1000 chars)")
    print("-" * 80)
    result2 = await call_tool(
        "get_source_code_advanced",
        {"github_url": test_url, "mode": "full", "context_lines": 15}
    )
    for item in result2:
        text = item.text
        print(text[:1000] + "..." if len(text) > 1000 else text)

    # Test 3: Class outline (if it's a class)
    print("\n\n[Test 3] Mode: outline (for class)")
    print("-" * 80)
    # Use a URL that points to a class definition
    class_url = "https://github.com/dagster-io/dagster/blob/master/python_modules/dagster/dagster/_core/definitions/auto_materialize_rule.py#L1"
    result3 = await call_tool(
        "get_source_code_advanced",
        {"github_url": class_url, "mode": "outline"}
    )
    for item in result3:
        text = item.text
        print(text[:1500] + "..." if len(text) > 1500 else text)

    # Test 4: Methods list
    print("\n\n[Test 4] Mode: methods_list (for class)")
    print("-" * 80)
    result4 = await call_tool(
        "get_source_code_advanced",
        {"github_url": class_url, "mode": "methods_list"}
    )
    for item in result4:
        print(item.text)

    # Test 5: Specific method extraction
    print("\n\n[Test 5] Extract specific method from class")
    print("-" * 80)
    # This would work if we know the class line and method name
    # For now, let's just show what the tool definition looks like
    print("To extract a specific method, use:")
    print('get_source_code_advanced(github_url="...", method_name="eager")')
    print("\nThis requires the URL to point to the class definition")

    print("\n" + "=" * 80)
    print("All mode tests complete!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_all_modes())
