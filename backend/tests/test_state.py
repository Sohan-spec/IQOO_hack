from __future__ import annotations

from datetime import timedelta

from app.models import PendingEntry, parse_amount, utcnow
from app.state import CONFIRMED, EXPIRED, PENDING, mark_confirmed, mark_expired


def _entry(status: str = PENDING) -> PendingEntry:
    return PendingEntry(
        session_id="s1",
        customer_name="Priya",
        amount=parse_amount("10.00"),
        created_at=utcnow() - timedelta(seconds=1),
        status=status,
        callback_url="http://storefront/confirm",
    )


def test_pending_to_confirmed() -> None:
    entry = _entry()
    assert mark_confirmed(entry) is True
    assert entry.status == CONFIRMED
    assert mark_confirmed(entry) is False


def test_pending_to_expired() -> None:
    entry = _entry()
    assert mark_expired(entry) is True
    assert entry.status == EXPIRED
    assert mark_confirmed(entry) is False


def test_confirmed_does_not_expire() -> None:
    entry = _entry(CONFIRMED)
    assert mark_expired(entry) is False
    assert entry.status == CONFIRMED
