import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import aiosqlite
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.models.chat import (
    ChatRequest,
    DoneChunk,
    ErrorChunk,
    RiskBadgeChunk,
    SavingChunk,
    SourceChunk,
    StreamChunk,
    TextChunk,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# ─── Dummy content (replaced by LlamaIndex + Claude in Phase 11) ─────────────

_DUMMY_ANSWER = (
    "Ja, Homeoffice-Kosten können Sie steuerlich geltend machen. "
    "Seit 2023 gilt die erhöhte Tagespauschale von **6 € pro Tag** "
    "(max. **1.260 € im Jahr**, also 210 Tage).\n\n"
    "Alternativ können Sie ein häusliches Arbeitszimmer absetzen, "
    "wenn es ausschließlich beruflich genutzt wird — dann sind die "
    "tatsächlichen anteiligen Kosten absetzbar, was bei größeren "
    "Wohnungen deutlich mehr einbringen kann.\n\n"
    "Haben Sie auch Arbeitsmittel wie Laptop, Monitor oder Bürostuhl gekauft?"
)

_DUMMY_SOURCE = SourceChunk(
    law="EStG",
    paragraph="§ 4",
    section="Abs. 5 Nr. 6b",
    text=(
        "Für jeden Kalendertag, an dem der Steuerpflichtige seine betriebliche "
        "oder berufliche Tätigkeit ausschließlich in der häuslichen Wohnung ausübt, "
        "kann er einen Betrag von 6 Euro abziehen, höchstens 1 260 Euro im "
        "Wirtschafts- oder Kalenderjahr."
    ),
)

_DUMMY_RISK = RiskBadgeChunk(
    level="low",
    label="Unstreitig",
    explanation="Seit 2023 gesetzlich klar geregelt in § 4 Abs. 5 Nr. 6b EStG.",
)

_DUMMY_SAVING = SavingChunk(amount=252)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _sse(chunk: StreamChunk) -> str:
    return f"data: {chunk.model_dump_json()}\n\n"


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def _ensure_session(db: aiosqlite.Connection, session_id: str, title: str) -> None:
    """Insert session row if it doesn't exist yet."""
    now = _now()
    await db.execute(
        """
        INSERT INTO sessions (id, title, created_at, updated_at, message_count, total_saving)
        VALUES (?, ?, ?, ?, 0, 0)
        ON CONFLICT(id) DO NOTHING
        """,
        (session_id, title, now, now),
    )
    await db.commit()


async def _persist_exchange(
    db: aiosqlite.Connection,
    session_id: str,
    user_content: str,
    assistant_content: str,
    source: SourceChunk | None,
    risk: RiskBadgeChunk | None,
    saving: SavingChunk | None,
) -> None:
    """Write user + assistant messages and update session stats."""
    now = _now()

    await db.execute(
        """
        INSERT INTO messages (id, session_id, role, content, created_at)
        VALUES (?, ?, 'user', ?, ?)
        """,
        (str(uuid.uuid4()), session_id, user_content, now),
    )

    sources_json = json.dumps([source.model_dump()]) if source else None
    risk_json = risk.model_dump_json() if risk else None
    saving_amount = saving.amount if saving else None

    await db.execute(
        """
        INSERT INTO messages (id, session_id, role, content, sources, risk_badge, saving_amount, created_at)
        VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            session_id,
            assistant_content,
            sources_json,
            risk_json,
            saving_amount,
            now,
        ),
    )

    await db.execute(
        """
        UPDATE sessions
        SET updated_at     = ?,
            message_count  = message_count + 2,
            total_saving   = total_saving + ?
        WHERE id = ?
        """,
        (now, saving_amount or 0, session_id),
    )

    await db.commit()


# ─── Generator ───────────────────────────────────────────────────────────────


async def _stream_chat(
    request: ChatRequest, db: aiosqlite.Connection
) -> AsyncGenerator[str, None]:
    """
    Yield SSE-formatted strings, then persist the exchange to SQLite.

    Event sequence:
      text (one per word, 35 ms apart) → source → risk_badge → saving → done
      error (only on exception)
    """
    session_id = request.session_id or str(uuid.uuid4())
    title = request.message[:60]
    assistant_parts: list[str] = []

    try:
        await _ensure_session(db, session_id, title)

        # Stream text word by word
        words = _DUMMY_ANSWER.split(" ")
        for i, word in enumerate(words):
            content = word if i == len(words) - 1 else word + " "
            assistant_parts.append(content)
            yield _sse(TextChunk(content=content))
            await asyncio.sleep(0.035)

        # Metadata events
        yield _sse(_DUMMY_SOURCE)
        yield _sse(_DUMMY_RISK)
        yield _sse(_DUMMY_SAVING)
        yield _sse(DoneChunk())

        # Persist after stream is fully sent
        await _persist_exchange(
            db=db,
            session_id=session_id,
            user_content=request.message,
            assistant_content="".join(assistant_parts),
            source=_DUMMY_SOURCE,
            risk=_DUMMY_RISK,
            saving=_DUMMY_SAVING,
        )

    except Exception as exc:
        logger.exception("Error in chat stream")
        yield _sse(ErrorChunk(message=str(exc)))


# ─── Endpoint ─────────────────────────────────────────────────────────────────


@router.post("/chat")
async def chat(request: ChatRequest, req: Request) -> StreamingResponse:
    """
    Stream a tax-advice response as Server-Sent Events and persist the exchange.

    Each event is a JSON object on a `data:` line with a `type` discriminator:
    `text` | `source` | `risk_badge` | `saving` | `done` | `error`
    """
    db: aiosqlite.Connection = req.app.state.db
    return StreamingResponse(
        _stream_chat(request, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
