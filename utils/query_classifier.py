"""Query classification for tiered decision routing."""

import re
from dataclasses import dataclass
from typing import List, Optional, Set
from enum import Enum


class QueryType(Enum):
    """Types of queries the system can handle."""

    EXACT_SYMBOL = "exact_symbol"  # "show me X.y", "what is X.y"
    SYMBOL_BROWSE = "symbol_browse"  # "what methods does X have"
    CONCEPT_EXPLAIN = "concept_explain"  # "how does X work"
    HOW_TO = "how_to"  # "how do I use X"
    DEBUG_BEHAVIOR = "debug_behavior"  # "why does X fail"
    COMPARISON = "comparison"  # "difference between X and Y"
    UNKNOWN_TARGET = "unknown_target"  # Can't identify clear target


@dataclass
class QueryClassification:
    """Result of query classification."""

    query_type: QueryType
    confidence: float  # 0.0 to 1.0
    extracted_symbols: List[str]  # Code symbols mentioned (e.g., ["AutomationCondition", "eager"])
    extracted_concepts: List[str]  # Concepts mentioned (e.g., ["schedules", "sensors"])
    library_hints: List[str]  # Library names mentioned (e.g., ["dagster", "pyiceberg"])
    reasoning: str  # Why this classification was chosen


class QueryClassifier:
    """Classifies user queries to determine optimal retrieval strategy."""

    # Pattern definitions for each query type
    EXACT_SYMBOL_PATTERNS = [
        r"(?:show|get|display|view|open)\s+(?:me\s+)?([A-Z][a-zA-Z0-9]*(?:\.[a-z_][a-zA-Z0-9_]*)*)",
        r"what\s+(?:is|does)\s+([A-Z][a-zA-Z0-9]*(?:\.[a-z_][a-zA-Z0-9_]*)*)",
        r"(?:definition|signature)\s+(?:of|for)\s+([A-Z][a-zA-Z0-9]*(?:\.[a-z_][a-zA-Z0-9_]*)*)",
        r"`([A-Z][a-zA-Z0-9]*(?:\.[a-z_][a-zA-Z0-9_]*)*)`",
    ]

    SYMBOL_BROWSE_PATTERNS = [
        r"(?:what|which|list)\s+(?:methods|functions|classes|attributes)\s+(?:does|in|of)\s+([A-Z][a-zA-Z0-9]*)",
        r"(?:where|find)\s+(?:is|are)\s+([A-Z][a-zA-Z0-9]*)\s+(?:implemented|defined|located)",
        r"(?:usages?|callers?|references?)\s+(?:of|to)\s+([A-Z][a-zA-Z0-9]*(?:\.[a-z_][a-zA-Z0-9_]*)*)",
        r"(?:what|show)\s+(?:can|methods)\s+(?:I|you)\s+(?:do|call)\s+(?:with|on)\s+([A-Z][a-zA-Z0-9]*)",
    ]

    CONCEPT_EXPLAIN_PATTERNS = [
        r"how\s+(?:does|do|is)\s+([a-z_][a-z0-9_\s]*?)\s+(?:work|function|operate)",
        r"what\s+(?:is|are)\s+([a-z_][a-z0-9_\s]*?)(?:\?|$)",
        r"explain\s+([a-z_][a-z0-9_\s]*)",
        r"(?:understand|learn)\s+(?:about\s+)?([a-z_][a-z0-9_\s]*)",
    ]

    HOW_TO_PATTERNS = [
        r"how\s+(?:do\s+I|to|can\s+I)\s+(use|configure|setup|create|implement|build|make)",
        r"(?:example|sample|demo)\s+(?:of|for|using)\s+([a-zA-Z0-9_\s]+)",
        r"(?:tutorial|guide)\s+(?:on|for)\s+([a-zA-Z0-9_\s]+)",
        r"steps?\s+to\s+(configure|setup|create|use)\s+([a-zA-Z0-9_\s]+)",
    ]

    DEBUG_BEHAVIOR_PATTERNS = [
        r"why\s+(?:is|does|doesn't|am\s+I\s+getting)\s+([a-zA-Z0-9_\s]+)",
        r"(?:error|exception|issue|problem)\s+(?:with|in|on)\s+([a-zA-Z0-9_\s]+)",
        r"(?:failing|broken|not\s+working)\s+([a-zA-Z0-9_\s]+)",
        r"debug\s+([a-zA-Z0-9_\s]+)",
        r"I\s+get\s+(?:error|exception)",
    ]

    COMPARISON_PATTERNS = [
        r"(?:difference|differ)\s+(?:between|vs)\s+([a-zA-Z0-9_\s]+?)\s+(?:and|vs)\s+([a-zA-Z0-9_\s]+)",
        r"([a-zA-Z0-9_]+)\s+vs\s+([a-zA-Z0-9_]+)",
        r"compare\s+([a-zA-Z0-9_\s]+?)\s+(?:and|to|with)\s+([a-zA-Z0-9_\s]+)",
        r"(?:which|should\s+I\s+use)\s+([a-zA-Z0-9_]+)\s+or\s+([a-zA-Z0-9_]+)",
    ]

    # Symbol extraction patterns
    SYMBOL_PATTERNS = [
        r"\b([A-Z][a-zA-Z0-9]*(?:\.[a-z_][a-zA-Z0-9_]*)*)\b",  # Class.method
        r"`([^`]+)`",  # Backticks
        r"@([a-z_][a-z0-9_]*)",  # Decorators
    ]

    # Known library names
    KNOWN_LIBRARIES = {
        "dagster",
        "pyiceberg",
        "iceberg",
        "pandas",
        "numpy",
        "polars",
        "duckdb",
        "prefect",
        "airflow",
    }

    def classify(self, query: str) -> QueryClassification:
        """
        Classify a user query into a query type.

        Args:
            query: User's question

        Returns:
            QueryClassification with type, confidence, and extracted info
        """
        query_lower = query.lower()

        # Extract symbols and concepts
        symbols = self._extract_symbols(query)
        concepts = self._extract_concepts(query)
        libraries = self._extract_libraries(query)

        # Try each classification in order of specificity
        # Most specific patterns first

        # EXACT_SYMBOL - very specific patterns
        if self._matches_patterns(query, self.EXACT_SYMBOL_PATTERNS):
            return QueryClassification(
                query_type=QueryType.EXACT_SYMBOL,
                confidence=0.9,
                extracted_symbols=symbols,
                extracted_concepts=concepts,
                library_hints=libraries,
                reasoning="Query matches exact symbol lookup pattern (show/get/what is X.y)",
            )

        # SYMBOL_BROWSE - exploring APIs
        if self._matches_patterns(query, self.SYMBOL_BROWSE_PATTERNS):
            return QueryClassification(
                query_type=QueryType.SYMBOL_BROWSE,
                confidence=0.85,
                extracted_symbols=symbols,
                extracted_concepts=concepts,
                library_hints=libraries,
                reasoning="Query matches symbol browsing pattern (methods/usages/where)",
            )

        # DEBUG_BEHAVIOR - troubleshooting
        if self._matches_patterns(query, self.DEBUG_BEHAVIOR_PATTERNS):
            return QueryClassification(
                query_type=QueryType.DEBUG_BEHAVIOR,
                confidence=0.85,
                extracted_symbols=symbols,
                extracted_concepts=concepts,
                library_hints=libraries,
                reasoning="Query matches debugging pattern (why/error/failing)",
            )

        # COMPARISON - comparing things
        if self._matches_patterns(query, self.COMPARISON_PATTERNS):
            return QueryClassification(
                query_type=QueryType.COMPARISON,
                confidence=0.8,
                extracted_symbols=symbols,
                extracted_concepts=concepts,
                library_hints=libraries,
                reasoning="Query matches comparison pattern (difference/vs/compare)",
            )

        # HOW_TO - practical usage
        if self._matches_patterns(query, self.HOW_TO_PATTERNS):
            return QueryClassification(
                query_type=QueryType.HOW_TO,
                confidence=0.8,
                extracted_symbols=symbols,
                extracted_concepts=concepts,
                library_hints=libraries,
                reasoning="Query matches how-to pattern (how do I/example/tutorial)",
            )

        # CONCEPT_EXPLAIN - understanding concepts
        if self._matches_patterns(query, self.CONCEPT_EXPLAIN_PATTERNS):
            return QueryClassification(
                query_type=QueryType.CONCEPT_EXPLAIN,
                confidence=0.75,
                extracted_symbols=symbols,
                extracted_concepts=concepts,
                library_hints=libraries,
                reasoning="Query matches concept explanation pattern (how does/what is)",
            )

        # UNKNOWN_TARGET - fallback
        # If we have clear symbols, treat as symbol query
        if symbols:
            return QueryClassification(
                query_type=QueryType.EXACT_SYMBOL,
                confidence=0.5,
                extracted_symbols=symbols,
                extracted_concepts=concepts,
                library_hints=libraries,
                reasoning="No clear pattern match, but symbols detected - treating as symbol lookup",
            )

        # If we have concepts, treat as concept explanation
        if concepts:
            return QueryClassification(
                query_type=QueryType.CONCEPT_EXPLAIN,
                confidence=0.5,
                extracted_symbols=symbols,
                extracted_concepts=concepts,
                library_hints=libraries,
                reasoning="No clear pattern match, but concepts detected - treating as concept explanation",
            )

        # Truly unknown
        return QueryClassification(
            query_type=QueryType.UNKNOWN_TARGET,
            confidence=0.3,
            extracted_symbols=symbols,
            extracted_concepts=concepts,
            library_hints=libraries,
            reasoning="Unable to classify query type - will use broad search",
        )

    def _matches_patterns(self, query: str, patterns: List[str]) -> bool:
        """Check if query matches any of the given patterns."""
        for pattern in patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _extract_symbols(self, query: str) -> List[str]:
        """Extract code symbols from query."""
        symbols = set()
        for pattern in self.SYMBOL_PATTERNS:
            matches = re.findall(pattern, query)
            symbols.update(matches)

        # Filter out common words that look like symbols
        common_words = {"I", "A", "In", "On", "To", "For", "The", "With"}
        symbols = {s for s in symbols if s not in common_words}

        return sorted(list(symbols))

    def _extract_concepts(self, query: str) -> List[str]:
        """Extract concept keywords from query."""
        # Remove symbols first
        query_no_symbols = re.sub(r"\b[A-Z][a-zA-Z0-9]*(?:\.[a-z_][a-zA-Z0-9_]*)*\b", "", query)

        # Common technical terms
        concept_keywords = {
            "schedule", "schedules", "scheduling",
            "sensor", "sensors",
            "asset", "assets",
            "partition", "partitions", "partitioning",
            "job", "jobs",
            "op", "ops", "operation", "operations",
            "graph", "graphs",
            "resource", "resources",
            "config", "configuration",
            "pipeline", "pipelines",
            "dag", "dags",
            "table", "tables",
            "schema", "schemas",
            "reconciliation",
            "automation",
            "materialization",
            "backfill",
        }

        found_concepts = []
        query_lower = query_no_symbols.lower()
        for keyword in concept_keywords:
            if keyword in query_lower:
                found_concepts.append(keyword)

        return found_concepts

    def _extract_libraries(self, query: str) -> List[str]:
        """Extract library names from query."""
        found_libraries = []
        query_lower = query.lower()
        for lib in self.KNOWN_LIBRARIES:
            if lib in query_lower:
                found_libraries.append(lib)
        return found_libraries
