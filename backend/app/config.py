from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API
    anthropic_api_key: str = ""

    # CORS — comma-separated list of allowed origins
    cors_origins: list[str] = ["http://localhost:3000"]

    # Tax year used for RAG metadata filtering
    tax_year: int = 2025

    # LLM provider: "anthropic" | "ollama"
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:26b"

    # RAG — Chroma vector store path (relative to backend working directory)
    chroma_path: str = "chroma_db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
