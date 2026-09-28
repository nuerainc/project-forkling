from buggy import binary_search


def test_finds_last_element():
    assert binary_search([1, 3, 5, 7, 9], 9) == 4


def test_finds_only_element():
    assert binary_search([42], 42) == 0


def test_finds_in_long_list():
    arr = list(range(0, 1001, 2))  # even numbers 0..1000
    assert binary_search(arr, 504) == 252


def test_target_below_all():
    assert binary_search([5, 10, 15], 1) == -1
