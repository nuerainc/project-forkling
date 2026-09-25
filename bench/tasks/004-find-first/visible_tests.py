from buggy import find_first


def test_basic():
    assert find_first([1, 2, 3], 2) == 1


def test_not_found():
    assert find_first([], 5) == -1


def test_strings_not_found():
    assert find_first(["a", "b"], "c") == -1


def test_equal_but_not_identical_lists():
    # Lists are equal by value but never by identity. The buggy `is`
    # check will always miss these — `find_first` returns -1.
    # Correct: returns 1.
    assert find_first([[1], [2]], [2]) == 1
