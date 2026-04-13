# steuerpilot-ai

An intelligent tax assistant powered by RAG, built to simplify and optimize German tax filings using up-to-date legal context.

## Projektstruktur

```text
steuerpilot-ai/
├── frontend/        # Next.js App (App Router, Tailwind CSS, pnpm)
├── backend/         # FastAPI + LlamaIndex + Chroma (uv)
├── data/
│   ├── raw/         # Rohe Rechtsdokumente (EStG, AO, UStG, ...)
│   └── processed/   # Verarbeitete Chunks nach Ingest
├── PRD.md           # Product Requirements Document
└── BACKLOG.md       # Implementierungsplan
```

## Starten

### Frontend

```bash
cd frontend
pnpm install
pnpm dev              # http://localhost:3000
```

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000
```

### Wissensbasis aufbauen

```bash
cd backend
uv run steuerpilot ingest --year 2025
```

## Umgebungsvariablen

| Datei | Variable | Beschreibung |
| --- | --- | --- |
| `backend/.env` | `ANTHROPIC_API_KEY` | Anthropic API Key |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL` | Backend-URL (default: `http://localhost:8000`) |
