from __future__ import annotations

import asyncio
from datetime import timedelta

from app.config import PII_TTL_SECONDS
from app.models import utcnow
from app.runtime import Runtime
from app.state import EXPIRED


async def _pii_cleared_on_expire_and_aged_confirm() -> None:
    runtime = Runtime(expiry_seconds=1)
    await runtime.enqueue(
        "s-exp",
        "Priya",
        "1.00",
        "http://storefront/confirm",
        customer_phone="9876543210",
        customer_email="a@b.c",
    )
    entry = runtime.queue.get_unlocked("s-exp")
    assert entry is not None
    entry.created_at = utcnow() - timedelta(seconds=5)
    await runtime.sweep_expired()
    assert entry.status == EXPIRED
    assert entry.customer_phone is None
    assert entry.customer_email is None

    runtime2 = Runtime()
    await runtime2.enqueue(
        "s-ok",
        "Priya",
        "1.00",
        "http://storefront/confirm",
        customer_phone="9876543210",
        customer_email="a@b.c",
    )
    confirmed = await runtime2.manual_confirm("s-ok")
    assert confirmed is not None
    assert confirmed.customer_phone == "9876543210"
    confirmed.confirmed_at = utcnow() - timedelta(seconds=PII_TTL_SECONDS + 1)
    await runtime2.sweep_expired()
    assert confirmed.customer_phone is None
    assert confirmed.customer_email is None
    snap = runtime2.snapshot()
    assert all(row["session_id"] != "s-ok" for row in snap["pending"])


def test_pii_cleared_on_expire_and_aged_confirm() -> None:
    asyncio.run(_pii_cleared_on_expire_and_aged_confirm())
