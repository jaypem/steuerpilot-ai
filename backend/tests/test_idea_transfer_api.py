import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def api_client(db):
    from app.main import app

    app.state.db = db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


def _own_gmbh_payload(**overrides):
    payload = {
        "case_kind": "own_gmbh_sale",
        "answers": {
            "idea_summary": "Privat entwickelte Methodik zur automatisierten Belegerfassung.",
            "origin_scope": "private",
            "connected_to_job_or_business": "no",
            "is_paid_transfer": "yes",
            "purchase_price_eur": 100000,
            "consideration_type": "cash",
            "buyer_use_plan_available": "yes",
            "buyer_use_description": "Die GmbH will die Methodik in ihr Produkt integrieren.",
            "valuation_mode": "external",
            "documentation_status": "complete",
            "family_value_alignment": "unclear",
            "useful_life_years": 5,
        },
    }
    payload["answers"].update(overrides.pop("answers", {}))
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_get_case_returns_404_when_missing(api_client):
    resp = await api_client.get("/api/idea-transfer/missing-session")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_draft_creates_case_and_session(api_client):
    resp = await api_client.put(
        "/api/idea-transfer/session-draft",
        json=_own_gmbh_payload(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "session-draft"
    assert body["status"] == "draft"
    assert body["result"] is None

    session_resp = await api_client.get("/api/sessions")
    assert session_resp.status_code == 200
    sessions = session_resp.json()
    assert any(session["id"] == "session-draft" for session in sessions)


@pytest.mark.asyncio
async def test_evaluate_own_gmbh_case_persists_summary_message(api_client):
    resp = await api_client.post(
        "/api/idea-transfer/evaluate",
        json={
            "session_id": "session-eval-gmbh",
            "tax_year": 2025,
            **_own_gmbh_payload(),
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["status"] == "completed"
    assert body["result"]["traffic_light"] == "green"
    assert body["result"]["estimated_tax_benefit_min_eur"] == 25000
    assert body["result"]["estimated_tax_benefit_mid_eur"] == 30000
    assert body["result"]["estimated_tax_benefit_max_eur"] == 35000
    assert body["result"]["annual_tax_benefit_mid_eur"] == 6000

    session_detail = await api_client.get("/api/sessions/session-eval-gmbh")
    assert session_detail.status_code == 200
    detail_body = session_detail.json()
    assert detail_body["message_count"] == 1
    assert detail_body["total_saving"] == 30000
    assert len(detail_body["messages"]) == 1
    message = detail_body["messages"][0]
    assert message["role"] == "assistant"
    assert message["saving_amount"] == 30000
    assert message["risk_badge"]["level"] == "low"
    assert "grundsaetzlich pruefbar" in message["content"]


@pytest.mark.asyncio
async def test_evaluate_professional_origin_turns_case_red(api_client):
    payload = _own_gmbh_payload(
        answers={
            "origin_scope": "professional",
            "connected_to_job_or_business": "yes",
            "valuation_mode": "none",
        }
    )
    resp = await api_client.post(
        "/api/idea-transfer/evaluate",
        json={
            "session_id": "session-red",
            "tax_year": 2025,
            **payload,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["traffic_light"] == "red"
    assert any(
        dim["id"] == "private_origin" and dim["traffic_light"] == "red"
        for dim in body["result"]["dimensions"]
    )
    assert any(
        dim["id"] == "employment_proximity" and dim["traffic_light"] == "red"
        for dim in body["result"]["dimensions"]
    )


@pytest.mark.asyncio
async def test_family_transfer_has_no_numeric_savings(api_client):
    payload = _own_gmbh_payload(
        case_kind="family_transfer",
        answers={
            "consideration_type": "asset_transfer",
            "purchase_price_eur": None,
            "family_value_alignment": "yes",
            "useful_life_years": "unclear",
        },
    )
    resp = await api_client.post(
        "/api/idea-transfer/evaluate",
        json={
            "session_id": "session-family",
            "tax_year": 2025,
            **payload,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    result = body["result"]
    assert result["traffic_light"] == "green"
    assert result["estimated_tax_benefit_min_eur"] is None
    assert result["estimated_tax_benefit_mid_eur"] is None
    assert result["estimated_tax_benefit_max_eur"] is None
    assert result["annual_tax_benefit_mid_eur"] is None
    assert any(source["law"] == "ErbStG" for source in result["sources"])


@pytest.mark.asyncio
async def test_deleting_session_cascades_idea_transfer_case(api_client):
    create_resp = await api_client.post(
        "/api/idea-transfer/evaluate",
        json={
            "session_id": "session-delete",
            "tax_year": 2025,
            **_own_gmbh_payload(),
        },
    )
    assert create_resp.status_code == 200

    delete_resp = await api_client.delete("/api/sessions/session-delete")
    assert delete_resp.status_code == 204

    get_case_resp = await api_client.get("/api/idea-transfer/session-delete")
    assert get_case_resp.status_code == 404
