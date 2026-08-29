#!/usr/bin/env python3
"""Throwaway Module A stand-in for A2 enqueue + A5 callback.

Not product code. Not Module A. Stdlib only.

Prints enqueue-sent and callback-received timestamps. The elapsed figure
is enqueue->callback, NOT G6 (G6 is pay-tap -> callback).
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PHONE_PORT_DEFAULT = 8787
LISTEN_PORT_DEFAULT = 8790
CUSTOMER_DEFAULT = "Demo Customer"
AMOUNT_DEFAULT = "1.00"
G6_NOTE = (
    "elapsed is enqueue->callback, NOT G6 "
    "(G6 is pay-tap in the sending app -> this callback)"
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_session_id(now: datetime | None = None) -> str:
    stamp = (now or utcnow()).strftime("%Y%m%dT%H%M%S%fZ")
    return f"g6-{stamp}"


def detect_non_loopback_ipv4() -> str:
    """Laptop IPv4 a phone on the hotspot can typically reach."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return "127.0.0.1"


class CallbackState:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.received_at: datetime | None = None
        self.body: dict | None = None


def _make_handler(state: CallbackState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length) if length else b""
            received_at = utcnow()
            try:
                parsed = json.loads(raw.decode("utf-8") or "{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                parsed = {}
            body = parsed if isinstance(parsed, dict) else {}
            reply = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(reply)))
            self.end_headers()
            self.wfile.write(reply)
            state.received_at = received_at
            state.body = body
            state.event.set()

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


class _CallbackServer(ThreadingHTTPServer):
    allow_reuse_address = True


def start_listener(host: str, port: int) -> tuple[ThreadingHTTPServer, CallbackState]:
    state = CallbackState()
    server = _CallbackServer((host, port), _make_handler(state))
    thread = threading.Thread(
        target=server.serve_forever,
        name="demo-stub-callback",
        daemon=True,
    )
    thread.start()
    return server, state


def enqueue_transaction(
    phone_host: str,
    session_id: str,
    customer_name: str,
    amount: str,
    callback_url: str,
    phone_port: int = PHONE_PORT_DEFAULT,
) -> tuple[datetime, dict]:
    payload = {
        "session_id": session_id,
        "customer_name": customer_name,
        "amount": amount,
        "callback_url": callback_url,
    }
    data = json.dumps(payload).encode("utf-8")
    if "://" in phone_host or "/" in phone_host:
        raise RuntimeError("phone-host must be a hostname or IP")
    url = f"http://{phone_host}:{phone_port}/v1/transactions"
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    sent_at = utcnow()
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected -- reason: URL scheme is fixed to http; host cannot contain :// or /
            raw = response.read().decode("utf-8")
            status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"enqueue HTTP {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"enqueue failed: {exc.reason}") from exc
    try:
        body = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"enqueue returned non-JSON: {raw!r}") from exc
    if status not in (200, 201):
        raise RuntimeError(f"enqueue HTTP {status}: {body}")
    return sent_at, body if isinstance(body, dict) else {}


def print_enqueue(sent_at: datetime, session_id: str, amount: str, callback_url: str) -> None:
    print(f"enqueue_sent   {sent_at.isoformat()}", flush=True)
    print(f"session_id     {session_id}", flush=True)
    print(f"amount         {amount}", flush=True)
    print(f"callback_url   {callback_url}", flush=True)


def print_callback(sent_at: datetime, received_at: datetime) -> None:
    elapsed = (received_at - sent_at).total_seconds()
    print(f"callback_recv  {received_at.isoformat()}", flush=True)
    print(f"elapsed_s      {elapsed:.3f}", flush=True)
    print(f"note           {G6_NOTE}", flush=True)


def wait_for_callback(state: CallbackState, timeout: float) -> bool:
    return state.event.wait(timeout=timeout)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="demo_storefront_stub",
        description=(
            "Throwaway storefront stub: POST /v1/transactions to the owner "
            "phone and listen for the C5 confirmation callback. Not Module A."
        ),
        epilog=(
            "Hotspot demo (this laptop is on the phone's hotspot):\n"
            "  python3 tools/demo_storefront_stub.py \\\n"
            "    --phone-host 192.168.43.1 \\\n"
            "    --callback-host 192.168.43.12 \\\n"
            "    --amount 1.00\n"
            "\n"
            "Local loopback:\n"
            "  python3 tools/demo_storefront_stub.py "
            "--phone-host 127.0.0.1 --callback-host 127.0.0.1\n"
            "\n"
            f"{G6_NOTE}."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--phone-host",
        default="127.0.0.1",
        help="Owner phone (or local backend) host. Default: 127.0.0.1",
    )
    parser.add_argument(
        "--phone-port",
        type=int,
        default=PHONE_PORT_DEFAULT,
        help=f"Owner HTTP port. Default: {PHONE_PORT_DEFAULT}",
    )
    parser.add_argument(
        "--listen-host",
        default="0.0.0.0",
        help="Bind address for the C5 callback listener. Default: 0.0.0.0",
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=LISTEN_PORT_DEFAULT,
        help=f"Bind port for the C5 callback listener. Default: {LISTEN_PORT_DEFAULT}",
    )
    parser.add_argument(
        "--callback-host",
        default=None,
        help=(
            "Host the phone should POST back to (laptop IP on the hotspot). "
            "Default: auto-detect a non-loopback IPv4."
        ),
    )
    parser.add_argument("--session-id", default=None, help="Opaque session id. Default: g6-<utc>")
    parser.add_argument(
        "--customer-name",
        default=CUSTOMER_DEFAULT,
        help=f"A2 customer_name. Default: {CUSTOMER_DEFAULT}",
    )
    parser.add_argument(
        "--amount",
        default=AMOUNT_DEFAULT,
        help=f"Exact amount string to enqueue (and to pay). Default: {AMOUNT_DEFAULT}",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="Seconds to wait for the C5 callback. Default: 180",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    callback_host = args.callback_host or detect_non_loopback_ipv4()
    if args.callback_host is None and callback_host.startswith("127."):
        print(
            "warning: auto-detect fell back to 127.0.0.1; "
            "pass --callback-host <laptop-hotspot-ip> for a phone demo",
            file=sys.stderr,
        )

    server, state = start_listener(args.listen_host, args.listen_port)
    listen_port = server.server_address[1]
    callback_url = f"http://{callback_host}:{listen_port}/confirm"
    session_id = args.session_id or generate_session_id()
    try:
        print(
            f"listening      {args.listen_host}:{listen_port} "
            f"(callback_url {callback_url})",
            flush=True,
        )
        sent_at, _body = enqueue_transaction(
            args.phone_host,
            session_id,
            args.customer_name,
            args.amount,
            callback_url,
            phone_port=args.phone_port,
        )
        print_enqueue(sent_at, session_id, args.amount, callback_url)
        print("waiting        for C5 callback (pay that amount, or R1-confirm)", flush=True)
        if not wait_for_callback(state, args.timeout):
            print(f"timeout after {args.timeout:.1f}s waiting for callback", file=sys.stderr)
            return 1
        assert state.received_at is not None
        print_callback(sent_at, state.received_at)
        if state.body:
            print(f"callback_body  {json.dumps(state.body, sort_keys=True)}", flush=True)
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
