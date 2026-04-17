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

**Kern (EStG, AO, UStG):**

```bash
cd backend
uv run steuerpilot ingest --year 2025
# oder via Make:
make local.ingest
```

**Vollständig (+ EStDV, SolzG, GewStG):**

```bash
cd backend
uv run steuerpilot ingest --laws EStG EStDV AO UStG SolzG GewStG --year 2025
# oder via Make:
make local.ingest-full
```

Unterstützte Gesetze:

| Kürzel | Gesetz | Relevanz |
| --- | --- | --- |
| `EStG` | Einkommensteuergesetz | Kerngesetz — Werbungskosten, Sonderausgaben, AfA |
| `EStDV` | EStG-Durchführungsverordnung | Konkretisierungen zu EStG-Paragrafen, Pauschalen |
| `AO` | Abgabenordnung | Verfahrensrecht, Einspruch, Fristen |
| `UStG` | Umsatzsteuergesetz | Vorsteuerabzug für Freiberufler |
| `SolzG` | Solidaritätszuschlaggesetz | Gesamtsteuerbelastung |
| `GewStG` | Gewerbesteuergesetz | Relevant für Gewerbetreibende und Freiberufler |

## Umgebungsvariablen

| Datei | Variable | Beschreibung |
| --- | --- | --- |
| `backend/.env` | `ANTHROPIC_API_KEY` | Anthropic API Key |
| `backend/.env` | `HF_TOKEN` | HuggingFace API Token (optional, siehe unten) |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL` | Backend-URL (default: `http://localhost:8000`) |

### HuggingFace Token (optional)

Das Embedding-Modell (`intfloat/multilingual-e5-large`) wird beim ersten Ingest-Lauf von HuggingFace heruntergeladen und danach lokal gecacht. Ohne Token ist der Download auf ca. 1 MB/s gedrosselt.

1. Kostenlosen Account erstellen: [huggingface.co/join](https://huggingface.co/join)
2. Token generieren: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → *New token* → Role: **Read**
3. In `backend/.env` eintragen:

```bash
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
```

Nach dem ersten erfolgreichen Download spielt die Drosselung keine Rolle mehr — das Modell liegt dann unter `~/.cache/huggingface/hub/`.
