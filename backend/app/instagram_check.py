import base64
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, cast

import aiosqlite
import chromadb
from anthropic import AsyncAnthropic
from fastapi import HTTPException, UploadFile
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.schema import QueryBundle
from ollama import AsyncClient as OllamaAsyncClient

from app.config import get_settings
from app.index import get_index, has_indexed_data
from app.llm import get_llm
from app.models.chat import RiskBadgeChunk
from app.models.idea_transfer import IdeaTransferSource
from app.models.instagram_check import (
    InstagramCheckSaveRequest,
    InstagramCheckStatus,
    InstagramClaim,
    InstagramEvaluatedTip,
    InstagramFollowUpQuestion,
    InstagramImageRef,
    InstagramPostCheck,
    ReturnBucket,
    TaxPrepItem,
    TipCategory,
)
from app.timestamps import parse_timestamp, utc_now
from ingest.store import COLLECTION_NAME

logger = logging.getLogger(__name__)

INSTAGRAM_CHECK_TITLE = "Instagram-Check"
UPLOAD_SUBDIR = "instagram-check"
_VALID_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
_OLLAMA_MULTIMODAL_MARKERS = (
    "llava",
    "vision",
    "gemma3",
    "gemma4",
    "qwen2.5vl",
    "qwen2-vl",
    "minicpm",
    "moondream",
    "bakllava",
)
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_CLAIM_SPLIT_RE = re.compile(r"(?:\n+|(?<=\.)\s{2,}|(?<=\!)\s+|(?<=\?)\s+)")
_RETURN_BUCKETS = {
    "anlage_n",
    "betriebsausgaben",
    "sonderausgaben",
    "vorsorge",
    "haushaltsnahe_dienstleistungen",
    "kinder/familie",
    "kapital",
    "other",
}
_TIP_CATEGORIES = {
    "arbeitsmittel",
    "homeoffice",
    "pendeln",
    "weiterbildung",
    "sonderausgaben",
    "vorsorge",
    "haushaltsnahe_dienstleistungen",
    "kinder/familie",
    "kapital",
    "betriebsausgaben",
    "other",
}

_CLAIM_ANALYSIS_PROMPT = """\
Du siehst Screenshots eines Instagram-Posts mit Steuerspar-Tipps.

Extrahiere daraus atomare, eigenstaendige Steuertipps fuer deutsche Steuererklaerungen.
Regeln:
- Zerlege Sammelposts in einzelne Tipps.
- Entferne Werbetext, Emojis, Call-to-Actions und irrelevante Einleitungen.
- Gib keine Dubletten aus.
- Maximal 8 Tipps.
- Antworte NUR mit JSON im Format:
{
  "claims": [
    {"text": "..." }
  ]
}
"""

_EVALUATION_PROMPT = """\
Du bewertest einen aus einem Instagram-Post extrahierten Steuer-Tipp fuer eine konkrete Person in Deutschland.

Steuerjahr: {tax_year}
Tipptext: {tip_text}
Vorklassifikation Kategorie: {category}
Vorklassifikation Return-Bucket: {return_bucket}
Antworten des Nutzers:
{answers_text}

Relevanter Gesetzeskontext:
{law_context}

Antworte NUR mit JSON:
{{
  "title": "<kurzer Titel>",
  "normalized_tip": "<sauber formulierter Tipp>",
  "traffic_light": "<green|yellow|red>",
  "explanation": "<klare fachliche Einordnung fuer diesen Nutzerfall>",
  "estimated_saving_eur": <ganze Zahl oder null>,
  "required_evidence": ["<Nachweis 1>", "<Nachweis 2>"],
  "category": "<arbeitsmittel|homeoffice|pendeln|weiterbildung|sonderausgaben|vorsorge|haushaltsnahe_dienstleistungen|kinder/familie|kapital|betriebsausgaben|other>",
  "return_bucket": "<anlage_n|betriebsausgaben|sonderausgaben|vorsorge|haushaltsnahe_dienstleistungen|kinder/familie|kapital|other>"
}}

Regeln:
- green nur wenn der Tipp nach den Angaben des Nutzers konkret anwendbar wirkt.
- yellow wenn Informationen oder Belege fehlen.
- red wenn der Tipp nach den Nutzerangaben nicht tragfaehig, nicht passend oder offensichtlich problematisch ist.
- estimated_saving_eur nur setzen, wenn eine belastbare Grobschaetzung moeglich ist; sonst null.
- required_evidence leer lassen, wenn keine besonderen Nachweise auffallen.
"""


