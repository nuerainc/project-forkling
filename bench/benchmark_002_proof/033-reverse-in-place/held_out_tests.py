from buggy import reverse_in_place


def test_reverse_empty():
    a = []
    reverse_in_place(a)
    assert a == []


def test_reverse_single():
    a = [9]
    reverse_in_place(a)
    assert a == [9]


def test_reverse_two_elements():
    a = [1, 2]
    reverse_in_place(a)
    assert a == [2, 1]


def test_reverse_palindrome():
    a = [1, 2, 3, 2, 1]
    reverse_in_place(a)
    assert a == [1, 2, 3, 2, 1]