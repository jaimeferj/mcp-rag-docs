"""Application settings and configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google AI Studio API Key
    google_api_key: str

    # RAG Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_results: int = 5

    # Qdrant Configuration
    qdrant_path: str = "./qdrant_storage"
    qdrant_collection_name: str = "documents"

    # Server Configuration
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000

    # Google AI Models
    embedding_model: str = "text-embedding-004"
    llm_model: str = "gemini-1.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()
