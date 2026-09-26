from buggy import insert_position


def test_empty():
    assert insert_position([], 7) == 0


def test_all_equal():
    assert insert_position([2, 2, 2, 2], 2) == 0


def test_bounds():
    assert insert_position([1, 2, 3], 0) == 0
    assert insert_position([1, 2, 3], 9) == 3


def test_exact_match_single():
    assert insert_position([5], 5) == 0
