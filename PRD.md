# PRD: steuerpilot-ai

**Version:** 0.1
**Datum:** 2026-04-10
**Status:** Draft
**Autor:** Jan-Philipp Praetorius

---

## 1. Zusammenfassung

steuerpilot-ai ist ein KI-gestütztes Tool, das mittels Retrieval-Augmented Generation (RAG) das deutsche Steuerrecht in einen intelligenten Steuerberater-Assistenten verwandelt. Es hilft Privatpersonen und Freiberuflern dabei, ihre Steuererklärung zu optimieren — durch präzise, gesetzlich fundierte Antworten und gezielte Empfehlungen zum Abzug von Ausgaben, Freibeträgen und steuerlichen Gestaltungsmöglichkeiten.

---

## 2. Problemstellung

Das deutsche Steuerrecht ist komplex, fragmentiert und ändert sich jährlich. Für die meisten Steuerpflichtigen ist es schwierig:

- relevante Paragrafen und Urteile selbst zu finden und korrekt anzuwenden
- zu wissen, welche Ausgaben absetzbar sind (und wie sie zu belegen sind)
- ihre Steuerlast legal zu minimieren, ohne teure Steuerberater zu beauftragen
- Änderungen im Steuerrecht rechtzeitig zu berücksichtigen

Bestehende Tools (ELSTER, Steuersoftware wie WISO/Taxfix) bieten Formulare, aber keine echte Beratungstiefe. LLMs ohne Retrieval halluzinieren Paragrafen oder arbeiten mit veraltetem Wissen.

---

## 3. Ziele

### Primärziele

- **Maximale Steuerersparnis**: Das Tool soll das legale Maximum ausschöpfen — jede Grauzone im Steuerrecht wird aktiv geprüft und genutzt, solange sie gesetzlich vertretbar ist
- Steuerpflichtige befähigen, ihre Steuererklärung eigenständig und optimiert einzureichen
- Gesetzeskonformität durch direkte Verankerung im aktuellen Steuerrecht sicherstellen
- Erklärungen und Empfehlungen mit Quellenangabe (Paragraf, Absatz, BMF-Schreiben) liefern

### Sekundärziele
- Zeitaufwand für die Steuererklärung signifikant reduzieren
- Als Lernplattform für Steuerrecht dienen
- Grundlage für zukünftige ELSTER-Integration schaffen

---

## 4. Nicht im Scope (v1)

- Direkte ELSTER-Integration / XML-Export
- Buchführung oder Jahresabschluss für Unternehmen (GmbH, AG)
- Internationales Steuerrecht (DBA, Auslandseinkünfte > einfache Fälle)
- Automatisiertes Befüllen von Formularen
- Echtzeitanbindung an Finanzamt-Bescheide

---

## 5. Zielgruppen

| Persona | Beschreibung |
|---|---|
| **Angestellter Arbeitnehmer** | Macht einmal jährlich Steuererklärung, kennt keine Paragrafen, will einfache Empfehlungen |
| **Freiberufler / Solo-Selbstständiger** | Hat Betriebsausgaben, Homeoffice, Fahrtkosten — komplexere Abzüge, braucht Belastbarkeit |
| **Berufseinsteiger** | Erste Steuererklärung, braucht Erklärungen + Orientierung |
| **Steueraffiner Power-User** | Kennt sich aus, will schnell spezifische Paragrafen und Urteile finden |

---

## 6. Kern-Features

### 6.1 RAG-Pipeline über deutsches Steuerrecht

**Was:** Ingest, Chunking, Embedding und Retrieval der relevanten Rechtsquellen.

**Rechtsquellen (Prio 1):**
- Einkommensteuergesetz (EStG)
- Abgabenordnung (AO)
- Umsatzsteuergesetz (UStG)
- Einkommensteuer-Durchführungsverordnung (EStDV)
- BMF-Schreiben (ausgewählte, relevante)
- Lohnsteuer-Richtlinien (LStR)

