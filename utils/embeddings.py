"""Google AI embeddings service for text vectorization."""

from typing import List

import google.generativeai as genai


class GoogleEmbeddingService:
    """Service for generating embeddings using Google AI Studio."""

    def __init__(self, api_key: str, model_name: str = "text-embedding-004"):
        """
        Initialize the Google embedding service.

        Args:
            api_key: Google AI Studio API key
            model_name: Name of the embedding model to use
        """
        genai.configure(api_key=api_key)
        self.model_name = model_name

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        result = genai.embed_content(
            model=f"models/{self.model_name}",
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a query.

        Args:
            query: Query text to embed

        Returns:
            Embedding vector as list of floats
        """
        result = genai.embed_content(
            model=f"models/{self.model_name}",
            content=query,
            task_type="retrieval_query",
        )
        return result["embedding"]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = self.embed_text(text)
            embeddings.append(embedding)
        return embeddings
