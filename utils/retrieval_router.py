"""Retrieval routing based on query classification."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

from utils.query_classifier import QueryType, QueryClassification


class RetrievalMode(Enum):
    """Detail level for code retrieval."""

    SIGNATURE = "signature"  # Just the def line
    METHODS_LIST = "methods_list"  # Class with method names
    OUTLINE = "outline"  # Class with all signatures
    FULL = "full"  # Complete implementation


class ToolType(Enum):
    """Types of retrieval tools."""

    CODE_INDEX = "code_index"  # search_code_index
    CODE_GET = "code_get"  # get_code_by_name
    DOC_RAG = "doc_rag"  # query_rag
    DOC_RAG_ENHANCED = "doc_rag_enhanced"  # query_rag_enhanced


@dataclass
class RetrievalStep:
    """A single step in the retrieval strategy."""

    tool: ToolType
    params: Dict[str, Any]
    reasoning: str
    fallback_on_empty: Optional['RetrievalStep'] = None


@dataclass
class RetrievalStrategy:
    """Complete strategy for answering a query."""

    steps: List[RetrievalStep]
    initial_mode: RetrievalMode
    expand_on_request: bool  # Whether to expand detail if needed
    confidence_threshold: float  # Minimum confidence to proceed
    reasoning: str


class RetrievalRouter:
    """Routes queries to optimal retrieval strategies."""

    def __init__(self, default_top_k: int = 5, default_repo: Optional[str] = None):
        """
        Initialize router.

        Args:
            default_top_k: Default number of RAG results
            default_repo: Default repository to search (None = all)
        """
        self.default_top_k = default_top_k
        self.default_repo = default_repo

    def route(
        self,
        classification: QueryClassification,
        expand_detail: bool = False,
    ) -> RetrievalStrategy:
        """
        Determine retrieval strategy based on query classification.

        Args:
            classification: Query classification result
            expand_detail: Whether to get full detail (user explicitly requested)

        Returns:
            RetrievalStrategy with ordered steps
        """
        query_type = classification.query_type

        if query_type == QueryType.EXACT_SYMBOL:
            return self._route_exact_symbol(classification, expand_detail)
        elif query_type == QueryType.SYMBOL_BROWSE:
            return self._route_symbol_browse(classification, expand_detail)
        elif query_type == QueryType.CONCEPT_EXPLAIN:
            return self._route_concept_explain(classification)
        elif query_type == QueryType.HOW_TO:
            return self._route_how_to(classification)
        elif query_type == QueryType.DEBUG_BEHAVIOR:
            return self._route_debug_behavior(classification, expand_detail)
        elif query_type == QueryType.COMPARISON:
            return self._route_comparison(classification)
        else:  # UNKNOWN_TARGET
            return self._route_unknown(classification)

    def _route_exact_symbol(
        self,
        classification: QueryClassification,
        expand_detail: bool,
    ) -> RetrievalStrategy:
        """Route EXACT_SYMBOL queries."""
        symbols = classification.extracted_symbols
        primary_symbol = symbols[0] if symbols else None

        if not primary_symbol:
            # Fallback to doc search
            return self._route_unknown(classification)

        # Start with signature unless full detail requested
        initial_mode = RetrievalMode.FULL if expand_detail else RetrievalMode.SIGNATURE

        steps = [
            # Step 1: Try code index exact match
            RetrievalStep(
                tool=ToolType.CODE_INDEX,
                params={
                    "query": primary_symbol,
                    "search_type": "exact",
                    "repo_name": self._get_repo_hint(classification),
                    "limit": 5,
                },
                reasoning=f"Look up exact symbol '{primary_symbol}' in code index",
                fallback_on_empty=RetrievalStep(
                    tool=ToolType.CODE_INDEX,
                    params={
                        "query": primary_symbol,
                        "search_type": "contains",
                        "repo_name": self._get_repo_hint(classification),
                        "limit": 10,
                    },
                    reasoning=f"Exact match failed, try fuzzy search for '{primary_symbol}'",
                ),
            ),
            # Step 2: Get source code
            RetrievalStep(
                tool=ToolType.CODE_GET,
                params={
                    "name": primary_symbol,
                    "mode": initial_mode.value,
                    "repo_name": self._get_repo_hint(classification),
                },
                reasoning=f"Retrieve {initial_mode.value} for '{primary_symbol}'",
            ),
        ]

        return RetrievalStrategy(
            steps=steps,
            initial_mode=initial_mode,
            expand_on_request=True,
            confidence_threshold=0.5,
            reasoning=f"Direct code lookup for symbol '{primary_symbol}'",
        )

    def _route_symbol_browse(
        self,
        classification: QueryClassification,
        expand_detail: bool,
    ) -> RetrievalStrategy:
        """Route SYMBOL_BROWSE queries."""
        symbols = classification.extracted_symbols
        primary_symbol = symbols[0] if symbols else None

        if not primary_symbol:
            return self._route_unknown(classification)

        # For browsing, start with methods_list or outline
        initial_mode = RetrievalMode.OUTLINE if expand_detail else RetrievalMode.METHODS_LIST

        steps = [
            # Step 1: Find the symbol
            RetrievalStep(
                tool=ToolType.CODE_INDEX,
                params={
                    "query": primary_symbol,
                    "search_type": "exact",
                    "repo_name": self._get_repo_hint(classification),
                    "limit": 5,
                },
                reasoning=f"Find '{primary_symbol}' in code index",
            ),
            # Step 2: Get overview
            RetrievalStep(
                tool=ToolType.CODE_GET,
                params={
                    "name": primary_symbol,
                    "mode": initial_mode.value,
                    "repo_name": self._get_repo_hint(classification),
                },
                reasoning=f"Get {initial_mode.value} to browse available methods",
            ),
        ]

        return RetrievalStrategy(
            steps=steps,
            initial_mode=initial_mode,
            expand_on_request=True,
            confidence_threshold=0.5,
            reasoning=f"Browse API of '{primary_symbol}'",
        )

    def _route_concept_explain(
        self,
        classification: QueryClassification,
    ) -> RetrievalStrategy:
        """Route CONCEPT_EXPLAIN queries."""
        # Primary: RAG for concepts
        # Secondary: Code examples for mentioned symbols

        steps = [
            # Step 1: Search documentation
            RetrievalStep(
                tool=ToolType.DOC_RAG,
                params={
                    "question": classification.reasoning,  # Original query
                    "top_k": self.default_top_k,
                    "tags": classification.library_hints or None,
                },
                reasoning="Search documentation for concept explanation",
            ),
        ]

        # If symbols mentioned, add code examples
        if classification.extracted_symbols:
            for symbol in classification.extracted_symbols[:2]:  # Limit to 2
                steps.append(
                    RetrievalStep(
                        tool=ToolType.CODE_GET,
                        params={
                            "name": symbol,
                            "mode": RetrievalMode.SIGNATURE.value,
                            "repo_name": self._get_repo_hint(classification),
                        },
                        reasoning=f"Get signature for mentioned symbol '{symbol}'",
                    )
                )

        return RetrievalStrategy(
            steps=steps,
            initial_mode=RetrievalMode.SIGNATURE,
            expand_on_request=False,
            confidence_threshold=0.3,
            reasoning="Explain concept using docs + code examples",
        )

    def _route_how_to(
        self,
        classification: QueryClassification,
    ) -> RetrievalStrategy:
        """Route HOW_TO queries."""
        # Use enhanced RAG which automatically follows references
        steps = [
            RetrievalStep(
                tool=ToolType.DOC_RAG_ENHANCED,
                params={
                    "question": classification.reasoning,
                    "top_k": self.default_top_k,
                    "max_followups": 2,
                    "tags": classification.library_hints or None,
                },
                reasoning="Use enhanced RAG to get how-to docs + code examples",
            ),
        ]

        return RetrievalStrategy(
            steps=steps,
            initial_mode=RetrievalMode.SIGNATURE,
            expand_on_request=True,
            confidence_threshold=0.3,
            reasoning="How-to guide with automatic code retrieval",
        )

    def _route_debug_behavior(
        self,
        classification: QueryClassification,
        expand_detail: bool,
    ) -> RetrievalStrategy:
        """Route DEBUG_BEHAVIOR queries."""
        symbols = classification.extracted_symbols
        mode = RetrievalMode.FULL if expand_detail else RetrievalMode.SIGNATURE

        steps = []

        # Step 1: Get code for mentioned symbols
        if symbols:
            for symbol in symbols[:2]:  # Limit to 2
                steps.extend([
                    RetrievalStep(
                        tool=ToolType.CODE_INDEX,
                        params={
                            "query": symbol,
                            "search_type": "exact",
                            "repo_name": self._get_repo_hint(classification),
                        },
                        reasoning=f"Find '{symbol}' to check implementation",
                    ),
                    RetrievalStep(
                        tool=ToolType.CODE_GET,
                        params={
                            "name": symbol,
                            "mode": mode.value,
                            "repo_name": self._get_repo_hint(classification),
                        },
                        reasoning=f"Get {mode.value} to understand behavior",
                    ),
                ])

        # Step 2: Search docs for error/behavior context
        steps.append(
            RetrievalStep(
                tool=ToolType.DOC_RAG,
                params={
                    "question": classification.reasoning,
                    "top_k": self.default_top_k,
                    "tags": classification.library_hints or None,
                },
                reasoning="Search docs for troubleshooting info",
            )
        )

        return RetrievalStrategy(
            steps=steps,
            initial_mode=mode,
            expand_on_request=True,
            confidence_threshold=0.4,
            reasoning="Debug by examining code + docs",
        )

    def _route_comparison(
        self,
        classification: QueryClassification,
    ) -> RetrievalStrategy:
        """Route COMPARISON queries."""
        # Search docs for each compared item
        steps = [
            RetrievalStep(
                tool=ToolType.DOC_RAG,
                params={
                    "question": classification.reasoning,
                    "top_k": self.default_top_k * 2,  # More results for comparison
                    "tags": classification.library_hints or None,
                },
                reasoning="Search docs for both items being compared",
            ),
        ]

        # Add code lookups for mentioned symbols
        if classification.extracted_symbols:
            for symbol in classification.extracted_symbols[:2]:
                steps.append(
                    RetrievalStep(
                        tool=ToolType.CODE_GET,
                        params={
                            "name": symbol,
                            "mode": RetrievalMode.SIGNATURE.value,
                            "repo_name": self._get_repo_hint(classification),
                        },
                        reasoning=f"Get signature for '{symbol}' to compare",
                    )
                )

        return RetrievalStrategy(
            steps=steps,
            initial_mode=RetrievalMode.SIGNATURE,
            expand_on_request=False,
            confidence_threshold=0.3,
            reasoning="Compare using docs + signatures",
        )

    def _route_unknown(
        self,
        classification: QueryClassification,
    ) -> RetrievalStrategy:
        """Route UNKNOWN_TARGET queries."""
        # Broad search to identify target
        steps = [
            RetrievalStep(
                tool=ToolType.DOC_RAG,
                params={
                    "question": classification.reasoning,
                    "top_k": self.default_top_k,
                },
                reasoning="Broad search to identify query target",
            ),
        ]

        return RetrievalStrategy(
            steps=steps,
            initial_mode=RetrievalMode.SIGNATURE,
            expand_on_request=True,
            confidence_threshold=0.2,
            reasoning="Unknown query type - using broad search",
        )

    def _get_repo_hint(self, classification: QueryClassification) -> Optional[str]:
        """Extract repository hint from classification."""
        if classification.library_hints:
            return classification.library_hints[0]
        return self.default_repo
