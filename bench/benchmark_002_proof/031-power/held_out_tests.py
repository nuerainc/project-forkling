from buggy import power


def test_zero_base_positive_exp():
    assert power(0, 5) == 0


def test_zero_exp_nonzero_base():
    assert power(5, 0) == 1


def test_exp_one():
    assert power(7, 1) == 7


def test_exp_two_small_base():
    assert power(2, 4) == 16


def test_base_one_large_exp():
    assert power(1, 10) == 1