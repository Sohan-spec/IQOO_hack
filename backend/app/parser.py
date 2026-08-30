"""C3 — extract credited amount and payer name; drop non-credits.

R3 capture from the demo iQOO is still pending. Regexes and
backend/app/fixtures/phonepe_credits.json are placeholders, not strings
captured from this device.

Last-4 payer phone matching is validated-false until a real OS banner
is shown to contain that field. Do not extract a last-4 into payer_name.
"""

from __future__ import annotations

import re
from decimal import Decimal

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
_AMOUNT = re.compile(
    r"(?:₹|rs\.?|inr)\s*([0-9]{1,3}(?:,[0-9]{2,})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
    re.I,
)
_FROM = re.compile(
    r"\bfrom\s+([A-Za-z][A-Za-z. ]{0,80}?)(?:\s+(?:on|via|UPI|for)\b|[.\n]|$)",
    re.I,
)


def _combined(title: str, text: str) -> str:
    return f"{title}\n{text}".strip()


def parse_credit(title: str, text: str) -> tuple[Decimal, str] | None:
    blob = _combined(title, text)
    if not blob:
        return None
    if _DEBIT.search(blob) or _PROMO.search(blob):
        return None
    if not _CREDIT.search(blob):
        return None
    amount_match = _AMOUNT.search(blob)
    if not amount_match:
        return None
    amount = parse_amount(amount_match.group(1))
    name_match = _FROM.search(blob)
    payer = name_match.group(1).strip() if name_match else ""
    return amount, payer
