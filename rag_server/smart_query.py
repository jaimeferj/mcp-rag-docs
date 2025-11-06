"""Smart query handler with tiered decision routing."""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

from utils.query_classifier import QueryClassifier, QueryClassification, QueryType
from utils.retrieval_router import RetrievalRouter, RetrievalStrategy, ToolType


@dataclass
class ToolCall:
    """Record of a tool call."""

    tool: str
    params: Dict[str, Any]
    result: Any
    success: bool
    reasoning: str
    error: Optional[str] = None


@dataclass
class SmartQueryResult:
    """Result of smart query execution."""

    answer: str  # Synthesized answer
    classification: Dict[str, Any]  # Query classification
    strategy: Dict[str, Any]  # Retrieval strategy used
    tool_calls: List[Dict[str, Any]]  # All tool calls made
    confidence: float  # Overall confidence (0.0 to 1.0)
    grounding: Dict[str, Any]  # Evidence used
    suggestions: List[str]  # Suggestions for follow-up


class SmartQueryHandler:
    """Orchestrates query classification, routing, and execution."""

    def __init__(self, rag_system):
        """
        Initialize smart query handler.

        Args:
            rag_system: RAGSystem instance for tool execution
        """
        self.rag_system = rag_system
        self.classifier = QueryClassifier()
        self.router = RetrievalRouter()
        self.tool_calls: List[ToolCall] = []

    def execute(
        self,
        query: str,
        expand_detail: bool = False,
        repo_filter: Optional[str] = None,
    ) -> SmartQueryResult:
        """
        Execute smart query with tiered decision routing.

        Args:
            query: User's question
            expand_detail: Whether to get full detail (vs minimal)
            repo_filter: Optional repository to filter

        Returns:
            SmartQueryResult with answer and metadata
        """
        self.tool_calls = []

        # Step 1: Classify query
        classification = self.classifier.classify(query)

        # Step 2: Route to retrieval strategy
        strategy = self.router.route(classification, expand_detail)

        # Step 3: Execute strategy
        results = self._execute_strategy(strategy, classification, repo_filter)

        # Step 4: Synthesize answer
        answer, confidence, grounding = self._synthesize_answer(
            query, classification, results
        )

        # Step 5: Generate suggestions
        suggestions = self._generate_suggestions(classification, results)

        return SmartQueryResult(
            answer=answer,
            classification=self._classification_to_dict(classification),
            strategy=self._strategy_to_dict(strategy),
            tool_calls=[self._tool_call_to_dict(tc) for tc in self.tool_calls],
            confidence=confidence,
            grounding=grounding,
            suggestions=suggestions,
        )

    def _execute_strategy(
        self,
        strategy: RetrievalStrategy,
        classification: QueryClassification,
        repo_filter: Optional[str],
    ) -> List[Any]:
        """Execute all steps in the retrieval strategy."""
        results = []

        for step in strategy.steps:
            # Override repo filter if provided
            if repo_filter and "repo_name" in step.params:
                step.params["repo_name"] = repo_filter

            # Execute the tool
            result = self._execute_tool(step.tool, step.params, step.reasoning)

            # Handle fallback
            if not result and step.fallback_on_empty:
                fallback = step.fallback_on_empty
                if repo_filter and "repo_name" in fallback.params:
                    fallback.params["repo_name"] = repo_filter
                result = self._execute_tool(fallback.tool, fallback.params, fallback.reasoning)

            if result:
                results.append(result)

        return results

    def _execute_tool(
        self,
        tool_type: ToolType,
        params: Dict[str, Any],
        reasoning: str,
    ) -> Optional[Any]:
        """Execute a single tool call."""
        try:
            if tool_type == ToolType.CODE_INDEX:
                result = self.rag_system.search_code(**params)
                self.tool_calls.append(
                    ToolCall(
                        tool="search_code_index",
                        params=params,
                        result=result,
                        success=bool(result),
                        reasoning=reasoning,
                    )
                )
                return result if result else None

            elif tool_type == ToolType.CODE_GET:
                result = self.rag_system.get_source_code_from_index(**params)
                self.tool_calls.append(
                    ToolCall(
                        tool="get_code_by_name",
                        params=params,
                        result=result,
                        success=result is not None and not result.get("error"),
                        reasoning=reasoning,
                    )
                )
                return result if result and not result.get("error") else None

            elif tool_type == ToolType.DOC_RAG:
                result = self.rag_system.query(**params)
                self.tool_calls.append(
                    ToolCall(
                        tool="query_rag",
                        params=params,
                        result=result,
                        success=bool(result.get("answer")),
                        reasoning=reasoning,
                    )
                )
                return result

            elif tool_type == ToolType.DOC_RAG_ENHANCED:
                result = self.rag_system.query_enhanced(**params)
                self.tool_calls.append(
                    ToolCall(
                        tool="query_rag_enhanced",
                        params=params,
                        result=result,
                        success=bool(result.get("answer")),
                        reasoning=reasoning,
                    )
                )
                return result

        except Exception as e:
            self.tool_calls.append(
                ToolCall(
                    tool=tool_type.value,
                    params=params,
                    result=None,
                    success=False,
                    reasoning=reasoning,
                    error=str(e),
                )
            )
            return None

        return None

    def _synthesize_answer(
        self,
        query: str,
        classification: QueryClassification,
        results: List[Any],
    ) -> tuple[str, float, Dict[str, Any]]:
        """
        Synthesize final answer from results.

        Returns:
            (answer, confidence, grounding)
        """
        if not results:
            return (
                "I couldn't find relevant information to answer your question. "
                f"Query type: {classification.query_type.value}. "
                "Try rephrasing or being more specific.",
                0.1,
                {"sources": [], "code": []},
            )

        answer_parts = []
        grounding = {"sources": [], "code": []}
        confidence_scores = []

        # Process results based on query type
        if classification.query_type == QueryType.EXACT_SYMBOL:
            answer_parts.append(self._format_exact_symbol_answer(results, grounding))
            confidence_scores.append(0.9 if results else 0.1)

        elif classification.query_type == QueryType.SYMBOL_BROWSE:
            answer_parts.append(self._format_symbol_browse_answer(results, grounding))
            confidence_scores.append(0.8 if results else 0.1)

        elif classification.query_type in [QueryType.CONCEPT_EXPLAIN, QueryType.HOW_TO]:
            answer_parts.append(self._format_concept_answer(results, grounding))
            confidence_scores.append(0.7 if results else 0.2)

        elif classification.query_type == QueryType.DEBUG_BEHAVIOR:
            answer_parts.append(self._format_debug_answer(results, grounding))
            confidence_scores.append(0.7 if results else 0.2)

        elif classification.query_type == QueryType.COMPARISON:
            answer_parts.append(self._format_comparison_answer(results, grounding))
            confidence_scores.append(0.6 if results else 0.2)

        else:
            answer_parts.append(self._format_unknown_answer(results, grounding))
            confidence_scores.append(0.4 if results else 0.1)

        answer = "\n\n".join(filter(None, answer_parts))
        confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        return answer, confidence, grounding

    def _format_exact_symbol_answer(
        self, results: List[Any], grounding: Dict[str, Any]
    ) -> str:
        """Format answer for EXACT_SYMBOL query."""
        parts = []

        for result in results:
            if isinstance(result, dict):
                # Code result
                if result.get("code"):
                    code = result["code"]
                    file_path = result.get("file_path", "unknown")
                    line = result.get("line_number", "?")
                    obj_type = result.get("type", "code")
                    name = result.get("name") or result.get("qualified_name", "")

                    parts.append(f"**{name}** ({obj_type})")
                    parts.append(f"Location: `{file_path}:{line}`")
                    parts.append(f"\n```python\n{code}\n```")

                    grounding["code"].append(
                        {
                            "name": name,
                            "file": file_path,
                            "line": line,
                            "type": obj_type,
                        }
                    )

                # Search results
                elif isinstance(result, list):
                    for item in result[:3]:  # Top 3
                        name = item.get("qualified_name", item.get("name"))
                        file_path = item.get("file_path", "")
                        line = item.get("line_number", "")
                        parts.append(f"- `{name}` at {file_path}:{line}")

        return "\n".join(parts) if parts else ""

    def _format_symbol_browse_answer(
        self, results: List[Any], grounding: Dict[str, Any]
    ) -> str:
        """Format answer for SYMBOL_BROWSE query."""
        return self._format_exact_symbol_answer(results, grounding)

    def _format_concept_answer(
        self, results: List[Any], grounding: Dict[str, Any]
    ) -> str:
        """Format answer for CONCEPT_EXPLAIN or HOW_TO query."""
        parts = []

        for result in results:
            if isinstance(result, dict):
                # RAG result
                if result.get("answer"):
                    parts.append("## Explanation")
                    parts.append(result["answer"])

                    if result.get("sources"):
                        grounding["sources"].extend(result["sources"])

                # Code examples
                if result.get("code"):
                    parts.append("\n## Code Example")
                    code = result["code"]
                    name = result.get("name", "")
                    parts.append(f"```python\n{code}\n```")

        return "\n\n".join(parts) if parts else ""

    def _format_debug_answer(
        self, results: List[Any], grounding: Dict[str, Any]
    ) -> str:
        """Format answer for DEBUG_BEHAVIOR query."""
        parts = []
        parts.append("## Implementation")

        for result in results:
            if isinstance(result, dict) and result.get("code"):
                code = result["code"]
                name = result.get("name", "")
                parts.append(f"\n**{name}**:")
                parts.append(f"```python\n{code}\n```")

            elif isinstance(result, dict) and result.get("answer"):
                parts.append("\n## Documentation")
                parts.append(result["answer"])

        return "\n".join(parts) if parts else ""

    def _format_comparison_answer(
        self, results: List[Any], grounding: Dict[str, Any]
    ) -> str:
        """Format answer for COMPARISON query."""
        return self._format_concept_answer(results, grounding)

    def _format_unknown_answer(
        self, results: List[Any], grounding: Dict[str, Any]
    ) -> str:
        """Format answer for UNKNOWN_TARGET query."""
        return self._format_concept_answer(results, grounding)

    def _generate_suggestions(
        self, classification: QueryClassification, results: List[Any]
    ) -> List[str]:
        """Generate follow-up suggestions."""
        suggestions = []

        if classification.query_type == QueryType.EXACT_SYMBOL and results:
            suggestions.append("Ask for 'full implementation' to see complete code")
            suggestions.append("Ask 'what methods does X have' to browse the API")

        elif classification.query_type == QueryType.SYMBOL_BROWSE and results:
            suggestions.append("Ask for specific method implementation")

        elif classification.query_type == QueryType.CONCEPT_EXPLAIN and results:
            suggestions.append("Ask 'how do I use this' for practical examples")

        return suggestions

    def _classification_to_dict(self, classification: QueryClassification) -> Dict:
        """Convert classification to dict."""
        return {
            "type": classification.query_type.value,
            "confidence": classification.confidence,
            "symbols": classification.extracted_symbols,
            "concepts": classification.extracted_concepts,
            "libraries": classification.library_hints,
            "reasoning": classification.reasoning,
        }

    def _strategy_to_dict(self, strategy: RetrievalStrategy) -> Dict:
        """Convert strategy to dict."""
        return {
            "reasoning": strategy.reasoning,
            "initial_mode": strategy.initial_mode.value,
            "expand_on_request": strategy.expand_on_request,
            "confidence_threshold": strategy.confidence_threshold,
            "steps": [
                {
                    "tool": step.tool.value,
                    "params": step.params,
                    "reasoning": step.reasoning,
                }
                for step in strategy.steps
            ],
        }

    def _tool_call_to_dict(self, tool_call: ToolCall) -> Dict:
        """Convert tool call to dict for JSON serialization."""
        return {
            "tool": tool_call.tool,
            "params": tool_call.params,
            "success": tool_call.success,
            "reasoning": tool_call.reasoning,
            "error": tool_call.error,
            "has_result": tool_call.result is not None,
        }
