"""
Kuratierter Katalog günstiger BFH-Urteile für die Einkommensteuer.

Aufnahmekriterien:
  1. Für Steuerpflichtige günstig (Abzug anerkannt, Besteuerung verneint o.ä.)
  2. Noch nicht von der Finanzverwaltung vollständig übernommen:
       - NICHT im BStBl II veröffentlicht  ODER
       - BMF hat Nichtanwendungserlass herausgegeben
  3. Praktisch relevant für Arbeitnehmer, Freiberufler oder Privatpersonen
  4. Aus dem Zeitraum 2017–2025

HINWEISE:
- bstbl_aufgenommen=True: Verwaltung wendet das Urteil an — immer noch nützlich
  als Kontext, aber kein Informationsvorsprung mehr.
- nichtanwendungserlass=True: BMF hat die Anwendung explizit abgelehnt —
  Urteil ist trotzdem im Einspruchsverfahren verwendbar.
- superseded=True: Neueres BFH-Urteil oder Gesetzesänderung macht dieses
  Urteil obsolet.
- valid_from_year: Frühestes Veranlagungsjahr, für das das Urteil relevant ist.
- URL-Format: https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE.../
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BfhUrteil:
    """Ein kuratierter BFH-Urteil-Eintrag."""

    id: str                    # Interner Bezeichner (snake_case, URL-sicher)
    aktenzeichen: str          # Amtliches Az., z.B. "VI R 15/20"
    datum: str                 # Entscheidungsdatum ISO (YYYY-MM-DD)
    senat: str                 # Zuständiger Senat, z.B. "VI. Senat"
    betreff: str               # Kurzbeschreibung des Entscheidungsinhalts
    url: str                   # Direkt-URL auf bundesfinanzhof.de
    thema: str                 # Kurzbezeichnung des Steuer-Themas
    valid_from_year: int       # Ab welchem Veranlagungszeitraum relevant
    ecli: str = ""             # ECLI, z.B. "ECLI:DE:BFH:2022:U.120522.VIR32.20.0"
    bstbl_aufgenommen: bool = False    # True = Verwaltung wendet Urteil an
    nichtanwendungserlass: bool = False  # True = BMF hat explizit abgelehnt
    superseded: bool = False   # True = durch neueres Urteil/Gesetz überholt
    url_verified: bool = True  # False = URL aus Sekundärquelle, nicht direkt geprüft


# ─── Katalog ──────────────────────────────────────────────────────────────────

BFH_URTEILE: list[BfhUrteil] = [

    # ── 1. ERSTE TÄTIGKEITSSTÄTTE — LEIHARBEITNEHMER ─────────────────────────
    BfhUrteil(
        id="leiharbeit_erste_taetigkeitsstaette_2022",
        aktenzeichen="VI R 32/20",
        ecli="ECLI:DE:BFH:2022:U.120522.VIR32.20.0",
        datum="2022-05-12",
        senat="VI. Senat",
        betreff=(
            "Bei befristeter Arbeitnehmerüberlassung liegt beim Entleiher keine "
            "erste Tätigkeitsstätte vor — Fahrtkosten nach günstigeren "
            "Reisekostengrundsätzen absetzbar (doppelter Kilometersatz + "
            "Verpflegungspauschale statt nur Entfernungspauschale)"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202210183/",
        thema="Erste Tätigkeitsstätte / Reisekosten Leiharbeit (§ 9 Abs. 4 EStG)",
        valid_from_year=2014,
        bstbl_aufgenommen=True,
    ),

    # ── 2. ERSTE TÄTIGKEITSSTÄTTE — AUSSENDIENSTLER (MÜLLWERKER) ─────────────
    BfhUrteil(
        id="aussendienst_keine_erste_taetigkeitsstaette_2021",
        aktenzeichen="VI R 25/19",
        ecli="ECLI:DE:BFH:2021:U.020921.VIR25.19.0",
        datum="2021-09-02",
        senat="VI. Senat",
        betreff=(
            "Betriebshof eines Entsorgers ist keine erste Tätigkeitsstätte eines "
            "Müllwerkers, wenn dessen Kerntätigkeit ausschließlich unterwegs stattfindet "
            "— Reisekostengrundsätze gelten für alle Fahrten zum Betriebshof"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202150193/",
        thema="Erste Tätigkeitsstätte / Außendienst / Reisekosten (§ 9 Abs. 4 EStG)",
        valid_from_year=2014,
        bstbl_aufgenommen=False,
    ),

    # ── 3. VERLUSTE AKTIENVERÄUSSERUNGEN — VERFASSUNGSWIDRIGKEIT ─────────────
    BfhUrteil(
        id="aktienverl_verfassungswidrig_vorlage_2020",
        aktenzeichen="VIII R 11/18",
        ecli="ECLI:DE:BFH:2020:B.171120.VIIIR11.18.0",
        datum="2020-11-17",
        senat="VIII. Senat",
        betreff=(
            "BFH legt BVerfG vor: Beschränkung, Aktienverluste nur mit "
            "Aktiengewinnen zu verrechnen (§ 20 Abs. 6 S. 4 EStG), verstößt "
            "möglicherweise gegen Art. 3 Abs. 1 GG — vorläufige Festsetzungen "
            "nach § 165 AO laufen (BVerfG Az. 2 BvL 3/21)"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202110103/",
        thema="Verluste Aktienveräußerungen / Verfassungswidrigkeit (§ 20 Abs. 6 S. 4 EStG)",
        valid_from_year=2009,
        bstbl_aufgenommen=True,
    ),

    # ── 4. VERLUSTE TERMINGESCHÄFTE — VERFASSUNGSWIDRIGKEIT (AdV) ────────────
    BfhUrteil(
        id="termingeschaefte_verlust_adv_2024",
        aktenzeichen="VIII B 113/23",
        ecli="ECLI:DE:BFH:2024:B.070624.VIIIB113.23.0",
        datum="2024-06-07",
        senat="VIII. Senat",
        betreff=(
            "Jahresdeckel 20.000 € für Termingeschäftsverluste (§ 20 Abs. 6 S. 5 "
            "EStG i.d.F. JStG 2020) mit hoher Wahrscheinlichkeit verfassungswidrig "
            "— AdV ist zu gewähren; JStG 2024 strich die Norm rückwirkend für "
            "alle offenen Fälle 2021–2023"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202410113/",
        thema="Verluste Termingeschäfte / Verfassungswidrigkeit (§ 20 Abs. 6 S. 5 EStG)",
        valid_from_year=2021,
        bstbl_aufgenommen=False,
    ),

    # ── 5. HÄUSLICHES ARBEITSZIMMER — KEIN ERFORDERLICHKEITSGEBOT ────────────
    BfhUrteil(
        id="arbeitszimmer_kein_erforderlichkeitsgebot_2019",
        aktenzeichen="VI R 46/17",
        ecli="ECLI:DE:BFH:2019:U.030419.VIR46.17.0",
        datum="2019-04-03",
        senat="VI. Senat",
        betreff=(
            "Häusliches Arbeitszimmer muss für die Tätigkeit nicht objektiv "
            "erforderlich sein — ausschließliche berufliche Nutzung genügt "
            "für den Abzug bis 1.250 € bei fehlendem anderen Arbeitsplatz; "
            "gilt z.B. für Außendienstler mit Vor-/Nachbereitungsarbeiten"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202210048/",
        thema="Homeoffice / häusliches Arbeitszimmer / Erforderlichkeit (§ 4 Abs. 5 Nr. 6b EStG)",
        valid_from_year=2019,
        bstbl_aufgenommen=False,
    ),

    # ── 6. HÄUSLICHES ARBEITSZIMMER — KEIN ANDERER ARBEITSPLATZ ──────────────
    BfhUrteil(
        id="arbeitszimmer_kein_anderer_arbeitsplatz_2023",
        aktenzeichen="VI R 4/21",
        ecli="ECLI:DE:BFH:2023:U.150223.VIR4.21.0",
        datum="2023-02-15",
        senat="VI. Senat",
        betreff=(
            "Steht dem Arbeitnehmer für die konkrete Tätigkeit kein anderer "
            "Arbeitsplatz zur Verfügung, sind Arbeitszimmerkosten bis 1.250 € "
            "absetzbar — selbst wenn für andere Tätigkeiten ein Büro vorhanden "
            "ist (z.B. Lehrer, Teilzeitkräfte, Außendienstler)"
        ),
        url="https://www.bundesfinanzhof.de/de/entscheidung/entscheidungen-online/detail/STRE202310116/",
        thema="Homeoffice / kein anderer Arbeitsplatz (§ 4 Abs. 5 Nr. 6b EStG)",
        valid_from_year=2020,
        bstbl_aufgenommen=True,
    ),

    # ── 7. DOPPELTE HAUSHALTSFÜHRUNG — EINRICHTUNGSKOSTEN ────────────────────
    BfhUrteil(
        id="doppelte_hf_einrichtungskosten_2019",
        aktenzeichen="VI R 18/17",
        ecli="ECLI:DE:BFH:2019:U.040419.VIR18.17.0",
        datum="2019-04-04",
        senat="VI. Senat",
        betreff=(
            "Möbel und Hausrat im Rahmen einer doppelten Haushaltsführung fallen "
            "nicht unter die 1.000-€-Unterkunftskostengrenze, sondern sind daneben "
            "als notwendige Mehraufwendungen in voller Höhe abziehbar"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE201910106/",
        thema="Doppelte Haushaltsführung / Einrichtungskosten / 1.000-€-Grenze (§ 9 Abs. 1 Nr. 5 EStG)",
        valid_from_year=2014,
        bstbl_aufgenommen=True,
    ),

    # ── 8. DOPPELTE HAUSHALTSFÜHRUNG — EIGENER HAUSSTAND BEI LEDIGEN ─────────
    BfhUrteil(
        id="doppelte_hf_eigener_hausstand_ledige_2023",
        aktenzeichen="VI R 39/19",
        ecli="ECLI:DE:BFH:2023:U.120123.VIR39.19.0",
        datum="2023-01-12",
        senat="VI. Senat",
        betreff=(
            "Für eigenen Hausstand bei Ledigen in Mehrgenerationen-Haushalt reicht "
            "auch eine einmalige Jahreszahlung als finanzielle Beteiligung — "
            "kein Erfordernis monatlich laufender Beiträge; "
            "anerkennt doppelte Haushaltsführung auch bei Wohnen bei den Eltern"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202310088/",
        thema="Doppelte Haushaltsführung / eigener Hausstand Ledige (§ 9 Abs. 1 Nr. 5 EStG)",
        valid_from_year=2014,
        bstbl_aufgenommen=True,
    ),

    # ── 9. DOPPELTE HAUSHALTSFÜHRUNG — EIN-PERSONEN-HAUSHALT ─────────────────
    BfhUrteil(
        id="doppelte_hf_einpersonenhaushalt_2025",
        aktenzeichen="VI R 12/23",
        datum="2025-04-29",
        senat="VI. Senat",
        betreff=(
            "Bei Ein-Personen-Haushalt ist das Kriterium der finanziellen "
            "Beteiligung an den Haushaltskosten per Definition erfüllt, wenn der "
            "Steuerpflichtige allein lebt und alle Kosten selbst trägt — "
            "keine Mindestbeteiligungshöhe vorgeschrieben"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202550207/",
        thema="Doppelte Haushaltsführung / eigener Hausstand Alleinstehende (§ 9 Abs. 1 Nr. 5 EStG)",
        valid_from_year=2025,
        bstbl_aufgenommen=False,
        url_verified=False,
    ),

    # ── 10. § 35A ESTG — HAUSHALTSNAHE DIENSTE FÜR MIETER (NEBENKOSTENABR.) ──
    BfhUrteil(
        id="haushaltsnahe_dienste_mieter_nebenkostenabr_2023",
        aktenzeichen="VI R 24/20",
        ecli="ECLI:DE:BFH:2023:U.200423.VIR24.20.0",
        datum="2023-04-20",
        senat="VI. Senat",
        betreff=(
            "Mieter können § 35a-Steuerermäßigung für haushaltsnahe Dienste auch "
            "geltend machen, wenn Vertrag über Vermieter/WEG abgeschlossen wurde "
            "— Nebenkostenabrechnung oder Bescheinigung des Vermieters genügt als "
            "Nachweis"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202310138/",
        thema="Haushaltsnahe Dienstleistungen / Mieter / Nebenkostenabrechnung (§ 35a EStG)",
        valid_from_year=2023,
        bstbl_aufgenommen=True,
    ),

    # ── 11. § 35A ESTG — HANDWERKERLEISTUNGEN FÜR MIETER ────────────────────
    BfhUrteil(
        id="handwerkerleistungen_mieter_bescheinigung_2023",
        aktenzeichen="VI R 8/21",
        ecli="ECLI:DE:BFH:2023:U.230323.VIR8.21.0",
        datum="2023-03-23",
        senat="VI. Senat",
        betreff=(
            "Mieter können Handwerkerleistungen nach § 35a EStG steuerlich "
            "geltend machen, auch wenn der Vermieter oder die Hausverwaltung "
            "beauftragt hat — Bescheinigung des Vermieters genügt als Nachweis "
            "(bis zu 1.200 € Steuerermäßigung)"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202350083/",
        thema="Handwerkerleistungen / Mieter / Steuerermäßigung (§ 35a EStG)",
        valid_from_year=2023,
        bstbl_aufgenommen=True,
    ),

    # ── 12. GEHALTSUMWANDLUNG — ZUSÄTZLICHKEITSERFORDERNIS ───────────────────
    # NAE BMF v. 05.02.2020 für VZ ab 2020 (gesetzliche Neuregelung § 8 Abs. 4 EStG);
    # für VZ bis 2019 aufgehoben durch BMF v. 05.01.2022.
    BfhUrteil(
        id="gehaltsumwandlung_zusaetzlichkeit_bis_2019",
        aktenzeichen="VI R 32/18",
        ecli="ECLI:DE:BFH:2019:U.010819.VIR32.18.0",
        datum="2019-08-01",
        senat="VI. Senat",
        betreff=(
            "Arbeitsrechtlich wirksame Gehaltsumwandlung ist unschädlich für die "
            "Steuerfreiheit von Arbeitgeberleistungen (z.B. Fahrtkostenzuschuss, "
            "Kindergartenzuschuss) für VZ bis 2019 — Nichtanwendungserlass für "
            "Altjahre wurde 2022 aufgehoben; Einsprüche für VZ bis 2019 lohnen sich"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE201910218/",
        thema="Steuerfreie Arbeitgeberleistungen / Gehaltsumwandlung (§ 3 EStG, VZ bis 2019)",
        valid_from_year=2018,
        bstbl_aufgenommen=False,
        nichtanwendungserlass=False,  # NAE für Altjahre 2022 aufgehoben
    ),

    # ── 13. EIGENNUTZUNG IMMOBILIEN — SPEKULATIONSFRIST ──────────────────────
    BfhUrteil(
        id="immobilien_eigennutzung_spekulationsfrist_2019",
        aktenzeichen="IX R 10/19",
        ecli="ECLI:DE:BFH:2019:U.030919.IXR10.19.0",
        datum="2019-09-03",
        senat="IX. Senat",
        betreff=(
            "Für Steuerfreiheit eines Immobilienverkaufs genügt Eigennutzung an "
            "einem einzigen Tag im Verkaufsjahr — kurze Vermietung vor dem Verkauf "
            "ist unschädlich, sofern Vorjahr durchgehend eigengenutzt"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202010060/",
        thema="Immobilienveräußerung / Eigennutzung / Spekulationsfrist (§ 23 EStG)",
        valid_from_year=2019,
        bstbl_aufgenommen=True,
    ),

    # ── 14. SFN-ZUSCHLÄGE — GRUNDLOHN BEI BEREITSCHAFTSDIENST ───────────────
    BfhUrteil(
        id="sfn_zuschlaege_grundlohn_bereitschaft_2024",
        aktenzeichen="VI R 1/22",
        ecli="ECLI:DE:BFH:2024:U.110424.VIR1.22.0",
        datum="2024-04-11",
        senat="VI. Senat",
        betreff=(
            "Grundlohn für Berechnung steuerfreier SFN-Zuschläge bei "
            "Bereitschaftsdiensten bemisst sich nach dem regulären Stundenentgelt "
            "der vertraglich vereinbarten Arbeitszeit — nicht nach dem niedrigeren "
            "Bereitschaftsdienstentgelt; gilt für Pflege, Rettungsdienst, Klinik"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202410106/",
        thema="Steuerfreie SFN-Zuschläge / Grundlohn Bereitschaftsdienst (§ 3b EStG)",
        valid_from_year=2022,
        bstbl_aufgenommen=False,
    ),

    # ── 15. SFN-ZUSCHLÄGE — GRUNDLOHNBERECHNUNG ALLGEMEIN ────────────────────
    BfhUrteil(
        id="sfn_zuschlaege_grundlohn_vertragslohn_2023",
        aktenzeichen="VI R 11/21",
        ecli="ECLI:DE:BFH:2023:U.100823.VIR11.21.0",
        datum="2023-08-10",
        senat="VI. Senat",
        betreff=(
            "Grundlohn für steuerfreie SFN-Zuschläge ist der vertraglich vereinbarte "
            "Lohn — nicht der nach Gehaltsumwandlung tatsächlich ausgezahlte (ggf. "
            "geminderte) Lohn; höhere Steuerfreiheit für Schichtarbeitnehmer mit "
            "bAV-Entgeltumwandlung"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202310202/",
        thema="Steuerfreie SFN-Zuschläge / Grundlohn Entgeltumwandlung (§ 3b EStG)",
        valid_from_year=2022,
        bstbl_aufgenommen=False,
    ),

    # ── 16. AKTIENVERL. — ADV-BESCHLUSS ZUR VERFASSUNGSWIDRIGKEIT ────────────
    BfhUrteil(
        id="aktienverluste_adv_verfassungswidrig_2022",
        aktenzeichen="VIII B 67/21",
        ecli="ECLI:DE:BFH:2022:B.070622.VIIIB67.21.0",
        datum="2022-06-07",
        senat="VIII. Senat",
        betreff=(
            "Ernstliche Zweifel an der Verfassungsmäßigkeit der Beschränkung, "
            "dass Aktienverluste nur mit Aktiengewinnen verrechnet werden dürfen "
            "— AdV ist zu gewähren; Bescheide offenhalten bis BVerfG "
            "(Az. 2 BvL 3/21) entschieden hat"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202250107/",
        thema="Verluste Aktienveräußerungen / AdV / Verfassungswidrigkeit (§ 20 Abs. 6 S. 4 EStG)",
        valid_from_year=2009,
        bstbl_aufgenommen=False,
    ),

    # ── 17. TOTALAUSFALL PRIVATDARLEHEN / CROWDLENDING ───────────────────────
    BfhUrteil(
        id="totalausfall_privatdarlehen_kapitalverlust_2017",
        aktenzeichen="VIII R 13/15",
        ecli="ECLI:DE:BFH:2017:U.241017.VIIIR13.15.0",
        datum="2017-10-24",
        senat="VIII. Senat",
        betreff=(
            "Endgültiger Ausfall einer privaten Darlehensforderung (Privatdarlehen, "
            "Crowdlending, Insolvenz des Schuldners) stellt steuerlich abzugsfähigen "
            "Verlust bei den Einkünften aus Kapitalvermögen dar — verrechenbar "
            "mit Zinsen und Dividenden"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202110189/",
        thema="Kapitalvermögen / Totalausfall Darlehen / Crowdlending (§ 20 EStG)",
        valid_from_year=2017,
        bstbl_aufgenommen=True,  # Im BStBl II 2020 nach mehrjähriger Nichtanwendungsphase
    ),

    # ── 18. DOPPELTE HAUSHALTSFÜHRUNG — ZWEITWOHNUNGSTEUER + 1.000-€-GRENZE ──
    BfhUrteil(
        id="doppelte_hf_zweitwohnungsteuer_grenze_2023",
        aktenzeichen="VI R 30/21",
        ecli="ECLI:DE:BFH:2023:U.131223.VIR30.21.0",
        datum="2023-12-13",
        senat="VI. Senat",
        betreff=(
            "Zweitwohnungsteuer fällt unter die 1.000-€-Monatsgrenze für "
            "Unterkunftskosten; zugleich bestätigt: Möbel und Einrichtung bleiben "
            "daneben voll abziehbar (Bestätigung VI R 18/17) — wer günstig mietet, "
            "kann mehr für Ausstattung ansetzen"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202410055/",
        thema="Doppelte Haushaltsführung / Zweitwohnungsteuer / 1.000-€-Grenze (§ 9 Abs. 1 Nr. 5 EStG)",
        valid_from_year=2014,
        bstbl_aufgenommen=True,
    ),

    # ── 19. MASTERSTUDIUM NACH BACHELOR — VORWEGGENOMMENE WERBUNGSKOSTEN ──────
    BfhUrteil(
        id="masterstudium_werbungskosten_2020",
        aktenzeichen="VI R 17/20",
        ecli="ECLI:DE:BFH:2020:U.120220.VIR17.20.0",
        datum="2020-02-12",
        senat="VI. Senat",
        betreff=(
            "Aufwendungen für ein Masterstudium unmittelbar nach einem beruflich "
            "motivierten Bachelorstudium sind als vorweggenommene Werbungskosten "
            "abziehbar — auch wenn der Bachelor das Erststudium war; "
            "Verlustfeststellung für Studienjahre möglich"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202010141/",
        thema="Werbungskosten / Masterstudium nach Bachelor / Fortbildungskosten (§ 9 EStG)",
        valid_from_year=2020,
        bstbl_aufgenommen=False,
    ),

    # ── 20. UNTERHALT — ANTEILIGE KÜRZUNG PRO MONAT ──────────────────────────
    BfhUrteil(
        id="unterhalt_anteilige_kuerzung_2024",
        aktenzeichen="VI R 21/21",
        ecli="ECLI:DE:BFH:2024:U.290224.VIR21.21.0",
        datum="2024-02-29",
        senat="VI. Senat",
        betreff=(
            "Unterhaltsaufwendungen können für die Monate mit tatsächlich "
            "vorliegender Bedürftigkeit in voller Höhe (1/12 des Jahreshöchstbetrags "
            "je Monat) abgezogen werden — präzisiert die Berechnung bei "
            "Studierenden und kurzzeitig bedürftigen Angehörigen"
        ),
        url="https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE202410078/",
        thema="Außergewöhnliche Belastungen / Unterhalt / anteilige Kürzung (§ 33a EStG)",
        valid_from_year=2024,
        bstbl_aufgenommen=False,
    ),
]


# ─── Zugriffs-Hilfsfunktionen ─────────────────────────────────────────────────

def get_active_urteile(year: int) -> list[BfhUrteil]:
    """Gibt alle nicht-superseded Urteile zurück, die für *year* relevant sind."""
    return [
        u for u in BFH_URTEILE
        if not u.superseded and u.valid_from_year <= year
    ]


def get_by_id(urteil_id: str) -> BfhUrteil:
    """Urteil nach ID suchen. Wirft KeyError wenn nicht gefunden."""
    for u in BFH_URTEILE:
        if u.id == urteil_id:
            return u
    raise KeyError(f"BFH-Urteil '{urteil_id}' nicht im Katalog.")
