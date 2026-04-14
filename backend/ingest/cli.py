"""
steuerpilot CLI — Developer / Ingest interface.

Commands:
  steuerpilot ingest  --year 2025 [--laws EStG AO UStG]
  steuerpilot search  QUERY [--year 2025] [--top-k 5]
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
            documents = parse_law_xml(xml_path, law, year)
            progress.update(t, completed=True)

        console.print(f"  {law}: [green]{len(documents)} Paragraphen[/green] geparst")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Einbetten und speichern {law}…")
            stored = store_documents(documents, chroma_path, law, year)

        console.print(f"  {law}: [green]{stored} Dokumente[/green] gespeichert\n")
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


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