def _strip_json_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text.strip()).strip()


def _parse_json(raw: str) -> dict[str, Any]:
    cleaned = _strip_json_fence(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM hat kein gueltiges JSON geliefert: {exc}",
        ) from exc


def _uploads_root() -> Path:
    settings = get_settings()
    return Path(settings.upload_path) / UPLOAD_SUBDIR


def _relative_upload_path(path: Path) -> str:
    return str(path.relative_to(_uploads_root().parent))


def _category_for_text(text: str) -> TipCategory:
    lowered = text.lower()
    if any(token in lowered for token in ("homeoffice", "arbeitszimmer", "remote")):
        return "homeoffice"
    if any(
        token in lowered
        for token in ("laptop", "monitor", "arbeitsmittel", "software", "headset", "buerostuhl")
    ):
        return "arbeitsmittel"
    if any(token in lowered for token in ("pendler", "fahrt", "kilometer", "bahncard", "zug")):
        return "pendeln"
    if any(token in lowered for token in ("weiterbildung", "fortbildung", "seminar", "fachbuch", "coaching")):
        return "weiterbildung"
    if any(token in lowered for token in ("spende", "kirchensteuer", "sonderausgabe", "ausbildungskosten")):
        return "sonderausgaben"
    if any(token in lowered for token in ("riester", "rente", "bu", "haftpflicht", "versicherung", "vorsorge")):
        return "vorsorge"
    if any(token in lowered for token in ("handwerker", "haushaltsnah", "putzhilfe", "garten", "reinigungskraft")):
        return "haushaltsnahe_dienstleistungen"
    if any(token in lowered for token in ("kind", "kita", "betreuung", "familie", "eltern")):
        return "kinder/familie"
    if any(token in lowered for token in ("aktie", "depot", "krypto", "kapital", "dividende")):
        return "kapital"
    if any(token in lowered for token in ("betrieb", "selbststaendig", "rechnung", "unternehmer", "gmbh")):
        return "betriebsausgaben"
    return "other"


def _bucket_for_category(category: TipCategory) -> ReturnBucket:
    if category in {"arbeitsmittel", "homeoffice", "pendeln", "weiterbildung"}:
        return "anlage_n"
    if category == "betriebsausgaben":
        return "betriebsausgaben"
    if category == "sonderausgaben":
        return "sonderausgaben"
    if category == "vorsorge":
        return "vorsorge"
    if category == "haushaltsnahe_dienstleistungen":
        return "haushaltsnahe_dienstleistungen"
    if category == "kinder/familie":
        return "kinder/familie"
    if category == "kapital":
        return "kapital"
    return "other"


