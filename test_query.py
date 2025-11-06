"""Quick test script to verify hierarchical structure in queries."""

from rag_server.rag_system import RAGSystem

# Initialize RAG system
rag = RAGSystem()

# Query about quickstart prerequisites
print("=" * 60)
print("Testing hierarchical structure in RAG queries")
print("=" * 60)
print()

# Test query
question = "What is an asset in Dagster?"
print(f"Question: {question}")
print()

result = rag.query(question, top_k=5, tags=["dagster"])

print("Answer:")
print(result["answer"])
print()

print("Sources with hierarchical paths:")
for source in result["sources"]:
    print(f"  - {source['section_path']}")
    print(f"    (from {source['filename']}, chunk {source['chunk_index']}, score: {source['score']:.4f})")
    print()
