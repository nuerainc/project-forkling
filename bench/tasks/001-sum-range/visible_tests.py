from buggy import sum_range


def test_basic_range():
    assert sum_range(1, 5) == 15


def test_zero_to_zero():
    assert sum_range(0, 0) == 0


def test_single_step():
    assert sum_range(3, 4) == 7
