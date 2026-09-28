from buggy import is_anagram


def test_simple_anagram():
    assert is_anagram("listen", "silent") is True


def test_simple_not_anagram():
    assert is_anagram("hello", "world") is False


def test_with_spaces():
    assert is_anagram("conversation", "voices rant on") is True
