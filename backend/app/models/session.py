from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    sources: list[dict[str, Any]] | None = None
    risk_badge: dict[str, Any] | None = None
    saving_amount: int | None = None
    created_at: datetime


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    total_saving: int


class SessionDetailResponse(SessionResponse):
    messages: list[MessageResponse]
