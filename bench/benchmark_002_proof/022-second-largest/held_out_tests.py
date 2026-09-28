from buggy import second_largest


def test_negative_numbers():
    assert second_largest([-3, -1, -7]) == -3


def test_descending():
    assert second_largest([5, 4, 3, 2, 1]) == 4


def test_single_element():
    assert second_largest([42]) is None


def test_with_zero():
    assert second_largest([0, 10, 5]) == 5
