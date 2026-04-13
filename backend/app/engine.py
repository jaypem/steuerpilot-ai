"""
Chat engine for steuerpilot-ai (Phase 11 — no RAG yet).

Builds a LlamaIndex SimpleChatEngine seeded with SQLite conversation
history and streams the response through a ResponseStreamProcessor that
separates the visible text from the trailing ===STEUERPILOT_META=== block.

Phase 12 will replace SimpleChatEngine with ContextChatEngine + retriever.
"""
import logging
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

import aiosqlite
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.memory import ChatMemoryBuffer

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
            # Split paragraph and section from the first token
            # e.g. "§4 Abs. 5 Nr. 6b" → paragraph="§4", section="Abs. 5 Nr. 6b"
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
    Splits an LLM token stream into:
      - visible text (everything before METADATA_SENTINEL)
      - metadata block (everything after METADATA_SENTINEL)

    Tokens are passed one-by-one via feed(); the processor keeps a rolling
    tail buffer to detect sentinels that span multiple tokens.  Call flush()
    after the last token to drain the tail buffer.
    """

    def __init__(self) -> None:
        self._sentinel = METADATA_SENTINEL
        self._s_len = len(self._sentinel)
        self._tail = ""          # rolling buffer for cross-token sentinel detection
        self._in_meta = False
        self._meta_buf = ""

    def feed(self, token: str) -> str:
        """Return the text fragment to emit (may be empty string)."""
        if self._in_meta:
            self._meta_buf += token
            return ""

        combined = self._tail + token
        idx = combined.find(self._sentinel)

        if idx != -1:
            # Sentinel found — emit text before it, buffer the rest as meta
            text_before = combined[:idx]
            self._in_meta = True
            self._meta_buf = combined[idx + self._s_len :]
            self._tail = ""
            return text_before

        # Keep the last (s_len - 1) chars in the tail in case the sentinel
        # is split across the current and next token.
        if len(combined) >= self._s_len:
            safe = combined[: len(combined) - self._s_len + 1]
            self._tail = combined[len(combined) - self._s_len + 1 :]
            return safe

        self._tail = combined
        return ""

    def flush(self) -> str:
        """Drain tail buffer at end of stream."""
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


# ─── Public API ───────────────────────────────────────────────────────────────


def _sse(chunk: StreamChunk) -> str:
    return f"data: {chunk.model_dump_json()}\n\n"


async def stream_chat_response(
    message: str,
    session_id: str,
    db: aiosqlite.Connection,
) -> AsyncGenerator[str, None]:
    """
    Full SSE generator for one chat exchange.

    Loads conversation history → builds SimpleChatEngine →
    streams LLM response → extracts metadata → emits SSE events.
    """
    try:
        history = await _load_history(db, session_id)

        memory = ChatMemoryBuffer.from_defaults(
            chat_history=history,
            token_limit=8192,
        )

        engine = SimpleChatEngine.from_defaults(
            llm=get_llm(),
            memory=memory,
            system_prompt=SYSTEM_PROMPT,
        )

        processor = ResponseStreamProcessor()
        streaming_response = await engine.astream_chat(message)

        async for token in streaming_response.async_response_gen():
            text = processor.feed(token)
            if text:
                yield _sse(TextChunk(content=text))

        # Flush tail
        tail = processor.flush()
        if tail:
            yield _sse(TextChunk(content=tail))

        # Emit metadata events
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
