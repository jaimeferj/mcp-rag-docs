"""Simple test script to verify the RAG system setup."""

import asyncio
from pathlib import Path

from config.settings import settings


async def test_setup():
    """Test the RAG system setup."""
    print("RAG System Setup Test")
    print("=" * 50)
    print()

    # Test 1: Check environment variables
    print("1. Checking environment variables...")
    try:
        api_key = settings.google_api_key
        if api_key and api_key != "your_api_key_here":
            print("   ✓ GOOGLE_API_KEY is set")
        else:
            print("   ✗ GOOGLE_API_KEY is not set or using default value")
            print("   Please set your Google API key in .env file")
            return False
    except Exception as e:
        print(f"   ✗ Error loading settings: {e}")
        return False

    # Test 2: Check dependencies
    print("\n2. Checking dependencies...")
    try:
        import fastapi
        import qdrant_client
        import google.generativeai
        import mcp
        print("   ✓ All required packages are installed")
    except ImportError as e:
        print(f"   ✗ Missing dependency: {e}")
        print("   Run: pip install -e .")
        return False

    # Test 3: Test Google AI connection
    print("\n3. Testing Google AI Studio connection...")
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.google_api_key)

        # Try to generate a simple embedding
        result = genai.embed_content(
            model=f"models/{settings.embedding_model}",
            content="test",
            task_type="retrieval_document",
        )

        if result and "embedding" in result:
            print("   ✓ Successfully connected to Google AI Studio")
            print(f"   ✓ Embedding model ({settings.embedding_model}) is working")
        else:
            print("   ✗ Unexpected response from Google AI Studio")
            return False

    except Exception as e:
        print(f"   ✗ Error connecting to Google AI Studio: {e}")
        print("   Check your API key and internet connection")
        return False

    # Test 4: Test Qdrant initialization
    print("\n4. Testing Qdrant vector database...")
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(path=":memory:")  # Use in-memory for testing
        print("   ✓ Qdrant client initialized successfully")
    except Exception as e:
        print(f"   ✗ Error initializing Qdrant: {e}")
        return False

    # Test 5: Check example document
    print("\n5. Checking example document...")
    example_path = Path("example_document.md")
    if example_path.exists():
        print("   ✓ Example document found")
    else:
        print("   ⚠ Example document not found (optional)")

    # All tests passed
    print("\n" + "=" * 50)
    print("✓ All tests passed! Your setup is ready.")
    print("\nNext steps:")
    print("  1. Start the FastAPI server: python -m rag_server.server")
    print("  2. Or start the MCP server: python -m mcp_server.server")
    print("  3. Upload documents and start querying!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_setup())
    exit(0 if success else 1)
