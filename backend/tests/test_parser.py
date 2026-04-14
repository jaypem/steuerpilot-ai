"""
Unit tests for ingest/parser.py.

Tests run against a minimal in-memory XML fixture — no network, no embeddings.
"""
from pathlib import Path

import pytest

from ingest.parser import _extract_text, _para_url, parse_law_xml
from tests.conftest import MINIMAL_XML


# ─── _extract_text ────────────────────────────────────────────────────────────

def test_extract_text_basic():
    from bs4 import BeautifulSoup
    soup = BeautifulSoup("<root><P>Hello</P> <P>World</P></root>", "lxml-xml")
    text = _extract_text(soup.find("root"))
    assert "Hello" in text
    assert "World" in text


def test_extract_text_nested():
    from bs4 import BeautifulSoup
    soup = BeautifulSoup("<root><div><span>inner</span></div></root>", "lxml-xml")
    text = _extract_text(soup.find("root"))
    assert "inner" in text


# ─── _para_url ────────────────────────────────────────────────────────────────

def test_para_url_estg():
    url = _para_url("EStG", "§ 9")
    assert url is not None
    assert "estg" in url
    assert "__9.html" in url


def test_para_url_estg_alpha():
    url = _para_url("EStG", "§ 4a")
    assert url is not None
    assert "__4a.html" in url


def test_para_url_unknown_law():
    assert _para_url("XYZ", "§ 1") is None


def test_para_url_no_para():
    assert _para_url("EStG", "Einleitung") is None


# ─── parse_law_xml ────────────────────────────────────────────────────────────

def test_parse_returns_only_paragraph_norms(xml_file: Path):
    """Non-§ norms (Einleitung, norms without gliederungseinheit) are skipped."""
    docs = parse_law_xml(xml_file, "EStG", 2025)
    # MINIMAL_XML has 2 § norms, 1 non-§ norm, 1 norm without gliederungseinheit
    assert len(docs) == 2


def test_parse_metadata_fields(xml_file: Path):
    docs = parse_law_xml(xml_file, "EStG", 2025)
    para4 = next(d for d in docs if d.metadata["paragraph"] == "§ 4")

    assert para4.metadata["law"] == "EStG"
    assert para4.metadata["title"] == "Betriebsausgaben"
    assert para4.metadata["year"] == 2025
    assert para4.metadata["url"] != ""


def test_parse_year_stored_as_int(xml_file: Path):
    docs = parse_law_xml(xml_file, "EStG", 2025)
    for doc in docs:
        assert isinstance(doc.metadata["year"], int)


def test_parse_text_content(xml_file: Path):
    docs = parse_law_xml(xml_file, "EStG", 2025)
    para4 = next(d for d in docs if d.metadata["paragraph"] == "§ 4")
    assert "Betriebsausgaben" in para4.text
    assert "Aufwendungen" in para4.text


def test_parse_text_includes_header(xml_file: Path):
    """Document text should start with '§ N LAW — Title'."""
    docs = parse_law_xml(xml_file, "EStG", 2025)
    para9 = next(d for d in docs if d.metadata["paragraph"] == "§ 9")
    assert para9.text.startswith("§ 9 EStG")


def test_parse_different_year(xml_file: Path):
    docs = parse_law_xml(xml_file, "AO", 2024)
    assert all(d.metadata["year"] == 2024 for d in docs)
    assert all(d.metadata["law"] == "AO" for d in docs)


def test_parse_empty_xml(tmp_path: Path):
    empty = tmp_path / "empty.xml"
    empty.write_text(
        '<?xml version="1.0" encoding="UTF-8"?><dokumente></dokumente>',
        encoding="utf-8",
    )
    docs = parse_law_xml(empty, "EStG", 2025)
    assert docs == []
