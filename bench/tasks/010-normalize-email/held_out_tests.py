import pytest
from buggy import normalize_email


def test_raises_on_no_at():
    # Buggy: returns "not-an-email" because @ is missing (so the if-branch
    # is skipped and we reach return). Correct: raises ValueError.
    with pytest.raises(ValueError):
        normalize_email("not-an-email")


def test_raises_on_empty_string():
    with pytest.raises(ValueError):
        normalize_email("")


def test_preserves_at_sign():
    assert "@" in normalize_email("USER@HOST")
