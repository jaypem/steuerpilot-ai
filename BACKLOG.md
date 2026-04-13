# Implementierungsplan: steuerpilot-ai

## Status-Legende

- [ ] Offen
- [~] In Arbeit
- [x] Erledigt

---

## Phase 0: Repo-Grundgerüst

- [x] **0.1** Top-Level-Verzeichnisse anlegen: `frontend/`, `backend/`, `data/raw/`, `data/processed/`
- [x] **0.2** `EStG.pdf` verschieben nach `data/raw/EStG_2025.pdf`
- [x] **0.3** `.gitignore` um Next.js, Chroma, SQLite und Modelle erweitern
- [x] **0.4** `README.md` mit Verzeichnisübersicht und Startbefehlen aktualisieren

---

## Phase 1: Frontend — Projekt-Setup

- [x] **1.1** Next.js-Projekt initialisieren (`pnpm create next-app@latest` mit App Router, TypeScript, Tailwind)
- [x] **1.2** Globales Layout definieren (`layout.tsx`, `globals.css`, Geist-Font, `lang="de"`)
- [x] **1.3** Farbschema und Design-Tokens in `globals.css` via `@theme` (Tailwind v4 — Grauzon-Farben, surface, accent, sidebar, saving)
- [x] **1.4** `.env.local` und `.env.example` anlegen (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_USE_MOCK`)

---

## Phase 2: Frontend — Grundlayout

- [x] **2.1** Haupt-App-Shell: Drei-Spalten-Layout (Session-Sidebar | Chat | Spar-Sidebar)
- [x] **2.2** Layout-Komponenten: `AppShell`, `SessionSidebar`, `SparSidebar`, `Header`
- [x] **2.3** Responsive Kollaps beider Sidebars auf schmalen Screens (Overlay + Toggle-Buttons)

---

## Phase 3: Frontend — Chat-Komponenten

- [x] **3.1** Typ-Definitionen: `Message`, `Source`, `RiskBadge` in `src/types/chat.ts`
- [x] **3.2** Nachrichten-Komponenten: `MessageList`, `UserMessage`, `AssistantMessage`
- [x] **3.3** `SourceChip` — aufklappbarer Chip mit Paragraf-Text
- [x] **3.4** `RiskBadge` — drei Varianten (low/medium/high) mit Tooltip
- [x] **3.5** `ChatInput` — Textarea mit Auto-Resize, Enter-Submit, Zeichenzähler
- [x] **3.6** `ChatContainer` — bindet alle Komponenten zusammen, Dummy-Nachrichten

---

## Phase 4: Frontend — Mock-SSE-Streaming

- [x] **4.1** Mock-Daten in `src/lib/mockData.ts` (7 Frage-Antwort-Paare: Homeoffice, Laptop, Pendler, Riester, Handwerker, Weiterbildung, Versicherung)
- [x] **4.2** `useMockChat`-Hook mit simuliertem Streaming (35ms/Wort via `setInterval`, Sources + Badge nach Stream-Ende)
- [x] **4.3** Streaming-Cursor (`animate-pulse` Balken) in `AssistantMessage` — war bereits vorhanden
- [x] **4.4** `useMockChat` in `ChatContainer` eingebunden, setTimeout-Platzhalter entfernt

---

## Phase 5: Frontend — Sidebars und State

- [x] **5.1** `SparSidebar` — animierte Ersparnis-Summe (Glow-Effekt bei Änderung), Positions-Liste mit Risiko-Indikator
- [x] **5.2** Session-Typen und Mock-Daten in `src/types/session.ts` und `src/lib/mockSessions.ts`
- [x] **5.3** `SessionSidebar` — liest Sessions aus Context, Ersparnis pro Session, relative Datumsformatierung
- [x] **5.4** `ChatContext` — globaler State (messages, sessions, totalSaving, savingEntries), `ChatProvider` in AppShell

---

## Phase 6: Frontend — Feinschliff

- [x] **6.1** Welcome-Screen mit Beispielfragen, Loading States, Error-Toast
- [x] **6.2** Keyboard-Navigation, ARIA-Labels, Accessibility
- [x] **6.3** Markdown-Rendering in `AssistantMessage` via `react-markdown` + `remark-gfm`

---

## Phase 7: Backend — FastAPI Setup

- [x] **7.1** Python-Projekt initialisieren (`uv init`, `uv python pin 3.12`, Basis-Dependencies)
- [x] **7.2** Projektstruktur anlegen (`app/main.py`, `app/config.py`, `app/routers/`, `app/models/`)
- [x] **7.3** Konfiguration via `pydantic-settings` (API Key, CORS Origins, Tax Year)
- [x] **7.4** CORS-Middleware und `GET /health` Endpunkt

---

## Phase 8: Backend — SSE-Streaming-Endpunkt

- [x] **8.1** Pydantic-Schemas: `ChatRequest`, `StreamChunk` in `app/models/chat.py`
- [x] **8.2** SSE-Generator mit `StreamingResponse` und Dummy-Text in `app/routers/chat.py`
- [x] **8.3** SSE-Event-Format finalisieren (`text`, `source`, `risk_badge`, `saving`, `done`, `error`)
- [x] **8.4** Error Handling im Generator

---

## Phase 9: Backend — SQLite Session-Memory

- [x] **9.1** `app/database.py` mit `aiosqlite` — Tabellen `sessions` und `messages`
- [x] **9.2** Sessions-Router: `GET /api/sessions`, `GET /api/sessions/{id}`, `DELETE /api/sessions/{id}`
- [x] **9.3** Chat-Endpunkt mit Persistenz verbinden (Message nach Stream in DB schreiben)

---

## Phase 10: Frontend — Echte API-Anbindung

- [ ] **10.1** API-Client `src/lib/api.ts` mit `fetch`-basiertem SSE via `ReadableStream`
- [ ] **10.2** SSE-Parser `src/lib/sseParser.ts`
- [ ] **10.3** `useChatAPI`-Hook als Drop-in-Ersatz für `useMockChat`
- [ ] **10.4** Feature-Flag `NEXT_PUBLIC_USE_MOCK` zum Umschalten Mock ↔ echte API
- [ ] **10.5** Session-Lade-Logik in `SessionSidebar`

---

## Phase 11: Backend — LlamaIndex + Claude Integration

- [ ] **11.1** LlamaIndex und Anthropic-Dependencies ergänzen
- [ ] **11.2** LLM-Wrapper `app/llm.py` mit Prompt Caching, Singleton via `lru_cache`
- [ ] **11.3** System-Prompt in `app/prompts.py` (Antwortformat laut PRD, Disclaimer)
- [ ] **11.4** `SimpleChatEngine` mit Konversations-History aus SQLite, SSE-Streaming
- [ ] **11.5** Source-Extraktion aus LLM-Output via `[[§X:Gesetz:Abs.Y]]`-Marker

---

## Phase 12: Backend — RAG-Pipeline

- [ ] **12.1** Ingest-Dependencies ergänzen (Chroma, sentence-transformers, pdfplumber, bs4, httpx, typer)
- [ ] **12.2** Ingest-Skript: `downloader.py`, `parser.py` (XML von gesetze-im-internet.de), `chunker.py`, `embedder.py`, `store.py`
- [ ] **12.3** CLI: `steuerpilot ingest --year 2025`, `steuerpilot search "..."` via Typer
- [ ] **12.4** Hybrid-Retriever: Dense (Chroma) + BM25 + Cross-Encoder Re-Ranking, `year`-Metadaten-Filter
- [ ] **12.5** Verweis-Auflöser `app/reference_resolver.py` — rekursive `i.V.m.`-Auflösung
- [ ] **12.6** `ContextChatEngine` in `app/engine.py` zusammenführen, Chat-Router anpassen

---

## Phase 13: Backend — Ausgaben-Scan

- [ ] **13.1** Scan-Schemas: `ScanRequest`, `ScanResult` in `app/models/scan.py`
- [ ] **13.2** `POST /api/scan` in `app/routers/scan.py` mit RAG + Claude

---

## Phase 14: Qualitätssicherung und Evaluation

- [ ] **14.1** Unit Tests: `test_parser.py`, `test_retriever.py`, `test_reference_resolver.py`, `test_chat_api.py`
- [ ] **14.2** Goldset anlegen: `evaluation/goldset.json` mit 20 Frage-Antwort-Paaren
- [ ] **14.3** RAGAS-Evaluation: `evaluation/eval.py`, CLI-Befehl `steuerpilot eval`

---

## Abhängigkeiten

```text
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 ──┐
Phase 0 → Phase 7 → Phase 8 → Phase 9 → Phase 11 → Phase 12 ───────────┤
                                                                         ↓
                                                                    Phase 10
                                                                    Phase 13
                                                                    Phase 14
```

Frontend (Phase 1–6) und Backend-Grundgerüst (Phase 7–9) können parallel entwickelt werden.  
Phase 10 verbindet beide Stränge und setzt Phase 6 + Phase 9 voraus.
