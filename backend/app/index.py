"""
LlamaIndex VectorStoreIndex factory backed by Chroma.

The embedding model and Chroma client are cached so they survive
multiple requests without re-loading the ~560 MB model each time.
"""
import logging
from functools import lru_cache

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from ingest.store import COLLECTION_NAME

logger = logging.getLogger(__name__)


@lru_cache
def get_embed_model() -> HuggingFaceEmbedding:
    """Shared embedding model — loads once, lives for the process lifetime."""
    logger.info("Loading intfloat/multilingual-e5-large …")
    return HuggingFaceEmbedding(
        model_name="intfloat/multilingual-e5-large",
        text_instruction="passage: ",
        query_instruction="query: ",
    )


def has_indexed_data(chroma_path: str) -> bool:
    """Return True if the Chroma collection exists and has at least one entry."""
    try:
        client = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_collection(COLLECTION_NAME)
        return collection.count() > 0
    except Exception:
        return False


def get_index(chroma_path: str) -> VectorStoreIndex:
    """
    Load a VectorStoreIndex from Chroma.
    Raises RuntimeError if no data has been ingested yet.
    """
    if not has_indexed_data(chroma_path):
        raise RuntimeError(
            "Kein RAG-Index gefunden. "
            "Bitte zuerst 'uv run steuerpilot ingest --year YYYY' ausführen."
        )

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    return VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=get_embed_model(),
    )
