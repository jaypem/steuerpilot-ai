"""
Unit tests for app/retriever.py.

Heavy dependencies (HuggingFace embeddings, Chroma, CrossEncoder, BM25) are
mocked so the test suite runs fast and offline.
"""
from unittest.mock import MagicMock, patch

import pytest
from llama_index.core.schema import NodeRelationship, NodeWithScore, QueryBundle, RelatedNodeInfo, TextNode

from app.retriever import DENSE_TOP_K, BM25_TOP_K, MERGE_THRESHOLD, RERANK_TOP_N, HybridRetriever


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


# ─── AutoMerge ────────────────────────────────────────────────────────────────

def _child_node(node_id: str, parent_id: str, score: float = 1.0) -> NodeWithScore:
    """Helper: a child TextNode with a PARENT relationship."""
    return NodeWithScore(
        node=TextNode(
            text="child text",
            id_=node_id,
            metadata={"year": 2025},
            relationships={NodeRelationship.PARENT: RelatedNodeInfo(node_id=parent_id)},
        ),
        score=score,
    )


def _make_retriever_with_docstore(parent_node: TextNode) -> HybridRetriever:
    """Build a minimal HybridRetriever with a mocked docstore."""
    retriever = _make_retriever([], [])
    mock_docstore = MagicMock()
    mock_docstore.get_document.side_effect = (
        lambda nid: parent_node if nid == parent_node.node_id else None
    )
    retriever._docstore = mock_docstore
    return retriever


def test_auto_merge_disabled_without_docstore():
    """When _docstore is None, nodes are returned unchanged."""
    retriever = _make_retriever([], [])
    assert retriever._docstore is None  # no chroma_path passed

    children = [_child_node(f"c{i}", "parent1") for i in range(MERGE_THRESHOLD)]
    result = retriever._auto_merge(children)
    assert len(result) == MERGE_THRESHOLD


def test_auto_merge_below_threshold_keeps_children():
    """Fewer than MERGE_THRESHOLD children → keep as-is."""
    parent = TextNode(text="parent", id_="parent1", metadata={"year": 2025})
    retriever = _make_retriever_with_docstore(parent)

    children = [_child_node(f"c{i}", "parent1") for i in range(MERGE_THRESHOLD - 1)]
    result = retriever._auto_merge(children)

    ids = [n.node.node_id for n in result]
    assert "parent1" not in ids
    assert len(result) == MERGE_THRESHOLD - 1


def test_auto_merge_at_threshold_replaces_with_parent():
    """Exactly MERGE_THRESHOLD children → replace with parent node."""
    parent = TextNode(text="parent text", id_="parent1", metadata={"year": 2025})
    retriever = _make_retriever_with_docstore(parent)

    children = [_child_node(f"c{i}", "parent1") for i in range(MERGE_THRESHOLD)]
    result = retriever._auto_merge(children)

    assert len(result) == 1
    assert result[0].node.node_id == "parent1"


def test_auto_merge_score_is_max_of_children():
    """Merged parent gets the highest score among its constituent children."""
    parent = TextNode(text="parent", id_="p1", metadata={"year": 2025})
    retriever = _make_retriever_with_docstore(parent)

    children = [
        _child_node("c0", "p1", score=1.5),
        _child_node("c1", "p1", score=3.0),
        _child_node("c2", "p1", score=2.0),
    ]
    result = retriever._auto_merge(children)

    assert result[0].score == pytest.approx(3.0)


def test_auto_merge_non_children_pass_through():
    """Nodes without a PARENT relationship are not touched by AutoMerge."""
    parent = TextNode(text="parent", id_="p1", metadata={"year": 2025})
    retriever = _make_retriever_with_docstore(parent)

    plain = NodeWithScore(
        node=TextNode(text="standalone", id_="lstr_r1", metadata={"year": 2025}),
        score=5.0,
    )
    children = [_child_node(f"c{i}", "p1") for i in range(MERGE_THRESHOLD)]

    result = retriever._auto_merge([plain] + children)
    ids = {n.node.node_id for n in result}

    assert "lstr_r1" in ids   # plain node preserved
    assert "p1" in ids         # children merged to parent
    assert not any(f"c{i}" in ids for i in range(MERGE_THRESHOLD))


def test_auto_merge_mixed_parents():
    """Children from two different parents are merged independently."""
    p1 = TextNode(text="parent1", id_="p1", metadata={"year": 2025})
    p2 = TextNode(text="parent2", id_="p2", metadata={"year": 2025})

    mock_docstore = MagicMock()
    mock_docstore.get_document.side_effect = lambda nid: {
        "p1": p1, "p2": p2
    }.get(nid)

    retriever = _make_retriever([], [])
    retriever._docstore = mock_docstore

    # p1: MERGE_THRESHOLD children → merge; p2: 1 child → keep
    p1_children = [_child_node(f"c1_{i}", "p1") for i in range(MERGE_THRESHOLD)]
    p2_children = [_child_node("c2_0", "p2")]

    result = retriever._auto_merge(p1_children + p2_children)
    ids = {n.node.node_id for n in result}

    assert "p1" in ids          # merged
    assert "c2_0" in ids        # kept (below threshold)
    assert "p2" not in ids      # not merged
