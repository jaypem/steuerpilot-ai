"""
Embeds Documents and stores them in the Chroma vector store.

Uses intfloat/multilingual-e5-large with the passage/query prefix convention:
  Storage  : "passage: " + text
  Retrieval: "query: "   + text  (handled in app/index.py)
"""
import logging

import chromadb
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.ingestion import IngestionPipeline
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

logger = logging.getLogger(__name__)

COLLECTION_NAME = "tax_law"


def get_embed_model() -> HuggingFaceEmbedding:
    """Embedding model singleton (heavy — cache at call site if needed)."""
    return HuggingFaceEmbedding(
        model_name="intfloat/multilingual-e5-large",
        text_instruction="passage: ",
        query_instruction="query: ",
    )


def get_chroma_client(chroma_path: str) -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=chroma_path)


def store_documents(
    documents: list[Document],
    chroma_path: str,
    law: str,
    year: int,
) -> int:
    """
    Embed and upsert *documents* into Chroma.  Already-existing nodes for
    the same (law, year) are deleted first to enable re-ingest.
    Returns the number of stored documents.
    """
    if not documents:
        logger.warning("No documents to store for %s %d", law, year)
        return 0

    client = get_chroma_client(chroma_path)
    collection = client.get_or_create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Delete existing entries for this (law, year) before re-ingest
    existing = collection.get(
        where={"$and": [{"law": {"$eq": law}}, {"year": {"$eq": year}}]},
        include=[],
    )
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        logger.info("Deleted %d stale entries for %s %d", len(existing["ids"]), law, year)

    embed_model = get_embed_model()
    vector_store = ChromaVectorStore(chroma_collection=collection)

    # IngestionPipeline with only the embedding step — no text splitting,
    # since each Document is already one paragraph.
    pipeline = IngestionPipeline(
        transformations=[embed_model],
        vector_store=vector_store,
    )
    pipeline.run(documents=documents, show_progress=True)

    logger.info("Stored %d documents for %s %d", len(documents), law, year)
    return len(documents)
