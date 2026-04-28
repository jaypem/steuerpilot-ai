from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.models.idea_transfer import IdeaTransferSource
from app.models.instagram_check import InstagramEvaluatedTip


@pytest_asyncio.fixture
async def api_client(db, tmp_path, monkeypatch):
    from app.config import get_settings
    from app.main import app

    settings = get_settings()
    settings.upload_path = str(tmp_path / "uploads")
    app.state.db = db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


def _png_file(name: str, payload: bytes = b"fake-image"):
    return ("images", (name, payload, "image/png"))


def _build_green_tip(claim_id: str) -> InstagramEvaluatedTip:
    return InstagramEvaluatedTip(
        claim_id=claim_id,
        title="Homeoffice-Pauschale pruefen",
        normalized_tip="Pruefe die Homeoffice-Pauschale fuer regelmaessige Remote-Tage.",
        category="homeoffice",
        return_bucket="anlage_n",
        traffic_light="green",
        explanation="Nach den Antworten wirkt die Homeoffice-Pauschale fuer diesen Fall grundsaetzlich anwendbar.",
        estimated_saving_eur=240,
        required_evidence=["Aufstellung der Homeoffice-Tage"],
        sources=[
            IdeaTransferSource(
                law="EStG",
                paragraph="§ 4",
                section="Abs. 5 Nr. 6b",
                text="Homeoffice-Pauschale.",
            )
        ],
    )


