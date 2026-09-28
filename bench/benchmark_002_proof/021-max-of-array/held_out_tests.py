from buggy import max_of


def test_single_element():
    assert max_of([42]) == 42


def test_with_zero():
    assert max_of([-1, 0, 1]) == 1


def test_max_in_middle():
    assert max_of([2, 9, 4]) == 9


def test_all_same():
    assert max_of([5, 5, 5]) == 5