**Rechtsquellen (Prio 2):**
- Gewerbesteuergesetz (GewStG)
- Solidaritätszuschlaggesetz (SolzG)
- Relevante BFH-Urteile

> **Entscheidung:** UStG ist Teil von v1 (Prio 1).

**Technischer Ansatz:**
- Dokumente werden als strukturierte Chunks (Paragraf / Absatz-Ebene) verarbeitet
- Jeder Chunk trägt Metadaten: Gesetz, Paragraf, Absatz, Geltungsjahr (`year`)
- Retrieval filtert immer auf `year` — kein versehentliches Mischen von Rechtsständen
- Verweisketten (`i.V.m.`, `nach Maßgabe von § X`) werden beim Retrieval rekursiv aufgelöst: referenzierte Paragrafen werden automatisch als zusätzliche Chunks mitgeladen
- Embedding-Modell: `intfloat/multilingual-e5-large` (Microsoft/HuggingFace, lokal via `sentence-transformers`)
- Vector Store: Chroma (lokal)
- Retrieval: Hybrid-Search (dense + BM25 sparse) für präzises Paragraf-Lookup

### 6.2 Steuererklärungsassistent (Chat-Interface)

**Was:** Konversationeller Assistent, der Fragen zur Steuererklärung beantwortet und Optimierungen empfiehlt.

**Funktionen:**
- Fragen beantworten mit Quellenangabe (`§ 9 Abs. 1 EStG`)
- Absetzbarkeit von Ausgaben prüfen (Homeoffice, Fahrtkosten, Arbeitsmittel, etc.)
- Freibeträge und Pauschalen erklären und anwenden
- Schrittweise durch relevante Anlage-Blöcke führen (Anlage N, S, KAP, etc.)
- Mehrjährige Optimierungen vorschlagen (z. B. Verlustvortrag)

**Optimierungsphilosophie:**

Das Tool agiert nach dem Prinzip **"legales Maximum"**: Es soll nicht nur offensichtliche Abzüge benennen, sondern aktiv Grauzonen im Steuerrecht prüfen und nutzen — z. B. streitige BMF-Positionen, günstige BFH-Urteile die noch nicht in Verwaltungspraxis überführt wurden, oder Gestaltungsspielräume bei Pauschalen. Jede Grauzonenempfehlung wird als solche gekennzeichnet und mit Risikoeinschätzung versehen.

**Antwortformat:**
```
Antwort: [Klare Empfehlung inkl. Maximierungsstrategie]
Rechtsgrundlage: § X Abs. Y EStG / BMF-Schreiben vom ...
Grauzone: [Falls zutreffend: Einschätzung des Risikos + Begründung warum trotzdem empfohlen]
Praxistipp: [Konkreter Hinweis zur Umsetzung / Belegpflicht]
Einschränkung: [Hinweis auf Grenzen oder Ausnahmen]
Weitere Sparpotenziale: [Rückfragen an den Nutzer, um noch mehr herauszuholen]
```

### 6.3 Proaktiver Spar-Dialog

**Was:** Nach jeder Antwort prüft das Tool aktiv, ob durch gezielte Rückfragen weitere Sparpotenziale aufgedeckt werden können. Der Nutzer wird nicht mit einem Fragebogen konfrontiert, sondern erhält kontextabhängige Folgefragen.

**Prinzip:** Das Tool kennt den aktuellen Stand der Konversation und leitet daraus ab, welche Informationen noch fehlen könnten, um die Steuerersparnis weiter zu maximieren.

**Beispiele:**
```
Nutzer: "Ich arbeite im Homeoffice."
Tool:   → Empfehlung Tagespauschale / Arbeitszimmer
        → "Haben Sie auch Arbeitsmittel (Laptop, Monitor, Headset) selbst gekauft?
           Fahrtkosten für gelegentliche Bürotage wären zusätzlich absetzbar —
           haben Sie solche gehabt?"

Nutzer: "Ich habe einen Laptop für 1.200 € gekauft."
Tool:   → Empfehlung Sofortabschreibung GWG / lineare AfA
        → "War das Ihr einziges Arbeitsmittel? Software, Fachliteratur oder
           ein zweiter Monitor könnten ebenfalls absetzbar sein."
```

