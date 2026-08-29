from __future__ import annotations

import json
import threading
import time
import urllib.request

from app.confirm import ConfirmationSender
from app.main import start, stop
from app.runtime import Runtime


def test_snapshot_route_on_loopback() -> None:
    async def poster(url: str, payload: dict) -> bool:
        return True

    runtime = Runtime(sender=ConfirmationSender(poster=poster))
    thread = threading.Thread(target=lambda: start(runtime), daemon=True)
    thread.start()
    body = None
    for _ in range(50):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8787/v1/internal/snapshot", timeout=1) as response:
                body = json.loads(response.read().decode())
                break
        except OSError:
            time.sleep(0.05)
    try:
        assert body is not None
        assert "pending" in body
        payload = json.dumps(
            {
                "session_id": "sess-http",
                "customer_name": "Priya",
                "amount": "10.00",
                "callback_url": "http://127.0.0.1:9/confirm",
            }
        ).encode()
        request = urllib.request.Request(
            "http://127.0.0.1:8787/v1/transactions",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            assert response.status == 201
    finally:
        stop()
