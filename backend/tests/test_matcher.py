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
    phone: str | None = None,
) -> PendingEntry:
    return PendingEntry(
        session_id=session_id,
        customer_name=name,
        amount=Decimal(amount),
        created_at=NOW - age,
        status=status,
        callback_url="http://storefront/confirm",
        customer_phone=phone,
    )


def _credit(
    amount: str,
    name: str = "PRIYA SHARMA",
    last4: str | None = None,
) -> CreditEvent:
    return CreditEvent(
        package="com.phonepe.app",
        title="Payment received",
        text=f"You have received Rs. {amount} from {name}",
        amount=Decimal(amount),
        payer_name=name,
        posted_at=NOW,
        payer_phone_last4=last4,
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


def test_last4_narrows_when_two_same_amount() -> None:
    entries = [
        _entry("typed", "349.00", name="A", phone="9876543419", age=timedelta(seconds=20)),
        _entry("payer", "349.00", name="B", phone="9876544562", age=timedelta(seconds=10)),
    ]
    winner = select_candidate(
        entries, _credit("349.00", name="", last4="4562"), NOW, WINDOW
    )
    assert winner is not None
    assert winner.session_id == "payer"


def test_last4_mismatch_does_not_block_single_candidate() -> None:
    entries = [_entry("only", "349.00", name="Typed Name", phone="9876543419")]
    winner = select_candidate(
        entries, _credit("349.00", name="", last4="4562"), NOW, WINDOW
    )
    assert winner is not None
    assert winner.session_id == "only"


def test_last4_mismatch_on_all_falls_through_to_oldest() -> None:
    entries = [
        _entry("newer", "349.00", name="A", phone="9876543419", age=timedelta(seconds=5)),
        _entry("older", "349.00", name="B", phone="9876540000", age=timedelta(seconds=40)),
    ]
    winner = select_candidate(
        entries, _credit("349.00", name="ZZZ", last4="4562"), NOW, WINDOW
    )
    assert winner is not None
    assert winner.session_id == "older"


def test_missing_last4_falls_through_to_name() -> None:
    entries = [
        _entry("other", "150.00", name="Other Person", phone="9876544562", age=timedelta(seconds=30)),
        _entry("named", "150.00", name="Priya Sharma", phone="9876543419", age=timedelta(seconds=10)),
    ]
    winner = select_candidate(entries, _credit("150.00", "Priya Sharma"), NOW, WINDOW)
    assert winner is not None
    assert winner.session_id == "named"


def test_garbage_stored_phone_does_not_crash() -> None:
    entries = [_entry("only", "150.00", phone="n/a")]
    winner = select_candidate(entries, _credit("150.00", last4="4562"), NOW, WINDOW)
    assert winner is not None
    assert winner.session_id == "only"
