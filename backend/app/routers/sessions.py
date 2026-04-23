import json

import aiosqlite
from fastapi import APIRouter, HTTPException, Request

from app.models.session import MessageResponse, SessionDetailResponse, SessionRenameRequest, SessionResponse
from app.timestamps import parse_timestamp, utc_now

router = APIRouter(prefix="/api", tags=["sessions"])


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _row_to_session(row: aiosqlite.Row) -> SessionResponse:
    return SessionResponse(
        id=row["id"],
        title=row["title"],
        created_at=parse_timestamp(row["created_at"]),
        updated_at=parse_timestamp(row["updated_at"]),
        message_count=row["message_count"],
        total_saving=row["total_saving"],
    )


def _row_to_message(row: aiosqlite.Row) -> MessageResponse:
    return MessageResponse(
        id=row["id"],
        session_id=row["session_id"],
        role=row["role"],
        content=row["content"],
        sources=json.loads(row["sources"]) if row["sources"] else None,
        risk_badge=json.loads(row["risk_badge"]) if row["risk_badge"] else None,
        saving_amount=row["saving_amount"],
        created_at=parse_timestamp(row["created_at"]),
    )


def _db(request: Request) -> aiosqlite.Connection:
    return request.app.state.db


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(request: Request) -> list[SessionResponse]:
    """Return all sessions ordered by last activity (newest first)."""
    db = _db(request)
    async with db.execute(
        "SELECT * FROM sessions ORDER BY updated_at DESC"
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_session(r) for r in rows]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str, request: Request) -> SessionDetailResponse:
    """Return a single session with its full message history."""
    db = _db(request)

    async with db.execute(
        "SELECT * FROM sessions WHERE id = ?", (session_id,)
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    async with db.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    ) as cursor:
        msg_rows = await cursor.fetchall()

    return SessionDetailResponse(
        **_row_to_session(row).model_dump(),
        messages=[_row_to_message(m) for m in msg_rows],
    )


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def rename_session(
    session_id: str, body: SessionRenameRequest, request: Request
) -> SessionResponse:
    """Update the title of a session."""
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title must not be empty")

    db = _db(request)
    now = utc_now()

    async with db.execute(
        "SELECT id FROM sessions WHERE id = ?", (session_id,)
    ) as cursor:
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Session not found")

    await db.execute(
        "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
        (title, now, session_id),
    )
    await db.commit()

    async with db.execute(
        "SELECT * FROM sessions WHERE id = ?", (session_id,)
    ) as cursor:
        row = await cursor.fetchone()

    return _row_to_session(row)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, request: Request) -> None:
    """Delete a session and all its messages (CASCADE)."""
    db = _db(request)

    async with db.execute(
        "SELECT id FROM sessions WHERE id = ?", (session_id,)
    ) as cursor:
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Session not found")

    await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    await db.commit()
