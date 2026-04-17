# Wissensbasis — Quellen und Begründungen

Dieses Dokument erklärt, warum welche Rechtsquellen in die RAG-Wissensbasis aufgenommen wurden, was sie inhaltlich abdecken und wo sie herkommen. Dient als schnelle Referenz bei Rückfragen.

---

## Überblick

steuerpilot-ai zieht seine Antworten aus einer mehrstufigen Hierarchie steuerrechtlicher Quellen. Die Schichten bauen aufeinander auf: Gesetz → Verordnung → Verwaltungsanweisung → Rechtsprechung.

```
Ebene 1 — Gesetze       EStG, EStDV, AO, UStG, SolzG, GewStG
Ebene 2 — Richtlinien   LStR, EStR (über EStH), LStH
Ebene 3 — Verwaltung    BMF-Schreiben (kuratierte Auswahl, ~20 Schreiben)
Ebene 4 — Rechtsprechung BFH-Urteile (geplant Phase 15.6)
```

---

## Ebene 1 — Gesetze

### EStG — Einkommensteuergesetz
- **Warum:** Das zentrale Steuergesetz für natürliche Personen. Regelt alle Einkunftsarten, Werbungskosten, Sonderausgaben, außergewöhnliche Belastungen, AfA und Steuerbefreiungen. Ohne EStG ist keine sinnvolle Antwort zur Einkommensteuer möglich.
- **Quelle:** gesetze-im-internet.de (XML-Archiv, Bundesministerium der Justiz)
- **Format:** XML → hierarchisches Chunking: Paragraf (Parent) → Absatz (Child)
- **Abdeckung:** 229 Paragrafen → 1.263 Nodes (EStG 2025)

### EStDV — Einkommensteuer-Durchführungsverordnung
- **Warum:** Konkretisiert EStG-Paragrafen wo das Gesetz delegiert. Enthält u.a. Pauschbeträge, Nachweisregelungen und Fristen, die im EStG nur abstrakt geregelt sind.
- **Quelle:** gesetze-im-internet.de (`estdv_1955/xml.zip`)

### AO — Abgabenordnung
- **Warum:** Verfahrensrecht: Fristen, Einspruch, Stundung, Erlass, Verjährung. Ohne AO fehlen Antworten auf „Kann ich noch Einspruch einlegen?" oder „Was passiert bei verspäteter Abgabe?".
- **Quelle:** gesetze-im-internet.de

### UStG — Umsatzsteuergesetz
- **Warum:** Vorsteuerabzug für Freiberufler und Unternehmer ist ein häufiges Anliegen. Auch Kleinunternehmerregelung (§ 19 UStG) wird regelmäßig gefragt.
- **Quelle:** gesetze-im-internet.de

### SolzG — Solidaritätszuschlaggesetz
- **Warum:** Für eine korrekte Gesamtsteuerbelastungsberechnung notwendig. Gilt ab 2021 nur noch für Spitzenverdiener (§ 3 SolzG).
- **Quelle:** gesetze-im-internet.de (`solzg_1995/xml.zip`)

### GewStG — Gewerbesteuergesetz
- **Warum:** Relevant für Gewerbetreibende und die Unterscheidung Freiberufler vs. Gewerbebetrieb (§ 15 EStG i.V.m. GewStG). Auch Gewerbesteueranrechnung auf ESt (§ 35 EStG).
- **Quelle:** gesetze-im-internet.de (`gewstg/xml.zip`)

---

## Ebene 2 — Richtlinien und Handbücher

### LStR — Lohnsteuer-Richtlinien
- **Warum:** Verbindliche Verwaltungsanweisung der Finanzbehörden für die Lohnsteuer. Enthält die maßgeblichen Auslegungen zu Dienstwagen, Reisekosten, Werbungskosten von Arbeitnehmern — Themen, die ca. 70 % der Nutzeranfragen ausmachen dürften.
- **Quelle:** Bundesfinanzministerium, PDF (`lohnsteuer-richtlinien-2023.pdf`, ~500 Seiten)
- **Format:** PDF → pdfplumber → Abschnittssplit
- **Besonderheit:** Erscheint nicht jährlich — die 2023er Fassung gilt bis zur nächsten Überarbeitung. URL-Prüfung daher nur anlassbezogen.
- **URL-Verwaltung:** `ingest/scrapers/registry.py` → Key `"LStR"`, `update_hint` enthält Suchpfad auf bundesfinanzministerium.de

### EStH / LStH — Amtliche Steuerhandbücher
- **Warum:** Das Einkommensteuer-Handbuch (EStH) und das Lohnsteuer-Handbuch (LStH) fassen die aktuell gültigen BMF-Schreiben und Richtlinien thematisch zusammen. Viele BMF-Schreiben sind nicht als eigenständige PDFs verfügbar, aber im jeweiligen Handbuch als HTML-Seite gepflegt.
- **Quelle:** `esth.bundesfinanzministerium.de` / `lsth.bundesfinanzministerium.de`
- **Format:** HTML → BeautifulSoup → Textsplit
- **Nutzung:** Als primäre URL-Quelle für viele BMF-Schreiben-Einträge (stabiler als direkte PDF-Links)

