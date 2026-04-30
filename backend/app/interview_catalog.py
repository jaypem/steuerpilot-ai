"""
Statischer Fragen-Katalog für den Proaktiven Steuer-Interview-Check (Phase 22).

Jede Frage hat:
  id          — eindeutige ID, z.B. "work.homeoffice"
  category    — eine der 8 Kategorien (Literal)
  text        — Fragetext auf Deutsch
  answer_type — "bool" | "choice" | "number" | "text"
  options     — Auswahlmöglichkeiten (nur bei answer_type="choice")
  condition   — (question_id, expected_value) — Frage wird nur gestellt wenn die
                Bedingung erfüllt ist. expected_value kann ein einzelner Wert
                oder eine Liste von Werten sein (OR-Logik).
  rag_hint    — Gesetze, die für die RAG-Auswertung dieser Frage relevant sind

Kategorien:
  "basis"      — Basisdaten & Sonderausgaben
  "arbeit"     — Arbeit & Beruf
  "wohnen"     — Wohnen, Haushalt & Energie
  "nebenberuf" — Nebenberuf & Ehrenamt
  "vermietung" — Vermietung & Verpachtung
  "vorsorge"   — Vorsorge & Versicherungen
  "kapital"    — Kapitalanlagen
  "gesundheit" — Gesundheit, Pflege & außergewöhnliche Belastungen
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Category = Literal[
    "basis",
    "arbeit",
    "wohnen",
    "nebenberuf",
    "vermietung",
    "vorsorge",
    "kapital",
    "gesundheit",
]

AnswerType = Literal["bool", "choice", "number", "text"]

# Human-readable category labels (used in reports / frontend)
CATEGORY_LABELS: dict[str, str] = {
    "basis":      "Basisdaten & Sonderausgaben",
    "arbeit":     "Arbeit & Beruf",
    "wohnen":     "Wohnen, Haushalt & Energie",
    "nebenberuf": "Nebenberuf & Ehrenamt",
    "vermietung": "Vermietung & Verpachtung",
    "vorsorge":   "Vorsorge & Versicherungen",
    "kapital":    "Kapitalanlagen",
    "gesundheit": "Gesundheit, Pflege & außergewöhnliche Belastungen",
}


@dataclass(frozen=True)
class Question:
    id: str
    category: Category
    text: str
    answer_type: AnswerType
    options: tuple[str, ...] | None = None
    # (question_id, expected_value | list[expected_value])
    condition: tuple[str, Any] | None = None
    rag_hint: tuple[str, ...] = field(default_factory=tuple)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _q(
    id: str,
    category: Category,
    text: str,
    answer_type: AnswerType,
    options: list[str] | None = None,
    condition: tuple[str, Any] | None = None,
    rag_hint: list[str] | None = None,
) -> Question:
    return Question(
        id=id,
        category=category,
        text=text,
        answer_type=answer_type,
        options=tuple(options) if options else None,
        condition=condition,
        rag_hint=tuple(rag_hint) if rag_hint else (),
    )


# ─── Katalog ──────────────────────────────────────────────────────────────────

# Angestellte + Beamte können Pendlerpauschale geltend machen
_EMPLOYED = ["Angestellt", "Beamter", "Beides"]
# Selbstständige + Freelancer haben eigene Betriebsausgaben
_SELF_EMPLOYED = ["Selbstständig", "Beides"]

QUESTIONS: list[Question] = [

    # ── 1. Basisdaten & Sonderausgaben ────────────────────────────────────────

    _q("base.employment",
       "basis",
       "Wie bist du aktuell beschäftigt?",
       "choice",
       options=["Angestellt", "Selbstständig", "Beides", "Beamter", "Rentner"],
       rag_hint=["EStG", "LStR"]),

    _q("base.marital_status",
       "basis",
       "Wie ist dein Familienstand?",
       "choice",
       options=["Ledig", "Verheiratet / eingetragene Lebenspartnerschaft",
                "Getrennt lebend", "Geschieden / verwitwet"],
       rag_hint=["EStG"]),

    _q("base.has_children",
       "basis",
       "Hast du Kinder?",
       "bool",
       rag_hint=["EStG"]),

    _q("base.children_count",
       "basis",
       "Wie viele Kinder hast du?",
       "number",
       condition=("base.has_children", True),
       rag_hint=["EStG"]),

    _q("base.children_under_14",
       "basis",
       "Sind eines oder mehrere deiner Kinder jünger als 14 Jahre?",
       "bool",
       condition=("base.has_children", True),
       rag_hint=["EStG"]),

    _q("base.childcare_costs",
       "basis",
       "Hast du im Steuerjahr Kinderbetreuungskosten gezahlt "
       "(Kita, Tagesmutter, Hort)?",
       "bool",
       condition=("base.children_under_14", True),
       rag_hint=["EStG"]),

    _q("base.school_fees",
       "basis",
       "Besucht ein Kind eine Privatschule mit anerkanntem Schulgeld?",
       "bool",
       condition=("base.has_children", True),
       rag_hint=["EStG"]),

    _q("base.church_tax",
       "basis",
       "Bist du kirchensteuerpflichtig?",
       "bool",
       rag_hint=["EStG"]),

    _q("base.donations",
       "basis",
       "Hast du im Steuerjahr Spenden oder Mitgliedsbeiträge "
       "an gemeinnützige Organisationen geleistet?",
       "bool",
       rag_hint=["EStG"]),

    _q("base.donations_amount",
       "basis",
       "Wie hoch waren deine gesamten Spenden und Mitgliedsbeiträge "
       "ungefähr (in Euro)?",
       "number",
       condition=("base.donations", True),
       rag_hint=["EStG"]),

    _q("base.alimony",
       "basis",
       "Zahlst du Unterhalt an eine frühere Ehe- oder Lebenspartnerin / "
       "einen früheren Ehe- oder Lebenspartner?",
       "bool",
       rag_hint=["EStG"]),

    _q("base.alimony_amount",
       "basis",
       "Wie hoch waren deine Unterhaltszahlungen im Steuerjahr "
       "insgesamt (in Euro)?",
       "number",
       condition=("base.alimony", True),
       rag_hint=["EStG"]),

    # ── 2. Arbeit & Beruf ─────────────────────────────────────────────────────

    _q("work.homeoffice",
       "arbeit",
       "Hast du im Steuerjahr (teilweise) von zu Hause gearbeitet?",
       "bool",
       rag_hint=["EStG", "LStR", "BMF"]),

    _q("work.homeoffice_days",
       "arbeit",
       "An wie vielen Tagen hast du ausschließlich von zu Hause gearbeitet?",
       "number",
       condition=("work.homeoffice", True),
       rag_hint=["EStG", "BMF"]),

    _q("work.homeoffice_room",
       "arbeit",
       "Hast du ein abgeschlossenes, ausschließlich beruflich genutztes "
       "Arbeitszimmer?",
       "bool",
       condition=("work.homeoffice", True),
       rag_hint=["EStG", "BMF"]),

    _q("work.commute_km",
       "arbeit",
       "Wie viele Kilometer beträgt deine einfache Pendlerstrecke "
       "zur ersten Tätigkeitsstätte?",
       "number",
       condition=("base.employment", _EMPLOYED),
       rag_hint=["EStG", "LStR"]),

    _q("work.commute_days",
       "arbeit",
       "An wie vielen Tagen bist du tatsächlich ins Büro / zur Arbeitsstätte "
       "gefahren?",
       "number",
       condition=("work.commute_km", True),  # any truthy number
       rag_hint=["EStG", "LStR"]),

    _q("work.equipment",
       "arbeit",
       "Hast du beruflich genutzte Arbeitsmittel selbst bezahlt "
       "(z.B. Computer, Schreibtisch, Fachliteratur)?",
       "bool",
       rag_hint=["EStG", "LStR"]),

    _q("work.equipment_amount",
       "arbeit",
       "Wie hoch waren diese Ausgaben für Arbeitsmittel ungefähr (in Euro)?",
       "number",
       condition=("work.equipment", True),
       rag_hint=["EStG", "LStR"]),

    _q("work.training",
       "arbeit",
       "Hast du im Steuerjahr Ausgaben für berufliche Weiterbildung "
       "oder Fortbildung gehabt?",
       "bool",
       rag_hint=["EStG", "LStR"]),

    _q("work.clothing",
       "arbeit",
       "Hast du typische Berufskleidung oder Schutzkleidung selbst "
       "gekauft oder gereinigt?",
       "bool",
       rag_hint=["EStG", "LStR"]),

    _q("work.double_household",
       "arbeit",
       "Führst du aus beruflichen Gründen einen doppelten Haushalt "
       "(zweite Wohnung am Arbeitsort)?",
       "bool",
       rag_hint=["EStG", "LStR"]),

    _q("work.vehicle_business",
       "arbeit",
       "Nutzt du dein Fahrzeug für betriebliche Zwecke?",
       "bool",
       condition=("base.employment", _SELF_EMPLOYED),
       rag_hint=["EStG", "LStR"]),

    _q("work.office_costs",
       "arbeit",
       "Hast du Kosten für ein externes Büro oder Co-Working-Space "
       "als Betriebsausgabe?",
       "bool",
       condition=("base.employment", _SELF_EMPLOYED),
       rag_hint=["EStG"]),

    # ── 3. Wohnen, Haushalt & Energie ─────────────────────────────────────────

    _q("home.owns_property",
       "wohnen",
       "Lebst du in einer eigenen Immobilie (Haus oder Eigentumswohnung)?",
       "bool",
       rag_hint=["EStG"]),

    _q("home.household_services",
       "wohnen",
       "Beschäftigst du eine Haushaltshilfe oder hast du haushaltsnahe "
       "Dienstleistungen (z.B. Reinigung, Gartenpflege) bezahlt?",
       "bool",
       rag_hint=["EStG"]),

    _q("home.household_services_amount",
       "wohnen",
       "Wie hoch waren die Kosten für haushaltsnahe Dienstleistungen "
       "ungefähr (in Euro)?",
       "number",
       condition=("home.household_services", True),
       rag_hint=["EStG"]),

    _q("home.craftsman",
       "wohnen",
       "Hast du Handwerker für Renovierungs- oder Instandhaltungsarbeiten "
       "in deinem Haushalt beauftragt?",
       "bool",
       rag_hint=["EStG"]),

    _q("home.craftsman_amount",
       "wohnen",
       "Wie hoch war der Arbeitslohnanteil der Handwerkerrechnung "
       "ungefähr (in Euro, ohne Material)?",
       "number",
       condition=("home.craftsman", True),
       rag_hint=["EStG"]),

    _q("home.relocation",
       "wohnen",
       "Bist du im Steuerjahr aus beruflichen Gründen umgezogen?",
       "bool",
       rag_hint=["EStG", "LStR"]),

    _q("home.energy_renovation",
       "wohnen",
       "Hast du energetische Sanierungsmaßnahmen durchgeführt "
       "(z.B. Dämmung, Heizungsaustausch, Fenster)?",
       "bool",
       condition=("home.owns_property", True),
       rag_hint=["EStG", "BMF"]),

    _q("home.energy_renovation_amount",
       "wohnen",
       "Wie hoch waren die Kosten der energetischen Sanierung "
       "ungefähr (in Euro)?",
       "number",
       condition=("home.energy_renovation", True),
       rag_hint=["EStG", "BMF"]),

    _q("home.photovoltaic",
       "wohnen",
       "Hast du eine Photovoltaikanlage auf deiner Immobilie?",
       "bool",
       condition=("home.owns_property", True),
       rag_hint=["EStG", "BMF"]),

    # ── 4. Nebenberuf & Ehrenamt ──────────────────────────────────────────────

    _q("side.has_side_activity",
       "nebenberuf",
       "Übst du neben deiner Haupttätigkeit ein Ehrenamt oder "
       "eine Nebentätigkeit aus?",
       "bool",
       rag_hint=["EStG"]),

    _q("side.activity_type",
       "nebenberuf",
       "Um welche Art von Tätigkeit handelt es sich?",
       "choice",
       options=["Übungsleiter / Ausbilder / Erzieher (§ 3 Nr. 26 EStG)",
                "Vereinsamt / Ehrenamt (§ 3 Nr. 26a EStG)",
                "Freiberufliche Nebentätigkeit",
                "Gewerbliche Nebentätigkeit",
                "Sonstiges"],
       condition=("side.has_side_activity", True),
       rag_hint=["EStG"]),

    _q("side.income_amount",
       "nebenberuf",
       "Wie hoch waren deine Einnahmen aus dieser Tätigkeit "
       "im Steuerjahr (in Euro)?",
       "number",
       condition=("side.has_side_activity", True),
       rag_hint=["EStG"]),

    _q("side.expenses",
       "nebenberuf",
       "Hattest du Ausgaben (z.B. Fahrtkosten, Material) im Zusammenhang "
       "mit dieser Nebentätigkeit?",
       "bool",
       condition=("side.has_side_activity", True),
       rag_hint=["EStG"]),

    # ── 5. Vermietung & Verpachtung ───────────────────────────────────────────

    _q("rental.has_rental",
       "vermietung",
       "Vermietest du eine Immobilie, eine Wohnung oder ein Zimmer?",
       "bool",
       rag_hint=["EStG"]),

    _q("rental.purchase_year",
       "vermietung",
       "In welchem Jahr wurde die vermietete Immobilie angeschafft "
       "oder hergestellt?",
       "number",
       condition=("rental.has_rental", True),
       rag_hint=["EStG"]),

    _q("rental.rental_income",
       "vermietung",
       "Wie hoch waren deine Mieteinnahmen im Steuerjahr "
       "ungefähr (in Euro)?",
       "number",
       condition=("rental.has_rental", True),
       rag_hint=["EStG"]),

    _q("rental.renovation_costs",
       "vermietung",
       "Hast du Renovierungs- oder Erhaltungsaufwendungen an der "
       "vermieteten Immobilie gehabt?",
       "bool",
       condition=("rental.has_rental", True),
       rag_hint=["EStG"]),

    _q("rental.financing_costs",
       "vermietung",
       "Hast du Finanzierungskosten (Hypothekenzinsen) für die "
       "vermietete Immobilie?",
       "bool",
       condition=("rental.has_rental", True),
       rag_hint=["EStG"]),

    # ── 6. Vorsorge & Versicherungen ──────────────────────────────────────────

    _q("pension.riester",
       "vorsorge",
       "Hast du einen Riester-Vertrag?",
       "bool",
       rag_hint=["EStG"]),

    _q("pension.riester_contributions",
       "vorsorge",
       "Wie hoch waren deine eigenen Beiträge zum Riester-Vertrag "
       "im Steuerjahr (in Euro)?",
       "number",
       condition=("pension.riester", True),
       rag_hint=["EStG"]),

    _q("pension.ruerup",
       "vorsorge",
       "Hast du einen Rürup-Vertrag (Basisrente)?",
       "bool",
       rag_hint=["EStG"]),

    _q("pension.company_pension",
       "vorsorge",
       "Hast du eine betriebliche Altersversorgung (bAV) über "
       "deinen Arbeitgeber?",
       "bool",
       condition=("base.employment", _EMPLOYED),
       rag_hint=["EStG", "LStR"]),

    _q("pension.private_health",
       "vorsorge",
       "Bist du privat krankenversichert?",
       "bool",
       rag_hint=["EStG"]),

    _q("pension.disability_insurance",
       "vorsorge",
       "Hast du eine Berufsunfähigkeitsversicherung?",
       "bool",
       rag_hint=["EStG"]),

    # ── 7. Kapitalanlagen ─────────────────────────────────────────────────────

    _q("capital.has_investments",
       "kapital",
       "Hast du Kapitalanlagen (Aktien, ETFs, Fonds, Tagesgeld)?",
       "bool",
       rag_hint=["EStG"]),

    _q("capital.exemption_order",
       "kapital",
       "Hast du einen Freistellungsauftrag bei deiner Bank gestellt?",
       "bool",
       condition=("capital.has_investments", True),
       rag_hint=["EStG"]),

    _q("capital.exemption_fully_used",
       "kapital",
       "Wurde dein Sparerpauschbetrag (1.000 € / 2.000 € bei "
       "Zusammenveranlagung) vollständig ausgenutzt?",
       "bool",
       condition=("capital.has_investments", True),
       rag_hint=["EStG"]),

    _q("capital.foreign_withholding_tax",
       "kapital",
       "Hast du ausländische Quellensteuer auf Dividenden oder Zinsen "
       "gezahlt, die über den anrechenbaren Betrag hinausgeht?",
       "bool",
       condition=("capital.has_investments", True),
       rag_hint=["EStG"]),

    _q("capital.loss_carryforward",
       "kapital",
       "Hast du einen Verlustverrechnungstopf aus Kapitalverlusten "
       "vergangener Jahre?",
       "bool",
       condition=("capital.has_investments", True),
       rag_hint=["EStG"]),

    # ── 8. Gesundheit, Pflege & außergewöhnliche Belastungen ─────────────────

    _q("health.high_medical_costs",
       "gesundheit",
       "Hattest du im Steuerjahr hohe Krankheitskosten, die nicht "
       "von der Krankenkasse erstattet wurden "
       "(z.B. Zuzahlungen, Hilfsmittel, Brillen, Zahnersatz)?",
       "bool",
       rag_hint=["EStG"]),

    _q("health.medical_costs_amount",
       "gesundheit",
       "Wie hoch waren diese nicht erstatteten Krankheitskosten "
       "ungefähr (in Euro)?",
       "number",
       condition=("health.high_medical_costs", True),
       rag_hint=["EStG"]),

    _q("health.disability",
       "gesundheit",
       "Liegt bei dir eine anerkannte Schwerbehinderung vor?",
       "bool",
       rag_hint=["EStG"]),

    _q("health.disability_degree",
       "gesundheit",
       "Wie hoch ist dein Grad der Behinderung (GdB)?",
       "number",
       condition=("health.disability", True),
       rag_hint=["EStG"]),

    _q("health.care_recipient",
       "gesundheit",
       "Pflegst du einen Angehörigen mit einem anerkannten Pflegegrad "
       "(unentgeltlich, in ihrer/seiner Wohnung oder deiner)?",
       "bool",
       rag_hint=["EStG"]),

    _q("health.care_degree",
       "gesundheit",
       "Welchen Pflegegrad hat die gepflegte Person?",
       "choice",
       options=["Pflegegrad 2", "Pflegegrad 3", "Pflegegrad 4", "Pflegegrad 5"],
       condition=("health.care_recipient", True),
       rag_hint=["EStG"]),
]

# ─── Public API ───────────────────────────────────────────────────────────────

_BY_ID: dict[str, Question] = {q.id: q for q in QUESTIONS}


def get_all_questions() -> list[Question]:
    """Return all questions in catalog order."""
    return list(QUESTIONS)


def get_by_id(question_id: str) -> Question:
    """Raise KeyError if question_id is unknown."""
    try:
        return _BY_ID[question_id]
    except KeyError:
        raise KeyError(
            f"Unknown question id: {question_id!r}. "
            f"Available: {list(_BY_ID)}"
        )


def get_by_category(category: str) -> list[Question]:
    """Return all questions for a given category slug."""
    return [q for q in QUESTIONS if q.category == category]
