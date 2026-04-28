from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import DB_PATH, init_db
from app.routers import chat, health, idea_transfer, instagram_check, scan, sessions

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await init_db(db)
    app.state.db = db

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    await db.close()


app = FastAPI(
    title="steuerpilot-ai",
    description="RAG-basierter Steuerberater-Assistent",
    version="0.1.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(idea_transfer.router)
app.include_router(instagram_check.router)
app.include_router(scan.router)
