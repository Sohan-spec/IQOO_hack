from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from auth import AuthError, DeviceAuth  # noqa: E402

SECRET = "test-relay-secret"


def _app(**kwargs):
    auth = DeviceAuth(SECRET)
    return create_app(auth=auth, ping_interval=60, pong_grace=5, **kwargs), auth


def test_issue_and_verify_token() -> None:
    auth = DeviceAuth(SECRET)
    merchant_id, token = auth.issue()
    assert auth.verify(token) == merchant_id
    with pytest.raises(AuthError):
        auth.verify(token[:-1] + ("0" if token[-1] != "0" else "1"))
    with pytest.raises(AuthError):
        auth.verify("not-a-token")


def test_health() -> None:
    app, _auth = _app()
    with TestClient(app) as client:
        assert client.get("/health").json() == {"ok": True}


def test_enqueue_requires_merchant_and_live_phone() -> None:
    app, _auth = _app()
    with TestClient(app) as client:
        missing = client.post("/v1/transactions", json={"session_id": "s"})
        assert missing.status_code == 400
        offline = client.post(
            "/v1/transactions",
            json={
                "merchant_id": "11111111-1111-1111-1111-111111111111",
                "session_id": "s1",
                "customer_name": "Priya",
                "amount": "1.00",
                "callback_url": "http://storefront/confirm",
            },
        )
        assert offline.status_code == 503
        assert offline.json()["error"] == "phone not connected"


def test_websocket_rejects_bad_token() -> None:
    app, _auth = _app()
    with TestClient(app) as client:
        with pytest.raises(Exception):
            with client.websocket_connect("/connect?token=nope"):
                pass


def test_enqueue_round_trip_strips_merchant_id() -> None:
    app, auth = _app()
    merchant_id, token = auth.issue()
    with TestClient(app) as client:
        with client.websocket_connect(
            "/connect",
            headers={"Authorization": f"Bearer {token}"},
        ) as ws:
            def phone() -> None:
                message = ws.receive_json()
                assert message["type"] == "enqueue"
                assert "merchant_id" not in message["body"]
                assert message["body"]["session_id"] == "s1"
                assert message["body"]["customer_name"] == "Priya"
                ws.send_json(
                    {
                        "type": "enqueue_result",
                        "correlation_id": message["correlation_id"],
                        "status": 201,
                        "body": {"session_id": "s1", "status": "pending"},
                    }
                )

            worker = threading.Thread(target=phone, daemon=True)
            worker.start()
            time.sleep(0.05)
            response = client.post(
                "/v1/transactions",
                json={
                    "merchant_id": merchant_id,
                    "session_id": "s1",
                    "customer_name": "Priya",
                    "amount": "1.00",
                    "callback_url": "http://storefront/confirm",
                },
            )
            worker.join(timeout=2)
            assert response.status_code == 201
            assert response.json()["session_id"] == "s1"


def test_enqueue_times_out_when_phone_silent() -> None:
    app, auth = _app(enqueue_timeout=0.2)
    merchant_id, token = auth.issue()
    with TestClient(app) as client:
        with client.websocket_connect(
            "/connect",
            headers={"Authorization": f"Bearer {token}"},
        ):
            response = client.post(
                "/v1/transactions",
                json={
                    "merchant_id": merchant_id,
                    "session_id": "s1",
                    "customer_name": "Priya",
                    "amount": "1.00",
                    "callback_url": "http://storefront/confirm",
                },
            )
            assert response.status_code == 504


def test_payload_too_large() -> None:
    app, _auth = _app()
    with TestClient(app) as client:
        huge = json.dumps({"merchant_id": "x", "pad": "a" * 70000}).encode()
        response = client.post(
            "/v1/transactions",
            content=huge,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413