---

## Ebene 3 — BMF-Schreiben

### BMF-Schreiben (kuratierte Auswahl)
- **Warum:** BMF-Schreiben sind das Bindeglied zwischen Gesetz und Praxis. Sie legen fest, wie die Finanzverwaltung eine Rechtsnorm auslegt — und damit, was in der Steuererklärung anerkannt wird. Ohne BMF-Schreiben fehlen Antworten auf konkrete Fragen wie „Wie genau wird der Dienstwagen mit 0,25 % besteuert?" oder „Welche Homeoffice-Pauschale gilt ab 2023?".
- **Quelle:** bundesfinanzministerium.de (PDF) sowie EStH/LStH-Handbücher (HTML)
- **Umfang:** ~20 kuratierte Schreiben zu den häufigsten Themen (Stand 2025)
- **Katalog:** `ingest/scrapers/bmf_catalog.py` — `BmfSchreiben`-Dataclass mit Aktenzeichen, Datum, URL, `superseded`-Flag
- **Technische Besonderheit:** BMF-Website blockiert headless HTTP ohne `User-Agent`-Header. URLs für Direktdownloads veralten regelmäßig. LStH/EStH-HTML-Seiten sind stabiler.

**Abgedeckte Themen:**
| Thema | Schreiben-ID |
|---|---|
| Homeoffice / häusliches Arbeitszimmer | `arbeitszimmer_tagespauschale_2023` |
| Dienstwagen (1%-Methode, Fahrtenbuch) | `dienstwagen_lohnsteuer_2022` |
| Elektro- und Hybridfahrzeuge (0,25% / 0,5%) | `elektro_hybridfahrzeuge_2021` |
| Dienstrad / Jobrad | `jobrad_steuerbefreiung_2019` |
| Reisekosten Inland / doppelte Haushaltsführung | `reisekosten_arbeitnehmer_inland_2020` |
| Reisekosten Ausland / Verpflegungsmehraufwand | `reisekosten_ausland_2025` |
| Betriebsausgabenpauschale Freiberufler | `betriebsausgabenpauschale_freiberufler_2023` |
| Bewirtungskosten | `bewirtungskosten_2025` |
| Jobticket / Deutschlandticket | `jobticket_oepnv_2023` |
| Betriebliche Altersversorgung (bAV) | `betriebliche_altersversorgung_2021` |
| Riester / private Altersvorsorge | `riester_private_altersvorsorge_2023` |
| Photovoltaik-Steuerbefreiung | `photovoltaik_steuerbefreiung_2023` |
| Sofortabschreibung Computer / Software | `sofortabschreibung_computer_2021` |
| Sachbezüge / Gutscheine / 50-€-Freigrenze | `sachbezuege_gutscheine_2024` |
| Behinderten-Pauschbetrag (§ 33b EStG) | `behinderten_pauschbetrag_2021` |
| Entfernungspauschale / Fernpendler | `entfernungspauschale_2022` |
| Abgeltungsteuer / Verlustverrechnung | `abgeltungsteuer_einzelfragen_2025` |
| Gesundheitsförderung durch Arbeitgeber | `gesundheitsfoerderung_ag_2025` |
| Elektrofahrzeuge – Stromkosten | `elektro_stromkosten_2025` |

---

## Ebene 4 — Rechtsprechung (geplant)

### BFH-Urteile — Bundesfinanzhof (Phase 15.6)
- **Warum:** Dies ist oft der größte praktische Steuervorteil für den Mandanten. Der BFH urteilt regelmäßig zugunsten von Steuerpflichtigen — aber die Finanzverwaltung ist nicht verpflichtet, ein Urteil sofort anzuwenden. Solange das BMF kein entsprechendes Anwendungsschreiben veröffentlicht (oder das Urteil im BStBl II veröffentlicht wird), kann der Berater das Urteil im Einspruchsverfahren einsetzen, die Verwaltung es aber im Massenverfahren ignorieren. **Wer dieses Urteil kennt, hat einen Informationsvorsprung.** Ein KI-Assistent, der auf diese Urteile zugreifen kann, hat damit einen echten USP gegenüber einfachen Gesetzestextsuchsystemen.
- **Quelle:** bundesfinanzhof.de (Entscheidungssuche), ECLI-Format, HTML-Volltext
- **Format:** HTML → strukturierter Split nach Leitsatz / Tatbestand / Entscheidungsgründe
- **Metadaten:** Aktenzeichen (z.B. `IX R 12/21`), ECLI, Datum, Senat, Thema, Veröffentlichungsstatus (BStBl-Aufnahme ja/nein)
- **Status:** Geplant (Backlog Phase 15.6) — Katalog + Scraper analog zu BMF-Schreiben

---

## Wartung und URL-Prüfung

Alle externen Quellen mit jährlichem Änderungsrisiko sind in `ingest/scrapers/registry.py` registriert. Der CLI-Befehl `make check-sources` führt HTTP-HEAD-Checks durch und gibt Exit-Code 1 bei Fehlern zurück — geeignet für CI/CD-Workflows.

Geplant: automatischer GitHub Actions Cron-Job (wöchentlich), der bei toten URLs eine GitHub Issue anlegt.
