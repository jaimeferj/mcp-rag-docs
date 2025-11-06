"""Qdrant vector store wrapper for document storage and retrieval."""

from typing import List, Optional
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
)


class VectorStore:
    """Wrapper for Qdrant vector database operations."""

    def __init__(
        self,
        path: str = "./qdrant_storage",
        collection_name: str = "documents",
        vector_size: int = 768,  # Google text-embedding-004 dimension
    ):
        """
        Initialize the Qdrant vector store.

        Args:
            path: Path to store Qdrant data
            collection_name: Name of the collection
            vector_size: Dimension of the embedding vectors
        """
        self.client = QdrantClient(path=path)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure the collection exists, create if it doesn't."""
        collections = self.client.get_collections().collections
        collection_names = [col.name for col in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=Distance.COSINE
                ),
            )

    def add_documents(
        self, texts: List[str], embeddings: List[List[float]], metadata: List[dict]
    ) -> List[str]:
        """
        Add documents to the vector store.

        Args:
            texts: List of text chunks
            embeddings: List of embedding vectors
            metadata: List of metadata dictionaries

        Returns:
            List of point IDs
        """
        points = []
        point_ids = []

        for text, embedding, meta in zip(texts, embeddings, metadata):
            point_id = str(uuid4())
            point_ids.append(point_id)

            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={"text": text, **meta},
            )
            points.append(point)

        self.client.upsert(collection_name=self.collection_name, points=points)
        return point_ids

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        doc_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        section_path: Optional[str] = None,
    ) -> List[dict]:
        """
        Search for similar documents with optional filtering.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            doc_id: Optional document ID to filter by
            tags: Optional list of tags to filter by (matches any)
            section_path: Optional section path to filter by (partial match)

        Returns:
            List of search results with text and metadata
        """
        # Build filter conditions
        filter_conditions = []

        if doc_id:
            filter_conditions.append(
                FieldCondition(key="doc_id", match=MatchValue(value=doc_id))
            )

        if tags:
            # Match documents that have any of the specified tags
            filter_conditions.append(
                FieldCondition(key="tags", match=MatchAny(any=tags))
            )

        if section_path:
            # Match documents where section_path contains the specified string
            # Note: Qdrant doesn't have built-in contains, so we use exact match
            # For partial matching, we'd need to use full-text search or filter in post-processing
            filter_conditions.append(
                FieldCondition(key="section_path", match=MatchValue(value=section_path))
            )

        query_filter = None
        if filter_conditions:
            query_filter = Filter(must=filter_conditions)

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=query_filter,
        )

        # If section_path was provided and we want partial matching, filter results
        filtered_results = results
        if section_path and not any(
            cond.key == "section_path" for cond in filter_conditions
        ):
            # Do partial match filtering in post-processing
            filtered_results = [
                r
                for r in results
                if section_path.lower() in r.payload.get("section_path", "").lower()
            ]

        return [
            {
                "text": result.payload.get("text", ""),
                "score": result.score,
                "metadata": {
                    k: v for k, v in result.payload.items() if k != "text"
                },
            }
            for result in filtered_results
        ]

    def delete_by_doc_id(self, doc_id: str) -> int:
        """
        Delete all chunks belonging to a document.

        Args:
            doc_id: Document ID to delete

        Returns:
            Number of points deleted
        """
        # Search for all points with this doc_id
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
            limit=10000,  # High limit to get all chunks
        )

        point_ids = [point.id for point in results[0]]

        if point_ids:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=point_ids,
            )

        return len(point_ids)

    def list_documents(self, tags: Optional[List[str]] = None) -> List[dict]:
        """
        List all unique documents in the store.

        Args:
            tags: Optional list of tags to filter by

        Returns:
            List of document metadata
        """
        # Build filter if tags provided
        scroll_filter = None
        if tags:
            scroll_filter = Filter(
                must=[FieldCondition(key="tags", match=MatchAny(any=tags))]
            )

        # Get all points
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=scroll_filter,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        # Extract unique documents
        documents = {}
        for point in results[0]:
            doc_id = point.payload.get("doc_id")
            if doc_id and doc_id not in documents:
                # Get tags as list (handle if stored as single tag or list)
                point_tags = point.payload.get("tags", [])
                if isinstance(point_tags, str):
                    point_tags = [point_tags]

                documents[doc_id] = {
                    "doc_id": doc_id,
                    "filename": point.payload.get("filename", "unknown"),
                    "file_type": point.payload.get("file_type", "unknown"),
                    "tags": point_tags,
                }

        return list(documents.values())

    def get_collection_info(self) -> dict:
        """Get information about the collection."""
        info = self.client.get_collection(collection_name=self.collection_name)
        return {
            "name": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
        }

    def get_all_tags(self) -> List[str]:
        """
        Get all unique tags across all documents.

        Returns:
            List of unique tags
        """
        # Get all points
        results = self.client.scroll(
            collection_name=self.collection_name,
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        # Collect all unique tags
        tags_set = set()
        for point in results[0]:
            point_tags = point.payload.get("tags", [])
            if isinstance(point_tags, str):
                tags_set.add(point_tags)
            elif isinstance(point_tags, list):
                tags_set.update(point_tags)

        return sorted(list(tags_set))

    def get_document_sections(self, doc_id: str) -> List[dict]:
        """
        Get all sections for a specific document.

        Args:
            doc_id: Document ID

        Returns:
            List of unique section paths with metadata
        """
        # Get all chunks for this document
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
            limit=10000,
            with_payload=True,
            with_vectors=False,
        )

        # Extract unique sections
        sections = {}
        for point in results[0]:
            section_path = point.payload.get("section_path", "Document")
            if section_path not in sections:
                sections[section_path] = {
                    "section_path": section_path,
                    "section_level": point.payload.get("section_level", 0),
                    "chunk_count": 0,
                }
            sections[section_path]["chunk_count"] += 1

        # Sort by section level and path
        return sorted(
            list(sections.values()), key=lambda x: (x["section_level"], x["section_path"])
        )
