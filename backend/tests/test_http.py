from __future__ import annotations

import json
import threading
import time
import urllib.error
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
        assert "recent_matches" in body
        assert "recent_credits" in body
        assert "recent_raw_notifications" in body
        assert isinstance(body["recent_raw_notifications"], list)
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


def _wait_snapshot() -> dict:
    for _ in range(50):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8787/v1/internal/snapshot", timeout=1) as response:
                return json.loads(response.read().decode())
        except OSError:
            time.sleep(0.05)
    raise AssertionError("HTTP server did not start")


def _post(url: str, body: dict) -> tuple[int, dict]:
    payload = json.dumps(body).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        parsed = json.loads(raw) if raw else {}
        return exc.code, parsed


def test_settings_default_callback_then_enqueue_omits_url() -> None:
    async def poster(url: str, payload: dict) -> bool:
        return True

    runtime = Runtime(sender=ConfirmationSender(poster=poster))
    thread = threading.Thread(target=lambda: start(runtime), daemon=True)
    thread.start()
    try:
        snap = _wait_snapshot()
        assert snap["default_callback_url"] == ""

        omit_body = {
            "session_id": "sess-omit",
            "customer_name": "Priya",
            "amount": "10.00",
        }
        status, err = _post("http://127.0.0.1:8787/v1/transactions", omit_body)
        assert status == 400
        assert "callback_url" in err.get("error", "")

        bad_status, _ = _post(
            "http://127.0.0.1:8787/v1/internal/settings",
            {"default_callback_url": "ftp://not-allowed"},
        )
        assert bad_status == 400

        default_url = "http://127.0.0.1:9/confirm"
        set_status, set_body = _post(
            "http://127.0.0.1:8787/v1/internal/settings",
            {"default_callback_url": default_url},
        )
        assert set_status == 200
        assert set_body["default_callback_url"] == default_url

        snap = _wait_snapshot()
        assert snap["default_callback_url"] == default_url

        created, public = _post("http://127.0.0.1:8787/v1/transactions", omit_body)
        assert created == 201
        assert public["session_id"] == "sess-omit"
        assert public["status"] == "pending"
        entry = runtime.queue.get_unlocked("sess-omit")
        assert entry is not None
        assert entry.callback_url == default_url

        cleared, cleared_body = _post(
            "http://127.0.0.1:8787/v1/internal/settings",
            {"default_callback_url": ""},
        )
        assert cleared == 200
        assert cleared_body["default_callback_url"] == ""
        assert runtime.default_callback_url == ""
    finally:
        stop()


def test_oversized_body_is_rejected() -> None:
    from app.config import MAX_HTTP_BODY_BYTES

    runtime = Runtime()
    thread = threading.Thread(target=lambda: start(runtime), daemon=True)
    thread.start()
    try:
        _wait_snapshot()
        huge = b"x" * (MAX_HTTP_BODY_BYTES + 1)
        request = urllib.request.Request(
            "http://127.0.0.1:8787/v1/internal/settings",
            data=huge,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(request, timeout=2)
            raise AssertionError("expected HTTPError")
        except urllib.error.HTTPError as exc:
            assert exc.code == 413
            body = json.loads(exc.read().decode())
            assert body.get("error") == "payload too large"
    finally:
        stop()
