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

- [x] **17.1** GitHub Actions Cron-Job `check-sources.yml` — wöchentlich (montags) `steuerpilot check-sources`, bei Fehlern automatisch GitHub Issue mit Quellenübersicht anlegen
- [x] **17.2** `NEXT_PUBLIC_USE_MOCK=false` setzen, Frontend gegen echtes Backend testen (End-to-End-Smoke-Test)

---

## Phase 18: Frontend-Features

- [x] **18.1** Chat-Export — Konversation als Markdown oder PDF (Browser-Print) herunterladen (inkl. Quellenangaben, Risikoeinschätzung, Sparschätzung); Export-Dropdown in ChatContainer oben rechts
- [x] **18.2** Steuerjahr-Umschalter im Frontend — Dropdown in SessionSidebar für 2023/2024/2025, verdrahtet mit `setTaxYear` aus ChatContext
- [x] **18.3** Session umbenennen — auto-generierter Name durch Nutzer editierbar (Doppelklick in SessionSidebar, Enter/Escape/Blur)

---

## Phase 19: LStR HTML-Scraper

- [x] **19.1** LStR-Scraper auf HTML umschreiben

---

## Phase 20: Spezialfall Ideen-/Erfindungs-Transfer

- [x] **20.1** Rechtsquellen fuer den Spezialfall erweitern - `KStG`, `ErbStG`, `ArbNErfG` in Ingest, Parser-Mappings und Referenzaufloesung aufnehmen
- [x] **20.2** Backend-Regelengine + API - neue Tabelle `idea_transfer_cases`, deterministische Bewertung, `GET/PUT/POST`-API und Zusammenfassungsnachricht in der Session
- [x] **20.3** Frontend-Spezialseite - eigenstaendige `/idea-transfer`-Seite mit 5-Schritt-Flow, Ampel, Sparspanne, Dokumentenliste und Quellen
- [x] **20.4** Chat-Onboarding + Session-Persistenz - lokale Quick Replies in neuen Sessions, Vorbelegung aus dem Chat und strukturierte Speicherung pro Session
- [x] **20.5** Tests + Doku - Backend-Tests fuer API/Persistenz sowie PRD-/Backlog-Abgleich auf den implementierten Spezialfall

---

## Phase 21: Instagram-Post-Check

- [x] **21.1** Rechtsquellen & Modelle — Pydantic-Schemas `InstagramClaim`, `InstagramEvaluatedTip`, `InstagramPostCheck`, `TaxPrepItem` in `app/models/instagram_check.py`; Kategorien (`TipCategory`) und Steuererklärungsfelder (`ReturnBucket`) als Literale
- [x] **21.2** Bild-Upload & KI-Analyse — `POST /api/instagram-check/analyze` nimmt Multipart-Upload (ein oder mehrere Bilder), extrahiert steuerrelevante Tipps via Vision-LLM und legt `InstagramClaim`-Objekte mit Follow-up-Fragen an; Bilder werden lokal unter `upload_path` gespeichert
- [x] **21.3** Claim-Verwaltung — `GET /api/instagram-check/{session_id}` lädt bestehenden Check; `PUT /api/instagram-check/{session_id}` speichert editierte Claims (Text, Kategorie, Bucket, Status, Follow-up-Antworten)
- [x] **21.4** RAG-Bewertung — `POST /api/instagram-check/evaluate` bewertet ausgewählte Claims gegen die Wissensbasis (EStG, BFH, BMF), gibt Ampelfarbe, Erklärung, Sparpotenzial und benötigte Belege zurück
- [x] **21.5** TaxPrep-Export — `GET /api/tax-prep/{session_id}` gibt strukturierte `TaxPrepItem`-Liste aus bestätigten Tipps zurück (Quelle, Kategorie, Risiko, Belege)
- [x] **21.6** Datenbankschema — Tabellen `instagram_checks`, `instagram_images`, `instagram_claims`, `instagram_follow_up_questions`, `instagram_evaluated_tips`, `tax_prep_items` in `app/database.py`
- [x] **21.7** Frontend-Seite — `/instagram-check` mit mehrstufigem Flow: Bild-Upload → Claim-Review (editierbar, markierbar) → Bewertungs-Ergebnis mit Ampel, Sparschätzung, Belegen und Quellen-Chips
- [x] **21.8** API-Client & Typen — `fetchInstagramCheck`, `analyzeInstagramCheck`, `saveInstagramCheck`, `evaluateInstagramCheck`, `fetchTaxPrepItems` in `frontend/src/lib/api.ts`; Typdefinitionen in `frontend/src/types/instagramCheck.ts`
- [x] **21.9** Tests — `backend/tests/test_instagram_check_api.py` mit API-Integration-Tests (Analyze, Save, Evaluate, TaxPrep)

