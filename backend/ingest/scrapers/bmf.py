"""
BMF-Schreiben scraper.

Technischer Ablauf:
  1. Alle aktiven Schreiben aus bmf_catalog.get_active_schreiben(year) laden
  2. Jedes Schreiben als PDF oder HTML herunterladen (httpx), Ergebnis cachen
  3. Inhalt in Abschnitte splitten:
       a) Römische Abschnitte  "I. Grundsätze" / "II. Anwendung …"
       b) Randnummern          "Rn. 1", "Rn. 5–10"
       c) Fallback             ganzes Dokument als einzelner Node
  4. Pro Abschnitt ein LlamaIndex Document mit Aktenzeichen + Datum als Metadaten
  5. Fehlgeschlagene Downloads werden übersprungen (Warnung, kein Abbruch)

Metadaten pro Document:
  law       — "BMF"
  paragraph — Aktenzeichen, z.B. "IV C 6 - S 2145/19/10006:027"
  section   — Abschnitts-Label, z.B. "I." oder "Rn. 5" (leer wenn ungeteilt)
  title     — Betreff des Schreibens
  datum     — ISO-Datum, z.B. "2023-08-15"
  year      — int Steuerjahr (RAG-Filter)
  source    — "bundesfinanzministerium.de"
  url       — direkte Download-URL
"""

import io
import logging
import re
from pathlib import Path

import httpx
from llama_index.core import Document
from llama_index.core.schema import BaseNode

from ingest.parser import ParsedLaw
from ingest.scrapers.bmf_catalog import BmfSchreiben, get_active_schreiben

logger = logging.getLogger(__name__)

# Minimum body length — discard near-empty chunks (headers, page numbers, …)
_MIN_CHUNK_CHARS = 120

# Roman-numeral section header at line start, e.g. "I. Allgemeines" / "IV. Sonderregeln"
_ABSCHNITT_RE = re.compile(r"(?m)^(I{1,3}V?|VI{0,3}|IX|XI{0,3}|X)\.\s+(.+)")

# Randnummer pattern: "Rn. 5", "Rn. 5 – 10", "Rz. 5"
_RANDNR_RE = re.compile(r"(?m)^((?:Rn|Rz)\.\s*\d+(?:\s*[-–]\s*\d+)?)\s*\n?")


# ─── Text splitting ───────────────────────────────────────────────────────────


def _split_text(full_text: str) -> list[tuple[str, str]]:
    """
    Return list of (section_label, body) pairs from *full_text*.

    Tries in order:
      1. Roman-numeral Abschnitte (≥ 2 matches)
      2. Randnummern (≥ 3 matches)
      3. Fallback: whole text as one chunk
    """
    # 1. Abschnitt split
    matches = list(_ABSCHNITT_RE.finditer(full_text))
    if len(matches) >= 2:
        parts: list[tuple[str, str]] = []
        for i, m in enumerate(matches):
            label = f"{m.group(1)}. {m.group(2).strip()}"
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            body = full_text[start:end].strip()
            if len(body) >= _MIN_CHUNK_CHARS:
                parts.append((label, body))
        if parts:
            return parts

    # 2. Randnummer split
    matches_rn = list(_RANDNR_RE.finditer(full_text))
    if len(matches_rn) >= 3:
        parts = []
        for i, m in enumerate(matches_rn):
            label = m.group(1).strip()
            start = m.end()
            end = (
                matches_rn[i + 1].start() if i + 1 < len(matches_rn) else len(full_text)
            )
            body = full_text[start:end].strip()
            if len(body) >= _MIN_CHUNK_CHARS:
                parts.append((label, body))
        if parts:
            return parts

    # 3. Fallback: whole document
    text = full_text.strip()
    if text:
        return [("", text)]
    return []


# ─── Format-specific parsers ──────────────────────────────────────────────────


def _parse_pdf(pdf_bytes: bytes, schreiben: BmfSchreiben, year: int) -> list[BaseNode]:
    import pdfplumber  # lazy import

    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        logger.info("BMF %s: PDF mit %d Seiten", schreiben.id, len(pdf.pages))
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

    full_text = "\n".join(pages)
    sections = _split_text(full_text)
    logger.info("BMF %s: %d Abschnitte aus PDF", schreiben.id, len(sections))
    return _build_documents(sections, schreiben, year)


def _parse_html(
    html_bytes: bytes, schreiben: BmfSchreiben, year: int
) -> list[BaseNode]:
    from bs4 import BeautifulSoup  # lazy import

    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup.find_all(["nav", "header", "footer", "script", "style"]):
        tag.decompose()

    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", class_=re.compile(r"content|main|text", re.I))
        or soup.body
    )
    raw = main.get_text(separator="\n") if main else soup.get_text(separator="\n")
    full_text = re.sub(r"\n{3,}", "\n\n", raw).strip()

    sections = _split_text(full_text)
    logger.info("BMF %s: %d Abschnitte aus HTML", schreiben.id, len(sections))
    return _build_documents(sections, schreiben, year)


