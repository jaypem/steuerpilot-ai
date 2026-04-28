from fastapi import APIRouter, File, Form, Request, UploadFile

from app.instagram_check import (
    analyze_instagram_images,
    evaluate_instagram_check,
    get_instagram_check,
    get_tax_prep_items,
    save_instagram_check,
)
from app.models.instagram_check import (
    InstagramCheckEvaluateRequest,
    InstagramCheckSaveRequest,
    InstagramPostCheck,
    TaxPrepItem,
)

router = APIRouter(tags=["instagram-check"])


@router.post("/api/instagram-check/analyze", response_model=InstagramPostCheck)
async def analyze_route(
    request: Request,
    session_id: str = Form(...),
    tax_year: int = Form(2025),
    images: list[UploadFile] = File(...),
) -> InstagramPostCheck:
    del tax_year
    return await analyze_instagram_images(
        db=request.app.state.db,
        session_id=session_id,
        images=images,
    )


@router.get("/api/instagram-check/{session_id}", response_model=InstagramPostCheck)
async def get_check_route(session_id: str, request: Request) -> InstagramPostCheck:
    check = await get_instagram_check(request.app.state.db, session_id)
    if check is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Instagram-Check nicht gefunden")
    return check


@router.put("/api/instagram-check/{session_id}", response_model=InstagramPostCheck)
async def save_check_route(
    session_id: str,
    body: InstagramCheckSaveRequest,
    request: Request,
) -> InstagramPostCheck:
    return await save_instagram_check(request.app.state.db, session_id, body)


@router.post("/api/instagram-check/evaluate", response_model=InstagramPostCheck)
async def evaluate_route(
    body: InstagramCheckEvaluateRequest,
    request: Request,
) -> InstagramPostCheck:
    return await evaluate_instagram_check(
        db=request.app.state.db,
        session_id=body.session_id,
        tax_year=body.tax_year,
    )


@router.get("/api/tax-prep/{session_id}", response_model=list[TaxPrepItem])
async def get_tax_prep_route(session_id: str, request: Request) -> list[TaxPrepItem]:
    return await get_tax_prep_items(request.app.state.db, session_id)