---

## Phase 22: Proaktiver Steuer-Interview-Check

Ziel: Die KI führt ein strukturiertes Interview durch und leitet eigeninitiativ Steuersparpotenziale ab — ohne dass der Nutzer wissen muss, was er fragen soll. Der Flow ist ähnlich dem Instagram-Check (mehrstufig, RAG-gestützte Auswertung, strukturierter Report), aber mit einem geführten Frage-Antwort-Dialog als Eingabe statt Bildern.

### Konzept

**Ablauf:** Nutzer startet Interview → KI stellt ~20 Fragen in 8 Kategorien (adaptive Folgefragen je nach Antwort) → Nutzer beantwortet → KI wertet jede Kategorie via RAG aus → Report mit Ampel, Sparschätzung und benötigten Belegen pro Position.

**Frage-Kategorien:**
1. **Basisdaten & Sonderausgaben** — Beschäftigungsverhältnis, Familienstand, Kinder; Spenden & Mitgliedsbeiträge (§ 10b EStG), Kirchensteuer, Unterhaltszahlungen an Ex-Partner (§ 10 EStG)
2. **Arbeit & Beruf** — Homeoffice/Arbeitszimmer, Pendeln, Arbeitsmittel, Weiterbildung, Berufskleidung; Selbstständige: Betriebsausgaben, Fahrzeug, Bürokosten
3. **Wohnen, Haushalt & Energie** — Miete vs. Eigentum, haushaltsnahe Dienstleistungen (Putzhilfe, Handwerker), Umzug aus beruflichen Gründen, energetische Sanierung (§ 35c EStG), Photovoltaik-Steuerfreiheit
4. **Nebenberuf & Ehrenamt** — Übungsleiterpauschale (§ 3 Nr. 26 EStG, bis 3.000 €/Jahr steuerfrei), Ehrenamtspauschale (§ 3 Nr. 26a EStG, bis 840 €/Jahr), freiberufliche Nebentätigkeit
5. **Vermietung & Verpachtung** — Vermietete Immobilien, AfA (2–3% p.a.), Renovierungs- und Werbungskosten (§ 21 EStG); nur wenn Nutzer vermietet
6. **Vorsorge & Versicherungen** — Riester/Rürup/bAV, PKV/Zusatzversicherung, Berufsunfähigkeit
7. **Kapitalanlagen** — Verlustverrechnungstöpfe ausgeschöpft, ausländische Quellensteuer anrechenbar, Freistellungsauftrag optimal verteilt (§ 20 EStG)
8. **Gesundheit, Pflege & außergewöhnliche Belastungen** — Krankheitskosten, Behinderten-Pauschbetrag (§ 33b EStG, bis 7.400 €/Jahr ohne Einzelnachweis), Pflege-Pauschbetrag für pflegende Angehörige

**Adaptive Logik (Beispiele):**
- Homeoffice: Ja → Folgefrage: "Eigenes abgeschlossenes Arbeitszimmer?" → beeinflusst ob Pauschale (1.260 €) oder tatsächliche Kosten angesetzt werden können
- Kinder: Ja → Folgefragen: Anzahl, Alter, Kinderbetreuungskosten, Schulgeld
- Selbstständig: Ja → zusätzlicher Block Betriebsausgaben
- Eigentum: Ja → Folgefragen zu energetischer Sanierung und Photovoltaik
- Vermietet: Ja → Kategorie 5 (Vermietung) wird freigeschaltet
- Ehrenamt/Nebenberuf: Ja → Folgefrage zu Art der Tätigkeit (Übungsleiter, Verein, freiberuflich)
- Behinderung/Pflegegrad: Ja → Folgefrage zu Grad der Behinderung bzw. Pflegestufe

---

### ~~22.1 — Fragen-Katalog (`backend/app/interview_catalog.py`) ✓~~

Statische Datei mit allen Fragen als Python-Datenklassen. Jede Frage hat:
- `id: str` — eindeutige ID (z.B. `"work.homeoffice"`)
- `category: str` — eine der 8 Kategorien
- `text: str` — Fragetext auf Deutsch
- `answer_type: Literal["bool", "choice", "number", "text"]`
- `options: list[str] | None` — bei Choice-Fragen
- `condition: tuple[str, Any] | None` — `(question_id, expected_value)` — nur stellen wenn Vorbedingung erfüllt
- `rag_hint: list[str]` — Gesetze die für diese Frage relevant sind (für gefilterte RAG-Auswertung)

