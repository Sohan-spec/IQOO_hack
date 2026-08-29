from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.matcher import select_candidate
from app.models import CreditEvent, PendingEntry
from app.state import CONFIRMED, EXPIRED, PENDING

NOW = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
WINDOW = timedelta(minutes=5)


def _entry(
    session_id: str,
    amount: str,
    name: str = "Priya Sharma",
    status: str = PENDING,
    age: timedelta = timedelta(seconds=10),
) -> PendingEntry:
    return PendingEntry(
        session_id=session_id,
        customer_name=name,
        amount=Decimal(amount),
        created_at=NOW - age,
        status=status,
        callback_url="http://storefront/confirm",
    )


def _credit(amount: str, name: str = "PRIYA SHARMA") -> CreditEvent:
    return CreditEvent(
        package="com.phonepe.app",
        title="Payment received",
        text=f"You have received Rs. {amount} from {name}",
        amount=Decimal(amount),
        payer_name=name,
        posted_at=NOW,
    )


def test_step0_skips_confirmed_and_expired() -> None:
    entries = [
        _entry("done", "150.00", status=CONFIRMED),
        _entry("old", "150.00", status=EXPIRED),
        _entry("live", "150.00", status=PENDING),
    ]
    winner = select_candidate(entries, _credit("150.00"), NOW, WINDOW)
    assert winner is not None
    assert winner.session_id == "live"


def test_amount_is_primary_key() -> None:
    entries = [_entry("a", "150.00"), _entry("b", "200.00")]
    winner = select_candidate(entries, _credit("200.00"), NOW, WINDOW)
    assert winner is not None
    assert winner.session_id == "b"


def test_time_window_drops_stale() -> None:
    entries = [_entry("stale", "150.00", age=timedelta(minutes=6))]
    assert select_candidate(entries, _credit("150.00"), NOW, WINDOW) is None


def test_name_disambiguates_when_multiple_amount_matches() -> None:
    entries = [
        _entry("older", "150.00", name="Other Person", age=timedelta(seconds=30)),
        _entry("named", "150.00", name="Priya Sharma", age=timedelta(seconds=10)),
    ]
    winner = select_candidate(entries, _credit("150.00", "Priya Sharma"), NOW, WINDOW)
    assert winner is not None
    assert winner.session_id == "named"


def test_single_amount_match_does_not_require_name() -> None:
    entries = [_entry("only", "150.00", name="Typed Checkout Name")]
    winner = select_candidate(entries, _credit("150.00", "BANK REGISTERED NAME"), NOW, WINDOW)
    assert winner is not None
    assert winner.session_id == "only"


def test_oldest_first_when_name_does_not_help() -> None:
    entries = [
        _entry("newer", "150.00", name="A", age=timedelta(seconds=5)),
        _entry("older", "150.00", name="B", age=timedelta(seconds=40)),
    ]
    winner = select_candidate(entries, _credit("150.00", "ZZZ"), NOW, WINDOW)
    assert winner is not None
    assert winner.session_id == "older"


def test_no_match_when_zero_candidates() -> None:
    entries = [_entry("a", "100.00")]
    assert select_candidate(entries, _credit("150.00"), NOW, WINDOW) is None
