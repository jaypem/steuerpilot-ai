"""
steuerpilot CLI — Developer / Ingest interface.

Commands:
  steuerpilot ingest       --year 2025 [--laws EStG AO UStG]
  steuerpilot ingest-lstr  --year 2023
  steuerpilot check-sources
  steuerpilot search       QUERY [--year 2025] [--top-k 5]
  steuerpilot eval         [--year 2025]
"""
import asyncio
import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(
    name="steuerpilot",
    help="steuerpilot-ai Developer CLI",
    no_args_is_help=True,
)
console = Console()

# Project root is two levels above this file: backend/ingest/cli.py → backend/
_BACKEND_DIR = Path(__file__).parent.parent
_RAW_DATA_DIR = _BACKEND_DIR.parent / "data" / "raw"


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


# ─── ingest ───────────────────────────────────────────────────────────────────


@app.command()
def ingest(
    year: int = typer.Option(2025, help="Steuerjahr"),
    laws: list[str] = typer.Option(
        ["EStG", "AO", "UStG"], help="Zu ingestende Gesetze"
    ),
    chroma_path: str = typer.Option("chroma_db", help="Pfad zur Chroma-Datenbank"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Wissensbasis für ein Steuerjahr neu aufbauen (Download → Parse → Embed → Store)."""
    _setup_logging(verbose)

    from ingest.downloader import download_law_xml, LAW_URLS
    from ingest.parser import parse_law_xml
    from ingest.store import store_documents

    unsupported = [l for l in laws if l not in LAW_URLS]
    if unsupported:
        console.print(f"[red]Unbekannte Gesetze: {unsupported}[/red]")
        console.print(f"Unterstützt: {list(LAW_URLS.keys())}")
        raise typer.Exit(code=1)

    xml_dir = _RAW_DATA_DIR / str(year)
    total_stored = 0

    for law in laws:
        console.rule(f"[bold]{law} {year}[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            # Download
            t = progress.add_task(f"Herunterladen {law}…")
            xml_path = asyncio.run(download_law_xml(law, xml_dir))
            progress.update(t, completed=True)

            # Parse
            progress.update(t, description=f"Parsen {law}…")
            result = parse_law_xml(xml_path, law, year)
            progress.update(t, completed=True)

        console.print(
            f"  {law}: [green]{len(result.parent_nodes)} Paragrafen[/green] → "
            f"[cyan]{len(result.child_nodes)} Absätze[/cyan] geparst"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Einbetten und speichern {law}…")
            stored = store_documents(result, chroma_path, law, year)

        console.print(f"  {law}: [green]{stored} Nodes[/green] in Chroma gespeichert\n")
        total_stored += stored

    console.print(
        f"\n[bold green]✓ Ingest abgeschlossen:[/bold green] "
        f"{total_stored} Dokumente für {laws} ({year}) in Chroma gespeichert."
    )


# ─── search ───────────────────────────────────────────────────────────────────


@app.command()
def search(
    query: str = typer.Argument(..., help="Suchanfrage"),
    year: int = typer.Option(2025, help="Steuerjahr"),
    top_k: int = typer.Option(5, help="Anzahl Ergebnisse"),
    chroma_path: str = typer.Option("chroma_db", help="Pfad zur Chroma-Datenbank"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Direkte Paragraf-Suche im Vektorspeicher."""
    _setup_logging(verbose)

    # Lazy imports to keep startup fast
    import chromadb
    from ingest.store import COLLECTION_NAME, get_embed_model

    client = chromadb.PersistentClient(path=chroma_path)
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        console.print("[red]Kein Index gefunden. Bitte zuerst 'steuerpilot ingest' ausführen.[/red]")
        raise typer.Exit(code=1)

    count = collection.count()
    if count == 0:
        console.print("[red]Index ist leer. Bitte zuerst 'steuerpilot ingest' ausführen.[/red]")
        raise typer.Exit(code=1)

    embed_model = get_embed_model()
    query_embedding = embed_model.get_query_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"year": {"$eq": year}},
        include=["documents", "metadatas", "distances"],
    )

    table = Table(title=f'Suchergebnisse: "{query}" ({year})', show_lines=True)
    table.add_column("Paragraf", style="cyan", no_wrap=True)
    table.add_column("Gesetz", style="magenta")
    table.add_column("Score", justify="right")
    table.add_column("Text (Auszug)")

    ids = results["ids"][0]
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    for doc, meta, dist in zip(docs, metas, dists):
        score = round(1 - dist, 3)  # cosine distance → similarity
        snippet = (doc or "")[:120].replace("\n", " ") + "…"
        table.add_row(
            meta.get("paragraph", ""),
            meta.get("law", ""),
            str(score),
            snippet,
        )

    console.print(table)


