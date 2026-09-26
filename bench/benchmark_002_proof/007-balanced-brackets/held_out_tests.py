from buggy import is_balanced


def test_interleaved():
    assert is_balanced("([)]") is False


def test_lone_closer():
    assert is_balanced("]") is False


def test_closer_before_opener():
    assert is_balanced(")(") is False


def test_empty_and_deep():
    assert is_balanced("") is True
    assert is_balanced("{[()()]}") is True
