from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TrafficLight = Literal["green", "yellow", "red"]
CaseKind = Literal["own_gmbh_sale", "family_transfer"]
CaseStatus = Literal["draft", "completed"]
DimensionId = Literal[
    "private_origin",
    "employment_proximity",
    "transferability",
    "valuation",
    "acquirer_use_plan",
    "transfer_tax",
]
OriginScope = Literal["private", "professional", "unclear"]
YesNoUnclear = Literal["yes", "no", "unclear"]
ConsiderationType = Literal["cash", "asset_transfer", "mixed", "unclear"]
ValuationMode = Literal["external", "internal", "none", "unclear"]
DocumentationStatus = Literal["complete", "partial", "none", "unclear"]
UsefulLifeYears = Literal[3, 5, 10, "unclear"]


class IdeaTransferAnswers(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idea_summary: str | None = Field(default=None, max_length=2000)
    origin_scope: OriginScope | None = None
    connected_to_job_or_business: YesNoUnclear | None = None
    is_paid_transfer: YesNoUnclear | None = None
    purchase_price_eur: float | None = Field(default=None, ge=0)
    consideration_type: ConsiderationType | None = None
    buyer_use_plan_available: YesNoUnclear | None = None
    buyer_use_description: str | None = Field(default=None, max_length=2000)
    valuation_mode: ValuationMode | None = None
    documentation_status: DocumentationStatus | None = None
    family_value_alignment: YesNoUnclear | None = None
    useful_life_years: UsefulLifeYears | None = None


class IdeaTransferSource(BaseModel):
    law: str
    paragraph: str
    section: str = ""
    text: str
    url: str | None = None


class IdeaTransferDimension(BaseModel):
    id: DimensionId
    title: str
    traffic_light: TrafficLight
    summary: str


class IdeaTransferEvaluationResponse(BaseModel):
    traffic_light: TrafficLight
    headline: str
    summary_markdown: str
    estimated_tax_benefit_min_eur: int | None = None
    estimated_tax_benefit_mid_eur: int | None = None
    estimated_tax_benefit_max_eur: int | None = None
    annual_tax_benefit_mid_eur: int | None = None
    dimensions: list[IdeaTransferDimension]
    required_documents: list[str]
    next_actions: list[str]
    sources: list[IdeaTransferSource]
    assumptions: list[str] = []


class IdeaTransferCase(BaseModel):
    session_id: str
    case_kind: CaseKind
    status: CaseStatus
    answers: IdeaTransferAnswers
    result: IdeaTransferEvaluationResponse | None = None
    updated_at: datetime


class IdeaTransferDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_kind: CaseKind
    answers: IdeaTransferAnswers


class IdeaTransferEvaluateRequest(IdeaTransferDraftRequest):
    session_id: str
    tax_year: int = 2025
