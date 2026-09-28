from buggy import is_sorted


def test_empty_list():
    assert is_sorted([]) is True


def test_single_element():
    assert is_sorted([5]) is True


def test_all_equal():
    assert is_sorted([4, 4, 4]) is True


def test_strictly_descending():
    assert is_sorted([3, 2, 1]) is False


def test_strictly_ascending():
    assert is_sorted([1, 2, 3]) is True