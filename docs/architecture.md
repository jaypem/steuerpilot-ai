# Architecture

`steuerpilot-ai` besteht aus einem Next.js-Frontend und einem FastAPI-Backend, die über REST und Server-Sent Events kommunizieren.

## Frontend

- `frontend/src/app/page.tsx`: Chat-Oberfläche
- `frontend/src/app/scan/page.tsx`: Ausgaben-Scan
- `frontend/src/context/ChatContext.tsx`: gemeinsamer Zustand für Sessions, ausgewähltes Steuerjahr, Saving-Summary und Mock-vs-API-Modus
- `frontend/src/lib/api.ts`: REST- und SSE-Client zum Backend

## Backend

- `backend/app/main.py`: FastAPI-App, Lifespan, SQLite-Initialisierung, CORS
- `backend/app/routers/chat.py`: `/api/chat` als SSE-Endpunkt, Persistenz von Nutzer- und Assistentenantworten
- `backend/app/routers/sessions.py`: Session-Liste, Detailansicht, Umbenennen, Löschen
- `backend/app/routers/scan.py`: strukturierter Ausgaben-Scan mit Steuerjahr-Bezug
- `backend/app/engine.py`: lädt Session-Verlauf aus SQLite, baut Chat-Engine und streamt Antwort-Chunks
- `backend/app/retriever.py`: Hybrid Retrieval aus Chroma, BM25 und Re-Ranking
- `backend/app/reference_resolver.py`: löst Paragraphen-Verweise gesetzsspezifisch auf

## Datenhaltung

- SQLite speichert Sessions und Chat-Nachrichten
- Chroma speichert Embeddings und Retrieval-Metadaten
- `data/` enthält heruntergeladene Rohquellen für den Ingest

## Ingest-Pipeline

- `backend/ingest/cli.py`: Einstiegspunkt für Ingest, Suche und Evaluation
- `backend/ingest/scrapers/`: Downloader für BFH, BMF und LStR
- `backend/ingest/parser.py` und `backend/ingest/store.py`: Parsing, Chunking und Persistenz in Chroma

## Request-Fluss

1. Das Frontend sendet eine Chat- oder Scan-Anfrage inklusive `session_id` und `tax_year`.
2. Das Backend lädt für Chat-Anfragen den bisherigen Verlauf aus SQLite.
3. Die Engine baut den RAG-Kontext aus Chroma für das angefragte Steuerjahr auf.
4. Die Antwort wird als SSE-Stream mit Text-, Quellen-, Risiko- und Spar-Chunks ans Frontend gesendet.
5. Nach Abschluss persistiert das Backend den vollständigen Austausch wieder in SQLite.
