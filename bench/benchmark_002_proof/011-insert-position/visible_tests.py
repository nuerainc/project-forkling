from buggy import insert_position


def test_between_values():
    assert insert_position([1, 3, 5], 4) == 2


def test_duplicates_leftmost():
    assert insert_position([1, 2, 2, 2, 3], 2) == 1
