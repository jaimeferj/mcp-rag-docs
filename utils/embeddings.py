"""Google AI embeddings service for text vectorization."""

from typing import List, Optional

from utils.google_api_client import GoogleAPIClient


class GoogleEmbeddingService:
    """Service for generating embeddings using Google AI Studio with rate limiting."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "text-embedding-004",
        api_client: Optional[GoogleAPIClient] = None,
    ):
        """
        Initialize the Google embedding service.

        Args:
            api_key: Google AI Studio API key
            model_name: Name of the embedding model to use
            api_client: Optional GoogleAPIClient instance (will create if not provided)
        """
        self.model_name = model_name
        self.api_client = api_client if api_client is not None else GoogleAPIClient(api_key=api_key)

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            RateLimitExceededError: If rate limits would be exceeded
        """
        result = self.api_client.embed_content(
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

        Raises:
            RateLimitExceededError: If rate limits would be exceeded
        """
        result = self.api_client.embed_content(
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
