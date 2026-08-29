from __future__ import annotations

from collections import deque

from app.config import EVENT_LOG_SIZE
from app.models import CreditEvent, MatchEvent, RawNotification


class EventLog:
    def __init__(self, size: int = EVENT_LOG_SIZE) -> None:
        self.credits: deque[CreditEvent] = deque(maxlen=size)
        self.matches: deque[MatchEvent] = deque(maxlen=size)
        self.raw_notifications: deque[RawNotification] = deque(maxlen=size)

    def add_credit(self, event: CreditEvent) -> None:
        self.credits.appendleft(event)

    def add_match(self, event: MatchEvent) -> None:
        self.matches.appendleft(event)

    def add_raw_notification(self, event: RawNotification) -> None:
        self.raw_notifications.appendleft(event)
