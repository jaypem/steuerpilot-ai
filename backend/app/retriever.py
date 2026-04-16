"""
Hybrid retriever: Dense (Chroma) + BM25 + Cross-Encoder re-ranking.

Pipeline per query:
  1. Dense retrieval via Chroma (multilingual-e5-large), top-30, year-filter
  2. BM25 retrieval over in-memory corpus for the same year, top-20
  3. Deduplicate by node_id
  4. Cross-encoder re-ranking (ms-marco-MiniLM-L-6-v2), top-8
  5. Reference resolution (app/reference_resolver.py)
"""
import logging
from functools import lru_cache
from typing import TYPE_CHECKING

import chromadb
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from llama_index.retrievers.bm25 import BM25Retriever

from app.reference_resolver import resolve_references

if TYPE_CHECKING:
    from llama_index.core import VectorStoreIndex

logger = logging.getLogger(__name__)

DENSE_TOP_K = 30   # mehr Kandidaten für den Cross-Encoder → besserer Recall
BM25_TOP_K = 20
RERANK_TOP_N = 8   # mehr Kontext für Claude bei komplexen Mehranfragen-Fragen


@lru_cache
def _get_reranker():
    """Load Cross-Encoder once and cache it."""
    from sentence_transformers import CrossEncoder
    logger.info("Loading cross-encoder/ms-marco-MiniLM-L-6-v2 …")
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def _nodes_from_chroma(
    collection: chromadb.Collection, year: int
) -> list[TextNode]:
    """Fetch all nodes for *year* from Chroma — used to build the BM25 corpus."""
    results = collection.get(
        where={"year": {"$eq": year}},
        include=["documents", "metadatas", "ids"],
    )
    nodes: list[TextNode] = []
    for doc_id, text, meta in zip(
        results.get("ids", []),
        results.get("documents", []) or [],
        results.get("metadatas", []) or [],
    ):
        if text:
            nodes.append(TextNode(text=text, id_=doc_id, metadata=meta or {}))
    return nodes


class HybridRetriever(BaseRetriever):
    """
    Dense + BM25 hybrid retriever with cross-encoder re-ranking and
    automatic §-reference resolution.
    """

    def __init__(
        self,
        index: "VectorStoreIndex",
        chroma_collection: chromadb.Collection,
        year: int,
    ) -> None:
        self._year = year
        self._chroma_collection = chroma_collection

        # Dense retriever with year metadata filter
        self._dense = index.as_retriever(
            similarity_top_k=DENSE_TOP_K,
            filters=MetadataFilters(
                filters=[MetadataFilter(key="year", value=year, operator="==")]
            ),
        )

        # BM25 over the full corpus for this year
        corpus_nodes = _nodes_from_chroma(chroma_collection, year)
        if corpus_nodes:
            self._bm25: BM25Retriever | None = BM25Retriever.from_defaults(
                nodes=corpus_nodes,
                similarity_top_k=BM25_TOP_K,
            )
        else:
            logger.warning("No corpus nodes for year %d — BM25 disabled.", year)
            self._bm25 = None

        super().__init__()

    # ── LlamaIndex retriever interface ────────────────────────────────────────

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        # 1. Dense
        dense_nodes = self._dense.retrieve(query_bundle)

        # 2. BM25
        bm25_nodes: list[NodeWithScore] = []
        if self._bm25:
            try:
                bm25_nodes = self._bm25.retrieve(query_bundle)
            except Exception as exc:
                logger.warning("BM25 retrieval failed: %s", exc)

        # 3. Deduplicate (dense scores take precedence)
        seen: set[str] = set()
        merged: list[NodeWithScore] = []
        for n in dense_nodes + bm25_nodes:
            nid = n.node.node_id
            if nid not in seen:
                seen.add(nid)
                merged.append(n)

        if not merged:
            return []

        # 4. Cross-encoder re-ranking
        merged = self._rerank(query_bundle.query_str, merged)

        # 5. Reference resolution
        merged = resolve_references(merged, self._chroma_collection, self._year)

        return merged

    async def _aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        # LlamaIndex falls back to sync _retrieve when async is not overridden
        return self._retrieve(query_bundle)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _rerank(
        self, query: str, nodes: list[NodeWithScore]
    ) -> list[NodeWithScore]:
        try:
            reranker = _get_reranker()
            pairs = [(query, n.node.get_content()) for n in nodes]
            scores = reranker.predict(pairs)
            for node, score in zip(nodes, scores):
                node.score = float(score)
            nodes.sort(key=lambda n: n.score or 0.0, reverse=True)
            return nodes[:RERANK_TOP_N]
        except Exception as exc:
            logger.warning("Re-ranking failed (%s) — using dense order.", exc)
            return nodes[:RERANK_TOP_N]
