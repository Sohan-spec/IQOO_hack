"""C1 / C4 / C5 / R1 orchestration. All decision logic lives here."""

from __future__ import annotations

from datetime import timedelta

from app.config import DEFAULT_CALLBACK_URL, EXPIRY_SECONDS
from app.confirm import ConfirmationSender
from app.events import EventLog
from app.matcher import select_candidate
from app.models import CreditEvent, MatchEvent, PendingEntry, parse_amount, parse_iso, utcnow
from app.parser import parse_credit
from app.queue import TransactionQueue
from app.state import PENDING, mark_confirmed


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
    ) -> tuple[str, PendingEntry]:
        url = (callback_url or self.default_callback_url).strip()
        entry = PendingEntry(
            session_id=session_id.strip(),
            customer_name=customer_name.strip(),
            amount=parse_amount(amount),
            created_at=utcnow(),
            status=PENDING,
            callback_url=url,
        )
        return await self.queue.enqueue(entry)

    async def ingest_notification(
        self,
        package: str,
        title: str,
        text: str,
        posted_at=None,
    ) -> CreditEvent | None:
        parsed = parse_credit(title, text)
        if parsed is None:
            return None
        amount, payer_name = parsed
        when = posted_at if hasattr(posted_at, "isoformat") else parse_iso(posted_at)
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
        self.events.add_match(
            MatchEvent(
                session_id=matched.session_id,
                customer_name=matched.customer_name,
                amount=matched.amount,
                payer_name=credit.payer_name,
                source="matcher",
            )
        )
        await self.sender.send(matched)
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
        self.events.add_match(
            MatchEvent(
                session_id=matched.session_id,
                customer_name=matched.customer_name,
                amount=matched.amount,
                payer_name=matched.customer_name,
                source="manual",
            )
        )
        await self.sender.send(matched)
        return matched

    async def sweep_expired(self) -> None:
        await self.queue.expire_due(utcnow(), self.expiry)

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
            "recent_matches": [event.to_public_dict() for event in self.events.matches],
            "server": {"bind": "0.0.0.0:8787"},
        }
