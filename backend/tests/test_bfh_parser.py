"""
Unit tests for ingest/scrapers/bfh.py and ingest/scrapers/bfh_catalog.py.

All tests are offline — no network, no embeddings, no Chroma.
HTML content is synthesized in-memory to match the real bundesfinanzhof.de structure.
"""
import re

import pytest

from ingest.scrapers.bfh_catalog import (
    BFH_URTEILE,
    BfhUrteil,
    get_active_urteile,
    get_by_id,
)
from ingest.scrapers.bfh import (
    _items_to_text,
    _fallback_text_split,
    _build_documents,
    _parse_html,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

SAMPLE_URTEIL = BfhUrteil(
    id="test_urteil",
    aktenzeichen="VI R 99/99",
    ecli="ECLI:DE:BFH:2023:U.010123.VIR99.99.0",
    datum="2023-01-01",
    senat="VI. Senat",
    betreff="Testsachverhalt zur Überprüfung des Parsers",
    url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE999999999/",
    thema="Test",
    valid_from_year=2023,
    bstbl_aufgenommen=False,
)

# Minimal HTML matching the real BFH site structure (div.m-article__body)
SAMPLE_HTML_STRUCTURED = """
<html><body>
<header class="page-header"><nav>Navigation</nav></header>
<main>
<div class="m-article__body">
  <p class="ecli highlighted">ECLI:DE:BFH:2023:U.010123.VIR99.99.0</p>
  <p class="spruchkoerper">BFH VI. Senat</p>

  <h2 class="a-headline__2">Leitsätze</h2>
  <div class="m-decisions">
    <p>1. Erster Leitsatz des Urteils mit ausreichend langem Text für den Mindest-Chunk.</p>
    <p>2. Zweiter Leitsatz mit ebenfalls ausreichend langem Text zur Vermeidung des Filters.</p>
  </div>

  <h2 class="a-headline__2">Tenor</h2>
  <div class="m-decisions">
    <p>Die Revision des Beklagten wird als unbegründet zurückgewiesen.</p>
    <p>Die Kosten des Revisionsverfahrens hat der Beklagte zu tragen.</p>
  </div>

  <h2 class="a-headline__2">Tatbestand</h2>
  <div class="m-decisions">
    <h3>I.</h3>
    <ol class="m-decisions__list">
      <li class="m-decisions__item" data-rd="1">
        <p>Die Kläger und Revisionskläger sind für das Streitjahr 2021 zusammen zur
        Einkommensteuer veranlagt worden. Der Kläger erzielt Einkünfte aus nicht-
        selbständiger Arbeit als Arbeitnehmer bei der Firma Mustermann GmbH.</p>
      </li>
      <li class="m-decisions__item" data-rd="2">
        <p>Er nutzt in seiner Wohnung einen Raum ausschließlich für berufliche
        Zwecke. Das Finanzamt versagte den Abzug der Arbeitszimmerkosten.</p>
      </li>
    </ol>
    <h3>II.</h3>
    <ol class="m-decisions__list">
      <li class="m-decisions__item" data-rd="3">
        <p>Das Finanzgericht wies die Klage ab. Es führte aus, das Arbeitszimmer
        sei nicht erforderlich gewesen, da dem Kläger ein Büro zur Verfügung stehe.</p>
      </li>
    </ol>
  </div>

  <h2 class="a-headline__2">Entscheidungsgründe</h2>
  <div class="m-decisions">
    <h3>I.</h3>
    <ol class="m-decisions__list">
      <li class="m-decisions__item" data-rd="10">
        <p>Die Revision ist begründet. Sie führt zur Aufhebung des angefochtenen
        Urteils und zur Zurückverweisung der Sache an das Finanzgericht.</p>
      </li>
      <li class="m-decisions__item" data-rd="11">
        <p>Nach § 9 Abs. 5 i.V.m. § 4 Abs. 5 Satz 1 Nr. 6b EStG sind Aufwendungen
        für ein häusliches Arbeitszimmer nur abziehbar, wenn es den Mittelpunkt der
        gesamten betrieblichen und beruflichen Betätigung bildet.</p>
      </li>
    </ol>
    <h3>II.</h3>
    <ol class="m-decisions__list">
      <li class="m-decisions__item" data-rd="15">
        <p>Entgegen der Auffassung des Finanzgerichts kommt es auf die objektive
        Erforderlichkeit des Arbeitszimmers nicht an. Maßgebend ist allein die
        tatsächliche ausschließliche berufliche Nutzung des Raumes.</p>
      </li>
    </ol>
  </div>
</div>
</main>
<footer>Impressum</footer>
</body></html>
""".encode("utf-8")

# HTML ohne erkannte Struktur — löst Fallback aus
SAMPLE_HTML_UNSTRUCTURED = """
<html><body>
<div class="m-article__body">
  <p>Leitsätze</p>
  <p>Kurze Einleitung.</p>
  <p>Entscheidungsgründe</p>
  <p>Der Senat entscheidet wie folgt. Die Revision hat Erfolg, da das Finanzgericht
  die Rechtslage verkannt hat. Nach ständiger Rechtsprechung des BFH sind die
  Aufwendungen für ein häusliches Arbeitszimmer als Werbungskosten abziehbar,
  wenn die übrigen Voraussetzungen erfüllt sind. Die Gegenauffassung des
  Finanzamts überzeugt nicht. Das Urteil ist daher aufzuheben.</p>
</div>
</body></html>
""".encode("utf-8")

LONG_TEXT_NO_STRUCTURE = (
    "Dieses Urteil enthält keine erkennbaren Abschnittsüberschriften. "
    "Der gesamte Text wird als ein Chunk zurückgegeben. " * 10
)


# ─── _items_to_text ───────────────────────────────────────────────────────────

class TestItemsToText:
    def test_with_rn_numbers(self):
        result = _items_to_text([("1", "Erster Satz."), ("2", "Zweiter Satz.")])
        assert "Rn. 1: Erster Satz." in result
        assert "Rn. 2: Zweiter Satz." in result

    def test_without_rn_numbers(self):
        result = _items_to_text([("", "Leitsatz Eins."), ("", "Leitsatz Zwei.")])
        assert "Rn." not in result
        assert "Leitsatz Eins." in result

    def test_mixed_rn_and_plain(self):
        result = _items_to_text([("1", "Mit Nummer."), ("", "Ohne Nummer.")])
        assert "Rn. 1: Mit Nummer." in result
        assert "Ohne Nummer." in result

    def test_empty_list(self):
        assert _items_to_text([]) == ""

    def test_separator_between_items(self):
        result = _items_to_text([("1", "A"), ("2", "B")])
        assert "\n\n" in result


# ─── _fallback_text_split ─────────────────────────────────────────────────────

class TestFallbackTextSplit:
    def test_splits_on_known_headings(self):
        text = "Leitsätze\nKurz.\n\nEntscheidungsgründe\n" + "x" * 200
        parts = _fallback_text_split(text)
        labels = [label for label, _ in parts]
        assert "Entscheidungsgründe" in labels

    def test_short_sections_filtered(self):
        text = "Leitsätze\nZu kurz.\n\nTatbestand\n" + "y" * 200
        parts = _fallback_text_split(text)
        # Leitsätze body "Zu kurz." < _MIN_CHUNK_CHARS → only Tatbestand passes
        labels = [label for label, _ in parts]
        assert "Tatbestand" in labels
        assert "Leitsätze" not in labels

    def test_fallback_whole_doc_when_no_headings(self):
        parts = _fallback_text_split(LONG_TEXT_NO_STRUCTURE)
        assert len(parts) == 1
        label, body = parts[0]
        assert label == ""
        assert len(body) >= 120

    def test_empty_text_returns_empty(self):
        assert _fallback_text_split("") == []
        assert _fallback_text_split("   \n\n   ") == []


# ─── _build_documents ─────────────────────────────────────────────────────────

class TestBuildDocuments:
    def test_metadata_fields_present(self):
        sections = [("Leitsätze", "Wichtiger Leitsatz " * 10)]
        docs = _build_documents(sections, SAMPLE_URTEIL, 2023)
        assert len(docs) == 1
        meta = docs[0].metadata
        assert meta["law"] == "BFH"
        assert meta["paragraph"] == SAMPLE_URTEIL.aktenzeichen
        assert meta["ecli"] == SAMPLE_URTEIL.ecli
        assert meta["datum"] == "2023-01-01"
        assert meta["senat"] == "VI. Senat"
        assert meta["year"] == 2023
        assert meta["source"] == "bundesfinanzhof.de"
        assert meta["url"] == SAMPLE_URTEIL.url
        assert meta["bstbl"] == "nein"

    def test_bstbl_ja_flag(self):
        urteil_bstbl = BfhUrteil(
            **{**SAMPLE_URTEIL.__dict__, "id": "bstbl_test", "bstbl_aufgenommen": True}
        )
        sections = [("Tenor", "Entscheidungsformel " * 10)]
        docs = _build_documents(sections, urteil_bstbl, 2023)
        assert docs[0].metadata["bstbl"] == "ja"

    def test_section_label_in_metadata(self):
        sections = [("Entscheidungsgründe — I.", "Text " * 30)]
        docs = _build_documents(sections, SAMPLE_URTEIL, 2023)
        assert docs[0].metadata["section"] == "Entscheidungsgründe — I."

    def test_header_contains_aktenzeichen(self):
        sections = [("", "Inhalt " * 20)]
        docs = _build_documents(sections, SAMPLE_URTEIL, 2023)
        assert SAMPLE_URTEIL.aktenzeichen in docs[0].text

    def test_header_contains_bstbl_hint_when_not_aufgenommen(self):
        sections = [("", "Inhalt " * 20)]
        docs = _build_documents(sections, SAMPLE_URTEIL, 2023)
        assert "BStBl" in docs[0].text or "Verwaltung" in docs[0].text

    def test_multiple_sections_produce_multiple_docs(self):
        sections = [
            ("Leitsätze", "Erster Leitsatz " * 15),
            ("Tatbestand", "Tatbestand-Text " * 15),
            ("Entscheidungsgründe", "Begründung " * 15),
        ]
        docs = _build_documents(sections, SAMPLE_URTEIL, 2025)
        assert len(docs) == 3

    def test_year_in_metadata(self):
        sections = [("", "Text " * 20)]
        docs = _build_documents(sections, SAMPLE_URTEIL, 2024)
        assert docs[0].metadata["year"] == 2024


# ─── _parse_html ──────────────────────────────────────────────────────────────

class TestParseHtml:
    def test_produces_documents(self):
        docs = _parse_html(SAMPLE_HTML_STRUCTURED, SAMPLE_URTEIL, 2023)
        assert len(docs) >= 1

    def test_nav_and_footer_stripped(self):
        docs = _parse_html(SAMPLE_HTML_STRUCTURED, SAMPLE_URTEIL, 2023)
        for doc in docs:
            assert "Navigation" not in doc.text
            assert "Impressum" not in doc.text

    def test_major_sections_found(self):
        docs = _parse_html(SAMPLE_HTML_STRUCTURED, SAMPLE_URTEIL, 2023)
        labels = {d.metadata["section"] for d in docs}
        # Leitsätze and Entscheidungsgründe sections should be present
        assert any(
            "Leitsätze" in label or "Entscheidungsgründe" in label
            for label in labels
        )

    def test_subsections_split(self):
        docs = _parse_html(SAMPLE_HTML_STRUCTURED, SAMPLE_URTEIL, 2023)
        labels = {d.metadata["section"] for d in docs}
        # Tatbestand and Entscheidungsgründe have h3 subsections I. and II.
        subsection_labels = [label for label in labels if " — " in label]
        assert len(subsection_labels) >= 2

    def test_rn_numbers_in_text(self):
        docs = _parse_html(SAMPLE_HTML_STRUCTURED, SAMPLE_URTEIL, 2023)
        all_text = " ".join(d.text for d in docs)
        assert "Rn." in all_text

    def test_metadata_set_correctly(self):
        docs = _parse_html(SAMPLE_HTML_STRUCTURED, SAMPLE_URTEIL, 2023)
        assert all(d.metadata["law"] == "BFH" for d in docs)
        assert all(d.metadata["year"] == 2023 for d in docs)

    def test_fallback_for_unstructured_html(self):
        docs = _parse_html(SAMPLE_HTML_UNSTRUCTURED, SAMPLE_URTEIL, 2023)
        # Should still produce at least one document via fallback
        assert len(docs) >= 1


# ─── bfh_catalog ──────────────────────────────────────────────────────────────

class TestBfhCatalog:
    def test_catalog_not_empty(self):
        assert len(BFH_URTEILE) >= 15

    def test_all_ids_unique(self):
        ids = [u.id for u in BFH_URTEILE]
        assert len(ids) == len(set(ids)), "Doppelte IDs im Katalog"

    def test_all_aktenzeichen_nonempty(self):
        for u in BFH_URTEILE:
            assert u.aktenzeichen.strip(), f"{u.id}: leeres Aktenzeichen"

    def test_all_urls_start_with_https(self):
        for u in BFH_URTEILE:
            assert u.url.startswith("https"), f"{u.id}: URL nicht HTTPS"

    def test_all_urls_contain_bundesfinanzhof(self):
        for u in BFH_URTEILE:
            assert "bundesfinanzhof.de" in u.url, f"{u.id}: URL nicht auf bundesfinanzhof.de"

    def test_all_datum_iso_format(self):
        pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for u in BFH_URTEILE:
            assert pattern.match(u.datum), f"{u.id}: Datum nicht ISO: {u.datum}"

    def test_get_active_urteile_filters_superseded(self):
        superseded = BfhUrteil(
            id="superseded_test",
            aktenzeichen="X R 99/00",
            datum="2020-01-01",
            senat="X. Senat",
            betreff="Altes Urteil",
            url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE000000001/",
            thema="Test",
            valid_from_year=2020,
            superseded=True,
        )
        import ingest.scrapers.bfh_catalog as cat
        cat.BFH_URTEILE.append(superseded)  # type: ignore[attr-defined]
        try:
            active = get_active_urteile(2025)
            ids = [u.id for u in active]
            assert "superseded_test" not in ids
        finally:
            cat.BFH_URTEILE.remove(superseded)  # type: ignore[attr-defined]

    def test_get_active_urteile_filters_future_year(self):
        future = BfhUrteil(
            id="future_test",
            aktenzeichen="X R 1/30",
            datum="2030-01-01",
            senat="X. Senat",
            betreff="Zukünftiges Urteil",
            url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE000000002/",
            thema="Test",
            valid_from_year=2030,
        )
        import ingest.scrapers.bfh_catalog as cat
        cat.BFH_URTEILE.append(future)  # type: ignore[attr-defined]
        try:
            active_2025 = get_active_urteile(2025)
            ids = [u.id for u in active_2025]
            assert "future_test" not in ids
        finally:
            cat.BFH_URTEILE.remove(future)  # type: ignore[attr-defined]

    def test_get_by_id_found(self):
        first = BFH_URTEILE[0]
        result = get_by_id(first.id)
        assert result.id == first.id

    def test_get_by_id_not_found(self):
        with pytest.raises(KeyError):
            get_by_id("does_not_exist_xyz")
