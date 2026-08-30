from __future__ import annotations

import asyncio

from app.confirm import ConfirmationSender
from app.demo_fastpath import (
    DEMO_SESSION_ID,
    apply_demo_hardcoded_match,
    is_demo_hardcoded_match,
)
from app.models import CreditEvent, parse_amount, utcnow
from app.runtime import Runtime
from app.state import CONFIRMED, PENDING

SHADE_349 = ("PhonePe · ******4562 · Now", "sent ₹349 to you.")
SHADE_1 = ("PhonePe · ******4562 · Now", "sent ₹1 to you.")
OTHER_349 = ("PhonePe · ******9999 · Now", "sent ₹349 to you.")


async def _collecting_runtime() -> tuple[Runtime, list[tuple[str, dict]]]:
    sent: list[tuple[str, dict]] = []

    async def poster(url: str, payload: dict) -> bool:
        sent.append((url, payload))
        return True

    runtime = Runtime(
        sender=ConfirmationSender(poster=poster),
        default_callback_url="http://checkout.test/confirm",
    )
    return runtime, sent


async def _demo_without_pending_posts_fixed_session() -> None:
    runtime, sent = await _collecting_runtime()
    credit = await runtime.ingest_notification("com.phonepe.app", *SHADE_349)
    runtime.sender.wait_idle(timeout=2)
    assert credit is not None
    assert credit.payer_phone_last4 == "4562"
    assert credit.amount == parse_amount("349.00")
    assert [(url, body["session_id"]) for url, body in sent] == [
        ("http://checkout.test/confirm", DEMO_SESSION_ID)
    ]
    assert sent[0][1]["status"] == "confirmed"
    assert runtime.queue.all_unlocked() == []
    match = runtime.snapshot()["recent_matches"][0]
    assert match["session_id"] == DEMO_SESSION_ID
    assert match["customer_name"] == "SOHAN REDDY P"
    assert match["source"] == "demo"


async def _demo_with_one_open_session_leaves_unrelated_pending() -> None:
    runtime, sent = await _collecting_runtime()
    await runtime.enqueue(
        "real-open",
        "Waiting Tab",
        "1.00",
        "http://checkout.test/confirm",
        customer_phone="9876500000",
    )
    await runtime.ingest_notification("com.phonepe.app", *SHADE_349)
    runtime.sender.wait_idle(timeout=2)
    ids = [body["session_id"] for _, body in sent]
    assert ids == [DEMO_SESSION_ID]
    assert runtime.queue.get_unlocked("real-open").status == PENDING
    matches = runtime.snapshot()["recent_matches"]
    assert [row["session_id"] for row in matches] == [DEMO_SESSION_ID]
    assert matches[0]["amount"] == "349.00"


async def _demo_349_pending_is_one_owner_row() -> None:
    runtime, sent = await _collecting_runtime()
    await runtime.enqueue(
        "real-349",
        "Typed",
        "349.00",
        "http://checkout.test/confirm",
        customer_phone="9108234562",
    )
    await runtime.ingest_notification("com.phonepe.app", *SHADE_349)
    runtime.sender.wait_idle(timeout=2)
    ids = [body["session_id"] for _, body in sent]
    assert DEMO_SESSION_ID in ids
    assert "real-349" in ids
    assert runtime.queue.get_unlocked("real-349").status == CONFIRMED
    matches = runtime.snapshot()["recent_matches"]
    assert [row["session_id"] for row in matches] == [DEMO_SESSION_ID]
    assert matches[0]["amount"] == "349.00"
    assert matches[0]["source"] == "demo"
    assert matches[0]["customer_name"] == "SOHAN REDDY P"
    assert runtime.snapshot()["pending"] == []


async def _duplicate_banner_does_not_double_count() -> None:
    runtime, sent = await _collecting_runtime()
    await runtime.ingest_notification("com.phonepe.app", *SHADE_349)
    await runtime.ingest_notification(
        "com.phonepe.app",
        "******4562: ******4562",
        "sent ₹349 to you.",
    )
    runtime.sender.wait_idle(timeout=2)
    matches = runtime.snapshot()["recent_matches"]
    assert [row["session_id"] for row in matches] == [DEMO_SESSION_ID]
    assert matches[0]["amount"] == "349.00"
    demo_posts = [body for _, body in sent if body["session_id"] == DEMO_SESSION_ID]
    assert len(demo_posts) == 1