@pytest.mark.asyncio
async def test_analyze_accepts_carousel_and_creates_claims(api_client, monkeypatch):
    monkeypatch.setattr(
        "app.instagram_check.extract_claim_texts",
        AsyncMock(
            return_value=[
                "Homeoffice-Pauschale nutzen",
                "Laptop als Arbeitsmittel absetzen",
            ]
        ),
    )

    response = await api_client.post(
        "/api/instagram-check/analyze",
        data={"session_id": "instagram-session", "tax_year": "2025"},
        files=[_png_file("post-1.png"), _png_file("post-2.png", b"more-data")],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "instagram-session"
    assert body["status"] == "draft"
    assert len(body["images"]) == 2
    assert len(body["claims"]) == 2
    assert body["claims"][0]["edited_text"] == "Homeoffice-Pauschale nutzen"
    assert body["claims"][1]["edited_text"] == "Laptop als Arbeitsmittel absetzen"


@pytest.mark.asyncio
async def test_put_persists_claim_edits_and_answers(api_client, monkeypatch):
    monkeypatch.setattr(
        "app.instagram_check.extract_claim_texts",
        AsyncMock(return_value=["Homeoffice-Pauschale nutzen"]),
    )
    analyze = await api_client.post(
        "/api/instagram-check/analyze",
        data={"session_id": "instagram-edit", "tax_year": "2025"},
        files=[_png_file("post.png")],
    )
    assert analyze.status_code == 200
    claim = analyze.json()["claims"][0]
    question = claim["follow_up_questions"][0]

    save_response = await api_client.put(
        "/api/instagram-check/instagram-edit",
        json={
            "claims": [
                {
                    "id": claim["id"],
                    "edited_text": "Homeoffice-Pauschale fuer 120 Tage nutzen",
                    "category": claim["category"],
                    "return_bucket": claim["return_bucket"],
                    "status": "active",
                    "selected_for_import": True,
                    "follow_up_questions": [
                        {
                            "id": question["id"],
                            "prompt": question["prompt"],
                            "answer": "120 Tage im Homeoffice, kein anderer Arbeitsplatz.",
                        },
                        {
                            "id": claim["follow_up_questions"][1]["id"],
                            "prompt": claim["follow_up_questions"][1]["prompt"],
                            "answer": "Eigene Aufstellung vorhanden.",
                        },
                    ],
                }
            ]
        },
    )

    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["claims"][0]["edited_text"] == "Homeoffice-Pauschale fuer 120 Tage nutzen"
    assert saved["claims"][0]["selected_for_import"] is True
    assert saved["claims"][0]["follow_up_questions"][0]["answer"].startswith("120 Tage")

    get_response = await api_client.get("/api/instagram-check/instagram-edit")
    assert get_response.status_code == 200
    reloaded = get_response.json()
    assert reloaded["claims"][0]["follow_up_questions"][1]["answer"] == "Eigene Aufstellung vorhanden."


@pytest.mark.asyncio
async def test_evaluate_creates_confirmed_tax_prep_items_and_summary(api_client, monkeypatch):
    monkeypatch.setattr(
        "app.instagram_check.extract_claim_texts",
        AsyncMock(return_value=["Homeoffice-Pauschale nutzen"]),
    )
    analyze = await api_client.post(
        "/api/instagram-check/analyze",
        data={"session_id": "instagram-eval", "tax_year": "2025"},
        files=[_png_file("post.png")],
    )
    claim = analyze.json()["claims"][0]

    save_response = await api_client.put(
        "/api/instagram-check/instagram-eval",
        json={
            "claims": [
                {
                    "id": claim["id"],
                    "edited_text": claim["edited_text"],
                    "category": claim["category"],
                    "return_bucket": claim["return_bucket"],
                    "status": "active",
                    "selected_for_import": True,
                    "follow_up_questions": [
                        {
                            "id": question["id"],
                            "prompt": question["prompt"],
                            "answer": "Ja",
                        }
                        for question in claim["follow_up_questions"]
                    ],
                }
            ]
        },
    )
    assert save_response.status_code == 200

    monkeypatch.setattr(
        "app.instagram_check._evaluate_claim",
        AsyncMock(return_value=_build_green_tip(claim["id"])),
    )

    evaluate_response = await api_client.post(
        "/api/instagram-check/evaluate",
        json={"session_id": "instagram-eval", "tax_year": 2025},
    )
    assert evaluate_response.status_code == 200
    evaluated = evaluate_response.json()
    assert evaluated["status"] == "evaluated"
    assert evaluated["evaluated_tips"][0]["traffic_light"] == "green"

    prep_response = await api_client.get("/api/tax-prep/instagram-eval")
    assert prep_response.status_code == 200
    prep_items = prep_response.json()
    assert len(prep_items) == 1
    assert prep_items[0]["source"] == "instagram_post"
    assert prep_items[0]["estimated_saving_eur"] == 240

    session_detail = await api_client.get("/api/sessions/instagram-eval")
    detail = session_detail.json()
    assert detail["message_count"] == 1
    assert detail["total_saving"] == 240
    assert "Instagram-Check" in detail["messages"][0]["content"]


@pytest.mark.asyncio
async def test_reupload_replaces_draft_but_keeps_confirmed_prep_items(api_client, monkeypatch):
    monkeypatch.setattr(
        "app.instagram_check.extract_claim_texts",
        AsyncMock(return_value=["Homeoffice-Pauschale nutzen"]),
    )
    analyze = await api_client.post(
        "/api/instagram-check/analyze",
        data={"session_id": "instagram-reupload", "tax_year": "2025"},
        files=[_png_file("first.png")],
    )
    claim = analyze.json()["claims"][0]

    await api_client.put(
        "/api/instagram-check/instagram-reupload",
        json={
            "claims": [
                {
                    "id": claim["id"],
                    "edited_text": claim["edited_text"],
                    "category": claim["category"],
                    "return_bucket": claim["return_bucket"],
                    "status": "active",
                    "selected_for_import": True,
                    "follow_up_questions": claim["follow_up_questions"],
                }
            ]
        },
    )
    monkeypatch.setattr(
        "app.instagram_check._evaluate_claim",
        AsyncMock(return_value=_build_green_tip(claim["id"])),
    )
    evaluate = await api_client.post(
        "/api/instagram-check/evaluate",
        json={"session_id": "instagram-reupload", "tax_year": 2025},
    )
    assert evaluate.status_code == 200

    monkeypatch.setattr(
        "app.instagram_check.extract_claim_texts",
        AsyncMock(return_value=["Handwerkerleistung pruefen"]),
    )
    reupload = await api_client.post(
        "/api/instagram-check/analyze",
        data={"session_id": "instagram-reupload", "tax_year": "2025"},
        files=[_png_file("second.png", b"new-image")],
    )
    assert reupload.status_code == 200
    body = reupload.json()
    assert len(body["claims"]) == 1
    assert body["claims"][0]["edited_text"] == "Handwerkerleistung pruefen"

    prep_response = await api_client.get("/api/tax-prep/instagram-reupload")
    prep_items = prep_response.json()
    assert len(prep_items) == 1
    assert prep_items[0]["title"] == "Homeoffice-Pauschale pruefen"


@pytest.mark.asyncio
async def test_non_multimodal_ollama_returns_clear_error(api_client, monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    previous_provider = settings.llm_provider
    previous_model = settings.ollama_model
    settings.llm_provider = "ollama"
    settings.ollama_model = "llama3.1"
    try:
        response = await api_client.post(
            "/api/instagram-check/analyze",
            data={"session_id": "instagram-vision-error", "tax_year": "2025"},
            files=[_png_file("vision.png")],
        )
    finally:
        settings.llm_provider = previous_provider
        settings.ollama_model = previous_model

    assert response.status_code == 422
    assert "multimodal" in response.json()["detail"].lower()