# ─── ingest-lstr ──────────────────────────────────────────────────────────────


@app.command(name="ingest-lstr")
def ingest_lstr(
    year: int = typer.Option(2023, help="LStR-Ausgabejahr (entspricht dem PDF-Jahr)"),
    chroma_path: str = typer.Option("chroma_db", help="Pfad zur Chroma-Datenbank"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """LStR-PDF herunterladen, parsen und in Chroma speichern."""
    _setup_logging(verbose)

    from ingest.scrapers.lstr import download_and_parse_lstr
    from ingest.scrapers.registry import get_source
    from ingest.store import store_documents

    source = get_source("LStR")
    console.rule(f"[bold]LStR {year}[/bold]")
    console.print(f"  URL (verif. {source.verified_year}): {source.url}")

    if year != source.verified_year:
        console.print(
            f"[yellow]⚠ Hinweis: Die URL wurde zuletzt für {source.verified_year} geprüft. "
            f"Prüfe, ob für {year} eine neue Version vorliegt:[/yellow]"
        )
        console.print(f"  {source.update_hint}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        t = progress.add_task("LStR herunterladen und parsen…")
        raw_dir = _RAW_DATA_DIR / str(year)
        result = asyncio.run(download_and_parse_lstr(raw_dir, year))
        progress.update(t, completed=True)

    console.print(f"  LStR: [green]{len(result.parent_nodes)} Abschnitte[/green] geparst")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Einbetten und speichern LStR…")
        stored = store_documents(result, chroma_path, "LStR", year)

    console.print(
        f"\n[bold green]✓ LStR-Ingest abgeschlossen:[/bold green] "
        f"{stored} Dokumente für LStR ({year}) in Chroma gespeichert."
    )


# ─── ingest-bfh ───────────────────────────────────────────────────────────────


@app.command(name="ingest-bfh")
def ingest_bfh(
    year: int = typer.Option(2025, help="Steuerjahr (RAG-Filter)"),
    chroma_path: str = typer.Option("chroma_db", help="Pfad zur Chroma-Datenbank"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """BFH-Urteile herunterladen, parsen und in Chroma speichern.

    Verwendet den kuratierten Katalog in ingest/scrapers/bfh_catalog.py.
    Fehlgeschlagene Downloads werden übersprungen (Warnung im Log).
    """
    _setup_logging(verbose)

    from ingest.scrapers.bfh import download_and_parse_bfh
    from ingest.store import store_documents

    console.rule(f"[bold]BFH-Urteile {year}[/bold]")

    from ingest.scrapers.bfh_catalog import get_active_urteile
    active = get_active_urteile(year)
    bstbl_nein = [u for u in active if not u.bstbl_aufgenommen]
    console.print(
        f"  Katalog: [cyan]{len(active)} aktive Urteile[/cyan] für {year} "
        f"([yellow]{len(bstbl_nein)} noch nicht von Verwaltung übernommen[/yellow])"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        t = progress.add_task("BFH-Urteile herunterladen und parsen…")
        raw_dir = _RAW_DATA_DIR / str(year)
        result = asyncio.run(download_and_parse_bfh(raw_dir, year))
        progress.update(t, completed=True)

    console.print(f"  BFH: [green]{len(result.parent_nodes)} Abschnitte[/green] geparst")

    if not result.parent_nodes:
        console.print("[yellow]⚠ Keine Dokumente extrahiert — Ingest abgebrochen.[/yellow]")
        raise typer.Exit(code=1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Einbetten und speichern BFH-Urteile…")
        stored = store_documents(result, chroma_path, "BFH", year)

    console.print(
        f"\n[bold green]✓ BFH-Ingest abgeschlossen:[/bold green] "
        f"{stored} Dokumente für BFH ({year}) in Chroma gespeichert."
    )


# ─── ingest-bmf ───────────────────────────────────────────────────────────────


@app.command(name="ingest-bmf")
def ingest_bmf(
    year: int = typer.Option(2025, help="Steuerjahr (RAG-Filter)"),
    chroma_path: str = typer.Option("chroma_db", help="Pfad zur Chroma-Datenbank"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """BMF-Schreiben herunterladen, parsen und in Chroma speichern.

    Verwendet den kuratierten Katalog in ingest/scrapers/bmf_catalog.py.
    Fehlgeschlagene Downloads werden übersprungen (Warnung im Log).
    """
    _setup_logging(verbose)

    from ingest.scrapers.bmf import download_and_parse_bmf
    from ingest.store import store_documents

    console.rule(f"[bold]BMF-Schreiben {year}[/bold]")

    from ingest.scrapers.bmf_catalog import get_active_schreiben
    active = get_active_schreiben(year)
    console.print(f"  Katalog: [cyan]{len(active)} aktive Schreiben[/cyan] für {year}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        t = progress.add_task("BMF-Schreiben herunterladen und parsen…")
        raw_dir = _RAW_DATA_DIR / str(year)
        result = asyncio.run(download_and_parse_bmf(raw_dir, year))
        progress.update(t, completed=True)

    console.print(f"  BMF: [green]{len(result.parent_nodes)} Abschnitte[/green] geparst")

    if not result.parent_nodes:
        console.print("[yellow]⚠ Keine Dokumente extrahiert — Ingest abgebrochen.[/yellow]")
        raise typer.Exit(code=1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Einbetten und speichern BMF-Schreiben…")
        stored = store_documents(result, chroma_path, "BMF", year)

    console.print(
        f"\n[bold green]✓ BMF-Ingest abgeschlossen:[/bold green] "
        f"{stored} Dokumente für BMF ({year}) in Chroma gespeichert."
    )


# ─── check-sources ────────────────────────────────────────────────────────────


@app.command(name="check-sources")
def check_sources(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """HTTP-HEAD-Check aller externen Quellen — für CI und jährliche URL-Prüfung.

    Gibt Exit-Code 1 zurück wenn mindestens eine Quelle nicht erreichbar ist.
    Für den GitHub Actions Cron-Job: .github/workflows/check-sources.yml
    """
    _setup_logging(verbose)

    import httpx as _httpx
    from ingest.scrapers.registry import all_sources

    sources = all_sources()
    table = Table(
        title="Externe Quellen — Erreichbarkeitscheck",
        show_lines=True,
    )
    table.add_column("Kürzel", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Verif.-Jahr", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("URL")

    any_failed = False

    for src in sources:
        try:
            resp = _httpx.head(src.url, timeout=15, follow_redirects=True)
            ok = resp.status_code < 400
            status = f"[green]HTTP {resp.status_code}[/green]" if ok else f"[red]HTTP {resp.status_code}[/red]"
            if not ok:
                any_failed = True
        except Exception as exc:
            status = f"[red]FEHLER: {exc}[/red]"
            any_failed = True

        table.add_row(src.key, src.name, str(src.verified_year), status, src.url[:70])

    console.print(table)

    if any_failed:
        console.print(
            "[bold red]✗ Mindestens eine Quelle ist nicht erreichbar.[/bold red]\n"
            "Bitte URL in [cyan]ingest/scrapers/registry.py[/cyan] aktualisieren."
        )
        raise typer.Exit(code=1)
    else:
        console.print("[bold green]✓ Alle Quellen erreichbar.[/bold green]")


# ─── eval ─────────────────────────────────────────────────────────────────────


@app.command()
def eval(
    year: int = typer.Option(2025, help="Steuerjahr für den RAG-Filter"),
    chroma_path: str = typer.Option("chroma_db", help="Pfad zur Chroma-Datenbank"),
    output: str = typer.Option("", help="Optionaler Pfad für JSON-Ausgabe"),
    limit: int = typer.Option(0, help="Nur N Fragen auswerten (0 = alle)"),
    no_automerge: bool = typer.Option(False, "--no-automerge", help="AutoMerge deaktivieren (Ablation)"),
    label: str = typer.Option("", help="Label für den Snapshot (z.B. 'hierarchical')"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """RAGAS-Evaluation über das Goldset (20 Frage-Antwort-Paare) ausführen.

    Benötigt:
      1. Aufgebauten RAG-Index: 'steuerpilot ingest --year <year>'
      2. Eval-Dependencies: 'uv add --group eval ragas langchain-anthropic langchain-huggingface datasets'
      3. ANTHROPIC_API_KEY in .env
    """
    _setup_logging(verbose)

    # Change working directory so relative chroma_path and .env resolve correctly
    import os
    os.chdir(_BACKEND_DIR)

    from evaluation.eval import run_evaluation

    run_evaluation(
        chroma_path=chroma_path,
        tax_year=year,
        output_path=output or None,
        limit=limit or None,
        automerge=not no_automerge,
        label=label,
    )


# ─── eval-compare ──────────────────────────────────────────────────────────────


@app.command(name="eval-compare")
def eval_compare(
    snapshot_a: str = typer.Argument(..., help="Pfad zu Snapshot A (Referenz)"),
    snapshot_b: str = typer.Argument(..., help="Pfad zu Snapshot B (Vergleich)"),
) -> None:
    """Zwei Eval-Snapshots (JSON) nebeneinander vergleichen."""
    import os
    os.chdir(_BACKEND_DIR)

    from evaluation.eval import compare_snapshots
    compare_snapshots(snapshot_a, snapshot_b)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
