from __future__ import annotations

import asyncio

from app.confirm import ConfirmationSender
from app.models import CreditEvent, parse_amount, utcnow
from app.runtime import Runtime
from app.state import CONFIRMED, PENDING


async def _race() -> None:
    sent: list[str] = []

    async def poster(url: str, payload: dict) -> bool:
        sent.append(payload["session_id"])
        return True

    runtime = Runtime(sender=ConfirmationSender(poster=poster))
    await runtime.enqueue("s1", "Priya Sharma", "150.00", "http://storefront/confirm")

    credit = CreditEvent(
        package="com.phonepe.app",
        title="Payment received",
        text="You have received Rs. 150.00 from PRIYA SHARMA",
        amount=parse_amount("150.00"),
        payer_name="PRIYA SHARMA",
        posted_at=utcnow(),
    )

    gate = asyncio.Event()

    async def auto() -> object:
        await gate.wait()
        return await runtime._match_and_confirm(credit)

    async def manual() -> object:
        await gate.wait()
        return await runtime.manual_confirm("s1")

    auto_task = asyncio.create_task(auto())
    manual_task = asyncio.create_task(manual())
    await asyncio.sleep(0)
    gate.set()
    auto_result, manual_result = await asyncio.gather(auto_task, manual_task)

    winners = [result for result in (auto_result, manual_result) if result is not None]
    assert len(winners) == 1
    runtime.sender.wait_idle(timeout=2)
    assert len(sent) == 1
    entry = runtime.queue.get_unlocked("s1")
    assert entry is not None
    assert entry.status == CONFIRMED
    still_pending = [e for e in runtime.queue.all_unlocked() if e.status == PENDING]
    assert still_pending == []


def test_matcher_and_manual_confirm_concurrent_one_confirmation() -> None:
    asyncio.run(_race())
