"""
Interview engine for Phase 22 — proactive tax interview check.

Public API:
  get_next_question(answers)         — next unanswered applicable question (pure, sync)
  ensure_interview_session(db, ...)  — create/reset session and tax_interviews row
  get_interview(db, session_id)      — load TaxInterview from DB
  save_answer(db, session_id, ...)   — upsert answer and return updated TaxInterview
  evaluate_interview(db, ...)        — run RAG+LLM per category, persist findings
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from typing import Any, cast

import aiosqlite

from app.config import get_settings
from app.interview_catalog import CATEGORY_LABELS, QUESTIONS, Question, get_by_category
from app.models.tax_interview import (
    AnswerPayload,
    InterviewQuestion,
    TaxInterview,
    TaxInterviewFinding,
)
from app.models.idea_transfer import IdeaTransferSource
from app.timestamps import parse_timestamp, utc_now

logger = logging.getLogger(__name__)

_INTERVIEW_TITLE = "steuer-interview"
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)

# ─── Conditional logic ────────────────────────────────────────────────────────


def _condition_met(question: Question, answers: dict[str, Any]) -> bool:
    """Return True if the question's condition is satisfied (or has no condition)."""
    if question.condition is None:
        return True
    ref_id, expected = question.condition
    if ref_id not in answers:
        return False  # gating question not yet answered
    actual = answers[ref_id]
    if isinstance(expected, list):
        return actual in expected
    # Special: condition=(ref_id, True) on a number question means "any truthy value"
    if expected is True and not isinstance(actual, bool):
        return bool(actual)
    return actual == expected


def get_next_question(answers: dict[str, Any]) -> InterviewQuestion | None:
    """
    Iterate catalog in order; return the first question that:
      - has not yet been answered, AND
      - whose condition (if any) is satisfied by the current answers.

    Returns None when all applicable questions have been answered.
    """
    for q in QUESTIONS:
        if q.id in answers:
            continue
        if _condition_met(q, answers):
            return InterviewQuestion(
                id=q.id,
                category=q.category,
                text=q.text,
                answer_type=q.answer_type,
                options=list(q.options) if q.options else None,
            )
    return None


# ─── DB helpers ───────────────────────────────────────────────────────────────


async def ensure_interview_session(
    db: aiosqlite.Connection,
    session_id: str,
    tax_year: int,
) -> None:
    """Upsert sessions row + tax_interviews row, delete any old answers/findings."""
    now = utc_now()
    await db.execute(
        """
        INSERT INTO sessions (id, title, created_at, updated_at, message_count, total_saving)
        VALUES (?, ?, ?, ?, 0, 0)
        ON CONFLICT(id) DO NOTHING
        """,
        (session_id, _INTERVIEW_TITLE, now, now),
    )
    # Reset: delete old answers + findings so the interview starts fresh
    await db.execute(
        "DELETE FROM tax_interview_answers WHERE session_id = ?", (session_id,)
    )
    await db.execute(
        "DELETE FROM tax_interview_findings WHERE session_id = ?", (session_id,)
    )
    await db.execute(
        """
        INSERT INTO tax_interviews (session_id, status, tax_year, created_at, updated_at)
        VALUES (?, 'in_progress', ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
          status = 'in_progress',
          tax_year = excluded.tax_year,
          updated_at = excluded.updated_at
        """,
        (session_id, tax_year, now, now),
    )
    await db.commit()


async def _load_answers(
    db: aiosqlite.Connection, session_id: str
) -> dict[str, bool | int | str]:
    async with db.execute(
        "SELECT question_id, answer FROM tax_interview_answers WHERE session_id = ?",
        (session_id,),
    ) as cur:
        rows = await cur.fetchall()
    result: dict[str, bool | int | str] = {}
    for row in rows:
        result[row["question_id"]] = json.loads(row["answer"])
    return result


async def _load_findings(
    db: aiosqlite.Connection, session_id: str
) -> list[TaxInterviewFinding]:
    async with db.execute(
        "SELECT * FROM tax_interview_findings WHERE session_id = ? ORDER BY created_at",
        (session_id,),
    ) as cur:
        rows = await cur.fetchall()
    findings: list[TaxInterviewFinding] = []
    for row in rows:
        findings.append(
            TaxInterviewFinding(
                category=row["category"],
                title=row["title"],
                traffic_light=row["traffic_light"],
                explanation=row["explanation"],
                estimated_saving_eur=row["estimated_saving_eur"],
                required_evidence=json.loads(row["required_evidence"]),
                sources=[
                    IdeaTransferSource.model_validate(s)
                    for s in json.loads(row["sources"])
                ],
            )
        )
    return findings


