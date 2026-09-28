from buggy import two_sum_sorted


def test_match_first_and_last():
    assert two_sum_sorted([2, 5, 9, 11], 13) == [0, 3]


def test_match_middle_pair():
    assert two_sum_sorted([1, 2, 4, 6], 6) == [1, 2]


def test_target_too_small():
    assert two_sum_sorted([1, 3, 5, 7], 0) == []


def test_target_too_large():
    assert two_sum_sorted([1, 3, 5, 7], 100) == []
