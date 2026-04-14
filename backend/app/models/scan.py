from typing import Literal

from pydantic import BaseModel, Field


# ─── Request ─────────────────────────────────────────────────────────────────


class ExpenseItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    amount: float = Field(..., ge=0)


class ScanRequest(BaseModel):
    expenses: list[ExpenseItem] = Field(..., min_length=1, max_length=50)
    # Optional free-text context: e.g. "Angestellter, 2 Kinder, Homeoffice 3 Tage/Woche"
    context: str | None = Field(None, max_length=1000)
    tax_year: int = 2025


# ─── Result ──────────────────────────────────────────────────────────────────


class SourceRef(BaseModel):
    law: str
    paragraph: str
    section: str = ""


class ScannedExpense(BaseModel):
    description: str
    amount: float
    deductible: bool
    # Partial deductibility is common (e.g. 50 % for mixed-use items)
    deductible_amount: float
    # Conservative saving estimate at 30 % average tax rate
    saving_estimate: int
    risk: Literal["low", "medium", "high"]
    explanation: str
    sources: list[SourceRef]


class ScanResult(BaseModel):
    items: list[ScannedExpense]
    total_saving_estimate: int
    # Positions the user likely has but didn't mention — proactive suggestions
    missing_positions: list[str]
