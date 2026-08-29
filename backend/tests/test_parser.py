from __future__ import annotations

import json
from pathlib import Path

from app.parser import parse_credit

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "phonepe_credits.json"


def test_fixtures_parse_as_expected() -> None:
    rows = json.loads(FIXTURES.read_text())
    for row in rows:
        parsed = parse_credit(row["title"], row["text"])
        if row["expect_credit"]:
            assert parsed is not None, row["id"]
            amount, name = parsed
            assert format(amount, "f") == row["amount"], row["id"]
            assert name == row["name"], row["id"]
        else:
            assert parsed is None, row["id"]