**Abbruchkriterium:** Keine weiteren Folgefragen, wenn das Tool mit > 90% Konfidenz einschätzt, dass alle relevanten Positionen erfasst sind.

### 6.4 Ausgaben-Optimierungs-Scan

**Was:** Der Nutzer gibt seine Ausgaben / Lebenssituation ein — das Tool prüft aktiv, was absetzbar ist und was fehlt.

**Input-Kategorien:**

- Arbeitsmittel (Laptop, Schreibtisch, Software)
- Homeoffice (Tagespauschale vs. Arbeitszimmer)
- Fahrtkosten (Pendlerpauschale, Dienstreisen)
- Weiterbildung / Fachliteratur
- Versicherungen (Basisabsicherung, BU, Haftpflicht)
- Spenden und Mitgliedsbeiträge
- Kinderbetreuung / außergewöhnliche Belastungen
- Handwerkerleistungen / haushaltsnahe Dienstleistungen

**Output:** Priorisierte Liste mit geschätzter Steuerersparnis pro Position + Quellenangabe.

### 6.5 Jahres-Update-Mechanismus

**Was:** Automatisierter Prozess, der bei Gesetzesänderungen (Jahressteuergesetz, BMF-Schreiben) die Wissensbasis aktualisiert.

- Versionierung der Rechtsquellen pro Steuerjahr
- Diff-Erkennung bei Paragrafen-Updates
- Re-Embedding nur geänderter Chunks

### 6.6 CLI-Tool (Developer-Interface)

**Was:** Kommandozeilen-Interface — primär für Entwicklung, Ingest und Debugging.

**Befehle:**
```bash
steuerpilot ingest --year 2025    # Wissensbasis neu aufbauen
steuerpilot search "§ 9 EStG"    # Direktes Paragraf-Lookup
steuerpilot eval                  # RAGAS Evaluation-Run starten
```

### 6.7 Web-Frontend (Next.js) + Backend (FastAPI)

**Was:** Primäres Nutzer-Interface — saubere Trennung zwischen Python-Backend und React-Frontend.

**Technische Entscheidungen:**

| Entscheidung | Wahl | Begründung |
| --- | --- | --- |
| Next.js Routing | App Router (Next.js 13+) | Aktueller Standard, Server Components |
| Styling | Tailwind CSS | Utility-first, kein CSS-Overhead |
| Streaming | Server-Sent Events (SSE) | Ausreichend für unidirektionalen Chat-Stream |
| Auth | Keine (v1) | Tool läuft lokal, kein Multi-User-Szenario |
| Deployment | Lokal-first, cloud-ready | v1 lokal (`localhost`), Architektur ermöglicht späteres Deployment (Vercel + Railway/Fly.io) |

**Architektur:**

```
Browser (Next.js App Router)
      │  HTTP + SSE (Streaming)
      ▼
FastAPI Backend (Python)
      │
      ├── POST /api/chat          # Konversation mit SSE-Streaming-Response
      ├── POST /api/scan          # Ausgaben-Optimierungs-Scan
      ├── GET  /api/sessions      # Gespeicherte Sessions laden
      └── GET  /api/search        # Direktes Paragraf-Lookup
      │
LlamaIndex RAG Engine + Chroma
```

**Frontend-Komponenten:**

- Chat-Interface mit SSE-Streaming (Antwort erscheint Wort für Wort)
- Quellenangaben als aufklappbare Chips (`§ 9 Abs. 1 EStG ▼`)
- Grauzon-Badges mit Risikostufe (grün / gelb / orange)
- Spar-Potenzial-Sidebar: laufende Summe der geschätzten Ersparnis
- Session-History in der Seitenleiste

