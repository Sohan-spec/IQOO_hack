"""Public checkout: C5 callback sink, per-session status, single Pay page."""

from __future__ import annotations

import base64
import html
import hmac
import io
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import segno
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

RELAY_URL = os.environ.get("RELAY_URL", "https://sohan-spec--relay.modal.run").rstrip("/")
TEMPLATE = Path(__file__).with_name("index.html")

logger = logging.getLogger("checkout")
_status: dict[str, dict] = {}


def _confirm_secret() -> str:
    return os.environ.get("CHECKOUT_CONFIRM_SECRET", "").strip()


def _provided_confirm_secret(request: Request) -> str:
    auth = request.headers.get("authorization") or ""
    scheme, _, rest = auth.partition(" ")
    if scheme.lower() == "bearer" and rest.strip():
        return rest.strip()
    return (request.headers.get("x-confirm-secret") or "").strip()


def _confirm_authorized(request: Request) -> bool:
    expected = _confirm_secret()
    provided = _provided_confirm_secret(request)
    if not expected or not provided:
        return False
    if len(provided) != len(expected):
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def upi_pay_payload(vpa: str, payee: str) -> str:
    """Single source for on-page UPI ID text and the QR payload."""
    return f"upi://pay?pa={quote(vpa, safe='@')}&pn={quote(payee)}&cu=INR"


def qr_img_tag(payload: str) -> str:
    buf = io.BytesIO()
    segno.make(payload, error="m").save(buf, kind="png", scale=6, border=2)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return (
        f'<img id="upi-qr" alt="UPI QR" width="192" height="192" '
        f'data-upi="{html.escape(payload, quote=True)}" '
        f'src="data:image/png;base64,{b64}"/>'
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Relay checkout")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Confirm-Secret"],
    )

    @app.post("/confirm")
    async def confirm(request: Request) -> JSONResponse:
        if not _confirm_secret():
            logger.warning("confirm 503 CHECKOUT_CONFIRM_SECRET missing")
            return JSONResponse(
                {"error": "CHECKOUT_CONFIRM_SECRET is not configured"},
                status_code=503,
            )
        try:
            raw = await request.json()
        except Exception:
            raw = None
        session_hint = ""
        if isinstance(raw, dict) and isinstance(raw.get("session_id"), str):
            session_hint = raw["session_id"].strip()
        if not _confirm_authorized(request):
            logger.warning("confirm 401 session_id=%s", session_hint or "-")
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        if not isinstance(raw, dict):
            return JSONResponse({"error": "JSON object required"}, status_code=400)
        session_id = raw.get("session_id")
        status = raw.get("status")
        if not isinstance(session_id, str) or not session_id.strip():
            return JSONResponse({"error": "session_id is required"}, status_code=400)
        session_id = session_id.strip()
        if status != "confirmed":
            return JSONResponse({"error": "status must be confirmed"}, status_code=400)
        confirmed_at = datetime.now(timezone.utc).isoformat()
        _status[session_id] = {
            "status": "confirmed",
            "confirmed_at": confirmed_at,
        }
        logger.info("confirm 200 session_id=%s confirmed_at=%s", session_id, confirmed_at)
        return JSONResponse({"ok": True})

    @app.get("/status/{session_id}")
    async def status(session_id: str) -> JSONResponse:
        row = _status.get(session_id.strip())
        if row is None:
            return JSONResponse({"status": "pending"})
        return JSONResponse(row)

    @app.get("/", response_class=HTMLResponse)
    async def pay_page(request: Request) -> HTMLResponse:
        vpa = os.environ.get("CHECKOUT_VPA", "").strip()
        payee = os.environ.get("CHECKOUT_PAYEE_NAME", "").strip()
        merchant_id = os.environ.get("CHECKOUT_MERCHANT_ID", "").strip()
        if not vpa or not payee or not merchant_id:
            return HTMLResponse(
                "<!doctype html><p>Checkout is not configured. Set CHECKOUT_VPA, "
                "CHECKOUT_PAYEE_NAME, and CHECKOUT_MERCHANT_ID.</p>",
                status_code=503,
            )
        origin = str(request.base_url).rstrip("/")
        payload = upi_pay_payload(vpa, payee)
        html_page = TEMPLATE.read_text(encoding="utf-8")
        html_page = (
            html_page.replace("__RELAY_URL__", RELAY_URL)
            .replace("__CALLBACK_URL__", f"{origin}/confirm")
            .replace("__VPA__", html.escape(vpa))
            .replace("__PAYEE__", html.escape(payee))
            .replace("__MERCHANT_ID__", html.escape(merchant_id))
            .replace("__QR_IMG__", qr_img_tag(payload))
        )
        return HTMLResponse(html_page)

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    return app


app = create_app()
