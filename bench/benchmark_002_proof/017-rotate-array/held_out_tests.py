from buggy import rotate


def test_rotate_k_just_over():
    # 6 mod 5 == 1
    assert rotate([1, 2, 3, 4, 5], 6) == [2, 3, 4, 5, 1]


def test_rotate_zero():
    assert rotate([1, 2, 3], 0) == [1, 2, 3]


def test_rotate_empty():
    assert rotate([], 3) == []


def test_rotate_k_twice_len():
    # 10 mod 4 == 2
    assert rotate([1, 2, 3, 4], 10) == [3, 4, 1, 2]
