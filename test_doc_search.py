"""Test documentation search."""

import asyncio
from rag_server.rag_system import RAGSystem


def main():
    rag = RAGSystem()

    # Test documentation query
    result = rag.query('what are automation conditions in Dagster?', top_k=5)

    print('Query Results:')
    print('Keys in result:', list(result.keys()))
    print(f'Confidence: {result.get("confidence", "N/A")}')
    print(f'Sources: {len(result.get("sources", []))}')
    print()

    if result['sources']:
        print('Top sources:')
        for i, src in enumerate(result['sources'][:5], 1):
            print(f'{i}. {src.get("filename", "unknown")}')
            print(f'   Tags: {src.get("tags", [])}')
            print(f'   Preview: {src.get("text", "")[:150]}...')
            print()

    print('Answer preview:')
    print(result['answer'][:500])


if __name__ == '__main__':
    main()
