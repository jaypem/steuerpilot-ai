"""
Tests for the chat engine and /api/chat endpoint.

Covers:
- ResponseStreamProcessor: sentinel detection, token-split edge cases
- _parse_meta_block: SOURCE / RISK / SAVING parsing
- /api/chat endpoint: SSE format, error handling (stream_chat_response mocked)
"""
import json
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.engine import ResponseStreamProcessor, _parse_meta_block
from app.models.chat import DoneChunk, RiskBadgeChunk, SavingChunk, SourceChunk, TextChunk
from app.prompts import METADATA_SENTINEL


# ─── ResponseStreamProcessor ─────────────────────────────────────────────────

class TestResponseStreamProcessor:
    def test_plain_text_passthrough(self):
        """
        Short tokens (< sentinel length) are kept in the rolling tail buffer
        and only released via flush(). The combined output must equal the input.
        """
        proc = ResponseStreamProcessor()
        t1 = proc.feed("Hello ")
        t2 = proc.feed("World")
        tail = proc.flush()
        combined = t1 + t2 + tail
        assert "Hello " in combined
        assert "World" in combined
        assert proc.metadata == ""

    def test_sentinel_in_single_token(self):
        proc = ResponseStreamProcessor()
        result = proc.feed("Text before" + METADATA_SENTINEL + "META")
        assert result == "Text before"
        assert proc.metadata == "META"

    def test_sentinel_split_across_two_tokens(self):
        """Sentinel split across token boundary must be detected correctly."""
        proc = ResponseStreamProcessor()
        # Split the sentinel at a known boundary
        half = len(METADATA_SENTINEL) // 2
        first_half = METADATA_SENTINEL[:half]
        second_half = METADATA_SENTINEL[half:]

        text1 = proc.feed("Answer text" + first_half)
        text2 = proc.feed(second_half + "METADATA_CONTENT")

        # Visible text should contain "Answer text", metadata should contain "METADATA_CONTENT"
        combined_visible = text1 + text2
        assert "Answer text" in combined_visible
        assert METADATA_SENTINEL not in combined_visible
        assert proc.metadata == "METADATA_CONTENT"

    def test_sentinel_split_one_char_at_a_time(self):
        """Feed the sentinel character-by-character."""
        proc = ResponseStreamProcessor()
        visible_parts = []

        text = "Response" + METADATA_SENTINEL + "SOURCE: §9|EStG|Text"
        for char in text:
            part = proc.feed(char)
            if part:
                visible_parts.append(part)

        tail = proc.flush()
        if tail:
            visible_parts.append(tail)

        visible = "".join(visible_parts)
        assert "Response" in visible
        assert METADATA_SENTINEL not in visible
        assert proc.metadata == "SOURCE: §9|EStG|Text"

    def test_flush_returns_buffered_tail(self):
        proc = ResponseStreamProcessor()
        # Feed text that is shorter than the sentinel — stays in tail
        proc.feed("Hi")
        tail = proc.flush()
        assert "Hi" in tail

    def test_no_sentinel_flush_returns_all(self):
        proc = ResponseStreamProcessor()
        proc.feed("Part1 ")
        proc.feed("Part2")
        visible = proc.flush()
        assert "Part1" in visible

    def test_metadata_accumulates_after_sentinel(self):
        proc = ResponseStreamProcessor()
        proc.feed("text" + METADATA_SENTINEL + "line1\n")
        proc.feed("line2\n")
        proc.feed("line3")
        assert "line1" in proc.metadata
        assert "line2" in proc.metadata
        assert "line3" in proc.metadata

    def test_nothing_passes_through_after_sentinel(self):
        proc = ResponseStreamProcessor()
        proc.feed("pre" + METADATA_SENTINEL)
        text = proc.feed("should be metadata not text")
        assert text == ""


# ─── _parse_meta_block ───────────────────────────────────────────────────────

