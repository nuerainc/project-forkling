from buggy import rotate


def test_rotate_basic():
    assert rotate([1, 2, 3, 4, 5], 2) == [3, 4, 5, 1, 2]


def test_rotate_k_greater_than_len():
    # 7 mod 5 == 2, so the expected output equals a rotation by 2.
    assert rotate([1, 2, 3, 4, 5], 7) == [3, 4, 5, 1, 2]


def test_rotate_k_equals_len():
    assert rotate([1, 2, 3, 4, 5], 5) == [1, 2, 3, 4, 5]


def test_rotate_single_element():
    assert rotate([42], 100) == [42]
