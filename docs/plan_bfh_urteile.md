# Implementierungsplan: Phase 15.6 — BFH-Urteile

## Ziel

Günstige BFH-Urteile, die die Finanzverwaltung noch nicht in die eigene Praxis übernommen hat, als vierte Wissensebene in die RAG-Pipeline aufnehmen. Damit kann steuerpilot dem Nutzer Informationsvorsprünge liefern, die über das hinausgehen, was Finanzbeamte im Massenverfahren anwenden.

Zur Begründung warum diese Quelle wichtig ist: [docs/justification.md](justification.md#ebene-4--rechtsprechung-geplant)

---

## Hintergrund

BFH-Urteile werden auf [bundesfinanzhof.de](https://www.bundesfinanzhof.de/entscheidungen/entscheidungen-online/) als HTML-Volltext veröffentlicht. Ein Urteil gilt als „von der Verwaltung übernommen", sobald das BMF es im **BStBl II** (Bundessteuerblatt Teil II) veröffentlicht oder ein Anwendungsschreiben herausgibt. Bis dahin ist es für den Berater verwendbar, aber die Finanzverwaltung wendet es im Massenverfahren nicht an.

Struktur eines BFH-Urteils (HTML):
```
Leitsatz          — das entscheidende Ergebnis in 1–3 Sätzen
Tatbestand        — Sachverhalt (was ist passiert?)
Entscheidungsgründe — Herleitung und Begründung
Tenor             — Entscheidungsformel
```

Metadaten die bundesfinanzhof.de liefert:
- Aktenzeichen (z.B. `VI R 15/20`)
- ECLI (z.B. `ECLI:DE:BFH:2021:U.010921.VIR15.20.0`)
- Datum, Senat, Entscheidungsart (Urteil / Beschluss)
- BStBl-Aufnahme ja/nein (entscheidet ob „noch nicht von Verwaltung übernommen")

---

## Schritt-für-Schritt-Plan

### Schritt 1 — Katalog kuratieren (`bfh_catalog.py`)

**Datei:** `backend/ingest/scrapers/bfh_catalog.py`

Analog zu `bmf_catalog.py` eine `BfhUrteil`-Dataclass und eine kuratierte Liste von ~20 günstigen Urteilen:

```python
@dataclass(frozen=True)
class BfhUrteil:
    id: str               # snake_case, URL-sicher
    aktenzeichen: str     # z.B. "VI R 15/20"
    ecli: str             # z.B. "ECLI:DE:BFH:2021:U.010921.VIR15.20.0"
    datum: str            # ISO YYYY-MM-DD
    senat: str            # z.B. "VI. Senat"
    betreff: str          # Kurzbeschreibung des Urteils
    url: str              # Direkt-URL auf bundesfinanzhof.de
    thema: str            # Kurzbezeichnung
    valid_from_year: int  # ab welchem VZ relevant
    bstbl_aufgenommen: bool = False   # True = Verwaltung hat übernommen
    superseded: bool = False
```

Zu recherchierende Themen (Startpunkt für Katalog):
| Thema | Stichworte |
|---|---|
| Homeoffice ohne Arbeitszimmer | Nutzung Küchentisch, kein abgeschlossener Raum |
| Doppelte Haushaltsführung — Kosten | Möblierungszuschläge, Höchstbetrag |
| Arbeitsmittel / Berufskleidung | Grenzfälle bürgerliche vs. typische Berufskleidung |
| Fortbildungskosten | Erststudium nach Ausbildung |
| Fahrtkosten / erste Tätigkeitsstätte | Zeitarbeitnehmer, häufig wechselnde Einsatzorte |
| Unterhaltszahlungen als agB | Nachweispflichten |
| Steuerfreie Zuschläge (§ 3b EStG) | Berechnungsgrundlagen Schichtarbeit |
| Verluste aus Kapitalvermögen | Termingeschäfte (§ 20 Abs. 6 S. 5 EStG) — verfassungsrechtlich fraglich |
| Vorfälligkeitsentschädigung | Werbungskosten bei Veräußerung Vermietungsobjekt |
| Haushaltsnahe Dienstleistungen (§ 35a EStG) | Grenzfälle handwerkliche vs. haushaltsnahe Leistung |

Hilfsmittel zur Katalogrecherche:
- [bundesfinanzhof.de/entscheidungen-online](https://www.bundesfinanzhof.de/entscheidungen/entscheidungen-online/) — Volltextsuche
- NWB / Haufe — kennzeichnen BFH-Urteile als „BMF-nicht-angewandt"
- `bstbl_aufgenommen=False` setzt man für Urteile, die **nicht** im BStBl II stehen

---

### Schritt 2 — Downloader und Parser (`bfh.py`)

**Datei:** `backend/ingest/scrapers/bfh.py`

```
Technischer Ablauf:
  1. Aus bfh_catalog.py alle aktiven Urteile laden (superseded=False, valid_from_year ≤ year)
  2. HTML-Seite herunterladen (httpx, User-Agent, Cache als BFH_{id}.html)
  3. Inhalt strukturiert parsen:
       a) Leitsatz-Block extrahieren
       b) Entscheidungsgründe in Abschnitte splitten (Randnummern "1.", "2." oder Rn.)
       c) Tatbestand als Kontext-Block
  4. Pro Abschnitt ein LlamaIndex Document mit Metadaten
  5. Fehlgeschlagene Downloads überspringen (Warnung, kein Abbruch)
```

**Metadaten pro Document:**
```python
{
    "law": "BFH",
    "paragraph": aktenzeichen,       # z.B. "VI R 15/20"
    "ecli": ecli,
    "section": section_label,        # z.B. "Leitsatz" / "Rn. 12"
    "title": betreff,
    "datum": datum,
    "senat": senat,
    "year": year,
    "source": "bundesfinanzhof.de",
    "url": url,
    "bstbl": str(bstbl_aufgenommen), # "false" = Verwaltung wendet nicht an
}
```

**Split-Strategie (Priorität):**
1. Abschnitte nach Überschriften (`Leitsatz`, `Tatbestand`, `Entscheidungsgründe`, `Tenor`)
2. Randnummern (`1.`, `2.` oder `Rn. 1`)
3. Fallback: ganzes Dokument

**Besonderheiten bundesfinanzhof.de:**
- HTML-Struktur ist konsistent (amtliches System), kein JavaScript-Rendering nötig
- URL-Muster: `https://www.bundesfinanzhof.de/entscheidungen/entscheidungen-online/detail/STRE{id}/`
  oder direkter Link aus dem Katalog
- `User-Agent`-Header wie bei BMF setzen (Server könnte headless blockieren)

---

### Schritt 3 — CLI-Command und Makefile

**In `ingest/cli.py`** einen neuen Command `ingest-bfh` ergänzen (analog `ingest-bmf`):

```python
@app.command(name="ingest-bfh")
def ingest_bfh(
    year: int = typer.Option(2025, help="Steuerjahr (RAG-Filter)"),
    chroma_path: str = typer.Option("chroma_db"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """BFH-Urteile herunterladen, parsen und in Chroma speichern."""
    ...
```

**In `Makefile`:**
```makefile
local.ingest-bfh: ## Download und Ingest BFH-Urteile (YEAR=2025)
    @cd backend && $(UV) run python -m ingest.cli ingest-bfh --year $(or $(YEAR),2025)
```

**In `ingest/scrapers/registry.py`:**
```python
ExternalSource(
    key="BFH",
    name="BFH-Urteile (kuratierte Auswahl, ~20 Urteile)",
    url="https://www.bundesfinanzhof.de/entscheidungen/entscheidungen-online/",
    verified_year=2025,
    update_hint=(
        "Einzelne Urteil-URLs in ingest/scrapers/bfh_catalog.py pflegen. "
        "bundesfinanzhof.de → Entscheidungen → Suche nach Az. oder Thema. "
        "BStBl-Status prüfen: wenn aufgenommen → bstbl_aufgenommen=True setzen."
    ),
)
```

---

### Schritt 4 — Unit-Tests (`test_bfh_parser.py`)

**Datei:** `backend/tests/test_bfh_parser.py`

Analog zu `test_bmf_parser.py` — alle Tests offline, kein Netzwerk:

| Testklasse | Tests |
|---|---|
| `TestSplitText` | Abschnittssplit, Leitsatz-Extraktion, Randnummern, Fallback, leer |
| `TestBuildDocuments` | Metadaten-Felder, `bstbl`-Flag, section-Label, Header-Inhalt |
| `TestParseHtml` | Nav/Footer stripped, Leitsatz gefunden, Metadaten korrekt |
| `TestBfhCatalog` | IDs eindeutig, Aktenzeichen nicht leer, Datum ISO, `get_active_urteile` filtert superseded |

Ziel: ~20 Tests.

---

### Schritt 5 — Backlog und Dokumentation aktualisieren

- `BACKLOG.md`: Unterpunkte 15.6.1–15.6.4 als `[x]` markieren
- `docs/justification.md`: Ebene-4-Abschnitt mit konkreten Urteilen aus dem Katalog vervollständigen
- `README.md`: `make local.ingest-bfh` in die Tabelle der Ingest-Befehle aufnehmen

---

## Abhängigkeiten

Keine neuen Python-Abhängigkeiten notwendig — `httpx`, `beautifulsoup4` und `pdfplumber` sind bereits im Projekt. `bfh.py` kann direkt auf die bereits vorhandenen Hilfsfunktionen aus `bmf.py` referenzieren (z.B. `_split_text` könnte in ein gemeinsames `scrapers/utils.py` extrahiert werden).

## Geschätzter Umfang

| Schritt | Aufwand |
|---|---|
| 1 — Katalog kuratieren | Recherche ~30–60 min, Code ~30 min |
| 2 — Downloader/Parser | ~2–3 h (HTML-Parsing, Split-Logik) |
| 3 — CLI + Makefile + Registry | ~30 min |
| 4 — Tests | ~1 h |
| 5 — Backlog / Docs | ~15 min |
