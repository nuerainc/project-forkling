from buggy import is_palindrome


def test_simple_palindrome():
    assert is_palindrome("racecar") is True


def test_simple_not_palindrome():
    assert is_palindrome("hello") is False


def test_uppercase_palindrome():
    # Buggy version preserves case; this should fail without lowercasing.
    assert is_palindrome("RaceCar") is True
