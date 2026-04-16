"""
Embeds child nodes into Chroma and persists all nodes into a SimpleDocumentStore.

Chroma (vector search):
  - Stores child nodes only — one per Absatz, with law/year/section metadata.
  - When a ParsedLaw has no child nodes (e.g. LStR Randnummern), parent nodes
    are stored instead.

SimpleDocumentStore (parent lookup for AutoMerging):
  - Persists ALL nodes (parent + children) to {chroma_path}_docstore.json.
  - Loaded by app/retriever.py in step 3 (AutoMergingRetriever).

Embedding model: intfloat/multilingual-e5-large with passage/query prefix.
"""
import logging
from pathlib import Path

import chromadb
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from ingest.parser import ParsedLaw

logger = logging.getLogger(__name__)

COLLECTION_NAME = "tax_law"
_DOCSTORE_SUFFIX = "_docstore.json"


def get_embed_model() -> HuggingFaceEmbedding:
    """Embedding model singleton (heavy — cache at call site if needed)."""
    return HuggingFaceEmbedding(
        model_name="intfloat/multilingual-e5-large",
        text_instruction="passage: ",
        query_instruction="query: ",
    )


def get_chroma_client(chroma_path: str) -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=chroma_path)


def _docstore_path(chroma_path: str) -> Path:
    """Sibling file to the Chroma directory: chroma_db → chroma_db_docstore.json"""
    p = Path(chroma_path)
    return p.parent / (p.name + _DOCSTORE_SUFFIX)


def store_documents(
    parsed: ParsedLaw,
    chroma_path: str,
    law: str,
    year: int,
) -> int:
    """
    Embed leaf nodes into Chroma and persist all nodes into the SimpleDocumentStore.

    Leaf nodes = child_nodes when present, parent_nodes otherwise.
    Returns the number of nodes embedded into Chroma.
    """
    leaf_nodes = parsed.child_nodes if parsed.child_nodes else parsed.parent_nodes

    if not leaf_nodes:
        logger.warning("No nodes to store for %s %d", law, year)
        return 0

    # ── Chroma: embed leaf nodes ───────────────────────────────────────────────
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
        logger.info("Deleted %d stale Chroma entries for %s %d", len(existing["ids"]), law, year)

    embed_model = get_embed_model()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    pipeline = IngestionPipeline(
        transformations=[embed_model],
        vector_store=vector_store,
    )
    pipeline.run(documents=leaf_nodes, show_progress=True)
    logger.info("Stored %d leaf nodes in Chroma for %s %d", len(leaf_nodes), law, year)

    # ── SimpleDocumentStore: persist all nodes (parents + children) ────────────
    ds_path = _docstore_path(chroma_path)

    if ds_path.exists():
        docstore = SimpleDocumentStore.from_persist_path(str(ds_path))
    else:
        docstore = SimpleDocumentStore()

    # Remove stale nodes for this (law, year) — IDs start with "{law}__{year}__"
    stale_prefix = f"{law}__{year}__"
    stale_ids = [nid for nid in docstore.docs if nid.startswith(stale_prefix)]
    for nid in stale_ids:
        docstore.delete_document(nid)
    if stale_ids:
        logger.info("Removed %d stale docstore entries for %s %d", len(stale_ids), law, year)

    docstore.add_documents(parsed.all_nodes)
    docstore.persist(str(ds_path))
    logger.info(
        "DocStore: %d nodes persisted for %s %d (path: %s)",
        len(parsed.all_nodes), law, year, ds_path,
    )

    return len(leaf_nodes)