def _follow_up_prompts(category: TipCategory) -> list[str]:
    if category == "homeoffice":
        return [
            "Wie oft hast du im Steuerjahr tatsaechlich im Homeoffice gearbeitet?",
            "Gibt es dazu Nachweise oder war daneben ein anderes Buero verfuegbar?",
        ]
    if category == "arbeitsmittel":
        return [
            "Welche konkreten Arbeitsmittel hast du gekauft und in welcher Hoehe?",
            "Wurden die Gegenstaende beruflich genutzt und sind Kaufbelege vorhanden?",
        ]
    if category == "pendeln":
        return [
            "Wie viele Wege zur ersten Taetigkeitsstaette hattest du im Jahr ungefaehr?",
            "Mit welchem Verkehrsmittel bist du gefahren und sind die Entfernungen bekannt?",
        ]
    if category == "weiterbildung":
        return [
            "Welche Weiterbildung oder welches Fachmaterial betrifft der Tipp konkret?",
            "Hast du Rechnungen oder Teilnahme-Nachweise fuer diese Kosten?",
        ]
    if category == "sonderausgaben":
        return [
            "Welche Zahlung oder welcher Vertrag steht hinter diesem Tipp?",
            "Liegt dir dazu ein Jahresnachweis oder eine Rechnung vor?",
        ]
    if category == "vorsorge":
        return [
            "Welche Vorsorge- oder Versicherungsbeitraege betreffen den Tipp konkret?",
            "Sind die gezahlten Beitraege und Jahresbescheinigungen verfuegbar?",
        ]
    if category == "haushaltsnahe_dienstleistungen":
        return [
            "Welche Leistung wurde in deinem Haushalt tatsaechlich beauftragt?",
            "Liegen Rechnung und unbare Zahlung fuer diese Leistung vor?",
        ]
    if category == "kinder/familie":
        return [
            "Welche Kinder- oder Familienkonstellation betrifft der Tipp in deinem Fall?",
            "Welche Zahlungen oder Betreuungsnachweise kannst du dazu belegen?",
        ]
    if category == "kapital":
        return [
            "Welche Kapitalertraege oder Depotkosten betrifft der Tipp konkret?",
            "Sind Steuerbescheinigung oder Transaktionsdaten vorhanden?",
        ]
    if category == "betriebsausgaben":
        return [
            "Welche betriebliche Ausgabe oder Unternehmer-Situation steckt hinter dem Tipp?",
            "Gibt es Rechnungen, Vertrage oder sonstige Nachweise fuer den Aufwand?",
        ]
    return [
        "Wie genau trifft dieser Tipp auf deinen Fall zu?",
        "Welche Belege, Betraege oder Vertrage kannst du dazu vorlegen?",
    ]


def _claim_questions(category: TipCategory) -> list[InstagramFollowUpQuestion]:
    return [
        InstagramFollowUpQuestion(id=str(uuid.uuid4()), prompt=prompt)
        for prompt in _follow_up_prompts(category)
    ]


def _tip_title(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= 72:
        return normalized
    return normalized[:69].rstrip() + "..."


def _summary_lines_from_prep_items(items: list[TaxPrepItem]) -> str:
    total = sum(item.estimated_saving_eur or 0 for item in items)
    lines = [
        "## Instagram-Check: uebernommene Steuerchancen",
        "",
        f"**Bestaetigte Tipps:** {len(items)}",
        f"**Geschaetzte Gesamtersparnis:** {total:,} EUR".replace(",", "."),
        "",
    ]
    for item in items:
        amount = (
            f"ca. {(item.estimated_saving_eur or 0):,} EUR".replace(",", ".")
            if item.estimated_saving_eur is not None
            else "derzeit nicht belastbar quantifiziert"
        )
        lines.append(f"- **{item.title}:** {amount} - {item.summary}")
    lines.extend(
        [
            "",
            "Diese uebernommenen Tipps sind als vorbereitete Steuerchancen in der Session gespeichert.",
        ]
    )
    return "\n".join(lines)


def _summary_risk() -> RiskBadgeChunk:
    return RiskBadgeChunk(
        level="low",
        label="Vorpruefung uebernommen",
        explanation="Nur als gruene und bestaetigte Instagram-Tipps uebernommene Steuerchancen.",
    )


def _message_saving(items: list[TaxPrepItem]) -> int:
    return sum(item.estimated_saving_eur or 0 for item in items)


def _validate_images(images: list[UploadFile]) -> None:
    if not images:
        raise HTTPException(status_code=422, detail="Mindestens ein Bild ist erforderlich.")
    if len(images) > 10:
        raise HTTPException(status_code=422, detail="Maximal 10 Bilder pro Upload.")
    for image in images:
        if image.content_type not in _VALID_IMAGE_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Nicht unterstuetzter Bildtyp: {image.content_type or 'unbekannt'}",
            )


