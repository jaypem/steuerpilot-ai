"""
Unit tests for ingest/scrapers/lstr.py.

All tests are offline — no network. HTML is synthesised in-memory to match
the real lsth.bundesfinanzministerium.de structure.
"""

import pytest

from ingest.scrapers.lstr import _paragraph_from_url, _parse_page


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_page(sections: list[dict]) -> str:
    """
    Build a minimal LStH HTML page with the given R-Richtlinie sections.

    Each entry in *sections* is a dict with:
      - number: e.g. "R 19.1"
      - title:  e.g. "Arbeitgeber"
      - body:   plain text body (>= 50 chars to pass the _MIN_CHARS filter)
    """
    items = ""
    for s in sections:
        items += f"""
        <div id="anchor999" class="toc-container pressrelease">
            <div class="richtext-margin-label">
                <span class="richtext-margin-number">{s["number"]}</span>
            </div>
            <div class="toc-inner-container">
                <h2 class="toc-headline">Richtlinie</h2>
                <h3 class="toc-subheadline">{s["title"]}</h3>
                <div class="toc collapse" id="controls-toc-999">
                    <p>{s["body"]}</p>
                </div>
            </div>
        </div>
        """
    return f"<html><body>{items}</body></html>"


SAMPLE_URL = (
    "https://lsth.bundesfinanzministerium.de/"
    "lsth/2023/A-Einkommensteuergesetz/II-Einkommen/"
    "8-Die-einzelnen-Einkunftsarten/d-Nichtselbstaendige-Arbeit/"
    "Paragraf-19/inhalt.html"
)

LONG_BODY = "x" * 120  # well above _MIN_CHARS = 50


# ─── Tests: _paragraph_from_url ───────────────────────────────────────────────


def test_paragraph_from_url_numeric():
    assert _paragraph_from_url(SAMPLE_URL) == "§ 19"


def test_paragraph_from_url_alpha():
    url = "https://lsth.bundesfinanzministerium.de/lsth/2023/…/Paragraf-3b/inhalt.html"
    assert _paragraph_from_url(url) == "§ 3b"


def test_paragraph_from_url_no_match():
    assert (
        _paragraph_from_url(
            "https://lsth.bundesfinanzministerium.de/lsth/2023/home.html"
        )
        == ""
    )


# ─── Tests: _parse_page ───────────────────────────────────────────────────────


def test_parse_single_section():
    html = _make_page([{"number": "R 19.1", "title": "Arbeitgeber", "body": LONG_BODY}])
    docs = _parse_page(html, SAMPLE_URL, 2023)

    assert len(docs) == 1
    doc = docs[0]
    assert doc.metadata["law"] == "LStR"
    assert doc.metadata["paragraph"] == "R 19.1"
    assert doc.metadata["section"] == "§ 19"
    assert doc.metadata["title"] == "Arbeitgeber"
    assert doc.metadata["year"] == 2023
    assert doc.metadata["source"] == "lsth.bundesfinanzministerium.de"
    assert doc.metadata["url"] == SAMPLE_URL
    assert "R 19.1 LStR 2023" in doc.text
    assert "Arbeitgeber" in doc.text


def test_parse_multiple_sections():
    html = _make_page(
        [
            {"number": "R 19.1", "title": "Arbeitgeber", "body": LONG_BODY},
            {"number": "R 19.2", "title": "Nebentätigkeit", "body": LONG_BODY},
            {"number": "R 19.3", "title": "Arbeitslohn", "body": LONG_BODY},
        ]
    )
    docs = _parse_page(html, SAMPLE_URL, 2023)
    assert len(docs) == 3
    assert [d.metadata["paragraph"] for d in docs] == ["R 19.1", "R 19.2", "R 19.3"]


def test_parse_skips_hinweise():
    """H-sections (Hinweise) must not be extracted."""
    html = _make_page(
        [
            {"number": "H 19.1", "title": "Hinweis", "body": LONG_BODY},
            {"number": "R 19.1", "title": "Richtlinie", "body": LONG_BODY},
        ]
    )
    docs = _parse_page(html, SAMPLE_URL, 2023)
    assert len(docs) == 1
    assert docs[0].metadata["paragraph"] == "R 19.1"


def test_parse_skips_short_bodies():
    """Sections with body < _MIN_CHARS should be filtered out."""
    html = _make_page(
        [
            {"number": "R 19.1", "title": "Kurz", "body": "Zu kurz."},
            {"number": "R 19.2", "title": "Lang genug", "body": LONG_BODY},
        ]
    )
    docs = _parse_page(html, SAMPLE_URL, 2023)
    assert len(docs) == 1
    assert docs[0].metadata["paragraph"] == "R 19.2"


def test_parse_nonbreaking_space_in_number():
    """The real site uses \xa0 between 'R' and the number — must be normalised."""
    html = f"""<html><body>
    <div class="toc-container pressrelease">
        <div class="richtext-margin-label">
            <span class="richtext-margin-number">R\xa019.1</span>
        </div>
        <div class="toc-inner-container">
            <h3 class="toc-subheadline">Arbeitgeber</h3>
            <div class="toc collapse" id="controls-toc-999">
                <p>{LONG_BODY}</p>
            </div>
        </div>
    </div>
    </body></html>"""
    docs = _parse_page(html, SAMPLE_URL, 2023)
    assert len(docs) == 1
    assert docs[0].metadata["paragraph"] == "R 19.1"


def test_parse_empty_page():
    docs = _parse_page("<html><body></body></html>", SAMPLE_URL, 2023)
    assert docs == []
