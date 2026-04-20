from typing import Literal

from pydantic import BaseModel, Field


# ─── Request ─────────────────────────────────────────────────────────────────


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    history: list[HistoryMessage] = []
    tax_year: int = 2025


# ─── SSE chunk types ─────────────────────────────────────────────────────────


class TextChunk(BaseModel):
    type: Literal["text"] = "text"
    content: str


class SourceChunk(BaseModel):
    type: Literal["source"] = "source"
    law: str
    paragraph: str
    section: str
    text: str
    url: str | None = None


class RiskBadgeChunk(BaseModel):
    type: Literal["risk_badge"] = "risk_badge"
    level: Literal["low", "medium", "high"]
    label: str
    explanation: str


class SavingChunk(BaseModel):
    type: Literal["saving"] = "saving"
    amount: int


class StatusChunk(BaseModel):
    type: Literal["status"] = "status"
    label: str


class DoneChunk(BaseModel):
    type: Literal["done"] = "done"


class ErrorChunk(BaseModel):
    type: Literal["error"] = "error"
    message: str


# Union used in type hints for documentation / future typed dispatch
StreamChunk = (
    TextChunk
    | SourceChunk
    | RiskBadgeChunk
    | SavingChunk
    | StatusChunk
    | DoneChunk
    | ErrorChunk
)
