from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.idea_transfer import IdeaTransferSource


InstagramCheckStatus = Literal["draft", "evaluated"]
ClaimStatus = Literal["active", "removed"]
TrafficLight = Literal["green", "yellow", "red"]
RiskLevel = Literal["low", "medium", "high"]
TipCategory = Literal[
    "arbeitsmittel",
    "homeoffice",
    "pendeln",
    "weiterbildung",
    "sonderausgaben",
    "vorsorge",
    "haushaltsnahe_dienstleistungen",
    "kinder/familie",
    "kapital",
    "betriebsausgaben",
    "other",
]
ReturnBucket = Literal[
    "anlage_n",
    "betriebsausgaben",
    "sonderausgaben",
    "vorsorge",
    "haushaltsnahe_dienstleistungen",
    "kinder/familie",
    "kapital",
    "other",
]
TaxPrepSource = Literal["instagram_post"]
TaxPrepStatus = Literal["confirmed"]


class InstagramImageRef(BaseModel):
    id: str
    original_filename: str
    stored_path: str
    content_type: str
    size_bytes: int


class InstagramFollowUpQuestion(BaseModel):
    id: str
    prompt: str = Field(..., min_length=1, max_length=400)
    answer: str | None = Field(default=None, max_length=1000)


class InstagramClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    raw_text: str = Field(..., min_length=1, max_length=1000)
    edited_text: str = Field(..., min_length=1, max_length=1000)
    category: TipCategory
    return_bucket: ReturnBucket
    status: ClaimStatus = "active"
    selected_for_import: bool = False
    follow_up_questions: list[InstagramFollowUpQuestion]


class InstagramEvaluatedTip(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    title: str = Field(..., min_length=1, max_length=200)
    normalized_tip: str = Field(..., min_length=1, max_length=1200)
    category: TipCategory
    return_bucket: ReturnBucket
    traffic_light: TrafficLight
    explanation: str = Field(..., min_length=1, max_length=2000)
    estimated_saving_eur: int | None = Field(default=None, ge=0)
    required_evidence: list[str]
    sources: list[IdeaTransferSource]


class InstagramPostCheck(BaseModel):
    session_id: str
    status: InstagramCheckStatus
    images: list[InstagramImageRef]
    claims: list[InstagramClaim]
    evaluated_tips: list[InstagramEvaluatedTip] | None = None
    updated_at: datetime


class InstagramClaimUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    edited_text: str = Field(..., min_length=1, max_length=1000)
    category: TipCategory
    return_bucket: ReturnBucket
    status: ClaimStatus
    selected_for_import: bool = False
    follow_up_questions: list[InstagramFollowUpQuestion]


class InstagramCheckSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[InstagramClaimUpdate]


class InstagramCheckEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    tax_year: int = 2025


class TaxPrepItem(BaseModel):
    id: str
    session_id: str
    source: TaxPrepSource
    source_claim_id: str
    title: str
    category: TipCategory
    return_bucket: ReturnBucket
    estimated_saving_eur: int | None = None
    risk_level: RiskLevel
    required_evidence: list[str]
    summary: str
    status: TaxPrepStatus
    created_at: datetime
    updated_at: datetime
