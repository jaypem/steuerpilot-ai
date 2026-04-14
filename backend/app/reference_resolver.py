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

import chromadb
from llama_index.core.schema import NodeWithScore, TextNode

logger = logging.getLogger(__name__)

MAX_DEPTH = 2  # maximum recursion depth for reference chasing

# Pattern captures the paragraph number after "§", e.g. "§ 4", "§ 9a", "§ 21b"
_PARA_PATTERN = re.compile(r"§\s*(\d+[a-zA-Z]?)")

# Common trigger phrases that indicate a cross-reference
_REF_TRIGGERS = re.compile(
    r"(?:i\.V\.m\.|in Verbindung mit|nach|gemäß|§§?|vgl\.|siehe)",
    re.IGNORECASE,
)


def extract_paragraph_numbers(text: str) -> set[str]:
    """Return all paragraph numbers mentioned in *text* (e.g. {"4", "9", "21b"})."""
    return set(_PARA_PATTERN.findall(text))


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
    seen_paras: set[str] = {
        n.node.metadata.get("paragraph", "") for n in initial_nodes
    }

    # Collect all paragraph numbers referenced in the retrieved text
    referenced: set[str] = set()
    for node in initial_nodes:
        text = node.node.get_content()
        for para_num in extract_paragraph_numbers(text):
            # Skip paragraphs we already have
            candidate = f"§ {para_num}"
            if candidate not in seen_paras:
                referenced.add(para_num)

    if not referenced:
        return initial_nodes

    # Build Chroma filter for referenced paragraphs
    # Chroma's $in operator checks if field value is in a list
    para_filters = [{"paragraph": {"$eq": f"§ {p}"}} for p in referenced]
    if len(para_filters) == 1:
        where_clause: dict = {
            "$and": [{"year": {"$eq": year}}, para_filters[0]]
        }
    else:
        where_clause = {
            "$and": [
                {"year": {"$eq": year}},
                {"$or": para_filters},
            ]
        }

    try:
        results = chroma_collection.get(
            where=where_clause,
            include=["documents", "metadatas", "ids"],
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
            node=TextNode(text=text or "", node_id=doc_id, metadata=meta or {}),
            score=0.5,  # neutral score for reference-resolved nodes
        )
        new_nodes.append(node)
        seen_ids.add(doc_id)
        seen_paras.add((meta or {}).get("paragraph", ""))

    if not new_nodes:
        return initial_nodes

    logger.debug(
        "Reference resolver depth=%d: added %d nodes for %s",
        depth, len(new_nodes), referenced,
    )

    combined = initial_nodes + new_nodes
    # Recurse to chase references within the newly added nodes
    return resolve_references(combined, chroma_collection, year, depth + 1)
