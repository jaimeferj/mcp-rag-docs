"""RAG system for document storage and retrieval-augmented generation."""

from pathlib import Path
from typing import List, Optional

import google.generativeai as genai

from config.settings import settings
from utils.document_processor import DocumentProcessor
from utils.embeddings import GoogleEmbeddingService
from utils.hierarchical_chunker import HierarchicalChunker
from utils.vector_store import VectorStore


class RAGSystem:
    """Retrieval-Augmented Generation system."""

    def __init__(self):
        """Initialize the RAG system with all components."""
        # Initialize services
        self.embedding_service = GoogleEmbeddingService(
            api_key=settings.google_api_key,
            model_name=settings.embedding_model,
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

        # Initialize Google AI for generation
        genai.configure(api_key=settings.google_api_key)
        self.llm_model = genai.GenerativeModel(settings.llm_model)

    async def add_document(
        self, file_path: str | Path, content: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> dict:
        """
        Add a document to the RAG system.

        Args:
            file_path: Path to the document
            content: Optional pre-loaded content
            tags: Optional list of tags for categorization

        Returns:
            Dictionary with document info, tags, and number of chunks
        """
        tags = tags or []

        # Process document
        doc_info = await self.document_processor.process_document(file_path, content)

        # Determine if this is markdown for hierarchical chunking
        is_markdown = doc_info["file_type"] == "markdown"

        # Chunk the text using hierarchical chunker
        chunks = self.chunker.chunk_with_metadata(
            text=doc_info["content"],
            doc_id=doc_info["doc_id"],
            is_markdown=is_markdown,
            extra_metadata={
                "filename": doc_info["filename"],
                "file_type": doc_info["file_type"],
                "tags": tags,
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

        # Generate answer using LLM
        prompt = self._build_prompt(question, context)
        response = self.llm_model.generate_content(prompt)

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
