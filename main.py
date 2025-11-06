"""Main entry point for the RAG system."""

import sys


def main():
    """Main CLI for the RAG system."""
    print("RAG Server with MCP Integration")
    print("=" * 50)
    print("\nAvailable commands:")
    print("  1. Start FastAPI server:  python -m rag_server.server")
    print("  2. Start MCP server:      python -m mcp_server.server")
    print("\nFor more information, see README.md")
    print("\nQuick setup:")
    print("  1. Copy .env.example to .env")
    print("  2. Add your GOOGLE_API_KEY to .env")
    print("  3. Run one of the servers above")
    print("\nAPI Documentation: http://localhost:8000/docs (when FastAPI server is running)")


if __name__ == "__main__":
    main()
