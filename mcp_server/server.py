"""MCP server for RAG system integration."""

import asyncio
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from rag_server.rag_system import RAGSystem

# Initialize RAG system
rag_system = RAGSystem()

# Create MCP server
mcp_server = Server("rag-mcp-server")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="query_rag",
            description="Query the RAG system with a question. Optionally filter by tags and/or section path. The system will retrieve relevant context and generate an answer using Google AI Studio.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask the RAG system",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of relevant chunks to retrieve (optional, default: 5)",
                        "default": 5,
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags to filter documents by (e.g., ['dagster', 'python'])",
                    },
                    "section_path": {
                        "type": "string",
                        "description": "Optional section path to filter by (e.g., 'Installation > Prerequisites')",
                    },
                },
                "required": ["question"],
            },
        ),
        Tool(
            name="add_document",
            description="Add a text or markdown document to the RAG system. Supports hierarchical chunking for markdown. Optionally add tags and base_path for organization.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the document file (.txt or .md)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for categorization (e.g., ['dagster', 'api', 'docs'])",
                    },
                    "base_path": {
                        "type": "string",
                        "description": "Optional base path to extract relative file structure from (e.g., '~/dagster/docs/docs' extracts 'getting-started/quickstart' from '~/dagster/docs/docs/getting-started/quickstart.md')",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="list_documents",
            description="List all documents stored in the RAG system. Optionally filter by tags.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags to filter by",
                    },
                },
            },
        ),
        Tool(
            name="delete_document",
            description="Delete a document from the RAG system by its document ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "The document ID to delete",
                    },
                },
                "required": ["doc_id"],
            },
        ),
        Tool(
            name="get_tags",
            description="Get all unique tags across all documents in the RAG system.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_document_structure",
            description="Get the hierarchical section structure of a specific document (table of contents).",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "The document ID to get structure for",
                    },
                },
                "required": ["doc_id"],
            },
        ),
        Tool(
            name="get_rag_stats",
            description="Get statistics about the RAG system, including number of documents and chunks.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "query_rag":
            question = arguments.get("question")
            top_k = arguments.get("top_k", 5)
            tags = arguments.get("tags")
            section_path = arguments.get("section_path")

            result = rag_system.query(question, top_k, tags=tags, section_path=section_path)

            # Format response with section information
            sources_text = "\n".join(
                [
                    f"- {source['section_path']} ({source['filename']}, chunk {source['chunk_index']}, score: {source['score']:.4f})"
                    for source in result["sources"]
                ]
            )

            filters_text = ""
            if tags:
                filters_text += f"\n**Filtered by tags:** {', '.join(tags)}"
            if section_path:
                filters_text += f"\n**Filtered by section:** {section_path}"

            response = f"""**Answer:**
{result['answer']}

**Sources:**
{sources_text}

**Context chunks used:** {len(result['context_used'])}{filters_text}
"""

            return [TextContent(type="text", text=response)]

        elif name == "add_document":
            file_path = arguments.get("file_path")
            tags = arguments.get("tags", [])
            base_path = arguments.get("base_path")
            path = Path(file_path).expanduser()  # Expand ~ to home directory

            if not path.exists():
                return [
                    TextContent(
                        type="text", text=f"Error: File not found at {file_path}"
                    )
                ]

            # Expand base_path if provided
            base_path_val = Path(base_path).expanduser() if base_path else None

            result = await rag_system.add_document(path, tags=tags, base_path=base_path_val)

            tags_text = f"\n- Tags: {', '.join(result['tags'])}" if result['tags'] else ""

            response = f"""**Document Added Successfully**

- Document ID: {result['doc_id']}
- Filename: {result['filename']}
- File Type: {result['file_type']}{tags_text}
- Number of chunks: {result['num_chunks']}
"""

            return [TextContent(type="text", text=response)]

        elif name == "list_documents":
            tags = arguments.get("tags")
            documents = rag_system.list_documents(tags=tags)

            if not documents:
                return [TextContent(type="text", text="No documents found in the RAG system.")]

            doc_list = "\n".join(
                [
                    f"- {doc['filename']} (ID: {doc['doc_id']}, Type: {doc['file_type']}, Tags: {', '.join(doc['tags']) if doc['tags'] else 'none'})"
                    for doc in documents
                ]
            )

            filter_text = f" (filtered by tags: {', '.join(tags)})" if tags else ""

            response = f"""**Documents in RAG System ({len(documents)} total{filter_text}):**

{doc_list}
"""

            return [TextContent(type="text", text=response)]

        elif name == "delete_document":
            doc_id = arguments.get("doc_id")
            chunks_deleted = rag_system.delete_document(doc_id)

            if chunks_deleted == 0:
                return [
                    TextContent(
                        type="text",
                        text=f"Error: Document with ID {doc_id} not found.",
                    )
                ]

            response = f"""**Document Deleted Successfully**

- Document ID: {doc_id}
- Chunks deleted: {chunks_deleted}
"""

            return [TextContent(type="text", text=response)]

        elif name == "get_tags":
            tags = rag_system.get_tags()

            if not tags:
                return [TextContent(type="text", text="No tags found in the RAG system.")]

            tags_text = "\n".join([f"- {tag}" for tag in tags])

            response = f"""**Tags in RAG System ({len(tags)} total):**

{tags_text}
"""

            return [TextContent(type="text", text=response)]

        elif name == "get_document_structure":
            doc_id = arguments.get("doc_id")
            sections = rag_system.get_document_sections(doc_id)

            if not sections:
                return [
                    TextContent(
                        type="text",
                        text=f"No structure found for document {doc_id}. It may not exist or have no hierarchical structure.",
                    )
                ]

            sections_text = "\n".join(
                [
                    f"{'  ' * (section['section_level'] - 1)}- {section['section_path']} ({section['chunk_count']} chunks)"
                    for section in sections
                ]
            )

            response = f"""**Document Structure (Table of Contents)**

Document ID: {doc_id}
Total sections: {len(sections)}

{sections_text}
"""

            return [TextContent(type="text", text=response)]

        elif name == "get_rag_stats":
            stats = rag_system.get_stats()

            response = f"""**RAG System Statistics**

- Total documents: {stats['total_documents']}
- Total chunks: {stats['total_chunks']}
- Collection name: {stats['collection_name']}
"""

            return [TextContent(type="text", text=response)]

        else:
            return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error executing tool: {str(e)}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
