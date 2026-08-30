"""C3 — extract credited amount, optional payer name, optional masked last-4.

Two on-file shapes from 2026-08-30 (same last-4, different title wrapping):

    Listener EXTRA_TITLE (snapshot / injected replay of the ₹349 credit):
        title: "******4562: ******4562"
        text:  "sent ₹349 to you."

    OS shade as seen on the paying device (₹1 credit):
        title: "PhonePe · ******4562 · Now"
        text:  "sent ₹1 to you."

The shade prepends the app name and appends "Now"; NotificationListener
EXTRA_TITLE is the middle segment and, on this device, was also seen
duplicated as "******4562: ******4562". The masked tail is always in the
title (`*{6}` + four digits), never in the body. Amount is in the body
("sent ₹X to you."). There is no payer display name on this banner.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import NamedTuple

from app.models import parse_amount

_DEBIT = re.compile(
    r"\b(you paid|paid to|debited|debit alert|sent to|money sent)\b",
    re.I,
)
_PROMO = re.compile(
    r"\b(cashback|offer|reward|scratch card|won |congratulations)\b",
    re.I,
)
_CREDIT = re.compile(
    r"\b(received|credited|credit of|payment received)\b",
    re.I,
)
# Real inbound banner: "sent ₹349 to you." — not the debit phrase "sent to".
_INBOUND_SENT_TO_YOU = re.compile(r"\bsent\b.+\bto you\b", re.I)
_AMOUNT = re.compile(
    r"(?:₹|rs\.?|inr)\s*([0-9]{1,3}(?:,[0-9]{2,})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
    re.I,
)
_FROM = re.compile(
    r"\bfrom\s+([A-Za-z][A-Za-z. ]{0,80}?)(?:\s+(?:on|via|UPI|for)\b|[.\n]|$)",
    re.I,
)
# Title only: "PhonePe · ******4562 · Now" and "******4562: ******4562"
_MASKED_LAST4 = re.compile(r"\*{6}(\d{4})")


class ParsedCredit(NamedTuple):
    amount: Decimal
    payer_name: str
    payer_phone_last4: str | None


def _combined(title: str, text: str) -> str:
    return f"{title}\n{text}".strip()


def parse_credit(title: str, text: str) -> ParsedCredit | None:
    blob = _combined(title, text)
    if not blob:
        return None
    if _DEBIT.search(blob) or _PROMO.search(blob):
        return None
    if not _CREDIT.search(blob) and not _INBOUND_SENT_TO_YOU.search(blob):
        return None
    amount_match = _AMOUNT.search(text) or _AMOUNT.search(blob)
    if not amount_match:
        return None
    amount = parse_amount(amount_match.group(1))
    name_match = _FROM.search(blob)
    payer = name_match.group(1).strip() if name_match else ""
    last4_match = _MASKED_LAST4.search(title)
    last4 = last4_match.group(1) if last4_match else None
    return ParsedCredit(amount, payer, last4)
