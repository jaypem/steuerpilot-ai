"""
Unit tests for app/reference_resolver.py.

Chroma is mocked — no vector store needed.
"""
from unittest.mock import MagicMock

import pytest
from llama_index.core.schema import NodeWithScore, TextNode

from app.reference_resolver import (
    MAX_DEPTH,
    extract_paragraph_numbers,
    resolve_references,
)


# ─── extract_paragraph_numbers ───────────────────────────────────────────────

def test_extract_single_para():
    refs = extract_paragraph_numbers("gemäß § 9 Abs. 1 EStG")
    assert "9" in refs


def test_extract_multiple_paras():
    refs = extract_paragraph_numbers("i.V.m. § 4 Abs. 5 und § 9 Abs. 1")
    assert "4" in refs
    assert "9" in refs


def test_extract_alpha_suffix():
    refs = extract_paragraph_numbers("nach § 21b EStG")
    assert "21b" in refs


def test_extract_multi_digit():
    refs = extract_paragraph_numbers("§ 100 AO")
    assert "100" in refs


def test_extract_no_para():
    refs = extract_paragraph_numbers("Kein Paragraf hier.")
    assert len(refs) == 0


def test_extract_deduplicates():
    refs = extract_paragraph_numbers("§ 9 und § 9 Abs. 2")
    assert refs.count("9") == 1 if isinstance(refs, list) else len(refs) == len(set(refs))


# ─── Helper: build mock nodes ─────────────────────────────────────────────────

def _node(
    node_id: str,
    text: str,
    paragraph: str = "",
    law: str = "EStG",
) -> NodeWithScore:
    return NodeWithScore(
        node=TextNode(
            text=text,
            id_=node_id,
            metadata={"law": law, "paragraph": paragraph, "year": 2025},
        ),
        score=1.0,
    )


def _mock_collection(ids=None, documents=None, metadatas=None):
    """Return a mock chromadb.Collection whose .get() returns given data."""
    col = MagicMock()
    col.get.return_value = {
        "ids": ids or [],
        "documents": documents or [],
        "metadatas": metadatas or [],
    }
    return col


# ─── resolve_references ──────────────────────────────────────────────────────

def test_no_references_returns_unchanged():
    nodes = [_node("n1", "Kein Paragrafverweis hier.", "§ 1")]
    col = _mock_collection()
    result = resolve_references(nodes, col, year=2025)
    assert result == nodes
    col.get.assert_not_called()


def test_already_retrieved_para_not_re_fetched():
    """If § 9 is already in context, its references should not trigger a new Chroma query."""
    nodes = [
        _node("n1", "Gemäß § 9 Abs. 1 …", "§ 9"),
        _node("n2", "Gemäß § 4 …", "§ 4"),
    ]
    col = _mock_collection()
    result = resolve_references(nodes, col, year=2025)
    # Both paragraphs are already present → no new nodes
    assert len(result) == 2
    col.get.assert_not_called()


def test_new_reference_fetched_from_chroma():
    """§ 9 references § 33 which is not yet retrieved → Chroma queried."""
    nodes = [_node("n1", "i.V.m. § 33 AO", "§ 9")]
    col = _mock_collection(
        ids=["n33"],
        documents=["§ 33 AO — außergewöhnliche Belastungen"],
        metadatas=[{"paragraph": "§ 33", "year": 2025}],
    )
    result = resolve_references(nodes, col, year=2025)
    assert len(result) == 2
    assert result[1].node.node_id == "n33"


def test_reference_defaults_to_same_law_when_no_law_is_explicit():
    nodes = [_node("n1", "i.V.m. § 33 Abs. 2", "§ 9", law="EStG")]
    col = _mock_collection(
        ids=["n33"],
        documents=["§ 33 EStG — außergewöhnliche Belastungen"],
        metadatas=[{"law": "EStG", "paragraph": "§ 33", "year": 2025}],
    )

    resolve_references(nodes, col, year=2025)

    where = col.get.call_args.kwargs["where"]
    assert {"law": {"$eq": "EStG"}} in where["$and"][1]["$and"]
    assert {"paragraph": {"$eq": "§ 33"}} in where["$and"][1]["$and"]


def test_explicit_law_disambiguates_same_paragraph_number():
    nodes = [_node("n1", "i.V.m. § 33 AO", "§ 9", law="EStG")]
    col = _mock_collection(
        ids=["ao-33"],
        documents=["§ 33 AO — Vollstreckung"],
        metadatas=[{"law": "AO", "paragraph": "§ 33", "year": 2025}],
    )

    resolve_references(nodes, col, year=2025)

    where = col.get.call_args.kwargs["where"]
    assert {"law": {"$eq": "AO"}} in where["$and"][1]["$and"]
    assert {"paragraph": {"$eq": "§ 33"}} in where["$and"][1]["$and"]


def test_non_law_sources_require_explicit_law_to_resolve():
    nodes = [_node("bfh-1", "i.V.m. § 33 Abs. 2", "VI R 32/20", law="BFH")]
    col = _mock_collection()

    result = resolve_references(nodes, col, year=2025)

    assert result == nodes
    col.get.assert_not_called()


def test_duplicate_node_id_not_added_twice():
    nodes = [_node("n1", "i.V.m. § 33 AO", "§ 9")]
    # Chroma returns n1 again (same id as already-retrieved)
    col = _mock_collection(
        ids=["n1"],
        documents=["duplicate"],
        metadatas=[{"paragraph": "§ 9", "year": 2025}],
    )
    result = resolve_references(nodes, col, year=2025)
    assert len(result) == 1  # n1 not added again


def test_max_depth_respected():
    """Recursion should stop at MAX_DEPTH even if references keep being found."""
    # Each new node references another paragraph → would recurse indefinitely
    # but MAX_DEPTH caps it.
    call_count = 0

    def get_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        new_id = f"n{call_count + 10}"
        new_para = f"§ {call_count + 100}"
        return {
            "ids": [new_id],
            "documents": [f"Text referencing § {call_count + 200}"],
            "metadatas": [{"paragraph": new_para, "year": 2025}],
        }

    col = MagicMock()
    col.get.side_effect = get_side_effect

    nodes = [_node("n1", "i.V.m. § 50", "§ 1")]
    resolve_references(nodes, col, year=2025)
    assert call_count <= MAX_DEPTH


def test_chroma_error_returns_original_nodes():
    """If Chroma raises an exception, return the original nodes unchanged."""
    nodes = [_node("n1", "i.V.m. § 33", "§ 9")]
    col = MagicMock()
    col.get.side_effect = RuntimeError("Chroma unavailable")
    result = resolve_references(nodes, col, year=2025)
    assert result == nodes


def test_reference_node_gets_neutral_score():
    nodes = [_node("n1", "i.V.m. § 33", "§ 9")]
    col = _mock_collection(
        ids=["n33"],
        documents=["§ 33 text"],
        metadatas=[{"paragraph": "§ 33", "year": 2025}],
    )
    result = resolve_references(nodes, col, year=2025)
    ref_node = next(n for n in result if n.node.node_id == "n33")
    assert ref_node.score == pytest.approx(0.5)