async def _other_amount_from_4562_skips_demo_uses_matcher() -> None:
    runtime, sent = await _collecting_runtime()
    await runtime.enqueue(
        "real-1",
        "Priya",
        "1.00",
        "http://checkout.test/confirm",
        customer_phone="9108234562",
    )
    await runtime.ingest_notification("com.phonepe.app", *SHADE_1)
    runtime.sender.wait_idle(timeout=2)
    ids = [body["session_id"] for _, body in sent]
    assert ids == ["real-1"]
    assert runtime.queue.get_unlocked("real-1").status == CONFIRMED
    assert all(row["source"] != "demo" for row in runtime.snapshot()["recent_matches"])


async def _other_payer_349_skips_demo_uses_matcher() -> None:
    runtime, sent = await _collecting_runtime()
    await runtime.enqueue(
        "real-other",
        "Priya",
        "349.00",
        "http://checkout.test/confirm",
        customer_phone="9876599999",
    )
    await runtime.ingest_notification("com.phonepe.app", *OTHER_349)
    runtime.sender.wait_idle(timeout=2)
    ids = [body["session_id"] for _, body in sent]
    assert ids == ["real-other"]
    assert runtime.queue.get_unlocked("real-other").status == CONFIRMED
    assert all(row["source"] != "demo" for row in runtime.snapshot()["recent_matches"])


def test_is_demo_hardcoded_match_is_exact() -> None:
    now = utcnow()
    hit = CreditEvent(
        package="com.phonepe.app",
        title="t",
        text="x",
        amount=parse_amount("349.00"),
        payer_name="",
        posted_at=now,
        payer_phone_last4="4562",
    )
    miss_amount = CreditEvent(
        package="com.phonepe.app",
        title="t",
        text="x",
        amount=parse_amount("349.01"),
        payer_name="",
        posted_at=now,
        payer_phone_last4="4562",
    )
    miss_last4 = CreditEvent(
        package="com.phonepe.app",
        title="t",
        text="x",
        amount=parse_amount("349"),
        payer_name="",
        posted_at=now,
        payer_phone_last4="4563",
    )
    assert is_demo_hardcoded_match(hit) is True
    assert is_demo_hardcoded_match(miss_amount) is False
    assert is_demo_hardcoded_match(miss_last4) is False
    assert parse_amount("349") == parse_amount("349.00")


def test_handle_demo_hardcoded_match_noops_when_criteria_miss() -> None:
    async def _run() -> None:
        runtime = Runtime(default_callback_url="http://checkout.test/confirm")
        miss = CreditEvent(
            package="com.phonepe.app",
            title="t",
            text="x",
            amount=parse_amount("1.00"),
            payer_name="",
            posted_at=utcnow(),
            payer_phone_last4="4562",
        )
        assert await apply_demo_hardcoded_match(runtime, miss) is False

    asyncio.run(_run())


def test_demo_without_pending_posts_fixed_session() -> None:
    asyncio.run(_demo_without_pending_posts_fixed_session())


def test_demo_with_one_open_session_leaves_unrelated_pending() -> None:
    asyncio.run(_demo_with_one_open_session_leaves_unrelated_pending())


def test_demo_349_pending_is_one_owner_row() -> None:
    asyncio.run(_demo_349_pending_is_one_owner_row())


def test_duplicate_banner_does_not_double_count() -> None:
    asyncio.run(_duplicate_banner_does_not_double_count())


def test_other_amount_from_4562_skips_demo_uses_matcher() -> None:
    asyncio.run(_other_amount_from_4562_skips_demo_uses_matcher())


def test_other_payer_349_skips_demo_uses_matcher() -> None:
    asyncio.run(_other_payer_349_skips_demo_uses_matcher())
