from buggy import running_sum


def test_empty():
    assert running_sum([]) == []


def test_single_element():
    assert running_sum([7]) == [7]


def test_all_zeros():
    assert running_sum([0, 0, 0]) == [0, 0, 0]


def test_negative_and_positive():
    assert running_sum([-1, 2, -3, 4]) == [-1, 1, -2, 2]