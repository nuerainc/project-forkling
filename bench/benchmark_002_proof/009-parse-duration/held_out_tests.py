import pytest

from buggy import parse_duration


def test_all_units():
    assert parse_duration("1h1m1s") == 3661


def test_multi_digit_after_unit():
    assert parse_duration("10m15s") == 615


def test_unknown_unit():
    with pytest.raises(ValueError):
        parse_duration("5x")


def test_missing_trailing_unit():
    with pytest.raises(ValueError):
        parse_duration("1h30")
