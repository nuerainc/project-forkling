from buggy import is_balanced


def test_nested_ok():
    assert is_balanced("a(b[c]{d})") is True


def test_wrong_closer_in_middle():
    assert is_balanced("(])") is False
