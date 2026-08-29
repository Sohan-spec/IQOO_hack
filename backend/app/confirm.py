"""C5 — POST callback_url with session_id; retry on failure; never revert to pending."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import CONFIRM_BACKOFF_SECONDS
from app.models import PendingEntry

JsonPoster = Callable[[str, dict[str, Any]], Awaitable[bool]]


def post_json_blocking(url: str, payload: dict[str, Any]) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return 200 <= getattr(response, "status", 200) < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


async def default_poster(url: str, payload: dict[str, Any]) -> bool:
    return await asyncio.to_thread(post_json_blocking, url, payload)


class ConfirmationSender:
    def __init__(self, poster: JsonPoster | None = None) -> None:
        self._poster = poster or default_poster

    async def send(self, entry: PendingEntry) -> bool:
        payload = {"session_id": entry.session_id, "status": "confirmed"}
        for delay in (0.0, *CONFIRM_BACKOFF_SECONDS):
            if delay:
                await asyncio.sleep(delay)
            if await self._poster(entry.callback_url, payload):
                entry.confirm_acked = True
                return True
        return False
