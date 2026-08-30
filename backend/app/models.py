from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

TWOPLACES = Decimal("0.01")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_amount(value: Any) -> Decimal:
    if value is None:
        raise ValueError("amount is required")
    if isinstance(value, bool):
        raise ValueError("amount must be a number")
    try:
        amount = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("amount is not a valid decimal") from exc
    amount = amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if amount <= 0:
        raise ValueError("amount must be > 0")
    return amount


def parse_iso(value: str | None) -> datetime:
    if not value:
        return utcnow()
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("posted_at is not ISO-8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@dataclass
class PendingEntry:
    session_id: str
    customer_name: str
    amount: Decimal
    created_at: datetime
    status: str
    callback_url: str
    confirm_acked: bool = False
    customer_phone: str | None = None
    customer_email: str | None = None
    confirmed_at: datetime | None = None

    def to_public_dict(self, now: datetime | None = None) -> dict[str, Any]:
        clock = now or utcnow()
        elapsed = (clock - self.created_at).total_seconds()
        return {
            "session_id": self.session_id,
            "customer_name": self.customer_name,
            "amount": format(self.amount, "f"),
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "confirm_acked": self.confirm_acked,
            "elapsed_seconds": max(0, int(elapsed)),
            "customer_phone": self.customer_phone,
            "customer_email": self.customer_email,
        }


@dataclass
class CreditEvent:
    package: str
    title: str
    text: str
    amount: Decimal
    payer_name: str
    posted_at: datetime
    raw: str = ""
    payer_phone_last4: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "package": self.package,
            "title": self.title,
            "text": self.text,
            "amount": format(self.amount, "f"),
            "payer_name": self.payer_name,
            "payer_phone_last4": self.payer_phone_last4,
            "posted_at": self.posted_at.isoformat(),
        }


@dataclass
class RawNotification:
    package: str
    title: str
    text: str
    posted_at: datetime
    parsed: bool

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "package": self.package,
            "title": self.title,
            "text": self.text,
            "posted_at": self.posted_at.isoformat(),
            "parsed": self.parsed,
        }


@dataclass
class MatchEvent:
    session_id: str
    customer_name: str
    amount: Decimal
    payer_name: str
    source: str
    at: datetime = field(default_factory=utcnow)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "customer_name": self.customer_name,
            "amount": format(self.amount, "f"),
            "payer_name": self.payer_name,
            "source": self.source,
            "at": self.at.isoformat(),
        }
