"""
Tests for the tax interview engine (22.8).

Unit tests: get_next_question conditional routing — offline, no DB.
API integration tests: all four endpoints via ASGI test client.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from app.tax_interview import get_next_question
from app.models.tax_interview import TaxInterviewFinding


# ─── Shared fixture ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def api_client(db):
    from app.main import app

    app.state.db = db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


# ─── Engine unit tests (pure, no DB) ─────────────────────────────────────────


class TestGetNextQuestion:
    def test_empty_answers_returns_first_question(self):
        q = get_next_question({})
        assert q is not None
        assert q.id == "base.employment"

    def test_skips_answered_question(self):
        q = get_next_question({"base.employment": "Angestellt"})
        assert q is not None
        assert q.id == "base.marital_status"

    def test_single_value_condition_not_met_skips_question(self):
        # homeoffice_days requires homeoffice=True; False means skip it
        answers = {
            "base.employment": "Angestellt",
            "base.marital_status": "Ledig",
            "base.has_children": False,
            "base.church_tax": False,
            "base.donations": False,
            "base.alimony": False,
            "work.homeoffice": False,
        }
        q = get_next_question(answers)
        assert q is not None
        assert q.id not in ("work.homeoffice_days", "work.homeoffice_room")

    def test_single_value_condition_met_unlocks_question(self):
        # homeoffice=True → next is homeoffice_days
        answers = {"work.homeoffice": True}
        # Fill base questions first so we reach the work block
        base = {
            "base.employment": "Angestellt",
            "base.marital_status": "Ledig",
            "base.has_children": False,
            "base.church_tax": False,
            "base.donations": False,
            "base.alimony": False,
        }
        q = get_next_question({**base, **answers})
        assert q is not None
        assert q.id == "work.homeoffice_days"

    def test_list_condition_met_when_answer_in_list(self):
        # commute_km requires employment in ["Angestellt", "Beamter", "Beides"]
        answers = {
            "base.employment": "Angestellt",
            "base.marital_status": "Ledig",
            "base.has_children": False,
            "base.church_tax": False,
            "base.donations": False,
            "base.alimony": False,
            "work.homeoffice": False,
            "work.equipment": False,
            "work.training": False,
            "work.clothing": False,
            "work.double_household": False,
        }
        q = get_next_question(answers)
        assert q is not None
        assert q.id == "work.commute_km"

    def test_list_condition_not_met_skips_question(self):
        # Rentner → no commute_km, no vehicle_business, no company_pension
        answers = {
            "base.employment": "Rentner",
            "base.marital_status": "Ledig",
            "base.has_children": False,
            "base.church_tax": False,
            "base.donations": False,
            "base.alimony": False,
            "work.homeoffice": False,
            "work.equipment": False,
            "work.training": False,
            "work.clothing": False,
            "work.double_household": False,
        }
        q = get_next_question(answers)
        # First question in "wohnen" block
        assert q is not None
        assert q.category == "wohnen"

    def test_truthy_number_condition_met(self):
        # commute_days requires commute_km to be truthy (any non-zero number)
        base = {
            "base.employment": "Angestellt",
            "base.marital_status": "Ledig",
            "base.has_children": False,
            "base.church_tax": False,
            "base.donations": False,
            "base.alimony": False,
            "work.homeoffice": False,
            "work.equipment": False,
            "work.training": False,
            "work.clothing": False,
            "work.double_household": False,
            "work.commute_km": 25,
        }
        q = get_next_question(base)
        assert q is not None
        assert q.id == "work.commute_days"

    def test_truthy_number_zero_does_not_unlock(self):
        base = {
            "base.employment": "Angestellt",
            "base.marital_status": "Ledig",
            "base.has_children": False,
            "base.church_tax": False,
            "base.donations": False,
            "base.alimony": False,
            "work.homeoffice": False,
            "work.equipment": False,
            "work.training": False,
            "work.clothing": False,
            "work.double_household": False,
            "work.commute_km": 0,
        }
        q = get_next_question(base)
        assert q is not None
        assert q.id != "work.commute_days"

    def test_chained_condition_unlocked_step_by_step(self):
        # children=True → children_count → children_under_14 → childcare_costs
        answers = {
            "base.employment": "Angestellt",
            "base.marital_status": "Ledig",
            "base.has_children": True,
            "base.children_count": 2,
            "base.children_under_14": True,
        }
        q = get_next_question(answers)
        assert q is not None
        assert q.id == "base.childcare_costs"

    def test_returns_none_when_all_answered(self):
        from app.interview_catalog import QUESTIONS

        # Answer all questions with minimal values that don't unlock sub-questions
        # Use "Rentner" for employment to avoid employed/self-employed branches
        all_ids = {q.id for q in QUESTIONS}
        # Build minimal answers: answer every question with a falsy/neutral value
        answers: dict = {}
        for q in QUESTIONS:
            if q.answer_type == "bool":
                answers[q.id] = False
            elif q.answer_type == "choice":
                answers[q.id] = q.options[0] if q.options else ""
            elif q.answer_type == "number":
                answers[q.id] = 0
            else:
                answers[q.id] = ""
        result = get_next_question(answers)
        assert result is None

    def test_gating_question_not_yet_answered_skips_dependent(self):
        # If the gating question has no answer yet, dependent question is skipped
        q = get_next_question({"base.has_children": True})
        # base.employment is not yet answered, but base.has_children=True would unlock
        # children_count. However base.employment comes first in catalog order.
        assert q is not None
        assert q.id == "base.employment"


# ─── API integration tests ────────────────────────────────────────────────────


class TestTaxInterviewAPI:
    @pytest.mark.asyncio
    async def test_get_returns_404_when_missing(self, api_client):
        resp = await api_client.get("/api/tax-interview/missing-session")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_start_creates_interview_and_returns_first_question(self, api_client):
        resp = await api_client.post(
            "/api/tax-interview/sess-start/start",
            json={"tax_year": 2025},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "sess-start"
        assert body["status"] == "in_progress"
        assert body["tax_year"] == 2025
        assert body["answers"] == {}
        assert body["next_question"] is not None
        assert body["next_question"]["id"] == "base.employment"

    @pytest.mark.asyncio
    async def test_start_resets_existing_interview(self, api_client):
        # First start with tax_year=2024
        await api_client.post(
            "/api/tax-interview/sess-reset/start",
            json={"tax_year": 2024},
        )
        # Answer one question
        await api_client.put(
            "/api/tax-interview/sess-reset/answer",
            json={"question_id": "base.employment", "answer": "Angestellt"},
        )
        # Reset with new tax_year
        resp = await api_client.post(
            "/api/tax-interview/sess-reset/start",
            json={"tax_year": 2025},
        )
        body = resp.json()
        assert body["tax_year"] == 2025
        assert body["answers"] == {}
        assert body["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_answer_saves_and_returns_next_question(self, api_client):
        await api_client.post(
            "/api/tax-interview/sess-answer/start",
            json={"tax_year": 2025},
        )
        resp = await api_client.put(
            "/api/tax-interview/sess-answer/answer",
            json={"question_id": "base.employment", "answer": "Angestellt"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["answers"]["base.employment"] == "Angestellt"
        assert body["next_question"]["id"] == "base.marital_status"
        assert body["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_answer_returns_404_when_interview_missing(self, api_client):
        resp = await api_client.put(
            "/api/tax-interview/no-such-session/answer",
            json={"question_id": "base.employment", "answer": "Angestellt"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_interview_completes_after_all_questions(self, api_client):
        from app.interview_catalog import QUESTIONS

        sid = "sess-complete"
        await api_client.post(
            f"/api/tax-interview/{sid}/start",
            json={"tax_year": 2025},
        )
        # Drive the interview to completion by answering each next_question
        # with a minimal value that doesn't unlock extra branches
        _SAFE_EMPLOYMENT = "Rentner"
        for _ in range(200):  # safety limit; catalog has 59 questions max
            state_resp = await api_client.get(f"/api/tax-interview/{sid}")
            state = state_resp.json()
            nq = state.get("next_question")
            if nq is None:
                break
            qid = nq["id"]
            answer_type = nq["answer_type"]
            if answer_type == "bool":
                answer: bool | int | str = False
            elif answer_type == "choice":
                # Pick Rentner for employment to avoid extra branches
                if qid == "base.employment":
                    answer = _SAFE_EMPLOYMENT
                else:
                    answer = nq["options"][0]
            elif answer_type == "number":
                answer = 0
            else:
                answer = ""
            await api_client.put(
                f"/api/tax-interview/{sid}/answer",
                json={"question_id": qid, "answer": answer},
            )

        final = await api_client.get(f"/api/tax-interview/{sid}")
        body = final.json()
        assert body["status"] == "completed"
        assert body["next_question"] is None

    @pytest.mark.asyncio
    async def test_evaluate_returns_422_when_still_in_progress(self, api_client):
        await api_client.post(
            "/api/tax-interview/sess-eval-guard/start",
            json={"tax_year": 2025},
        )
        resp = await api_client.post("/api/tax-interview/sess-eval-guard/evaluate")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_evaluate_returns_404_when_missing(self, api_client):
        resp = await api_client.post("/api/tax-interview/no-such/evaluate")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_evaluate_persists_findings(self, api_client):
        """Evaluate with mocked _evaluate_category to avoid real LLM calls."""
        sid = "sess-eval"
        await api_client.post(
            f"/api/tax-interview/{sid}/start",
            json={"tax_year": 2025},
        )
        await api_client.put(
            f"/api/tax-interview/{sid}/answer",
            json={"question_id": "base.employment", "answer": "Rentner"},
        )
        # Drive to "completed" quickly by answering all remaining with falsy values
        for _ in range(200):
            state = (await api_client.get(f"/api/tax-interview/{sid}")).json()
            nq = state.get("next_question")
            if nq is None:
                break
            at = nq["answer_type"]
            answer: bool | int | str = (
                False
                if at == "bool"
                else (
                    nq["options"][0] if at == "choice" else 0 if at == "number" else ""
                )
            )
            await api_client.put(
                f"/api/tax-interview/{sid}/answer",
                json={"question_id": nq["id"], "answer": answer},
            )

        mock_finding = TaxInterviewFinding(
            category="basis",
            title="Test-Finding",
            traffic_light="green",
            explanation="Test explanation",
            estimated_saving_eur=500,
            required_evidence=["Nachweis A"],
            sources=[],
        )

        with patch(
            "app.tax_interview._evaluate_category",
            new=AsyncMock(return_value=mock_finding),
        ):
            resp = await api_client.post(f"/api/tax-interview/{sid}/evaluate")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "evaluated"
        assert body["findings"] is not None
        assert len(body["findings"]) == 8  # one per category (all mocked)
        assert body["findings"][0]["title"] == "Test-Finding"
        assert body["findings"][0]["traffic_light"] == "green"

    @pytest.mark.asyncio
    async def test_delete_session_cascades_interview(self, api_client):
        sid = "sess-cascade"
        await api_client.post(
            f"/api/tax-interview/{sid}/start",
            json={"tax_year": 2025},
        )
        assert (await api_client.get(f"/api/tax-interview/{sid}")).status_code == 200

        delete_resp = await api_client.delete(f"/api/sessions/{sid}")
        assert delete_resp.status_code == 204

        assert (await api_client.get(f"/api/tax-interview/{sid}")).status_code == 404
