"""
Chat engine for steuerpilot-ai.

Phase 12: ContextChatEngine with HybridRetriever (dense + BM25 + cross-encoder).
Falls back to SimpleChatEngine when no RAG index is available (e.g. first run
before 'steuerpilot ingest' has been executed).

The response stream is processed by ResponseStreamProcessor which separates
visible text from the trailing ===STEUERPILOT_META=== metadata block.
"""
import logging
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

import aiosqlite
from llama_index.core.chat_engine import ContextChatEngine, SimpleChatEngine
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.memory import ChatMemoryBuffer

from app.config import get_settings
from app.index import get_index, has_indexed_data
from app.llm import get_llm
from app.models.chat import (
    DoneChunk,
    ErrorChunk,
    RiskBadgeChunk,
    SavingChunk,
    SourceChunk,
    StreamChunk,
    TextChunk,
)
from app.prompts import METADATA_SENTINEL, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# ─── Metadata parsing ─────────────────────────────────────────────────────────

_SOURCE_RE = re.compile(
    r"^SOURCE:\s*(?P<para>§[^|]+?)\s*\|\s*(?P<law>[A-Z][A-Za-z]+)\s*(?:\|\s*(?P<text>.+))?$"
)
_RISK_RE = re.compile(
    r"^RISK:\s*(?P<level>low|medium|high)\s*\|\s*(?P<label>[^|]+?)\s*\|\s*(?P<explanation>.+)$"
)
_SAVING_RE = re.compile(r"^SAVING:\s*(?P<amount>\d+)$")


@dataclass
class ParsedMeta:
    sources: list[SourceChunk] = field(default_factory=list)
    risk: RiskBadgeChunk | None = None
    saving: SavingChunk | None = None


def _parse_meta_block(raw: str) -> ParsedMeta:
    meta = ParsedMeta()
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        m = _SOURCE_RE.match(line)
        if m:
            para_raw = m.group("para").strip()
            parts = para_raw.split(None, 1)
            paragraph = parts[0]
            section = parts[1] if len(parts) > 1 else ""
            meta.sources.append(
                SourceChunk(
                    law=m.group("law"),
                    paragraph=paragraph,
                    section=section,
                    text=(m.group("text") or "").strip(),
                )
            )
            continue

        m = _RISK_RE.match(line)
        if m:
            level = m.group("level")
            if level in ("low", "medium", "high"):
                meta.risk = RiskBadgeChunk(
                    level=level,  # type: ignore[arg-type]
                    label=m.group("label").strip(),
                    explanation=m.group("explanation").strip(),
                )
            continue

        m = _SAVING_RE.match(line)
        if m:
            meta.saving = SavingChunk(amount=int(m.group("amount")))

    return meta


# ─── Stream processor ─────────────────────────────────────────────────────────


class ResponseStreamProcessor:
    """
    Splits the LLM token stream into visible text and the trailing metadata block.
    Keeps a rolling tail buffer to detect sentinels split across tokens.
    """

    def __init__(self) -> None:
        self._sentinel = METADATA_SENTINEL
        self._s_len = len(self._sentinel)
        self._tail = ""
        self._in_meta = False
        self._meta_buf = ""

    def feed(self, token: str) -> str:
        if self._in_meta:
            self._meta_buf += token
            return ""

        combined = self._tail + token
        idx = combined.find(self._sentinel)

        if idx != -1:
            text_before = combined[:idx]
            self._in_meta = True
            self._meta_buf = combined[idx + self._s_len :]
            self._tail = ""
            return text_before

        if len(combined) >= self._s_len:
            safe = combined[: len(combined) - self._s_len + 1]
            self._tail = combined[len(combined) - self._s_len + 1 :]
            return safe

        self._tail = combined
        return ""

    def flush(self) -> str:
        tail, self._tail = self._tail, ""
        return tail

    @property
    def metadata(self) -> str:
        return self._meta_buf


# ─── History loader ───────────────────────────────────────────────────────────


async def _load_history(
    db: aiosqlite.Connection, session_id: str
) -> list[ChatMessage]:
    async with db.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    ) as cur:
        rows = await cur.fetchall()
    return [
        ChatMessage(
            role=MessageRole.USER if r["role"] == "user" else MessageRole.ASSISTANT,
            content=r["content"],
        )
        for r in rows
    ]


# ─── Engine factory ───────────────────────────────────────────────────────────


def _build_engine(
    memory: ChatMemoryBuffer,
    tax_year: int,
) -> ContextChatEngine | SimpleChatEngine:
    """
    Returns a ContextChatEngine if a RAG index is available,
    otherwise falls back to SimpleChatEngine.
    """
    settings = get_settings()
    llm = get_llm()

    if has_indexed_data(settings.chroma_path):
        import chromadb
        from ingest.store import COLLECTION_NAME
        from app.retriever import HybridRetriever

        client = chromadb.PersistentClient(path=settings.chroma_path)
        collection = client.get_or_create_collection(COLLECTION_NAME)
        index = get_index(settings.chroma_path)

        retriever = HybridRetriever(
            index=index,
            chroma_collection=collection,
            year=tax_year,
            chroma_path=settings.chroma_path,
        )
        logger.info("Using ContextChatEngine (RAG) for year %d", tax_year)
        return ContextChatEngine.from_defaults(
            retriever=retriever,
            llm=llm,
            memory=memory,
            system_prompt=SYSTEM_PROMPT,
            context_template=(
                "Relevante Gesetzestexte (Jahr {year}):\n"
                "---------------------\n"
                "{context_str}\n"
                "---------------------\n"
                "Beantworte die Frage auf Basis dieser Rechtsquellen."
            ).replace("{year}", str(tax_year)),
        )

    logger.warning(
        "Kein RAG-Index gefunden — SimpleChatEngine (kein Retrieval) wird verwendet. "
        "Bitte 'uv run steuerpilot ingest --year %d' ausführen.",
        tax_year,
    )
    return SimpleChatEngine.from_defaults(
        llm=llm,
        memory=memory,
        system_prompt=SYSTEM_PROMPT,
    )


# ─── SSE helper ──────────────────────────────────────────────────────────────


def _sse(chunk: StreamChunk) -> str:
    return f"data: {chunk.model_dump_json()}\n\n"


# ─── Public API ───────────────────────────────────────────────────────────────


async def stream_chat_response(
    message: str,
    session_id: str,
    db: aiosqlite.Connection,
    tax_year: int = 2025,
) -> AsyncGenerator[str, None]:
    """
    Full SSE generator for one chat exchange:
      load history → build engine → stream LLM response →
      extract metadata → emit SSE events.
    """
    try:
        history = await _load_history(db, session_id)
        memory = ChatMemoryBuffer.from_defaults(
            chat_history=history,
            token_limit=8192,
        )
        engine = _build_engine(memory, tax_year)
        processor = ResponseStreamProcessor()

        streaming_response = await engine.astream_chat(message)
        async for token in streaming_response.async_response_gen():
            text = processor.feed(token)
            if text:
                yield _sse(TextChunk(content=text))

        tail = processor.flush()
        if tail:
            yield _sse(TextChunk(content=tail))

        meta = _parse_meta_block(processor.metadata)
        for source in meta.sources:
            yield _sse(source)
        if meta.risk:
            yield _sse(meta.risk)
        if meta.saving:
            yield _sse(meta.saving)

        yield _sse(DoneChunk())

    except Exception as exc:
        logger.exception("Error in chat engine stream")
        yield _sse(ErrorChunk(message=str(exc)))
