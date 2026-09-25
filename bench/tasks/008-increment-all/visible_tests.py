from buggy import increment_all


def test_basic():
    assert increment_all([1, 2, 3]) == [2, 3, 4]


def test_empty():
    assert increment_all([]) == []


def test_does_not_mutate_input():
    src = [1, 2, 3]
    increment_all(src)
    assert src == [1, 2, 3]
