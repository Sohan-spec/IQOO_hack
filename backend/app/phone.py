"""Indian mobile numbers for enqueue. Matcher uses the last four digits of
the already-normalised 10-digit value; it does not import this module.
"""

from __future__ import annotations

import re

_DIGITS = re.compile(r"\D")


def normalize_in_mobile(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("customer_phone must be a string")
    raw = value.strip()
    if not raw:
        return None
    digits = _DIGITS.sub("", raw)
    if digits.startswith("91") and len(digits) >= 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) != 10 or digits[0] not in "6789":
        raise ValueError("customer_phone must be a 10-digit Indian mobile number")
    return digits
