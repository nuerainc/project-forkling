from buggy import is_anagram


def test_empty_strings():
    assert is_anagram("", "") is True


def test_single_char_match():
    assert is_anagram("a", "a") is True


def test_identical_with_case_diff():
    assert is_anagram("Hello", "hello") is True


def test_different_lengths():
    assert is_anagram("abc", "ab") is False


def test_whitespace_inside():
    assert is_anagram("a b c", "abc") is True