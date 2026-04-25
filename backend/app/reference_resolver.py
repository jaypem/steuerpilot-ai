"""
Verweis-Auflöser — resolves §-cross-references in retrieved law chunks.

German tax law is full of references like:
  "i.V.m. § 9 Abs. 1 EStG"
  "nach § 4 Abs. 5 Satz 1 Nr. 6b"
  "gemäß § 23 EStG"

After the initial retrieval the resolver extracts all such references,
fetches the referenced paragraphs from Chroma (if not already retrieved),
and appends them to the context — up to MAX_DEPTH levels deep.
"""

import logging
import re
from collections.abc import Mapping
from typing import Any

import chromadb
from llama_index.core.schema import NodeWithScore, TextNode

logger = logging.getLogger(__name__)

MAX_DEPTH = 2  # maximum recursion depth for reference chasing
_RESOLVABLE_LAWS = {"EStG", "EStDV", "AO", "UStG", "SolzG", "GewStG", "KStG", "ErbStG", "ArbNErfG"}

# Pattern captures the paragraph number after "§", e.g. "§ 4", "§ 9a", "§ 21b"
_PARA_PATTERN = re.compile(r"§\s*(\d+[a-zA-Z]?)")
_LAW_PATTERN = re.compile(r"\b(EStG|EStDV|AO|UStG|SolzG|GewStG|KStG|ErbStG|ArbNErfG)\b")

# Common trigger phrases that indicate a cross-reference
_REF_TRIGGERS = re.compile(
    r"(?:i\.V\.m\.|in Verbindung mit|nach|gemäß|§§?|vgl\.|siehe)",
    re.IGNORECASE,
)


def extract_paragraph_numbers(text: str) -> set[str]:
    """Return all paragraph numbers mentioned in *text* (e.g. {"4", "9", "21b"})."""
    return set(_PARA_PATTERN.findall(text))


def _meta_text(meta: Mapping[str, Any], key: str) -> str:
    value = meta.get(key)
    return value if isinstance(value, str) else ""


def _extract_references(text: str, default_law: str | None) -> set[tuple[str, str]]:
    """Extract paragraph references as (paragraph_number, law) pairs."""
    references: set[tuple[str, str]] = set()

    for match in _PARA_PATTERN.finditer(text):
        para_num = match.group(1)
        tail = text[match.end() :].split("§", 1)[0][:80]
        law_match = _LAW_PATTERN.search(tail)
        law = law_match.group(1) if law_match else default_law
        if law:
            references.add((para_num, law))

    return references


def resolve_references(
    initial_nodes: list[NodeWithScore],
    chroma_collection: chromadb.Collection,
    year: int,
    depth: int = 0,
) -> list[NodeWithScore]:
    """
    Recursively resolve §-references found in *initial_nodes*.

    Already-retrieved node IDs are tracked to avoid duplicates.
    Returns *initial_nodes* extended with all referenced paragraphs.
    """
    if depth >= MAX_DEPTH:
        return initial_nodes

    seen_ids: set[str] = {n.node.node_id for n in initial_nodes}
    seen_refs: set[tuple[str, str]] = set()
    for node in initial_nodes:
        law = _meta_text(node.node.metadata, "law")
        paragraph = _meta_text(node.node.metadata, "paragraph")
        if law in _RESOLVABLE_LAWS and paragraph.startswith("§"):
            seen_refs.add((law, paragraph))

    # Collect all paragraph references mentioned in the retrieved text.
    referenced: set[tuple[str, str]] = set()
    for node in initial_nodes:
        text = node.node.get_content()
        law = _meta_text(node.node.metadata, "law")
        default_law = law if law in _RESOLVABLE_LAWS else None
        for para_num, ref_law in _extract_references(text, default_law):
            candidate = (ref_law, f"§ {para_num}")
            if candidate not in seen_refs:
                referenced.add((para_num, ref_law))

    if not referenced:
        return initial_nodes

    # Build a Chroma filter that keeps paragraph and law tied together.
    ref_filters = [
        {
            "$and": [
                {"law": {"$eq": law}},
                {"paragraph": {"$eq": f"§ {para_num}"}},
            ]
        }
        for para_num, law in sorted(referenced)
    ]
    if len(ref_filters) == 1:
        where_clause: dict[str, Any] = {"$and": [{"year": {"$eq": year}}, ref_filters[0]]}
    else:
        where_clause = {
            "$and": [
                {"year": {"$eq": year}},
                {"$or": ref_filters},
            ]
        }

    try:
        results = chroma_collection.get(
            where=where_clause,
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        logger.warning("Reference resolution query failed: %s", exc)
        return initial_nodes

    new_nodes: list[NodeWithScore] = []
    for doc_id, text, meta in zip(
        results.get("ids", []),
        results.get("documents", []) or [],
        results.get("metadatas", []) or [],
    ):
        if doc_id in seen_ids:
            continue
        node = NodeWithScore(
            node=TextNode(text=text or "", id_=doc_id, metadata=meta or {}),
            score=0.5,  # neutral score for reference-resolved nodes
        )
        new_nodes.append(node)
        seen_ids.add(doc_id)
        law = _meta_text(meta or {}, "law")
        paragraph = _meta_text(meta or {}, "paragraph")
        if law in _RESOLVABLE_LAWS and paragraph.startswith("§"):
            seen_refs.add((law, paragraph))

    if not new_nodes:
        return initial_nodes

    logger.debug(
        "Reference resolver depth=%d: added %d nodes for %s",
        depth,
        len(new_nodes),
        referenced,
    )

    combined = initial_nodes + new_nodes
    # Recurse to chase references within the newly added nodes
    return resolve_references(combined, chroma_collection, year, depth + 1)
