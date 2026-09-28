from buggy import max_of


def test_basic():
    assert max_of([1, 5, 3]) == 5


def test_negative_numbers():
    assert max_of([-3, -1, -7]) == -1


def test_empty_returns_none():
    assert max_of([]) is None


def test_max_at_end():
    assert max_of([1, 2, 7]) == 7
