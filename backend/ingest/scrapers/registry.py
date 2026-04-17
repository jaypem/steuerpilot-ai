"""
Registry of all external sources that require annual URL checks.

Each entry carries a name, the current URL, the year it was last verified,
and a note explaining where to find the new version when the URL changes.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalSource:
    key: str
    name: str
    url: str
    verified_year: int
    update_hint: str


# ─── Registry ─────────────────────────────────────────────────────────────────

_SOURCES: list[ExternalSource] = [
    ExternalSource(
        key="BFH",
        name="BFH-Urteile (kuratierte Auswahl, ~20 Urteile)",
        url="https://www.bundesfinanzhof.de/entscheidungen/entscheidungen-online/",
        verified_year=2025,
        update_hint=(
            "Einzelne Urteil-URLs in ingest/scrapers/bfh_catalog.py pflegen. "
            "bundesfinanzhof.de → Entscheidungen online → Az. oder Thema suchen. "
            "BStBl-Status prüfen: wenn aufgenommen → bstbl_aufgenommen=True setzen. "
            "URL-Muster: /en/entscheidungen/entscheidungen-online/decision-detail/STRE.../"
        ),
    ),
    ExternalSource(
        key="LStR",
        name="Lohnsteuer-Richtlinien",
        url="https://www.bundesfinanzministerium.de/Content/DE/Downloads/Steuern/Steuerarten/Lohnsteuer/Lohnsteuer-Richtlinien/2023-10-06-lohnsteuer-richtlinien-2023.pdf?__blob=publicationFile&v=3",
        verified_year=2023,
        update_hint=(
            "Bundesfinanzministerium → Steuern → Steuerarten → Lohnsteuer → "
            "Lohnsteuer-Richtlinien. Suche nach 'LStR <Jahr>'. "
            "URL-Muster: lohnsteuer-richtlinien-<YYYY>.pdf"
        ),
    ),
    ExternalSource(
        key="BMF",
        name="BMF-Schreiben (kuratierte Auswahl, ~20 Schreiben)",
        url="https://www.bundesfinanzministerium.de/Web/DE/Service/BMF_Schreiben/bmf_schreiben.html",
        verified_year=2025,
        update_hint=(
            "Einzelne PDF-URLs in ingest/scrapers/bmf_catalog.py pflegen. "
            "Bundesfinanzministerium → Service → BMF-Schreiben-Suche (nach Thema filtern). "
            "Neue Schreiben: BmfSchreiben-Eintrag hinzufügen, veraltete auf superseded=True setzen."
        ),
    ),
]


def all_sources() -> list[ExternalSource]:
    """Return all registered external sources."""
    return list(_SOURCES)


def get_source(key: str) -> ExternalSource:
    """Look up a source by key (e.g. 'LStR'). Raises KeyError if not found."""
    for src in _SOURCES:
        if src.key == key:
            return src
    raise KeyError(f"Unknown source key: {key!r}. Available: {[s.key for s in _SOURCES]}")
