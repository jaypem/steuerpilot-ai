"""
Unit tests for ingest/scrapers/bmf.py and ingest/scrapers/bmf_catalog.py.

All tests are offline — no network, no embeddings, no Chroma.
PDF and HTML content is synthesized in-memory.
"""

import pytest

from ingest.scrapers.bmf_catalog import (
    BMF_SCHREIBEN,
    BmfSchreiben,
    get_active_schreiben,
    get_by_id,
)
from ingest.scrapers.bmf import _split_text, _build_documents, _parse_html


# ─── Fixtures ─────────────────────────────────────────────────────────────────

SAMPLE_SCHREIBEN = BmfSchreiben(
    id="test_schreiben",
    aktenzeichen="IV C 6 - S 0000/00/00000:001",
    datum="2023-01-01",
    betreff="Testschreiben über Musterregelungen",
    url="https://example.com/test.pdf",
    valid_from_year=2023,
    thema="Test",
)

TEXT_WITH_ABSCHNITTE = """\
I. Allgemeines

Diese Regelung gilt für alle Steuerpflichtigen, die Aufwendungen
im Sinne von § 4 EStG geltend machen wollen. Voraussetzung ist,
dass die Kosten tatsächlich entstanden sind und nachgewiesen werden.

II. Anwendungsbereich

Der Anwendungsbereich umfasst alle natürlichen Personen, die
Einkünfte aus nichtselbständiger Arbeit oder selbständiger Arbeit
erzielen. Ausgenommen sind Körperschaften im Sinne des KStG.

III. Übergangsregelung

Für Veranlagungszeiträume vor 2023 gilt das BMF-Schreiben vom
01.01.2020 weiterhin entsprechend. Ab VZ 2023 ist ausschließlich
die neue Fassung anzuwenden.
"""

TEXT_WITH_RANDNUMMERN = """\
Präambel des Schreibens ohne Randnummer.

Rn. 1
Grundsätzlich sind alle Aufwendungen, die betrieblich oder beruflich
veranlasst sind, als Betriebsausgaben oder Werbungskosten abziehbar,
soweit keine Abzugsbeschränkung nach § 4 Abs. 5 EStG greift.

Rn. 2
Für die Nachweisführung sind Belege im Original vorzulegen oder
digital in unveränderlicher Form zu archivieren. Die Aufbewahrungsfrist
beträgt zehn Jahre ab Ende des Veranlagungszeitraums.

Rn. 3
Fahrten zwischen Wohnung und Betriebsstätte sind mit der
Entfernungspauschale von 0,30 € je Entfernungskilometer anzusetzen,
ab dem 21. Kilometer mit 0,38 € (§ 9 Abs. 1 Satz 3 Nr. 4 EStG).
"""

TEXT_WITHOUT_STRUCTURE = """\
Dieses Schreiben enthält eine einheitliche Regelung ohne Untergliederung.
Es werden alle relevanten Aspekte in einem zusammenhängenden Fließtext
dargestellt. Eine Aufteilung in Abschnitte oder Randnummern ist nicht
vorgesehen, da die Regelung kurz und abschließend ist.
"""

SIMPLE_HTML = """
<html>
<head><title>BMF-Schreiben Test</title></head>
<body>
<nav>Navigation hier</nav>
<main>
<h1>I. Allgemeines</h1>
<p>Dieser Abschnitt regelt die grundlegenden Anforderungen an
den Nachweis beruflich veranlasster Aufwendungen im Sinne von
Paragraph 9 EStG. Die Regelung gilt ab dem Veranlagungszeitraum 2023.</p>
<h2>II. Anwendungsbereich</h2>
<p>Der Anwendungsbereich umfasst alle Arbeitnehmer sowie
Selbststaendige und Freiberufler mit Einkuenften aus Paragraph 18 EStG,
die im Inland steuerpflichtig sind und Aufwendungen nachweisen.</p>
</main>
<footer>Impressum</footer>
</body>
</html>
""".encode("utf-8")


# ─── _split_text ──────────────────────────────────────────────────────────────

class TestSplitText:
    def test_abschnitt_split(self):
        parts = _split_text(TEXT_WITH_ABSCHNITTE)
        assert len(parts) == 3
        labels = [label for label, _ in parts]
        assert any("I." in label for label in labels)
        assert any("II." in label for label in labels)
        assert any("III." in label for label in labels)

    def test_abschnitt_body_not_empty(self):
        parts = _split_text(TEXT_WITH_ABSCHNITTE)
        for label, body in parts:
            assert len(body) >= 50, f"Body für '{label}' zu kurz"

    def test_randnummer_split(self):
        parts = _split_text(TEXT_WITH_RANDNUMMERN)
        assert len(parts) == 3
        labels = [label for label, _ in parts]
        assert any("Rn. 1" in label for label in labels)
        assert any("Rn. 3" in label for label in labels)

    def test_fallback_whole_document(self):
        parts = _split_text(TEXT_WITHOUT_STRUCTURE)
        assert len(parts) == 1
        label, body = parts[0]
        assert label == ""
        assert "einheitliche Regelung" in body

    def test_empty_text_returns_empty(self):
        assert _split_text("") == []
        assert _split_text("   \n\n   ") == []

    def test_short_sections_discarded(self):
        # Very short body between two Abschnitte should be filtered
        text = "I. Erster\n\nzu kurz\n\nII. Zweiter\n\n" + ("a" * 200)
        parts = _split_text(text)
        # Only the second section passes the _MIN_CHUNK_CHARS threshold
        labels = [label for label, _ in parts]
        assert any("II." in label for label in labels)


