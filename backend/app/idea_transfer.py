import json
import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any, cast

import aiosqlite
import chromadb
from chromadb.api.types import Where

from app.config import get_settings
from app.models.chat import RiskBadgeChunk
from app.models.idea_transfer import (
    CaseKind,
    DimensionId,
    IdeaTransferAnswers,
    IdeaTransferCase,
    IdeaTransferDimension,
    IdeaTransferEvaluationResponse,
    IdeaTransferSource,
    TrafficLight,
)
from app.timestamps import parse_timestamp, utc_now
from ingest.store import COLLECTION_NAME

logger = logging.getLogger(__name__)

_CASE_TITLE_PREFIX = "doppelt-steuern-sparen"
_LEGACY_CASE_TITLE_PREFIX = "Ideen-Transfer"

_LAW_BASE_URLS: dict[str, str] = {
    "EStG": "https://www.gesetze-im-internet.de/estg/",
    "AO": "https://www.gesetze-im-internet.de/ao_1977/",
    "KStG": "https://www.gesetze-im-internet.de/kstg_1977/",
    "ErbStG": "https://www.gesetze-im-internet.de/erbstg_1974/",
    "ArbNErfG": "https://www.gesetze-im-internet.de/arbnerfg/",
}

_PARA_NUM_RE = re.compile(r"§\s*(\d+[a-zA-Z]?)")

_FALLBACK_SOURCE_TEXTS: dict[tuple[str, str], str] = {
    ("EStG", "§ 5"): "Entgeltlich erworbene immaterielle Wirtschaftsgüter koennen im Betriebsvermoegen bilanziell anzusetzen sein; selbst geschaffene sind gesondert behandelt.",
    ("EStG", "§ 7"): "Absetzungen setzen ein abnutzbares Wirtschaftsgut und eine nachvollziehbare Nutzungsdauer voraus.",
    ("EStG", "§ 22"): "Sonstige Einkuenfte erfassen nicht jede private Vermoegensumschichtung; die Einordnung haengt vom konkreten Veranlassungszusammenhang ab.",
    ("EStG", "§ 23"): "Private Veraeusserungsgeschaefte knuepfen regelmaessig an angeschaffte Wirtschaftsgueter und Fristen an.",
    ("AO", "§ 42"): "Steuerliche Gestaltungen koennen bei missbraeuchlicher Ausnutzung unangemessen sein und anders beurteilt werden.",
    ("KStG", "§ 8"): "Bei Kapitalgesellschaften kann ein nicht fremduebliches Geschaeft mit Gesellschaftern als verdeckte Gewinnausschuettung zu beurteilen sein.",
    ("ErbStG", "§ 7"): "Freigebige Zuwendungen unter Lebenden koennen schenkungsteuerlich relevant werden, wenn Leistung und Gegenleistung nicht wertgleich sind.",
    ("ArbNErfG", "§ 4"): "Die Abgrenzung zwischen Diensterfindung und freier Erfindung ist fuer die Zuordnung zum Arbeitgeber wesentlich.",
}


@dataclass(frozen=True)
class _SourceRef:
    law: str
    paragraph: str
    section: str = ""


def case_title(case_kind: CaseKind) -> str:
    return (
        f"{_CASE_TITLE_PREFIX} GmbH"
        if case_kind == "own_gmbh_sale"
        else f"{_CASE_TITLE_PREFIX} Familie"
    )


def _law_url(law: str, paragraph: str) -> str | None:
    base = _LAW_BASE_URLS.get(law)
    if not base:
        return None
    match = _PARA_NUM_RE.search(paragraph)
    if not match:
        return base
    return f"{base}__{match.group(1)}.html"


def _fallback_source(ref: _SourceRef) -> IdeaTransferSource:
    return IdeaTransferSource(
        law=ref.law,
        paragraph=ref.paragraph,
        section=ref.section,
        text=_FALLBACK_SOURCE_TEXTS.get(
            (ref.law, ref.paragraph),
            "Rechtsquelle fuer die strukturierte Pruefung des Spezialfalls.",
        ),
        url=_law_url(ref.law, ref.paragraph),
    )


