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

- [x] **10.1** API-Client `src/lib/api.ts` mit `fetch`-basiertem SSE via `ReadableStream`
- [x] **10.2** SSE-Parser `src/lib/sseParser.ts`
- [x] **10.3** `useChatAPI`-Hook als Drop-in-Ersatz für `useMockChat`
- [x] **10.4** Feature-Flag `NEXT_PUBLIC_USE_MOCK` zum Umschalten Mock ↔ echte API
- [x] **10.5** Session-Lade-Logik in `SessionSidebar`

---

## Phase 11: Backend — LlamaIndex + Claude Integration

- [x] **11.1** LlamaIndex und Anthropic-Dependencies ergänzen
- [x] **11.2** LLM-Wrapper `app/llm.py` mit Prompt Caching, Singleton via `lru_cache`
- [x] **11.3** System-Prompt in `app/prompts.py` (Antwortformat laut PRD, Disclaimer)
- [x] **11.4** `SimpleChatEngine` mit Konversations-History aus SQLite, SSE-Streaming
- [x] **11.5** Source-Extraktion aus LLM-Output via `===STEUERPILOT_META===`-Block

---

## Phase 12: Backend — RAG-Pipeline

- [x] **12.1** Ingest-Dependencies ergänzen (Chroma, sentence-transformers, pdfplumber, bs4, httpx, typer)
- [x] **12.2** Ingest-Skript: `downloader.py`, `parser.py` (XML von gesetze-im-internet.de), `chunker.py`, `embedder.py`, `store.py`
- [x] **12.3** CLI: `steuerpilot ingest --year 2025`, `steuerpilot search "..."` via Typer
- [x] **12.4** Hybrid-Retriever: Dense (Chroma) + BM25 + Cross-Encoder Re-Ranking, `year`-Metadaten-Filter
- [x] **12.5** Verweis-Auflöser `app/reference_resolver.py` — rekursive `i.V.m.`-Auflösung
- [x] **12.6** `ContextChatEngine` in `app/engine.py` zusammenführen, Chat-Router anpassen

---

## Phase 13: Backend — Ausgaben-Scan

- [x] **13.1** Scan-Schemas: `ScanRequest`, `ScanResult` in `app/models/scan.py`
- [x] **13.2** `POST /api/scan` in `app/routers/scan.py` mit RAG + Claude
- [x] **13.3** Scan-UI im Frontend: `/scan`-Seite mit Formular (Ausgabenpositionen + Kontext), Ergebnis-Cards mit Absetzbarkeit/Risiko/Ersparnis/Quellen; Nav-Link im Header

---

## Phase 14: Qualitätssicherung und Evaluation

- [x] **14.1** Unit Tests: `test_parser.py`, `test_retriever.py`, `test_reference_resolver.py`, `test_chat_api.py`
- [x] **14.2** Goldset anlegen: `evaluation/goldset.json` mit 20 Frage-Antwort-Paaren
- [x] **14.3** RAGAS-Evaluation: `evaluation/eval.py`, CLI-Befehl `steuerpilot eval`

---

## Phase 15: Wissensbasis erweitern — zusätzliche Gesetze

- [x] **15.1** EStDV (Einkommensteuer-Durchführungsverordnung) in `LAW_URLS` ergänzen und ingestieren (`estdv_1955/xml.zip`)
- [x] **15.2** SolzG (Solidaritätszuschlaggesetz) in `LAW_URLS` ergänzen und ingestieren (`solzg_1995/xml.zip`)
- [x] **15.3** GewStG (Gewerbesteuergesetz) in `LAW_URLS` ergänzen und ingestieren (`gewstg/xml.zip`)
- [x] **15.4** LStR (Lohnsteuer-Richtlinien) — eigener Downloader/Scraper für bundesfinanzministerium.de
- [x] **15.5** BMF-Schreiben (ausgewählte, relevante) — Scraper + strukturierter Ingest (Datum, Aktenzeichen als Metadaten)
  - [x] `bmf_catalog.py` — 20 kuratierte Schreiben (Aktenzeichen, Datum, URL, valid_from_year)
  - [x] `scrapers/bmf.py` — Download + PDF/HTML-Parser + Abschnitt-Split + `ParsedLaw`
  - [x] Registry-Eintrag, `ingest-bmf`-CLI-Command, `make local.ingest-bmf`
  - [x] 24 Unit-Tests in `tests/test_bmf_parser.py`
  - [ ] `make local.ingest-bmf` ausführen + unverified URLs manuell prüfen *(zurückgestellt)*
