"""
BFH-Urteile scraper.

Technischer Ablauf:
  1. Alle aktiven Urteile aus bfh_catalog.get_active_urteile(year) laden
  2. HTML-Seite von bundesfinanzhof.de herunterladen (httpx, User-Agent, Cache)
  3. Inhalt strukturiert parsen:
       a) Hauptbereich: div.m-article__body
       b) Sections via h2.a-headline__2 (Leitsätze, Tatbestand, Entscheidungsgründe, Tenor)
       c) Subsections via h3 (I., II., …) innerhalb jeder Section
       d) Paragraphen via li.m-decisions__item[data-rd] (z.B. Rn. 1, Rn. 2)
       e) Fallback: ganzes Dokument wenn Struktur nicht erkannt
  4. Pro Abschnitt ein LlamaIndex Document mit Metadaten
  5. Fehlgeschlagene Downloads werden übersprungen (Warnung, kein Abbruch)

Metadaten pro Document:
  law       — "BFH"
  paragraph — Aktenzeichen, z.B. "VI R 32/20"
  ecli      — z.B. "ECLI:DE:BFH:2022:U.120522.VIR32.20.0"
  section   — Abschnitts-Label, z.B. "Entscheidungsgründe — I." (leer wenn ungeteilt)
  title     — Kurzbeschreibung des Urteils
  datum     — ISO-Datum, z.B. "2022-05-12"
  senat     — z.B. "VI. Senat"
  year      — int Steuerjahr (RAG-Filter)
  source    — "bundesfinanzhof.de"
  url       — direkte URL auf bundesfinanzhof.de
  bstbl     — "ja" | "nein" (von Verwaltung übernommen?)
"""

import logging
import re
from pathlib import Path

import httpx
from llama_index.core import Document

from ingest.parser import ParsedLaw
from ingest.scrapers.bfh_catalog import BfhUrteil, get_active_urteile

logger = logging.getLogger(__name__)

# Minimum body length — discard near-empty chunks
_MIN_CHUNK_CHARS = 120

_USER_AGENT = (
    "Mozilla/5.0 (compatible; steuerpilot-ingest/1.0; "
    "+https://github.com/steuerpilot-ai)"
)


# ─── HTML parsing ─────────────────────────────────────────────────────────────


def _items_to_text(items: list[tuple[str, str]]) -> str:
    """
    Convert a list of (rn_number, text) pairs to a readable string.
    Items with a Rn. number are prefixed with "Rn. N: ".
    """
    parts = []
    for rn, text in items:
        parts.append(f"Rn. {rn}: {text}" if rn else text)
    return "\n\n".join(parts)


