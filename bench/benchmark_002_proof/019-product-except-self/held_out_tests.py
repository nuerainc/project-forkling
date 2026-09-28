from buggy import product_except_self


def test_two_zeros():
    # Two zeros -> every output is zero.
    assert product_except_self([1, 0, 3, 0, 5]) == [0, 0, 0, 0, 0]


def test_no_zeros_three_elements():
    assert product_except_self([2, 3, 4]) == [12, 8, 6]


def test_negative_numbers():
    assert product_except_self([-1, 2, -3, 4]) == [-24, 12, -8, 6]


def test_zero_at_end():
    assert product_except_self([2, 5, 1, 0]) == [0, 0, 0, 10]


def test_all_zeros():
    assert product_except_self([0, 0, 0]) == [0, 0, 0]
