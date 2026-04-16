"""
LStR (Lohnsteuer-Richtlinien) scraper.

Technischer Ablauf:
  1. PDF herunterladen (httpx)
  2. pdfplumber öffnet das PDF und iteriert über jede Seite
  3. page.extract_text() rekonstruiert den Fließtext aus PDF-Text-Objekten
     (jedes Zeichen hat x/y-Koordinaten — pdfplumber sortiert nach Position)
  4. Volltext aller Seiten zu einem String zusammenführen
  5. Auf Randnummern-Muster splitten: "R \d+(\.\d+)*" steht am Zeilenanfang
     und markiert jeden LStR-Abschnitt (z.B. "R 19.3", "R 40")
  6. Jeden Abschnitt als eigenes LlamaIndex Document speichern

Metadaten pro Document:
  law       — "LStR"
  section   — Randnummer, z.B. "R 19.3"
  year      — int, z.B. 2023
  source    — "bundesfinanzministerium.de"
  url       — direkte PDF-URL
"""
import io
import logging
import re
from pathlib import Path

import httpx
from llama_index.core import Document

from ingest.parser import ParsedLaw
from ingest.scrapers.registry import get_source

logger = logging.getLogger(__name__)

# Randnummer am Zeilenanfang: "R 19.3" oder "R 40"
_RANDNR_RE = re.compile(r"(?m)^(R\s+\d+(?:\.\d+)*)\s*\n")

# Minimum character count — discard near-empty chunks (page headers etc.)
_MIN_CHUNK_CHARS = 80


def _split_by_randnummer(full_text: str) -> list[tuple[str, str]]:
    """
    Split *full_text* on Randnummern headers.
    Returns list of (randnr, body_text) tuples.
    """
    parts: list[tuple[str, str]] = []
    matches = list(_RANDNR_RE.finditer(full_text))

    for i, m in enumerate(matches):
        randnr = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        body = full_text[start:end].strip()
        if len(body) >= _MIN_CHUNK_CHARS:
            parts.append((randnr, body))

    return parts


def parse_lstr_pdf(pdf_bytes: bytes, year: int, url: str) -> list[Document]:
    """
    Parse *pdf_bytes* (raw PDF content) into LlamaIndex Documents.
    One Document per Randnummer section.
    """
    import pdfplumber  # lazy import — optional dependency

    documents: list[Document] = []
    pages: list[str] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        logger.info("LStR PDF: %d Seiten", len(pdf.pages))
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

    full_text = "\n".join(pages)
    logger.debug("LStR Volltext: %d Zeichen", len(full_text))

    sections = _split_by_randnummer(full_text)
    logger.info("LStR: %d Abschnitte nach Randnummer-Split", len(sections))

    for randnr, body in sections:
        doc_text = f"{randnr} LStR {year}\n\n{body}"
        documents.append(
            Document(
                text=doc_text,
                metadata={
                    "law": "LStR",
                    "paragraph": randnr,
                    "section": "",
                    "title": "",
                    "year": year,
                    "source": "bundesfinanzministerium.de",
                    "url": url,
                },
            )
        )

    if not documents:
        logger.warning(
            "LStR: Keine Abschnitte extrahiert — PDF-Struktur möglicherweise geändert. "
            "Randnummer-Regex prüfen: %s",
            _RANDNR_RE.pattern,
        )

    return documents


async def download_and_parse_lstr(dest_dir: Path, year: int) -> ParsedLaw:
    """
    Download the LStR PDF for *year* and return parsed Documents.
    The PDF is cached at *dest_dir*/LStR_<year>.pdf.
    """
    source = get_source("LStR")
    url = source.url

    dest_dir.mkdir(parents=True, exist_ok=True)
    cache_path = dest_dir / f"LStR_{year}.pdf"

    if cache_path.exists():
        logger.info("LStR: Verwende gecachtes PDF: %s", cache_path)
        pdf_bytes = cache_path.read_bytes()
    else:
        logger.info("LStR: Herunterladen von %s", url)
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        pdf_bytes = response.content
        cache_path.write_bytes(pdf_bytes)
        logger.info("LStR: PDF gespeichert unter %s (%d bytes)", cache_path, len(pdf_bytes))

    documents = parse_lstr_pdf(pdf_bytes, year, url)
    # LStR Randnummern are already leaf-level chunks — no further splitting needed.
    # Use parent_nodes slot so store.py embeds them directly into Chroma.
    return ParsedLaw(parent_nodes=documents, child_nodes=[])
