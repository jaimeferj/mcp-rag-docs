# Enhanced RAG Query System with Self-Thinking

## Overview

Implemented a self-thinking RAG system that automatically identifies Python object references in documentation and follows them to retrieve additional context and source code.

## Components Created

### 1. Python Reference Extractor (`utils/reference_extractor.py`)
- **Purpose**: Extract Python object references from text
- **Capabilities**:
  - Identifies class methods (e.g., `AutomationCondition.eager()`)
  - Identifies module objects (e.g., `dagster.AssetSpec`)
  - Identifies decorators (e.g., `@asset`, `@op`)
  - Identifies functions and classes
  - Identifies qualified names
  - Extracts GitHub URLs from documentation
  - Prioritizes references for follow-up queries

### 2. Enhanced Query Method (`rag_server/rag_system.py`)
- **Method**: `query_enhanced(question, top_k, max_followups, tags, section_path)`
- **Self-Thinking Process**:
  1. Execute initial RAG query
  2. Analyze answer and context for Python references
  3. Prioritize top N references to follow
  4. For each reference:
     - Query RAG for specific documentation
     - Extract GitHub URLs from retrieved context
     - Retrieve source code if URLs found
  5. Compile comprehensive response with thinking process

### 3. Enhanced MCP Tool (`mcp_server/server.py`)
- **Tool Name**: `query_rag_enhanced`
- **Additional Parameters**:
  - `max_followups`: Maximum number of references to follow (default: 3)
- **Response Includes**:
  - Original answer
  - Sources with scores
  - Complete thinking process (numbered steps)
  - Followed references with their answers
  - Retrieved source code with file paths and line numbers

## Example Usage

### Question:
"How should I use asset automation to update an asset every time the upstream is updated?"

### System Behavior:
1. **Initial Query**: Retrieves documentation about asset automation
2. **Reference Extraction**: Identifies `AutomationCondition.eager()` and `AutomationCondition.data_version_changed()`
3. **Follow-up Queries**:
   - Queries for "what is AutomationCondition eager"
   - Queries for "what is AutomationCondition data_version_changed"
4. **Source Code**: Attempts to retrieve source code if GitHub URLs found
5. **Comprehensive Answer**: Provides initial answer + additional context about referenced objects

### Output:
```
Answer: Use AutomationCondition.eager()

Thinking Process:
[1] Executing initial query...
[2] Analyzing for Python references...
[3] Found 2 references: AutomationCondition.eager, AutomationCondition.data_version_changed
[3.1] Querying for 'AutomationCondition.eager'...
[3.2] Querying for 'AutomationCondition.data_version_changed'...
[4] Checking for GitHub URLs...
[5] Complete! Followed 2 references, retrieved 0 code snippets

Followed References:
- AutomationCondition.eager: [detailed explanation]
- AutomationCondition.data_version_changed: [detailed explanation]
```

## Key Features

### 1. Automatic Reference Detection
- No manual specification needed
- Intelligently identifies relevant Python objects
- Prioritizes most important references

### 2. Transparent Thinking Process
- Shows each step taken
- Explains which references were followed
- Reports what was retrieved

### 3. Source Code Integration
- Automatically retrieves source code when available
- Formats with line numbers
- Shows file path and function/class information

### 4. Configurable
- `max_followups`: Control how many references to follow
- `top_k`: Control number of chunks retrieved per query
- Same filtering as regular query (tags, section_path)

## Tools Available

### Regular Query: `query_rag`
- Fast, simple query
- No follow-ups
- Best for simple questions

### Enhanced Query: `query_rag_enhanced`
- Self-thinking with reference following
- Comprehensive answers
- Shows reasoning process
- Best for complex questions about APIs/objects

### Source Code: `get_source_code`
- Direct source code retrieval
- Requires GitHub URL
- Shows function/class definition with context

## Testing

All tests pass successfully:
- ✅ Reference extraction from text
- ✅ Enhanced query with follow-ups
- ✅ MCP tool integration
- ✅ Source code retrieval
- ✅ Complete end-to-end flow

## Files Modified/Created

### New Files:
- `utils/reference_extractor.py` - Python reference extraction
- `utils/github_parser.py` - GitHub URL parsing
- `utils/source_extractor.py` - Source code extraction
- `test_enhanced_query.py` - Enhanced query tests
- `test_mcp_enhanced.py` - MCP tool tests
- `test_with_source_code.py` - Source code tests

### Modified Files:
- `rag_server/rag_system.py` - Added `query_enhanced()` method
- `mcp_server/server.py` - Added `query_rag_enhanced` tool
- `config/settings.py` - Added Dagster repo path configuration

## Usage Recommendations

### Use `query_rag_enhanced` when:
- Asking about specific Python objects/classes/functions
- Need comprehensive understanding with examples
- Want to see related concepts automatically
- Learning about APIs and their usage

### Use `query_rag` when:
- Simple informational questions
- Speed is priority
- Don't need reference following

### Use `get_source_code` when:
- Have a specific GitHub URL
- Want to see implementation details
- Need to understand how something works internally
