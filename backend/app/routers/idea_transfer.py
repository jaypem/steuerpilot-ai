from fastapi import APIRouter, HTTPException, Request

from app.idea_transfer import (
    evaluate_and_persist_case,
    get_case,
    save_case_draft,
)
from app.models.idea_transfer import (
    IdeaTransferCase,
    IdeaTransferDraftRequest,
    IdeaTransferEvaluateRequest,
)

router = APIRouter(prefix="/api/idea-transfer", tags=["idea-transfer"])


@router.post("/evaluate", response_model=IdeaTransferCase)
async def evaluate_case_route(
    request: IdeaTransferEvaluateRequest,
    req: Request,
) -> IdeaTransferCase:
    db = req.app.state.db
    return await evaluate_and_persist_case(
        db=db,
        session_id=request.session_id,
        case_kind=request.case_kind,
        answers=request.answers,
        tax_year=request.tax_year,
    )


@router.get("/{session_id}", response_model=IdeaTransferCase)
async def get_case_route(session_id: str, req: Request) -> IdeaTransferCase:
    db = req.app.state.db
    case = await get_case(db, session_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Idea-transfer case not found")
    return case


@router.put("/{session_id}", response_model=IdeaTransferCase)
async def save_case_route(
    session_id: str,
    request: IdeaTransferDraftRequest,
    req: Request,
) -> IdeaTransferCase:
    db = req.app.state.db
    return await save_case_draft(
        db=db,
        session_id=session_id,
        case_kind=request.case_kind,
        answers=request.answers,
    )
