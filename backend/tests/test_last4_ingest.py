from __future__ import annotations

import asyncio

from app.confirm import ConfirmationSender
from app.runtime import Runtime
from app.state import CONFIRMED, PENDING

# Both captured title shapes must extract last-4 and still auto-confirm.
SHADE_TITLE = "PhonePe · ******4562 · Now"
LISTENER_TITLE = "******4562: ******4562"
TEXT = "sent ₹1 to you."


async def _ok(url: str, payload: dict) -> bool:
    return True


async def _single_candidate_last4_mismatch_still_confirms() -> None:
    runtime = Runtime(sender=ConfirmationSender(poster=_ok))
    await runtime.enqueue(
        "s-3419",
        "Customer",
        "1.00",
        "http://127.0.0.1:9/confirm",
        customer_phone="9876543419",
    )
    credit = await runtime.ingest_notification("com.phonepe.app", SHADE_TITLE, TEXT)
    assert credit is not None
    assert credit.payer_phone_last4 == "4562"
    assert format(credit.amount, "f") == "1.00"
    entry = runtime.queue.get_unlocked("s-3419")
    assert entry is not None
    assert entry.status == CONFIRMED


async def _collision_last4_picks_the_matching_phone() -> None:
    sent: list[str] = []

    async def poster(url: str, payload: dict) -> bool:
        sent.append(payload["session_id"])
        return True

    runtime = Runtime(sender=ConfirmationSender(poster=poster))
    await runtime.enqueue(
        "s-3419",
        "Typed",
        "1.00",
        "http://127.0.0.1:9/confirm",
        customer_phone="9876543419",
    )
    await runtime.enqueue(
        "s-4562",
        "Payer",
        "1.00",
        "http://127.0.0.1:9/confirm",
        customer_phone="9108234562",
    )
    credit = await runtime.ingest_notification(
        "com.phonepe.app", LISTENER_TITLE, "sent ₹1 to you."
    )
    assert credit is not None
    assert credit.payer_phone_last4 == "4562"
    runtime.sender.wait_idle(timeout=2)
    assert runtime.queue.get_unlocked("s-4562").status == CONFIRMED
    assert runtime.queue.get_unlocked("s-3419").status == PENDING
    assert sent == ["s-4562"]


async def _unparseable_last4_does_not_crash() -> None:
    runtime = Runtime(sender=ConfirmationSender(poster=_ok))
    await runtime.enqueue(
        "s-ok",
        "Priya Sharma",
        "150.00",
        "http://127.0.0.1:9/confirm",
        customer_phone="not-a-phone",
    )
    credit = await runtime.ingest_notification(
        "com.phonepe.app",
        "Payment received",
        "You have received Rs. 150.00 from PRIYA SHARMA",
    )
    assert credit is not None
    assert credit.payer_phone_last4 is None
    assert runtime.queue.get_unlocked("s-ok").status == CONFIRMED


def test_single_candidate_last4_mismatch_still_confirms() -> None:
    asyncio.run(_single_candidate_last4_mismatch_still_confirms())


def test_collision_last4_picks_the_matching_phone() -> None:
    asyncio.run(_collision_last4_picks_the_matching_phone())


def test_unparseable_last4_falls_back_without_crash() -> None:
    asyncio.run(_unparseable_last4_does_not_crash())
