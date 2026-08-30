from __future__ import annotations

from app.models import parse_amount
from app.phone import normalize_in_mobile
from app.runtime import Runtime


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _require_str(body: dict, key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ApiError(400, f"{key} is required")
    return value.strip()


async def enqueue(runtime: Runtime, body: dict) -> tuple[int, dict]:
    if not isinstance(body, dict):
        raise ApiError(400, "JSON object required")
    session_id = _require_str(body, "session_id")
    customer_name = _require_str(body, "customer_name")
    callback_url = body.get("callback_url")
    if isinstance(callback_url, str):
        callback_url = callback_url.strip()
    else:
        callback_url = ""
    if not callback_url and not runtime.default_callback_url:
        raise ApiError(400, "callback_url is required")
    try:
        parse_amount(body.get("amount"))
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc
    email = body.get("customer_email")
    if email is None:
        customer_email = None
    elif not isinstance(email, str):
        raise ApiError(400, "customer_email must be a string")
    else:
        customer_email = email.strip() or None
    raw_phone = body.get("customer_phone")
    if raw_phone is None:
        customer_phone = None
    elif not isinstance(raw_phone, str):
        raise ApiError(400, "customer_phone must be a string")
    else:
        try:
            customer_phone = normalize_in_mobile(raw_phone)
        except ValueError as exc:
            raise ApiError(400, str(exc)) from exc
    outcome, entry = await runtime.enqueue(
        session_id,
        customer_name,
        body.get("amount"),
        callback_url,
        customer_phone=customer_phone,
        customer_email=customer_email,
    )
    public = {
        "session_id": entry.session_id,
        "status": entry.status,
        "created_at": entry.created_at.isoformat(),
    }
    if outcome == "conflict":
        return 409, {"error": "session_id already exists", **public}
    return 201, public