def _build_where_clause(year: int, refs: list[_SourceRef]) -> Where:
    filters: list[dict[str, Any]] = []
    for ref in refs:
        and_terms: list[dict[str, Any]] = [
            {"law": {"$eq": ref.law}},
            {"paragraph": {"$eq": ref.paragraph}},
        ]
        if ref.section:
            and_terms.append({"section": {"$eq": ref.section}})
        filters.append({"$and": and_terms})

    if len(filters) == 1:
        return cast(
            Where,
            {
            "$and": [
                {"year": {"$eq": year}},
                filters[0],
            ]
            },
        )
    return cast(
        Where,
        {
        "$and": [
            {"year": {"$eq": year}},
            {"$or": filters},
        ]
        },
    )


def _load_source_map(year: int, refs: list[_SourceRef]) -> dict[tuple[str, str, str], IdeaTransferSource]:
    if not refs:
        return {}

    settings = get_settings()
    try:
        client = chromadb.PersistentClient(path=settings.chroma_path)
        collection = client.get_collection(COLLECTION_NAME)
        results = collection.get(
            where=_build_where_clause(year, refs),
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        logger.info("Idea-transfer source lookup fell back to static texts: %s", exc)
        return {}

    source_map: dict[tuple[str, str, str], IdeaTransferSource] = {}
    for document, metadata in zip(
        results.get("documents", []) or [],
        results.get("metadatas", []) or [],
    ):
        if not metadata:
            continue
        law = metadata.get("law")
        paragraph = metadata.get("paragraph")
        section = metadata.get("section", "")
        url = metadata.get("url")
        if not isinstance(law, str) or not isinstance(paragraph, str):
            continue
        if not isinstance(section, str):
            section = ""
        source_map[(law, paragraph, section)] = IdeaTransferSource(
            law=law,
            paragraph=paragraph,
            section=section,
            text=document or _FALLBACK_SOURCE_TEXTS.get((law, paragraph), ""),
            url=url if isinstance(url, str) else _law_url(law, paragraph),
        )

    return source_map


def _pick_sources(year: int, refs: list[_SourceRef]) -> list[IdeaTransferSource]:
    source_map = _load_source_map(year, refs)
    picked: list[IdeaTransferSource] = []
    seen: set[tuple[str, str, str]] = set()
    for ref in refs:
        key = (ref.law, ref.paragraph, ref.section)
        if key in seen:
            continue
        seen.add(key)
        picked.append(source_map.get(key, _fallback_source(ref)))
    return picked


def _to_int(value: float | None) -> int | None:
    if value is None:
        return None
    return int(round(value))


def _truthy_summary(value: str | None) -> bool:
    return bool(value and value.strip())


def _useful_life_value(raw: int | str | None) -> tuple[int, bool]:
    if raw in (3, 5, 10):
        return int(raw), False
    return 10, True


def _risk_label(light: TrafficLight) -> RiskBadgeChunk:
    if light == "green":
        return RiskBadgeChunk(
            level="low",
            label="Plausibel pruefbar",
            explanation="Nach den aktuellen Angaben wirkt der Spezialfall strukturell nachvollziehbar, bleibt aber dokumentationsabhaengig.",
        )
    if light == "yellow":
        return RiskBadgeChunk(
            level="medium",
            label="Nur mit Zusatzpruefung",
            explanation="Wesentliche Dokumentations- oder Bewertungsfragen sind noch offen.",
        )
    return RiskBadgeChunk(
        level="high",
        label="Derzeit nicht tragfaehig",
        explanation="Mindestens ein harter Blocker spricht aktuell gegen die Struktur.",
    )


def _dimension(
    dim_id: DimensionId,
    title: str,
    traffic_light: TrafficLight,
    summary: str,
) -> IdeaTransferDimension:
    return IdeaTransferDimension(
        id=dim_id,
        title=title,
        traffic_light=traffic_light,
        summary=summary,
    )


def evaluate_case(
    case_kind: CaseKind,
    answers: IdeaTransferAnswers,
    tax_year: int,
) -> IdeaTransferEvaluationResponse:
    summary_present = _truthy_summary(answers.idea_summary)
    buyer_use_plan_present = _truthy_summary(answers.buyer_use_description)
    useful_life_years, useful_life_assumed = _useful_life_value(answers.useful_life_years)

    if answers.origin_scope == "professional":
        origin_light: TrafficLight = "red"
        origin_summary = "Die Idee wurde als beruflich oder dienstlich entstanden eingeordnet. Das ist fuer diesen Spezialfall ein harter Gegenpunkt."
    elif answers.origin_scope == "private":
        origin_light = "green"
        origin_summary = "Die Idee wurde als privat entstanden eingeordnet. Das passt grundsaetzlich zum avisierten Spezialfall."
    else:
        origin_light = "yellow"
        origin_summary = "Die Entstehung der Idee ist noch nicht klar privat abgegrenzt."

    if answers.origin_scope == "professional" or answers.connected_to_job_or_business == "yes":
        employment_light: TrafficLight = "red"
        employment_summary = "Es besteht eine Naehe zu Anstellung, Arbeitgeber oder laufendem Betrieb. Das spricht deutlich gegen eine saubere Privatzuordnung."
    elif answers.connected_to_job_or_business == "no":
        employment_light = "green"
        employment_summary = "Nach den aktuellen Angaben besteht keine erkennbare Naehe zu Arbeitgeber oder laufendem Betrieb."
    else:
        employment_light = "yellow"
        employment_summary = "Die Abgrenzung zu Job oder Betrieb ist noch offen und sollte vor Umsetzung sauber dokumentiert werden."

    if answers.documentation_status == "none" or not summary_present:
        transferability_light: TrafficLight = "red"
        transferability_summary = "Die Idee ist bislang nicht ausreichend konkret beschrieben oder dokumentiert. Ohne belastbare Beschreibung ist die Uebertragbarkeit derzeit nicht tragfaehig."
    elif answers.documentation_status == "complete":
        transferability_light = "green"
        transferability_summary = "Die Idee ist konkret beschrieben und die Dokumentation wirkt fuer eine Uebertragung grundsaetzlich ausreichend."
    else:
        transferability_light = "yellow"
        transferability_summary = "Die Idee ist erfasst, die Dokumentation ist aber noch nicht vollstaendig genug fuer eine belastbare Uebertragungspruefung."

    if answers.valuation_mode == "external":
        valuation_light: TrafficLight = "green"
        valuation_summary = "Eine externe oder belastbare unabhaengige Bewertung ist vorgesehen bzw. vorhanden."
    elif answers.valuation_mode == "internal":
        valuation_light = "yellow"
        valuation_summary = "Es liegt nur eine interne Bewertung vor. Fuer Fremdvergleich und Belastbarkeit ist das noch zu duenn."
    else:
        valuation_light = "red" if answers.valuation_mode == "none" else "yellow"
        valuation_summary = (
            "Es ist aktuell keine belastbare Bewertung hinterlegt."
            if answers.valuation_mode == "none"
            else "Die Bewertungsgrundlage ist noch unklar."
        )

    if answers.buyer_use_plan_available == "no":
        use_plan_light: TrafficLight = "red"
        use_plan_summary = "Es gibt aktuell keinen plausiblen Nutzungsplan beim Erwerber. Das ist fuer die Struktur ein harter Blocker."
    elif answers.buyer_use_plan_available == "yes" and buyer_use_plan_present:
        use_plan_light = "green"
        use_plan_summary = "Ein plausibler Nutzungsplan beim Erwerber ist beschrieben."
    else:
        use_plan_light = "yellow"
        use_plan_summary = "Der Nutzungsplan ist noch nicht belastbar beschrieben."

    if answers.is_paid_transfer == "no":
        transfer_tax_light: TrafficLight = "red"
        transfer_tax_summary = "Die geplante Uebertragung ist nicht entgeltlich. Damit faellt der v1-Scope weg und es entsteht ein deutliches Schenkungs- bzw. Strukturierungsrisiko."
    elif case_kind == "family_transfer":
        if answers.family_value_alignment == "yes":
            transfer_tax_light = "green"
            transfer_tax_summary = "Die Wertgleichheit zwischen Gegenleistung und Uebertragung wird aktuell als plausibel dokumentierbar eingeschaetzt."
        elif answers.family_value_alignment == "no":
            transfer_tax_light = "red"
            transfer_tax_summary = "Die Wertgleichheit ist aktuell nicht gegeben. Damit steht ein klares Schenkungsteuerrisiko im Raum."
        else:
            transfer_tax_light = "yellow"
            transfer_tax_summary = "Die Wertgleichheit innerhalb des Familienfalls ist noch offen und muss gesondert geprueft werden."
    else:
        if answers.is_paid_transfer == "yes" and answers.consideration_type in ("cash", "mixed"):
            transfer_tax_light = "green"
            transfer_tax_summary = "Die Struktur ist entgeltlich angelegt; im GmbH-Fall liegt der Schwerpunkt damit auf Fremdvergleich und Bewertung."
        else:
            transfer_tax_light = "yellow"
            transfer_tax_summary = "Die Gegenleistung ist noch nicht klar genug beschrieben, um den Transfer sauber einzuordnen."

    dimensions = [
        _dimension("private_origin", "Private Entstehung", origin_light, origin_summary),
        _dimension(
            "employment_proximity",
            "Naehe zu Beschaeftigung/Betrieb",
            employment_light,
            employment_summary,
        ),
        _dimension(
            "transferability",
            "Uebertragbarkeit und Dokumentation",
            transferability_light,
            transferability_summary,
        ),
        _dimension("valuation", "Bewertung und Fremdvergleich", valuation_light, valuation_summary),
        _dimension("acquirer_use_plan", "Nutzungsplan beim Erwerber", use_plan_light, use_plan_summary),
        _dimension(
            "transfer_tax",
            "Transfer-/Schenkungsteuerrelevanz",
            transfer_tax_light,
            transfer_tax_summary,
        ),
    ]

    overall: TrafficLight = "green"
    if any(dim.traffic_light == "red" for dim in dimensions):
        overall = "red"
    elif any(dim.traffic_light == "yellow" for dim in dimensions):
        overall = "yellow"

    assumptions: list[str] = []
    if case_kind == "own_gmbh_sale" and useful_life_assumed:
        assumptions.append("Fuer die jaehrliche Wirkung wurde mangels klarer Nutzungsdauer mit 10 Jahren gerechnet.")

    estimated_min = estimated_mid = estimated_max = annual_mid = None
    if case_kind == "own_gmbh_sale" and answers.purchase_price_eur and answers.purchase_price_eur > 0:
        estimated_min = _to_int(answers.purchase_price_eur * 0.25)
        estimated_mid = _to_int(answers.purchase_price_eur * 0.30)
        estimated_max = _to_int(answers.purchase_price_eur * 0.35)
        if estimated_mid is not None:
            annual_mid = _to_int(estimated_mid / useful_life_years)

    if overall == "green":
        headline = "Der Ideen-/Erfindungs-Transfer ist nach den aktuellen Angaben grundsaetzlich pruefbar."
    elif overall == "yellow":
        headline = "Der Ideen-/Erfindungs-Transfer ist derzeit nur mit zusaetzlicher Pruefung belastbar."
    else:
        headline = "Der Ideen-/Erfindungs-Transfer ist nach den aktuellen Angaben derzeit nicht tragfaehig."

    benefit_text = (
        f"**Moegliche Sparspanne:** ca. {estimated_min:,} bis {estimated_max:,} EUR gesamt, Mittelwert ca. {estimated_mid:,} EUR.\n\n"
        f"**Jaehrliche Wirkung:** ca. {annual_mid:,} EUR bei angenommener Nutzungsdauer von {useful_life_years} Jahren.\n\n"
        if estimated_mid is not None and estimated_min is not None and estimated_max is not None and annual_mid is not None
        else ""
    ).replace(",", ".")
    if case_kind == "family_transfer":
        benefit_text = (
            "**Quantifizierung:** Fuer den Familienfall wird in v1 bewusst keine feste Euro-Sparspanne ausgewiesen. "
            "Im Vordergrund stehen Wertgleichheit, Dokumentation und die Abgrenzung zur freigebigen Zuwendung.\n\n"
        )

    summary_lines = [
        f"## {headline}",
        "",
        benefit_text.rstrip(),
        "",
        "**Kurzbewertung:**",
    ]
    for dim in dimensions:
        summary_lines.append(
            f"- **{dim.title}:** {dim.summary}"
        )
    summary_lines.extend(
        [
            "",
            "**Einordnung:** Diese Auswertung ist ein strukturierter Vorab-Check und ersetzt keine individuelle Steuer- oder Rechtsberatung.",
        ]
    )
    if assumptions:
        summary_lines.extend(["", "**Annahmen:**"])
        summary_lines.extend([f"- {assumption}" for assumption in assumptions])
    summary_markdown = "\n".join(line for line in summary_lines if line != "" or summary_lines)

    required_documents = [
        "Kurze Beschreibung der Idee mit Entstehungszeitpunkt und Abgrenzung zum beruflichen Umfeld",
        "Entwurf eines entgeltlichen Uebertragungs- oder Kaufvertrags",
        "Nachweis zur geplanten Nutzung beim Erwerber",
    ]
    if answers.valuation_mode != "external":
        required_documents.append("Belastbare Bewertungsunterlage oder externes Bewertungsgutachten")
    if answers.documentation_status != "complete":
        required_documents.append("Dokumentation zur Konkretisierung und Uebertragbarkeit der Idee")
    if case_kind == "family_transfer":
        required_documents.append("Wertevergleich zwischen Gegenleistung und uebertragenem Vorteil fuer den Familienfall")

    next_actions = [
        "Kauf- bzw. Uebertragungsstruktur nur mit schriftlicher Dokumentation weiterverfolgen.",
        "Bewertung und Nutzungsplan mit dem steuerlichen Berater gegenpruefen.",
    ]
    if overall != "green":
        next_actions.insert(
            0,
            "Zunaechst die gelben bzw. roten Pruffelder schliessen, bevor eine Umsetzung vorbereitet wird.",
        )
    if case_kind == "family_transfer":
        next_actions.append("Schenkungsteuerliche Wertgleichheit gesondert dokumentieren.")

    refs = [
        _SourceRef("EStG", "§ 22"),
        _SourceRef("EStG", "§ 23"),
        _SourceRef("EStG", "§ 5"),
        _SourceRef("EStG", "§ 7"),
        _SourceRef("AO", "§ 42"),
        _SourceRef("KStG", "§ 8"),
    ]
    if case_kind == "family_transfer":
        refs.append(_SourceRef("ErbStG", "§ 7"))
    if origin_light == "red" or employment_light != "green":
        refs.append(_SourceRef("ArbNErfG", "§ 4"))

    return IdeaTransferEvaluationResponse(
        traffic_light=overall,
        headline=headline,
        summary_markdown=summary_markdown.strip(),
        estimated_tax_benefit_min_eur=estimated_min,
        estimated_tax_benefit_mid_eur=estimated_mid,
        estimated_tax_benefit_max_eur=estimated_max,
        annual_tax_benefit_mid_eur=annual_mid,
        dimensions=dimensions,
        required_documents=required_documents,
        next_actions=next_actions,
        sources=_pick_sources(tax_year, refs),
        assumptions=assumptions,
    )


async def ensure_case_session(
    db: aiosqlite.Connection,
    session_id: str,
    case_kind: CaseKind,
) -> None:
    now = utc_now()
    title = case_title(case_kind)
    await db.execute(
        """
        INSERT INTO sessions (id, title, created_at, updated_at, message_count, total_saving)
        VALUES (?, ?, ?, ?, 0, 0)
        ON CONFLICT(id) DO NOTHING
        """,
        (session_id, title, now, now),
    )
    await db.execute(
        """
        UPDATE sessions
        SET title = CASE
              WHEN message_count = 0
                OR title LIKE ?
                OR title LIKE ?
              THEN ?
              ELSE title
            END,
            updated_at = ?
        WHERE id = ?
        """,
        (f"{_CASE_TITLE_PREFIX}%", f"{_LEGACY_CASE_TITLE_PREFIX}%", title, now, session_id),
    )
    await db.commit()


async def get_case(db: aiosqlite.Connection, session_id: str) -> IdeaTransferCase | None:
    async with db.execute(
        "SELECT * FROM idea_transfer_cases WHERE session_id = ?",
        (session_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return IdeaTransferCase(
        session_id=row["session_id"],
        case_kind=row["case_kind"],
        status=row["status"],
        answers=IdeaTransferAnswers.model_validate(json.loads(row["answers_json"])),
        result=(
            IdeaTransferEvaluationResponse.model_validate(json.loads(row["result_json"]))
            if row["result_json"]
            else None
        ),
        updated_at=parse_timestamp(row["updated_at"]),
    )


async def _drop_summary_message(db: aiosqlite.Connection, session_id: str) -> None:
    async with db.execute(
        "SELECT summary_message_id FROM idea_transfer_cases WHERE session_id = ?",
        (session_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None or not row["summary_message_id"]:
        return

    summary_message_id = row["summary_message_id"]
    async with db.execute(
        "SELECT saving_amount FROM messages WHERE id = ?",
        (summary_message_id,),
    ) as cursor:
        msg_row = await cursor.fetchone()

    if msg_row is None:
        await db.execute(
            "UPDATE idea_transfer_cases SET summary_message_id = NULL WHERE session_id = ?",
            (session_id,),
        )
        await db.commit()
        return

    saving_amount = msg_row["saving_amount"] or 0
    await db.execute("DELETE FROM messages WHERE id = ?", (summary_message_id,))
    await db.execute(
        """
        UPDATE sessions
        SET message_count = CASE WHEN message_count > 0 THEN message_count - 1 ELSE 0 END,
            total_saving = CASE
              WHEN total_saving >= ? THEN total_saving - ?
              ELSE 0
            END,
            updated_at = ?
        WHERE id = ?
        """,
        (saving_amount, saving_amount, utc_now(), session_id),
    )
    await db.execute(
        "UPDATE idea_transfer_cases SET summary_message_id = NULL WHERE session_id = ?",
        (session_id,),
    )
    await db.commit()


async def save_case_draft(
    db: aiosqlite.Connection,
    session_id: str,
    case_kind: CaseKind,
    answers: IdeaTransferAnswers,
) -> IdeaTransferCase:
    await ensure_case_session(db, session_id, case_kind)
    existing = await get_case(db, session_id)
    if existing and existing.status == "completed":
        await _drop_summary_message(db, session_id)

    now = utc_now()
    await db.execute(
        """
        INSERT INTO idea_transfer_cases
          (session_id, case_kind, status, answers_json, result_json, summary_message_id, updated_at)
        VALUES (?, ?, 'draft', ?, NULL, NULL, ?)
        ON CONFLICT(session_id) DO UPDATE SET
          case_kind = excluded.case_kind,
          status = 'draft',
          answers_json = excluded.answers_json,
          result_json = NULL,
          summary_message_id = NULL,
          updated_at = excluded.updated_at
        """,
        (
            session_id,
            case_kind,
            answers.model_dump_json(),
            now,
        ),
    )
    await db.commit()
    case = await get_case(db, session_id)
    if case is None:
        raise RuntimeError("Idea-transfer draft could not be reloaded after save.")
    return case


def _summary_message_content(result: IdeaTransferEvaluationResponse) -> str:
    return result.summary_markdown


async def _upsert_summary_message(
    db: aiosqlite.Connection,
    session_id: str,
    result: IdeaTransferEvaluationResponse,
) -> None:
    risk = _risk_label(result.traffic_light)
    saving_amount = result.estimated_tax_benefit_mid_eur
    sources_json = json.dumps([source.model_dump() for source in result.sources])
    risk_json = risk.model_dump_json()
    content = _summary_message_content(result)
    now = utc_now()

    async with db.execute(
        "SELECT summary_message_id FROM idea_transfer_cases WHERE session_id = ?",
        (session_id,),
    ) as cursor:
        row = await cursor.fetchone()

    summary_message_id = row["summary_message_id"] if row else None
    if summary_message_id:
        async with db.execute(
            "SELECT saving_amount FROM messages WHERE id = ?",
            (summary_message_id,),
        ) as cursor:
            existing_msg = await cursor.fetchone()
        previous_saving = existing_msg["saving_amount"] if existing_msg else 0
        if existing_msg:
            await db.execute(
                """
                UPDATE messages
                SET content = ?, sources = ?, risk_badge = ?, saving_amount = ?, created_at = ?
                WHERE id = ?
                """,
                (
                    content,
                    sources_json,
                    risk_json,
                    saving_amount,
                    now,
                    summary_message_id,
                ),
            )
            await db.execute(
                """
                UPDATE sessions
                SET total_saving = CASE
                      WHEN total_saving - ? + ? >= 0 THEN total_saving - ? + ?
                      ELSE 0
                    END,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    previous_saving or 0,
                    saving_amount or 0,
                    previous_saving or 0,
                    saving_amount or 0,
                    now,
                    session_id,
                ),
            )
            await db.commit()
            return

    summary_message_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO messages
          (id, session_id, role, content, sources, risk_badge, saving_amount, created_at)
        VALUES (?, ?, 'assistant', ?, ?, ?, ?, ?)
        """,
        (
            summary_message_id,
            session_id,
            content,
            sources_json,
            risk_json,
            saving_amount,
            now,
        ),
    )
    await db.execute(
        """
        UPDATE sessions
        SET message_count = message_count + 1,
            total_saving = total_saving + ?,
            updated_at = ?
        WHERE id = ?
        """,
        (saving_amount or 0, now, session_id),
    )
    await db.execute(
        "UPDATE idea_transfer_cases SET summary_message_id = ? WHERE session_id = ?",
        (summary_message_id, session_id),
    )
    await db.commit()


async def evaluate_and_persist_case(
    db: aiosqlite.Connection,
    session_id: str,
    case_kind: CaseKind,
    answers: IdeaTransferAnswers,
    tax_year: int,
) -> IdeaTransferCase:
    await ensure_case_session(db, session_id, case_kind)
    result = evaluate_case(case_kind, answers, tax_year)
    now = utc_now()
    await db.execute(
        """
        INSERT INTO idea_transfer_cases
          (session_id, case_kind, status, answers_json, result_json, summary_message_id, updated_at)
        VALUES (?, ?, 'completed', ?, ?, NULL, ?)
        ON CONFLICT(session_id) DO UPDATE SET
          case_kind = excluded.case_kind,
          status = 'completed',
          answers_json = excluded.answers_json,
          result_json = excluded.result_json,
          updated_at = excluded.updated_at
        """,
        (
            session_id,
            case_kind,
            answers.model_dump_json(),
            result.model_dump_json(),
            now,
        ),
    )
    await db.commit()
    await _upsert_summary_message(db, session_id, result)
    case = await get_case(db, session_id)
    if case is None:
        raise RuntimeError("Idea-transfer case could not be reloaded after evaluation.")
    return case
