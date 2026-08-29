"""Local A2/A5 proof for tools/demo_storefront_stub.py.

Uses R1 manual confirm + the Phase 1 background C5 worker. Does not call
the matcher and does not special-case session ids in matcher.py.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

from app.main import start, stop
from app.matcher import select_candidate
from app.runtime import Runtime

_STUB_PATH = Path(__file__).resolve().parents[2] / "tools" / "demo_storefront_stub.py"


def _load_stub():
    spec = importlib.util.spec_from_file_location("demo_storefront_stub", _STUB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stub = _load_stub()


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


def test_help_is_usable() -> None:
    help_text = stub.build_parser().format_help()
    assert "--phone-host" in help_text
    assert "--listen-host" in help_text
    assert "--listen-port" in help_text
    assert "--callback-host" in help_text
    assert "--amount" in help_text
    assert "G6" in help_text


def test_matcher_not_hardcoded_for_stub() -> None:
    source = inspect.getsource(select_candidate)
    assert "g6-" not in source
    assert "demo_storefront" not in source
    assert "8790" not in source
    assert "status == PENDING" in source or 'status == "pending"' in source


def test_stub_a2_a5_via_r1_background_c5(capsys) -> None:
    runtime = Runtime()
    thread = threading.Thread(target=lambda: start(runtime), daemon=True)
    thread.start()
    server = None
    try:
        _wait_up()
        server, state = stub.start_listener("127.0.0.1", 0)
        listen_port = server.server_address[1]
        callback_url = f"http://127.0.0.1:{listen_port}/confirm"
        session_id = stub.generate_session_id()

        sent_at, enqueue_body = stub.enqueue_transaction(
            "127.0.0.1",
            session_id,
            "Ada",
            "1.00",
            callback_url,
        )
        assert enqueue_body.get("session_id") == session_id
        assert enqueue_body.get("status") == "pending"
        stub.print_enqueue(sent_at, session_id, "1.00", callback_url)

        status, confirm_body = _post_json(
            f"http://127.0.0.1:8787/v1/internal/transactions/{session_id}/confirm",
            {},
        )
        assert status == 200
        assert confirm_body["status"] == "confirmed"
        # C5 is Phase 1 background: R1 returns before delivery. Wait; do not
        # assume the callback has already arrived.
        assert stub.wait_for_callback(state, timeout=3.0)
        assert state.received_at is not None
        assert state.body == {"session_id": session_id, "status": "confirmed"}
        stub.print_callback(sent_at, state.received_at)

        out = capsys.readouterr().out
        assert sent_at.isoformat() in out
        assert state.received_at.isoformat() in out
        assert "enqueue_sent" in out
        assert "callback_recv" in out
        assert "NOT G6" in out
        assert "pay-tap" in out
    finally:
        stop()
        if server is not None:
            server.shutdown()
            server.server_close()


def test_cli_help_subprocess() -> None:
    import subprocess

    result = subprocess.run(
        [sys.executable, str(_STUB_PATH), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--phone-host" in result.stdout
    assert "127.0.0.1" in result.stdout
