"""RAG system for document storage and retrieval-augmented generation."""

from pathlib import Path
from typing import List, Optional

from config.settings import settings
from utils.document_processor import DocumentProcessor
from utils.embeddings import GoogleEmbeddingService
from utils.google_api_client import GoogleAPIClient
from utils.github_parser import GitHubURLParser
from utils.hierarchical_chunker import HierarchicalChunker
from utils.reference_extractor import PythonReferenceExtractor
from utils.source_extractor import SourceCodeExtractor
from utils.vector_store import VectorStore
from utils.code_index_store import CodeIndexStore


class RAGSystem:
    """Retrieval-Augmented Generation system."""

    def __init__(self):
        """Initialize the RAG system with all components."""
        # Initialize rate-limited Google API client
        self.api_client = GoogleAPIClient(
            api_key=settings.google_api_key,
            rpm_limit=settings.google_api_rpm_limit,
            tpm_limit=settings.google_api_tpm_limit,
            rpd_limit=settings.google_api_rpd_limit,
            rate_limit_db_path=settings.rate_limit_db_path,
        )

        # Initialize services with shared API client
        self.embedding_service = GoogleEmbeddingService(
            api_key=settings.google_api_key,
            model_name=settings.embedding_model,
            api_client=self.api_client,
        )
        self.vector_store = VectorStore(
            path=settings.qdrant_path,
            collection_name=settings.qdrant_collection_name,
        )
        self.chunker = HierarchicalChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        self.document_processor = DocumentProcessor()

        # Initialize source code utilities
        self.github_parser = GitHubURLParser(repo_root=settings.dagster_repo_path)
        self.source_extractor = SourceCodeExtractor()
        self.reference_extractor = PythonReferenceExtractor()

        # Initialize code index
        self.code_index = None
        if settings.enable_code_index:
            try:
                self.code_index = CodeIndexStore(db_path=settings.code_index_path)
            except Exception as e:
                print(f"Warning: Could not initialize code index: {e}")

        # Store model name for generation
        self.llm_model_name = settings.llm_model

    async def add_document(
        self,
        file_path: str | Path,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        base_path: Optional[str | Path] = None,
    ) -> dict:
        """
        Add a document to the RAG system.

        Args:
            file_path: Path to the document
            content: Optional pre-loaded content
            tags: Optional list of tags for categorization
            base_path: Optional base path to extract relative path structure from

        Returns:
            Dictionary with document info, tags, and number of chunks
        """
        tags = tags or []

        # Process document with base_path to extract filesystem structure
        doc_info = await self.document_processor.process_document(file_path, content, base_path)

        # Determine if this is markdown for hierarchical chunking
        is_markdown = doc_info["file_type"] == "markdown"

        # Chunk the text using hierarchical chunker with path structure
        chunks = self.chunker.chunk_with_metadata(
            text=doc_info["content"],
            doc_id=doc_info["doc_id"],
            is_markdown=is_markdown,
            extra_metadata={
                "filename": doc_info["filename"],
                "file_type": doc_info["file_type"],
                "tags": tags,
                "path_structure": doc_info.get("path_structure"),
            },
        )

        # Generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_service.embed_batch(texts)

        # Store in vector database
        metadata = [
            {
                "doc_id": chunk["doc_id"],
                "chunk_index": chunk["chunk_index"],
                "total_chunks": chunk["total_chunks"],
                "filename": chunk["filename"],
                "file_type": chunk["file_type"],
                "tags": tags,
                "section_path": chunk["section_path"],
                "section_level": chunk["section_level"],
            }
            for chunk in chunks
        ]

        self.vector_store.add_documents(texts, embeddings, metadata)

        return {
            "doc_id": doc_info["doc_id"],
            "filename": doc_info["filename"],
            "file_type": doc_info["file_type"],
            "tags": tags,
            "num_chunks": len(chunks),
        }

    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        tags: Optional[List[str]] = None,
        section_path: Optional[str] = None,
    ) -> dict:
        """
        Query the RAG system with a question.

        Args:
            question: User's question
            top_k: Number of chunks to retrieve (default from settings)
            tags: Optional list of tags to filter by
            section_path: Optional section path to filter by

        Returns:
            Dictionary with answer, sources, and retrieved context
        """
        top_k = top_k or settings.top_k_results

        # Generate query embedding
        query_embedding = self.embedding_service.embed_query(question)

        # Retrieve relevant chunks with filtering
        results = self.vector_store.search(
            query_embedding, top_k=top_k, tags=tags, section_path=section_path
        )

        if not results:
            return {
                "answer": "I don't have any relevant information to answer this question.",
                "sources": [],
                "context_used": [],
            }

        # Build context from retrieved chunks with section information
        context_parts = []
        for i, result in enumerate(results):
            section = result["metadata"].get("section_path", "Document")
            text = result["text"]
            context_parts.append(f"[{section}]\n{text}")

        context = "\n\n".join(context_parts)

        # Generate answer using LLM with rate limiting
        prompt = self._build_prompt(question, context)
        response = self.api_client.generate_content(self.llm_model_name, prompt)

        # Extract sources with section information
        sources = [
            {
                "filename": result["metadata"].get("filename", "unknown"),
                "chunk_index": result["metadata"].get("chunk_index", 0),
                "score": result["score"],
                "section_path": result["metadata"].get("section_path", "Document"),
            }
            for result in results
        ]

        return {
            "answer": response.text,
            "sources": sources,
            "context_used": [result["text"] for result in results],
        }

    def _build_prompt(self, question: str, context: str) -> str:
        """Build a prompt for the LLM with context."""
        return f"""You are a helpful assistant that answers questions based on the provided context.

Context:
{context}

Question: {question}

Please provide a clear and concise answer based on the context above. If the context doesn't contain enough information to answer the question, say so."""

    def query_enhanced(
        self,
        question: str,
        top_k: Optional[int] = None,
        max_followups: int = 3,
        tags: Optional[List[str]] = None,
        section_path: Optional[str] = None,
    ) -> dict:
        """
        Enhanced query with automatic reference following and source code retrieval.

        This method implements self-thinking by:
        1. Executing initial query
        2. Extracting Python object references from the answer
        3. Following up with queries for referenced objects
        4. Retrieving source code when GitHub URLs are found
        5. Compiling comprehensive response

        Args:
            question: User's question
            top_k: Number of chunks to retrieve per query
            max_followups: Maximum number of references to follow
            tags: Optional list of tags to filter by
            section_path: Optional section path to filter by

        Returns:
            Dictionary with:
            - answer: Original answer
            - sources: List of sources
            - context_used: Retrieved context chunks
            - thinking_process: List of follow-up actions taken
            - followed_references: Dict of reference -> docs
            - source_code: Dict of reference -> code snippets
        """
        thinking_process = []
        followed_references = {}
        source_code_snippets = {}

        # Step 1: Initial query
        thinking_process.append(f"[1] Executing initial query: '{question}'")
        initial_result = self.query(question, top_k, tags, section_path)

        # Step 2: Extract references from answer and context
        thinking_process.append("[2] Analyzing answer for Python object references...")
        all_text = initial_result['answer'] + '\n\n' + '\n\n'.join(initial_result['context_used'])
        references = self.reference_extractor.extract_references(all_text)

        # Get prioritized references to follow
        priority_refs = self.reference_extractor.prioritize_references(
            references, max_refs=max_followups
        )

        if priority_refs:
            thinking_process.append(
                f"[3] Found {len(references['all'])} references. Following up on top {len(priority_refs)}: {', '.join(priority_refs)}"
            )

            # Step 3: Follow up on each reference
            for i, ref in enumerate(priority_refs, 1):
                ref_query = self.reference_extractor.format_reference_for_query(ref)
                thinking_process.append(f"[3.{i}] Querying for reference: '{ref}' -> '{ref_query}'")

                # Query for this reference
                ref_result = self.query(ref_query, top_k=3, tags=tags)
                followed_references[ref] = {
                    'query': ref_query,
                    'answer': ref_result['answer'],
                    'sources': ref_result['sources'],
                }

                # Extract GitHub URLs from this reference's context
                ref_context = '\n'.join(ref_result['context_used'])
                github_urls = self.reference_extractor.extract_github_urls(ref_context)

                if github_urls:
                    thinking_process.append(
                        f"[3.{i}.a] Found {len(github_urls)} GitHub URL(s) for '{ref}'"
                    )

                    # Try to get source code from the first URL
                    for url in github_urls[:1]:  # Just get the first one to avoid too much data
                        thinking_process.append(
                            f"[3.{i}.b] Retrieving source code from: {url[:80]}..."
                        )
                        code_result = self.get_source_code(url, context_lines=15)

                        if not code_result.get('error'):
                            source_code_snippets[ref] = {
                                'url': url,
                                'file_path': code_result.get('file_path', 'unknown'),
                                'code': code_result.get('code', ''),
                                'start_line': code_result.get('start_line', 0),
                                'end_line': code_result.get('end_line', 0),
                                'type': code_result.get('type', 'unknown'),
                                'name': code_result.get('name', 'unknown'),
                            }
                            thinking_process.append(
                                f"[3.{i}.c] Successfully retrieved source code for '{ref}'"
                            )
                        else:
                            thinking_process.append(
                                f"[3.{i}.c] Could not retrieve source code: {code_result['error']}"
                            )
        else:
            thinking_process.append("[3] No significant Python references found to follow up on")

        # Step 4: Extract GitHub URLs from initial context too
        thinking_process.append("[4] Checking initial context for GitHub URLs...")
        initial_urls = self.reference_extractor.extract_github_urls(
            '\n'.join(initial_result['context_used'])
        )

        if initial_urls and not source_code_snippets:
            thinking_process.append(f"[4.a] Found {len(initial_urls)} GitHub URL(s) in initial context")
            # Try first URL if we haven't retrieved any code yet
            url = initial_urls[0]
            thinking_process.append(f"[4.b] Retrieving source code from: {url[:80]}...")
            code_result = self.get_source_code(url, context_lines=15)

            if not code_result.get('error'):
                source_code_snippets['_initial_context'] = {
                    'url': url,
                    'file_path': code_result.get('file_path', 'unknown'),
                    'code': code_result.get('code', ''),
                    'start_line': code_result.get('start_line', 0),
                    'end_line': code_result.get('end_line', 0),
                    'type': code_result.get('type', 'unknown'),
                    'name': code_result.get('name', 'unknown'),
                }
                thinking_process.append("[4.c] Successfully retrieved source code from initial context")

        thinking_process.append(
            f"[5] Complete! Followed {len(followed_references)} references, retrieved {len(source_code_snippets)} code snippets"
        )

        return {
            'answer': initial_result['answer'],
            'sources': initial_result['sources'],
            'context_used': initial_result['context_used'],
            'thinking_process': thinking_process,
            'followed_references': followed_references,
            'source_code': source_code_snippets,
        }

    def delete_document(self, doc_id: str) -> int:
        """
        Delete a document from the RAG system.

        Args:
            doc_id: Document ID to delete

        Returns:
            Number of chunks deleted
        """
        return self.vector_store.delete_by_doc_id(doc_id)

    def list_documents(self, tags: Optional[List[str]] = None) -> List[dict]:
        """
        List all documents in the RAG system.

        Args:
            tags: Optional list of tags to filter by

        Returns:
            List of document metadata
        """
        return self.vector_store.list_documents(tags=tags)

    def get_stats(self) -> dict:
        """
        Get statistics about the RAG system.

        Returns:
            Dictionary with system statistics
        """
        collection_info = self.vector_store.get_collection_info()
        documents = self.list_documents()

        return {
            "total_documents": len(documents),
            "total_chunks": collection_info["points_count"],
            "collection_name": collection_info["name"],
        }

    def get_tags(self) -> List[str]:
        """
        Get all unique tags across all documents.

        Returns:
            List of unique tags
        """
        return self.vector_store.get_all_tags()

    def get_document_sections(self, doc_id: str) -> List[dict]:
        """
        Get the section structure of a document.

        Args:
            doc_id: Document ID

        Returns:
            List of section information
        """
        return self.vector_store.get_document_sections(doc_id)

    def get_source_code(
        self,
        github_url: str,
        context_lines: int = 20,
        mode: str = 'full',
        method_name: Optional[str] = None,
    ) -> dict:
        """
        Retrieve source code from local Dagster repository using GitHub URL.

        Args:
            github_url: GitHub URL from documentation (e.g.,
                       https://github.com/dagster-io/dagster/blob/master/...)
            context_lines: Number of context lines to include (default: 20, for 'full' mode)
            mode: Retrieval mode - 'full', 'signature', 'outline', 'methods_list' (default: 'full')
            method_name: Specific method to extract from a class (optional)

        Returns:
            Dictionary with source code and metadata:
            {
                'github_url': 'https://...',
                'local_path': '/home/ubuntu/dagster/...',
                'line_number': 130,
                'code': 'def function_name(...):\\n    ...',
                'name': 'function_name',
                'type': 'function' | 'class' | 'context',
                'start_line': 130,
                'end_line': 150,
                'mode': 'full' | 'signature' | 'outline' | 'methods_list',
                'docstring': '...',
                'error': 'error message' (if failed)
            }
        """
        # Parse GitHub URL
        local_path, line_number = self.github_parser.github_url_to_local_path(github_url)

        if not local_path:
            return {
                'error': 'Invalid GitHub URL format',
                'github_url': github_url,
            }

        if not self.github_parser.validate_local_path(local_path):
            return {
                'error': f'Local file not found: {local_path}',
                'github_url': github_url,
                'local_path': str(local_path),
            }

        # Extract source code based on mode
        result = None

        if method_name:
            # Extract specific method from a class
            result = self.source_extractor.extract_class_method(
                local_path, line_number, method_name
            )
        elif mode == 'signature':
            result = self.source_extractor.extract_signature(local_path, line_number)
        elif mode == 'outline':
            result = self.source_extractor.extract_class_outline(local_path, line_number)
        elif mode == 'methods_list':
            result = self.source_extractor.extract_class_methods_list(local_path, line_number)
        else:  # mode == 'full'
            result = self.source_extractor.extract_at_line(
                local_path, line_number, context_lines
            )

        if result:
            result['github_url'] = github_url
            result['local_path'] = str(local_path)
            result['line_number'] = line_number
            if 'mode' not in result:
                result['mode'] = mode
            return result

        return {
            'error': 'Failed to extract source code',
            'github_url': github_url,
            'local_path': str(local_path),
            'line_number': line_number,
            'mode': mode,
        }

    def search_code(
        self,
        query: str,
        repo_name: Optional[str] = None,
        search_type: str = 'exact',
        limit: int = 10,
    ) -> List[dict]:
        """
        Search for code objects in the index.

        Args:
            query: Name or pattern to search for
            repo_name: Optional repository filter
            search_type: 'exact', 'prefix', or 'contains'
            limit: Maximum number of results

        Returns:
            List of matching code objects with metadata
        """
        if not self.code_index:
            return []

        results = []

        if search_type == 'exact':
            # Try qualified name first
            obj = self.code_index.get_by_qualified_name(query)
            if obj:
                results.append(obj)
            else:
                # Try simple name
                objs = self.code_index.get_by_name(query, repo_name)
                results.extend(objs)
        elif search_type == 'prefix':
            results = self.code_index.search_by_name_pattern(
                f"{query}%", repo_name, limit
            )
        elif search_type == 'contains':
            results = self.code_index.search_by_name_pattern(
                f"%{query}%", repo_name, limit
            )

        # Convert to dictionaries
        return [
            {
                'name': obj.name,
                'qualified_name': obj.qualified_name,
                'type': obj.type,
                'file_path': obj.file_path,
                'line_number': obj.line_number,
                'end_line_number': obj.end_line_number,
                'repo_name': obj.repo_name,
                'docstring': obj.docstring,
                'parent_class': obj.parent_class,
            }
            for obj in results[:limit]
        ]

    def get_source_code_from_index(
        self,
        name: str,
        repo_name: Optional[str] = None,
        context_lines: int = 20,
        mode: str = 'full',
    ) -> Optional[dict]:
        """
        Get source code using the code index.

        Args:
            name: Name or qualified name of the code object
            repo_name: Optional repository filter
            context_lines: Number of context lines for full mode
            mode: Retrieval mode (full, signature, outline, methods_list)

        Returns:
            Source code dictionary or None if not found
        """
        if not self.code_index:
            return None

        # Try qualified name first
        obj = self.code_index.get_by_qualified_name(name)

        # If not found, try simple name
        if not obj:
            objects = self.code_index.get_by_name(name, repo_name)
            if not objects:
                return None
            obj = objects[0]  # Use first match

        # Now extract source code from the file
        file_path = Path(obj.file_path)
        line_number = obj.line_number

        result = None
        if mode == 'signature':
            result = self.source_extractor.extract_signature(file_path, line_number)
        elif mode == 'outline':
            result = self.source_extractor.extract_class_outline(file_path, line_number)
        elif mode == 'methods_list':
            result = self.source_extractor.extract_class_methods_list(file_path, line_number)
        else:  # mode == 'full'
            result = self.source_extractor.extract_at_line(
                file_path, line_number, context_lines
            )

        if result:
            result['repo_name'] = obj.repo_name
            result['qualified_name'] = obj.qualified_name
            result['mode'] = mode
            result['from_index'] = True

        return result

    def query_with_code_index(
        self,
        question: str,
        top_k: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> dict:
        """
        Enhanced query that combines RAG with code index lookup.

        This method:
        1. Checks if the question is asking about specific code (e.g., "show me X")
        2. Uses code index for direct code lookups
        3. Uses RAG for documentation and conceptual questions
        4. Combines both for comprehensive answers

        Args:
            question: User's question
            top_k: Number of chunks to retrieve
            tags: Optional tags filter

        Returns:
            Dictionary with answer, sources, code, and metadata
        """
        # Try to extract code object name from question
        # Simple heuristic: look for capitalized words or dotted names
        import re

        code_patterns = [
            r'\b([A-Z][a-zA-Z0-9]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\b',  # Class.method
            r'`([^`]+)`',  # Backticks
        ]

        potential_code_refs = set()
        for pattern in code_patterns:
            matches = re.findall(pattern, question)
            potential_code_refs.update(matches)

        # Search code index for these references
        code_results = []
        for ref in potential_code_refs:
            if self.code_index:
                matches = self.search_code(ref, search_type='exact', limit=3)
                code_results.extend(matches)

        # Execute normal RAG query
        rag_result = self.query(question, top_k, tags)

        # Combine results
        return {
            'answer': rag_result['answer'],
            'sources': rag_result['sources'],
            'context_used': rag_result['context_used'],
            'code_matches': code_results,
            'used_code_index': len(code_results) > 0,
        }

    def smart_query(
        self,
        question: str,
        expand_detail: bool = False,
        repo_filter: Optional[str] = None,
    ) -> dict:
        """
        Smart query with tiered decision routing.

        This method automatically:
        1. Classifies the query type (symbol lookup, concept, how-to, etc.)
        2. Routes to optimal retrieval strategy (code index vs RAG)
        3. Executes strategy with progressive detail levels
        4. Synthesizes grounded answer with evidence

        Args:
            question: User's question
            expand_detail: Whether to get full detail (vs minimal/signature)
            repo_filter: Optional repository to filter (e.g., "dagster", "pyiceberg")

        Returns:
            Dictionary with:
            - answer: Synthesized answer
            - classification: Query type and extracted entities
            - strategy: Retrieval strategy used
            - tool_calls: All tool calls made with reasoning
            - confidence: Overall confidence score (0.0-1.0)
            - grounding: Evidence used (sources, code)
            - suggestions: Follow-up suggestions
        """
        from rag_server.smart_query import SmartQueryHandler

        handler = SmartQueryHandler(self)
        result = handler.execute(question, expand_detail, repo_filter)

        return {
            'answer': result.answer,
            'classification': result.classification,
            'strategy': result.strategy,
            'tool_calls': result.tool_calls,
            'confidence': result.confidence,
            'grounding': result.grounding,
            'suggestions': result.suggestions,
        }
