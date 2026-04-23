# steuerpilot-ai

RAG-basierter Steueroptimierungs-Assistent für das deutsche Steuerrecht. Beantwortet Steuerfragen mit direktem Bezug auf EStG, AO, UStG, BFH-Urteile, BMF-Schreiben und LStR — inklusive Quellenangaben, Risikoeinschätzung und Sparpotenzial-Schätzung.

## Projektstruktur

```text
steuerpilot-ai/
├── frontend/        # Next.js 16 (App Router, Tailwind CSS v4, React 19)
├── backend/         # FastAPI + LlamaIndex + Chroma (uv)
│   ├── app/         # API, RAG-Engine, Retriever, Prompts
│   └── ingest/      # CLI zum Scrapen und Indexieren der Rechtsquellen
├── data/            # Heruntergeladene Rohdokumente (gitignored)
├── PRD.md           # Product Requirements Document
└── BACKLOG.md       # Geplante Features und bekannte Issues
```

## Architektur

Die UI ist ein Next.js-Frontend mit Chat-Ansicht unter `/` und Ausgaben-Scan unter `/scan`. Gemeinsamer Zustand wie aktive Session, Steuerjahr und Mock-vs-API-Modus liegt in `frontend/src/context/ChatContext.tsx`; HTTP- und SSE-Kommunikation läuft über `frontend/src/lib/api.ts`.

Das Backend ist eine FastAPI-App mit vier zentralen Routern: `chat`, `sessions`, `scan` und `health`. Chat-Verläufe werden in SQLite gespeichert, beim nächsten Request wieder geladen und zusammen mit RAG-Kontext aus Chroma an die LLM-Engine übergeben. Ingest und Index-Aufbau laufen separat über `backend/ingest/cli.py`.

Mehr Details stehen in [docs/architecture.md](docs/architecture.md).

## Lokale Entwicklung

### Voraussetzungen

- [uv](https://docs.astral.sh/uv/) (Python-Paketmanager)
- [Node.js 20+](https://nodejs.org/) + [pnpm](https://pnpm.io/)
- [Ollama](https://ollama.com/) (optional, für lokale LLM-Inferenz ohne Mock-Modus)

### Setup

```bash
# 1. Abhängigkeiten installieren und lokale Env-Dateien anlegen
make setup

# 2. Frontend aus dem Mock-Modus holen
# frontend/.env.local: NEXT_PUBLIC_USE_MOCK=false

# 3. Backend konfigurieren
# backend/.env aus backend/.env.example prüfen/anpassen

# 4. Backend starten (http://localhost:8000)
make local.api

# 5. Frontend starten (http://localhost:3000)
make local.web
```

`make setup` erstellt bei Bedarf `backend/.env` aus `backend/.env.example` und `frontend/.env.local` aus `frontend/.env.example`.

### Wissensbasis aufbauen

```bash
# Status prüfen — was ist bereits indexiert?
make local.status

# Kerngesetze (EStG, AO, UStG)
make local.ingest YEAR=2025

# Vollständig (+ EStDV, SolzG, GewStG)
make local.ingest-full YEAR=2025

# Einzelne Quellen
make local.ingest-lstr YEAR=2025
make local.ingest-bmf  YEAR=2025
make local.ingest-bfh  YEAR=2025
```

Unterstützte Rechtsquellen:

| Kürzel | Quelle | Relevanz |
| --- | --- | --- |
| `EStG` | Einkommensteuergesetz | Kerngesetz — Werbungskosten, Sonderausgaben, AfA |
| `EStDV` | EStG-Durchführungsverordnung | Konkretisierungen zu EStG-Paragrafen |
| `AO` | Abgabenordnung | Verfahrensrecht, Einspruch, Fristen |
| `UStG` | Umsatzsteuergesetz | Vorsteuerabzug für Freiberufler |
| `SolzG` | Solidaritätszuschlaggesetz | Gesamtsteuerbelastung |
| `GewStG` | Gewerbesteuergesetz | Relevant für Gewerbetreibende |
| `BFH` | BFH-Urteile | Günstige Rechtsprechung und Gestaltungsspielräume |
| `BMF` | BMF-Schreiben | Verwaltungsanweisungen, oft zugunsten des Steuerpflichtigen |
| `LStR` | Lohnsteuer-Richtlinien | Konkrete Pauschalen und Arbeitnehmer-Abzüge |

## Docker

```bash
# Beide Services bauen und starten
docker compose up --build

# Nur Backend
docker compose up backend
```

Persistente Volumes: `chroma_db` (Vektoren), `sqlite_db` (Sessions), `hf_cache` (Embedding-Modell).

## LLM-Provider

### Ollama (Standard, lokal)

```bash
ollama pull gemma4:26b   # empfohlen für Produktion
ollama pull gemma3:4b    # schneller für Tests
```

In `backend/.env`:

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=gemma4:26b
```

### Anthropic (Cloud)

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

## Umgebungsvariablen

Alle Variablen sind in [`backend/.env.example`](backend/.env.example) dokumentiert. Wichtigste Einstellungen:

| Variable | Default | Beschreibung |
| --- | --- | --- |
| `LLM_PROVIDER` | `ollama` | `ollama` oder `anthropic` |
| `OLLAMA_MODEL` | `gemma4:26b` | Ollama-Modellname |
| `RAG_TOP_N` | `5` | Chunks ans LLM nach Re-Ranking (4B-Modelle: 3) |
| `RAG_CHUNK_MAX_CHARS` | `800` | Max. Zeichen pro Chunk (0 = unbegrenzt) |
| `MEMORY_TOKEN_LIMIT` | `2048` | Chat-Verlauf in Tokens |
| `HYDE_ENABLED` | `false` | HyDE Query Expansion aktivieren |

### HuggingFace Token (optional)

Das Embedding-Modell (`intfloat/multilingual-e5-large`) wird beim ersten Ingest von HuggingFace heruntergeladen. Ohne Token ist der Download gedrosselt (~1 MB/s).

1. [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → *New token* → Role: **Read**
2. In `backend/.env` eintragen: `HF_TOKEN=hf_...`

Nach dem ersten Download liegt das Modell unter `~/.cache/huggingface/hub/` und wird lokal gecacht.

## Entwicklung

```bash
make test              # pytest (Backend)
make lint              # ruff check (Backend)
make format            # ruff format + ruff check --fix (Backend)
make typecheck         # mypy (Backend)
make lint.frontend     # eslint (Frontend)
make typecheck.frontend # tsc --noEmit (Frontend)
make help              # alle verfügbaren Targets
```

## CI/CD

GitHub Actions liegen unter [`.github/workflows/`](.github/workflows/):

- `ci.yml`: Backend-Linting, Format-Check, Mypy, Pytest sowie Frontend-Linting und Typecheck
- `check-sources.yml`: jährlicher URL-Check für externe Rechtsquellen mit automatischer Issue-Erstellung bei Ausfällen
