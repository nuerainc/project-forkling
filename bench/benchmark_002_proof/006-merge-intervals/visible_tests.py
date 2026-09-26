from buggy import merge_intervals


def test_overlap():
    assert merge_intervals([[1, 3], [2, 6], [8, 10]]) == [[1, 6], [8, 10]]


def test_contained_interval():
    assert merge_intervals([[1, 10], [2, 3]]) == [[1, 10]]
