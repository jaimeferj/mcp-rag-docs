

# Query Routing Guide

## Overview

The **Smart Query System** uses a tiered decision policy to automatically route queries to the optimal retrieval strategy. Instead of choosing between tools manually, the system:

1. **Classifies** the query type
2. **Routes** to appropriate retrieval methods
3. **Executes** with progressive detail levels
4. **Synthesizes** grounded answers with evidence

## Query Types

### 1. EXACT_SYMBOL
**Pattern:** "show me X.y", "what is X.y", "definition of X.y"

**Strategy:**
- Primary: Code index lookup (exact match)
- Fallback: Fuzzy search if not found
- Detail: Start with signature, expand if requested

**Example:**
```
Q: "show me AutomationCondition.eager"

Classification: EXACT_SYMBOL
Tools: search_code_index → get_code_by_name(signature)
Result: Function signature + file location
```

### 2. SYMBOL_BROWSE
**Pattern:** "what methods does X have", "where is X implemented", "usages of X"

**Strategy:**
- Primary: Code index to find symbol
- Detail: Methods list or outline (not full implementation)
- Purpose: Exploration, not deep dive

**Example:**
```
Q: "what methods does AutomationCondition have"

Classification: SYMBOL_BROWSE
Tools: search_code_index → get_code_by_name(methods_list)
Result: Class with all method names listed
```

### 3. CONCEPT_EXPLAIN
**Pattern:** "how does X work", "what is Y", "explain Z"

**Strategy:**
- Primary: Documentation RAG search
- Secondary: Code examples for mentioned symbols
- Detail: Conceptual explanation + signatures

**Example:**
```
Q: "how do Dagster schedules work"

Classification: CONCEPT_EXPLAIN
Tools: query_rag → get_code_by_name(signature) for examples
Result: Doc explanation + code examples
```

### 4. HOW_TO
**Pattern:** "how do I use X", "example of Y", "tutorial for Z"

**Strategy:**
- Primary: Enhanced RAG (auto-follows references)
- Automatically retrieves docs + code + examples
- Detail: Practical, executable examples

**Example:**
```
Q: "how do I create a sensor"

Classification: HOW_TO
Tools: query_rag_enhanced(auto-follows references)
Result: Tutorial + code examples + referenced functions
```

### 5. DEBUG_BEHAVIOR
**Pattern:** "why does X fail", "error with Y", "X not working"

**Strategy:**
- Primary: Get implementation of mentioned code
- Secondary: Search docs for troubleshooting
- Detail: Full implementation by default

**Example:**
```
Q: "why is my asset not materializing"

Classification: DEBUG_BEHAVIOR
Tools: get_code_by_name(full) → query_rag(troubleshooting)
Result: Implementation + docs on common issues
```

### 6. COMPARISON
**Pattern:** "difference between X and Y", "X vs Y", "compare X to Y"

**Strategy:**
- Primary: RAG search for both items
- Secondary: Code signatures for comparison
- Detail: Side-by-side from docs

**Example:**
```
Q: "difference between schedules and sensors"

Classification: COMPARISON
Tools: query_rag(both concepts) → signatures
Result: Doc comparison + API differences
```

### 7. UNKNOWN_TARGET
**Pattern:** Ambiguous or unclear query

**Strategy:**
- Fallback: Broad documentation search
- Attempt to identify target from results
- Low confidence indicator

**Example:**
```
Q: "how to make things run"

Classification: UNKNOWN_TARGET (confidence: 0.3)
Tools: query_rag(broad search)
Result: Best-effort answer with low confidence warning
```

## Progressive Detail Levels

The system uses four detail levels to balance speed and information:

### 1. Signature (Fastest)
```python
def eager() -> AutomationCondition:
```
**When:** Initial response for symbol queries
**Size:** ~1-2 lines
**Speed:** Instant

### 2. Methods List (Fast)
```python
class AutomationCondition:
    - eager
    - on_cron
    - missing
    ... (58 more methods)
```
**When:** Browsing APIs
**Size:** ~10-30 lines
**Speed:** Very fast

### 3. Outline (Medium)
```python
class AutomationCondition:
    def eager() -> AutomationCondition: ...
    def on_cron(cron_schedule: str) -> AutomationCondition: ...
    def missing() -> AutomationCondition: ...
```
**When:** Understanding complete API
**Size:** ~50-200 lines
**Speed:** Fast

### 4. Full (Complete)
```python
def eager() -> AutomationCondition:
    """Create condition that is always eager to materialize."""
    return AutomationCondition(
        operand=None,
        label="eager",
        ...
    )
```
**When:** Deep dive into implementation
**Size:** ~100-1000+ lines
**Speed:** Moderate

## Using Smart Query

### MCP Tool (Claude)

**Recommended:** Use `smart_query` as your primary tool:

```
smart_query:
  question: "show me AutomationCondition.eager"
  expand_detail: false  # Use true for full implementation
  repo_filter: "dagster"  # Optional
```

The tool returns:
- ✅ Answer
- 📊 Query classification
- 🔄 Retrieval strategy
- 🛠️ Tool calls with reasoning
- 📈 Confidence score
- 💡 Suggestions

### Python API

```python
from rag_server.rag_system import RAGSystem

rag = RAGSystem()

# Smart query (automatic routing)
result = rag.smart_query(
    question="show me AutomationCondition.eager",
    expand_detail=False,
    repo_filter="dagster"
)

print(result['answer'])
print(f"Confidence: {result['confidence']}")
print(f"Query type: {result['classification']['type']}")
print(f"Tools used: {[tc['tool'] for tc in result['tool_calls']]}")
```

## Grounding Rules

The system enforces strict grounding to prevent hallucination:

