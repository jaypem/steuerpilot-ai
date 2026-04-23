from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


def _assert_utc_aware(timestamp: str) -> datetime:
    parsed = datetime.fromisoformat(timestamp)
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)
    return parsed


@pytest_asyncio.fixture
async def api_client(db):
    from app.main import app

    app.state.db = db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_session_detail_normalizes_legacy_naive_timestamps(api_client, db):
    await db.execute(
        """
        INSERT INTO sessions (id, title, created_at, updated_at, message_count, total_saving)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("legacy-session", "Legacy", "2026-04-23T10:00:00", "2026-04-23T11:00:00", 1, 0),
    )
    await db.execute(
        """
        INSERT INTO messages (id, session_id, role, content, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("msg-1", "legacy-session", "user", "Hallo", "2026-04-23T10:05:00"),
    )
    await db.commit()

    resp = await api_client.get("/api/sessions/legacy-session")

    assert resp.status_code == 200
    body = resp.json()
    _assert_utc_aware(body["created_at"])
    _assert_utc_aware(body["updated_at"])
    _assert_utc_aware(body["messages"][0]["created_at"])


@pytest.mark.asyncio
async def test_rename_session_returns_utc_aware_updated_at(api_client, db):
    await db.execute(
        """
        INSERT INTO sessions (id, title, created_at, updated_at, message_count, total_saving)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "sess-rename",
            "Alt",
            "2024-04-23T10:00:00+00:00",
            "2024-04-23T10:00:00+00:00",
            0,
            0,
        ),
    )
    await db.commit()

    resp = await api_client.patch(
        "/api/sessions/sess-rename",
        json={"title": "Neu"},
    )

    assert resp.status_code == 200
    body = resp.json()
    _assert_utc_aware(body["created_at"])
    updated_at = _assert_utc_aware(body["updated_at"])
    assert updated_at >= datetime.fromisoformat("2024-04-23T10:00:00+00:00")
