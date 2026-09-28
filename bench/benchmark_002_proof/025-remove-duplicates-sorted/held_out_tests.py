from buggy import remove_duplicates


def test_all_same_values():
    assert remove_duplicates([5, 5, 5, 5]) == [5]


def test_all_distinct_values():
    assert remove_duplicates([1, 2, 3, 4]) == [1, 2, 3, 4]


def test_single_element():
    assert remove_duplicates([7]) == [7]


def test_two_elements_same():
    assert remove_duplicates([4, 4]) == [4]


def test_two_elements_distinct():
    assert remove_duplicates([4, 5]) == [4, 5]
