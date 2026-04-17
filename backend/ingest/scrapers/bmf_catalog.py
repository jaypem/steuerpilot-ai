"""
Kuratierter Katalog relevanter BMF-Schreiben für die Einkommensteuer.

Jedes Schreiben ist ein BMF-Anwendungsschreiben (Verwaltungsanweisung),
das die Gesetzeslage für Arbeitnehmer, Freiberufler oder Selbstständige
konkretisiert.

HINWEISE:
- url: Direkt-URL zum PDF auf bundesfinanzministerium.de  (wo verfügbar)
  oder HTML-Fassung aus dem amtlichen LStH/EStH-Handbuch.
  Nicht alle URLs wurden maschinell verifiziert — fehlgeschlagene Downloads
  werden beim Ingest übersprungen (Warnung im Log).
- aktenzeichen: Aus Primär- oder verifizierten Sekundärquellen (Haufe, NWB).
  Bei mit (*) markierten Einträgen empfiehlt sich manuelle Überprüfung.
- superseded=True: Schreiben wurde durch ein neueres ersetzt; wird nicht ingestiert.
- valid_from_year: Frühestes Steuerjahr, für das das Schreiben gilt (RAG-Filter).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BmfSchreiben:
    """Ein kuratierter BMF-Schreiben-Eintrag."""

    id: str                  # Interner Bezeichner (snake_case, URL-sicher)
    aktenzeichen: str        # Aktenzeichen des BMF (z.B. "IV C 6 - S 2145/19/10006:027")
    datum: str               # Veröffentlichungsdatum ISO (YYYY-MM-DD)
    betreff: str             # Vollständiger Titel / Betreff
    url: str                 # Direkt-URL zum PDF oder HTML-Volltext
    valid_from_year: int     # Ab welchem Steuerjahr gültig
    thema: str               # Kurzbezeichnung des Themas
    superseded: bool = False  # True = durch neueres Schreiben ersetzt
    url_verified: bool = True  # False = URL aus Sekundärquelle, nicht manuell geprüft


# ─── Katalog ──────────────────────────────────────────────────────────────────

BMF_SCHREIBEN: list[BmfSchreiben] = [

    # ── 1. HOMEOFFICE / HÄUSLICHES ARBEITSZIMMER ─────────────────────────────
    BmfSchreiben(
        id="arbeitszimmer_tagespauschale_2023",
        aktenzeichen="IV C 6 - S 2145/19/10006:027",
        datum="2023-08-15",
        betreff=(
            "Ertragsteuerliche Beurteilung der betrieblichen und beruflichen "
            "Betätigung in der häuslichen Wohnung nach § 4 Abs. 5 Satz 1 Nr. 6b "
            "und 6c, § 9 Abs. 5 Satz 1 und § 10 Abs. 1 Nr. 7 Satz 4 EStG; "
            "Neuregelung durch das Jahressteuergesetz 2022 (JStG 2022)"
        ),
        url="https://lsth.bundesfinanzministerium.de/lsth/2025/B-Anhaenge/Anhang-19/I/inhalt.html",
        valid_from_year=2023,
        thema="Homeoffice / häusliches Arbeitszimmer",
        url_verified=True,
    ),

    # ── 2. DIENSTWAGEN / PKW-NUTZUNG ─────────────────────────────────────────
    BmfSchreiben(
        id="dienstwagen_lohnsteuer_2022",
        aktenzeichen="IV C 5 - S 2334/21/10004:001",
        datum="2022-03-03",
        betreff=(
            "Lohnsteuerliche Behandlung der Überlassung eines betrieblichen "
            "Kraftfahrzeugs an Arbeitnehmer"
        ),
        url="https://lsth.bundesfinanzministerium.de/lsth/2025/B-Anhaenge/Anhang-24/IV/IV-1/inhalt.html",
        valid_from_year=2022,
        thema="Dienstwagen / PKW-Nutzung (1%-Regel, Fahrtenbuch)",
        url_verified=True,
    ),

    # ── 3. ELEKTRO- UND HYBRIDFAHRZEUGE ──────────────────────────────────────
    BmfSchreiben(
        id="elektro_hybridfahrzeuge_2021",
        aktenzeichen="IV C 6 - S 2177/19/10004:008",
        datum="2021-11-05",
        betreff=(
            "Nutzung eines betrieblichen Kraftfahrzeugs für private Fahrten, "
            "Fahrten zwischen Wohnung und Betriebsstätte/erster Tätigkeitsstätte "
            "und Familienheimfahrten; Nutzung von Elektro- und Hybridelektrofahrzeugen"
        ),
        url="https://lsth.bundesfinanzministerium.de/lsth/2025/B-Anhaenge/Anhang-24/IV/IV-6/inhalt.html",
        valid_from_year=2019,
        thema="Elektrofahrzeuge / Hybridfahrzeuge (0,25%- und 0,5%-Regel)",
        url_verified=True,
    ),

    # ── 4. ELEKTROFAHRZEUGE: SELBST GETRAGENE STROMKOSTEN ────────────────────
    BmfSchreiben(
        id="elektro_stromkosten_2025",
        aktenzeichen="IV C 5 - S 2334/00087/014/013",
        datum="2025-11-11",
        betreff=(
            "Steuerbefreiung nach § 3 Nummer 46 EStG und Pauschalierung der "
            "Lohnsteuer nach § 40 Absatz 2 Satz 1 Nummer 6 EStG; "
            "Steuerliche Behandlung der vom Arbeitnehmer selbst getragenen Stromkosten"
        ),
        url=(
            "https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/"
            "Steuerarten/Lohnsteuer/"
            "2025-11-11-selbst-getragenen-stromkosten.pdf?__blob=publicationFile&v=3"
        ),
        valid_from_year=2026,
        thema="Elektrofahrzeuge – Stromkosten / Ladeinfrastruktur",
        url_verified=False,
    ),

    # ── 5. DIENSTRAD / JOBRAD ─────────────────────────────────────────────────
    BmfSchreiben(
        id="jobrad_steuerbefreiung_2019",
        aktenzeichen="IV C 5 - S 2378/19/10002:001",
        datum="2019-09-09",
        betreff=(
            "Steuerbefreiung nach § 3 Nummer 37 EStG; "
            "Steuerliche Behandlung der Überlassung von (Elektro-)Fahrrädern"
        ),
        url=(
            "https://lsth.bundesfinanzministerium.de/lsth/2025/B-Anhaenge/Anhang-24/IV/IV-4/anhang-24-IV-4.html"
        ),
        valid_from_year=2019,
        thema="Dienstrad / Jobrad (§ 3 Nr. 37 EStG)",
        url_verified=True,
    ),

    # ── 6. REISEKOSTEN INLAND / DOPPELTE HAUSHALTSFÜHRUNG ────────────────────
    BmfSchreiben(
        id="reisekosten_arbeitnehmer_inland_2020",
        aktenzeichen="IV C 5 - S 2353/19/10011:006",
        datum="2020-11-25",
        betreff=(
            "Steuerliche Behandlung der Reisekosten von Arbeitnehmern "
            "(inkl. doppelter Haushaltsführung, erste Tätigkeitsstätte, "
            "Mahlzeitengestellung)"
        ),
        url=(
            "https://lsth.bundesfinanzministerium.de/lsth/2025/B-Anhaenge/Anhang-25/III/anhang-25-III.html"
        ),
        valid_from_year=2020,
        thema="Reisekosten Inland / doppelte Haushaltsführung / erste Tätigkeitsstätte",
        url_verified=True,
    ),

    # ── 7. REISEKOSTEN AUSLAND (PAUSCHBETRÄGE AB 2025) ───────────────────────
    BmfSchreiben(
        id="reisekosten_ausland_2025",
        aktenzeichen="IV C 5 - S 2353/19/10010:006",
        datum="2024-12-02",
        betreff=(
            "Steuerliche Behandlung von Reisekosten und Reisekostenvergütungen "
            "bei betrieblich und beruflich veranlassten Auslandsreisen "
            "ab 1. Januar 2025"
        ),
        url=(
            "https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/"
            "Steuerarten/Lohnsteuer/"
            "2024-12-02-steuerliche-behandlung-reisekosten-2025.pdf"
            "?__blob=publicationFile&v=15"
        ),
        valid_from_year=2025,
        thema="Reisekosten Ausland / Verpflegungsmehraufwand Ausland",
    ),

    # ── 8. BETRIEBSAUSGABENPAUSCHALE FREIBERUFLER ─────────────────────────────
    BmfSchreiben(
        id="betriebsausgabenpauschale_freiberufler_2023",
        aktenzeichen="IV C 6 - S 2246/20/10002:001",
        datum="2023-04-06",
        betreff=(
            "Betriebsausgabenpauschale bei der Ermittlung der Einkünfte aus "
            "hauptberuflicher selbständiger schriftstellerischer oder "
            "journalistischer Tätigkeit, aus wissenschaftlicher, künstlerischer "
            "und schriftstellerischer Nebentätigkeit sowie aus nebenamtlicher "
            "Lehr- und Prüfungstätigkeit (H 18.2 EStH)"
        ),
        url=(
            "https://esth.bundesfinanzministerium.de/esth/2024/A-Einkommensteuergesetz/"
            "II-Einkommen-2-24b/8-Die-einzelnen-Einkunftsarten-13-24b/c-Selbstaendige-Arbeit-18/"
            "Paragraf-18/h-18-2.html"
        ),
        valid_from_year=2023,
        thema="Betriebsausgaben Freiberufler / Pauschale",
        url_verified=True,
    ),

    # ── 9. BEWIRTUNGSKOSTEN ALS BETRIEBSAUSGABEN ─────────────────────────────
    BmfSchreiben(
        id="bewirtungskosten_2025",
        aktenzeichen="IV C 6 - S 2056/00/10001:001",
        datum="2025-11-19",
        betreff=(
            "Steuerliche Anerkennung von Aufwendungen für die Bewirtung von "
            "Personen aus geschäftlichem Anlass in einem Bewirtungsbetrieb "
            "als Betriebsausgaben"
        ),
        url=(
            "https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/"
            "Steuerarten/Einkommensteuer/"
            "2025-11-19-bewirtungskosten-als-betriebsausgaben.pdf"
            "?__blob=publicationFile&v=4"
        ),
        valid_from_year=2025,
        thema="Bewirtungskosten / Betriebsausgaben (§ 4 Abs. 5 Nr. 2 EStG)",
        url_verified=False,
    ),

    # ── 10. JOBTICKET / DEUTSCHLANDTICKET (§ 3 NR. 15 ESTG) ─────────────────
    BmfSchreiben(
        id="jobticket_oepnv_2023",
        aktenzeichen="IV C 5 - S 2342/19/10007:009",
        datum="2023-11-07",
        betreff=(
            "Steuerbefreiung nach § 3 Nummer 15 EStG; "
            "Steuerfreiheit von Arbeitgeberleistungen für Fahrten mit öffentlichen "
            "Verkehrsmitteln (Jobticket, Deutschlandticket)"
        ),
        url=(
            "https://lsth.bundesfinanzministerium.de/lsth/2025/B-Anhaenge/Anhang-17a/anhang-17a.html"
        ),
        valid_from_year=2019,
        thema="Steuerfreie Arbeitgeberleistungen / Jobticket / Deutschlandticket",
        url_verified=True,
    ),

    # ── 11. BETRIEBLICHE ALTERSVERSORGUNG (§ 3 NR. 63 ESTG) ─────────────────
    BmfSchreiben(
        id="betriebliche_altersversorgung_2021",
        aktenzeichen="IV C 5 - S 2333/19/10008:017",
        datum="2021-08-12",
        betreff="Steuerliche Förderung der betrieblichen Altersversorgung",
        url="https://lsth.bundesfinanzministerium.de/lsth/2025/B-Anhaenge/Anhang-02/III/inhalt.html",
        valid_from_year=2021,
        thema="Betriebliche Altersvorsorge / bAV (§ 3 Nr. 63 EStG)",
        url_verified=True,
    ),

    # ── 12. RIESTER-RENTE / PRIVATE ALTERSVORSORGE (§ 10A ESTG) ─────────────
    BmfSchreiben(
        id="riester_private_altersvorsorge_2023",
        aktenzeichen="IV C 3 - S 2015/22/10001:001",
        datum="2023-10-05",
        betreff=(
            "Steuerliche Förderung der privaten Altersvorsorge "
            "(§ 10a EStG, Abschnitte XI EStG)"
        ),
        url="https://esth.bundesfinanzministerium.de/esth/2024/C-Anhaenge/Anhang-01a/I/inhalt.html",
        valid_from_year=2023,
        thema="Riester-Rente / private Altersvorsorge (§ 10a EStG)",
        url_verified=True,
    ),

    # ── 13. PHOTOVOLTAIK – STEUERBEFREIUNG (§ 3 NR. 72 ESTG) ────────────────
    BmfSchreiben(
        id="photovoltaik_steuerbefreiung_2023",
        aktenzeichen="IV C 6 - S 2121/23/10001:001",
        datum="2023-07-17",
        betreff="Steuerbefreiung für Photovoltaikanlagen (§ 3 Nummer 72 EStG)",
        url=(
            "https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/"
            "Steuerarten/Einkommensteuer/"
            "2023-07-17-Photovoltaikanlagen-Steuerbefreiung.pdf"
            "?__blob=publicationFile&v=2"
        ),
        valid_from_year=2022,
        thema="Photovoltaik / Steuerbefreiung (§ 3 Nr. 72 EStG)",
        url_verified=False,  # Aktenzeichen aus Sekundärquelle
    ),

    # ── 14. SOFORTABSCHREIBUNG COMPUTER / SOFTWARE ───────────────────────────
    # Nachfolge-Schreiben vom 22.02.2022 (Az. IV C 3 - S 2190/21/10002:025) ist
    # die gültige Fassung im EStH 2024 (Anhang 1 V.) — Originalschreiben 26.02.2021
    # wurde damit ersetzt; Inhalt identisch.
    BmfSchreiben(
        id="sofortabschreibung_computer_2021",
        aktenzeichen="IV C 3 - S 2190/21/10002:025",
        datum="2022-02-22",
        betreff=(
            "Sofortabschreibung für Computerhardware und Software "
            "zur Dateneingabe und -verarbeitung; Nutzungsdauer von 1 Jahr "
            "(§ 7 Abs. 1 EStG)"
        ),
        url="https://esth.bundesfinanzministerium.de/esth/2024/C-Anhaenge/Anhang-01/V/inhalt.html",
        valid_from_year=2021,
        thema="Arbeitsmittel / Sofortabschreibung Computer und Software",
        url_verified=True,
    ),

    # ── 15. SACHBEZÜGE / GUTSCHEINE / 50-€-FREIGRENZE ───────────────────────
    # Korrektur: Az. IV C 5 - S 2334/19/10007:007 (15.03.2022) ist das gültige
    # Gutscheine/Geldkarten-Schreiben. Das ursprüngliche Az. /10010:006 vom
    # 10.12.2024 betrifft Mahlzeiten-Sachbezugswerte 2025 (anderes Thema).
    BmfSchreiben(
        id="sachbezuege_gutscheine_2024",
        aktenzeichen="IV C 5 - S 2334/19/10007:007",
        datum="2022-03-15",
        betreff=(
            "Steuerliche Behandlung von Gutscheinen und Geldkarten "
            "als Sachbezug (§ 8 Abs. 1 Satz 2 und 3 EStG); "
            "50-Euro-Freigrenze"
        ),
        url="https://lsth.bundesfinanzministerium.de/lsth/2025/B-Anhaenge/Anhang-24/VII/inhalt.html",
        valid_from_year=2022,
        thema="Steuerfreie Sachbezüge / Gutscheine / 50-€-Freigrenze (§ 8 EStG)",
        url_verified=True,
    ),

    # ── 16. AUSSERGEWÖHNLICHE BELASTUNGEN / BEHINDERTEN-PAUSCHBETRAG ─────────
    BmfSchreiben(
        id="behinderten_pauschbetrag_2021",
        aktenzeichen="IV C 8 - S 2286/20/10001:001",
        datum="2021-03-16",
        betreff=(
            "Außergewöhnliche Belastungen; "
            "Pauschbeträge für Menschen mit Behinderungen, Hinterbliebene "
            "und Pflegepersonen (§ 33b EStG); Anhebung ab VZ 2021"
        ),
        url="https://esth.bundesfinanzministerium.de/esth/2024/A-Einkommensteuergesetz/IV-Tarif-31-34b/Paragraf-33b/h-33b.html",
        valid_from_year=2021,
        thema="Außergewöhnliche Belastungen / Behinderten-Pauschbetrag (§ 33b EStG)",
        url_verified=True,
    ),

    # ── 17. ENTFERNUNGSPAUSCHALE / FERNPENDLER ───────────────────────────────
    # Korrektur: Az. IV C 5 - S 2351/20/10001:002 gehört zum Schreiben vom
    # 18.11.2021 (BStBl I S. 2315), nicht 18.10.2022 wie ursprünglich angegeben.
    BmfSchreiben(
        id="entfernungspauschale_2022",
        aktenzeichen="IV C 5 - S 2351/20/10001:002",
        datum="2021-11-18",
        betreff=(
            "Erhöhte Entfernungspauschale für Fernpendler; "
            "steuerliche Behandlung ab 2022 nach dem "
            "Klimaschutzprogramm 2030 (§ 9 Abs. 1 Satz 3 Nr. 4 EStG)"
        ),
        url="https://lsth.bundesfinanzministerium.de/lsth/2025/B-Anhaenge/Anhang-14/inhalt.html",
        valid_from_year=2022,
        thema="Entfernungspauschale / Pendler (§ 9 Abs. 1 Nr. 4 EStG)",
        url_verified=True,
    ),

    # ── 18. VERLUSTVERRECHNUNG / KAPITALVERMÖGEN (§ 20 ABS. 6 ESTG) ─────────
    # Superseded by 2025-05-14 version (confirmed working PDF)
    BmfSchreiben(
        id="verlustverrechnung_kapitalvermoegen_2022",
        aktenzeichen="IV C 1 - S 2252/19/10003:009",
        datum="2022-05-19",
        betreff=(
            "Einzelfragen zur Abgeltungsteuer; "
            "Verlustverrechnungsbeschränkungen bei Kapitaleinkünften "
            "(§ 20 Abs. 6 EStG)"
        ),
        url=(
            "https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/"
            "Steuerarten/Einkommensteuer/"
            "2022-05-19-einzelfragen-abgeltungsteuer.pdf?__blob=publicationFile&v=2"
        ),
        valid_from_year=2022,
        thema="Verlustverrechnung / Abgeltungsteuer / Kapitalvermögen",
        url_verified=False,
        superseded=True,
    ),

    # ── 18b. VERLUSTVERRECHNUNG / ABGELTUNGSTEUER (AKTUELL 2025) ────────────
    BmfSchreiben(
        id="abgeltungsteuer_einzelfragen_2025",
        aktenzeichen="IV C 1 - S 2252/19/10003:009",  # Aktenzeichen ggf. aktualisiert
        datum="2025-05-14",
        betreff=(
            "Einzelfragen zur Abgeltungsteuer; "
            "Verlustverrechnungsbeschränkungen bei Kapitaleinkünften "
            "(§ 20 Abs. 6 EStG) — Fassung 2025"
        ),
        url=(
            "https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/"
            "Steuerarten/Abgeltungsteuer/"
            "2025-05-14-einzelfragen-zur-abgeltungsteuer.pdf?__blob=publicationFile&v=4"
        ),
        valid_from_year=2022,
        thema="Verlustverrechnung / Abgeltungsteuer / Kapitalvermögen",
        url_verified=True,
    ),

    # ── 19. RIESTER ZULAGENVERFAHREN / DAUERHAFTER ZULAGENANTRAG ─────────────
    # Superseded by riester_private_altersvorsorge_2023 (2023-10-05)
    BmfSchreiben(
        id="riester_zulagenverfahren_2018",
        aktenzeichen="IV C 3 - S 2015/18/10001",
        datum="2018-11-15",
        betreff=(
            "Steuerliche Förderung der privaten Altersvorsorge; "
            "dauerhafter Zulagenantrag, Änderungen durch das BMAS-Gesetz 2018"
        ),
        url=(
            "https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/"
            "Steuerarten/Einkommensteuer/"
            "2018-11-15-riester-zulagenverfahren.pdf?__blob=publicationFile&v=1"
        ),
        valid_from_year=2018,
        thema="Riester-Rente / Zulagenverfahren",
        url_verified=False,
        superseded=True,
    ),

    # ── 20. STEUERFREIE ARBEITGEBERZUSCHÜSSE GESUNDHEITSFÖRDERUNG ────────────
    # Korrektur: Schreiben vom 14.01.2025 nicht auffindbar (evtl. fehlerhafte Metadaten).
    # Im LStH 2025 (Anhang 18c) ist das Schreiben vom 20.04.2021
    # (Az. IV C 5 - S 2342/20/10003:003, BStBl I S. 700) hinterlegt.
    BmfSchreiben(
        id="gesundheitsfoerderung_ag_2025",
        aktenzeichen="IV C 5 - S 2342/20/10003:003",
        datum="2021-04-20",
        betreff=(
            "Steuerbefreiung nach § 3 Nummer 34 EStG; "
            "Leistungen des Arbeitgebers zur Verbesserung des allgemeinen "
            "Gesundheitszustands und der betrieblichen Gesundheitsförderung"
        ),
        url="https://lsth.bundesfinanzministerium.de/lsth/2025/B-Anhaenge/Anhang-18c/inhalt.html",
        valid_from_year=2021,
        thema="Steuerfreie Arbeitgeberleistungen / Gesundheitsförderung (§ 3 Nr. 34 EStG)",
        url_verified=True,
    ),
]


# ─── Zugriffs-Hilfsfunktionen ─────────────────────────────────────────────────

def get_active_schreiben(year: int) -> list[BmfSchreiben]:
    """Gibt alle nicht-superseded Schreiben zurück, die für *year* gültig sind."""
    return [
        s for s in BMF_SCHREIBEN
        if not s.superseded and s.valid_from_year <= year
    ]


def get_by_id(schreiben_id: str) -> BmfSchreiben:
    for s in BMF_SCHREIBEN:
        if s.id == schreiben_id:
            return s
    raise KeyError(f"BMF-Schreiben '{schreiben_id}' nicht im Katalog.")