- [x] **15.6** BFH-Urteile (günstige, nicht in Verwaltungspraxis überführte) — Scraper für bundesfinanzhof.de
  - [x] **15.6.1** Katalog `bfh_catalog.py` — 20 kuratierte Urteile (Az., ECLI, Datum, Thema, BStBl-Status)
  - [x] **15.6.2** Downloader/Parser `scrapers/bfh.py` — HTML-Volltext von bundesfinanzhof.de, Split nach Leitsatz / Tatbestand / Entscheidungsgründe
  - [x] **15.6.3** Registry-Eintrag, `ingest-bfh`-CLI-Command, `make local.ingest-bfh`
  - [x] **15.6.4** Unit-Tests `tests/test_bfh_parser.py` — 33 Tests, alle grün

---

## Phase 16: Hierarchisches Chunking

- [x] **16.1** XML-Parser erweitern: Absätze (`Abs. X`) als separate Child-Nodes extrahieren (Bug fix: `<enbez>`/`<titel>` statt falscher Tags; `ParsedLaw` Datenklasse; 229 Paragrafen → 1263 Nodes für EStG)
- [x] **16.2** Zwei-Ebenen-Hierarchie: Paragraf (Parent) → Absatz (Child) mit `NodeRelationship.PARENT/CHILD`; `SimpleDocumentStore` für späteres AutoMerging persistiert
- [x] **16.4** `section`-Metadatum im SourceChunk präzisieren (`Abs. 1`, `Abs. 4a` aus `(N)`-Prefix extrahiert)
- [x] **16.3** AutoMergingRetriever einsetzen: Child-Treffer zu Parent-Node zusammenführen wenn ≥ N Kinder eines Paragrafen gematcht werden (`MERGE_THRESHOLD=3`)
- [~] **16.5** Goldset-Evaluation nach Umstellung (Baseline vs. Hierarchie vergleichen)
  - [x] `eval.snapshot`-Target + Timestamp-JSON + `.gitignore` für Snapshots
  - [x] `automerge`-Flag in `HybridRetriever`, `--no-automerge` in CLI
  - [x] `compare_snapshots()` + `eval-compare`-CLI-Command
  - [x] `eval.ablation`-Target (beide Modi sequenziell + Vergleichstabelle)
  - [ ] Ablation tatsächlich ausführen und Ergebnisse dokumentieren *(zurückgestellt)*

---

---

## Phase 17: Infrastruktur und Betrieb

- [ ] **17.1** GitHub Actions Cron-Job `check-sources.yml` — wöchentlich `make check-sources`, bei Fehlern automatisch GitHub Issue anlegen
- [ ] **17.2** `NEXT_PUBLIC_USE_MOCK=false` setzen, Frontend gegen echtes Backend testen (End-to-End-Smoke-Test)

---

## Phase 18: Frontend-Features

- [ ] **18.1** Chat-Export — Konversation als PDF oder Markdown herunterladen (inkl. Quellenangaben)
- [ ] **18.2** Steuerjahr-Umschalter im Frontend — aktuell hartkodiert auf 2025; Dropdown für Nachveranlagungen
- [ ] **18.3** Session umbenennen — auto-generierter Name durch Nutzer editierbar

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
