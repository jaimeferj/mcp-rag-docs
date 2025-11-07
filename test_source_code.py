"""Test script for source code retrieval functionality."""

from rag_server.rag_system import RAGSystem

def test_source_code_retrieval():
    """Test various scenarios for source code retrieval."""
    rag = RAGSystem()

    print("=" * 80)
    print("Test 1: Valid GitHub URL with line number")
    print("=" * 80)
    url1 = "https://github.com/dagster-io/dagster/blob/master/python_modules/dagster/dagster/_core/definitions/decorators/asset_decorator.py#L130"
    result1 = rag.get_source_code(url1, context_lines=10)

    if result1.get("error"):
        print(f"ERROR: {result1['error']}")
    else:
        print(f"File: {result1['file_path']}")
        print(f"Lines: {result1['start_line']}-{result1['end_line']} (target: {result1.get('line_number', 'N/A')})")
        print(f"Type: {result1.get('type', 'N/A')}, Name: {result1.get('name', 'N/A')}")
        print("\nSource code:")
        print(result1['code'][:500] + "..." if len(result1['code']) > 500 else result1['code'])

    print("\n" + "=" * 80)
    print("Test 2: Valid GitHub URL without line number")
    print("=" * 80)
    url2 = "https://github.com/dagster-io/dagster/blob/master/python_modules/dagster/dagster/_core/definitions/decorators/asset_decorator.py"
    result2 = rag.get_source_code(url2, context_lines=20)

    if result2.get("error"):
        print(f"ERROR: {result2['error']}")
    else:
        print(f"File: {result2['file_path']}")
        print(f"Lines: {result2['start_line']}-{result2['end_line']}")
        print(f"Total lines: {len(result2['code'].split(chr(10)))}")

    print("\n" + "=" * 80)
    print("Test 3: Invalid URL format")
    print("=" * 80)
    url3 = "https://github.com/invalid-url"
    result3 = rag.get_source_code(url3)

    if result3.get("error"):
        print(f"ERROR (expected): {result3['error']}")
    else:
        print("Unexpected success!")

    print("\n" + "=" * 80)
    print("Test 4: Non-existent file")
    print("=" * 80)
    url4 = "https://github.com/dagster-io/dagster/blob/master/python_modules/nonexistent/file.py#L10"
    result4 = rag.get_source_code(url4)

    if result4.get("error"):
        print(f"ERROR (expected): {result4['error']}")
    else:
        print("Unexpected success!")

    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)

if __name__ == "__main__":
    test_source_code_retrieval()
