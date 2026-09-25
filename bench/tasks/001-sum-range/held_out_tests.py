from buggy import sum_range


def test_stop_equals_start():
    # Off-by-one: range(start, stop) excludes stop.
    # sum_range(7, 7) should be 7, not 0.
    assert sum_range(7, 7) == 7


def test_large_inclusive():
    # sum 1..10 = 55. range(1, 10) excludes 10 -> 45.
    assert sum_range(1, 10) == 55


def test_negative_inclusive():
    # sum -3..3 = 0 (since -3,-2,-1,0,1,2,3).
    # range(-3, 3) excludes 3 -> -3.
    assert sum_range(-3, 3) == 0
