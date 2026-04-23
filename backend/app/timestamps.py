from datetime import UTC, datetime


def utc_now() -> str:
    """Return an ISO timestamp with explicit UTC offset."""
    return datetime.now(UTC).isoformat()


def parse_timestamp(value: str) -> datetime:
    """
    Parse persisted timestamps as UTC-aware datetimes.

    Legacy rows may still contain naive ISO strings from older code paths.
    Those are interpreted as UTC to keep API responses consistent.
    """
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC)
