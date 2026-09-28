from buggy import second_largest


def test_basic():
    assert second_largest([1, 5, 3, 4]) == 4


def test_two_elements():
    assert second_largest([10, 20]) == 10


def test_all_duplicates():
    assert second_largest([5, 5, 5]) is None


def test_empty_list():
    assert second_largest([]) is None
