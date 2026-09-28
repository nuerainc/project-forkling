from buggy import is_palindrome


def test_empty_string():
    assert is_palindrome("") is True


def test_single_char():
    assert is_palindrome("a") is True


def test_uppercase_non_palindrome():
    # Buggy version: "Aa" filtered="Aa", reversed="aA", not equal -> False.
    # Expected: "aa" reversed="aa" -> True.
    assert is_palindrome("Aa") is True
