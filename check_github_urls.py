"""Check if we have GitHub URLs in our documentation."""

from rag_server.rag_system import RAGSystem

def check_for_urls():
    """Check if any chunks contain GitHub URLs."""
    rag = RAGSystem()

    # Do a broad search that should match many documents
    result = rag.query("asset decorator", top_k=20)

    print("Checking for GitHub URLs in retrieved chunks...")
    print("=" * 80)

    found_urls = False
    for i, chunk in enumerate(result['context_used'], 1):
        if 'github.com' in chunk.lower():
            found_urls = True
            print(f"\nChunk {i} contains GitHub URL:")
            print("-" * 80)
            # Find and print the URL
            lines = chunk.split('\n')
            for line in lines:
                if 'github.com' in line.lower():
                    print(line.strip())

    if not found_urls:
        print("\nNo GitHub URLs found in any of the retrieved chunks.")
        print("\nThis suggests the documentation might not include GitHub URLs in the markdown,")
        print("or they were filtered out during processing.")

    print("\n" + "=" * 80)
    print("Let's check a specific API reference document...")
    print("=" * 80)

    # Try searching in API reference specifically
    result2 = rag.query("AssetSpec API reference", top_k=10)

    found_urls = False
    for i, chunk in enumerate(result2['context_used'], 1):
        if 'github.com' in chunk.lower() or 'source code' in chunk.lower():
            found_urls = True
            print(f"\nChunk {i}:")
            print("-" * 80)
            print(chunk[:500] + "..." if len(chunk) > 500 else chunk)

    if not found_urls:
        print("\nNo GitHub URLs or 'source code' references found.")

if __name__ == "__main__":
    check_for_urls()
