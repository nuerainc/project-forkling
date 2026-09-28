from buggy import product_except_self


def test_no_zeros():
    assert product_except_self([1, 2, 3, 4]) == [24, 12, 8, 6]


def test_single_zero_in_middle():
    # Only the index that "is" the zero should be 8; the rest are 0.
    assert product_except_self([1, 2, 0, 4]) == [0, 0, 8, 0]


def test_zero_at_start():
    assert product_except_self([0, 1, 2, 3]) == [6, 0, 0, 0]


def test_two_elements():
    assert product_except_self([4, 2]) == [2, 4]
