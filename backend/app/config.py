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

    # RAG — HyDE: generate a hypothetical answer before embedding the query
    hyde_enabled: bool = False

    # RAG — number of chunks passed to the LLM after re-ranking
    # reduce for smaller models (e.g. 3–4 for 4B), increase for larger ones (8+)
    rag_top_n: int = 5

    # RAG — max characters per chunk passed to the LLM (0 = no limit)
    rag_chunk_max_chars: int = 800

    # Chat memory — max tokens kept in history sent to the LLM
    # reduce for smaller models (e.g. 1024–2048 for 4B)
    memory_token_limit: int = 2048


@lru_cache
def get_settings() -> Settings:
    return Settings()
