from __future__ import annotations

import asyncio

from app.api.storefront import enqueue


async def _conflict() -> None:
    from app.confirm import ConfirmationSender
    from app.runtime import Runtime

    async def poster(url: str, payload: dict) -> bool:
        return True

    runtime = Runtime(sender=ConfirmationSender(poster=poster))
    first = await enqueue(
        runtime,
        {
            "session_id": "s1",
            "customer_name": "Priya",
            "amount": "10.00",
            "callback_url": "http://storefront/confirm",
        },
    )
    second = await enqueue(
        runtime,
        {
            "session_id": "s1",
            "customer_name": "Priya",
            "amount": "10.00",
            "callback_url": "http://storefront/confirm",
        },
    )
    assert first[0] == 201
    assert first[1]["status"] == "pending"
    assert second[0] == 409
    assert second[1]["status"] == "pending"


def test_duplicate_session_id_is_conflict() -> None:
    asyncio.run(_conflict())
