"""C4 matcher. Ordered rules — stop at first resolution.

step 0: candidates = entries where status == pending
1. Amount exact Decimal equality
2. Drop candidates older than the expiry window
3. If multiple remain: last-4 of stored customer_phone vs extracted
   payer_phone_last4. A mismatch does not reject; it only narrows when at
   least one candidate matches. A single amount+window candidate always
   wins even when the typed phone tail differs from the banner.
4. If still multiple: normalised case-insensitive name compare
5. Else oldest created_at
6. Zero candidates → no confirm
7. Confirm at most once (enforced by the confirm critical section, not here)

customer_email is display-only. This module must never read it.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from app.models import CreditEvent, PendingEntry
from app.state import PENDING

_WS = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    return _WS.sub(" ", name.casefold()).strip()


def stored_phone_last4(entry: PendingEntry) -> str | None:
    phone = entry.customer_phone
    if not phone or len(phone) < 4 or not phone[-4:].isdigit():
        return None
    return phone[-4:]


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

    # 3. Last-4 — only when more than one amount+window match remains.
    if len(candidates) > 1 and credit.payer_phone_last4:
        tailed = [
            entry
            for entry in candidates
            if stored_phone_last4(entry) == credit.payer_phone_last4
        ]
        if tailed:
            candidates = tailed

    # 4. Name as a secondary signal — only when more than one match remains.
    if len(candidates) > 1 and credit.payer_name:
        target = normalize_name(credit.payer_name)
        named = [entry for entry in candidates if normalize_name(entry.customer_name) == target]
        if named:
            candidates = named

    # 5. Oldest-first tie-break.
    return min(candidates, key=lambda entry: entry.created_at)
