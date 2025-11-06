# MCP Server Setup for Claude

## Overview
This guide shows how to configure Claude Desktop or Claude Code to use the RAG MCP server for querying Dagster documentation.

## Configuration

### For Claude Desktop

Add this configuration to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "rag-dagster-docs": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/ubuntu/work/rag",
        "run",
        "python",
        "-m",
        "mcp_server.server"
      ]
    }
  }
}
```

**Note:** The API key is read automatically from `/home/ubuntu/work/rag/.env` - no need to put it in the config!

### For Claude Code (Current Environment)

Since you're already in Claude Code, you can add the MCP server configuration:

1. **Option A: Using Claude Code Settings**
   - Run the command: `/mcp add`
   - Or manually edit the MCP configuration in Claude Code settings

2. **Option B: Direct MCP Configuration**

   Add to Claude Code's MCP servers configuration:

   ```json
   {
     "name": "rag-dagster-docs",
     "command": "uv",
     "args": [
       "--directory",
       "/home/ubuntu/work/rag",
       "run",
       "python",
       "-m",
       "mcp_server.server"
     ]
   }
   ```

**Security Note:** The MCP server automatically loads the Google API key from `/home/ubuntu/work/rag/.env`. You don't need to (and shouldn't) include API keys in the MCP configuration JSON.

## Available MCP Tools

Once configured, Claude will have access to these tools:

### 1. `query_rag` - Query the documentation
```
Query the RAG system with a question about Dagster.
```

**Parameters:**
- `question` (required): Your question about Dagster
- `top_k` (optional): Number of relevant chunks (default: 5)
- `tags` (optional): Filter by tags like `["dagster", "docs"]`
- `section_path` (optional): Filter by section like `"getting-started > Concepts"`

**Example usage in Claude:**
```
Use the query_rag tool to ask: "How do I define assets in Dagster?"
with tags: ["dagster"]
```

### 2. `add_document` - Add new documentation
```
Add a markdown or text document to the RAG system.
```

### 3. `list_documents` - List all documents
```
See all documents in the system, optionally filtered by tags.
```

### 4. `delete_document` - Remove a document
```
Delete a document by its ID.
```

### 5. `get_tags` - List available tags
```
Get all unique tags across all documents.
```

### 6. `get_document_structure` - View table of contents
```
Get the hierarchical section structure of a specific document.
```

### 7. `get_rag_stats` - System statistics
```
Get statistics about the RAG system (documents, chunks, etc.).
```

## Querying Only Dagster Docs

To ensure Claude only searches Dagster documentation, use the `tags` parameter:

```json
{
  "question": "How do I create a schedule in Dagster?",
  "tags": ["dagster", "docs"]
}
```

All Dagster docs were ingested with tags `["dagster", "docs"]`, so filtering by these tags ensures you only get Dagster-specific results.

## Testing the Setup

After configuration, restart Claude Desktop/Code and try:

1. Check available tools: Claude should show the MCP tools in its tool list
2. Test a query: Ask Claude to "Use query_rag to find information about Dagster assets with tags: dagster, docs"
3. Verify results include hierarchical paths like `getting-started > Concepts > Asset`

## Environment Variables

The MCP server reads configuration from `/home/ubuntu/work/rag/.env`. This file should contain:

```bash
GOOGLE_API_KEY=your-actual-api-key
```

**Current status:** ✅ Already configured and working

**Security best practice:**
- ✅ API keys in `.env` file (gitignored)
- ✅ MCP config has NO hardcoded secrets
- ✅ Settings automatically load from `.env` via Pydantic

To verify your `.env` is set up correctly:
```bash
cd /home/ubuntu/work/rag
grep GOOGLE_API_KEY .env
```

## Troubleshooting

### MCP Server Won't Start
- Check that the Google API key is set
- Verify the path `/home/ubuntu/work/rag` is correct
- Check logs in Claude Desktop/Code

### No Results Returned
- Verify documents were ingested: Use `get_rag_stats` tool
- Check tags match: Use `get_tags` tool to see available tags
- Try without tag filtering first

### Wrong Documentation
- Always include `"tags": ["dagster"]` in your queries
- Use `section_path` to narrow down to specific sections like `"getting-started"`
