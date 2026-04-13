import type { Source, RiskBadge } from "@/types/chat";

export interface MockAnswer {
  text: string;
  sources?: Source[];
  riskBadge?: RiskBadge;
  savingAmount?: number;
}

export interface MockEntry {
  keywords: string[];
  answer: MockAnswer;
}

export const MOCK_ENTRIES: MockEntry[] = [
  {
    keywords: ["homeoffice", "home office", "zuhause arbeiten", "häuslich"],
    answer: {
      text: "Ja, Sie können Homeoffice-Kosten steuerlich geltend machen. Seit 2023 gilt die erhöhte Tagespauschale von 6 € pro Tag — maximal 210 Tage, also bis zu 1.260 € im Jahr.\n\nAlternativ: Wenn Ihr Arbeitszimmer ausschließlich beruflich genutzt wird und den Mittelpunkt Ihrer Tätigkeit bildet, können Sie die anteiligen Raumkosten (Miete, Nebenkosten, Abschreibung) unbegrenzt absetzen — das lohnt sich bei größeren Wohnungen oft deutlich mehr.\n\nHaben Sie auch Arbeitsmittel wie Laptop, Monitor oder Bürostuhl gekauft? Diese wären zusätzlich absetzbar.",
      sources: [
        {
          law: "EStG",
          paragraph: "§ 4",
          section: "Abs. 5 Nr. 6b",
          text: "Für jeden Kalendertag, an dem der Steuerpflichtige seine betriebliche oder berufliche Tätigkeit ausschließlich in der häuslichen Wohnung ausübt, kann er einen Betrag von 6 Euro abziehen, höchstens 1 260 Euro im Wirtschafts- oder Kalenderjahr.",
        },
        {
          law: "EStG",
          paragraph: "§ 9",
          section: "Abs. 1 Nr. 7",
          text: "Aufwendungen für ein häusliches Arbeitszimmer sowie die Kosten der Ausstattung sind unbeschränkt als Werbungskosten abzugsfähig, wenn das Arbeitszimmer den Mittelpunkt der gesamten betrieblichen und beruflichen Betätigung bildet.",
        },
      ],
      riskBadge: {
        level: "low",
        label: "Unstreitig",
        explanation: "Tagespauschale ist seit 2023 gesetzlich klar geregelt (§ 4 Abs. 5 Nr. 6b EStG). Volle Akzeptanz durch Finanzbehörden, kein Streitpotenzial.",
      },
      savingAmount: 252,
    },
  },
  {
    keywords: ["laptop", "computer", "pc", "monitor", "arbeitsmittel", "notebook"],
    answer: {
      text: "Ja — und sogar vollständig im Kaufjahr. Seit dem BMF-Schreiben vom 22.02.2022 können Computerhardware und Software mit einer Nutzungsdauer von 0 Jahren sofort und zu 100 % abgeschrieben werden.\n\nBei einem Laptop für 1.400 € und einem Grenzsteuersatz von 30 % wären das ~420 € Steuerersparnis.\n\nGrauzone: Das Finanzamt prüft gelegentlich die berufliche Nutzung. Bei gemischter Nutzung (privat + beruflich) empfehle ich ein kurzes Nutzungsprotokoll — das schützt den vollen Abzug.\n\nHaben Sie weitere Arbeitsmittel gekauft? Headset, zweiter Monitor, Bürostuhl, externe Festplatte?",
      sources: [
        {
          law: "EStG",
          paragraph: "§ 9",
          section: "Abs. 1 Nr. 7",
          text: "Bei Wirtschaftsgütern, die ausschließlich oder fast ausschließlich der Berufsausübung dienen, können die Anschaffungskosten als Werbungskosten abgezogen werden.",
        },
      ],
      riskBadge: {
        level: "medium",
        label: "Grauzone",
        explanation: "Sofortabschreibung für PCs ist seit BMF-Schreiben 22.02.2022 möglich. Bei gemischter Nutzung (privat + beruflich) prüft das FA die Aufteilung. Nutzungsprotokoll empfohlen.",
      },
      savingAmount: 420,
    },
  },
  {
    keywords: ["pendler", "fahrtkosten", "pendlerpauschale", "entfernungspauschale", "fahrtweg", "kilometer"],
    answer: {
      text: "Die Pendlerpauschale beträgt 0,30 € pro Kilometer für die ersten 20 km und 0,38 € ab dem 21. Kilometer (einfache Strecke, nicht Hin- und Rückweg).\n\nBeispiel: Bei 35 km Arbeitsweg und 220 Arbeitstagen ergibt sich:\n• 20 km × 0,30 € × 220 Tage = 1.320 €\n• 15 km × 0,38 € × 220 Tage = 1.254 €\n→ Gesamte Werbungskosten: 2.574 €\n\nDas übersteigt den Arbeitnehmer-Pauschbetrag (1.230 €) um 1.344 € — die tatsächliche Steuerersparnis hängt von Ihrem Grenzsteuersatz ab.\n\nNutzen Sie Öffentliche Verkehrsmittel? Dann können die tatsächlichen Kosten günstiger sein.",
      sources: [
        {
          law: "EStG",
          paragraph: "§ 9",
          section: "Abs. 1 Nr. 4",
          text: "Aufwendungen des Arbeitnehmers für Wege zwischen Wohnung und erster Tätigkeitsstätte sind als Werbungskosten abzugsfähig. Zur Abgeltung dieser Aufwendungen ist für jeden Arbeitstag, an dem der Arbeitnehmer die erste Tätigkeitsstätte aufsucht, eine Entfernungspauschale für jeden vollen Kilometer der Entfernung anzusetzen von 0,30 Euro für die ersten 20 Kilometer und 0,38 Euro für jeden weiteren Kilometer.",
        },
      ],
      riskBadge: {
        level: "low",
        label: "Unstreitig",
        explanation: "Gesetzlich eindeutig geregelt in § 9 Abs. 1 Nr. 4 EStG. Keine Streitgefahr bei korrekter Angabe der Arbeitstage und Entfernung.",
      },
      savingAmount: 403,
    },
  },
  {
    keywords: ["riester", "riester-rente", "altersvorsorge", "rente", "vorsorge"],
    answer: {
      text: "Riester-Beiträge können Sie als Sonderausgaben absetzen — bis zu 2.100 € pro Jahr (inkl. staatlicher Zulagen).\n\nDas Finanzamt prüft automatisch, ob der Sonderausgabenabzug oder die staatliche Zulage (175 € Grundzulage + 300 € je Kind) günstiger ist (Günstigerprüfung). Sie müssen das nicht selbst berechnen.\n\nGrauzone: Bei langen Laufzeiten und veränderten Lebensumständen (Kündigung, Auslandsaufenthalt) kann die schädliche Verwendung zu Rückforderungen führen — das prüfen wir, wenn Sie Änderungen planen.\n\nWie hoch war Ihr Beitrag im letzten Jahr?",
      sources: [
        {
          law: "EStG",
          paragraph: "§ 10a",
          section: "Abs. 1",
          text: "In der inländischen gesetzlichen Rentenversicherung Pflichtversicherte können Altersvorsorgebeiträge bis zu 2 100 Euro jährlich als Sonderausgaben abziehen.",
        },
      ],
      riskBadge: {
        level: "low",
        label: "Unstreitig",
        explanation: "Riester-Sonderausgabenabzug ist gesetzlich klar geregelt. Günstigerprüfung erfolgt automatisch durch das FA.",
      },
      savingAmount: 315,
    },
  },
  {
    keywords: ["handwerker", "handwerkerleistung", "renovierung", "reparatur", "haushaltsnahe"],
    answer: {
      text: "Für Handwerkerleistungen im eigenen Haushalt können Sie 20 % der Lohnkosten (nicht Materialkosten!) direkt von der Steuerschuld abziehen — das ist eine Steuerermäßigung, keine Werbungskosten.\n\nMaximum: 1.200 € Steuerersparnis pro Jahr (= 20 % von 6.000 € Lohnkosten).\n\nWichtig: Die Zahlung muss per Überweisung erfolgen — Barzahlung wird nicht anerkannt. Bewahren Sie die Rechnung mit ausgewiesenen Lohnkosten auf.\n\nZusätzlich: Haushaltsnahe Dienstleistungen (Putzfrau, Gärtner, Pflegedienst) sind separat mit bis zu 4.000 € Steuerermäßigung absetzbar.\n\nWelche Handwerkerarbeiten haben Sie durchführen lassen?",
      sources: [
        {
          law: "EStG",
          paragraph: "§ 35a",
          section: "Abs. 3",
          text: "Für die Inanspruchnahme von Handwerkerleistungen für Renovierungs-, Erhaltungs- und Modernisierungsmaßnahmen ermäßigt sich die tarifliche Einkommensteuer um 20 Prozent der Aufwendungen des Steuerpflichtigen, höchstens jedoch um 1 200 Euro.",
        },
      ],
      riskBadge: {
        level: "low",
        label: "Unstreitig",
        explanation: "Direkt in § 35a EStG geregelt. Einzige Anforderung: Banküberweisung und Rechnung mit separatem Lohnkostenausweis.",
      },
      savingAmount: 1200,
    },
  },
  {
    keywords: ["weiterbildung", "fortbildung", "studium", "kurs", "seminar", "fachliteratur", "bücher"],
    answer: {
      text: "Berufliche Weiterbildungskosten sind vollständig als Werbungskosten absetzbar — Kursgebühren, Fahrtkosten, Übernachtungen und Fachliteratur.\n\nBei Fachliteratur gilt: Das Buch muss überwiegend beruflich genutzt werden. Ein Steuerratgeber für Privatpersonen ist absetzbar; ein Roman nicht. Bei Grenzfällen (z. B. allgemeines IT-Buch) empfehle ich, den Berufskontext kurz zu notieren.\n\nGrauzone: Ein Erststudium oder eine erstmalige Berufsausbildung ist nicht als Werbungskosten absetzbar (nur als Sonderausgaben bis 6.000 €) — das ist ein häufiges Missverständnis und führt zu Ablehnungen.\n\nWas genau haben Sie belegt oder gekauft?",
      sources: [
        {
          law: "EStG",
          paragraph: "§ 9",
          section: "Abs. 1 Nr. 7",
          text: "Aufwendungen für Arbeitsmittel, zum Beispiel für Werkzeuge und typische Berufskleidung, sind als Werbungskosten abzugsfähig.",
        },
        {
          law: "EStG",
          paragraph: "§ 12",
          section: "Nr. 5",
          text: "Aufwendungen für eine erstmalige Berufsausbildung oder für ein Erststudium, das zugleich eine Erstausbildung vermittelt, sind nicht als Werbungskosten abzugsfähig.",
        },
      ],
      riskBadge: {
        level: "medium",
        label: "Grauzone",
        explanation: "Fortbildung klar absetzbar, Erstausbildung nicht. Grauzone bei Umschulungen und berufsbegleitenden Erststudien — hier gibt es laufende BFH-Rechtsprechung.",
      },
      savingAmount: 180,
    },
  },
  {
    keywords: ["versicherung", "berufsunfähigkeit", "bu", "haftpflicht", "krankenversicherung"],
    answer: {
      text: "Versicherungsbeiträge lassen sich teils als Vorsorgeaufwendungen (Sonderausgaben), teils als Werbungskosten absetzen — je nach Art:\n\n• Kranken- und Pflegeversicherung (Basisabsicherung): vollständig als Sonderausgaben absetzbar, kein Höchstbetrag\n• Berufsunfähigkeitsversicherung: als Vorsorgeaufwand bis zum allgemeinen Höchstbetrag (1.900 € Angestellte / 2.800 € Selbstständige)\n• Private Haftpflicht: Sonderausgaben im Rahmen des Höchstbetrags\n• Berufshaftpflicht (z. B. für Freiberufler): vollständig als Betriebsausgabe absetzbar\n\nSind Sie angestellt oder selbstständig? Das ändert die Höchstbeträge erheblich.",
      sources: [
        {
          law: "EStG",
          paragraph: "§ 10",
          section: "Abs. 1 Nr. 3",
          text: "Beiträge zu Krankenversicherungen und gesetzlichen Pflegeversicherungen sind als Sonderausgaben abzugsfähig, soweit diese zur Erlangung eines sozialhilfegleichen Versorgungsniveaus erforderlich sind.",
        },
      ],
      riskBadge: {
        level: "low",
        label: "Unstreitig",
        explanation: "Kranken- und Pflegeversicherungsbeiträge sind durch BVerfG-Entscheidung gesichert und vollständig absetzbar. BU und Haftpflicht unterliegen Höchstbeträgen.",
      },
      savingAmount: 285,
    },
  },
];

export function findMatchingEntry(question: string): MockEntry {
  const lower = question.toLowerCase();
  const match = MOCK_ENTRIES.find((entry) =>
    entry.keywords.some((kw) => lower.includes(kw))
  );
  return match ?? MOCK_ENTRIES[Math.floor(Math.random() * MOCK_ENTRIES.length)];
}
