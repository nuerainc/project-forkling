from buggy import merge


def test_b_is_longer():
    # B keeps emitting values after A is exhausted.
    assert merge([1, 3, 5], [2, 4, 6, 8, 10]) == [1, 2, 3, 4, 5, 6, 8, 10]


def test_a_is_longer():
    assert merge([1, 5, 10, 12], [3, 4]) == [1, 3, 4, 5, 10, 12]


def test_one_input_empty():
    assert merge([1, 2], []) == [1, 2]


def test_equal_length():
    assert merge([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]
