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

_CREATE_IDEA_TRANSFER_CASES = """
CREATE TABLE IF NOT EXISTS idea_transfer_cases (
    session_id         TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    case_kind          TEXT NOT NULL CHECK(case_kind IN ('own_gmbh_sale', 'family_transfer')),
    status             TEXT NOT NULL CHECK(status IN ('draft', 'completed')),
    answers_json       TEXT NOT NULL,
    result_json        TEXT,
    summary_message_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
    updated_at         TEXT NOT NULL
)
"""


async def init_db(db: aiosqlite.Connection) -> None:
    """Create tables and enable foreign-key enforcement."""
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute(_CREATE_SESSIONS)
    await db.execute(_CREATE_MESSAGES)
    await db.execute(_CREATE_IDEA_TRANSFER_CASES)
    await db.commit()
