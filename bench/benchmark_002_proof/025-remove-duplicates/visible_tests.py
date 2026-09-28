from buggy import remove_duplicates


def test_with_duplicates():
    assert remove_duplicates([1, 1, 2, 3, 3]) == [1, 2, 3]


def test_empty_list():
    assert remove_duplicates([]) == []