> **Deployment-Strategie:** v1 läuft vollständig lokal (`localhost:3000` Frontend, `localhost:8000` Backend). Die Architektur ist von Anfang an deployment-ready gehalten — kein lokaler State im Frontend, Backend zustandslos außer SQLite. Für ein späteres Deployment: Frontend via Vercel, Backend via Railway oder Fly.io.

---

## 7. Technische Architektur

```
┌──────────────────────────────────────────────────────┐
│            Next.js Frontend (Browser)                │
│  Chat · Quellen-Chips · Grauzon-Badges · Spar-Sidebar│
└───────────────────────┬──────────────────────────────┘
          HTTP + SSE (Streaming)
┌───────────────────────▼──────────────────────────────┐
│              FastAPI Backend (Python)                │
│  /api/chat · /api/scan · /api/sessions · /api/search │
└────────┬──────────────────────────────┬──────────────┘
         │                              │
┌────────▼────────┐           ┌─────────▼─────────────┐
│  LlamaIndex     │           │  LLM Provider          │
│  RAG Engine     │           │  (via LLM_PROVIDER)    │
│                 │◄─────────►│                        │
│ - Query Rewrite │           │  anthropic →           │
│ - Retrieval     │           │    claude-sonnet-4-6   │
│ - Re-ranking    │           │  ollama →              │
│ - Verweis-      │           │    lokales Modell      │
│   auflösung     │           └───────────────────────-┘
│ - Re-ranking    │
│ - Verweis-      │
│   auflösung     │
└────────┬────────┘
         │
┌────────▼────────────────────────────────────────────┐
│              Chroma Vector Store (lokal)            │
│                                                     │
│  Chunks: [Gesetz | § | Abs. | Text | year | URL]   │
│  Filter: year (Metadaten-Filter je Query)           │
└────────┬────────────────────────────────────────────┘
         │                              │
┌────────▼────────┐           ┌─────────▼─────────────┐
│ Ingestion (CLI) │           │   SQLite              │
│                 │           │   Konversations-      │
│ Parse → Chunk   │           │   gedächtnis          │
│ Embed → Store   │           └───────────────────────┘
└─────────────────┘
```

### Tech Stack

| Komponente | Technologie |
| --- | --- |
| Sprache Backend | Python 3.12 |
| Dependency Management Backend | uv |
| Dependency Management Frontend | pnpm |
| LLM (Produktion) | `claude-sonnet-4-6` (Anthropic SDK, mit Prompt Caching) |
| LLM (Lokal/Testing) | Ollama — austauschbarer LLM-Provider via LlamaIndex (`llama-index-llms-ollama`) |
| Embeddings | `intfloat/multilingual-e5-large` (lokal, via `sentence-transformers`) |
| Vector Store | Chroma (lokal) |
| Orchestrierung | LlamaIndex |
| Chunking | Hierarchisch (Gesetz → Paragraf → Absatz als verschachtelte Nodes) |
| Re-Ranking | `cross-encoder/ms-marco-MiniLM` (lokal, via `sentence-transformers`) |
| Konversationsgedächtnis | Persistent (SQLite) — sessionübergreifend |
| Backend API | FastAPI (Python) |
| Frontend | Next.js App Router (React, Tailwind CSS) |
| API-Kommunikation | HTTP + SSE (Streaming) |
| Config / Secrets | `.env`-Dateien (Anthropic API Key, nie ins Git) |
| LLM-Provider | Über `LLM_PROVIDER=anthropic\|ollama` in `.env` umschaltbar |
| CLI | Typer + Rich (Developer/Ingest-Interface) |
| Ingest | BeautifulSoup + PDFPlumber für Dokument-Parse |
| Evaluation | RAGAS (automatisierte Runs) + manuelles Goldset (Regression) |
| Testing | pytest |

---

## 8. Nicht-funktionale Anforderungen

