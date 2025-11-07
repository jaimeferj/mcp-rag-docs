"""Test enhanced query with a question that should include source code."""

import asyncio
from rag_server.rag_system import RAGSystem

async def test_with_source():
    """Test with API reference question that should have GitHub URLs."""
    rag = RAGSystem()

    print("=" * 80)
    print("Testing Enhanced Query with Source Code Retrieval")
    print("=" * 80)

    # Try a query about a specific API that should have GitHub links
    question = "what is the @asset decorator and how does it work"

    print(f"\nQuestion: {question}\n")
    print("Executing enhanced query...")
    print("-" * 80)

    try:
        result = rag.query_enhanced(question, top_k=5, max_followups=2)

        print("\nTHINKING PROCESS:")
        print("-" * 80)
        for step in result['thinking_process']:
            print(step)

        print("\n\nANSWER:")
        print("-" * 80)
        print(result['answer'][:500] + "..." if len(result['answer']) > 500 else result['answer'])

        if result['followed_references']:
            print("\n\nFOLLOWED REFERENCES:")
            print("-" * 80)
            for ref, ref_data in result['followed_references'].items():
                print(f"\n{ref}:")
                print(f"  Query: {ref_data['query']}")
                print(f"  Answer: {ref_data['answer'][:200]}...")

        if result['source_code']:
            print("\n\nSOURCE CODE RETRIEVED:")
            print("=" * 80)
            for ref, code_data in result['source_code'].items():
                ref_display = ref if ref != '_initial_context' else 'From documentation'
                print(f"\n### {ref_display}")
                print(f"File: {code_data['file_path']}")
                print(f"Lines: {code_data['start_line']}-{code_data['end_line']}")
                if code_data.get('name') and code_data['name'] != 'unknown':
                    print(f"Type: {code_data['type']}, Name: {code_data['name']}")
                print(f"\nCode:")
                # Show line numbers
                lines = code_data['code'].split('\n')
                for i, line in enumerate(lines[:30], code_data['start_line']):  # Show first 30 lines
                    print(f"{i:4d} | {line}")
                if len(lines) > 30:
                    print(f"     ... ({len(lines) - 30} more lines)")
        else:
            print("\n\nNo source code retrieved.")

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"References followed: {len(result['followed_references'])}")
        print(f"Source code snippets: {len(result['source_code'])}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_with_source())