def _extract_sections(body) -> list[tuple[str, str]]:
    """
    Parse BFH ruling HTML body (div.m-article__body) into (label, text) pairs.

    Structure on bundesfinanzhof.de:
      h2.a-headline__2      — major section (Leitsätze / Tatbestand /
                              Entscheidungsgründe / Tenor)
      div.m-decisions       — content of that section, contains either:
          p                 — plain paragraphs (Leitsatz / Tenor items)
          h3                — subsection heading (I., II., …)
          ol.m-decisions__list > li.m-decisions__item[data-rd]
                            — numbered paragraphs (Rn.)
    """
    sections: list[tuple[str, str]] = []
    current_h2 = ""

    for el in body.children:
        if not hasattr(el, "name") or not el.name:
            continue

        # ── Major section heading ────────────────────────────────────────────
        if el.name == "h2":
            current_h2 = el.get_text(" ", strip=True)
            continue

        # ── Section content ──────────────────────────────────────────────────
        if el.name == "div" and "m-decisions" in " ".join(el.get("class") or []):
            # Check whether subsection h3 headings exist (direct children only)
            has_h3 = bool(el.find("h3"))

            if has_h3:
                # Split by h3 — each (h3 heading + its ol/p content) = one section
                current_h3 = ""
                current_items: list[tuple[str, str]] = []

                for child in el.children:
                    if not hasattr(child, "name") or not child.name:
                        continue

                    if child.name == "h3":
                        # Flush previous h3 block
                        if current_items:
                            text = _items_to_text(current_items)
                            label = (
                                f"{current_h2} — {current_h3}"
                                if current_h3
                                else current_h2
                            )
                            if len(text) >= _MIN_CHUNK_CHARS:
                                sections.append((label, text))
                        current_h3 = child.get_text(" ", strip=True)
                        current_items = []

                    elif child.name == "ol":
                        for li in child.find_all(
                            "li", class_="m-decisions__item"
                        ):
                            rn = li.get("data-rd", "")
                            t = li.get_text(" ", strip=True)
                            if t:
                                current_items.append((rn, t))

                    elif child.name == "p":
                        t = child.get_text(" ", strip=True)
                        if t:
                            current_items.append(("", t))

                # Flush last h3 block
                if current_items:
                    text = _items_to_text(current_items)
                    label = (
                        f"{current_h2} — {current_h3}"
                        if current_h3
                        else current_h2
                    )
                    if len(text) >= _MIN_CHUNK_CHARS:
                        sections.append((label, text))

            else:
                # No h3 — single block (Leitsätze / Tenor / short section)
                items: list[tuple[str, str]] = []

                for li in el.find_all("li", class_="m-decisions__item"):
                    rn = li.get("data-rd", "")
                    t = li.get_text(" ", strip=True)
                    if t:
                        items.append((rn, t))

                # Fallback: plain <p> inside div.m-decisions
                if not items:
                    for p in el.find_all("p"):
                        t = p.get_text(" ", strip=True)
                        if t:
                            items.append(("", t))

                if items:
                    text = _items_to_text(items)
                    if len(text) >= _MIN_CHUNK_CHARS:
                        sections.append((current_h2, text))

    return sections


def _fallback_text_split(full_text: str) -> list[tuple[str, str]]:
    """
    Fallback when HTML structure is not recognized.
    Splits by known BFH section headings found as plain text, then
    falls back to whole document as one chunk.
    """
    _SECTION_NAMES = [
        "Leitsatz", "Leitsätze", "Tenor", "Tatbestand", "Entscheidungsgründe",
    ]
    pattern = re.compile(
        r"(?m)^(" + "|".join(re.escape(s) for s in _SECTION_NAMES) + r")\s*$"
    )
    matches = list(pattern.finditer(full_text))
    if len(matches) >= 2:
        parts = []
        for i, m in enumerate(matches):
            label = m.group(1)
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            body = full_text[start:end].strip()
            if len(body) >= _MIN_CHUNK_CHARS:
                parts.append((label, body))
        if parts:
            return parts

    text = full_text.strip()
    if text:
        return [("", text)]
    return []


def _parse_html(
    html_bytes: bytes, urteil: BfhUrteil, year: int
) -> list[Document]:
    from bs4 import BeautifulSoup  # lazy import

    soup = BeautifulSoup(html_bytes, "html.parser")

    # Strip navigation and boilerplate
    for tag in soup.find_all(["header", "nav", "footer", "script", "style"]):
        tag.decompose()

    # Target the main ruling body
    body = (
        soup.find("div", class_="m-article__body")
        or soup.find("main")
        or soup.find("article")
        or soup.body
    )
    if not body:
        logger.warning("BFH %s: Kein Hauptinhalt gefunden", urteil.id)
        return []

    sections = _extract_sections(body)

    # If structured parsing yielded nothing, fall back to raw text split
    if not sections:
        logger.info(
            "BFH %s: Strukturiertes Parsing ergab keine Abschnitte — Fallback",
            urteil.id,
        )
        raw = re.sub(r"\n{3,}", "\n\n", body.get_text(separator="\n")).strip()
        sections = _fallback_text_split(raw)

    logger.info("BFH %s: %d Abschnitte extrahiert", urteil.id, len(sections))
    return _build_documents(sections, urteil, year)


# ─── Document builder ─────────────────────────────────────────────────────────