Beispiel-Einträge:
```python
Question(id="base.employment", category="basis", text="Wie bist du beschäftigt?",
         answer_type="choice", options=["Angestellt", "Selbstständig", "Beides", "Beamter", "Rentner"])
Question(id="base.donations", category="basis", text="Hast du 2025 Spenden oder Mitgliedsbeiträge geleistet?",
         answer_type="bool", rag_hint=["EStG"])
Question(id="base.alimony", category="basis", text="Zahlst du Unterhalt an einen Ex-Partner?",
         answer_type="bool", rag_hint=["EStG"])
Question(id="work.homeoffice", category="arbeit", text="Hast du 2025 von zu Hause gearbeitet?",
         answer_type="bool", rag_hint=["EStG", "LStR", "BMF"])
Question(id="work.homeoffice_room", category="arbeit", text="Hast du ein abgeschlossenes Arbeitszimmer?",
         answer_type="bool", condition=("work.homeoffice", True), rag_hint=["EStG", "BMF"])
Question(id="work.commute_km", category="arbeit", text="Wie viele Kilometer beträgt deine einfache Pendlerstrecke?",
         answer_type="number", condition=("base.employment", "Angestellt"), rag_hint=["EStG", "LStR"])
Question(id="home.owns_property", category="wohnen", text="Wohnst du in einer eigenen Immobilie?",
         answer_type="bool", rag_hint=["EStG"])
Question(id="home.energy_renovation", category="wohnen", text="Hast du 2025 energetische Sanierungsmaßnahmen durchgeführt?",
         answer_type="bool", condition=("home.owns_property", True), rag_hint=["EStG", "BMF"])
Question(id="side.volunteer", category="nebenberuf", text="Übst du ein Ehrenamt oder eine Nebentätigkeit aus?",
         answer_type="bool", rag_hint=["EStG"])
Question(id="rental.has_rental", category="vermietung", text="Vermietest du eine Immobilie oder ein Zimmer?",
         answer_type="bool", rag_hint=["EStG"])
Question(id="health.disability", category="gesundheit", text="Liegt bei dir oder einem Angehörigen eine anerkannte Behinderung vor?",
         answer_type="bool", rag_hint=["EStG"])
```

---

### 22.2 — Datenbankschema (`backend/app/database.py`)

Neue Tabellen:
```sql
CREATE TABLE tax_interviews (
    session_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'in_progress',  -- in_progress | completed | evaluated
    tax_year INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE tax_interview_answers (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES tax_interviews(session_id),
    question_id TEXT NOT NULL,
    answer TEXT NOT NULL,  -- JSON-encoded (bool/str/int)
    created_at TEXT NOT NULL
);

CREATE TABLE tax_interview_findings (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES tax_interviews(session_id),
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    traffic_light TEXT NOT NULL,  -- green | yellow | red
    explanation TEXT NOT NULL,
    estimated_saving_eur INTEGER,
    required_evidence TEXT NOT NULL,  -- JSON array
    sources TEXT NOT NULL,  -- JSON array
    created_at TEXT NOT NULL
);
```

---

### 22.3 — Pydantic-Modelle (`backend/app/models/tax_interview.py`)

```python
class TaxInterviewStatus(str, Enum): ...  # in_progress | completed | evaluated
class AnswerType(str, Enum): ...          # bool | choice | number | text
class TrafficLight(str, Enum): ...        # green | yellow | red

class InterviewQuestion(BaseModel):
    id: str
    category: str
    text: str
    answer_type: AnswerType
    options: list[str] | None = None

class TaxInterviewAnswer(BaseModel):
    question_id: str
    answer: bool | str | int  # discriminated by question type

class TaxInterviewFinding(BaseModel):
    category: str
    title: str
    traffic_light: TrafficLight
    explanation: str
    estimated_saving_eur: int | None
    required_evidence: list[str]
    sources: list[Source]

class TaxInterview(BaseModel):
    session_id: str
    status: TaxInterviewStatus
    tax_year: int
    answers: dict[str, bool | str | int]   # question_id → answer
    next_question: InterviewQuestion | None  # None wenn Interview abgeschlossen
    findings: list[TaxInterviewFinding] | None
    updated_at: datetime
```

---

### 22.4 — Interview-Engine (`backend/app/tax_interview.py`)

Kernfunktionen:

**`get_next_question(answers: dict) -> InterviewQuestion | None`**
Iteriert den Katalog, prüft Bedingungen (`condition`-Feld) gegen bereits gegebene Antworten, gibt die erste unbeantwortete Frage zurück. Gibt `None` zurück wenn alle anwendbaren Fragen beantwortet sind → Interview abgeschlossen.

