"""
Unit tests for ingest/parser.py.

Tests run against a minimal in-memory XML fixture — no network, no embeddings.
"""
from pathlib import Path

from llama_index.core.schema import NodeRelationship

from ingest.parser import ParsedLaw, _abs_section, _extract_text, _para_url, parse_law_xml


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


# ─── _abs_section ─────────────────────────────────────────────────────────────

def test_abs_section_simple():
    assert _abs_section("(1) Gewinn ist…") == "Abs. 1"


def test_abs_section_alpha():
    assert _abs_section("(4a) Mehraufwendungen…") == "Abs. 4a"


def test_abs_section_no_prefix():
    assert _abs_section("Werbungskosten sind…") == ""


def test_abs_section_footnote():
    assert _abs_section("(+++ § 9: Zur Anwendung…") == ""


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


# ─── parse_law_xml — return type ──────────────────────────────────────────────

def test_parse_returns_parsed_law(xml_file: Path):
    result = parse_law_xml(xml_file, "EStG", 2025)
    assert isinstance(result, ParsedLaw)


def test_parse_returns_only_paragraph_norms(xml_file: Path):
    """Non-§ norms (Inhaltsübersicht, norms without <enbez>) are skipped."""
    result = parse_law_xml(xml_file, "EStG", 2025)
    # MINIMAL_XML has 2 § norms, 1 non-§ norm, 1 norm without <enbez>
    assert len(result.parent_nodes) == 2


# ─── parse_law_xml — parent nodes ─────────────────────────────────────────────

def test_parse_metadata_fields(xml_file: Path):
    result = parse_law_xml(xml_file, "EStG", 2025)
    para4 = next(n for n in result.parent_nodes if n.metadata["paragraph"] == "§ 4")

    assert para4.metadata["law"] == "EStG"
    assert para4.metadata["title"] == "Betriebsausgaben"
    assert para4.metadata["year"] == 2025
    assert para4.metadata["url"] != ""
    assert para4.metadata["node_level"] == "parent"
    assert para4.metadata["section"] == ""


def test_parse_year_stored_as_int(xml_file: Path):
    result = parse_law_xml(xml_file, "EStG", 2025)
    for node in result.all_nodes:
        assert isinstance(node.metadata["year"], int)


def test_parse_text_content(xml_file: Path):
    result = parse_law_xml(xml_file, "EStG", 2025)
    para4 = next(n for n in result.parent_nodes if n.metadata["paragraph"] == "§ 4")
    assert "Betriebsausgaben" in para4.text
    assert "Aufwendungen" in para4.text


def test_parse_text_includes_header(xml_file: Path):
    """Parent text should start with '§ N LAW — Title'."""
    result = parse_law_xml(xml_file, "EStG", 2025)
    para9 = next(n for n in result.parent_nodes if n.metadata["paragraph"] == "§ 9")
    assert para9.text.startswith("§ 9 EStG")


def test_parse_different_year(xml_file: Path):
    result = parse_law_xml(xml_file, "AO", 2024)
    assert all(n.metadata["year"] == 2024 for n in result.all_nodes)
    assert all(n.metadata["law"] == "AO" for n in result.all_nodes)


def test_parse_empty_xml(tmp_path: Path):
    empty = tmp_path / "empty.xml"
    empty.write_text(
        '<?xml version="1.0" encoding="UTF-8"?><dokumente></dokumente>',
        encoding="utf-8",
    )
    result = parse_law_xml(empty, "EStG", 2025)
    assert result.parent_nodes == []
    assert result.child_nodes == []


# ─── parse_law_xml — child nodes ──────────────────────────────────────────────

def test_parse_child_count(xml_file: Path):
    """MINIMAL_XML: § 4 has 2 <P>, § 9 has 2 <P> → 4 children total."""
    result = parse_law_xml(xml_file, "EStG", 2025)
    assert len(result.child_nodes) == 4


def test_child_section_metadata(xml_file: Path):
    result = parse_law_xml(xml_file, "EStG", 2025)
    para4_children = [n for n in result.child_nodes if n.metadata["paragraph"] == "§ 4"]
    sections = {c.metadata["section"] for c in para4_children}
    assert "Abs. 1" in sections
    assert "Abs. 2" in sections


def test_child_node_level_metadata(xml_file: Path):
    result = parse_law_xml(xml_file, "EStG", 2025)
    for child in result.child_nodes:
        assert child.metadata["node_level"] == "child"


def test_child_text_includes_context(xml_file: Path):
    """Child text should include law/paragraph context for good embeddings."""
    result = parse_law_xml(xml_file, "EStG", 2025)
    para4_children = [n for n in result.child_nodes if n.metadata["paragraph"] == "§ 4"]
    for child in para4_children:
        assert "§ 4" in child.text
        assert "EStG" in child.text


# ─── parse_law_xml — parent ↔ child relationships ────────────────────────────

def test_child_references_parent(xml_file: Path):
    result = parse_law_xml(xml_file, "EStG", 2025)
    para4 = next(n for n in result.parent_nodes if n.metadata["paragraph"] == "§ 4")
    para4_children = [n for n in result.child_nodes if n.metadata["paragraph"] == "§ 4"]

    for child in para4_children:
        assert NodeRelationship.PARENT in child.relationships
        assert child.relationships[NodeRelationship.PARENT].node_id == para4.node_id


def test_parent_references_children(xml_file: Path):
    result = parse_law_xml(xml_file, "EStG", 2025)
    para4 = next(n for n in result.parent_nodes if n.metadata["paragraph"] == "§ 4")
    para4_children = [n for n in result.child_nodes if n.metadata["paragraph"] == "§ 4"]

    assert NodeRelationship.CHILD in para4.relationships
    child_ids = {ri.node_id for ri in para4.relationships[NodeRelationship.CHILD]}
    assert all(c.node_id in child_ids for c in para4_children)


def test_stable_ids_are_unique(xml_file: Path):
    result = parse_law_xml(xml_file, "EStG", 2025)
    all_ids = [n.node_id for n in result.all_nodes]
    assert len(all_ids) == len(set(all_ids)), "Duplicate node IDs detected"


# ─── parse_law_xml — fussnoten excluded ───────────────────────────────────────

def test_fussnoten_excluded_from_children(xml_file: Path):
    """<fussnoten> block in MINIMAL_XML must not appear in any child node."""
    result = parse_law_xml(xml_file, "EStG", 2025)
    for child in result.child_nodes:
        assert "ignoriert" not in child.text
        assert "(+++" not in child.text
