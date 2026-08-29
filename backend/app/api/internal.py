from __future__ import annotations

from app.api.storefront import ApiError
from app.confirm import is_callback_url
from app.runtime import Runtime


async def snapshot(runtime: Runtime) -> tuple[int, dict]:
    return 200, runtime.snapshot()


async def update_settings(runtime: Runtime, body: dict) -> tuple[int, dict]:
    if not isinstance(body, dict):
        raise ApiError(400, "JSON object required")
    if "default_callback_url" not in body:
        raise ApiError(400, "default_callback_url is required")
    value = body.get("default_callback_url")
    if not isinstance(value, str):
        raise ApiError(400, "default_callback_url must be a string")
    url = value.strip()
    if url and not is_callback_url(url):
        raise ApiError(400, "default_callback_url must start with http:// or https://")
    runtime.default_callback_url = url
    return 200, {"default_callback_url": runtime.default_callback_url}


async def ingest_notification(runtime: Runtime, body: dict) -> tuple[int, dict]:
    if not isinstance(body, dict):
        raise ApiError(400, "JSON object required")
    package = body.get("package") or ""
    title = body.get("title") or ""
    text = body.get("text") or ""
    if not isinstance(package, str) or not isinstance(title, str) or not isinstance(text, str):
        raise ApiError(400, "package, title, and text must be strings")
    posted_at = body.get("posted_at")
    if posted_at is not None and not isinstance(posted_at, str):
        raise ApiError(400, "posted_at must be a string")
    credit = await runtime.ingest_notification(package, title, text, posted_at)
    if credit is None:
        return 200, {"accepted": True, "credit": False}
    return 200, {"accepted": True, "credit": True, "event": credit.to_public_dict()}


async def manual_confirm(runtime: Runtime, session_id: str) -> tuple[int, dict]:
    if not session_id:
        raise ApiError(400, "session_id is required")
    entry = await runtime.manual_confirm(session_id)
    if entry is None:
        raise ApiError(409, "session is not pending")
    return 200, {
        "session_id": entry.session_id,
        "status": entry.status,
        "confirm_acked": entry.confirm_acked,
    }
