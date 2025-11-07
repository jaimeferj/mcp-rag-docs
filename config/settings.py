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
    use_qdrant_server: bool = True
    qdrant_url: str = "http://localhost:6333"
    qdrant_path: str = "./qdrant_storage"
    qdrant_collection_name: str = "documents"

    # Server Configuration
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000

    # Google AI Models
    embedding_model: str = "text-embedding-004"
    llm_model: str = "gemini-1.5-flash"

    # Rate Limiting Configuration
    google_api_rpm_limit: int = 15  # Requests per minute
    google_api_tpm_limit: int = 250000  # Tokens per minute
    google_api_rpd_limit: int = 1000  # Requests per day
    rate_limit_db_path: str = "./rate_limits.db"

    # Dagster Repository
    dagster_repo_path: str = "/home/ubuntu/dagster"

    # Code Index
    code_index_path: str = "./code_index.db"
    enable_code_index: bool = True

    # OpenAI-Compatible API
    enable_openai_api: bool = True
    openai_api_key: str = ""  # Optional API key for authentication

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()