def _assert_vision_capable_provider() -> None:
    settings = get_settings()
    if settings.llm_provider == "anthropic":
        return
    if settings.llm_provider == "ollama":
        model = settings.ollama_model.lower()
        if any(marker in model for marker in _OLLAMA_MULTIMODAL_MARKERS):
            return
        raise HTTPException(
            status_code=422,
            detail=(
                "Der konfigurierte Ollama-Modelname wirkt nicht multimodal. "
                "Bitte ein Vision-faehiges Modell konfigurieren."
            ),
        )
    raise HTTPException(
        status_code=422,
        detail="Der konfigurierte LLM-Provider unterstuetzt den Bild-Check nicht.",
    )


async def _store_images(session_id: str, images: list[UploadFile]) -> list[InstagramImageRef]:
    root = _uploads_root() / session_id
    root.mkdir(parents=True, exist_ok=True)
    stored: list[InstagramImageRef] = []
    for image in images:
        suffix = Path(image.filename or "upload").suffix.lower() or ".bin"
        image_id = str(uuid.uuid4())
        filename = f"{image_id}{suffix}"
        target = root / filename
        data = await image.read()
        target.write_bytes(data)
        stored.append(
            InstagramImageRef(
                id=image_id,
                original_filename=image.filename or filename,
                stored_path=_relative_upload_path(target),
                content_type=image.content_type or "application/octet-stream",
                size_bytes=len(data),
            )
        )
    return stored


def _delete_stored_images(images: list[InstagramImageRef]) -> None:
    for image in images:
        path = _uploads_root().parent / image.stored_path
        if path.exists():
            path.unlink()
    session_dirs = {(_uploads_root().parent / image.stored_path).parent for image in images}
    for session_dir in session_dirs:
        if session_dir.exists() and not any(session_dir.iterdir()):
            session_dir.rmdir()


def _image_media_type(content_type: str) -> str:
    if content_type in _VALID_IMAGE_TYPES:
        return "image/jpeg" if content_type == "image/jpg" else content_type
    return "image/png"


async def _extract_claim_texts_anthropic(images: list[InstagramImageRef]) -> list[str]:
    settings = get_settings()
    client = AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        default_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
    )
    content: list[dict[str, Any]] = [{"type": "text", "text": _CLAIM_ANALYSIS_PROMPT}]
    for image in images:
        image_path = _uploads_root().parent / image.stored_path
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": _image_media_type(image.content_type),
                    "data": base64.b64encode(image_path.read_bytes()).decode("ascii"),
                },
            }
        )

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=cast(Any, [{"role": "user", "content": content}]),
    )
    text_parts: list[str] = []
    for block in response.content:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            text_parts.append(text)
    data = _parse_json("\n".join(text_parts))
    return [str(item.get("text", "")).strip() for item in data.get("claims", []) if str(item.get("text", "")).strip()]


async def _extract_claim_texts_ollama(images: list[InstagramImageRef]) -> list[str]:
    settings = get_settings()
    client = OllamaAsyncClient(host=settings.ollama_base_url)
    encoded_images = [
        base64.b64encode((_uploads_root().parent / image.stored_path).read_bytes()).decode("ascii")
        for image in images
    ]
    response = await client.chat(
        model=settings.ollama_model,
        format="json",
        messages=[
            {
                "role": "user",
                "content": _CLAIM_ANALYSIS_PROMPT,
                "images": encoded_images,
            }
        ],
    )
    raw = response["message"]["content"] if isinstance(response, dict) else response.message.content
    data = _parse_json(raw or "")
    return [str(item.get("text", "")).strip() for item in data.get("claims", []) if str(item.get("text", "")).strip()]


async def extract_claim_texts(images: list[InstagramImageRef]) -> list[str]:
    _assert_vision_capable_provider()
    settings = get_settings()
    if settings.llm_provider == "anthropic":
        return await _extract_claim_texts_anthropic(images)
    return await _extract_claim_texts_ollama(images)


def _fallback_claims(images: list[InstagramImageRef]) -> list[str]:
    claims: list[str] = []
    for image in images:
        stem = Path(image.original_filename).stem.replace("-", " ").replace("_", " ")
        if stem.strip():
            claims.append(f"Steuertipp aus Screenshot: {stem.strip()}")
    return claims or ["Pruefe, ob der dargestellte Steuertipp fuer den Nutzerfall nutzbar ist."]


