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

_CREATE_INSTAGRAM_POST_CHECKS = """
CREATE TABLE IF NOT EXISTS instagram_post_checks (
    session_id         TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    status             TEXT NOT NULL CHECK(status IN ('draft', 'evaluated')),
    images_json        TEXT NOT NULL,
    claims_json        TEXT NOT NULL,
    evaluated_tips_json TEXT,
    summary_message_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
    updated_at         TEXT NOT NULL
)
"""

_CREATE_TAX_PREP_ITEMS = """
CREATE TABLE IF NOT EXISTS tax_prep_items (
    id                   TEXT PRIMARY KEY,
    session_id           TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    source               TEXT NOT NULL CHECK(source IN ('instagram_post')),
    source_claim_id      TEXT NOT NULL,
    title                TEXT NOT NULL,
    category             TEXT NOT NULL,
    return_bucket        TEXT NOT NULL,
    estimated_saving_eur INTEGER,
    risk_level           TEXT NOT NULL CHECK(risk_level IN ('low', 'medium', 'high')),
    required_evidence_json TEXT NOT NULL,
    summary              TEXT NOT NULL,
    status               TEXT NOT NULL CHECK(status IN ('confirmed')),
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL,
    UNIQUE(session_id, source, source_claim_id)
)
"""

_CREATE_TAX_INTERVIEWS = """
CREATE TABLE IF NOT EXISTS tax_interviews (
    session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    status     TEXT NOT NULL DEFAULT 'in_progress'
               CHECK(status IN ('in_progress', 'completed', 'evaluated')),
    tax_year   INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_CREATE_TAX_INTERVIEW_ANSWERS = """
CREATE TABLE IF NOT EXISTS tax_interview_answers (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES tax_interviews(session_id) ON DELETE CASCADE,
    question_id TEXT NOT NULL,
    answer      TEXT NOT NULL,  -- JSON-encoded value (bool/str/int)
    created_at  TEXT NOT NULL,
    UNIQUE(session_id, question_id)
)
"""

_CREATE_TAX_INTERVIEW_FINDINGS = """
CREATE TABLE IF NOT EXISTS tax_interview_findings (
    id                   TEXT PRIMARY KEY,
    session_id           TEXT NOT NULL REFERENCES tax_interviews(session_id) ON DELETE CASCADE,
    category             TEXT NOT NULL,
    title                TEXT NOT NULL,
    traffic_light        TEXT NOT NULL CHECK(traffic_light IN ('green', 'yellow', 'red')),
    explanation          TEXT NOT NULL,
    estimated_saving_eur INTEGER,
    required_evidence    TEXT NOT NULL,  -- JSON array of strings
    sources              TEXT NOT NULL,  -- JSON array of source objects
    created_at           TEXT NOT NULL
)
"""


async def init_db(db: aiosqlite.Connection) -> None:
    """Create tables and enable foreign-key enforcement."""
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute(_CREATE_SESSIONS)
    await db.execute(_CREATE_MESSAGES)
    await db.execute(_CREATE_IDEA_TRANSFER_CASES)
    await db.execute(_CREATE_INSTAGRAM_POST_CHECKS)
    await db.execute(_CREATE_TAX_PREP_ITEMS)
    await db.execute(_CREATE_TAX_INTERVIEWS)
    await db.execute(_CREATE_TAX_INTERVIEW_ANSWERS)
    await db.execute(_CREATE_TAX_INTERVIEW_FINDINGS)
    await db.commit()
