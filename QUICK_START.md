# Quick Start Guide - Secure MCP Setup

## TL;DR - Add to Claude Code

Copy this configuration (no API keys needed!):

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

## How It Works Securely

1. **API Key Location:** `/home/ubuntu/work/rag/.env` (gitignored ✅)
2. **MCP Config:** No secrets, just command to run
3. **Auto-Loading:** Settings.py loads `.env` automatically via Pydantic

## Query Only Dagster Docs

Always use tags to filter for Dagster documentation:

```
Use query_rag to ask "How do I define assets?" with tags: ["dagster"]
```

## Available Tags

- `dagster` - Main Dagster documentation (use this!)
- `docs` - General documentation tag
- `getting-started` - Getting started section
- `tutorial` - Tutorial content

## System Status

✅ **543 documents** ingested
✅ **4,566 chunks** ready to search
✅ **API key** securely in `.env`
✅ **Hierarchical paths** preserved (e.g., `getting-started > Concepts > Asset`)

## MCP Tools

| Tool | Use |
|------|-----|
| `query_rag` | Search docs with tags: ["dagster"] |
| `get_rag_stats` | Check system status |
| `get_tags` | List available tags |
| `list_documents` | View all documents |

## Security Checklist

- ✅ `.env` file in `.gitignore`
- ✅ No API keys in MCP config JSON
- ✅ Settings auto-load from `.env`
- ✅ Google API key working

## Test It

After adding to Claude Code MCP settings, try:

```
Use get_rag_stats to show system information
```

Should return: 543 documents, 4566 chunks

Then:

```
Use query_rag with question "What is an asset?" and tags: ["dagster"]
```

Should return: Dagster asset definition with hierarchical source paths.
