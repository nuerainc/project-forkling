from buggy import is_singleton


def test_none_is_singleton():
    # The whole point. Buggy: returns False. Correct: True.
    assert is_singleton(None) is True


def test_zero_is_not_none():
    assert is_singleton(0) is False


def test_empty_string_is_not_none():
    assert is_singleton("") is False


def test_empty_list_is_not_none():
    assert is_singleton([]) is False
