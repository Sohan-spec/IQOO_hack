from __future__ import annotations

from datetime import timedelta

from app.models import PendingEntry, parse_amount, utcnow
from app.queue import TransactionQueue
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


def test_expire_due_marks_stale_pending_only() -> None:
    import asyncio

    queue = TransactionQueue()
    stale = _entry()
    stale.session_id = "stale"
    stale.created_at = utcnow() - timedelta(minutes=6)
    fresh = _entry()
    fresh.session_id = "fresh"
    confirmed = _entry(CONFIRMED)
    confirmed.session_id = "done"
    confirmed.created_at = utcnow() - timedelta(minutes=6)

    async def _run() -> None:
        await queue.enqueue(stale)
        await queue.enqueue(fresh)
        await queue.enqueue(confirmed)
        expired = await queue.expire_due(utcnow(), timedelta(minutes=5))
        assert [e.session_id for e in expired] == ["stale"]
        assert queue.get_unlocked("stale").status == EXPIRED
        assert queue.get_unlocked("fresh").status == PENDING
        assert queue.get_unlocked("done").status == CONFIRMED

    asyncio.run(_run())

