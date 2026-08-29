"""C5 — POST callback_url with session_id; retry on failure; never revert to pending."""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlsplit

from app.config import CONFIRM_BACKOFF_SECONDS
from app.models import PendingEntry

logger = logging.getLogger(__name__)

JsonPoster = Callable[[str, dict[str, Any]], Awaitable[bool]]

# No FileHandler / FTPHandler / HTTPRedirectHandler: callback_url is
# merchant-controlled (C5). Default urlopen would follow a 3xx to file://.
_OPENER = urllib.request.build_opener(
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(),
    urllib.request.HTTPDefaultErrorHandler(),
    urllib.request.HTTPErrorProcessor(),
)


def is_callback_url(url: str) -> bool:
    parsed = urlsplit(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def post_json_blocking(url: str, payload: dict[str, Any]) -> bool:
    ok, _reason = _post_json_with_reason(url, payload)
    return ok


def _post_json_with_reason(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    if not is_callback_url(url):
        return False, "invalid_url"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected -- reason: C5 POSTs to merchant callback_url; scheme is http/https via urlsplit and this opener has no FileHandler or redirect handler
        with _OPENER.open(request, timeout=5) as response:
            status = getattr(response, "status", 200)
            if 200 <= status < 300:
                return True, "ok"
            return False, f"non-2xx HTTP {status}"
    except TimeoutError as exc:
        return False, f"timeout: {exc}"
    except urllib.error.HTTPError as exc:
        return False, f"non-2xx HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return False, f"URLError: {exc.reason}"
    except OSError as exc:
        return False, f"OSError: {exc}"


class ConfirmationSender:
    def __init__(self, poster: JsonPoster | None = None) -> None:
        self._poster = poster
        self._jobs: queue.Queue[PendingEntry] = queue.Queue()
        self._idle = threading.Condition()
        self._pending_jobs = 0
        self._started = False
        self._thread = threading.Thread(
            target=self._run,
            name="relay-confirm",
            daemon=True,
        )

    def submit(self, entry: PendingEntry) -> None:
        """Queue outbound POST; return without waiting for delivery."""
        with self._idle:
            self._pending_jobs += 1
            if not self._started:
                self._thread.start()
                self._started = True
        self._jobs.put(entry)

    def wait_idle(self, timeout: float = 15.0) -> None:
        """Block until queued deliveries finish. Used by tests."""
        deadline = time.monotonic() + timeout
        with self._idle:
            while self._pending_jobs > 0:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("confirm worker still busy")
                self._idle.wait(timeout=remaining)

    def _run(self) -> None:
        while True:
            entry = self._jobs.get()
            try:
                self._deliver(entry)
            except Exception:
                logger.exception(
                    "confirm worker crashed session_id=%s",
                    entry.session_id,
                )
            finally:
                with self._idle:
                    self._pending_jobs -= 1
                    self._idle.notify_all()

    def _deliver(self, entry: PendingEntry) -> bool:
        payload = {"session_id": entry.session_id, "status": "confirmed"}
        last_reason = "retries exhausted"
        for delay in (0.0, *CONFIRM_BACKOFF_SECONDS):
            if delay:
                time.sleep(delay)
            ok, reason = self._attempt(entry.callback_url, payload)
            if ok:
                entry.confirm_acked = True
                return True
            last_reason = reason
        logger.warning(
            "confirm delivery failed session_id=%s reason=%s",
            entry.session_id,
            last_reason,
        )
        return False

    def _attempt(self, url: str, payload: dict[str, Any]) -> tuple[bool, str]:
        if self._poster is None:
            return _post_json_with_reason(url, payload)
        try:
            ok = asyncio.run(self._poster(url, payload))
            return (True, "ok") if ok else (False, "non-2xx")
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    async def send(self, entry: PendingEntry) -> bool:
        return await asyncio.to_thread(self._deliver, entry)
