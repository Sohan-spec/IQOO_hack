from __future__ import annotations

import asyncio

from app.confirm import ConfirmationSender
from app.models import PendingEntry, parse_amount, utcnow
from app.runtime import Runtime


async def _retries_until_success() -> None:
    attempts: list[int] = []

    async def poster(url: str, payload: dict) -> bool:
        attempts.append(1)
        return len(attempts) >= 3

    sender = ConfirmationSender(poster=poster)
    entry = PendingEntry(
        session_id="s1",
        customer_name="Priya",
        amount=parse_amount("10.00"),
        created_at=utcnow(),
        status="confirmed",
        callback_url="http://storefront/confirm",
    )
    ok = await sender.send(entry)
    assert ok is True
    assert entry.confirm_acked is True
    assert len(attempts) == 3
    assert entry.status == "confirmed"


async def _manual_uses_sender() -> None:
    sent: list[str] = []

    async def poster(url: str, payload: dict) -> bool:
        sent.append(payload["session_id"])
        return True

    runtime = Runtime(sender=ConfirmationSender(poster=poster))
    await runtime.enqueue("s1", "Priya", "10.00", "http://storefront/confirm")
    entry = await runtime.manual_confirm("s1")
    assert entry is not None
    assert sent == ["s1"]


def test_retries_until_success() -> None:
    asyncio.run(_retries_until_success())


def test_manual_confirm_uses_same_send_path() -> None:
    asyncio.run(_manual_uses_sender())
