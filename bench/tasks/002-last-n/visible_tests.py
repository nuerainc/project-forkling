from buggy import last_n


def test_basic():
    assert last_n([1, 2, 3, 4, 5], 2) == [4, 5]


def test_n_larger_than_len():
    assert last_n([1, 2, 3], 5) == [1, 2, 3]


def test_n_zero():
    assert last_n([1, 2, 3], 0) == []
