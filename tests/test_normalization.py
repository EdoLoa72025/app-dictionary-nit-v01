from backend.normalization import normalize_identification, parse_number


def test_long_identification_is_kept_as_text():
    assert normalize_identification("12345678901234567890") == (
        "12345678901234567890"
    )


def test_number_formats():
    assert parse_number("1.234.567,89") == 1234567.89
    assert parse_number("1234567.89") == 1234567.89