def _prepare_claims(raw_claims: list[str]) -> list[InstagramClaim]:
    seen: set[str] = set()
    prepared: list[InstagramClaim] = []
    for raw in raw_claims:
        normalized = re.sub(r"\s+", " ", raw).strip(" -•\n\t")
        if not normalized:
            continue
        if len(normalized) > 1000:
            normalized = normalized[:1000].rstrip()
        dedupe_key = normalized.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        category = _category_for_text(normalized)
        prepared.append(
            InstagramClaim(
                id=str(uuid.uuid4()),
                raw_text=normalized,
                edited_text=normalized,
                category=category,
                return_bucket=_bucket_for_category(category),
                follow_up_questions=_claim_questions(category),
            )
        )
    if prepared:
        return prepared

    fallback = "Kein klarer Tipp extrahiert - bitte Screenshot oder Tipptext pruefen."
    category = _category_for_text(fallback)
    return [
        InstagramClaim(
            id=str(uuid.uuid4()),
            raw_text=fallback,
            edited_text=fallback,
            category=category,
            return_bucket=_bucket_for_category(category),
            follow_up_questions=_claim_questions(category),
        )
    ]


def _build_law_context(nodes: list[Any]) -> str:
    if not nodes:
        return "(Kein Retrieval-Kontext verfuegbar)"
    parts: list[str] = []
    for node in nodes[:4]:
        meta = node.node.metadata
        law = str(meta.get("law", ""))
        paragraph = str(meta.get("paragraph", ""))
        section = str(meta.get("section", ""))
        title = " ".join(part for part in (law, paragraph, section) if part).strip()
        header = f"[{title}]" if title else "[Rechtsquelle]"
        parts.append(f"{header}\n{node.node.get_content()}")
    return "\n\n".join(parts)


def _nodes_to_sources(nodes: list[Any]) -> list[IdeaTransferSource]:
    sources: list[IdeaTransferSource] = []
    seen: set[tuple[str, str, str]] = set()
    for node in nodes[:4]:
        meta = node.node.metadata
        law = str(meta.get("law", ""))
        paragraph = str(meta.get("paragraph", ""))
        section = str(meta.get("section", ""))
        if not law or not paragraph:
            continue
        key = (law, paragraph, section)
        if key in seen:
            continue
        seen.add(key)
        url = meta.get("url")
        sources.append(
            IdeaTransferSource(
                law=law,
                paragraph=paragraph,
                section=section,
                text=node.node.get_content(),
                url=str(url) if isinstance(url, str) else None,
            )
        )
    return sources


def _retrieve_nodes(query: str, year: int) -> list[Any]:
    settings = get_settings()
    if not has_indexed_data(settings.chroma_path):
        return []
    try:
        from app.retriever import HybridRetriever

        client = chromadb.PersistentClient(path=settings.chroma_path)
        collection = client.get_or_create_collection(COLLECTION_NAME)
        index = get_index(settings.chroma_path)
        retriever = HybridRetriever(index=index, chroma_collection=collection, year=year)
        return retriever.retrieve(QueryBundle(query_str=query))
    except Exception as exc:
        logger.warning("Instagram check retrieval failed: %s", exc)
        return []


def _answers_text(claim: InstagramClaim) -> str:
    answered = [
        f"- {question.prompt}\n  Antwort: {question.answer.strip()}"
        for question in claim.follow_up_questions
        if question.answer and question.answer.strip()
    ]
    return "\n".join(answered) if answered else "- Keine Antworten erfasst."


