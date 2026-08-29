from __future__ import annotations

import json
import logging
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.main import start, stop
from app.runtime import Runtime


def _wait_up(timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8787/v1/internal/snapshot", timeout=0.5):
                return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("HTTP server did not start")


def _post_json(url: str, body: dict, timeout: float = 2.0):
    payload = json.dumps(body).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode())


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=2) as response:
        return json.loads(response.read().decode())


def test_r1_unreachable_callback_returns_quickly(caplog) -> None:
    runtime = Runtime()
    thread = threading.Thread(target=lambda: start(runtime), daemon=True)
    thread.start()
    try:
        _wait_up()
        _post_json(
            "http://127.0.0.1:8787/v1/transactions",
            {
                "session_id": "sess-r1-unreach",
                "customer_name": "Priya",
                "amount": "10.00",
                "callback_url": "http://127.0.0.1:9/confirm",
            },
        )
        started = time.monotonic()
        status, body = _post_json(
            "http://127.0.0.1:8787/v1/internal/transactions/sess-r1-unreach/confirm",
            {},
        )
        elapsed = time.monotonic() - started
        print(f"R1 unreachable callback elapsed={elapsed:.4f}s")
        assert status == 200
        assert elapsed < 1.0
        assert body["session_id"] == "sess-r1-unreach"
        assert body["status"] == "confirmed"
        assert body["confirm_acked"] is False

        snap = _get_json("http://127.0.0.1:8787/v1/internal/snapshot")
        match = next(m for m in snap["recent_matches"] if m["session_id"] == "sess-r1-unreach")
        assert match["status"] == "confirmed"
        assert match["confirm_acked"] is False
        assert match["via"] == "manual"
        assert match["customer_name"] == "Priya"
        assert match["amount"] == "10.00"
        assert match["source"] == "manual"
        assert "matched_at" in match
        assert "session_id" in match

        with caplog.at_level(logging.WARNING, logger="app.confirm"):
            runtime.sender.wait_idle(timeout=40)
        snap_after = _get_json("http://127.0.0.1:8787/v1/internal/snapshot")
        match_after = next(
            m for m in snap_after["recent_matches"] if m["session_id"] == "sess-r1-unreach"
        )
        assert match_after["status"] == "confirmed"
        assert match_after["confirm_acked"] is False
        assert "session_id=sess-r1-unreach" in caplog.text
        assert "URLError" in caplog.text or "non-2xx" in caplog.text or "timeout" in caplog.text
    finally:
        stop()


def test_r1_reachable_callback_flips_confirm_acked() -> None:
    hits: list[bytes] = []
    release = threading.Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or "0")
            hits.append(self.rfile.read(length) if length else b"")
            release.wait(timeout=2)
            payload = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args) -> None:
            return

    listener = ThreadingHTTPServer(("127.0.0.1", 0), CallbackHandler)
    listen_thread = threading.Thread(target=listener.serve_forever, daemon=True)
    listen_thread.start()
    callback_url = f"http://127.0.0.1:{listener.server_address[1]}/confirm"

    runtime = Runtime()
    thread = threading.Thread(target=lambda: start(runtime), daemon=True)
    thread.start()
    try:
        _wait_up()
        _post_json(
            "http://127.0.0.1:8787/v1/transactions",
            {
                "session_id": "sess-r1-ok",
                "customer_name": "Priya",
                "amount": "10.00",
                "callback_url": callback_url,
            },
        )
        started = time.monotonic()
        status, body = _post_json(
            "http://127.0.0.1:8787/v1/internal/transactions/sess-r1-ok/confirm",
            {},
        )
        elapsed = time.monotonic() - started
        assert status == 200
        assert elapsed < 1.0
        assert body["confirm_acked"] is False

        snap = _get_json("http://127.0.0.1:8787/v1/internal/snapshot")
        match = next(m for m in snap["recent_matches"] if m["session_id"] == "sess-r1-ok")
        assert match["status"] == "confirmed"
        assert match["confirm_acked"] is False
        assert match["via"] == "manual"
        assert match["customer_name"] == "Priya"

        release.set()
        runtime.sender.wait_idle(timeout=2)
        snap = _get_json("http://127.0.0.1:8787/v1/internal/snapshot")
        match = next(m for m in snap["recent_matches"] if m["session_id"] == "sess-r1-ok")
        assert match["status"] == "confirmed"
        assert match["confirm_acked"] is True
        assert hits
    finally:
        stop()
        listener.shutdown()
