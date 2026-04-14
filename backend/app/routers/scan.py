"""
POST /api/scan — Ausgaben-Optimierungs-Scan mit RAG + Claude.

Ablauf:
  1. Retrieval: HybridRetriever holt relevante Gesetzesparagrafen für alle
     eingegebenen Ausgaben (year-gefiltert).
  2. LLM-Aufruf: Claude analysiert jede Position auf steuerliche Absetzbarkeit
     und antwortet im strukturierten JSON-Format.
  3. Parse + Return: ScanResult mit ScannedExpense-Liste, Gesamtersparnis
     und proaktiv vorgeschlagenen fehlenden Positionen.

Fallback: Wenn noch kein RAG-Index vorhanden ist, wird ohne Retrieval-Kontext
gearbeitet (Claude kennt das Steuerrecht aus dem Pretraining).
"""
import json
import logging

from fastapi import APIRouter, HTTPException
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.schema import QueryBundle

from app.config import get_settings
from app.index import get_index, has_indexed_data
from app.llm import get_llm
from app.models.scan import ScanRequest, ScanResult, ScannedExpense, SourceRef

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scan"])


# ─── Prompts ─────────────────────────────────────────────────────────────────

_SYSTEM = (
    "Du bist steuerpilot-ai, ein aggressiver Steueroptimierer im deutschen Steuerrecht. "
    "Dein Ziel: das legale Maximum an Steuerersparnis herausholen. "
    "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt — kein Text davor oder danach, "
    "keine Markdown-Codeblöcke."
)

_USER_TEMPLATE = """\
Steuerjahr: {year}
Nutzer-Kontext: {context}

Zu analysierende Ausgaben:
{expenses_list}

Relevante Gesetzestexte:
{law_context}

Analysiere jede Ausgabe und antworte mit exakt diesem JSON:
{{
  "items": [
    {{
      "description": "<exakter Text der Ausgabe>",
      "amount": <Betrag als Zahl>,
      "deductible": <true oder false>,
      "deductible_amount": <absetzbarer Betrag in Euro, 0.0 wenn nicht absetzbar>,
      "saving_estimate": <geschätzte Steuerersparnis in Euro bei 30% Steuersatz, ganzzahlig>,
      "risk": "<low|medium|high>",
      "explanation": "<ein bis zwei Sätze mit konkretem Paragrafenbezug>",
      "sources": [
        {{"law": "<EStG|AO|UStG>", "paragraph": "<§X>", "section": "<Abs. Y Satz Z>"}}
      ]
    }}
  ],
  "missing_positions": [
    "<Ausgabe oder Position die der Nutzer vermutlich hat, aber nicht angegeben hat>"
  ]
}}

Regeln:
- saving_estimate = deductible_amount * 0.30 (auf ganze Euro gerundet)
- risk low = eindeutige Rechtslage, medium = Grauzone / streitig, high = hohes Prüfungsrisiko
- missing_positions: 2–4 proaktive Vorschläge basierend auf dem Nutzer-Kontext
- Erfinde keine Paragrafen — nutze nur EStG, AO, UStG
"""


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _build_law_context(nodes: list) -> str:
    if not nodes:
        return "(Kein Retrieval-Kontext — Claude antwortet aus Vortraining)"
    parts: list[str] = []
    for n in nodes:
        meta = n.node.metadata
        law = meta.get("law", "")
        para = meta.get("paragraph", "")
        title = meta.get("title", "")
        header = f"[{law} {para} {title}]".strip()
        parts.append(f"{header}\n{n.node.get_content()}")
    return "\n\n".join(parts)


def _retrieve_nodes(chroma_path: str, query: str, year: int) -> list:
    """Run hybrid retrieval; returns [] on any error."""
    try:
        import chromadb
        from ingest.store import COLLECTION_NAME
        from app.retriever import HybridRetriever

        client = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_or_create_collection(COLLECTION_NAME)
        index = get_index(chroma_path)
        retriever = HybridRetriever(index=index, chroma_collection=collection, year=year)
        return retriever.retrieve(QueryBundle(query_str=query))
    except Exception as exc:
        logger.warning("Scan retrieval failed: %s", exc)
        return []


def _strip_markdown_fence(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first line (```json or ```) and last line (```)
        inner = lines[1:] if lines[-1].strip() == "```" else lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        text = "\n".join(inner).strip()
    return text


def _parse_response(raw: str, request: ScanRequest) -> ScanResult:
    """Parse Claude's JSON response into ScanResult."""
    cleaned = _strip_markdown_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Scan JSON parse error: %s\nRaw (first 800): %.800s", exc, raw)
        raise HTTPException(
            status_code=502,
            detail=f"LLM hat kein gültiges JSON zurückgegeben: {exc}",
        )

    items: list[ScannedExpense] = []
    for raw_item in data.get("items", []):
        try:
            sources = [SourceRef(**s) for s in raw_item.get("sources", [])]
            items.append(
                ScannedExpense(
                    description=raw_item["description"],
                    amount=float(raw_item.get("amount", 0)),
                    deductible=bool(raw_item.get("deductible", False)),
                    deductible_amount=float(raw_item.get("deductible_amount", 0)),
                    saving_estimate=int(raw_item.get("saving_estimate", 0)),
                    risk=raw_item.get("risk", "low"),
                    explanation=raw_item.get("explanation", ""),
                    sources=sources,
                )
            )
        except Exception as exc:
            logger.warning("Skipping malformed scan item: %s — %s", raw_item, exc)

    total = sum(i.saving_estimate for i in items)
    missing = [str(m) for m in data.get("missing_positions", [])]

    return ScanResult(items=items, total_saving_estimate=total, missing_positions=missing)


# ─── Endpoint ─────────────────────────────────────────────────────────────────


@router.post("/scan", response_model=ScanResult)
async def scan(request: ScanRequest) -> ScanResult:
    """
    Analyse a list of expenses for tax deductibility using RAG + Claude.

    Returns a structured result with per-item deductibility, estimated savings,
    legal sources, and proactive suggestions for positions the user may have missed.
    """
    settings = get_settings()

    # 1. Build retrieval query from all expense descriptions
    desc_text = " ".join(item.description for item in request.expenses)
    query = f"steuerliche Absetzbarkeit Werbungskosten Betriebsausgaben {desc_text}"

    # 2. Retrieve relevant law paragraphs
    nodes: list = []
    if has_indexed_data(settings.chroma_path):
        nodes = _retrieve_nodes(settings.chroma_path, query, request.tax_year)
    else:
        logger.warning(
            "No RAG index — scan will run without retrieval context. "
            "Run 'uv run steuerpilot ingest --year %d' first.",
            request.tax_year,
        )

    law_context = _build_law_context(nodes)

    # 3. Format the prompt
    expenses_list = "\n".join(
        f"{i + 1}. {item.description}: {item.amount:.2f} €"
        for i, item in enumerate(request.expenses)
    )
    user_message = _USER_TEMPLATE.format(
        year=request.tax_year,
        context=request.context or "Nicht angegeben",
        expenses_list=expenses_list,
        law_context=law_context,
    )

    # 4. Call LLM
    llm = get_llm()
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=_SYSTEM),
        ChatMessage(role=MessageRole.USER, content=user_message),
    ]
    try:
        response = await llm.achat(messages)
        raw = response.message.content or ""
    except Exception as exc:
        logger.exception("LLM call failed during scan")
        raise HTTPException(status_code=502, detail=f"LLM-Fehler: {exc}")

    # 5. Parse and return
    return _parse_response(raw, request)
