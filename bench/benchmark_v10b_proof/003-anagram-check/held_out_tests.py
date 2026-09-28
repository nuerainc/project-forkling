from buggy import is_anagram


def test_case_insensitive():
    assert is_anagram("Listen", "SILENT") is True


def test_empty_strings():
    assert is_anagram("", "") is True


def test_different_lengths():
    assert is_anagram("aabb", "ababcc") is False
