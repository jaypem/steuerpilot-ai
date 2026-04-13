from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import chat, health

settings = get_settings()

app = FastAPI(
    title="steuerpilot-ai",
    description="RAG-basierter Steuerberater-Assistent",
    version="0.1.0",
)

# ─── CORS ────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Router ──────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(chat.router)
