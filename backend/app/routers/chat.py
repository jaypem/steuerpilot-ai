import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import aiosqlite
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.engine import stream_chat_response
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


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _sse(chunk: StreamChunk) -> str:
    return f"data: {chunk.model_dump_json()}\n\n"


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def _ensure_session(
    db: aiosqlite.Connection, session_id: str, title: str
) -> None:
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
    sources: list[SourceChunk],
    risk: RiskBadgeChunk | None,
    saving: SavingChunk | None,
) -> None:
    now = _now()

    await db.execute(
        "INSERT INTO messages (id, session_id, role, content, created_at) VALUES (?, ?, 'user', ?, ?)",
        (str(uuid.uuid4()), session_id, user_content, now),
    )

    sources_json = (
        json.dumps([s.model_dump() for s in sources]) if sources else None
    )
    risk_json = risk.model_dump_json() if risk else None
    saving_amount = saving.amount if saving else None

    await db.execute(
        """
        INSERT INTO messages
          (id, session_id, role, content, sources, risk_badge, saving_amount, created_at)
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
        SET updated_at    = ?,
            message_count = message_count + 2,
            total_saving  = total_saving + ?
        WHERE id = ?
        """,
        (now, saving_amount or 0, session_id),
    )
    await db.commit()


# ─── Wrapper generator — collects metadata for persistence ───────────────────


async def _tracked_stream(
    request: ChatRequest,
    db: aiosqlite.Connection,
) -> AsyncGenerator[str, None]:
    """
    Wraps stream_chat_response to intercept metadata events so we can
    persist the full exchange to SQLite after the stream completes.
    """
    session_id = request.session_id or str(uuid.uuid4())
    await _ensure_session(db, session_id, request.message[:60])

    text_parts: list[str] = []
    sources: list[SourceChunk] = []
    risk: RiskBadgeChunk | None = None
    saving: SavingChunk | None = None

    async for raw_sse in stream_chat_response(
        request.message,
        session_id,
        db,
        request.tax_year,
    ):
        yield raw_sse

        # Parse the emitted chunk to track metadata (no additional LLM calls)
        if not raw_sse.startswith("data: "):
            continue
        try:
            payload = json.loads(raw_sse[6:])
        except Exception:
            continue

        t = payload.get("type")
        if t == "text":
            text_parts.append(payload.get("content", ""))
        elif t == "source":
            sources.append(SourceChunk(**{k: v for k, v in payload.items() if k != "type"}))
        elif t == "risk_badge":
            risk = RiskBadgeChunk(**{k: v for k, v in payload.items() if k != "type"})
        elif t == "saving":
            saving = SavingChunk(amount=payload["amount"])
        elif t == "done":
            # Persist after the done event has already been yielded
            await _persist_exchange(
                db=db,
                session_id=session_id,
                user_content=request.message,
                assistant_content="".join(text_parts),
                sources=sources,
                risk=risk,
                saving=saving,
            )


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
        _tracked_stream(request, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
