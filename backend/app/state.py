"""§8 device-side transitions: pending → confirmed | expired."""

PENDING = "pending"
CONFIRMED = "confirmed"
EXPIRED = "expired"
TERMINAL = frozenset({CONFIRMED, EXPIRED})


def mark_confirmed(entry) -> bool:
    if entry is None or entry.status != PENDING:
        return False
    entry.status = CONFIRMED
    return True


def mark_expired(entry) -> bool:
    if entry is None or entry.status != PENDING:
        return False
    entry.status = EXPIRED
    return True
