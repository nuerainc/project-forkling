from buggy import binary_search


def test_finds_middle():
    assert binary_search([1, 3, 5, 7, 9], 5) == 2


def test_finds_last_element():
    # BUGGY: returns -1. The loop ends when lo==hi, but the buggy
    # version never re-checks arr[lo]==target after exit.
    assert binary_search([1, 3, 5, 7, 9], 9) == 4


def test_returns_minus_one_when_missing():
    assert binary_search([1, 3, 5, 7, 9], 4) == -1


def test_empty_list():
    assert binary_search([], 7) == -1
