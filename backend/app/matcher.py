"""C4 matcher. Ordered rules — stop at first resolution.

step 0: candidates = entries where status == pending
1. Amount exact Decimal equality
2. Drop candidates older than the expiry window
3. If multiple remain, normalised case-insensitive name compare
4. Else oldest created_at
5. Zero candidates → no confirm
6. Confirm at most once (enforced by the confirm critical section, not here)
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from app.models import CreditEvent, PendingEntry
from app.state import PENDING

_WS = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    return _WS.sub(" ", name.casefold()).strip()


def select_candidate(
    entries: list[PendingEntry],
    credit: CreditEvent,
    now: datetime,
    window: timedelta,
) -> PendingEntry | None:
    # step 0: candidates = entries where status == pending
    candidates = [entry for entry in entries if entry.status == PENDING]

    # 1. Amount is the primary key.
    candidates = [entry for entry in candidates if entry.amount == credit.amount]

    # 2. Time window.
    candidates = [entry for entry in candidates if now - entry.created_at <= window]
    if not candidates:
        return None

    # 3. Name as a secondary signal — only when more than one amount match remains.
    if len(candidates) > 1 and credit.payer_name:
        target = normalize_name(credit.payer_name)
        named = [entry for entry in candidates if normalize_name(entry.customer_name) == target]
        if named:
            candidates = named

    # 4. Oldest-first tie-break.
    return min(candidates, key=lambda entry: entry.created_at)