async def _evaluate_claim(claim: InstagramClaim, tax_year: int) -> InstagramEvaluatedTip:
    query = f"{claim.edited_text} {_answers_text(claim)}"
    nodes = _retrieve_nodes(query, tax_year)
    law_context = _build_law_context(nodes)

    llm = get_llm()
    response = await llm.achat(
        [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=(
                    "Du bewertest Steuertipps fuer deutsche Steuererklaerungen. "
                    "Antworte nur mit JSON."
                ),
            ),
            ChatMessage(
                role=MessageRole.USER,
                content=_EVALUATION_PROMPT.format(
                    tax_year=tax_year,
                    tip_text=claim.edited_text,
                    category=claim.category,
                    return_bucket=claim.return_bucket,
                    answers_text=_answers_text(claim),
                    law_context=law_context,
                ),
            ),
        ]
    )
    data = _parse_json(response.message.content or "")
    category = str(data.get("category", claim.category))
    if category not in _TIP_CATEGORIES:
        category = claim.category
    return_bucket = str(data.get("return_bucket", claim.return_bucket))
    if return_bucket not in _RETURN_BUCKETS:
        return_bucket = claim.return_bucket
    traffic_light = str(data.get("traffic_light", "yellow"))
    if traffic_light not in {"green", "yellow", "red"}:
        traffic_light = "yellow"
    estimate = data.get("estimated_saving_eur")
    estimated_saving_eur = int(estimate) if isinstance(estimate, (int, float)) else None
    if estimated_saving_eur is not None and estimated_saving_eur < 0:
        estimated_saving_eur = None
    required_evidence = [
        str(item).strip()
        for item in data.get("required_evidence", [])
        if str(item).strip()
    ]

    return InstagramEvaluatedTip(
        claim_id=claim.id,
        title=_tip_title(str(data.get("title", claim.edited_text)).strip() or claim.edited_text),
        normalized_tip=str(data.get("normalized_tip", claim.edited_text)).strip() or claim.edited_text,
        category=category,  # type: ignore[arg-type]
        return_bucket=return_bucket,  # type: ignore[arg-type]
        traffic_light=traffic_light,  # type: ignore[arg-type]
        explanation=str(data.get("explanation", "")).strip() or "Keine belastbare Einordnung geliefert.",
        estimated_saving_eur=estimated_saving_eur,
        required_evidence=required_evidence,
        sources=_nodes_to_sources(nodes),
    )


async def ensure_instagram_session(db: aiosqlite.Connection, session_id: str) -> None:
    now = utc_now()
    await db.execute(
        """
        INSERT INTO sessions (id, title, created_at, updated_at, message_count, total_saving)
        VALUES (?, ?, ?, ?, 0, 0)
        ON CONFLICT(id) DO NOTHING
        """,
        (session_id, INSTAGRAM_CHECK_TITLE, now, now),
    )
    await db.execute(
        """
        UPDATE sessions
        SET title = CASE
              WHEN message_count = 0 OR title = ?
              THEN ?
              ELSE title
            END,
            updated_at = ?
        WHERE id = ?
        """,
        (INSTAGRAM_CHECK_TITLE, INSTAGRAM_CHECK_TITLE, now, session_id),
    )
    await db.commit()


def _row_to_check(row: aiosqlite.Row) -> InstagramPostCheck:
    return InstagramPostCheck(
        session_id=row["session_id"],
        status=row["status"],
        images=[InstagramImageRef.model_validate(item) for item in json.loads(row["images_json"])],
        claims=[InstagramClaim.model_validate(item) for item in json.loads(row["claims_json"])],
        evaluated_tips=(
            [InstagramEvaluatedTip.model_validate(item) for item in json.loads(row["evaluated_tips_json"])]
            if row["evaluated_tips_json"]
            else None
        ),
        updated_at=parse_timestamp(row["updated_at"]),
    )


def _row_to_tax_prep_item(row: aiosqlite.Row) -> TaxPrepItem:
    return TaxPrepItem(
        id=row["id"],
        session_id=row["session_id"],
        source=row["source"],
        source_claim_id=row["source_claim_id"],
        title=row["title"],
        category=row["category"],
        return_bucket=row["return_bucket"],
        estimated_saving_eur=row["estimated_saving_eur"],
        risk_level=row["risk_level"],
        required_evidence=json.loads(row["required_evidence_json"]),
        summary=row["summary"],
        status=row["status"],
        created_at=parse_timestamp(row["created_at"]),
        updated_at=parse_timestamp(row["updated_at"]),
    )


