"""
Parses gesetze-im-internet.de XML into LlamaIndex Document objects.

Each <norm> element that has a <gliederungsbez> starting with "§" becomes
one Document.  The text is the concatenated content of all <P> children.

Metadata per Document:
  law       — e.g. "EStG"
  paragraph — e.g. "§ 4"
  section   — e.g. "Abs. 5 Nr. 6b" (empty for the paragraph heading itself)
  title     — e.g. "Betriebsausgaben"
  year      — int, e.g. 2025
  url       — canonical permalink on gesetze-im-internet.de
"""
import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup
from llama_index.core import Document

logger = logging.getLogger(__name__)

# URL template for gesetze-im-internet.de permalinks (for source chips)
_URL_BASES: dict[str, str] = {
    "EStG": "https://www.gesetze-im-internet.de/estg/",
    "AO":   "https://www.gesetze-im-internet.de/ao_1977/",
    "UStG": "https://www.gesetze-im-internet.de/ustg_1980/",
}

# Maps "§ 4" → "__4.html" (simplified — actual filenames vary)
_PARA_RE = re.compile(r"§\s*(\d+[a-z]?)", re.IGNORECASE)


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


def parse_law_xml(xml_path: Path, law: str, year: int) -> list[Document]:
    """
    Parse *xml_path* and return one Document per paragraph of *law*.
    *year* is stored as integer metadata for Chroma filtering.
    """
    with open(xml_path, encoding="utf-8") as fh:
        soup = BeautifulSoup(fh.read(), "lxml-xml")

    documents: list[Document] = []
    skipped = 0

    for norm in soup.find_all("norm"):
        meta_tag = norm.find("metadaten")
        if not meta_tag:
            continue

        # Paragraph reference (§ 1, § 2a, …)
        gl = meta_tag.find("gliederungseinheit")
        if not gl:
            skipped += 1
            continue

        bez_tag = gl.find("gliederungsbez")
        if not bez_tag:
            skipped += 1
            continue

        paragraph = bez_tag.get_text(strip=True)
        if not paragraph.startswith("§"):
            skipped += 1
            continue  # skip table-of-contents / intro sections

        title_tag = gl.find("gliederungstitel")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Body text
        textdaten = norm.find("textdaten")
        if not textdaten:
            skipped += 1
            continue

        text = _extract_text(textdaten).strip()
        if not text:
            skipped += 1
            continue

        doc_text = f"{paragraph} {law}"
        if title:
            doc_text += f" — {title}"
        doc_text += f"\n\n{text}"

        documents.append(
            Document(
                text=doc_text,
                metadata={
                    "law": law,
                    "paragraph": paragraph,
                    "title": title,
                    "year": year,
                    "url": _para_url(law, paragraph) or "",
                },
            )
        )

    logger.info(
        "Parsed %s %d: %d documents, %d skipped",
        law, year, len(documents), skipped,
    )
    return documents
