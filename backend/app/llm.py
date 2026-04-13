"""
LLM factory — returns a LlamaIndex LLM instance.

The result is cached via lru_cache so the same object (and its connection
pool / token budget) is reused across requests.

Provider selection: set LLM_PROVIDER=anthropic (default) or ollama in .env.
"""
from functools import lru_cache

from llama_index.core.llms import LLM

from app.config import get_settings


@lru_cache
def get_llm() -> LLM:
    settings = get_settings()

    if settings.llm_provider == "ollama":
        from llama_index.llms.ollama import Ollama  # lazy import

        return Ollama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            request_timeout=180.0,
        )

    # Default: Anthropic claude-sonnet-4-6 with prompt caching
    from llama_index.llms.anthropic import Anthropic  # lazy import

    return Anthropic(
        model="claude-sonnet-4-6",
        api_key=settings.anthropic_api_key,
        max_tokens=4096,
        # Enable extended prompt caching for the system prompt.
        # llama-index-llms-anthropic passes this to the underlying SDK.
        default_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
    )
