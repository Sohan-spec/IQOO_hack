"""C1 / C4 / C5 / R1 orchestration. All decision logic lives here."""

from __future__ import annotations

import logging
from datetime import timedelta

from app.config import DEFAULT_CALLBACK_URL, EXPIRY_SECONDS, PII_TTL_SECONDS
from app.confirm import ConfirmationSender
from app.events import EventLog
from app.matcher import select_candidate
from app.models import (
    CreditEvent,
    MatchEvent,
    PendingEntry,
    RawNotification,
    parse_amount,
    parse_iso,
    utcnow,
)
from app.parser import parse_credit
from app.queue import TransactionQueue
from app.state import CONFIRMED, PENDING, mark_confirmed

logger = logging.getLogger(__name__)


class Runtime:
    def __init__(
        self,
        queue: TransactionQueue | None = None,
        sender: ConfirmationSender | None = None,
        default_callback_url: str = DEFAULT_CALLBACK_URL,
        expiry_seconds: int = EXPIRY_SECONDS,
    ) -> None:
        self.queue = queue or TransactionQueue()
        self.events = EventLog()
        self.sender = sender or ConfirmationSender()
        self.default_callback_url = default_callback_url
        self.expiry = timedelta(seconds=expiry_seconds)

    async def enqueue(
        self,
        session_id: str,
        customer_name: str,
        amount,
        callback_url: str,
        customer_phone: str | None = None,
        customer_email: str | None = None,
    ) -> tuple[str, PendingEntry]:
        url = (callback_url or self.default_callback_url).strip()
        entry = PendingEntry(
            session_id=session_id.strip(),
            customer_name=customer_name.strip(),
            amount=parse_amount(amount),
            created_at=utcnow(),
            status=PENDING,
            callback_url=url,
            customer_phone=customer_phone,
            customer_email=customer_email,
        )
        return await self.queue.enqueue(entry)

    async def ingest_notification(
        self,
        package: str,
        title: str,
        text: str,
        posted_at=None,
    ) -> CreditEvent | None:
        when = posted_at if hasattr(posted_at, "isoformat") else parse_iso(posted_at)
        parsed = parse_credit(title, text)
        logger.info(
            "ingest package=%s title=%s text=%s parsed=%s",
            package,
            title,
            text,
            parsed is not None,
        )
        self.events.add_raw_notification(
            RawNotification(
                package=package,
                title=title,
                text=text,
                posted_at=when,
                parsed=parsed is not None,
            )
        )
        if parsed is None:
            return None
        amount, payer_name = parsed
        credit = CreditEvent(
            package=package,
            title=title,
            text=text,
            amount=amount,
            payer_name=payer_name,
            posted_at=when,
            raw=f"{title}\n{text}",
        )
        self.events.add_credit(credit)
        await self._match_and_confirm(credit)
        return credit

    async def _match_and_confirm(self, credit: CreditEvent) -> PendingEntry | None:
        async with self.queue.lock:
            # This lock wraps the full read-check-transition-to-confirmed sequence
            # so an in-flight automatic match and a manual confirm click on the
            # same session cannot both succeed.
            winner = select_candidate(
                self.queue.all_unlocked(),
                credit,
                utcnow(),
                self.expiry,
            )
            if winner is None or not mark_confirmed(winner):
                return None
            matched = winner
            matched.confirmed_at = utcnow()
        self.events.add_match(
            MatchEvent(
                session_id=matched.session_id,
                customer_name=matched.customer_name,
                amount=matched.amount,
                payer_name=credit.payer_name,
                source="matcher",
            )
        )
        self.sender.submit(matched)
        return matched

    async def manual_confirm(self, session_id: str) -> PendingEntry | None:
        async with self.queue.lock:
            # This lock wraps the full read-check-transition-to-confirmed sequence
            # so an in-flight automatic match and a manual confirm click on the
            # same session cannot both succeed.
            entry = self.queue.get_unlocked(session_id)
            if not mark_confirmed(entry):
                return None
            matched = entry
            matched.confirmed_at = utcnow()
        self.events.add_match(
            MatchEvent(
                session_id=matched.session_id,
                customer_name=matched.customer_name,
                amount=matched.amount,
                payer_name=matched.customer_name,
                source="manual",
            )
        )
        self.sender.submit(matched)
        return matched

    async def sweep_expired(self) -> None:
        expired = await self.queue.expire_due(utcnow(), self.expiry)
        for entry in expired:
            self._clear_pii(entry)
        now = utcnow()
        ttl = timedelta(seconds=PII_TTL_SECONDS)
        for entry in self.queue.all_unlocked():
            if entry.status != CONFIRMED or entry.confirmed_at is None:
                continue
            if now - entry.confirmed_at > ttl:
                self._clear_pii(entry)

    @staticmethod
    def _clear_pii(entry: PendingEntry) -> None:
        entry.customer_phone = None
        entry.customer_email = None

    def snapshot(self) -> dict:
        now = utcnow()
        pending = [
            entry.to_public_dict(now)
            for entry in self.queue.all_unlocked()
            if entry.status == PENDING
        ]
        pending.sort(key=lambda item: item["created_at"])
        return {
            "pending": pending,
            "recent_credits": [event.to_public_dict() for event in self.events.credits],
            "recent_raw_notifications": [
                event.to_public_dict() for event in self.events.raw_notifications
            ],
            "recent_matches": [self._recent_match_dict(event) for event in self.events.matches],
            "default_callback_url": self.default_callback_url,
            "server": {"bind": "0.0.0.0:8787"},
        }

    def _recent_match_dict(self, event: MatchEvent) -> dict:
        item = event.to_public_dict()
        item["via"] = "auto" if event.source == "matcher" else "manual"
        item["matched_at"] = item["at"]
        live = self.queue.get_unlocked(event.session_id)
        if live is not None:
            item["status"] = live.status
            # Read on the asyncio-loop thread; the confirm worker writes this
            # bool. Only atomic-attribute writes are allowed on this field.
            item["confirm_acked"] = live.confirm_acked
        else:
            item.setdefault("status", "confirmed")
            item.setdefault("confirm_acked", False)
        return item