def _build_documents(
    sections: list[tuple[str, str]],
    urteil: BfhUrteil,
    year: int,
) -> list[Document]:
    documents: list[Document] = []
    for section_label, body in sections:
        header_lines = [
            f"BFH-Urteil {urteil.datum}",
            f"{urteil.senat}  |  Az. {urteil.aktenzeichen}",
        ]
        if urteil.ecli:
            header_lines.append(f"ECLI: {urteil.ecli}")
        header_lines.append(urteil.betreff)
        if not urteil.bstbl_aufgenommen:
            header_lines.append(
                "[Noch nicht im BStBl II — Verwaltung wendet nicht allgemein an]"
            )
        if section_label:
            header_lines.append(f"\n{section_label}")

        header = "\n".join(header_lines)

        documents.append(
            Document(
                text=f"{header}\n\n{body}",
                metadata={
                    "law": "BFH",
                    "paragraph": urteil.aktenzeichen,
                    "ecli": urteil.ecli,
                    "section": section_label,
                    "title": urteil.betreff,
                    "datum": urteil.datum,
                    "senat": urteil.senat,
                    "year": year,
                    "source": "bundesfinanzhof.de",
                    "url": urteil.url,
                    "bstbl": "ja" if urteil.bstbl_aufgenommen else "nein",
                },
            )
        )
    return documents


# ─── Per-Urteil download ──────────────────────────────────────────────────────


async def _download_one(
    urteil: BfhUrteil,
    dest_dir: Path,
    year: int,
    client: httpx.AsyncClient,
) -> list[Document]:
    """
    Download and parse a single BFH ruling.
    Returns empty list on any failure (download error, parse error, empty result).
    """
    cache_path = dest_dir / f"BFH_{urteil.id}.bin"

    # ── Cache hit ─────────────────────────────────────────────────────────────
    if cache_path.exists():
        logger.info("BFH %s: Cache-Treffer %s", urteil.id, cache_path)
        raw = cache_path.read_bytes()
        try:
            return _parse_html(raw, urteil, year)
        except Exception as exc:
            logger.warning(
                "BFH %s: Parse-Fehler aus Cache (%s) — übersprungen.",
                urteil.id, exc,
            )
            return []

    # ── Download ──────────────────────────────────────────────────────────────
    logger.info("BFH %s: Download von %s", urteil.id, urteil.url)
    try:
        response = await client.get(urteil.url)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "BFH %s: HTTP %s — übersprungen. (URL ggf. veraltet: %s)",
            urteil.id, exc.response.status_code, urteil.url,
        )
        return []
    except httpx.RequestError as exc:
        logger.warning(
            "BFH %s: Verbindungsfehler (%s) — übersprungen.", urteil.id, exc
        )
        return []

    raw = response.content
    cache_path.write_bytes(raw)

    try:
        return _parse_html(raw, urteil, year)
    except Exception as exc:
        logger.warning(
            "BFH %s: Parse-Fehler (%s) — übersprungen.", urteil.id, exc
        )
        return []


# ─── Public entry point ───────────────────────────────────────────────────────


async def download_and_parse_bfh(dest_dir: Path, year: int) -> ParsedLaw:
    """
    Download and parse all active BFH-Urteile for *year*.

    Failed individual downloads are skipped with a warning — the overall ingest
    continues. Returns a flat ParsedLaw (parent_nodes only, no children) because
    BFH ruling sections are already leaf-level chunks.

    Args:
        dest_dir:  Directory for caching downloaded files.
        year:      Tax year; only Urteile with valid_from_year ≤ year are fetched.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    urteile = get_active_urteile(year)
    logger.info("BFH: %d aktive Urteile für Steuerjahr %d", len(urteile), year)

    all_documents: list[Document] = []
    failed: list[str] = []

    async with httpx.AsyncClient(
        timeout=60,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        for urteil in urteile:
            docs = await _download_one(urteil, dest_dir, year, client)
            if docs:
                all_documents.extend(docs)
            else:
                failed.append(urteil.id)

    logger.info(
        "BFH: %d Nodes aus %d/%d Urteilen extrahiert",
        len(all_documents),
        len(urteile) - len(failed),
        len(urteile),
    )
    if failed:
        logger.warning(
            "BFH: Übersprungene Urteile (%d): %s", len(failed), ", ".join(failed)
        )

    return ParsedLaw(parent_nodes=all_documents, child_nodes=[])
