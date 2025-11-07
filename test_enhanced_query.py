"""Test script for enhanced query with self-thinking."""

import asyncio
from rag_server.rag_system import RAGSystem

async def test_enhanced_query():
    """Test the enhanced query system."""
    rag = RAGSystem()

    print("=" * 80)
    print("Testing Enhanced RAG Query with Self-Thinking")
    print("=" * 80)

    question = "how should I use asset automation to update an asset everytime the upstream is updated"

    print(f"\nQuestion: {question}\n")
    print("Executing enhanced query...")
    print("-" * 80)

    try:
        result = rag.query_enhanced(question, top_k=5, max_followups=3)

        print("\n" + "=" * 80)
        print("ANSWER")
        print("=" * 80)
        print(result['answer'])

        print("\n" + "=" * 80)
        print("THINKING PROCESS")
        print("=" * 80)
        for step in result['thinking_process']:
            print(step)

        print("\n" + "=" * 80)
        print("SOURCES")
        print("=" * 80)
        for i, source in enumerate(result['sources'], 1):
            print(f"{i}. {source['section_path']}")
            print(f"   File: {source['filename']}, Chunk: {source['chunk_index']}, Score: {source['score']:.4f}")

        if result['followed_references']:
            print("\n" + "=" * 80)
            print("FOLLOWED REFERENCES")
            print("=" * 80)
            for ref, ref_data in result['followed_references'].items():
                print(f"\n### Reference: {ref}")
                print(f"Query: {ref_data['query']}")
                print(f"\nAnswer (first 300 chars):")
                print(ref_data['answer'][:300] + "..." if len(ref_data['answer']) > 300 else ref_data['answer'])
                print(f"\nSources:")
                for source in ref_data['sources']:
                    print(f"  - {source['section_path']} (score: {source['score']:.4f})")

        if result['source_code']:
            print("\n" + "=" * 80)
            print("RETRIEVED SOURCE CODE")
            print("=" * 80)
            for ref, code_data in result['source_code'].items():
                ref_display = ref if ref != '_initial_context' else 'From documentation'
                print(f"\n### {ref_display}")
                print(f"File: {code_data['file_path']}")
                print(f"Lines: {code_data['start_line']}-{code_data['end_line']}")
                if code_data.get('name') and code_data['name'] != 'unknown':
                    print(f"Type: {code_data['type']}, Name: {code_data['name']}")
                print(f"\nCode (first 500 chars):")
                print(code_data['code'][:500] + "..." if len(code_data['code']) > 500 else code_data['code'])

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total references followed: {len(result['followed_references'])}")
        print(f"Total source code snippets: {len(result['source_code'])}")
        print(f"Total thinking steps: {len(result['thinking_process'])}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_enhanced_query())
