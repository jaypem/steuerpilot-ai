import aiosqlite

DB_PATH = "steuerpilot.db"

_CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    id           TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    message_count INTEGER NOT NULL DEFAULT 0,
    total_saving  INTEGER NOT NULL DEFAULT 0
)
"""

_CREATE_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
    id           TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role         TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content      TEXT NOT NULL,
    sources      TEXT,        -- JSON array  | NULL
    risk_badge   TEXT,        -- JSON object | NULL
    saving_amount INTEGER,
    created_at   TEXT NOT NULL
)
"""


async def init_db(db: aiosqlite.Connection) -> None:
    """Create tables and enable foreign-key enforcement."""
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute(_CREATE_SESSIONS)
    await db.execute(_CREATE_MESSAGES)
    await db.commit()
