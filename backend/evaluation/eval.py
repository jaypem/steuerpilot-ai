"""
RAGAS-Evaluation für steuerpilot-ai.

Ablauf:
  1. Goldset aus evaluation/goldset.json laden
  2. Jede Frage durch die RAG-Pipeline schicken (Retrieval + LLM)
  3. RAGAS-Dataset aufbauen
  4. Metriken berechnen: faithfulness, answer_relevancy,
     context_precision, context_recall
  5. Ergebnisse in Rich-Tabelle ausgeben und optional als JSON speichern

Voraussetzungen:
  - `uv run steuerpilot ingest --year <year>` muss vorher ausgeführt worden sein
  - Eval-Dependencies: `uv run --group eval steuerpilot eval`
    (ragas, langchain-anthropic, datasets)
  - ANTHROPIC_API_KEY in .env gesetzt
"""
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_GOLDSET_PATH = Path(__file__).parent / "goldset.json"
_EVAL_DIR = Path(__file__).parent


# ─── RAG pipeline helpers ─────────────────────────────────────────────────────


async def _run_question(
    question: str,
    chroma_path: str,
    tax_year: int,
) -> dict[str, Any]:
    """
    Run a single question through the retrieval pipeline.
    Returns {"answer": str, "contexts": list[str]}.
    """
    import aiosqlite
    from app.database import DB_PATH, init_db
    from app.engine import stream_chat_response

    # Use a temporary in-memory DB for evaluation (no side effects)
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await init_db(db)

    answer_parts: list[str] = []
    try:
        async for raw in stream_chat_response(
            message=question,
            session_id="eval-session",
            db=db,
            tax_year=tax_year,
        ):
            if not raw.startswith("data: "):
                continue
            try:
                payload = json.loads(raw[6:])
            except Exception:
                continue
            if payload.get("type") == "text":
                answer_parts.append(payload.get("content", ""))
    finally:
        await db.close()

    answer = "".join(answer_parts)

    # Also retrieve contexts directly (for RAGAS context metrics)
    contexts = await _get_contexts(question, chroma_path, tax_year)

    return {"answer": answer, "contexts": contexts}


async def _get_contexts(query: str, chroma_path: str, year: int) -> list[str]:
    """Run the hybrid retriever and return text of top-N nodes."""
    from app.config import get_settings
    from app.index import get_index, has_indexed_data

    if not has_indexed_data(chroma_path):
        return []

    try:
        import chromadb
        from ingest.store import COLLECTION_NAME
        from app.retriever import HybridRetriever
        from llama_index.core.schema import QueryBundle

        client = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_or_create_collection(COLLECTION_NAME)
        index = get_index(chroma_path)
        retriever = HybridRetriever(index=index, chroma_collection=collection, year=year)
        nodes = retriever.retrieve(QueryBundle(query_str=query))
        return [n.node.get_content() for n in nodes]
    except Exception as exc:
        logger.warning("Context retrieval failed for eval: %s", exc)
        return []


# ─── RAGAS setup ──────────────────────────────────────────────────────────────


def _build_ragas_evaluator(api_key: str):
    """Build RAGAS LLM and embeddings wrappers using Anthropic + HuggingFace."""
    try:
        from langchain_anthropic import ChatAnthropic
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError as e:
        raise SystemExit(
            f"\n[eval] Missing eval dependencies: {e}\n"
            "Install them with:\n"
            "  uv add --group eval ragas langchain-anthropic langchain-huggingface datasets\n"
        )

    llm = LangchainLLMWrapper(
        ChatAnthropic(model="claude-haiku-4-5-20251001", api_key=api_key, max_tokens=2048)
    )
    embeddings = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")
    )
    return llm, embeddings


def _ragas_evaluate(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
    api_key: str,
) -> dict[str, float]:
    """Run RAGAS evaluation and return metric scores."""
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            LLMContextRecall,
            Faithfulness,
            FactualCorrectness,
            ResponseRelevancy,
        )
    except ImportError as e:
        raise SystemExit(
            f"\n[eval] Missing eval dependencies: {e}\n"
            "Install them with:\n"
            "  uv add --group eval ragas langchain-anthropic langchain-huggingface datasets\n"
        )

    llm, embeddings = _build_ragas_evaluator(api_key)

    metrics = [
        LLMContextRecall(llm=llm),
        Faithfulness(llm=llm),
        ResponseRelevancy(llm=llm, embeddings=embeddings),
        FactualCorrectness(llm=llm),
    ]

    dataset = Dataset.from_dict({
        "user_input": questions,
        "response": answers,
        "retrieved_contexts": contexts,
        "reference": ground_truths,
    })

    result = evaluate(dataset=dataset, metrics=metrics)
    return dict(result)


