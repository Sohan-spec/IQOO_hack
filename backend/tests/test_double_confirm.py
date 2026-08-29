from __future__ import annotations

import asyncio

from app.confirm import ConfirmationSender
from app.runtime import Runtime
from app.state import CONFIRMED


async def _once() -> None:
    sent: list[str] = []

    async def poster(url: str, payload: dict) -> bool:
        sent.append(payload["session_id"])
        return True

    runtime = Runtime(sender=ConfirmationSender(poster=poster))
    await runtime.enqueue("s1", "Priya Sharma", "150.00", "http://storefront/confirm")
    first = await runtime.ingest_notification(
        "com.phonepe.app",
        "Payment received",
        "You have received Rs. 150.00 from PRIYA SHARMA",
    )
    second = await runtime.ingest_notification(
        "com.phonepe.app",
        "Payment received",
        "You have received Rs. 150.00 from PRIYA SHARMA",
    )
    assert first is not None
    assert second is not None
    assert len(sent) == 1
    assert runtime.queue.get_unlocked("s1").status == CONFIRMED


def test_repeat_credit_does_not_double_confirm() -> None:
    asyncio.run(_once())
