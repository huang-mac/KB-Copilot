from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "KB Copilot API"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "kb_copilot"
    document_db_path: str = "data/kb_copilot.sqlite3"
    metadata_db_provider: Literal["sqlite", "mysql"] = "sqlite"
    mysql_dsn: str = ""

    minio_enabled: bool = False
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "admin"
    minio_secret_key: str = "admin123456"
    minio_bucket: str = "kb-copilot-documents"
    minio_secure: bool = False

    chunk_size: int = 700
    chunk_overlap: int = 120
    top_k: int = 5
    async_index_enabled: bool = True
    index_worker_poll_interval_seconds: float = 1.0
    index_worker_concurrency: int = 1
    chat_stream_enabled: bool = True
    metrics_enabled: bool = True
    rerank_enabled: bool = False

    embedding_provider: Literal["openai", "mock"] = "openai"
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    llm_provider: Literal["openai", "mock"] = "openai"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_timeout_seconds: float = 60.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
