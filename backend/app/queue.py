from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from app.models import PendingEntry
from app.state import PENDING, mark_expired


class TransactionQueue:
    """In-memory session store. Confirmed/expired rows are never evicted:
    snapshot live-ack lookup needs the entry present for confirm_acked.
    """

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self._entries: dict[str, PendingEntry] = {}

    def get_unlocked(self, session_id: str) -> PendingEntry | None:
        return self._entries.get(session_id)

    def all_unlocked(self) -> list[PendingEntry]:
        return list(self._entries.values())

    def put_unlocked(self, entry: PendingEntry) -> None:
        self._entries[entry.session_id] = entry

    async def enqueue(self, entry: PendingEntry) -> tuple[str, PendingEntry]:
        async with self.lock:
            existing = self._entries.get(entry.session_id)
            if existing is not None:
                return "conflict", existing
            self._entries[entry.session_id] = entry
            return "created", entry

    async def expire_due(self, now: datetime, window: timedelta) -> list[PendingEntry]:
        expired: list[PendingEntry] = []
        async with self.lock:
            for entry in self._entries.values():
                if entry.status != PENDING:
                    continue
                if now - entry.created_at > window:
                    mark_expired(entry)
                    expired.append(entry)
        return expired
