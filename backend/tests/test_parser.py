from __future__ import annotations

import json
from pathlib import Path

from app.parser import parse_credit

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "phonepe_credits.json"


def test_fixtures_parse_as_expected() -> None:
    rows = json.loads(FIXTURES.read_text(encoding="utf-8"))
    for row in rows:
        parsed = parse_credit(row["title"], row["text"])
        if row["expect_credit"]:
            assert parsed is not None, row["id"]
            assert format(parsed.amount, "f") == row["amount"], row["id"]
            assert parsed.payer_name == row["name"], row["id"]
            assert parsed.payer_phone_last4 == row.get("last4"), row["id"]
        else:
            assert parsed is None, row["id"]


def test_last4_comes_from_title_not_body() -> None:
    parsed = parse_credit(
        "PhonePe · ******4562 · Now",
        "sent ₹1 to you. ignore ******9999 in body",
    )
    assert parsed is not None
    assert parsed.payer_phone_last4 == "4562"
    assert format(parsed.amount, "f") == "1.00"
    assert parsed.payer_name == ""


def test_missing_title_last4_is_none() -> None:
    parsed = parse_credit("Payment received", "You have received ₹1.00 from A")
    assert parsed is not None
    assert parsed.payer_phone_last4 is None
