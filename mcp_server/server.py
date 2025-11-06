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
            name="smart_query",
            description="🌟 RECOMMENDED: Intelligent query router with automatic strategy selection. Classifies query type (symbol lookup, concept explanation, how-to, etc.) and automatically chooses optimal retrieval method (code index vs documentation RAG). Returns grounded answers with full reasoning trace showing which tools were called and why. Use this as your primary entry point instead of choosing between individual tools.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask (e.g., 'show me AutomationCondition.eager', 'how do schedules work', 'example of using sensors')",
                    },
                    "expand_detail": {
                        "type": "boolean",
                        "description": "Get full implementation details instead of signatures/summaries (default: false)",
                        "default": False,
                    },
                    "repo_filter": {
                        "type": "string",
                        "description": "Optional repository filter (e.g., 'dagster', 'pyiceberg') to limit search scope",
                    },
                },
                "required": ["question"],
            },
        ),
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
            name="query_rag_enhanced",
            description="Enhanced RAG query with self-thinking: automatically identifies Python object references (e.g., AutomationCondition.eager), follows them to retrieve additional documentation and source code with appropriate detail level. Shows complete thinking process. Use this for complex questions that may involve multiple concepts or when you want comprehensive answers with automatic reference following.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask the RAG system",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of relevant chunks to retrieve per query (optional, default: 5)",
                        "default": 5,
                    },
                    "max_followups": {
                        "type": "integer",
                        "description": "Maximum number of Python references to follow up on (optional, default: 3)",
                        "default": 3,
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
        Tool(
            name="get_source_code",
            description="Retrieve the actual Python source code for a function/class from the local Dagster repository using its GitHub documentation URL. Returns the complete implementation with surrounding context. For more control over the level of detail (signature only, class outline, methods list, or specific method extraction), use get_source_code_advanced instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "github_url": {
                        "type": "string",
                        "description": "GitHub URL from Dagster documentation (e.g., 'https://github.com/dagster-io/dagster/blob/master/python_modules/dagster/dagster/_core/definitions/decorators/asset_decorator.py#L130')",
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Number of context lines before/after the target line (optional, default: 20)",
                        "default": 20,
                    },
                },
                "required": ["github_url"],
            },
        ),
        Tool(
            name="search_code_index",
            description="Search for code objects (classes, functions, methods) in the indexed codebase. Fast direct lookup without RAG. Returns file locations and metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Name or pattern to search for (e.g., 'AutomationCondition', 'eager', 'AutomationCondition.eager')",
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["exact", "prefix", "contains"],
                        "description": "Search type: 'exact' for exact name match, 'prefix' for names starting with query, 'contains' for names containing query (default: exact)",
                        "default": "exact",
                    },
                    "repo_name": {
                        "type": "string",
                        "description": "Optional repository filter (e.g., 'dagster', 'pyiceberg')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_code_by_name",
            description="Get source code directly by name using the code index. Much faster than searching through documentation. Supports multiple retrieval modes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name or qualified name of the code object (e.g., 'AutomationCondition', 'AutomationCondition.eager', 'dagster.AutomationCondition')",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["signature", "outline", "methods_list", "full"],
                        "description": "Retrieval mode: 'signature' (just def line), 'outline' (class with all method signatures), 'methods_list' (class with method names only), 'full' (complete implementation)",
                        "default": "full",
                    },
                    "repo_name": {
                        "type": "string",
                        "description": "Optional repository filter if name is ambiguous",
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Number of context lines for 'full' mode (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="list_indexed_repos",
            description="List all repositories that have been indexed in the code index.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_code_index_stats",
            description="Get statistics about the code index including total objects, objects by type, and objects by repository.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_source_code_advanced",
            description="""Advanced source code retrieval with intelligent mode selection for different levels of detail.

MODE DETAILS (choose based on user's needs):

1. 'signature' mode (~1-2 lines):
   - Returns: Just the def/class line with parameters
   - Use when: User asks "what's the signature?", "what parameters does it take?", "quick look at the definition"
   - Example output: "def eager() -> AutomationCondition:"
   - Best for: Quick reference, understanding function interface

2. 'methods_list' mode (~10-30 lines):
   - Returns: Class definition + bulleted list of all method names (no signatures, no implementations)
   - Use when: User asks "what methods does X have?", "what can I do with X?", "exploring a class"
   - Example output:
     class AutomationCondition:
         - eager
         - on_cron
         - missing
         [... 58 more methods]
   - Best for: Discovery, exploring available functionality

3. 'outline' mode (~50-200 lines):
   - Returns: Class with ALL method signatures (parameters + return types) but NO implementations (just ...)
   - Use when: User asks "what's the API of X?", "show me the class interface", "what methods and their signatures?"
   - Example output:
     class AutomationCondition:
         def eager() -> AutomationCondition: ...
         def on_cron(cron_schedule: str) -> AutomationCondition: ...
         [... all other method signatures]
   - Best for: Understanding the complete API surface without implementation details

4. 'full' mode (~100-1000+ lines):
   - Returns: Complete implementation with all code, docstrings, and logic
   - Use when: User asks "how does X work?", "show me the implementation", "I need to understand the logic"
   - Example output: [complete source code]
   - Best for: Deep dives, understanding implementation details, debugging

5. method_name parameter (~10-100 lines):
   - Returns: One specific method's complete implementation from a class
   - Use when: User asks about a specific method like "how does the eager method work?"
   - Requires: GitHub URL pointing to the class definition + method_name parameter
   - Example: method_name="eager" extracts just the eager method
   - Best for: Focused investigation of specific functionality

DECISION GUIDE:
- "What is X?" → signature mode
- "What can X do?" → methods_list mode
- "What's the API of X?" → outline mode
- "How does X work?" → full mode
- "How does X.method work?" → method_name parameter""",
            inputSchema={
                "type": "object",
                "properties": {
                    "github_url": {
                        "type": "string",
                        "description": "GitHub URL from Dagster documentation",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["signature", "outline", "methods_list", "full"],
                        "description": "Retrieval mode - see tool description for detailed explanation of each mode and when to use it. Default: 'full'",
                        "default": "full",
                    },
                    "method_name": {
                        "type": "string",
                        "description": "Extract a specific method from a class (e.g., 'eager'). The github_url must point to the class definition. Returns just that method's implementation (~10-100 lines). Use when user asks about a specific method.",
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Number of context lines before/after for 'full' mode only (default: 20). Ignored for other modes.",
                        "default": 20,
                    },
                },
                "required": ["github_url"],
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "smart_query":
            question = arguments.get("question")
            expand_detail = arguments.get("expand_detail", False)
            repo_filter = arguments.get("repo_filter")

            result = rag_system.smart_query(
                question=question,
                expand_detail=expand_detail,
                repo_filter=repo_filter,
            )

            # Format response with full reasoning trace
            classification = result["classification"]
            strategy = result["strategy"]
            tool_calls = result["tool_calls"]
            confidence = result["confidence"]
            suggestions = result["suggestions"]

            # Build classification summary
            class_summary = (
                f"**Query Type:** {classification['type']}\n"
                f"**Confidence:** {classification['confidence']:.2f}\n"
                f"**Reasoning:** {classification['reasoning']}"
            )

            if classification["symbols"]:
                class_summary += f"\n**Symbols:** {', '.join(classification['symbols'])}"
            if classification["concepts"]:
                class_summary += f"\n**Concepts:** {', '.join(classification['concepts'])}"
            if classification["libraries"]:
                class_summary += f"\n**Libraries:** {', '.join(classification['libraries'])}"

            # Build tool trace
            tool_trace = []
            for i, tc in enumerate(tool_calls, 1):
                status = "✓" if tc["success"] else "✗"
                tool_trace.append(
                    f"{i}. {status} **{tc['tool']}**\n"
                    f"   Reasoning: {tc['reasoning']}\n"
                    f"   Result: {'Found' if tc['has_result'] else 'Empty'}"
                )

            tool_trace_text = "\n".join(tool_trace) if tool_trace else "No tools called"

            # Build suggestions
            suggestions_text = ""
            if suggestions:
                suggestions_text = "\n\n**Suggestions:**\n" + "\n".join(
                    f"- {s}" for s in suggestions
                )

            # Confidence indicator
            confidence_emoji = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.4 else "🔴"

            response = f"""**Answer:**
{result['answer']}

---

**Query Analysis:**
{class_summary}

**Strategy:** {strategy['reasoning']}

**Retrieval Trace:**
{tool_trace_text}

**Confidence:** {confidence_emoji} {confidence:.2f}{suggestions_text}
"""

            return [TextContent(type="text", text=response)]

        elif name == "query_rag":
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

        elif name == "query_rag_enhanced":
            question = arguments.get("question")
            top_k = arguments.get("top_k", 5)
            max_followups = arguments.get("max_followups", 3)
            tags = arguments.get("tags")
            section_path = arguments.get("section_path")

            result = rag_system.query_enhanced(
                question, top_k, max_followups, tags=tags, section_path=section_path
            )

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

            # Format thinking process
            thinking_text = "\n".join(result['thinking_process'])

            # Format followed references
            followed_refs_text = ""
            if result['followed_references']:
                followed_refs_text = "\n\n**Followed References:**\n"
                for ref, ref_data in result['followed_references'].items():
                    followed_refs_text += f"\n### {ref}\n"
                    followed_refs_text += f"**Query:** {ref_data['query']}\n\n"
                    followed_refs_text += f"{ref_data['answer']}\n"

            # Format source code
            source_code_text = ""
            if result['source_code']:
                source_code_text = "\n\n**Retrieved Source Code:**\n"
                for ref, code_data in result['source_code'].items():
                    ref_display = ref if ref != '_initial_context' else 'From documentation'
                    source_code_text += f"\n### {ref_display}\n"
                    source_code_text += f"**File:** {code_data['file_path']}\n"
                    source_code_text += f"**Lines:** {code_data['start_line']}-{code_data['end_line']}\n"
                    if code_data.get('name') and code_data['name'] != 'unknown':
                        source_code_text += f"**Type:** {code_data['type']}, **Name:** {code_data['name']}\n"
                    source_code_text += f"\n```python\n{code_data['code']}\n```\n"

            response = f"""**Answer:**
{result['answer']}

**Sources:**
{sources_text}

**Context chunks used:** {len(result['context_used'])}{filters_text}

**Thinking Process:**
```
{thinking_text}
```
{followed_refs_text}{source_code_text}"""

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

        elif name == "get_source_code":
            github_url = arguments.get("github_url")
            context_lines = arguments.get("context_lines", 20)

            result = rag_system.get_source_code(github_url, context_lines)

            if result.get("error"):
                return [TextContent(type="text", text=f"**Error:** {result['error']}")]

            # Format the source code with line numbers
            source_lines = result['code'].split('\n')
            start_line = result['start_line']
            formatted_lines = []
            for i, line in enumerate(source_lines):
                line_num = start_line + i
                formatted_lines.append(f"{line_num:4d} | {line}")

            formatted_source = '\n'.join(formatted_lines)

            # Build response with available metadata
            name_info = f" ({result['type']}: {result['name']})" if result.get('name') else ""
            target_line = result.get('line_number', 'N/A')

            response = f"""**Source Code Retrieved**

**File:** {result['file_path']}{name_info}
**Lines:** {result['start_line']}-{result['end_line']} (target: {target_line})
**GitHub URL:** {result.get('github_url', 'N/A')}

```python
{formatted_source}
```
"""

            return [TextContent(type="text", text=response)]

        elif name == "search_code_index":
            query = arguments.get("query")
            search_type = arguments.get("search_type", "exact")
            repo_name = arguments.get("repo_name")
            limit = arguments.get("limit", 10)

            results = rag_system.search_code(
                query=query,
                repo_name=repo_name,
                search_type=search_type,
                limit=limit,
            )

            if not results:
                return [TextContent(type="text", text=f"No code objects found matching '{query}'.")]

            # Format results
            results_text = []
            for i, obj in enumerate(results, 1):
                parent = f" (in {obj['parent_class']})" if obj['parent_class'] else ""
                doc = f"\n  {obj['docstring']}" if obj['docstring'] else ""
                results_text.append(
                    f"{i}. **{obj['qualified_name']}** [{obj['type']}]{parent}\n"
                    f"   File: {obj['file_path']}:{obj['line_number']}{doc}"
                )

            response = f"""**Code Index Search Results**

Query: {query}
Search type: {search_type}
Found: {len(results)} matches

{chr(10).join(results_text)}
"""

            return [TextContent(type="text", text=response)]

        elif name == "get_code_by_name":
            name_arg = arguments.get("name")
            mode = arguments.get("mode", "full")
            repo_name = arguments.get("repo_name")
            context_lines = arguments.get("context_lines", 20)

            result = rag_system.get_source_code_from_index(
                name=name_arg,
                repo_name=repo_name,
                context_lines=context_lines,
                mode=mode,
            )

            if not result:
                return [
                    TextContent(
                        type="text",
                        text=f"**Error:** Code object '{name_arg}' not found in index.",
                    )
                ]

            if result.get("error"):
                return [TextContent(type="text", text=f"**Error:** {result['error']}")]

            # Format the source code
            code = result['code']
            if mode == 'full' or '\n' in code:
                source_lines = code.split('\n')
                start_line = result['start_line']
                formatted_lines = []
                for i, line in enumerate(source_lines):
                    line_num = start_line + i
                    formatted_lines.append(f"{line_num:4d} | {line}")
                formatted_source = '\n'.join(formatted_lines)
            else:
                formatted_source = code

            # Build response
            mode_label = {
                'signature': 'Signature',
                'outline': 'Class Outline',
                'methods_list': 'Methods List',
                'full': 'Full Implementation',
            }.get(mode, mode)

            name_info = f" ({result['type']}: {result.get('name', 'unknown')})" if result.get('name') else ""
            qualified = result.get('qualified_name', name_arg)

            response = f"""**Code Retrieved from Index ({mode_label})**

**Object:** {qualified}{name_info}
**Repository:** {result.get('repo_name', 'unknown')}
**File:** {result['file_path']}
**Lines:** {result['start_line']}-{result['end_line']}

```python
{formatted_source}
```
"""

            return [TextContent(type="text", text=response)]

        elif name == "list_indexed_repos":
            if not rag_system.code_index:
                return [TextContent(type="text", text="Code index is not enabled.")]

            repos = rag_system.code_index.list_repos()

            if not repos:
                return [
                    TextContent(
                        type="text",
                        text="No repositories have been indexed yet. Use build_code_index.py to index a repository.",
                    )
                ]

            response = f"""**Indexed Repositories**

Total: {len(repos)}

{chr(10).join(f'- {repo}' for repo in repos)}

To index a new repository:
```bash
python build_code_index.py --repo <name> --path /path/to/repo
```
"""

            return [TextContent(type="text", text=response)]

        elif name == "get_code_index_stats":
            if not rag_system.code_index:
                return [TextContent(type="text", text="Code index is not enabled.")]

            stats = rag_system.code_index.get_stats()

            type_counts_text = "\n".join(
                [f"  - {obj_type}: {count}" for obj_type, count in stats['type_counts'].items()]
            )

            repo_counts_text = "\n".join(
                [f"  - {repo}: {count}" for repo, count in stats['repo_counts'].items()]
            )

            response = f"""**Code Index Statistics**

**Total Objects:** {stats['total_objects']}

**Objects by Type:**
{type_counts_text}

**Objects by Repository:**
{repo_counts_text}
"""

            return [TextContent(type="text", text=response)]

        elif name == "get_source_code_advanced":
            github_url = arguments.get("github_url")
            mode = arguments.get("mode", "full")
            method_name = arguments.get("method_name")
            context_lines = arguments.get("context_lines", 20)

            result = rag_system.get_source_code(
                github_url, context_lines, mode=mode, method_name=method_name
            )

            if result.get("error"):
                return [TextContent(type="text", text=f"**Error:** {result['error']}")]

            # Build mode-specific response
            mode_label = {
                'signature': 'Signature',
                'outline': 'Class Outline',
                'methods_list': 'Methods List',
                'full': 'Full Implementation',
            }.get(mode, mode)

            # Format the source code
            code = result['code']

            # Add line numbers for full mode or if we have multi-line code
            if mode == 'full' or '\n' in code:
                source_lines = code.split('\n')
                start_line = result['start_line']
                formatted_lines = []
                for i, line in enumerate(source_lines):
                    line_num = start_line + i
                    formatted_lines.append(f"{line_num:4d} | {line}")
                formatted_source = '\n'.join(formatted_lines)
            else:
                formatted_source = code

            # Build response
            name_info = ""
            if result.get('name'):
                name_info = f" ({result['type']}: {result['name']})"

            method_info = ""
            if method_name:
                method_info = f"\n**Method:** {method_name}"

            method_count_info = ""
            if result.get('method_count'):
                method_count_info = f"\n**Method Count:** {result['method_count']}"

            response = f"""**Source Code Retrieved ({mode_label})**

**File:** {result['file_path']}{name_info}
**Lines:** {result['start_line']}-{result['end_line']}{method_info}{method_count_info}
**GitHub URL:** {result.get('github_url', 'N/A')}

```python
{formatted_source}
```
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
