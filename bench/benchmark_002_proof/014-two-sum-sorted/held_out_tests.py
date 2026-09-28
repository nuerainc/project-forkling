from buggy import two_sum_sorted


def test_match_three_and_six():
    assert two_sum_sorted([1, 3, 4, 7], 7) == [1, 2]


def test_negative_numbers():
    assert two_sum_sorted([-3, -1, 2, 5], 1) == [1, 2]


def test_match_outer_pair_first():
    # Two pairs sum to 3 here: (0,3) and (1,2). Two-pointer returns the
    # leftmost such pair by index, which is [0, 3].
    assert two_sum_sorted([-2, 0, 3, 5], 3) == [0, 3]


def test_two_element_match():
    assert two_sum_sorted([3, 7], 10) == [0, 1]


def test_single_element_no_pair():
    assert two_sum_sorted([5], 10) == []
