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

## Lokale Entwicklung

### Voraussetzungen

- [uv](https://docs.astral.sh/uv/) (Python-Paketmanager)
- [Node.js 20+](https://nodejs.org/) + npm
- [Ollama](https://ollama.com/) (für lokale LLM-Inferenz)

### Setup

```bash
# 1. Umgebungsvariablen konfigurieren
cp backend/.env.example backend/.env
# → backend/.env befüllen (mindestens OLLAMA_MODEL prüfen)

# 2. Abhängigkeiten installieren
make setup

# 3. Backend starten (http://localhost:8000)
make local.api

# 4. Frontend starten (http://localhost:3000)
make local.web
```

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
make lint              # ruff check
make format            # ruff format
make typecheck         # mypy
make help              # alle verfügbaren Targets
```
