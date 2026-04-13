import asyncio
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.chat import (
    ChatRequest,
    DoneChunk,
    ErrorChunk,
    RiskBadgeChunk,
    SavingChunk,
    SourceChunk,
    StreamChunk,
    TextChunk,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# ─── Dummy content (replaced by LlamaIndex + Claude in Phase 11) ─────────────

_DUMMY_ANSWER = (
    "Ja, Homeoffice-Kosten können Sie steuerlich geltend machen. "
    "Seit 2023 gilt die erhöhte Tagespauschale von **6 € pro Tag** "
    "(max. **1.260 € im Jahr**, also 210 Tage).\n\n"
    "Alternativ können Sie ein häusliches Arbeitszimmer absetzen, "
    "wenn es ausschließlich beruflich genutzt wird — dann sind die "
    "tatsächlichen anteiligen Kosten absetzbar, was bei größeren "
    "Wohnungen deutlich mehr einbringen kann.\n\n"
    "Haben Sie auch Arbeitsmittel wie Laptop, Monitor oder Bürostuhl gekauft?"
)

_DUMMY_SOURCE = SourceChunk(
    law="EStG",
    paragraph="§ 4",
    section="Abs. 5 Nr. 6b",
    text=(
        "Für jeden Kalendertag, an dem der Steuerpflichtige seine betriebliche "
        "oder berufliche Tätigkeit ausschließlich in der häuslichen Wohnung ausübt, "
        "kann er einen Betrag von 6 Euro abziehen, höchstens 1 260 Euro im "
        "Wirtschafts- oder Kalenderjahr."
    ),
)

_DUMMY_RISK = RiskBadgeChunk(
    level="low",
    label="Unstreitig",
    explanation="Seit 2023 gesetzlich klar geregelt in § 4 Abs. 5 Nr. 6b EStG.",
)

_DUMMY_SAVING = SavingChunk(amount=252)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _sse(chunk: StreamChunk) -> str:
    """Serialize a chunk as an SSE data line."""
    return f"data: {chunk.model_dump_json()}\n\n"


# ─── Generator ───────────────────────────────────────────────────────────────


async def _stream_chat(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Async generator that yields SSE-formatted strings.

    Event sequence:
      text  (one per word, 35 ms apart)  →  source  →  risk_badge  →  saving  →  done
      error  (only on exception)
    """
    try:
        words = _DUMMY_ANSWER.split(" ")
        for i, word in enumerate(words):
            # Re-add the space that split() removed (except after the last word)
            content = word if i == len(words) - 1 else word + " "
            yield _sse(TextChunk(content=content))
            await asyncio.sleep(0.035)

        yield _sse(_DUMMY_SOURCE)
        yield _sse(_DUMMY_RISK)
        yield _sse(_DUMMY_SAVING)
        yield _sse(DoneChunk())

    except Exception as exc:
        logger.exception("Error in chat stream")
        yield _sse(ErrorChunk(message=str(exc)))


# ─── Endpoint ─────────────────────────────────────────────────────────────────


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """
    Stream a tax-advice response as Server-Sent Events.

    Each event is a JSON object on a `data:` line, with a `type` discriminator:
    - `text`       — partial assistant text
    - `source`     — law citation
    - `risk_badge` — legal certainty badge
    - `saving`     — estimated tax saving in EUR
    - `done`       — stream finished
    - `error`      — unrecoverable error
    """
    return StreamingResponse(
        _stream_chat(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # prevent nginx from buffering the stream
        },
    )
