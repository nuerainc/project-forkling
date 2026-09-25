from buggy import reverse_string


def test_empty():
    # Buggy returns "" by accident (input is ""). Correct also returns "".
    # Held out still validates the fix doesn't break the edge.
    assert reverse_string("") == ""


def test_palindrome():
    # Palindrome should reverse to itself.
    assert reverse_string("racecar") == "racecar"


def test_numbers_as_string():
    assert reverse_string("12345") == "54321"
