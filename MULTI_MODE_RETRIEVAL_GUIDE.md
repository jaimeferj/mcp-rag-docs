# Multi-Mode Code Retrieval System

## Overview

The intelligent code retrieval system now supports multiple modes for retrieving Python source code, allowing you to get exactly the information you need without overwhelming detail.

## Available Modes

### 1. **Signature Mode** (`mode='signature'`)
Retrieves only the function/class definition line.

**Use Case:** Quick reference to see function signature, parameters, and return type.

**Example:**
```python
get_source_code_advanced(
    github_url="https://github.com/dagster-io/dagster/.../automation_condition.py#L63",
    mode="signature"
)
```

**Output:**
```python
class AutomationCondition(ABC, Generic[T_EntityKey]):
```

### 2. **Methods List Mode** (`mode='methods_list'`)
For classes: shows class name with a list of all method names.

**Use Case:** Explore what methods a class has without seeing implementation details.

**Example:**
```python
get_source_code_advanced(
    github_url="https://github.com/dagster-io/dagster/.../automation_condition.py#L63",
    mode="methods_list"
)
```

**Output:**
```python
class AutomationCondition(ABC, Generic[T_EntityKey]):
    - requires_cursor
    - children
    - eager
    - on_cron
    - missing
    [... 56 more methods]
```

### 3. **Outline Mode** (`mode='outline'`)
For classes: shows class with all method signatures (no implementation).

**Use Case:** Understand the API surface of a class - what methods exist and their signatures.

**Example:**
```python
get_source_code_advanced(
    github_url="https://github.com/dagster-io/dagster/.../automation_condition.py#L63",
    mode="outline"
)
```

**Output:**
```python
class AutomationCondition(ABC, Generic[T_EntityKey]):
    """An AutomationCondition represents a condition..."""
    def requires_cursor(self) -> bool: ...
    def children(self) -> Sequence["AutomationCondition"]: ...
    def eager() -> "AndAutomationCondition": ...
    def on_cron(cron_schedule: str) -> "AutomationCondition": ...
    [... 57 more method signatures]
```

### 4. **Full Mode** (`mode='full'`, default)
Retrieves complete implementation with all code.

**Use Case:** Deep dive into implementation details.

**Example:**
```python
get_source_code_advanced(
    github_url="https://github.com/dagster-io/dagster/.../automation_condition.py#L63",
    mode="full",
    context_lines=30
)
```

**Output:** Complete class definition with all methods implemented (100+ lines)

### 5. **Specific Method Extraction** (`method_name='method_name'`)
Extracts a single method from a class.

**Use Case:** Focus on one specific method implementation from a large class.

**Example:**
```python
get_source_code_advanced(
    github_url="https://github.com/dagster-io/dagster/.../automation_condition.py#L63",
    method_name="eager"
)
```

**Output:**
```python
def eager() -> "AndAutomationCondition":
    """Returns an AutomationCondition which will cause a target to be
    executed if any of its dependencies update..."""
    return (
        AutomationCondition.in_latest_time_window()
        & (
            AutomationCondition.newly_missing()
            | AutomationCondition.any_deps_updated()
        ).since_last_handled()
        & ~AutomationCondition.any_deps_missing()
        & ~AutomationCondition.any_deps_in_progress()
        & ~AutomationCondition.in_progress()
    ).with_label("eager")
```

## MCP Tool: `get_source_code_advanced`

### Parameters

- **`github_url`** (required): GitHub URL from documentation
- **`mode`** (optional): One of `'signature'`, `'outline'`, `'methods_list'`, `'full'` (default: `'full'`)
- **`method_name`** (optional): Specific method to extract from a class
- **`context_lines`** (optional): Number of context lines for `'full'` mode (default: 20)

### Usage Examples

#### Example 1: Quick Signature Lookup
```
Query: "What's the signature of the eager method?"

MCP Call:
get_source_code_advanced(
    github_url="...",
    mode="signature"
)
```

#### Example 2: Explore Class API
```
Query: "What methods does AutomationCondition have?"

MCP Call:
get_source_code_advanced(
    github_url="...",
    mode="methods_list"
)
```

#### Example 3: Understand Class Structure
```
Query: "Show me the API of AutomationCondition"

MCP Call:
get_source_code_advanced(
    github_url="...",
    mode="outline"
)
```

#### Example 4: Deep Dive into Method
```
Query: "How is the eager method implemented?"

MCP Call:
get_source_code_advanced(
    github_url="...",
    method_name="eager"
)
```

## Benefits

### 1. **Token Efficiency**
- Signature mode: ~1 line
- Methods list: ~10-20 lines
- Outline: ~50-100 lines
- Full: 100-1000+ lines

Choose the appropriate mode to minimize token usage.

### 2. **Progressive Disclosure**
Start with high-level views (methods_list, outline) and drill down to specific implementations as needed.

### 3. **Better UX**
Users aren't overwhelmed with hundreds of lines of code when they just want to see available methods.

### 4. **Intelligent Following**
The enhanced query system can now make smarter choices about what level of detail to retrieve.

## Technical Implementation

### New Methods in `SourceCodeExtractor`:
- `extract_signature()` - Single line extraction
- `extract_class_outline()` - Class with method signatures
- `extract_class_methods_list()` - Class with method names
- `extract_class_method()` - Specific method from class

### Updated RAG System:
- `get_source_code()` now accepts `mode` and `method_name` parameters
- Automatically routes to appropriate extractor based on mode

### AST-Based Analysis:
All modes use Python's AST parser for intelligent extraction:
- Accurate method detection
- Proper handling of decorators
- Multi-line signature support
- Docstring extraction

## Test Results

All modes tested successfully:

✅ Signature mode - Extracts class/function signature
✅ Methods list mode - Lists all 61 methods in AutomationCondition
✅ Outline mode - Shows all method signatures with docstrings
✅ Full mode - Complete implementation (769 lines)
✅ Method extraction - Successfully extracted `eager` method (19 lines)

## Future Enhancements

Potential additions:
- Auto-detect optimal mode based on context
- Support for extracting multiple specific methods
- Diff mode to compare method implementations
- Dependency graph visualization from class relationships
