from app.phone import normalize_in_mobile


def test_normalize_strips_country_code_and_separators() -> None:
    assert normalize_in_mobile("9876543210") == "9876543210"
    assert normalize_in_mobile("+91 98765-43210") == "9876543210"
    assert normalize_in_mobile("09876543210") == "9876543210"
    assert normalize_in_mobile("  ") is None
    assert normalize_in_mobile(None) is None


def test_normalize_rejects_malformed() -> None:
    try:
        normalize_in_mobile("12345")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        normalize_in_mobile("0123456789")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