async def get_instagram_check(
    db: aiosqlite.Connection, session_id: str
) -> InstagramPostCheck | None:
    async with db.execute(
        "SELECT * FROM instagram_post_checks WHERE session_id = ?",
        (session_id,),
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    return _row_to_check(row)


async def get_tax_prep_items(
    db: aiosqlite.Connection, session_id: str
) -> list[TaxPrepItem]:
    async with db.execute(
        """
        SELECT * FROM tax_prep_items
        WHERE session_id = ?
        ORDER BY created_at DESC
        """,
        (session_id,),
    ) as cursor:
        rows = await cursor.fetchall()
    return [_row_to_tax_prep_item(row) for row in rows]


async def _upsert_check(
    db: aiosqlite.Connection,
    session_id: str,
    status: InstagramCheckStatus,
    images: list[InstagramImageRef],
    claims: list[InstagramClaim],
    evaluated_tips: list[InstagramEvaluatedTip] | None,
) -> InstagramPostCheck:
    now = utc_now()
    existing = await get_instagram_check(db, session_id)
    summary_message_id: str | None = None
    if existing is not None:
        async with db.execute(
            "SELECT summary_message_id FROM instagram_post_checks WHERE session_id = ?",
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()
        summary_message_id = row["summary_message_id"] if row else None

    await db.execute(
        """
        INSERT INTO instagram_post_checks
          (session_id, status, images_json, claims_json, evaluated_tips_json, summary_message_id, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
          status = excluded.status,
          images_json = excluded.images_json,
          claims_json = excluded.claims_json,
          evaluated_tips_json = excluded.evaluated_tips_json,
          summary_message_id = COALESCE(instagram_post_checks.summary_message_id, excluded.summary_message_id),
          updated_at = excluded.updated_at
        """,
        (
            session_id,
            status,
            json.dumps([image.model_dump() for image in images]),
            json.dumps([claim.model_dump() for claim in claims]),
            json.dumps([tip.model_dump() for tip in evaluated_tips]) if evaluated_tips is not None else None,
            summary_message_id,
            now,
        ),
    )
    await db.commit()
    reloaded = await get_instagram_check(db, session_id)
    if reloaded is None:
        raise RuntimeError("Instagram check could not be reloaded after save.")
    return reloaded


async def _upsert_tax_prep_items(
    db: aiosqlite.Connection,
    session_id: str,
    tips: list[InstagramEvaluatedTip],
) -> list[TaxPrepItem]:
    created_at = utc_now()
    for tip in tips:
        await db.execute(
            """
            INSERT INTO tax_prep_items
              (id, session_id, source, source_claim_id, title, category, return_bucket,
               estimated_saving_eur, risk_level, required_evidence_json, summary, status, created_at, updated_at)
            VALUES (?, ?, 'instagram_post', ?, ?, ?, ?, ?, 'low', ?, ?, 'confirmed', ?, ?)
            ON CONFLICT(session_id, source, source_claim_id) DO UPDATE SET
              title = excluded.title,
              category = excluded.category,
              return_bucket = excluded.return_bucket,
              estimated_saving_eur = excluded.estimated_saving_eur,
              risk_level = excluded.risk_level,
              required_evidence_json = excluded.required_evidence_json,
              summary = excluded.summary,
              updated_at = excluded.updated_at
            """,
            (
                str(uuid.uuid4()),
                session_id,
                tip.claim_id,
                tip.title,
                tip.category,
                tip.return_bucket,
                tip.estimated_saving_eur,
                json.dumps(tip.required_evidence),
                tip.explanation,
                created_at,
                created_at,
            ),
        )
    await db.commit()
    return await get_tax_prep_items(db, session_id)


async def _upsert_summary_message(
    db: aiosqlite.Connection,
    session_id: str,
    prep_items: list[TaxPrepItem],
) -> None:
    if not prep_items:
        return
    summary = _summary_lines_from_prep_items(prep_items)
    risk_json = _summary_risk().model_dump_json()
    sources_json = json.dumps([])
    saving_amount = _message_saving(prep_items)
    now = utc_now()

    async with db.execute(
        "SELECT summary_message_id FROM instagram_post_checks WHERE session_id = ?",
        (session_id,),
    ) as cursor:
        row = await cursor.fetchone()

    summary_message_id = row["summary_message_id"] if row else None
    if summary_message_id:
        async with db.execute(
            "SELECT saving_amount FROM messages WHERE id = ?",
            (summary_message_id,),
        ) as cursor:
            existing = await cursor.fetchone()
        previous_saving = existing["saving_amount"] if existing else 0
        if existing:
            await db.execute(
                """
                UPDATE messages
                SET content = ?, sources = ?, risk_badge = ?, saving_amount = ?, created_at = ?
                WHERE id = ?
                """,
                (
                    summary,
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
                    saving_amount,
                    previous_saving or 0,
                    saving_amount,
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
            summary,
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
        (saving_amount, now, session_id),
    )
    await db.execute(
        """
        UPDATE instagram_post_checks
        SET summary_message_id = ?
        WHERE session_id = ?
        """,
        (summary_message_id, session_id),
    )
    await db.commit()


async def analyze_instagram_images(
    db: aiosqlite.Connection,
    session_id: str,
    images: list[UploadFile],
) -> InstagramPostCheck:
    _validate_images(images)
    await ensure_instagram_session(db, session_id)
    existing = await get_instagram_check(db, session_id)
    if existing is not None:
        _delete_stored_images(existing.images)

    stored_images = await _store_images(session_id, images)
    try:
        raw_claims = await extract_claim_texts(stored_images)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Vision extraction failed, using fallback claims: %s", exc)
        raw_claims = _fallback_claims(stored_images)

    claims = _prepare_claims(raw_claims)
    return await _upsert_check(
        db=db,
        session_id=session_id,
        status="draft",
        images=stored_images,
        claims=claims,
        evaluated_tips=None,
    )


async def save_instagram_check(
    db: aiosqlite.Connection,
    session_id: str,
    body: InstagramCheckSaveRequest,
) -> InstagramPostCheck:
    existing = await get_instagram_check(db, session_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Instagram-Check nicht gefunden")

    existing_by_id = {claim.id: claim for claim in existing.claims}
    claims: list[InstagramClaim] = []
    for claim_update in body.claims:
        original = existing_by_id.get(claim_update.id)
        if original is None:
            raise HTTPException(
                status_code=422,
                detail=f"Unbekannter Claim im Instagram-Check: {claim_update.id}",
            )
        claims.append(
            InstagramClaim(
                id=claim_update.id,
                raw_text=original.raw_text,
                edited_text=claim_update.edited_text,
                category=claim_update.category,
                return_bucket=claim_update.return_bucket,
                status=claim_update.status,
                selected_for_import=claim_update.selected_for_import,
                follow_up_questions=claim_update.follow_up_questions,
            )
        )
    return await _upsert_check(
        db=db,
        session_id=session_id,
        status="draft",
        images=existing.images,
        claims=claims,
        evaluated_tips=None,
    )


async def evaluate_instagram_check(
    db: aiosqlite.Connection,
    session_id: str,
    tax_year: int,
) -> InstagramPostCheck:
    existing = await get_instagram_check(db, session_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Instagram-Check nicht gefunden")

    active_claims = [claim for claim in existing.claims if claim.status == "active"]
    evaluated_tips: list[InstagramEvaluatedTip] = []
    for claim in active_claims:
        evaluated_tips.append(await _evaluate_claim(claim, tax_year))

    await _upsert_check(
        db=db,
        session_id=session_id,
        status="evaluated",
        images=existing.images,
        claims=existing.claims,
        evaluated_tips=evaluated_tips,
    )

    selected_green = [
        tip
        for tip in evaluated_tips
        if next(
            (
                claim.selected_for_import
                for claim in existing.claims
                if claim.id == tip.claim_id
            ),
            False,
        )
        and tip.traffic_light == "green"
    ]
    if selected_green:
        prep_items = await _upsert_tax_prep_items(db, session_id, selected_green)
        await _upsert_summary_message(db, session_id, prep_items)

    reloaded = await get_instagram_check(db, session_id)
    if reloaded is None:
        raise RuntimeError("Instagram-Check konnte nach Bewertung nicht geladen werden.")
    return reloaded
