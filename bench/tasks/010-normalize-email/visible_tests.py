import pytest
from buggy import normalize_email


def test_basic_lowercases():
    # Buggy raises ValueError on this. Correct returns "foo@bar.com".
    assert normalize_email("Foo@Bar.COM") == "foo@bar.com"


def test_strips_whitespace():
    # Buggy raises ValueError. Correct returns "a@b.co".
    assert normalize_email("  a@b.co  ") == "a@b.co"


def test_does_not_raise_on_valid():
    # Sanity: a valid email should NOT raise.
    normalize_email("ok@example.com")