async def get_interview(
    db: aiosqlite.Connection, session_id: str
) -> TaxInterview | None:
    async with db.execute(
        "SELECT * FROM tax_interviews WHERE session_id = ?", (session_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None

    answers = await _load_answers(db, session_id)
    status = row["status"]
    findings = await _load_findings(db, session_id) if status == "evaluated" else None

    return TaxInterview(
        session_id=session_id,
        status=status,
        tax_year=row["tax_year"],
        answers=answers,
        next_question=get_next_question(answers) if status == "in_progress" else None,
        findings=findings,
        updated_at=parse_timestamp(row["updated_at"]),
    )


async def save_answer(
    db: aiosqlite.Connection,
    session_id: str,
    payload: AnswerPayload,
) -> TaxInterview:
    now = utc_now()
    answer_json = json.dumps(payload.answer)
    await db.execute(
        """
        INSERT INTO tax_interview_answers (id, session_id, question_id, answer, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_id, question_id) DO UPDATE SET
          answer = excluded.answer
        """,
        (str(uuid.uuid4()), session_id, payload.question_id, answer_json, now),
    )
    answers = await _load_answers(db, session_id)
    next_q = get_next_question(answers)
    new_status = "in_progress" if next_q is not None else "completed"
    await db.execute(
        "UPDATE tax_interviews SET status = ?, updated_at = ? WHERE session_id = ?",
        (new_status, now, session_id),
    )
    await db.execute(
        "UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id)
    )
    await db.commit()

    interview = await get_interview(db, session_id)
    if interview is None:
        raise RuntimeError("Interview not found after save_answer.")
    return interview


# ─── Evaluation ───────────────────────────────────────────────────────────────


def _retrieve_nodes(query: str, year: int) -> list[Any]:
    settings = get_settings()
    try:
        import chromadb
        from llama_index.core.schema import QueryBundle
        from app.index import get_index, has_indexed_data
        from app.retriever import HybridRetriever
        from ingest.store import COLLECTION_NAME

        if not has_indexed_data(settings.chroma_path):
            return []
        client = chromadb.PersistentClient(path=settings.chroma_path)
        collection = client.get_or_create_collection(COLLECTION_NAME)
        index = get_index(settings.chroma_path)
        retriever = HybridRetriever(index=index, chroma_collection=collection, year=year)
        return retriever.retrieve(QueryBundle(query_str=query))
    except Exception as exc:
        logger.warning("Interview retrieval failed for query %r: %s", query[:60], exc)
        return []


def _build_law_context(nodes: list[Any]) -> str:
    if not nodes:
        return "(Kein Retrieval-Kontext verfuegbar)"
    parts: list[str] = []
    for node in nodes[:4]:
        meta = node.node.metadata
        law = str(meta.get("law", ""))
        paragraph = str(meta.get("paragraph", ""))
        section = str(meta.get("section", ""))
        title = " ".join(p for p in (law, paragraph, section) if p).strip()
        header = f"[{title}]" if title else "[Rechtsquelle]"
        parts.append(f"{header}\n{node.node.get_content()}")
    return "\n\n".join(parts)


def _nodes_to_sources(nodes: list[Any]) -> list[IdeaTransferSource]:
    sources: list[IdeaTransferSource] = []
    seen: set[tuple[str, str, str]] = set()
    for node in nodes[:4]:
        meta = node.node.metadata
        law = str(meta.get("law", ""))
        paragraph = str(meta.get("paragraph", ""))
        section = str(meta.get("section", ""))
        if not law or not paragraph:
            continue
        key = (law, paragraph, section)
        if key in seen:
            continue
        seen.add(key)
        url = meta.get("url")
        sources.append(
            IdeaTransferSource(
                law=law,
                paragraph=paragraph,
                section=section,
                text=node.node.get_content(),
                url=str(url) if isinstance(url, str) else None,
            )
        )
    return sources


def _strip_json_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text.strip()).strip()


def _answers_context(
    category: str, answers: dict[str, Any]
) -> str:
    """Format answered questions for a given category as readable context."""
    qs = get_by_category(category)
    lines: list[str] = []
    for q in qs:
        if q.id in answers:
            lines.append(f"- {q.text}\n  Antwort: {answers[q.id]}")
    return "\n".join(lines) if lines else "- Keine Antworten fuer diese Kategorie."


_EVALUATION_PROMPT = """\
Du bewertest eine Steuerkategorie im Rahmen eines proaktiven Steuer-Interview-Checks fuer eine konkrete Person in Deutschland.

Steuerjahr: {tax_year}
Kategorie: {category_label}

Antworten des Nutzers:
{answers_context}

Relevanter Gesetzeskontext:
{law_context}

Antworte NUR mit JSON:
{{
  "title": "<kurzer aussagekraeftiger Titel fuer diese Kategorie>",
  "traffic_light": "<green|yellow|red>",
  "explanation": "<klare fachliche Einordnung: welche Steuerchancen ergeben sich, was fehlt noch oder was passt nicht>",
  "estimated_saving_eur": <ganze Zahl oder null>,
  "required_evidence": ["<Nachweis 1>", "<Nachweis 2>"]
}}

Regeln:
- green: Konkrete Steuerchancen sind erkennbar und koennen direkt geltend gemacht werden.
- yellow: Potenzial vorhanden, aber Belege fehlen oder weitere Angaben sind noetig.
- red: Keine relevante Steuerchance in dieser Kategorie (Antworten zeigen kein Einsparpotenzial).
- estimated_saving_eur nur setzen, wenn eine belastbare Grobschaetzung moeglich ist (Steuersatz ~30 %); sonst null.
- required_evidence leer lassen, wenn keine besonderen Nachweise auffallen.
- Antworte auf Deutsch.
"""


async def _evaluate_category(
    category: str,
    tax_year: int,
    answers: dict[str, Any],
) -> TaxInterviewFinding | None:
    """RAG + LLM for one category. Returns None if no answers exist for the category."""
    # Only evaluate categories that have at least one answered question
    cat_questions = get_by_category(category)
    answered_ids = {q.id for q in cat_questions if q.id in answers}
    if not answered_ids:
        return None

    settings = get_settings()
    category_label = CATEGORY_LABELS[category]
    answers_ctx = _answers_context(category, answers)

    # Build RAG query from answered question texts + rag_hints
    rag_terms: list[str] = []
    for q in cat_questions:
        if q.id in answers:
            rag_terms.extend(q.rag_hint)
    rag_query = f"{category_label} {' '.join(dict.fromkeys(rag_terms))}"
    nodes = _retrieve_nodes(rag_query, tax_year)
    law_context = _build_law_context(nodes)
    sources = _nodes_to_sources(nodes)

    prompt = _EVALUATION_PROMPT.format(
        tax_year=tax_year,
        category_label=category_label,
        answers_context=answers_ctx,
        law_context=law_context,
    )

    raw_json: str = ""
    try:
        if settings.llm_provider == "anthropic":
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=800,
                messages=cast(Any, [{"role": "user", "content": prompt}]),
            )
            raw_json = "".join(
                getattr(block, "text", "") for block in response.content
            )
        else:
            from ollama import AsyncClient as OllamaAsyncClient

            client = OllamaAsyncClient(host=settings.ollama_base_url)
            response = await client.chat(
                model=settings.ollama_model,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_json = response.message.content or ""

        data = json.loads(_strip_json_fence(raw_json))
        return TaxInterviewFinding(
            category=category,
            title=str(data.get("title", category_label)),
            traffic_light=data.get("traffic_light", "yellow"),
            explanation=str(data.get("explanation", "")),
            estimated_saving_eur=data.get("estimated_saving_eur"),
            required_evidence=list(data.get("required_evidence", [])),
            sources=sources,
        )
    except Exception as exc:
        logger.warning(
            "Interview evaluation failed for category %r: %s", category, exc
        )
        return TaxInterviewFinding(
            category=category,
            title=category_label,
            traffic_light="yellow",
            explanation=f"Auswertung konnte nicht abgeschlossen werden ({exc}).",
            required_evidence=[],
            sources=sources,
        )


async def evaluate_interview(
    db: aiosqlite.Connection,
    session_id: str,
    tax_year: int,
    answers: dict[str, Any],
) -> list[TaxInterviewFinding]:
    """
    Evaluate all 8 categories in parallel (asyncio.gather).
    Persist findings to DB and mark interview as 'evaluated'.
    Returns the list of findings (categories with no answers are skipped).
    """
    tasks = [
        _evaluate_category(category, tax_year, answers)
        for category in CATEGORY_LABELS
    ]
    results = await asyncio.gather(*tasks)
    findings = [f for f in results if f is not None]

    now = utc_now()
    # Delete any previous findings first
    await db.execute(
        "DELETE FROM tax_interview_findings WHERE session_id = ?", (session_id,)
    )
    for finding in findings:
        await db.execute(
            """
            INSERT INTO tax_interview_findings
              (id, session_id, category, title, traffic_light, explanation,
               estimated_saving_eur, required_evidence, sources, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                session_id,
                finding.category,
                finding.title,
                finding.traffic_light,
                finding.explanation,
                finding.estimated_saving_eur,
                json.dumps(finding.required_evidence),
                json.dumps([s.model_dump() for s in finding.sources]),
                now,
            ),
        )
    await db.execute(
        "UPDATE tax_interviews SET status = 'evaluated', updated_at = ? WHERE session_id = ?",
        (now, session_id),
    )
    await db.execute(
        "UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id)
    )
    await db.commit()
    return findings
