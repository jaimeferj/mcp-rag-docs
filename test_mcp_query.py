"""Test script to query the RAG system directly."""

import asyncio
from rag_server.rag_system import RAGSystem

async def test_query():
    """Test querying the RAG system."""
    rag = RAGSystem()

    print("=" * 80)
    print("Testing RAG System Query")
    print("=" * 80)

    question = "how should I use asset automation to update an asset everytime the upstream is updated"

    print(f"\nQuestion: {question}\n")
    print("Querying RAG system...")
    print("-" * 80)

    try:
        result = rag.query(question, top_k=5)

        print(f"\nAnswer:\n{result['answer']}\n")

        print("Sources:")
        for i, source in enumerate(result['sources'], 1):
            print(f"{i}. {source['section_path']}")
            print(f"   File: {source['filename']}")
            print(f"   Chunk: {source['chunk_index']}, Score: {source['score']:.4f}")

        print(f"\nTotal context chunks used: {len(result['context_used'])}")

        # If sources mention GitHub URLs, let's test source code retrieval
        print("\n" + "=" * 80)
        print("Testing Source Code Retrieval")
        print("=" * 80)

        # Try to find a GitHub URL in the context
        github_urls = []
        for context in result['context_used']:
            # Look for GitHub URLs in the context
            import re
            urls = re.findall(
                r'https://github\.com/dagster-io/dagster/blob/master/python_modules/[^\s\)]+',
                context
            )
            github_urls.extend(urls)

        if github_urls:
            print(f"\nFound {len(github_urls)} GitHub URL(s) in the context")
            # Test with the first URL
            test_url = github_urls[0]
            print(f"\nTesting source code retrieval with:\n{test_url}\n")

            source_result = rag.get_source_code(test_url, context_lines=15)

            if source_result.get('error'):
                print(f"Error: {source_result['error']}")
            else:
                print(f"File: {source_result['file_path']}")
                print(f"Lines: {source_result['start_line']}-{source_result['end_line']}")
                if source_result.get('name'):
                    print(f"Type: {source_result['type']}, Name: {source_result['name']}")
                print(f"\nSource code preview:")
                lines = source_result['code'].split('\n')[:20]  # First 20 lines
                for i, line in enumerate(lines, source_result['start_line']):
                    print(f"{i:4d} | {line}")
                if len(source_result['code'].split('\n')) > 20:
                    print("...")
        else:
            print("\nNo GitHub URLs found in the context to test source code retrieval")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_query())
