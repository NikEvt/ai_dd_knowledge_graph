from datetime import UTC, datetime

_frozen: datetime | None = None


def now() -> datetime:
    return _frozen or datetime.now(UTC)


def freeze(at: datetime | None) -> None:
    global _frozen
    _frozen = at