# ─── Public entry point ───────────────────────────────────────────────────────


def run_evaluation(
    chroma_path: str = "chroma_db",
    tax_year: int = 2025,
    output_path: str | None = None,
    limit: int | None = None,
    api_key: str = "",
) -> None:
    """
    Full evaluation run: goldset → RAG pipeline → RAGAS metrics → Rich table.

    Args:
        chroma_path:  Path to the Chroma vector store (must be built with 'ingest').
        tax_year:     Tax year filter used during retrieval.
        output_path:  If set, save the full results dict as JSON to this path.
        limit:        Evaluate only the first N questions (useful for quick checks).
        api_key:      Anthropic API key (falls back to ANTHROPIC_API_KEY env var).
    """
    import os
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn

    console = Console()
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key:
        console.print("[red]ANTHROPIC_API_KEY nicht gesetzt — Eval abgebrochen.[/red]")
        raise SystemExit(1)

    # ── Load goldset ──────────────────────────────────────────────────────────
    goldset = json.loads(_GOLDSET_PATH.read_text(encoding="utf-8"))
    questions_data = goldset["questions"]
    if limit:
        questions_data = questions_data[:limit]

    console.rule(f"[bold]steuerpilot-ai RAGAS-Eval — {len(questions_data)} Fragen[/bold]")

    # ── Run pipeline for each question ────────────────────────────────────────
    questions: list[str] = []
    answers: list[str] = []
    contexts: list[list[str]] = []
    ground_truths: list[str] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for item in questions_data:
            task = progress.add_task(f"Frage {item['id']}: {item['question'][:50]}…")
            result = asyncio.run(_run_question(item["question"], chroma_path, tax_year))
            progress.update(task, completed=True)

            questions.append(item["question"])
            answers.append(result["answer"])
            contexts.append(result["contexts"])
            ground_truths.append(item["ground_truth"])

    # ── RAGAS evaluation ──────────────────────────────────────────────────────
    console.print("\n[bold]RAGAS-Metriken werden berechnet …[/bold]")
    t0 = time.monotonic()
    try:
        scores = _ragas_evaluate(questions, answers, contexts, ground_truths, api_key)
    except SystemExit:
        raise
    except Exception as exc:
        console.print(f"[red]RAGAS-Evaluation fehlgeschlagen: {exc}[/red]")
        raise
    elapsed = time.monotonic() - t0

    # ── Display results ───────────────────────────────────────────────────────
    table = Table(
        title="RAGAS-Ergebnis",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Metrik", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Bewertung")

    def _grade(v: float) -> str:
        if v >= 0.8:
            return "[green]Gut[/green]"
        if v >= 0.6:
            return "[yellow]Mittel[/yellow]"
        return "[red]Schwach[/red]"

    metric_labels = {
        "context_recall": "Context Recall",
        "faithfulness": "Faithfulness",
        "answer_relevancy": "Answer Relevancy",
        "factual_correctness": "Factual Correctness",
        "llm_context_recall": "LLM Context Recall",
        "response_relevancy": "Response Relevancy",
    }
    for key, value in scores.items():
        if isinstance(value, float):
            label = metric_labels.get(key, key)
            table.add_row(label, f"{value:.3f}", _grade(value))

    console.print(table)
    console.print(f"\n[dim]Laufzeit: {elapsed:.1f}s für {len(questions)} Fragen[/dim]")

    # ── Optional JSON output ──────────────────────────────────────────────────
    if output_path:
        full_result = {
            "tax_year": tax_year,
            "n_questions": len(questions),
            "elapsed_seconds": round(elapsed, 1),
            "scores": {k: v for k, v in scores.items() if isinstance(v, float)},
            "details": [
                {
                    "id": item["id"],
                    "question": q,
                    "answer": a,
                    "ground_truth": gt,
                    "n_contexts": len(ctx),
                }
                for item, q, a, gt, ctx in zip(
                    questions_data, questions, answers, ground_truths, contexts
                )
            ],
        }
        Path(output_path).write_text(
            json.dumps(full_result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        console.print(f"[green]Ergebnisse gespeichert:[/green] {output_path}")
