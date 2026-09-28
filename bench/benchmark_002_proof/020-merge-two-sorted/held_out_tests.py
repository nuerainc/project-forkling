from buggy import merge


def test_a_empty():
    assert merge([], [1, 2, 3]) == [1, 2, 3]


def test_both_empty():
    assert merge([], []) == []


def test_with_duplicates():
    # When the two lists overlap, ties are broken by taking from a first
    # (stable merge).
    assert merge([1, 2, 3], [2, 3, 4]) == [1, 2, 2, 3, 3, 4]


def test_negative_numbers():
    assert merge([-5, -1, 0], [-3, 2]) == [-5, -3, -1, 0, 2]
