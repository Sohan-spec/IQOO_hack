"""Public ingress: storefront HTTP in, owner-phone WebSocket out. No payment state."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from auth import AuthError, DeviceAuth, new_correlation_id, secret_from_env

logger = logging.getLogger("relay")

PING_INTERVAL_SECONDS = 25
PONG_GRACE_SECONDS = 10
ENQUEUE_TIMEOUT_SECONDS = 8
MAX_BODY_BYTES = 65536


class PhoneLink:
    def __init__(self, websocket: WebSocket, merchant_id: str) -> None:
        self.websocket = websocket
        self.merchant_id = merchant_id
        self.send_lock = asyncio.Lock()
        self.pong = asyncio.Event()
        self.pending: dict[str, asyncio.Future] = {}

    async def send(self, payload: dict[str, Any]) -> None:
        async with self.send_lock:
            await self.websocket.send_json(payload)

    def fail_pending(self, error: str) -> None:
        for future in self.pending.values():
            if not future.done():
                future.set_exception(RuntimeError(error))
        self.pending.clear()


class Hub:
    def __init__(self) -> None:
        self._links: dict[str, PhoneLink] = {}

    def get(self, merchant_id: str) -> PhoneLink | None:
        return self._links.get(merchant_id)

    async def attach(self, link: PhoneLink) -> None:
        previous = self._links.get(link.merchant_id)
        self._links[link.merchant_id] = link
        if previous is not None and previous is not link:
            previous.fail_pending("replaced by a new connection")
            try:
                await previous.websocket.close(code=4000, reason="replaced")
            except Exception:
                logger.info("closed stale socket merchant=%s", link.merchant_id)
        logger.info("phone connected merchant=%s", link.merchant_id)

    def drop(self, link: PhoneLink) -> None:
        if self._links.get(link.merchant_id) is link:
            del self._links[link.merchant_id]
        link.fail_pending("phone disconnected")
        logger.info("phone disconnected merchant=%s", link.merchant_id)


def create_app(
    auth: DeviceAuth | None = None,
    enqueue_timeout: float = ENQUEUE_TIMEOUT_SECONDS,
    ping_interval: float = PING_INTERVAL_SECONDS,
    pong_grace: float = PONG_GRACE_SECONDS,
) -> FastAPI:
    hub = Hub()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if auth is None:
            app.state.auth = DeviceAuth(secret_from_env())
        else:
            app.state.auth = auth
        app.state.hub = hub
        app.state.enqueue_timeout = enqueue_timeout
        app.state.ping_interval = ping_interval
        app.state.pong_grace = pong_grace
        yield

    app = FastAPI(title="Relay ingress", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/v1/transactions")
    async def enqueue(request: Request) -> JSONResponse:
        raw = await request.body()
        if len(raw) > MAX_BODY_BYTES:
            return JSONResponse({"error": "payload too large"}, status_code=413)
        try:
            body = json.loads(raw.decode("utf-8") or "null")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JSONResponse({"error": "invalid JSON"}, status_code=400)
        if not isinstance(body, dict):
            return JSONResponse({"error": "JSON object required"}, status_code=400)
        merchant_id = body.get("merchant_id")
        if not isinstance(merchant_id, str) or not merchant_id.strip():
            return JSONResponse({"error": "merchant_id is required"}, status_code=400)
        merchant_id = merchant_id.strip()
        link = hub.get(merchant_id)
        if link is None:
            return JSONResponse({"error": "phone not connected"}, status_code=503)
        forwarded = {key: value for key, value in body.items() if key != "merchant_id"}
        correlation_id = new_correlation_id()
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        link.pending[correlation_id] = future
        try:
            await link.send(
                {
                    "type": "enqueue",
                    "correlation_id": correlation_id,
                    "body": forwarded,
                }
            )
        except Exception:
            link.pending.pop(correlation_id, None)
            return JSONResponse({"error": "phone not connected"}, status_code=503)
        try:
            result = await asyncio.wait_for(future, timeout=app.state.enqueue_timeout)
        except TimeoutError:
            link.pending.pop(correlation_id, None)
            return JSONResponse({"error": "phone did not respond"}, status_code=504)
        except RuntimeError:
            return JSONResponse({"error": "phone not connected"}, status_code=503)
        status = result.get("status")
        payload = result.get("body")
        if not isinstance(status, int) or not isinstance(payload, dict):
            return JSONResponse({"error": "invalid phone reply"}, status_code=502)
        return JSONResponse(payload, status_code=status)

    @app.websocket("/connect")
    async def connect(websocket: WebSocket) -> None:
        token = _token_from_websocket(websocket)
        try:
            merchant_id = websocket.app.state.auth.verify(token)
        except AuthError:
            await websocket.close(code=4401, reason="unauthorized")
            return
        await websocket.accept()
        link = PhoneLink(websocket, merchant_id)
        await hub.attach(link)
        try:
            await asyncio.gather(
                _reader(link),
                _heartbeat(
                    link,
                    websocket.app.state.ping_interval,
                    websocket.app.state.pong_grace,
                ),
            )
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("socket failed merchant=%s", merchant_id)
        finally:
            hub.drop(link)

    return app


def _token_from_websocket(websocket: WebSocket) -> str:
    header = websocket.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return (websocket.query_params.get("token") or "").strip()


async def _reader(link: PhoneLink) -> None:
    while True:
        message = await link.websocket.receive_json()
        if not isinstance(message, dict):
            continue
        kind = message.get("type")
        if kind == "pong":
            link.pong.set()
            logger.info("pong merchant=%s", link.merchant_id)
            continue
        if kind != "enqueue_result":
            continue
        correlation_id = message.get("correlation_id")
        if not isinstance(correlation_id, str):
            continue
        future = link.pending.pop(correlation_id, None)
        if future is None or future.done():
            continue
        future.set_result(message)


async def _heartbeat(link: PhoneLink, ping_interval: float, pong_grace: float) -> None:
    while True:
        await asyncio.sleep(ping_interval)
        link.pong.clear()
        await link.send({"type": "ping"})
        logger.info("ping merchant=%s", link.merchant_id)
        try:
            await asyncio.wait_for(link.pong.wait(), timeout=pong_grace)
        except TimeoutError:
            logger.warning("pong timeout merchant=%s", link.merchant_id)
            await link.websocket.close(code=4001, reason="pong timeout")
            return


app = create_app()


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        ws_ping_interval=PING_INTERVAL_SECONDS,
        ws_ping_timeout=PONG_GRACE_SECONDS,
    )
