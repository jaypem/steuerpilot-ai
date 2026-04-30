"""
Hybrid retriever: Dense (Chroma) + BM25 + Cross-Encoder re-ranking + AutoMerge.

Pipeline per query:
  1. Dense retrieval via Chroma (multilingual-e5-large), top-30, year-filter
  2. BM25 retrieval over in-memory corpus for the same year, top-20
  3. Deduplicate by node_id
  4. Cross-encoder re-ranking (ms-marco-MiniLM-L-6-v2), top-5 by default
  5. AutoMerge: child nodes → parent paragraph when ≥ MERGE_THRESHOLD
     children of the same § appear in the result set
  6. Reference resolution (app/reference_resolver.py)
"""

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, cast

from chromadb.api.models.Collection import Collection
from chromadb.api.types import Where
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import (
    BaseNode,
    NodeRelationship,
    NodeWithScore,
    QueryBundle,
    RelatedNodeInfo,
    TextNode,
)
from llama_index.core.storage.docstore import BaseDocumentStore, SimpleDocumentStore
from llama_index.core.vector_stores import (
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)
from llama_index.retrievers.bm25 import BM25Retriever

from app.reference_resolver import resolve_references
from ingest.store import docstore_path

if TYPE_CHECKING:
    from llama_index.core import VectorStoreIndex

logger = logging.getLogger(__name__)

DENSE_TOP_K = 50  # mehr Kandidaten für den Cross-Encoder → besserer Recall
BM25_TOP_K = 20
RERANK_TOP_N = 5
MERGE_THRESHOLD = 3  # min. Child-Treffer eines § um zum Parent zusammenzuführen


@lru_cache
def _get_reranker():
    """Load Cross-Encoder once and cache it."""
    from sentence_transformers import CrossEncoder

    logger.info("Loading cross-encoder/ms-marco-MiniLM-L-6-v2 …")
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def _nodes_from_chroma(collection: Collection, year: int) -> list[BaseNode]:
    """Fetch all nodes for *year* from Chroma — used to build the BM25 corpus."""
    where = cast(Where, {"year": {"$eq": year}})
    results = collection.get(
        where=where,
        include=["documents", "metadatas"],
    )
    nodes: list[BaseNode] = []
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
    Dense + BM25 hybrid retriever with cross-encoder re-ranking, AutoMerge,
    and automatic §-reference resolution.
    """

    def __init__(
        self,
        index: "VectorStoreIndex",
        chroma_collection: Collection,
        year: int,
        chroma_path: str = "",
        automerge: bool = True,
        rerank_top_n: int = RERANK_TOP_N,
        chunk_max_chars: int = 0,
        use_hyde: bool = False,
    ) -> None:
        self._year = year
        self._chroma_collection = chroma_collection
        self._automerge = automerge
        self._rerank_top_n = rerank_top_n
        self._chunk_max_chars = chunk_max_chars
        self._use_hyde = use_hyde

        # Dense retriever with year metadata filter
        self._dense = index.as_retriever(
            similarity_top_k=DENSE_TOP_K,
            filters=MetadataFilters(
                filters=[
                    MetadataFilter(
                        key="year",
                        value=year,
                        operator=FilterOperator.EQ,
                    )
                ]
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

        # SimpleDocumentStore for AutoMerge parent lookup
        self._docstore: BaseDocumentStore | None = None
        if chroma_path:
            ds_path = docstore_path(chroma_path)
            if ds_path.exists():
                try:
                    self._docstore = SimpleDocumentStore.from_persist_path(str(ds_path))
                    logger.info(
                        "AutoMerge: docstore loaded (%d nodes) from %s",
                        len(self._docstore.docs),
                        ds_path,
                    )
                except Exception as exc:
                    logger.warning("AutoMerge: could not load docstore: %s", exc)
            else:
                logger.warning(
                    "AutoMerge: no docstore found at %s — re-run 'steuerpilot ingest' "
                    "to enable parent merging.",
                    ds_path,
                )

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

        # 5. AutoMerge: child nodes → parent when ≥ MERGE_THRESHOLD children matched
        if self._automerge:
            merged = self._auto_merge(merged)

        # 6. Reference resolution
        merged = resolve_references(merged, self._chroma_collection, self._year)

        # 7. Chunk truncation
        if self._chunk_max_chars > 0:
            merged = self._truncate(merged)

        return merged

    async def _aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        if self._use_hyde:
            from app.hyde import expand_query
            from app.llm import get_llm

            expanded = await expand_query(query_bundle.query_str, get_llm())
            query_bundle = QueryBundle(query_str=expanded)
        return self._retrieve(query_bundle)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _truncate(self, nodes: list[NodeWithScore]) -> list[NodeWithScore]:
        result = []
        for n in nodes:
            text = n.node.get_content()
            if len(text) > self._chunk_max_chars:
                truncated = TextNode(
                    text=text[: self._chunk_max_chars],
                    id_=n.node.node_id,
                    metadata=n.node.metadata,
                )
                result.append(NodeWithScore(node=truncated, score=n.score))
            else:
                result.append(n)
        return result

    def _rerank(self, query: str, nodes: list[NodeWithScore]) -> list[NodeWithScore]:
        try:
            reranker = _get_reranker()
            pairs = [(query, n.node.get_content()) for n in nodes]
            scores = reranker.predict(pairs)
            for node, score in zip(nodes, scores):
                node.score = float(score)
            nodes.sort(key=lambda n: n.score or 0.0, reverse=True)
            return nodes[: self._rerank_top_n]
        except Exception as exc:
            logger.warning("Re-ranking failed (%s) — using dense order.", exc)
            return nodes[: self._rerank_top_n]

    def _auto_merge(self, nodes: list[NodeWithScore]) -> list[NodeWithScore]:
        """
        Replace groups of ≥ MERGE_THRESHOLD child nodes that share the same parent
        with the parent node itself. Score of merged parent = max child score.

        Nodes without a PARENT relationship (e.g. LStR Randnummern, already-merged
        parents, or pre-hierarchy index entries) pass through unchanged.
        """
        if not self._docstore:
            return nodes

        # Partition into children-by-parent and pass-through nodes
        by_parent: dict[str, list[NodeWithScore]] = {}
        pass_through: list[NodeWithScore] = []

        for n in nodes:
            parent_rel = n.node.relationships.get(NodeRelationship.PARENT)
            if isinstance(parent_rel, RelatedNodeInfo):
                by_parent.setdefault(parent_rel.node_id, []).append(n)
            else:
                pass_through.append(n)

        result: list[NodeWithScore] = list(pass_through)

        for parent_id, children in by_parent.items():
            if len(children) >= MERGE_THRESHOLD:
                try:
                    parent_doc = self._docstore.get_document(parent_id)
                    if parent_doc is not None:
                        max_score = max(c.score or 0.0 for c in children)
                        result.append(NodeWithScore(node=parent_doc, score=max_score))
                        logger.debug(
                            "AutoMerge: %d children of %s → parent (score %.3f)",
                            len(children),
                            parent_id,
                            max_score,
                        )
                        continue
                except Exception as exc:
                    logger.warning(
                        "AutoMerge: could not load parent %s: %s", parent_id, exc
                    )
            # Below threshold or load failed — keep children
            result.extend(children)

        result.sort(key=lambda n: n.score or 0.0, reverse=True)
        return result
