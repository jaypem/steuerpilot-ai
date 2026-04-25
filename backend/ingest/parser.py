"""
Parses gesetze-im-internet.de XML into a two-level node hierarchy.

XML structure (gesetze-im-internet.de DTD 1.01):
  <norm>
    <metadaten>
      <enbez>§ 4</enbez>           ← paragraph reference
      <titel>Gewinnbegriff…</titel> ← optional title
    </metadaten>
    <textdaten>
      <fussnoten>…</fussnoten>      ← cross-references/annotations — skipped
      <text format="XML">
        <Content>
          <P>(1) Gewinn ist…</P>    ← one <P> per Absatz
          <P>(2) …</P>
        </Content>
      </text>
    </textdaten>
  </norm>

Returned hierarchy (ParsedLaw):
  parent_node  — full paragraph text (§ 4 EStG complete)
  child_nodes  — one node per <P> / Absatz

Metadata per node:
  law        — e.g. "EStG"
  paragraph  — e.g. "§ 4"
  title      — e.g. "Betriebsausgaben"
  section    — e.g. "Abs. 1" (empty on parent nodes)
  year       — int, e.g. 2025
  url        — canonical permalink on gesetze-im-internet.de
  node_level — "parent" | "child"
"""
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup
from llama_index.core.schema import (
    BaseNode,
    NodeRelationship,
    RelatedNodeInfo,
    TextNode,
)

logger = logging.getLogger(__name__)

# URL template for gesetze-im-internet.de permalinks (for source chips)
_URL_BASES: dict[str, str] = {
    "EStG":   "https://www.gesetze-im-internet.de/estg/",
    "EStDV":  "https://www.gesetze-im-internet.de/estdv_1955/",
    "AO":     "https://www.gesetze-im-internet.de/ao_1977/",
    "UStG":   "https://www.gesetze-im-internet.de/ustg_1980/",
    "SolzG":  "https://www.gesetze-im-internet.de/solzg_1995/",
    "GewStG": "https://www.gesetze-im-internet.de/gewstg/",
    "KStG": "https://www.gesetze-im-internet.de/kstg_1977/",
    "ErbStG": "https://www.gesetze-im-internet.de/erbstg_1974/",
    "ArbNErfG": "https://www.gesetze-im-internet.de/arbnerfg/",
}

_PARA_RE = re.compile(r"§\s*(\d+[a-z]?)", re.IGNORECASE)
_ABS_RE  = re.compile(r"^\((\d+[a-z]?)\)")  # "(1)" "(4a)" at start of <P> text


# ─── Public types ─────────────────────────────────────────────────────────────

@dataclass
class ParsedLaw:
    """Two-level hierarchy for one law-year ingest run."""
    parent_nodes: list[BaseNode] = field(default_factory=list)
    child_nodes: list[BaseNode] = field(default_factory=list)

    @property
    def all_nodes(self) -> list[BaseNode]:
        return self.parent_nodes + self.child_nodes


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _para_url(law: str, paragraph: str) -> str | None:
    base = _URL_BASES.get(law)
    if not base:
        return None
    m = _PARA_RE.search(paragraph)
    if not m:
        return None
    return f"{base}__{m.group(1)}.html"


def _extract_text(node) -> str:
    """Recursively extract plain text, collapsing whitespace."""
    parts: list[str] = []
    for child in node.descendants:
        if isinstance(child, str) and child.strip():
            parts.append(child.strip())
    return " ".join(parts)


def _abs_section(text: str) -> str:
    """'(4a) …' → 'Abs. 4a';  text without prefix → ''."""
    m = _ABS_RE.match(text.strip())
    return f"Abs. {m.group(1)}" if m else ""


def _stable_id(law: str, year: int, paragraph: str, section: str = "") -> str:
    """Build a deterministic, URL-safe node ID."""
    para_clean = re.sub(r"[^\w]", "", paragraph)      # "§ 9" → "9"
    parts = [law, str(year), para_clean]
    if section:
        parts.append(re.sub(r"[^\w]", "", section))   # "Abs. 4a" → "Abs4a"
    return "__".join(parts)


# ─── Main parser ──────────────────────────────────────────────────────────────

def parse_law_xml(xml_path: Path, law: str, year: int) -> ParsedLaw:
    """
    Parse *xml_path* and return a two-level hierarchy for *law* / *year*.
    Each § paragraph becomes one parent node; each <P> (Absatz) one child node.
    """
    with open(xml_path, encoding="utf-8") as fh:
        soup = BeautifulSoup(fh.read(), "lxml-xml")

    result = ParsedLaw()
    skipped = 0

    for norm in soup.find_all("norm"):
        meta_tag = norm.find("metadaten")
        if not meta_tag:
            skipped += 1
            continue

        # Paragraph reference lives in <metadaten>/<enbez>
        enbez_tag = meta_tag.find("enbez")
        if not enbez_tag:
            skipped += 1
            continue

        paragraph = enbez_tag.get_text(strip=True)
        if not paragraph.startswith("§"):
            skipped += 1
            continue  # skip table-of-contents / intro sections

        title_tag = meta_tag.find("titel")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Body — extract from <text> only, skipping <fussnoten>
        textdaten = norm.find("textdaten")
        if not textdaten:
            skipped += 1
            continue

        text_node = textdaten.find("text")
        if not text_node:
            skipped += 1
            continue

        # ── Parent node (full paragraph text) ─────────────────────────────────
        full_text = _extract_text(text_node).strip()
        if not full_text:
            skipped += 1
            continue

        parent_header = f"{paragraph} {law}"
        if title:
            parent_header += f" — {title}"

        parent_id = _stable_id(law, year, paragraph)
        url = _para_url(law, paragraph) or ""
        base_meta = {
            "law": law,
            "paragraph": paragraph,
            "title": title,
            "year": year,
            "url": url,
        }

        parent_node = TextNode(
            id_=parent_id,
            text=f"{parent_header}\n\n{full_text}",
            metadata={**base_meta, "section": "", "node_level": "parent"},
        )

        # ── Child nodes (one per <P> / Absatz) ────────────────────────────────
        children: list[TextNode] = []
        p_tags = text_node.find_all("P")

        for i, p_tag in enumerate(p_tags):
            p_text = _extract_text(p_tag).strip()
            if not p_text:
                continue
            # Skip footnote lines that slipped through (e.g. "(+++ …)")
            if p_text.startswith("(+++"):
                continue

            section = _abs_section(p_text)
            child_id = _stable_id(law, year, paragraph, section or f"p{i}")

            child_header = parent_header
            if section:
                child_header += f", {section}"

            child_node = TextNode(
                id_=child_id,
                text=f"{child_header}\n\n{p_text}",
                metadata={**base_meta, "section": section, "node_level": "child"},
                relationships={
                    NodeRelationship.PARENT: RelatedNodeInfo(node_id=parent_id),
                },
            )
            children.append(child_node)

        # Link parent → children
        if children:
            parent_node.relationships[NodeRelationship.CHILD] = [
                RelatedNodeInfo(node_id=c.node_id) for c in children
            ]

        result.parent_nodes.append(parent_node)
        result.child_nodes.extend(children)

    logger.info(
        "Parsed %s %d: %d parents, %d children, %d skipped",
        law, year, len(result.parent_nodes), len(result.child_nodes), skipped,
    )
    return result
