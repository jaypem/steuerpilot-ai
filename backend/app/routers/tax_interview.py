from fastapi import APIRouter, HTTPException, Request

from app.models.tax_interview import (
    AnswerPayload,
    StartInterviewRequest,
    TaxInterview,
)
from app.tax_interview import (
    ensure_interview_session,
    evaluate_interview,
    get_interview,
    save_answer,
)

router = APIRouter(prefix="/api/tax-interview", tags=["tax-interview"])


@router.get("/{session_id}", response_model=TaxInterview)
async def get_interview_route(session_id: str, req: Request) -> TaxInterview:
    interview = await get_interview(req.app.state.db, session_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Tax interview not found")
    return interview


@router.post("/{session_id}/start", response_model=TaxInterview)
async def start_interview_route(
    session_id: str,
    body: StartInterviewRequest,
    req: Request,
) -> TaxInterview:
    """Create or reset the interview for this session."""
    db = req.app.state.db
    await ensure_interview_session(db, session_id, body.tax_year)
    interview = await get_interview(db, session_id)
    if interview is None:
        raise HTTPException(status_code=500, detail="Failed to load interview after start")
    return interview


@router.put("/{session_id}/answer", response_model=TaxInterview)
async def answer_route(
    session_id: str,
    payload: AnswerPayload,
    req: Request,
) -> TaxInterview:
    """Save one answer and return the updated interview with the next question."""
    db = req.app.state.db
    interview = await get_interview(db, session_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Tax interview not found")
    return await save_answer(db, session_id, payload)


@router.post("/{session_id}/evaluate", response_model=TaxInterview)
async def evaluate_route(session_id: str, req: Request) -> TaxInterview:
    """Run RAG+LLM evaluation across all answered categories and return findings."""
    db = req.app.state.db
    interview = await get_interview(db, session_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="Tax interview not found")
    if interview.status == "in_progress":
        raise HTTPException(
            status_code=422,
            detail="Interview is still in progress — answer all questions first",
        )
    await evaluate_interview(db, session_id, interview.tax_year, interview.answers)
    result = await get_interview(db, session_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Failed to reload interview after evaluation")
    return result
