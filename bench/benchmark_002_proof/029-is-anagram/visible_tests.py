from buggy import is_anagram


def test_case_insensitive_anagram():
    assert is_anagram("Listen", "silent") is True


def test_simple_not_anagrams():
    assert is_anagram("hello", "world") is False