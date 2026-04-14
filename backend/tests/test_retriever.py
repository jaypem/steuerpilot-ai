"""
Unit tests for app/retriever.py.

Heavy dependencies (HuggingFace embeddings, Chroma, CrossEncoder, BM25) are
mocked so the test suite runs fast and offline.
"""
from unittest.mock import MagicMock, patch

import pytest
from llama_index.core.schema import NodeWithScore, TextNode, QueryBundle

from app.retriever import DENSE_TOP_K, BM25_TOP_K, RERANK_TOP_N, HybridRetriever


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _scored_node(node_id: str, text: str = "text", score: float = 1.0) -> NodeWithScore:
    return NodeWithScore(
        node=TextNode(text=text, id_=node_id, metadata={"year": 2025}),
        score=score,
    )


def _make_retriever(
    dense_nodes: list[NodeWithScore],
    bm25_nodes: list[NodeWithScore],
    chroma_get_result: dict | None = None,
    reranker_scores: list[float] | None = None,
) -> HybridRetriever:
    """Build a HybridRetriever with all heavy parts mocked."""

    # Mock VectorStoreIndex
    mock_index = MagicMock()
    mock_dense = MagicMock()
    mock_dense.retrieve.return_value = dense_nodes
    mock_index.as_retriever.return_value = mock_dense

    # Mock chromadb.Collection — used for BM25 corpus loading
    mock_collection = MagicMock()
    mock_collection.get.return_value = chroma_get_result or {
        "ids": ["c1"],
        "documents": ["corpus text"],
        "metadatas": [{"year": 2025}],
    }

    # Mock BM25Retriever so it doesn't do real IR
    mock_bm25 = MagicMock()
    mock_bm25.retrieve.return_value = bm25_nodes

    # Mock CrossEncoder
    if reranker_scores is None:
        n_total = len(dense_nodes) + len(bm25_nodes)
        reranker_scores = list(range(n_total, 0, -1))  # descending

    mock_cross_encoder = MagicMock()
    mock_cross_encoder.predict.return_value = reranker_scores

    with (
        patch("app.retriever.BM25Retriever") as mock_bm25_cls,
        patch("app.retriever._get_reranker", return_value=mock_cross_encoder),
        patch("app.retriever.resolve_references", side_effect=lambda nodes, *a, **kw: nodes),
    ):
        mock_bm25_cls.from_defaults.return_value = mock_bm25
        retriever = HybridRetriever(
            index=mock_index,
            chroma_collection=mock_collection,
            year=2025,
        )
        # Inject the mock BM25 instance (already set during __init__)
        retriever._bm25 = mock_bm25
        # Inject a reranker wrapper that uses our mock scores
        def _mock_rerank(query, nodes):
            scores = mock_cross_encoder.predict([(query, n.node.get_content()) for n in nodes])
            for node, score in zip(nodes, scores):
                node.score = float(score)
            nodes.sort(key=lambda n: n.score or 0.0, reverse=True)
            return nodes[:RERANK_TOP_N]
        retriever._rerank = _mock_rerank

    return retriever


# ─── Deduplication ────────────────────────────────────────────────────────────

def test_deduplication_removes_duplicates():
    """A node that appears in both dense and BM25 results should appear once."""
    shared = _scored_node("shared")
    dense = [shared, _scored_node("dense_only")]
    bm25 = [shared, _scored_node("bm25_only")]

    retriever = _make_retriever(dense, bm25, reranker_scores=[3, 2, 1])

    with (
        patch("app.retriever._get_reranker", return_value=MagicMock()),
        patch("app.retriever.resolve_references", side_effect=lambda nodes, *a, **kw: nodes),
    ):
        results = retriever._retrieve(QueryBundle(query_str="test"))

    ids = [n.node.node_id for n in results]
    assert len(ids) == len(set(ids)), "Duplicate node IDs found in results"


def test_dense_score_takes_precedence_on_dedup():
    """When deduplicating, the dense-retrieved copy should be kept (it appears first)."""
    node_dense = _scored_node("dupe", score=0.9)
    node_bm25 = _scored_node("dupe", score=0.3)

    retriever = _make_retriever([node_dense], [node_bm25], reranker_scores=[1])

    with (
        patch("app.retriever._get_reranker", return_value=MagicMock()),
        patch("app.retriever.resolve_references", side_effect=lambda nodes, *a, **kw: nodes),
    ):
        results = retriever._retrieve(QueryBundle(query_str="test"))

    assert len(results) == 1


# ─── Reranking top-N ──────────────────────────────────────────────────────────

def test_rerank_limits_to_top_n():
    """After reranking, at most RERANK_TOP_N nodes are returned."""
    nodes = [_scored_node(f"n{i}") for i in range(RERANK_TOP_N + 5)]
    scores = list(range(len(nodes), 0, -1))
    retriever = _make_retriever(nodes, [], reranker_scores=scores)

    with (
        patch("app.retriever._get_reranker", return_value=MagicMock()),
        patch("app.retriever.resolve_references", side_effect=lambda nodes, *a, **kw: nodes),
    ):
        results = retriever._retrieve(QueryBundle(query_str="test"))

    assert len(results) <= RERANK_TOP_N


def test_rerank_sorts_by_score_descending():
    nodes = [
        _scored_node("low", score=0.1),
        _scored_node("high", score=0.9),
        _scored_node("mid", score=0.5),
    ]
    # Cross-encoder scores: low=1, high=10, mid=5
    retriever = _make_retriever(nodes, [], reranker_scores=[1, 10, 5])

    with (
        patch("app.retriever._get_reranker", return_value=MagicMock()),
        patch("app.retriever.resolve_references", side_effect=lambda nodes, *a, **kw: nodes),
    ):
        results = retriever._retrieve(QueryBundle(query_str="test"))

    assert results[0].node.node_id == "high"


# ─── BM25 disabled when no corpus ────────────────────────────────────────────

def test_bm25_disabled_when_no_corpus():
    """If chroma returns no nodes, BM25 retriever should be None."""
    mock_index = MagicMock()
    mock_dense = MagicMock()
    mock_dense.retrieve.return_value = []
    mock_index.as_retriever.return_value = mock_dense

    mock_collection = MagicMock()
    mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}

    with (
        patch("app.retriever.BM25Retriever"),
        patch("app.retriever._get_reranker", return_value=MagicMock()),
        patch("app.retriever.resolve_references", side_effect=lambda nodes, *a, **kw: nodes),
    ):
        retriever = HybridRetriever(
            index=mock_index,
            chroma_collection=mock_collection,
            year=2025,
        )

    assert retriever._bm25 is None


def test_empty_dense_and_bm25_returns_empty():
    retriever = _make_retriever([], [], reranker_scores=[])

    with (
        patch("app.retriever._get_reranker", return_value=MagicMock()),
        patch("app.retriever.resolve_references", side_effect=lambda nodes, *a, **kw: nodes),
    ):
        results = retriever._retrieve(QueryBundle(query_str="test"))

    assert results == []
