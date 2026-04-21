"""
HyDE (Hypothetical Document Embeddings) query expansion.

Generates a short hypothetical tax-law answer for the user query and
prepends it to the query string before embedding. This moves the query
vector closer to real document vectors in the Chroma index.
"""

import logging

from llama_index.core.llms import LLM

logger = logging.getLogger(__name__)

_HYDE_PROMPT = """\
Schreibe einen kurzen deutschen Steuerrechts-Textabschnitt (max. 3 Sätze), \
der die folgende Frage beantwortet. Nenne konkrete Paragraphen wo möglich. \
Antworte nur mit dem Textabschnitt, ohne Einleitung.

Frage: {query}

Antwort:"""


async def expand_query(query: str, llm: LLM) -> str:
    """Return query + hypothetical answer for better embedding recall."""
    try:
        response = await llm.acomplete(_HYDE_PROMPT.format(query=query))
        hypothesis = response.text.strip()
        if hypothesis:
            logger.debug("HyDE hypothesis: %s", hypothesis[:120])
            return f"{query}\n\n{hypothesis}"
    except Exception as exc:
        logger.warning("HyDE expansion failed (%s) — using original query.", exc)
    return query
