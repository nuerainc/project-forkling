from buggy import reverse_in_place


def test_reverse_basic():
    a = [1, 2, 3, 4]
    reverse_in_place(a)
    assert a == [4, 3, 2, 1]


def test_reverse_five_elements():
    a = [1, 2, 3, 4, 5]
    reverse_in_place(a)
    assert a == [5, 4, 3, 2, 1]