from buggy import is_sorted


def test_equal_neighbors():
    assert is_sorted([1, 2, 2, 3]) is True


def test_unordered():
    assert is_sorted([1, 3, 2]) is False