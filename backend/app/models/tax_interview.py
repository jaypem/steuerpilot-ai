from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.idea_transfer import IdeaTransferSource

TaxInterviewStatus = Literal["in_progress", "completed", "evaluated"]
AnswerType = Literal["bool", "choice", "number", "text"]
TrafficLight = Literal["green", "yellow", "red"]

# Re-export for convenience (engine and router import from here)
InterviewSource = IdeaTransferSource


class InterviewQuestion(BaseModel):
    id: str
    category: str
    text: str
    answer_type: AnswerType
    options: list[str] | None = None


class AnswerPayload(BaseModel):
    """Request body for the answer endpoint."""

    question_id: str
    answer: bool | int | str


class StartInterviewRequest(BaseModel):
    """Request body for the start/reset endpoint."""

    tax_year: int


class TaxInterviewFinding(BaseModel):
    category: str
    title: str
    traffic_light: TrafficLight
    explanation: str
    estimated_saving_eur: int | None = None
    required_evidence: list[str]
    sources: list[InterviewSource]


class TaxInterview(BaseModel):
    session_id: str
    status: TaxInterviewStatus
    tax_year: int
    answers: dict[str, bool | int | str]
    next_question: InterviewQuestion | None  # None when all applicable questions answered
    findings: list[TaxInterviewFinding] | None = None
    updated_at: datetime
