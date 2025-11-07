"""Test class-specific retrieval modes."""

import asyncio
from mcp_server.server import call_tool

async def test_class_modes():
    """Test class-specific retrieval modes."""
    print("=" * 80)
    print("Testing Class-Specific Retrieval Modes")
    print("=" * 80)

    # AutomationCondition class URL
    class_url = "https://github.com/dagster-io/dagster/blob/master/python_modules/dagster/dagster/_core/definitions/declarative_automation/automation_condition.py#L63"

    # Test 1: Signature
    print("\n[Test 1] Class Signature")
    print("-" * 80)
    result1 = await call_tool(
        "get_source_code_advanced",
        {"github_url": class_url, "mode": "signature"}
    )
    for item in result1:
        print(item.text)

    # Test 2: Methods List
    print("\n[Test 2] Methods List")
    print("-" * 80)
    result2 = await call_tool(
        "get_source_code_advanced",
        {"github_url": class_url, "mode": "methods_list"}
    )
    for item in result2:
        print(item.text)

    # Test 3: Class Outline
    print("\n[Test 3] Class Outline (first 2000 chars)")
    print("-" * 80)
    result3 = await call_tool(
        "get_source_code_advanced",
        {"github_url": class_url, "mode": "outline"}
    )
    for item in result3:
        text = item.text
        print(text[:2000] + "..." if len(text) > 2000 else text)

    # Test 4: Full Implementation (truncated)
    print("\n[Test 4] Full Implementation (first 1500 chars)")
    print("-" * 80)
    result4 = await call_tool(
        "get_source_code_advanced",
        {"github_url": class_url, "mode": "full", "context_lines": 30}
    )
    for item in result4:
        text = item.text
        print(text[:1500] + "..." if len(text) > 1500 else text)

    # Test 5: Specific Method
    print("\n[Test 5] Extract Specific Method: 'eager'")
    print("-" * 80)
    result5 = await call_tool(
        "get_source_code_advanced",
        {"github_url": class_url, "method_name": "eager"}
    )
    for item in result5:
        text = item.text
        print(text[:1500] + "..." if len(text) > 1500 else text)

    print("\n" + "=" * 80)
    print("All class mode tests complete!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_class_modes())
