from __future__ import annotations

import asyncio
import logging
import threading
from unittest.mock import patch

from app.confirm import ConfirmationSender
from app.models import PendingEntry, parse_amount, utcnow
from app.runtime import Runtime
from app.state import CONFIRMED, PENDING


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
    assert entry.status == CONFIRMED
    assert entry.confirm_acked is False
    runtime.sender.wait_idle(timeout=2)
    assert sent == ["s1"]
    assert entry.confirm_acked is True


async def _snapshot_keeps_banner_fields_and_live_ack() -> None:
    release = threading.Event()

    async def poster(url: str, payload: dict) -> bool:
        await asyncio.to_thread(release.wait, 2.0)
        return True

    runtime = Runtime(sender=ConfirmationSender(poster=poster))
    await runtime.enqueue("s1", "Priya", "10.00", "http://storefront/confirm")
    entry = await runtime.manual_confirm("s1")
    assert entry is not None
    assert entry.confirm_acked is False

    snap = runtime.snapshot()
    assert snap["pending"] == []
    match = snap["recent_matches"][0]
    assert match["session_id"] == "s1"
    assert match["customer_name"] == "Priya"
    assert match["amount"] == "10.00"
    assert match["source"] == "manual"
    assert match["via"] == "manual"
    assert match["status"] == CONFIRMED
    assert match["confirm_acked"] is False
    assert match["matched_at"] == match["at"]
    assert "payer_name" in match

    release.set()
    runtime.sender.wait_idle(timeout=2)
    live = runtime.snapshot()["recent_matches"][0]
    assert live["confirm_acked"] is True
    assert live["status"] == CONFIRMED
    assert live["customer_name"] == "Priya"
    assert live["source"] == "manual"


async def _auto_match_via_and_pending_filter() -> None:
    async def poster(url: str, payload: dict) -> bool:
        return True

    runtime = Runtime(sender=ConfirmationSender(poster=poster))
    await runtime.enqueue("s1", "Priya Sharma", "150.00", "http://storefront/confirm")
    credit = await runtime.ingest_notification(
        "com.phonepe.app",
        "Payment received",
        "You have received Rs. 150.00 from PRIYA SHARMA",
    )
    assert credit is not None
    still_pending = [e for e in runtime.queue.all_unlocked() if e.status == PENDING]
    assert still_pending == []
    snap = runtime.snapshot()
    assert snap["pending"] == []
    match = snap["recent_matches"][0]
    assert match["via"] == "auto"
    assert match["source"] == "matcher"
    assert match["session_id"] == "s1"
    runtime.sender.wait_idle(timeout=2)
    assert runtime.snapshot()["recent_matches"][0]["confirm_acked"] is True


def test_retries_until_success() -> None:
    asyncio.run(_retries_until_success())


def test_manual_confirm_uses_same_send_path() -> None:
    asyncio.run(_manual_uses_sender())


def test_snapshot_recent_matches_live_confirm_acked() -> None:
    asyncio.run(_snapshot_keeps_banner_fields_and_live_ack())


def test_auto_match_snapshot_via_auto() -> None:
    asyncio.run(_auto_match_via_and_pending_filter())


def test_exhausted_retries_are_logged(caplog) -> None:
    async def poster(url: str, payload: dict) -> bool:
        return False

    entry = PendingEntry(
        session_id="s-fail",
        customer_name="Priya",
        amount=parse_amount("10.00"),
        created_at=utcnow(),
        status=CONFIRMED,
        callback_url="http://storefront/confirm",
    )
    sender = ConfirmationSender(poster=poster)
    with caplog.at_level(logging.WARNING, logger="app.confirm"):
        with patch("app.confirm.CONFIRM_BACKOFF_SECONDS", ()):
            ok = asyncio.run(sender.send(entry))
    assert ok is False
    assert entry.confirm_acked is False
    assert entry.status == CONFIRMED
    assert "session_id=s-fail" in caplog.text
    assert "non-2xx" in caplog.text


def test_file_and_empty_urls_are_rejected() -> None:
    from app.confirm import _post_json_with_reason, is_callback_url

    payload = {"session_id": "s1", "status": "confirmed"}
    ok, reason = _post_json_with_reason("file:///etc/passwd", payload)
    assert ok is False
    assert reason == "invalid_url"
    assert is_callback_url("file:///etc/passwd") is False
    assert is_callback_url("ftp://example/confirm") is False
    assert is_callback_url("http://") is False
    assert is_callback_url("http://127.0.0.1:9/confirm") is True


def test_confirm_post_sends_bearer_secret() -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from app.confirm import _post_json_with_reason, set_confirm_secret

    captured: dict[str, str] = {}

    class CaptureHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            captured["authorization"] = self.headers.get("Authorization") or ""
            length = int(self.headers.get("Content-Length") or "0")
            if length:
                self.rfile.read(length)
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            return

    set_confirm_secret("checkout-confirm-test-secret")
    server = ThreadingHTTPServer(("127.0.0.1", 0), CaptureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/confirm"
        ok, reason = _post_json_with_reason(
            url, {"session_id": "s1", "status": "confirmed"}
        )
        assert ok is True
        assert reason == "ok"
        assert captured["authorization"] == "Bearer checkout-confirm-test-secret"
        set_confirm_secret("")
        captured.clear()
        ok_plain, _ = _post_json_with_reason(
            url, {"session_id": "s2", "status": "confirmed"}
        )
        assert ok_plain is True
        assert captured.get("authorization", "") == ""
    finally:
        set_confirm_secret("")
        server.shutdown()
        server.server_close()


def test_http_redirect_is_not_success() -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from app.confirm import _post_json_with_reason

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or "0")
            if length:
                self.rfile.read(length)
            self.send_response(302)
            self.send_header("Location", "file:///etc/passwd")
            self.end_headers()

        def log_message(self, format: str, *args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/confirm"
        ok, reason = _post_json_with_reason(url, {"session_id": "s1", "status": "confirmed"})
        assert ok is False
        assert "302" in reason or "non-2xx" in reason
    finally:
        server.shutdown()
        server.server_close()
