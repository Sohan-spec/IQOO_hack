from __future__ import annotations

from app.confirm import is_callback_url
from app.models import parse_amount
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
    if callback_url and not is_callback_url(callback_url):
        raise ApiError(400, "callback_url must start with http:// or https://")
    if not callback_url and not runtime.default_callback_url:
        raise ApiError(400, "callback_url is required")
    try:
        parse_amount(body.get("amount"))
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc
    outcome, entry = await runtime.enqueue(
        session_id,
        customer_name,
        body.get("amount"),
        callback_url,
    )
    public = {
        "session_id": entry.session_id,
        "status": entry.status,
        "created_at": entry.created_at.isoformat(),
    }
    if outcome == "conflict":
        return 409, {"error": "session_id already exists", **public}
    return 201, public