**`evaluate_interview(session_id, tax_year, answers, db) -> list[TaxInterviewFinding]`**
Wird nach Abschluss des Interviews aufgerufen. Für jede Kategorie:
1. Relevante Antworten zu einem Kontext-String zusammenfassen
2. RAG-Query mit Kategorie-spezifischem Filter (`rag_hint`-Gesetze) ausführen
3. LLM-Call mit Antwort-Kontext + RAG-Chunks → strukturiertes Finding (Ampel, Erklärung, Sparschätzung, Belege)
4. Findings in DB persistieren

Evaluierung läuft kategorie-weise (5 parallele RAG+LLM-Calls via `asyncio.gather`) für kurze Gesamtlaufzeit.

---

### 22.5 — API-Router (`backend/app/routers/tax_interview.py`)

```
GET  /api/tax-interview/{session_id}          → TaxInterview (aktueller Stand + nächste Frage)
POST /api/tax-interview/{session_id}/start    → TaxInterview anlegen / zurücksetzen
PUT  /api/tax-interview/{session_id}/answer   → Antwort speichern, nächste Frage zurückgeben
POST /api/tax-interview/{session_id}/evaluate → RAG-Auswertung starten → TaxInterview mit Findings
```

Die `answer`-Route gibt nach dem Speichern sofort die nächste Frage zurück (oder `next_question: null` wenn abgeschlossen) — kein separater State-Load nötig.

---

### 22.6 — Frontend: Typen & API-Client

**`frontend/src/types/taxInterview.ts`**
TypeScript-Entsprechungen der Pydantic-Modelle: `TaxInterview`, `InterviewQuestion`, `TaxInterviewFinding`, `TaxInterviewStatus`.

**`frontend/src/lib/api.ts`** — neue Funktionen:
- `fetchTaxInterview(sessionId)` → `TaxInterview | null`
- `startTaxInterview(sessionId, taxYear)` → `TaxInterview`
- `submitTaxInterviewAnswer(sessionId, questionId, answer)` → `TaxInterview`
- `evaluateTaxInterview(sessionId, taxYear)` → `TaxInterview`

---

### 22.7 — Frontend: Interview-Seite (`frontend/src/app/tax-interview/page.tsx`)

**Drei Phasen in einer Seite:**

**Phase 1 — Start**
Kurze Erklärung ("Ich stelle dir ~15 Fragen zu deiner Steuersituation und suche dann eigenständig nach Sparpotenzial."), Start-Button, Hinweis auf Datensensitivität.

**Phase 2 — Interview (Frage für Frage)**
- Fortschrittsbalken (Frage X von ~Y, geschätzt)
- Frage-Text prominent
- Antwort-UI je nach `answer_type`:
  - `bool` → Ja/Nein-Buttons
  - `choice` → Auswahl-Kacheln (wie beim Ideen-Transfer-Flow)
  - `number` → Zahlen-Input mit Einheit
  - `text` → Textarea
- "Weiter"-Button → ruft `submitTaxInterviewAnswer` auf, rendert nächste Frage
- "Überspringen"-Option für optionale Fragen

**Phase 3 — Report**
Nach `evaluate` (mit Lade-Indikator + Status-Meldungen):
- Gesamt-Sparschätzung prominent (Summe aller `estimated_saving_eur`)
- Pro Kategorie eine Karte: Ampel + Titel + Erklärung + Belege + Quellen-Chips
- Sortiert nach Sparschätzung absteigend
- "In Chat besprechen"-Button öffnet neuen Chat mit Kontext dieser Kategorie

---

### 22.8 — Tests (`backend/tests/test_tax_interview.py`)

- `test_question_routing_basics` — erste Frage ist immer Basisdaten
- `test_conditional_question_skipped` — homeoffice_room nicht gestellt wenn homeoffice=False
- `test_conditional_question_shown` — homeoffice_room gestellt wenn homeoffice=True
- `test_selbststaendig_extra_questions` — Selbstständigen-Block erscheint nur bei korrektem Beschäftigungsstatus
- `test_interview_complete_when_all_answered` — `get_next_question` gibt None zurück wenn fertig
- `test_api_start_creates_interview` — POST /start legt Interview an
- `test_api_answer_advances_question` — PUT /answer gibt nächste Frage zurück
- `test_api_evaluate_returns_findings` — POST /evaluate liefert strukturierten Report (LLM gemockt)

---

### Abhängigkeiten innerhalb der Phase

```
22.1 (Katalog) → 22.4 (Engine) → 22.5 (API)
22.2 (DB)      → 22.4 (Engine)
22.3 (Modelle) → 22.4 (Engine) → 22.5 (API) → 22.6 (Frontend-Client) → 22.7 (UI)
22.5 (API)     → 22.8 (Tests)
```

22.1–22.3 können parallel entwickelt werden. 22.7 (UI) und 22.8 (Tests) können erst nach 22.5 beginnen.

---

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