| Anforderung | Zielwert |
|---|---|
| Antwortlatenz (Chat) | < 5 Sekunden (mit Streaming) |
| Retrieval-Precision (Top-5) | > 85% relevante Chunks |
| Quellenabdeckung | 100% EStG + AO für v1 |
| Halluzinationsrate | < 5% (gemessen an Paragraf-Zitaten) |
| Aktualität der Wissensbasis | Aktuelles Steuerjahr + Vorjahr |
| Datenschutz | Keine Nutzerdaten persistiert ohne explizite Zustimmung |

---

## 9. Datenquellen & Rechtliches

| Quelle | Lizenz | URL |
|---|---|---|
| gesetze-im-internet.de | Open Government Data (CC0-kompatibel) | Bundesjustizministerium |
| bundesfinanzministerium.de | Öffentlich (BMF-Schreiben) | BMF |
| BFH-Urteile | Öffentlich | bundesfinanzhof.de |

**Hinweis:** Das Tool gibt keine Steuerberatung im Sinne des StBerG. Outputs sind informatorisch und ersetzen keinen zugelassenen Steuerberater. Entsprechende Disclaimer müssen in jeder Antwort verankert sein.

---

## 10. Metriken & Erfolgskriterien

| Metrik | Ziel v1 |
|---|---|
| Korrekte Paragraf-Zitate | > 90% |
| Nutzer-Zufriedenheit (informell) | Positive Bewertung in > 80% der Testfälle |
| Abgedeckte Steuertatbestände | 20 häufigste Fälle für Arbeitnehmer + Freelancer |
| Ingest-Zeit (vollständiges EStG) | < 10 Minuten |
| Retrieval-Geschwindigkeit | < 200ms für Top-10 Chunks |

---

## 11. Meilensteine (v1 Roadmap)

| Phase | Inhalt | Ziel |
| --- | --- | --- |
| **Phase 1** | Ingestion-Pipeline + Vector Store | EStG, AO & UStG vollständig eingebunden, hierarchisches Chunking, year-Filter aktiv |
| **Phase 2** | RAG-Engine + Claude-Integration | Fragen mit Quellenangabe beantwortbar, Verweisauflösung funktioniert, Re-Ranking aktiv |
| **Phase 3** | FastAPI Backend | Alle API-Endpunkte funktionsfähig, SSE-Streaming, SQLite-Memory, CLI für Ingest/Eval |
| **Phase 4** | Next.js Frontend | Chat-UI mit Streaming, Quellen-Chips, Grauzon-Badges, Spar-Sidebar, Session-History |
| **Phase 5** | Proaktiver Spar-Dialog + Ausgaben-Scan | Optimierungsempfehlungen, kontextabhängige Folgefragen, geschätzte Steuerersparnis |
| **Phase 6** | Qualitätssicherung + Eval-Suite | RAGAS-Benchmark über 50+ Testfälle, Halluzinationsrate < 5%, manuelles Goldset |

---

## 12. Offene Fragen

- [x] Welches Embedding-Modell? → `intfloat/multilingual-e5-large` (lokal)
- [x] Lokal-first oder cloud-deploybar? → Chroma lokal
- [x] UStG in v1? → Ja, UStG ist Teil von Prio 1
- [x] Orchestrierung? → LlamaIndex
- [x] Chunking-Strategie? → Hierarchisch (Gesetz → Paragraf → Absatz)
- [x] Re-Ranking? → Cross-Encoder lokal (`cross-encoder/ms-marco-MiniLM`)
- [x] Konversationsgedächtnis? → Persistent via SQLite
- [x] Evaluation? → RAGAS (automatisiert) + manuelles Goldset (Regression)
- [x] Dependency Management? → uv
- [x] Verweisketten? → Verlinkte Paragrafen werden automatisch mit ins Retrieval gezogen (rekursive Auflösung von `i.V.m.`-Verweisen)
- [x] Steuerjahr als Kontext? → Wird als Metadaten-Filter in Chroma mitgeführt (jeder Chunk trägt `year`-Metadatum, jede Query filtert darauf)