### ✅ Allowed
- Information from retrieved docs
- Code from indexed repositories
- Explicit "I don't know" when not found
- Citing sources (file paths, line numbers)

### ❌ Not Allowed
- Inventing APIs not in retrieved code
- Guessing function signatures
- Assuming behavior without code evidence
- Making up examples not from docs

### Confidence Indicators

- 🟢 **High (0.7-1.0):** Strong evidence, exact matches
- 🟡 **Medium (0.4-0.7):** Partial evidence, fuzzy matches
- 🔴 **Low (0.0-0.4):** Weak or no evidence

## Example Flows

### Example 1: Exact Symbol Lookup

```
User: "show me AutomationCondition.eager"

Step 1: Classification
  Type: EXACT_SYMBOL (confidence: 0.9)
  Symbols: ["AutomationCondition.eager"]
  Libraries: ["dagster"]

Step 2: Routing
  Strategy: Direct code index lookup
  Initial mode: signature

Step 3: Execution
  ✓ search_code_index(query="AutomationCondition.eager", search_type="exact")
    → Found 1 match in dagster repo
  ✓ get_code_by_name(name="AutomationCondition.eager", mode="signature")
    → Retrieved signature from file

Step 4: Synthesis
  Answer: Function signature + file location
  Confidence: 🟢 0.9
  Suggestions:
    - Ask for 'full implementation' to see complete code
    - Ask 'what methods does AutomationCondition have' to browse API
```

### Example 2: Concept Explanation

```
User: "how do Dagster schedules work"

Step 1: Classification
  Type: CONCEPT_EXPLAIN (confidence: 0.75)
  Concepts: ["schedules"]
  Libraries: ["dagster"]

Step 2: Routing
  Strategy: Documentation RAG + code examples

Step 3: Execution
  ✓ query_rag(question="how do Dagster schedules work", tags=["dagster"])
    → Retrieved 5 doc chunks about schedules
  ✓ get_code_by_name(name="ScheduleDefinition", mode="signature")
    → Retrieved example signature

Step 4: Synthesis
  Answer: Doc explanation + code example
  Confidence: 🟡 0.7
  Suggestions:
    - Ask 'how do I use this' for practical examples
```

### Example 3: Debugging

```
User: "why is my asset not materializing"

Step 1: Classification
  Type: DEBUG_BEHAVIOR (confidence: 0.85)
  Concepts: ["asset", "materializing"]
  Libraries: ["dagster"]

Step 2: Routing
  Strategy: Get implementation + docs for troubleshooting
  Initial mode: full (debugging needs detail)

Step 3: Execution
  ✓ search_code_index(query="asset", search_type="contains")
    → Found multiple matches
  ✓ get_code_by_name(name="asset", mode="full")
    → Retrieved full decorator implementation
  ✓ query_rag(question="troubleshooting asset materialization")
    → Retrieved troubleshooting docs

Step 4: Synthesis
  Answer: Implementation + common issues
  Confidence: 🟡 0.7
```

## When to Use Which Tool

### Use `smart_query` (recommended)
- ✅ General questions
- ✅ When unsure which tool to use
- ✅ Want automatic optimization
- ✅ Need reasoning trace

### Use `search_code_index`
- Manual code exploration
- When you know exact symbol name
- Browsing multiple matches

### Use `get_code_by_name`
- When you know symbol and detail level
- Direct code retrieval
- Bypassing classification

### Use `query_rag`
- Pure documentation questions
- No code lookup needed
- Specific section filtering

### Use `query_rag_enhanced`
- How-to questions with auto-follow
- When you want thinking process
- Complex multi-step queries

## Performance Characteristics

### Smart Query Overhead
- Classification: ~5ms
- Routing: ~1ms
- Total overhead: ~6ms

### Tool Performance
- Code index lookup: ~5-10ms
- Code retrieval: ~10-20ms
- RAG query: ~200-500ms
- Enhanced RAG: ~500-1500ms

### Smart vs Manual
```
Manual approach:
  User chooses tool → Calls tool → Interprets result
  Time: Tool time + user decision time
  Risk: Wrong tool choice, missed optimization

Smart query:
  Auto classifies → Auto routes → Executes → Synthesizes
  Time: Tool time + ~6ms overhead
  Risk: Minimal, with confidence scoring
```

## Tips for Best Results

### 1. Be Specific
```
❌ "how to make things run"
✅ "how do I create a Dagster schedule"
```

### 2. Mention Libraries
```
❌ "show me the Table class"
✅ "show me the PyIceberg Table class"
```

### 3. Use Natural Language
```
❌ "AutomationCondition.eager documentation"
✅ "show me AutomationCondition.eager"
```

### 4. Request Detail When Needed
```
expand_detail=False: Quick signature
expand_detail=True: Full implementation
```

### 5. Filter by Repository
```
repo_filter="dagster": Only Dagster code
repo_filter=None: Search all indexed repos
```

## Troubleshooting

### Low Confidence Answers
**Cause:** Ambiguous query or missing data
**Solution:**
- Be more specific
- Mention library name
- Check if repo is indexed

### No Results Found
**Cause:** Symbol/concept not in index/docs
**Solution:**
- Verify spelling
- Check repo is indexed
- Try broader search terms

### Wrong Tool Choice
**Cause:** Misclassification
**Solution:**
- File issue with query example
- Use specific tool directly
- Rephrase query

## Summary

The tiered decision policy provides:

✅ **Automatic optimization** - No manual tool selection
✅ **Fast by default** - Progressive detail levels
✅ **Fully grounded** - No hallucination
✅ **Observable** - Complete reasoning trace
✅ **Confident** - Explicit confidence scoring

Use `smart_query` as your primary interface and let the system handle the complexity of optimal retrieval.
