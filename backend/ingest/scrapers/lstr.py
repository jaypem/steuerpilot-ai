"""
LStR (Lohnsteuer-Richtlinien) scraper — HTML edition.

Technischer Ablauf:
  1. Home-Seite abrufen (lsth.bundesfinanzministerium.de/lsth/{year}/home.html)
  2. Alle Paragraf-*/inhalt.html Links extrahieren
  3. Jede Paragraf-Seite nebenläufig abrufen (Semaphore: 10 gleichzeitige Anfragen)
  4. Auf jeder Seite alle Richtlinien-Abschnitte (class="toc-container pressrelease")
     mit einem richtext-margin-number "R <nr>" extrahieren:
       - margin-number → paragraph-Metadatum (z.B. "R 19.1")
       - toc-subheadline → Abschnittstitel
       - toc-inner-container Text → Fließtext der Richtlinie
  5. Jeden R-Abschnitt als eigenes LlamaIndex Document speichern

Metadaten pro Document:
  law       — "LStR"
  paragraph — Randnummer, z.B. "R 19.1"
  section   — Paragraf aus der URL, z.B. "§ 19"
  title     — Abschnittsüberschrift, z.B. "Arbeitgeber"
  year      — int, z.B. 2023
  source    — "lsth.bundesfinanzministerium.de"
  url       — direkte URL der Paragraf-Seite
"""

import asyncio
import logging
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from llama_index.core import Document
from llama_index.core.schema import BaseNode

from ingest.parser import ParsedLaw
from ingest.scrapers.registry import get_source

logger = logging.getLogger(__name__)

_BASE_URL = "https://lsth.bundesfinanzministerium.de/"

# Extracts Paragraf-N from a URL path segment, e.g. "Paragraf-19" → "§ 19"
_PARAGRAF_RE = re.compile(r"Paragraf-(\d+[a-zA-Z]*)", re.IGNORECASE)

# Only scrape Paragraf-* leaf pages (skip meta/index/appendix pages)
_PARAGRAF_URL_RE = re.compile(r"lsth/\d+/.+/Paragraf-[^/]+/inhalt\.html$")

# Minimum character count for a section body
_MIN_CHARS = 50

# Concurrent HTTP requests
_SEMAPHORE_LIMIT = 10


def _paragraph_from_url(url: str) -> str:
    """Extract '§ 19' from '…/Paragraf-19/inhalt.html'."""
    m = _PARAGRAF_RE.search(url)
    if not m:
        return ""
    raw = m.group(1)
    # Normalise: "19a" stays "19a", digits only adds space
    return f"§ {raw}"


def _extract_text(element) -> str:
    """Return clean text from a BeautifulSoup element."""
    return " ".join(element.get_text(" ", strip=True).split())


def _parse_page(html: str, url: str, year: int) -> list[BaseNode]:
    """
    Parse one Paragraf HTML page and return one Document per R-Richtlinie.
    """
    soup = BeautifulSoup(html, "html.parser")
    section = _paragraph_from_url(url)
    documents: list[BaseNode] = []

    # Each R-Richtlinie section lives in a toc-container that has
    # a richtext-margin-number starting with "R".
    for container in soup.find_all("div", class_="toc-container"):
        margin_el = container.find("span", class_="richtext-margin-number")
        if margin_el is None:
            continue

        # Replace non-breaking spaces and normalise
        raw_number = margin_el.get_text(" ", strip=True).replace("\xa0", " ")
        if not raw_number.startswith("R "):
            continue  # skip H (Hinweise), LStDV, etc.

        # Title: the toc-subheadline heading
        inner = container.find("div", class_="toc-inner-container")
        if inner is None:
            continue

        title_el = inner.find(class_="toc-subheadline")
        title = _extract_text(title_el) if title_el else ""

        # Body: collapsed content div (still present in static HTML)
        body_el = inner.find("div", class_="toc")
        if body_el is None:
            # Fall back to all inner text minus the headline
            if title_el:
                title_el.decompose()
            body = _extract_text(inner)
        else:
            body = _extract_text(body_el)

        if len(body) < _MIN_CHARS:
            continue

        doc_text = f"{raw_number} LStR {year}"
        if title:
            doc_text += f" – {title}"
        doc_text += f"\n\n{body}"

        documents.append(
            Document(
                text=doc_text,
                metadata={
                    "law": "LStR",
                    "paragraph": raw_number,
                    "section": section,
                    "title": title,
                    "year": year,
                    "source": "lsth.bundesfinanzministerium.de",
                    "url": url,
                },
            )
        )

    return documents


async def _fetch_page(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    url: str,
    year: int,
) -> list[BaseNode]:
    async with sem:
        try:
            resp = await client.get(url, timeout=30)
            resp.raise_for_status()
            return _parse_page(resp.text, url, year)
        except Exception as exc:
            logger.warning("LStR: Fehler beim Abrufen von %s: %s", url, exc)
            return []


async def _collect_paragraf_urls(client: httpx.AsyncClient, year: int) -> list[str]:
    """Fetch home.html and return all absolute Paragraf inhalt.html URLs."""
    home_url = f"{_BASE_URL}lsth/{year}/home.html"
    resp = await client.get(home_url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        # href may be relative (e.g. "lsth/2023/…") or absolute
        if href.startswith("http"):
            abs_url = href
        else:
            abs_url = _BASE_URL + href.lstrip("/")

        # Strip fragment
        abs_url = abs_url.split("#")[0]

        if _PARAGRAF_URL_RE.search(abs_url) and abs_url not in seen:
            seen.add(abs_url)
            urls.append(abs_url)

    logger.info("LStR: %d Paragraf-Seiten gefunden (Jahr %d)", len(urls), year)
    return urls


async def download_and_parse_lstr(dest_dir: Path, year: int) -> ParsedLaw:
    """
    Crawl the LStH website for *year* and return parsed Documents.
    *dest_dir* is accepted for API compatibility but not used (no caching).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(_SEMAPHORE_LIMIT)
    documents: list[BaseNode] = []

    async with httpx.AsyncClient(
        base_url=_BASE_URL,
        follow_redirects=True,
        headers={"Accept-Language": "de-DE,de;q=0.9"},
    ) as client:
        paragraf_urls = await _collect_paragraf_urls(client, year)

        tasks = [_fetch_page(client, sem, url, year) for url in paragraf_urls]
        results = await asyncio.gather(*tasks)

    for page_docs in results:
        documents.extend(page_docs)

    logger.info("LStR: %d R-Richtlinien-Abschnitte extrahiert", len(documents))

    if not documents:
        logger.warning(
            "LStR: Keine Abschnitte extrahiert — HTML-Struktur möglicherweise geändert. "
            "URL prüfen: %slsth/%d/home.html",
            _BASE_URL,
            year,
        )

    # LStR sections are already leaf-level chunks
    return ParsedLaw(parent_nodes=documents, child_nodes=[])
