from buggy import is_singleton


def test_none_is_singleton():
    # The whole point: buggy compares v == [None], so None never matches
    # a list. Correct: v is None.
    assert is_singleton(None) is True


def test_other_falsy():
    assert is_singleton(False) is False
    assert is_singleton(0.0) is False
    assert is_singleton(()) is False


def test_truthy():
    assert is_singleton("x") is False
    assert is_singleton(42) is False
