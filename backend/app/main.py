"""On-device HTTP listener (stdlib http.server). Binds 0.0.0.0:8787."""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from app.api import internal, storefront
from app.api.storefront import ApiError
from app.config import BIND_HOST, PORT, SWEEP_INTERVAL_SECONDS
from app.runtime import Runtime

_runtime: Runtime | None = None
_loop: asyncio.AbstractEventLoop | None = None
_http: ThreadingHTTPServer | None = None
_running = False


def get_runtime() -> Runtime:
    if _runtime is None:
        raise RuntimeError("runtime is not started")
    return _runtime


def _call(coro):
    assert _loop is not None
    return asyncio.run_coroutine_threadsafe(coro, _loop).result(timeout=15)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(400, "invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise ApiError(400, "JSON object required")
        return parsed

    def _send(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self._cors()
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/v1/internal/snapshot":
                status, body = _call(internal.snapshot(get_runtime()))
                self._send(status, body)
                return
            self._send(404, {"error": "not found"})
        except ApiError as exc:
            self._send(exc.status, {"error": exc.message})
        except Exception as exc:  # noqa: BLE001 — last-line HTTP guard
            self._send(500, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            body = self._read_json()
            runtime = get_runtime()
            if path == "/v1/transactions":
                status, payload = _call(storefront.enqueue(runtime, body))
                self._send(status, payload)
                return
            if path == "/v1/internal/notifications":
                status, payload = _call(internal.ingest_notification(runtime, body))
                self._send(status, payload)
                return
            prefix = "/v1/internal/transactions/"
            suffix = "/confirm"
            if path.startswith(prefix) and path.endswith(suffix):
                session_id = path[len(prefix) : -len(suffix)]
                status, payload = _call(internal.manual_confirm(runtime, session_id))
                self._send(status, payload)
                return
            self._send(404, {"error": "not found"})
        except ApiError as exc:
            self._send(exc.status, {"error": exc.message})
        except Exception as exc:  # noqa: BLE001 — last-line HTTP guard
            self._send(500, {"error": str(exc)})


async def _sweeper(runtime: Runtime) -> None:
    while _running:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        if _running:
            await runtime.sweep_expired()


def start(runtime: Runtime | None = None) -> None:
    global _runtime, _loop, _http, _running
    if _http is not None:
        return
    _running = True
    _runtime = runtime or Runtime()
    _loop = asyncio.new_event_loop()
    thread = threading.Thread(target=_loop.run_forever, name="relay-asyncio", daemon=True)
    thread.start()
    asyncio.run_coroutine_threadsafe(_sweeper(_runtime), _loop)
    _http = ThreadingHTTPServer((BIND_HOST, PORT), Handler)
    _http.serve_forever()


def stop() -> None:
    global _http, _loop, _running
    _running = False
    if _http is not None:
        _http.shutdown()
        _http = None
    if _loop is not None:
        loop = _loop

        def _halt() -> None:
            for task in asyncio.all_tasks(loop):
                task.cancel()
            loop.stop()

        _loop.call_soon_threadsafe(_halt)


if __name__ == "__main__":
    start()
