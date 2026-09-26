from buggy import merge_intervals


def test_unsorted_input():
    assert merge_intervals([[8, 10], [1, 3], [2, 6]]) == [[1, 6], [8, 10]]


def test_touching_intervals_merge():
    assert merge_intervals([[1, 2], [2, 3]]) == [[1, 3]]


def test_contained_then_extended():
    assert merge_intervals([[1, 10], [2, 3], [4, 12]]) == [[1, 12]]


def test_empty_and_input_not_mutated():
    data = [[1, 5], [2, 3]]
    assert merge_intervals([]) == []
    merge_intervals(data)
    assert data == [[1, 5], [2, 3]]