class TestParseMetaBlock:
    def test_source_minimal(self):
        meta = _parse_meta_block("SOURCE: §9 Abs. 1|EStG")
        assert len(meta.sources) == 1
        assert meta.sources[0].law == "EStG"
        assert meta.sources[0].paragraph == "§9"

    def test_source_with_section_and_text(self):
        meta = _parse_meta_block("SOURCE: §9 Abs. 1 Satz 3|EStG|Werbungskosten")
        src = meta.sources[0]
        assert src.paragraph == "§9"
        assert "Abs. 1" in src.section
        assert src.text == "Werbungskosten"

    def test_multiple_sources(self):
        raw = "SOURCE: §9|EStG\nSOURCE: §4 Abs. 5|EStG|Betriebsausgaben"
        meta = _parse_meta_block(raw)
        assert len(meta.sources) == 2
        laws = {s.law for s in meta.sources}
        assert laws == {"EStG"}

    def test_risk_low(self):
        meta = _parse_meta_block("RISK: low|Eindeutige Rechtslage|Klarer Paragrafenbezug")
        assert meta.risk is not None
        assert meta.risk.level == "low"
        assert meta.risk.label == "Eindeutige Rechtslage"

    def test_risk_high(self):
        meta = _parse_meta_block("RISK: high|Streitig|Noch kein BFH-Urteil")
        assert meta.risk is not None
        assert meta.risk.level == "high"

    def test_risk_invalid_level_ignored(self):
        meta = _parse_meta_block("RISK: critical|label|explanation")
        assert meta.risk is None

    def test_saving(self):
        meta = _parse_meta_block("SAVING: 360")
        assert meta.saving is not None
        assert meta.saving.amount == 360

    def test_saving_zero(self):
        meta = _parse_meta_block("SAVING: 0")
        assert meta.saving is not None
        assert meta.saving.amount == 0

    def test_full_block(self):
        raw = (
            "SOURCE: §9 Abs. 1|EStG|Werbungskosten\n"
            "RISK: medium|Grauzone|Streitig beim BFH\n"
            "SAVING: 252"
        )
        meta = _parse_meta_block(raw)
        assert len(meta.sources) == 1
        assert meta.risk is not None and meta.risk.level == "medium"
        assert meta.saving is not None and meta.saving.amount == 252

    def test_empty_block(self):
        meta = _parse_meta_block("")
        assert meta.sources == []
        assert meta.risk is None
        assert meta.saving is None

    def test_whitespace_lines_ignored(self):
        meta = _parse_meta_block("\n  \nSAVING: 100\n  \n")
        assert meta.saving is not None
        assert meta.saving.amount == 100


# ─── /api/chat endpoint ───────────────────────────────────────────────────────

@pytest.fixture
def mock_stream_simple():
    """Patch stream_chat_response to emit text → done."""
    async def _gen(message, session_id, db, tax_year=2025):
        yield f"data: {TextChunk(content='Hallo Welt').model_dump_json()}\n\n"
        yield f"data: {DoneChunk().model_dump_json()}\n\n"

    with patch("app.routers.chat.stream_chat_response", side_effect=_gen):
        yield


@pytest.fixture
def mock_stream_with_meta():
    """Patch stream_chat_response to emit text + source + risk + saving + done."""
    async def _gen(message, session_id, db, tax_year=2025):
        yield f"data: {TextChunk(content='Empfehlung').model_dump_json()}\n\n"
        yield f"data: {SourceChunk(law='EStG', paragraph='§9', section='Abs. 1', text='').model_dump_json()}\n\n"
        yield f"data: {RiskBadgeChunk(level='low', label='Klar', explanation='eindeutig').model_dump_json()}\n\n"
        yield f"data: {SavingChunk(amount=360).model_dump_json()}\n\n"
        yield f"data: {DoneChunk().model_dump_json()}\n\n"

    with patch("app.routers.chat.stream_chat_response", side_effect=_gen):
        yield


@pytest_asyncio.fixture
async def api_client(db):
    """
    AsyncClient wired to the FastAPI app.
    ASGITransport does NOT trigger the lifespan, so we bypass it by
    injecting the in-memory db fixture directly into app.state.
    """
    from app.main import app
    app.state.db = db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_chat_returns_200_with_sse(api_client, mock_stream_simple):
    resp = await api_client.post(
        "/api/chat",
        json={"message": "Homeoffice Pauschale?", "session_id": "sess-1"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_chat_sse_contains_text_and_done(api_client, mock_stream_simple):
    resp = await api_client.post(
        "/api/chat",
        json={"message": "Test", "session_id": "sess-2"},
    )
    body = resp.text
    chunks = [
        json.loads(line[6:])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    types = [c["type"] for c in chunks]
    assert "text" in types
    assert "done" in types


@pytest.mark.asyncio
async def test_chat_sse_meta_chunks_present(api_client, mock_stream_with_meta):
    resp = await api_client.post(
        "/api/chat",
        json={"message": "Werbungskosten?", "session_id": "sess-3"},
    )
    chunks = [
        json.loads(line[6:])
        for line in resp.text.splitlines()
        if line.startswith("data: ")
    ]
    types = [c["type"] for c in chunks]
    assert "source" in types
    assert "risk_badge" in types
    assert "saving" in types
    assert "done" in types


@pytest.mark.asyncio
async def test_chat_forwards_tax_year(api_client):
    seen: list[int] = []

    async def _gen(message, session_id, db, tax_year=2025):
        seen.append(tax_year)
        yield f"data: {DoneChunk().model_dump_json()}\n\n"

    with patch("app.routers.chat.stream_chat_response", side_effect=_gen):
        resp = await api_client.post(
            "/api/chat",
            json={
                "message": "Homeoffice",
                "session_id": "sess-tax-year",
                "tax_year": 2024,
            },
        )

    assert resp.status_code == 200
    assert seen == [2024]


@pytest.mark.asyncio
async def test_chat_requires_message(api_client):
    resp = await api_client.post("/api/chat", json={"message": ""})
    # Empty message violates min_length=1 constraint → 422
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint(api_client):
    resp = await api_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