# ─── _build_documents ─────────────────────────────────────────────────────────

class TestBuildDocuments:
    def test_metadata_fields_present(self):
        sections = [("I. Allgemeines", "Langer Text " * 20)]
        docs = _build_documents(sections, SAMPLE_SCHREIBEN, 2023)
        assert len(docs) == 1
        meta = docs[0].metadata
        assert meta["law"] == "BMF"
        assert meta["paragraph"] == SAMPLE_SCHREIBEN.aktenzeichen
        assert meta["title"] == SAMPLE_SCHREIBEN.betreff
        assert meta["datum"] == "2023-01-01"
        assert meta["year"] == 2023
        assert meta["source"] == "bundesfinanzministerium.de"
        assert meta["url"] == SAMPLE_SCHREIBEN.url

    def test_section_label_in_metadata(self):
        sections = [("II. Sonderregelung", "Text " * 30)]
        docs = _build_documents(sections, SAMPLE_SCHREIBEN, 2023)
        assert docs[0].metadata["section"] == "II. Sonderregelung"

    def test_empty_section_label(self):
        sections = [("", "Ganzer Text ohne Abschnitt " * 10)]
        docs = _build_documents(sections, SAMPLE_SCHREIBEN, 2023)
        assert docs[0].metadata["section"] == ""

    def test_text_contains_header(self):
        sections = [("", "Inhalt " * 20)]
        docs = _build_documents(sections, SAMPLE_SCHREIBEN, 2023)
        text = docs[0].text
        assert SAMPLE_SCHREIBEN.aktenzeichen in text
        assert SAMPLE_SCHREIBEN.datum in text

    def test_multiple_sections_produce_multiple_docs(self):
        sections = [
            ("I. Erster", "Text " * 30),
            ("II. Zweiter", "Text " * 30),
            ("III. Dritter", "Text " * 30),
        ]
        docs = _build_documents(sections, SAMPLE_SCHREIBEN, 2025)
        assert len(docs) == 3

    def test_year_in_metadata(self):
        sections = [("", "Text " * 20)]
        docs = _build_documents(sections, SAMPLE_SCHREIBEN, 2025)
        assert docs[0].metadata["year"] == 2025


# ─── _parse_html ──────────────────────────────────────────────────────────────

class TestParseHtml:
    def test_nav_and_footer_stripped(self):
        docs = _parse_html(SIMPLE_HTML, SAMPLE_SCHREIBEN, 2023)
        for doc in docs:
            assert "Navigation hier" not in doc.text
            assert "Impressum" not in doc.text

    def test_produces_documents(self):
        docs = _parse_html(SIMPLE_HTML, SAMPLE_SCHREIBEN, 2023)
        assert len(docs) >= 1

    def test_metadata_set_correctly(self):
        docs = _parse_html(SIMPLE_HTML, SAMPLE_SCHREIBEN, 2023)
        assert all(d.metadata["law"] == "BMF" for d in docs)
        assert all(d.metadata["year"] == 2023 for d in docs)


# ─── bmf_catalog ──────────────────────────────────────────────────────────────

class TestBmfCatalog:
    def test_catalog_not_empty(self):
        assert len(BMF_SCHREIBEN) >= 10

    def test_all_ids_unique(self):
        ids = [s.id for s in BMF_SCHREIBEN]
        assert len(ids) == len(set(ids)), "Doppelte IDs im Katalog"

    def test_all_aktenzeichen_nonempty(self):
        for s in BMF_SCHREIBEN:
            assert s.aktenzeichen.strip(), f"{s.id}: leeres Aktenzeichen"

    def test_all_urls_nonempty(self):
        for s in BMF_SCHREIBEN:
            assert s.url.startswith("http"), f"{s.id}: ungültige URL"

    def test_all_datum_iso_format(self):
        import re
        pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for s in BMF_SCHREIBEN:
            assert pattern.match(s.datum), f"{s.id}: Datum nicht ISO: {s.datum}"

    def test_get_active_schreiben_filters_superseded(self):
        from ingest.scrapers.bmf_catalog import BmfSchreiben
        # Inject a superseded entry temporarily
        superseded = BmfSchreiben(
            id="superseded_test",
            aktenzeichen="IV X - S 0000/00/00",
            datum="2020-01-01",
            betreff="Altes Schreiben",
            url="https://example.com/old.pdf",
            valid_from_year=2020,
            thema="Test",
            superseded=True,
        )
        import ingest.scrapers.bmf_catalog as cat
        cat.BMF_SCHREIBEN.append(superseded)  # type: ignore[attr-defined]
        try:
            active = get_active_schreiben(2025)
            ids = [s.id for s in active]
            assert "superseded_test" not in ids
        finally:
            cat.BMF_SCHREIBEN.remove(superseded)  # type: ignore[attr-defined]

    def test_get_active_schreiben_filters_future_year(self):
        # valid_from_year=2026 should not appear for year=2025
        active_2025 = get_active_schreiben(2025)
        for s in active_2025:
            assert s.valid_from_year <= 2025

    def test_get_by_id_found(self):
        first = BMF_SCHREIBEN[0]
        result = get_by_id(first.id)
        assert result.id == first.id

    def test_get_by_id_not_found(self):
        with pytest.raises(KeyError):
            get_by_id("does_not_exist_xyz")
