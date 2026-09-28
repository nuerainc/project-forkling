from buggy import running_sum


def test_basic_running_sum():
    assert running_sum([1, 2, 3, 4]) == [1, 3, 6, 10]


def test_two_elements():
    assert running_sum([1, 2]) == [1, 3]