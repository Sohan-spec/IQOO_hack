from __future__ import annotations

import asyncio
import logging

from app.runtime import Runtime


PHONEPE = "com.phonepe.app"
CREDIT_TITLE = "Payment received"
CREDIT_TEXT = "You have received Rs. 150.00 from PRIYA SHARMA"
DEBIT_TITLE = "Payment successful"
DEBIT_TEXT = "You paid Rs. 150.00 to RELAY STORE"


async def _non_credit_in_raw_only() -> None:
    runtime = Runtime()
    credit = await runtime.ingest_notification(PHONEPE, DEBIT_TITLE, DEBIT_TEXT)
    assert credit is None
    snap = runtime.snapshot()
    assert snap["recent_credits"] == []
    raw = snap["recent_raw_notifications"]
    assert len(raw) == 1
    assert raw[0]["package"] == PHONEPE
    assert raw[0]["title"] == DEBIT_TITLE
    assert raw[0]["text"] == DEBIT_TEXT
    assert raw[0]["parsed"] is False
    assert "posted_at" in raw[0]


async def _credit_in_raw_and_credits() -> None:
    runtime = Runtime()
    credit = await runtime.ingest_notification(PHONEPE, CREDIT_TITLE, CREDIT_TEXT)
    assert credit is not None
    snap = runtime.snapshot()
    credits = snap["recent_credits"]
    assert len(credits) == 1
    assert credits[0]["title"] == CREDIT_TITLE
    assert credits[0]["text"] == CREDIT_TEXT
    assert credits[0]["amount"] == "150.00"
    assert credits[0]["payer_name"] == "PRIYA SHARMA"
    raw = snap["recent_raw_notifications"]
    assert len(raw) == 1
    assert raw[0]["parsed"] is True
    assert raw[0]["package"] == PHONEPE
    assert raw[0]["title"] == CREDIT_TITLE
    assert raw[0]["text"] == CREDIT_TEXT


def test_non_credit_stored_in_raw_not_credits() -> None:
    asyncio.run(_non_credit_in_raw_only())


def test_credit_stored_in_raw_and_credits() -> None:
    asyncio.run(_credit_in_raw_and_credits())


def test_ingest_logs_package_title_text(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.runtime"):
        asyncio.run(Runtime().ingest_notification(PHONEPE, DEBIT_TITLE, DEBIT_TEXT))
    assert f"package={PHONEPE}" in caplog.text
    assert f"title={DEBIT_TITLE}" in caplog.text
    assert f"text={DEBIT_TEXT}" in caplog.text
    assert "parsed=False" in caplog.text
