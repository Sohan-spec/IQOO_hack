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


async def _enqueue_omits_callback(runtime, session_id: str = "s-default"):
    return await enqueue(
        runtime,
        {
            "session_id": session_id,
            "customer_name": "Priya",
            "amount": "10.00",
        },
    )


def test_enqueue_without_callback_url_fails_when_default_empty() -> None:
    async def _run() -> None:
        from app.api.storefront import ApiError
        from app.runtime import Runtime

        runtime = Runtime()
        try:
            await _enqueue_omits_callback(runtime)
            raise AssertionError("expected ApiError")
        except ApiError as exc:
            assert exc.status == 400
            assert "callback_url" in exc.message

    asyncio.run(_run())


def test_enqueue_without_callback_url_uses_operator_default() -> None:
    async def _run() -> None:
        from app.runtime import Runtime

        runtime = Runtime()
        runtime.default_callback_url = "http://storefront.example/confirm"
        status, body = await _enqueue_omits_callback(runtime, "s-default-hit")
        assert status == 201
        assert body["status"] == "pending"
        entry = runtime.queue.get_unlocked("s-default-hit")
        assert entry is not None
        assert entry.callback_url == "http://storefront.example/confirm"

    asyncio.run(_run())