# ─── Document builder ─────────────────────────────────────────────────────────


def _build_documents(
    sections: list[tuple[str, str]],
    schreiben: BmfSchreiben,
    year: int,
) -> list[BaseNode]:
    documents: list[BaseNode] = []
    for section_label, body in sections:
        header = f"BMF-Schreiben {schreiben.datum}\nAktenzeichen: {schreiben.aktenzeichen}\n{schreiben.betreff}"
        if section_label:
            header += f"\n\n{section_label}"
        documents.append(
            Document(
                text=f"{header}\n\n{body}",
                metadata={
                    "law": "BMF",
                    "paragraph": schreiben.aktenzeichen,
                    "section": section_label,
                    "title": schreiben.betreff,
                    "datum": schreiben.datum,
                    "year": year,
                    "source": "bundesfinanzministerium.de",
                    "url": schreiben.url,
                },
            )
        )
    return documents


# ─── Per-Schreiben download ───────────────────────────────────────────────────


async def _download_one(
    schreiben: BmfSchreiben,
    dest_dir: Path,
    year: int,
    client: httpx.AsyncClient,
) -> list[BaseNode]:
    """
    Download and parse a single BMF-Schreiben.
    Returns empty list on any failure (download error, parse error, empty result).
    """
    cache_path = dest_dir / f"BMF_{schreiben.id}.bin"

    # ── Cache hit ─────────────────────────────────────────────────────────────
    if cache_path.exists():
        logger.info("BMF %s: Cache-Treffer %s", schreiben.id, cache_path)
        raw = cache_path.read_bytes()
        try:
            if raw[:4] == b"%PDF":
                return _parse_pdf(raw, schreiben, year)
            return _parse_html(raw, schreiben, year)
        except Exception as exc:
            logger.warning(
                "BMF %s: Parse-Fehler aus Cache (%s) — übersprungen.", schreiben.id, exc
            )
            return []

    # ── Download ──────────────────────────────────────────────────────────────
    logger.info("BMF %s: Download von %s", schreiben.id, schreiben.url)
    try:
        response = await client.get(schreiben.url)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "BMF %s: HTTP %s — übersprungen. (URL ggf. veraltet: %s)",
            schreiben.id,
            exc.response.status_code,
            schreiben.url,
        )
        return []
    except httpx.RequestError as exc:
        logger.warning(
            "BMF %s: Verbindungsfehler (%s) — übersprungen.", schreiben.id, exc
        )
        return []

    raw = response.content
    cache_path.write_bytes(raw)

    content_type = response.headers.get("content-type", "").lower()
    is_pdf = "pdf" in content_type or raw[:4] == b"%PDF"

    try:
        if is_pdf:
            return _parse_pdf(raw, schreiben, year)
        elif "html" in content_type or "text" in content_type:
            logger.info("BMF %s: HTML-Quelle erkannt", schreiben.id)
            return _parse_html(raw, schreiben, year)
        else:
            logger.warning(
                "BMF %s: Unbekannter Content-Type '%s' — übersprungen.",
                schreiben.id,
                content_type,
            )
            return []
    except Exception as exc:
        logger.warning("BMF %s: Parse-Fehler (%s) — übersprungen.", schreiben.id, exc)
        return []


# ─── Public entry point ───────────────────────────────────────────────────────


async def download_and_parse_bmf(dest_dir: Path, year: int) -> ParsedLaw:
    """
    Download and parse all active BMF-Schreiben for *year*.

    Failed individual downloads are skipped with a warning — the overall ingest
    continues. Returns a flat ParsedLaw (parent_nodes only, no children) because
    BMF-Schreiben sections are already leaf-level chunks.

    Args:
        dest_dir:  Directory for caching downloaded files.
        year:      Tax year; only Schreiben with valid_from_year ≤ year are fetched.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    schreiben_list = get_active_schreiben(year)
    logger.info("BMF: %d aktive Schreiben für Steuerjahr %d", len(schreiben_list), year)

    all_documents: list[BaseNode] = []
    failed: list[str] = []

    async with httpx.AsyncClient(
        timeout=60,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; steuerpilot-ingest/1.0; +https://github.com/steuerpilot-ai)"
        },
    ) as client:
        for schreiben in schreiben_list:
            docs = await _download_one(schreiben, dest_dir, year, client)
            if docs:
                all_documents.extend(docs)
            else:
                failed.append(schreiben.id)

    logger.info(
        "BMF: %d Nodes aus %d/%d Schreiben extrahiert",
        len(all_documents),
        len(schreiben_list) - len(failed),
        len(schreiben_list),
    )
    if failed:
        logger.warning(
            "BMF: Übersprungene Schreiben (%d): %s", len(failed), ", ".join(failed)
        )

    return ParsedLaw(parent_nodes=all_documents, child_nodes=[])
