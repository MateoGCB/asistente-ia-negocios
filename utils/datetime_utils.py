from datetime import datetime, timezone

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def to_utc(value: datetime) -> datetime:
    """Normalize any datetime to an aware datetime in UTC.

    SQLite gives datetimes back without timezone (naive). In this project every stored
    datetime is written in UTC, so a naive value is interpreted as UTC. An aware value
    in another timezone is converted. Use this on BOTH sides of every date comparison.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
