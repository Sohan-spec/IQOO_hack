from fastapi.testclient import TestClient

from app import create_app

_SECRET = "a" * 64


def _configured(monkeypatch) -> None:
    monkeypatch.setenv("CHECKOUT_VPA", "merchant@upi")
    monkeypatch.setenv("CHECKOUT_PAYEE_NAME", "Demo Shop")
    monkeypatch.setenv("CHECKOUT_MERCHANT_ID", "11111111-1111-1111-1111-111111111111")
    monkeypatch.setenv("CHECKOUT_CONFIRM_SECRET", _SECRET)


def test_confirm_then_status(monkeypatch) -> None:
    _configured(monkeypatch)
    client = TestClient(create_app())
    sid = "sess-1"
    pending = client.get(f"/status/{sid}")
    assert pending.status_code == 200
    assert pending.json()["status"] == "pending"
    posted = client.post(
        "/confirm",
        json={"session_id": sid, "status": "confirmed"},
        headers={"X-Confirm-Secret": _SECRET},
    )
    assert posted.status_code == 200
    confirmed = client.get(f"/status/{sid}")
    assert confirmed.json()["status"] == "confirmed"
    assert "confirmed_at" in confirmed.json()


def test_confirm_rejects_missing_or_wrong_secret(monkeypatch) -> None:
    _configured(monkeypatch)
    client = TestClient(create_app())
    body = {"session_id": "sess-x", "status": "confirmed"}
    assert client.post("/confirm", json=body).status_code == 401
    assert client.post(
        "/confirm", json=body, headers={"X-Confirm-Secret": "nope"}
    ).status_code == 401
    assert client.get("/status/sess-x").json()["status"] == "pending"
    ok = client.post(
        "/confirm",
        json=body,
        headers={"Authorization": f"Bearer {_SECRET}"},
    )
    assert ok.status_code == 200


def test_confirm_unconfigured_secret(monkeypatch) -> None:
    _configured(monkeypatch)
    monkeypatch.delenv("CHECKOUT_CONFIRM_SECRET", raising=False)
    client = TestClient(create_app())
    posted = client.post(
        "/confirm",
        json={"session_id": "sess-x", "status": "confirmed"},
        headers={"X-Confirm-Secret": _SECRET},
    )
    assert posted.status_code == 503


def test_pay_page_has_no_vpa_input(monkeypatch) -> None:
    _configured(monkeypatch)
    client = TestClient(create_app())
    page = client.get("/")
    assert page.status_code == 200
    html = page.text
    assert 'id="vpa"' not in html
    assert "merchant@upi" in html
    assert "upi://pay" in html
    assert "tr=" in html
    assert _SECRET not in html
    assert "X-Confirm-Secret" not in html


def test_status_allows_cross_origin_storefront(monkeypatch) -> None:
    _configured(monkeypatch)
    client = TestClient(create_app())
    res = client.get("/status/sess-cors", headers={"Origin": "http://localhost:3000"})
    assert res.status_code == 200
    assert res.json()["status"] == "pending"
    assert res.headers.get("access-control-allow-origin") in (
        "*",
        "http://localhost:3000",
    )


def test_unconfigured_pay_page(monkeypatch) -> None:
    monkeypatch.delenv("CHECKOUT_VPA", raising=False)
    monkeypatch.delenv("CHECKOUT_PAYEE_NAME", raising=False)
    monkeypatch.delenv("CHECKOUT_MERCHANT_ID", raising=False)
    client = TestClient(create_app())
    page = client.get("/")
    assert page.status_code == 503
