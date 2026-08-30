"""DEMO-ONLY FAKE MATCH — not real payment verification.

Strip this file and the `apply_demo_hardcoded_match` call in runtime.py.

Activates only for the exact hardcoded credit:
  payer_phone_last4 == "4562"
  amount == 349.00  (same Decimal/2-dp convention as parse_amount)

On match, fires one C5 confirm for session demo-4562-349 and records
one MatchEvent. Duplicate PhonePe banners for the same credit are ignored.
The real matcher is skipped for this credit so a waiting ₹349 row is not
counted a second time.
"""

from __future__ import annotations

import logging

from app.models import CreditEvent, MatchEvent, PendingEntry, parse_amount, utcnow
from app.state import CONFIRMED, PENDING, mark_confirmed

logger = logging.getLogger(__name__)

DEMO_PAYER_LAST4 = "4562"
DEMO_AMOUNT = parse_amount("349.00")
DEMO_DISPLAY_NAME = "SOHAN REDDY P"
DEMO_DISPLAY_PHONE = "9108234562"
# Must match checkout/index.html DEMO_SESSION_ID.
DEMO_SESSION_ID = "demo-4562-349"
# Used only when no pending callback_url and no operator default is set.
DEMO_FALLBACK_CALLBACK_URL = "https://sohan-spec--pay.modal.run/confirm"


def is_demo_hardcoded_match(credit: CreditEvent) -> bool:
    return credit.payer_phone_last4 == DEMO_PAYER_LAST4 and credit.amount == DEMO_AMOUNT


def demo_match_already_recorded(runtime) -> bool:
    return any(event.session_id == DEMO_SESSION_ID for event in runtime.events.matches)


async def apply_demo_hardcoded_match(runtime, credit: CreditEvent) -> bool:
    """Handle the 4562 + ₹349 demo credit. True → skip the real matcher."""
    if not is_demo_hardcoded_match(credit):
        return False

    async with runtime.queue.lock:
        if demo_match_already_recorded(runtime):
            logger.info(
                "DEMO FASTPATH skip duplicate last4=%s amount=%s",
                credit.payer_phone_last4,
                format(credit.amount, "f"),
            )
            return True

        pending = [
            entry for entry in runtime.queue.all_unlocked() if entry.status == PENDING
        ]
        open_349 = None
        for entry in sorted(pending, key=lambda item: item.created_at):
            if entry.amount == DEMO_AMOUNT:
                open_349 = entry
                break

        callback_url = ""
        if open_349 is not None:
            callback_url = (open_349.callback_url or "").strip()
        if not callback_url:
            callback_url = (runtime.default_callback_url or "").strip()
        if not callback_url:
            callback_url = DEMO_FALLBACK_CALLBACK_URL

        logger.info(
            "DEMO FASTPATH hardcoded match last4=%s amount=%s "
            "demo_session_id=%s open_session_id=%s callback_host=%s",
            credit.payer_phone_last4,
            format(credit.amount, "f"),
            DEMO_SESSION_ID,
            open_349.session_id if open_349 is not None else None,
            callback_url.split("/")[2] if "://" in callback_url else "",
        )

        runtime.events.add_match(
            MatchEvent(
                session_id=DEMO_SESSION_ID,
                customer_name=DEMO_DISPLAY_NAME,
                amount=DEMO_AMOUNT,
                payer_name=DEMO_DISPLAY_NAME,
                source="demo",
            )
        )
        demo_entry = PendingEntry(
            session_id=DEMO_SESSION_ID,
            customer_name=DEMO_DISPLAY_NAME,
            amount=DEMO_AMOUNT,
            created_at=utcnow(),
            status=CONFIRMED,
            callback_url=callback_url,
            customer_phone=DEMO_DISPLAY_PHONE,
            confirmed_at=utcnow(),
        )
        extra = None
        if open_349 is not None and mark_confirmed(open_349):
            open_349.confirmed_at = utcnow()
            extra = open_349

    runtime.sender.submit(demo_entry)
    if extra is not None:
        # Flip a waiting Pay tab without a second owner-app match row.
        runtime.sender.submit(extra)
    return True
